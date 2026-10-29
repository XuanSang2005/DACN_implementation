"""Scoped T0/seal adapters over the unchanged E1 repository and DB2 schema."""
from copy import deepcopy
from dataclasses import asdict
from .codec_boundary import encode, decode
from .errors import require, storage_error, S02Error
from .repository import digest
from .service import staged
from .profiles import E1
from . import store_profiles
from .profile_graph import validate_graph
from .validation import shape, valid_id, time as valid_time
from .h1_store import WorkStore, profile_pins, logical
from .h2_checkpoint import CONFIG, PLAN, HANDLER
from .h2_limits import DEFAULTS, VERSION, need

CONFIG_KEYS=set('profile_id contract_version rules_id source_context_id base_model_id base_analysis_set_id session_id aliases parent_metadata marker config_version handler_version limits_version limits command_id parent_command_id mode step unit_ids goal guard_keys store_id execution_origin binding authority intent inputs reserved_run_id started_at intent_sha256'.split())

PLAN_KEYS={'marker','plan_version','profile_id','contract_version','rules_id','bindings','allocation','batch','promotions','admission','candidate_outcome','diagnostics'}


def integrity(fn):
    def checked(*args,**kwargs):
        try:return fn(*args,**kwargs)
        except S02Error as exc:
            if exc.error['stage']=='persistence':raise
            raise storage_error('Invalid H2 stored metadata; no rebuild: '+exc.error['code']) from exc
        except (KeyError,TypeError,ValueError,StopIteration) as exc:
            raise storage_error('Malformed H2 stored metadata; no rebuild') from exc
    return checked


class ScopeStore(WorkStore):
    def __init__(self, repo, budget):
        super().__init__(repo);self.budget=budget;self.origin_cache={}

    def load(self,command_id):
        from .errors import S02Error
        try:
            with self.repo._read() as c:
                state=self.state(c);cmd=self.repo._command(c,command_id)
                if cmd is None:return None
                cfg,primary,raw=self.primary(cmd,state,execute=cmd['state']!='finalized')
                info=store_profiles.check(c,path=self.repo.path)
                need(info['metadata']['store_id']==cfg['store_id'] and info['metadata']['origin_kind']=='fresh','h2_load_store_identity')
                view=self.context(cmd,state,cfg);view.update(primary=primary,raw=raw)
                view['current_head']=list(c.execute('SELECT head_model_id,head_analysis_set_id FROM sessions WHERE session_id=?',(cfg['session_id'],)).fetchone())
                return view
        except S02Error as exc:
            if exc.error['stage']=='persistence':raise
            raise storage_error('Invalid stored H2 config or identity; no rebuild: '+exc.error['code']) from exc

    @integrity
    def primary(self, cmd, state, *, execute=True):
        need(cmd['operation']['request']['kind']=='work','h2_work_only')
        refs=cmd['events'][0]['payload']['stage_refs']
        stages=[state['stages'][r['command_id'],r['blob_id']] for r in refs]
        primary=[s for s in stages if s['purpose']=='config']
        need(len(primary)==1,'h2_primary_unique');primary=primary[0]
        self.budget.cap('config_bytes',len(primary['bytes']));cfg=decode(primary['bytes'])
        if type(cfg) is not dict or cfg.get('marker')!=CONFIG or cfg.get('config_version')!=CONFIG:
            raise storage_error('Unsupported H2 config; H1 bridge is not supported')
        need(set(cfg)==CONFIG_KEYS,'h2_config_closed')
        need(all(cfg.get(k)==v for k,v in profile_pins().items()),'h2_config_profile')
        need(cfg.get('intent_sha256')==digest(encode(logical(cfg))),'h2_intent_hash')
        op=cmd['operation'];req=op['request']
        need(all(cfg.get(k)==op[k] for k in ('command_id','session_id','parent_command_id','reserved_run_id')),'h2_config_operation')
        need(all(cfg.get(k)==req[k] for k in ('source_context_id','base_model_id','base_analysis_set_id')),'h2_config_base')
        if cfg.get('handler_version')!=HANDLER or cfg.get('limits_version')!=VERSION or cfg.get('limits')!=asdict(DEFAULTS):
            raise storage_error('Unsupported H2 handler/limits; no rebuild')
        raw={}
        for lane in ('candidate','analysis'):
            pin=cfg['inputs'][lane]
            if pin is None:raw[lane]=None;continue
            matches=[s for s in stages if s['blob_id']==pin['blob_id']]
            need(len(matches)==1,'h2_raw_inventory');stage=matches[0]
            need(stage['purpose']=='llm_response' and all(stage[k]==pin[k] for k in ('sha256','byte_length','media_type')),'h2_raw_pin')
            raw[lane]=stage
        need(len(stages)==1+sum(s is not None for s in raw.values()),'h2_stage_inventory')
        return cfg,primary,raw

    def plans(self,cmd,state):
        found=[];primary_ids={r['blob_id'] for r in cmd['events'][0]['payload']['stage_refs']}
        for (owner,bid),stage in state['stages'].items():
            if owner!=cmd['operation']['command_id'] or stage['purpose']!='config' or bid in primary_ids:continue
            self.budget.cap('plan_bytes',len(stage['bytes']));value=decode(stage['bytes'])
            if type(value) is not dict or value.get('marker')!=PLAN:raise storage_error('Unexpected H2 plan stage; no rebuild')
            found.append((value,stage))
        if len(found)>1:raise storage_error('Multiple H2 plans; no winner or repair')
        return found

    def bindings(self,cfg,primary,raw):
        return dict(command_id=cfg['command_id'],session_id=cfg['session_id'],parent_command_id=cfg['parent_command_id'],
                    reserved_run_id=cfg['reserved_run_id'],primary_config_sha256=primary['sha256'],
                    primary_config_stage_ref=dict(command_id=primary['command_id'],blob_id=primary['blob_id']),
                    intent_sha256=cfg['intent_sha256'],base_pair=[cfg['base_model_id'],cfg['base_analysis_set_id']],
                    inputs=cfg['inputs'],authority=cfg['authority'],binding=cfg['binding'],handler_version=HANDLER)

    @integrity
    def checked_plan(self,cmd,state,cfg,primary,raw):
        found=self.plans(cmd,state)
        if not found:return None
        plan,stage=found[0];self.validate_plan(plan,cmd,cfg,primary,raw)
        need(plan['allocation']['plan_blob_id']==stage['blob_id'],'h2_plan_stage_identity')
        self.check_result(plan,state,cfg)
        return plan,stage

    def validate_plan(self,plan,cmd,cfg,primary,raw):
        try:
            need(type(plan) is dict and set(plan)==PLAN_KEYS and plan['marker']==PLAN and plan['plan_version']==PLAN,'h2_plan_envelope')
            need(all(plan[k]==v for k,v in profile_pins().items()),'h2_plan_profile')
            need(encode(plan['bindings'])==encode(self.bindings(cfg,primary,raw)),'h2_plan_bindings')
            a=plan['allocation'];batch=plan['batch']
            need(set(a)=={'plan_blob_id','plan_artifact_id','created_at','aliases'} and valid_id(a['plan_blob_id']) and valid_id(a['plan_artifact_id']) and valid_time(a['created_at']),'h2_allocation')
            need(set(batch)=={'records','artifact_sources','head'} and type(batch['records']) is list,'h2_batch')
            ids=[];runs=[]
            for r in batch['records']:
                self.budget.check();shape(r,profile=E1)
                need(r['type'] in ('run','artifact','issue','model','change','analysis_set'),'h2_record_kind');ids.append(r['id'])
                if r['type']=='run':runs.append(r)
                if r['type']=='issue':need(not r['body']['answer_ids'] and not r['body']['resolution_event_refs'] and r['body']['resolution_carry'] is None and r['body']['resolution_replacement'] is None,'h2_no_a2')
            need(len(ids)==len(set(ids)) and a['plan_artifact_id'] not in ids,'h2_fresh_identity')
            need(len(runs)==1 and runs[0]['id']==cfg['reserved_run_id'] and runs[0]['body']['command_id']==cfg['command_id'] and not runs[0]['body']['attempts'],'h2_run_identity')
            head=batch['head'];need(head is None or type(head) is list and len(head)==2 and all(valid_id(i) for i in head),'h2_head')
            prepared={(r['command_id'],r['blob_id']) for r in cmd['events'][0]['payload']['stage_refs']}
            refs=[]
            for entry in batch['artifact_sources']:
                need(set(entry)=={'artifact_id','stage_ref'},'h2_artifact_source');shape(entry['stage_ref'],'StageRef',profile=E1)
                refs.append((entry['stage_ref']['command_id'],entry['stage_ref']['blob_id']))
            need(len(refs)==len(set(refs)) and set(refs)==prepared,'h2_promoted_inputs')
            expected=deepcopy(batch['artifact_sources'])+[dict(artifact_id=a['plan_artifact_id'],stage_ref=dict(command_id=cfg['command_id'],blob_id=a['plan_blob_id']))]
            need(plan['promotions']==expected,'h2_promotions')
            need(plan['candidate_outcome'] in ('valid','blocked','rejected','guard_only','revalidated'),'h2_outcome')
            if head:
                meta=plan['admission'];need(meta['result_pair']==head,'h2_result_pair')
                sets=[r for r in batch['records'] if r['type']=='analysis_set']
                need(len(sets)==1 and sets[0]['id']==head[1] and sets[0]['body']['model_id']==head[0],'h2_result_as')
                need(set(meta['selectors'])=={r['body']['issue_key'] for r in batch['records'] if r['type']=='issue'} | set(meta['unchanged_issue_keys']),'h2_result_keys')
                self.budget.inspect(meta)
                for progress in meta['progress_by_unit'].values():
                    need(progress['latest_checked_pair']==head,'h2_progress_pair')
                    if progress['assessment_state']=='needs_revalidation':need(bool(progress['guard_keys']),'h2_progress_guard')
                    assessment=progress['assessment']
                    need(assessment['result_pair']==head and assessment['result_analysis_set_sha256']==digest(encode(sets[0])),'h2_assessment_as')
            else:need(not plan['admission'],'h2_rejection_no_progress')
            self.budget.serialized(plan,'plan')
        except (KeyError,TypeError,ValueError) as exc:raise storage_error('Malformed H2 plan; no rebuild') from exc

    @integrity
    def published_plan(self,cmd,state):
        need(cmd['state']=='finalized','h2_finalized_publisher')
        cfg,primary,raw=self.primary(cmd,state,execute=False)
        event=next(e for e in cmd['events'] if e['kind']=='finalized')
        promoted=[p for p in event['payload']['promotions'] if p['artifact_id']!=cmd['run']['body']['config_artifact_id'] and state['records'][p['artifact_id']]['body']['purpose']=='config']
        need(len(promoted)==1,'h2_unique_promoted_plan')
        promotion=promoted[0];ref=promotion['stage_ref'];stage=state['stages'][ref['command_id'],ref['blob_id']]
        self.budget.cap('plan_bytes',len(stage['bytes']));plan=decode(stage['bytes'])
        self.validate_plan(plan,cmd,cfg,primary,raw);self.check_result(plan,state,cfg)
        need(plan['allocation']['plan_blob_id']==stage['blob_id'] and plan['allocation']['plan_artifact_id']==promotion['artifact_id'],'h2_finalized_plan_identity')
        need(event['payload']['promotions']==plan['promotions'],'h2_finalized_promotions')
        aid=plan['allocation']['plan_artifact_id']
        need(state['blobs'].get(aid)==stage['bytes'],'h2_promoted_plan_bytes')
        run=cmd['run'];head=plan['batch']['head']
        if run['body']['status'] in ('completed','blocked'):
            need(head is not None and [run['body']['result_model_id'] or run['body']['base_model_id'],run['body']['result_analysis_set_id']]==head,'h2_actual_pair')
            for r in plan['batch']['records']:need(state['records'].get(r['id'])==r,'h2_actual_records')
        return plan

    def parent(self,c,state,parent,mode):
        cmd=self.repo._command(c,parent)
        need(cmd is not None and cmd['state']=='finalized' and state['operation_profiles'][parent]==E1,'h2_parent_finalized')
        run=cmd['run']['body'];session=cmd['operation']['session_id']
        if mode=='bootstrap':
            need(cmd['operation']['request']['kind']=='start' and run['status']=='completed','h2_intake_entry')
            pair=[None,None];meta=None;aliases={}
        else:
            plan=self.published_plan(cmd,state)
            need(run['status'] in ('completed','blocked') and plan['batch']['head'] is not None,'h2_parent_publication')
            pair=plan['batch']['head'];meta=deepcopy(plan['admission']);aliases=deepcopy(plan['allocation']['aliases'])
            publishers=[]
            for cid,op in state['commands'].items():
                if op['session_id']!=session:continue
                other=self.repo._command(c,cid)
                if other['state']=='finalized' and other['run']['body']['result_analysis_set_id']==pair[1]:publishers.append(cid)
            need(publishers==[parent],'h2_unique_as_publisher')
        cfg=dict(source_context_id=run['source_context_id'],base_model_id=pair[0],base_analysis_set_id=pair[1],session_id=session,aliases=aliases,parent_metadata=meta)
        view=self.context(dict(operation=cmd['operation']),state,cfg)
        view.update(parent_command=cmd)
        return view

    def preflight(self,parent,mode,expected_pair):
        with self.repo._read() as c:
            state=self.state(c);info=store_profiles.check(c,path=self.repo.path)
            need(info['metadata']['origin_kind']=='fresh','h2_fresh_only')
            view=self.parent(c,state,parent,mode)
            cfg=view['config'];pair=[cfg['base_model_id'],cfg['base_analysis_set_id']]
            need(pair==expected_pair,'h2_expected_pair')
            head=list(c.execute('SELECT head_model_id,head_analysis_set_id FROM sessions WHERE session_id=?',(cfg['session_id'],)).fetchone())
            need(head==pair,'h2_parent_current')
            view['store_id']=info['metadata']['store_id']
            return view

    def prepare(self,config,raws):
        command_id=config['command_id'];expected=deepcopy(config)
        def work(c):
            state=self.state(c);info=store_profiles.check(c,path=self.repo.path,writable=True)
            need(info['metadata']['origin_kind']=='fresh' and info['metadata']['store_id']==config['store_id'],'h2_store_binding')
            current=self.repo._command(c,command_id)
            if current:
                old,_,oldraw=self.primary(current,state)
                # Blob allocations are reserved by the winning T0, not a losing preparer.
                def intent(v):return {k:x for k,x in logical(v).items() if k!='inputs'}
                need(intent(old)==intent(config),'h2_prepare_intent_conflict')
                need(all((oldraw[k]['bytes'] if oldraw[k] else None)==raws[k] for k in raws),'h2_prepare_raw_conflict')
                return current
            parent=self.parent(c,state,config['parent_command_id'],config['mode'])
            need(parent['config']['parent_metadata']==config['parent_metadata'] and parent['config']['aliases']==config['aliases'],'h2_prepare_parent_correspondence')
            head=list(c.execute('SELECT head_model_id,head_analysis_set_id FROM sessions WHERE session_id=?',(config['session_id'],)).fetchone())
            need(head==[config['base_model_id'],config['base_analysis_set_id']],'h2_prepare_stale')
            fresh=self.fresh(state);cfg=deepcopy(config);cfg.update(reserved_run_id=fresh(),started_at=self.repo._clock())
            stages=[];cfg['inputs']={}
            for lane,raw in raws.items():
                if raw is None:cfg['inputs'][lane]=None;continue
                stage=staged(command_id,fresh(),'llm_response',raw);stages.append(stage)
                cfg['inputs'][lane]={k:stage[0][k] for k in ('blob_id','sha256','byte_length','media_type')}
            cfg['intent_sha256']=digest(encode(logical(cfg)))
            primary=staged(command_id,fresh(),'config',self.budget.serialized(cfg,'config'));stages.insert(0,primary)
            request=dict(kind='work',source_context_id=cfg['source_context_id'],base_model_id=cfg['base_model_id'],base_analysis_set_id=cfg['base_analysis_set_id'],scope=None,config_artifact_id=None)
            c.execute('INSERT INTO operations VALUES (?,?,?,?,?,?,?)',(command_id,cfg['session_id'],cfg['parent_command_id'],cfg['reserved_run_id'],encode(request).decode('ascii'),digest(encode(request)),E1))
            self.repo._put_stages(c,command_id,stages)
            self.repo._put_event(c,self.repo._event(c,command_id,'prepared',dict(stage_refs=[dict(command_id=command_id,blob_id=s['blob_id']) for s,_ in stages],attempt_id=None)))
            return self.repo._command(c,command_id)
        def probe():
            view=self.load(command_id)
            if view is None:return None
            old=view['config']
            need(all(old[k]==v for k,v in expected.items() if k!='inputs'),'h2_prepare_probe_intent')
            need(all((view['raw'][k]['bytes'] if view['raw'][k] else None)==raws[k] for k in raws),'h2_prepare_probe_raw')
            return view['command']
        return self.repo._write(work,probe)

    def seal(self,command_id,plan):
        planraw=encode(plan);self.budget.cap('plan_bytes',len(planraw))
        def work(c):
            state=self.state(c);cmd=self.repo._command(c,command_id);require(cmd is not None,'h2_prepared_command')
            if cmd['state']=='finalized':return dict(finalized=cmd['run'])
            config,primary,raw=self.primary(cmd,state)
            existing=self.checked_plan(cmd,state,config,primary,raw)
            if existing:return dict(plan=existing[0],stage=existing[1])
            self.validate_plan(plan,cmd,config,primary,raw)
            self.check_result(plan,state,config)
            require(set(plan)==PLAN_KEYS and plan['marker']==PLAN and plan['plan_version']==PLAN,'h2_plan_envelope')
            require(all(plan[k]==v for k,v in profile_pins().items()),'h2_plan_profile')
            require(encode(plan['bindings'])==encode(self.bindings(config,primary,raw)),'h2_plan_bindings')
            bid=plan['allocation']['plan_blob_id'];stage=staged(command_id,bid,'config',planraw)
            self.repo._put_stages(c,command_id,[stage])
            self.repo._put_event(c,self.repo._event(c,command_id,'log',dict(message='H2 immutable work plan sealed')))
            # Detached whole-graph preflight includes the exact promoted plan.
            state=self.state(c);records,blobs=self.materialize(plan,planraw,state)
            run=next(r for r in records if r['id']==cmd['operation']['reserved_run_id'])
            conflict=self.repo._base_error(c,cmd['operation'])
            if conflict:
                records=[r for r in records if r['type'] in ('run','artifact')]
                run['body'].update(status='stale',result_model_id=None,result_analysis_set_id=None,errors=[conflict.error])
            require(not (set(r['id'] for r in records)&state['records'].keys()),'h2_plan_fresh_records')
            for r in records:
                state['records'][r['id']]=r;state['owners'][r['id']]=config['session_id'];state['record_profiles'][r['id']]=E1
            state['blobs'].update(blobs)
            projection=self.repo._event(c,command_id,'finalized',dict(run_id=run['id'],promotions=plan['promotions']))
            state['events'][command_id,projection['event_id']]=projection
            validate_graph(**state,reviews=self.repo._reviews)
            return dict(plan=plan,stage={**stage[0],'bytes':planraw})
        def probe():
            view=self.load(command_id)
            if view['command']['state']=='finalized':return dict(finalized=view['command']['run'])
            found=self.checked_plan(view['command'],view['state'],view['config'],view['primary'],view['raw'])
            return dict(plan=found[0],stage=found[1]) if found else None
        return self.repo._write(work,probe)

    def check_result(self,plan,state,cfg):
        """Verify persisted result correspondence without allocating/rebuilding."""
        if plan['batch']['head'] is None:return
        from .h2_checkpoint import source_inventory
        from .h2_contracts import SourceInventory
        from .h2_limits import digest as value_hash
        from .s01_adapter import verify_archive
        from .h2_graph import ModelContext
        records={**state['records'],**{r['id']:r for r in plan['batch']['records']}}
        model=records[plan['batch']['head'][0]];aset=records[plan['batch']['head'][1]]
        issues=[records[i] for i in aset['body']['issue_ids']];meta=plan['admission']
        context=records[cfg['source_context_id']];snapshot=verify_archive(context,state['records'],state['blobs'])
        source=SourceInventory(snapshot,context['id'],records[context['body']['envelope_artifact_id']]['body']['sha256'],self.budget)
        ctx=ModelContext(model,source,self.budget)
        need(set(meta['progress_by_unit'])==set(source.units),'h2_progress_inventory')
        need(meta['obligations']==[dict(source_ref=r['source_ref'],mapping_row_id=r['id'],assessment=r['assessment'],mapping_part_ids=[p['id'] for p in r['parts']],issue_ids=r['issue_ids']) for r in model['body']['mappings']],'h2_obligation_correspondence')
        need(set(meta['selectors'])=={q['body']['issue_key'] for q in issues},'h2_selector_keys')
        for q in issues:
            s=meta['selectors'][q['body']['issue_key']]
            need(s['issue_id']==q['id'] and set(q['body']['blocking']['element_ids'])<=set(s['element_ids']) and set(q['body']['blocking']['mapping_part_ids'])<=set(s['mapping_part_ids']),'h2_selector_result')
        parent=cfg['parent_metadata']
        need(meta['parent_progress_sha256']==(value_hash(parent['progress_by_unit']) if parent else None),'h2_parent_progress_hash')
        from .h2_checkpoint import selectors,blocking_keys
        blockers=blocking_keys(ctx,issues,selectors(meta,issues,source,self.budget,derived=True),source.units)
        for unit,p in meta['progress_by_unit'].items():
            assessment=p['assessment'];prior=parent['progress_by_unit'][unit] if parent else None
            expected=int(prior['work_completed_through']) if prior else 0
            if cfg['mode']=='step' and plan['candidate_outcome']=='valid' and unit in cfg['unit_ids']:expected=int(cfg['step'])
            need(p['work_completed_through']==expected and set(p['outputs'])=={str(i) for i in range(1,expected+1)},'h2_completed_correspondence')
            need(assessment['result_model_sha256']==value_hash(model) and assessment['result_analysis_set_sha256']==value_hash(aset),'h2_result_hashes')
            need(assessment['parent_assessment_sha256']==(value_hash(prior['assessment']) if prior and prior['assessment'] else None),'h2_assessment_chain')
            need(assessment['output_refs']==p['outputs'] and assessment['state']==p['assessment_state'],'h2_assessment_outputs')
            need(p['unresolved_keys']==blockers[unit],'h2_progress_physical_blockers')
            if cfg['mode']=='step' and int(cfg['step'])>1 and plan['candidate_outcome']=='valid' and unit in cfg['unit_ids']:
                need(not (set(blockers[unit])-set(meta['tasks'])),'h2_completed_output_not_blocked')
            if prior:
                need(all(p['outputs'].get(k)==v for k,v in prior['outputs'].items()),'h2_retained_output_immutable')
            for key in p['guard_keys']:
                need(key in meta['guards'] and any(q['body']['issue_key']==key and q['body']['status']=='open' for q in issues),'h2_progress_current_guard')
        if cfg['mode']=='revalidate' or plan['candidate_outcome']=='guard_only':
            need(not any(r['type'] in ('model','change') for r in plan['batch']['records']),'h2_as_only')
            previous={q['body']['issue_key']:q for q in (state['records'][i] for i in state['records'][cfg['base_analysis_set_id']]['body']['issue_ids'])}
            selected={q['body']['issue_key']:q for q in issues}
            need(previous.keys()<=selected.keys(),'h2_as_keeps_all_keys')
            for key,q in previous.items():
                if cfg['mode']!='revalidate' or key not in cfg['guard_keys']:
                    need(selected[key]==q,'h2_as_only_non_guard_immutable')
                else:
                    current=selected[key]
                    need(current['body']['supersedes_id']==q['id'] and current['id']!=q['id'],'h2_guard_successor')
                    need(current['body']['status']==('resolved' if meta['policy']['predicate_passed'] else 'open'),'h2_guard_predicate_transition')
            if cfg['mode']=='revalidate':need(selected.keys()==previous.keys(),'h2_revalidate_no_new_key')

        if cfg['mode']=='step' and plan['candidate_outcome']=='valid':
            from .h2_checkpoint import normalized_model
            old_model=state['records'][cfg['base_model_id']]
            old_issues=[state['records'][i] for i in state['records'][cfg['base_analysis_set_id']]['body']['issue_ids']]
            old=normalized_model(old_model,old_issues);new=normalized_model(model,issues)
            from .validation import COLLECTIONS
            for collection in COLLECTIONS:
                indexed={e['id']:e for e in new[collection]}
                need(all(indexed.get(e['id'])==e for e in old[collection]),'h2_existing_domain_immutable')
            old_rows={r['id']:r for r in old['mappings']};new_rows={r['id']:r for r in new['mappings']}
            need(old_rows.keys()==new_rows.keys(),'h2_mapping_row_inventory')
            allowed=source.selected(cfg['unit_ids']) if int(cfg['step'])==4 else set()
            for identity,row in old_rows.items():
                after=new_rows[identity]
                need(row['source_ref']==after['source_ref'],'h2_row_source_immutable')
                if row['source_ref']['input_pointer'] not in allowed or row['assessment']!='not_assessed' or row['parts']:
                    need(row==after,'h2_retained_mapping_immutable')
            self.check_projection(plan,state,cfg,model,issues,snapshot,source)

    def check_projection(self,plan,state,cfg,model,issues,snapshot,source):
        from .h2_candidates import parse_candidate,scope_request_hash
        from .h2_graph import ModelContext
        from .h1_candidates import Linker,KINDS
        from .h2_limits import digest as value_hash
        pin=cfg['inputs']['candidate'];raw=state['stages'][cfg['command_id'],pin['blob_id']]['bytes']
        base=state['records'][cfg['base_model_id']];aset=state['records'][cfg['base_analysis_set_id']]
        from .h2_candidates import schema
        from .validation import Validator,FORMATS
        self.budget.cap('raw_bytes',len(raw));value=decode(raw);self.budget.inspect(value)
        need(next(Validator(schema(int(cfg['step'])),format_checker=FORMATS).iter_errors(value),None) is None,'h2_projection_schema')
        need(value['scope_request_sha256']==scope_request_hash(cfg['binding']) and set(value['unit_ids'])==set(cfg['unit_ids']),'h2_projection_scope')
        projection=plan['admission']['projection'];need(projection is not None and projection['candidate_sha256']==digest(raw),'h2_projection_pin')
        bindings=projection['local_bindings']
        # Linker allocation order is fixed by closed projection, never by DB time.
        handles=[]
        for k in KINDS:
            for e in value['proposals'].get(k,[]):
                handles.append(e['handle'])
                if k=='workflows':handles.extend(x['handle'] for field in ('nodes','edges') for x in e[field])
        handles.extend(p['handle'] for r in value['proposals'].get('mappings',[]) for p in r['parts'])
        handles.extend(f['handle'] for f in value['proposals']['findings'])
        need(set(handles)==set(bindings),'h2_projection_allocations')
        ids=iter(bindings[h]['id'] for h in handles)
        linker=Linker(value,cfg['aliases'],snapshot,lambda:next(ids))
        need(linker.local==bindings,'h2_projection_types')
        current={q['body']['issue_key']:q for q in issues}
        remap={i:current[state['records'][i]['body']['issue_key']]['id'] for i in aset['body']['issue_ids']}
        def expected_refs(v):
            if isinstance(v,list):return [expected_refs(x) for x in v]
            if isinstance(v,dict):return {k:[remap.get(i,i) for i in x] if k=='issue_ids' else expected_refs(x) for k,x in v.items()}
            return v
        for k in KINDS:
            actual={e['id']:e for e in model['body'][k]}
            for proposed in value['proposals'].get(k,[]):
                expected=linker.convert(proposed)
                if k=='actors':expected['kind']='candidate'
                if k=='actions' and expected['initiator']=='unknown':expected['state']='needs_clarification'
                need(expected['id'] in actual and expected_refs(expected)==actual[expected['id']],'h2_raw_entity_fidelity')
        rows={r['source_ref']['input_pointer']:r for r in model['body']['mappings']}
        for row in value['proposals'].get('mappings',[]):
            expected=linker.convert(row);actual=rows[row['source_ref']['input_pointer']]
            need(expected_refs(expected)=={k:v for k,v in actual.items() if k!='id'},'h2_raw_mapping_fidelity')
        for f in value['proposals']['findings']:
            q=next((q for q in issues if q['id']==bindings[f['handle']]['id']),None)
            need(q is not None and all(q['body'][k]==f[k] for k in ('question','reason','kind')) and q['body']['trace']==expected_refs(linker.convert(f['trace'])),'h2_raw_finding_fidelity')
