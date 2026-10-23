"""Pure, explicit-profile graph verification for P1 fixtures and future P2.

No database connection or publication API. This does not implement claims,
atomic CAS, storage profile allocation, migration, activation, or E1 writes.
"""
from hashlib import sha256
from dacn_s01.revision import json_equal
from .errors import require
from .profiles import get_profile
from .validation import shape,fields,validate_record,COLLECTIONS
from .events import validate_operations
from .s01_adapter import verify_archive


def validate_graph(*, records, record_profiles, owners, commands, operation_profiles,
                   events, stages, blobs, reviews=None):
    require(set(records)==set(record_profiles)==set(owners),'graph_owner_inventory')
    require(set(commands)==set(operation_profiles),'graph_operation_profiles')
    # Identity is independent of profile and of whether a Run is finalized.
    reserved=set()
    for identity,op in commands.items():
        require(type(op) is dict and identity==op.get('command_id'),'graph_operation_identity')
        run_id=op.get('reserved_run_id')
        require(type(run_id) is str and bool(run_id),'graph_reserved_run_identity')
        require(run_id not in reserved,'graph_reserved_run_unique');reserved.add(run_id)
    profiles={i:get_profile(p).profile_id for i,p in record_profiles.items()}
    op_profiles={i:get_profile(p).profile_id for i,p in operation_profiles.items()}
    for identity,r in records.items():
        shape(r,profile=profiles[identity]);require(identity==r['id'],'graph_record_identity')
        for value,spec,_,_ in fields(r,profile=profiles[identity]):
            if 'x-record' in spec:
                require(value in records and owners[value]==owners[identity],'graph_record_session')
    require(set(blobs)=={i for i,r in records.items() if r['type']=='artifact'},'graph_artifact_inventory')
    for identity,raw in blobs.items():
        b=records[identity]['body']
        require(type(raw) is bytes and b['sha256']==sha256(raw).hexdigest() and b['byte_length']==len(raw),'graph_artifact_hash')
    for (cmd,bid),s in stages.items():
        require(cmd in commands and type(s.get('bytes')) is bytes and sha256(s['bytes']).hexdigest()==s['sha256'] and len(s['bytes'])==s['byte_length'],'graph_stage_hash')
    snapshots={};specs={}
    for i,r in records.items():
        if r['type']=='source_context':
            snap=verify_archive(r,records,blobs);sid=snap['snapshot_id']
            require(sid not in snapshots or json_equal(snapshots[sid],snap),'graph_snapshot_identity')
            snapshots[sid]=snap
            session=owners[i];spec=snap['spec_id'];store=r['body']['store_key']
            require(session not in specs or specs[session]==(spec,store),'graph_session_source');specs[session]=(spec,store)
    # Shape all targets before following any nested graph refs.
    for i,r in records.items():
        same={k:v for k,v in records.items() if owners[k]==owners[i]}
        same_commands={k:v for k,v in commands.items() if v['session_id']==owners[i]}
        validate_record(r,same,snapshots,events=events,stages=stages,commands=same_commands,
                        owner_profile=profiles[i],profile_map={k:profiles[k] for k in same},reviews=reviews)
    validate_operations(commands,events,stages,records,owners,snapshots,
                        operation_profile_map=op_profiles,record_profile_map=profiles,blobs=blobs)
    # SQL uniqueness remains in DB1 unchanged; check equivalent graph facts here.
    applied=set();finalized=set();published=set()
    for (cmd,_),e in events.items():
        require(cmd in commands,'graph_event_operation')
        if e['kind']=='application_applied':
            answer=e['payload']['answer_id'];require(answer not in applied,'graph_unique_application');applied.add(answer)
        if e['kind']=='finalized':
            r=records[e['payload']['run_id']];b=r['body']
            require(r['id'] not in finalized and owners[r['id']]==commands[cmd]['session_id'],'graph_run_owner');finalized.add(r['id'])
            created=[r['id']]
            if b['result_model_id']:
                m=records[b['result_model_id']];created.append(m['id'])
                if m['body']['change_id']:created.append(m['body']['change_id'])
            sid=b['result_analysis_set_id']
            if sid:created.extend([sid,*records[sid]['body']['changed_record_ids']])
            created.extend(p['artifact_id'] for p in e['payload']['promotions'])
            require(all(profiles[i]==op_profiles[cmd] for i in created),'graph_publication_profile')
            if sid:
                require(sid not in published,'graph_set_publication_unique');published.add(sid)
                result=records[sid]['body'];baseid=b['base_analysis_set_id']
                if baseid:
                    base=records[baseid]['body']
                    for field,key in (('issue_ids','issue_key'),('scenario_ids','analysis_key'),('characteristic_ids','analysis_key')):
                        old={records[i]['body'][key]:i for i in base[field]}
                        new={records[i]['body'][key]:i for i in result[field]}
                        require(old.keys()<=new.keys(),'graph_current_keys_preserved')
                        for k,oldid in old.items():require(new[k]==oldid or records[new[k]]['body']['supersedes_id']==oldid,'graph_current_lineage')
                if b['result_model_id'] is None:require(baseid is not None and result['parent_set_id']==baseid,'graph_set_base')
            for promotion in e['payload']['promotions']:
                ref=promotion['stage_ref'];stage=stages[ref['command_id'],ref['blob_id']];aid=promotion['artifact_id'];art=records[aid]['body']
                require(stage['bytes']==blobs[aid] and stage['purpose']==art['purpose'] and stage['media_type']==art['media_type'] and art['producer_run_id']==r['id'],'graph_promotion_exact')
    require(finalized=={i for i,r in records.items() if r['type']=='run'},'graph_finalized_run_inventory')
    require(published=={i for i,r in records.items() if r['type']=='analysis_set'},'graph_published_set_inventory')
    for session in set(owners.values()):
        kinds={};revisions=set();parents=set()
        models=[r for i,r in records.items() if r['type']=='model' and owners[i]==session]
        for m in sorted(models,key=lambda r:r['body']['revision']):
            b=m['body'];require(b['revision'] not in revisions and b['parent_model_id'] not in parents,'graph_model_linearity')
            revisions.add(b['revision']);parents.add(b['parent_model_id'])
            for k in COLLECTIONS:
                for e in b[k]:require(e['id'] not in kinds or kinds[e['id']]==k,'logical_id_kind_stable');kinds[e['id']]=k
        require(revisions==set(range(1,len(models)+1)),'graph_model_revisions')
    for mid,model in records.items():
        if model['type']!='model':continue
        sets=[r for r in records.values() if r['type']=='analysis_set' and r['body']['model_id']==mid]
        revisions=[r['body']['revision'] for r in sets]
        parents=[r['body']['parent_set_id'] for r in sets]
        require(len(revisions)==len(set(revisions)) and len(parents)==len(set(parents)) and
                set(revisions)==set(range(1,len(sets)+1)),'graph_set_linearity')
        require(bool(sets),'graph_model_initial_set')
        for successor in records.values():
            if successor['type']=='model' and successor['body']['parent_model_id']==mid:
                run=records[successor['body']['created_by_run_id']]['body']
                latest=max(sets,key=lambda r:r['body']['revision'])
                require(run['base_analysis_set_id']==latest['id'],'graph_model_switch_final_base_set')
    # The caller gets no acceptance, CAS, or persistence token from this result.
    return snapshots
