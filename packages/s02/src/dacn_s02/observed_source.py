"""A1 pure checks over archived bytes. No submit, resend, or S01 orchestration."""
from hashlib import sha256
from dacn_s01.revision import json_equal
from .codec_boundary import decode
from .errors import require
from .s01_adapter import verify_archive


def check_application_source(payload, request, change, selected, *, records, events,
                             stages, blobs, snapshots):
    def body(i,kind):
        r=records.get(i);require(r is not None and r['type']==kind,'a1_record_type');return r['body']
    def event(ref,kind):
        e=events.get((ref['command_id'],ref['event_id'])) if ref else None
        require(e is not None and e['kind']==kind,'a1_event_type');return e['payload']
    base=body(request['base_model_id'],'model')
    require(body(request['base_analysis_set_id'],'analysis_set')['model_id']==request['base_model_id'],'a1_base_pair')
    require(base['source_context_id']==request['source_context_id']==change['old_source_context_id'],'a1_base_source')
    if selected['interpretation']=='points_to_existing_source':
        require(payload['observed_source_context_id'] is None and payload['s01_observation_event'] is None and
                change['kind']=='analysis_edit' and payload['new_source_context_id']==base['source_context_id'],'a1_existing_source')
        require(all(r['snapshot_id']==body(base['source_context_id'],'source_context')['snapshot_id'] for r in selected['existing_source_refs']),'a1_existing_source_pin')
        return 'analysis_edit'
    require(payload['observed_source_context_id'] is not None,'a1_observed_context_required')
    consent=event(payload['consent_event'],'consent_recorded')
    observation=event(payload['s01_observation_event'],'s01_result_observed')
    dispatch=event(observation['dispatch_event'],'s01_dispatch_intent')
    require(consent['interpretation_event']==payload['interpretation_event'] and dispatch['consent_event']==payload['consent_event'],'a1_consent_chain')
    require(all(x['answer_id']==payload['answer_id'] for x in (selected,consent,observation,dispatch)),'a1_answer_chain')
    require(observation['lookup_status']=='validated','a1_validated_observation')
    observed=body(payload['observed_source_context_id'],'source_context')
    model_context=body(base['source_context_id'],'source_context')
    require(observed['store_key']==model_context['store_key']==dispatch['s01_store_key'],'a1_selected_store')
    require(observed['s01_run_id']==observation['s01_run_id']==dispatch['s01_run_id'],'a1_observed_run')
    require(observed['snapshot_id']==observation['snapshot_id'],'a1_observed_snapshot')
    require(blobs is not None,'a1_archive_bytes_required')
    for context_id in (payload['observed_source_context_id'],base['source_context_id']):
        context=body(context_id,'source_context')
        for field in ('envelope_artifact_id','run_source_artifact_id','origin_source_artifact_id','schema_artifact_id'):
            art=body(context[field],'artifact');raw=blobs.get(context[field])
            require(type(raw) is bytes and sha256(raw).hexdigest()==art['sha256'] and len(raw)==art['byte_length'],'a1_archive_hash')
        snapshot=verify_archive(records[context_id],records,blobs)
        require(json_equal(snapshot,snapshots.get(context['snapshot_id'])),'a1_snapshot_archive_identity')
    env=decode(blobs[observed['envelope_artifact_id']])
    require(env['snapshot']['spec_id']==snapshots[model_context['snapshot_id']]['spec_id'],'a1_spec_identity')
    require(json_equal(env['run']['request'],selected['s01_request']) and json_equal(dispatch['s01_request'],selected['s01_request']),'a1_checked_request')
    require(dispatch['input_stage_ref']==selected['proposed_input'],'a1_full_input_stage')
    staged=stages.get((dispatch['input_stage_ref']['command_id'],dispatch['input_stage_ref']['blob_id']))
    raw=blobs[observed['run_source_artifact_id']]
    require(staged is not None and staged['purpose']=='requirement_update_input' and staged.get('bytes')==raw,'a1_full_input_bytes')
    digest=sha256(raw).hexdigest()
    require(digest==staged['sha256']==consent['approved_input_sha256'],'a1_full_input_hash')
    require(len(raw)==staged['byte_length'],'a1_full_input_length')
    # Same snapshot must have identical archived values; result_kind is irrelevant.
    same=observed['snapshot_id']==model_context['snapshot_id']
    kind='analysis_edit' if same else 'requirements_switch'
    result=base['source_context_id'] if same else payload['observed_source_context_id']
    require(change['kind']==kind and change['new_source_context_id']==result==payload['new_source_context_id'],'a1_snapshot_branch')
    require(body(change['new_model_id'],'model')['source_context_id']==result,'a1_result_model_source')
    return kind


def check_base_pair(request, current_pair):
    """Pre-publication comparison only; P2 must perform the actual atomic CAS."""
    require(tuple(current_pair)==(request['base_model_id'],request['base_analysis_set_id']),'a1_current_base_pair')
