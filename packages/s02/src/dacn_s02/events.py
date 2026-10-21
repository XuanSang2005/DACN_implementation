"""Typed operational invariants. This is not a clarification orchestrator."""
from .errors import require
from .validation import walk_schema,SCHEMA,resolve_pointer
from dacn_s01.revision import json_equal


def validate_operations(commands,events,stages,records,owners,snapshots):
    def record(i,kind=None):
        r=records.get(i);require(r is not None and (kind is None or r['type']==kind),'event_record_type');return r['body']
    def ref(value,kind=None):
        e=events.get((value['command_id'],value['event_id']))
        require(e is not None and (kind is None or e['kind']==kind),'event_ref_kind');return e
    def stage(value):
        s=stages.get((value['command_id'],value['blob_id']));require(s is not None,'event_stage_reference');return s
    def lineage(cmd):
        seen=set()
        while cmd:
            require(cmd in commands and cmd not in seen,'command_lineage');seen.add(cmd);cmd=commands[cmd]['parent_command_id']
        return seen
    def check_attempts(run, ordered, promotions):
        """T3 evidence must describe the same call pinned at T0/T1/T2.

        One dispatch per command in this foundation. No provider-specific
        response enrichment: captured metadata (including null) is authoritative.
        """
        prepared=ordered[0]['payload']
        dispatch=next((e['payload'] for e in ordered if e['kind']=='dispatch_intent'),None)
        capture=next((e['payload'] for e in ordered if e['kind']=='response_received'),None)
        promoted={(x['stage_ref']['command_id'],x['stage_ref']['blob_id']):x['artifact_id'] for x in promotions}
        def check_pin(owner,field,purpose):
            staged_refs=[s for s in prepared['stage_refs'] if stage(s)['purpose']==purpose]
            reused=[i for i in prepared.get('reused_artifact_ids',[]) if record(i,'artifact')['purpose']==purpose]
            if purpose=='config' and not staged_refs and not reused:
                return  # Existing operation.request pin is checked separately.
            require(len(staged_refs)+len(reused)==1,'attempt_input_pin_inventory')
            expected=reused[0] if reused else promoted.get((staged_refs[0]['command_id'],staged_refs[0]['blob_id']))
            require(expected is not None and owner[field]==expected,'attempt_prepared_'+purpose)
        # Config belongs to Run, including interruption/failure before dispatch.
        # Artifact identity comes from promotion/reuse; repository checks bytes.
        check_pin(run,'config_artifact_id','config')
        if dispatch is None:
            require(not run['attempts'],'attempt_requires_dispatch')
            return
        require(prepared['attempt_id'] is not None and len(run['attempts'])==1,'dispatched_attempt_inventory')
        attempt=run['attempts'][0]
        require(attempt['id']==prepared['attempt_id'],'attempt_prepared_identity')
        require(attempt['transport_attempt']==dispatch['transport_attempt'],'attempt_transport_identity')
        for field,purpose in (('prompt_artifact_id','prompt'),('request_artifact_id','llm_request')):
            check_pin(attempt,field,purpose)
        if capture is not None:
            expected=promoted.get((capture['response']['command_id'],capture['response']['blob_id']))
            require(expected is not None and attempt['response_artifact_id']==expected,'captured_response_preserved')
            for field in ('requested_model','returned_model','provider_response_id','usage','elapsed_ms'):
                require(json_equal(attempt[field],capture[field]),'attempt_capture_'+field)
            require(attempt['status']!='unknown_outcome','captured_outcome_known')
        else:
            require(attempt['response_artifact_id'] is None,'attempt_no_uncaptured_response')
            require(all(attempt[f] is None for f in ('returned_model','provider_response_id','usage')),'attempt_no_uncaptured_metadata')
            require(attempt['status'] in ('transport_failed','unknown_outcome','stale'),'attempt_no_response_status')
    for cmd,op in commands.items():
        req=op['request'];ancestors=lineage(cmd)
        if req['kind']=='recovery':
            require(op['parent_command_id'] is not None and commands[op['parent_command_id']]['session_id']==op['session_id'],'recovery_parent_session')
        if req['kind'] in ('work','apply_answer'):
            require((req['base_model_id'] is None)==(req['base_analysis_set_id'] is None),'operation_base_pair')
            record(req['source_context_id'],'source_context')
            if req['base_model_id']:
                record(req['base_model_id'],'model');require(record(req['base_analysis_set_id'],'analysis_set')['model_id']==req['base_model_id'],'operation_base_set')
            for value,schema,_,_ in walk_schema(req,SCHEMA['$defs']['Operation']['properties']['request']):
                if 'x-record' in schema:
                    record(value,schema['x-record']);require(owners[value]==op['session_id'],'operation_record_session')
        if req['kind']=='apply_answer':
            answer=record(req['answer_id'],'answer');issue=record(answer['issue_id'],'issue')
            require(issue['issue_key']==req['issue_key'] and owners[req['answer_id']]==op['session_id'],'application_answer_lineage')
            if op['parent_command_id']:
                parent=commands[op['parent_command_id']]
                require(parent['request'].get('answer_id')==req['answer_id'],'application_parent_answer')
        ordered=sorted((e for (c,_),e in events.items() if c==cmd),key=lambda e:e['ordinal'])
        require([e['ordinal'] for e in ordered]==list(range(1,len(ordered)+1)),'event_ordinals')
        require(ordered and ordered[0]['kind']=='prepared' and sum(e['kind']=='prepared' for e in ordered)==1,'prepared_first')
        require(sum(e['kind']=='finalized' for e in ordered)<=1,'single_finalization')
        for event in ordered:
            p=event['payload'];kind=event['kind']
            for value,spec,path,name in walk_schema(event,SCHEMA['$defs'][kind+'Event']):
                if 'x-record' in spec:
                    target=records.get(value);expected=spec['x-record']
                    require(target is not None and (expected=='*' or target['type']==expected),'event_typed_record')
                    require(owners[value]==op['session_id'],'event_session')
                if name=='StageRef':
                    stage(value);require(value['command_id'] in ancestors,'stage_command_lineage')
                if name=='EventRef':
                    other=ref(value);require(value['command_id'] in ancestors,'event_command_lineage')
                    if value['command_id']==cmd: require(other['ordinal']<event['ordinal'],'event_points_back')
                    elif req['kind']=='apply_answer': require(other['payload'].get('answer_id')==req['answer_id'],'same_answer_cross_command')
                if name=='SourceRef':
                    # Structural source resolution through archived context in records.
                    contexts=[r['body'] for r in records.values() if r['type']=='source_context' and owners[r['id']]==op['session_id'] and r['body']['snapshot_id']==value['snapshot_id']]
                    require(bool(contexts),'event_source_snapshot')
                    try: resolve_pointer(snapshots[value['snapshot_id']]['input'],value['input_pointer'])
                    except (KeyError,ValueError,IndexError): require(False,'event_source_pointer')
            if 'answer_id' in p:
                require(req['kind']=='apply_answer' and p['answer_id']==req['answer_id'],'event_answer_identity')
            prior=ordered[:int(event['ordinal'])-1]
            require(not any(e['kind']=='finalized' for e in prior) or kind=='log','no_work_after_finalization')
            if kind=='prepared':
                require(all(s['command_id']==cmd for s in p['stage_refs']),'prepared_stage_owner')
                require(len({(s['command_id'],s['blob_id']) for s in p['stage_refs']})==len(p['stage_refs']),'prepared_stage_unique')
                require(all(record(i,'artifact')['purpose'] in ('prompt','config') for i in p.get('reused_artifact_ids',[])),'prepared_reuse_kind')
            elif kind=='dispatch_intent':
                require(ref(p['prepared_event'],'prepared')['command_id']==cmd,'dispatch_prepared')
                require(not any(e['kind'] in ('dispatch_intent','response_received') for e in prior),'one_dispatch_per_command')
            elif kind=='response_received':
                require(any(e['kind']=='dispatch_intent' for e in prior),'capture_after_intent')
                require(not any(e['kind']=='response_received' for e in prior),'one_response_per_command')
                require(stage(p['response'])['purpose']=='llm_response','response_stage_kind')
            elif kind=='finalized':
                run=record(p['run_id'],'run');require(p['run_id']==op['reserved_run_id'] and run['command_id']==cmd,'finalized_reserved_run')
                require(run['base_model_id']==req.get('base_model_id') and run['base_analysis_set_id']==req.get('base_analysis_set_id'),'run_intent_base')
                context=record(run['source_context_id'],'source_context')
                if req['kind']=='start':
                    require(context['store_key']==req['store_key'] and context['s01_run_id']==req['s01_run_id'] and (req['expected_snapshot_id'] is None or context['snapshot_id']==req['expected_snapshot_id']),'start_intent_source')
                else: require(run['source_context_id']==req.get('source_context_id'),'run_intent_source')
                if run['result_model_id']:
                    model=record(run['result_model_id'],'model')
                    require(model['created_by_run_id']==p['run_id'] and model['parent_model_id']==req.get('base_model_id'),'run_created_model')
                    require(run['result_analysis_set_id'] is not None and record(run['result_analysis_set_id'],'analysis_set')['model_id']==run['result_model_id'],'new_model_initial_set')
                require(len({(x['stage_ref']['command_id'],x['stage_ref']['blob_id']) for x in p['promotions']})==len(p['promotions']),'promotion_unique')
                check_attempts(run,prior,p['promotions'])
                if req.get('config_artifact_id') is not None:
                    require(run['config_artifact_id']==req['config_artifact_id'],'run_intent_config')
                if run['status'] in ('rejected','failed','stale','interrupted'):
                    require(run['result_model_id'] is None and run['result_analysis_set_id'] is None,'failed_run_no_publication')
            elif kind=='interpretation_selected':
                if p['interpretation']=='changes_requirements':
                    require(p['proposed_input'] is not None and p['s01_request'] is not None,'requirements_interpretation_payload')
                    require(stage(p['proposed_input'])['purpose']=='requirement_update_input','proposed_input_kind')
                else: require(p['proposed_input'] is None and p['s01_request'] is None and bool(p['existing_source_refs']),'existing_source_interpretation')
            elif kind=='consent_recorded':
                interpretation=ref(p['interpretation_event'],'interpretation_selected')['payload']
                require(interpretation['answer_id']==p['answer_id'],'consent_answer')
                expected=stage(interpretation['proposed_input'])['sha256'] if interpretation['proposed_input'] else None
                require(p['approved_input_sha256']==expected,'consent_exact_input_hash')
            elif kind=='s01_dispatch_intent':
                consent=ref(p['consent_event'],'consent_recorded')['payload'];interpretation=ref(consent['interpretation_event'],'interpretation_selected')['payload']
                require(consent['answer_id']==p['answer_id'] and interpretation['interpretation']=='changes_requirements','dispatch_consent')
                require(p['input_stage_ref']==interpretation['proposed_input'] and p['s01_request']==interpretation['s01_request'],'dispatch_exact_consented_input_request')
                require(not any(e['kind']=='s01_dispatch_intent' for e in prior),'one_s01_dispatch')
            elif kind=='s01_result_observed':
                dispatch=ref(p['dispatch_event'],'s01_dispatch_intent')['payload']
                require(dispatch['s01_run_id']==p['s01_run_id'] and dispatch['answer_id']==p['answer_id'],'observed_run_identity')
                require((p['snapshot_id'] is not None)==(p['lookup_status']=='validated'),'observed_snapshot_status')
            elif kind=='application_applied':
                selected=ref(p['interpretation_event'],'interpretation_selected')['payload']
                require(selected['answer_id']==p['answer_id'],'applied_interpretation_answer')
                change=record(p['change_id'],'change');issue=record(p['resolved_issue_id'],'issue')
                here={'command_id':cmd,'event_id':event['event_id']}
                require(here in change['application_event_refs'] and here in issue['resolution_event_refs'],'applied_backlinks')
                require(issue['status']=='resolved' and p['answer_id'] in issue['answer_ids'] and p['answer_id'] in change['source_record_ids'],'applied_answer_preserved')
                require(change['new_source_context_id']==p['new_source_context_id'],'application_source_binding')
                require(change['base_model_id']==req['base_model_id'] and issue['model_id']==change['new_model_id'],'application_base_model')
                base_set=record(req['base_analysis_set_id'],'analysis_set')
                current=[i for i in base_set['issue_ids'] if record(i,'issue')['issue_key']==req['issue_key']]
                require(len(current)==1,'application_current_issue')
                current_id=current[0];previous=record(current_id,'issue')
                require(previous['status'] in ('open','answered_pending_application'),'application_pending_issue')
                require(issue['issue_key']==req['issue_key'] and issue['supersedes_id']==current_id,'application_issue_successor')
                # Answer may have been recorded against an earlier version of
                # this question; follow explicit immutable lineage, never text.
                original=record(p['answer_id'],'answer')['issue_id'];ancestor=current_id;seen=set()
                while ancestor is not None and ancestor!=original:
                    require(ancestor not in seen,'application_issue_lineage_cycle');seen.add(ancestor)
                    ancestor=record(ancestor,'issue')['supersedes_id']
                require(ancestor==original,'application_answer_current_lineage')
                require(current_id in change['source_record_ids'],'application_issue_change_source')
                if selected['interpretation']=='changes_requirements':
                    require(p['consent_event'] is not None and p['s01_observation_event'] is not None,'application_requires_consent_observation')
                    consent=ref(p['consent_event'],'consent_recorded')['payload'];observed=ref(p['s01_observation_event'],'s01_result_observed')['payload']
                    require(consent['interpretation_event']==p['interpretation_event'] and observed['lookup_status']=='validated','application_validated_observation')
                    context=record(p['new_source_context_id'],'source_context')
                    require(context['s01_run_id']==observed['s01_run_id'] and context['snapshot_id']==observed['snapshot_id'] and change['kind']=='requirements_switch','application_selected_s01_result')
                    dispatch=ref(observed['dispatch_event'],'s01_dispatch_intent')['payload']
                    require(dispatch['consent_event']==p['consent_event'],'application_same_consent_chain')
                else:
                    require(change['kind']=='analysis_edit' and p['s01_observation_event'] is None,'existing_source_application')
                final=next((e for e in ordered if e['kind']=='finalized'),None)
                require(final is not None,'application_atomic_finalization')
                run=record(final['payload']['run_id'],'run')
                require(run['result_model_id']==change['new_model_id'] and run['result_analysis_set_id'] is not None,'application_model_set_atomic')
                result_set=record(run['result_analysis_set_id'],'analysis_set')
                require(result_set['model_id']==change['new_model_id'] and p['resolved_issue_id'] in result_set['issue_ids'],'application_resolved_issue_selected')
            elif kind=='recovery_observed': require(ref(p['related_event'])['payload'].get('answer_id')==p['answer_id'],'recovery_answer_identity')
