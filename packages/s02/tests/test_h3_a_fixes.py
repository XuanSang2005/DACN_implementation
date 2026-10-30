"""Independent expectations for the three a1 findings; no H3 writer.

Anchor fixture extraction is adapted from the sealed auditor setup (not its
assertions). Original auditor files/replay assertions remain byte-identical.
"""
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import pytest
from dacn_s02.codec_boundary import encode,decode
from dacn_s02.errors import S02Error
from dacn_s02.profiles import E1
from dacn_s02.h3_limits import Budget,DEFAULTS,references,digest
from dacn_s02.h3_contracts import REGISTRY,ANCHOR
from dacn_s02.h3_history import HistoryData,ReviewRegistry,ReviewTrustContext
from dacn_s02.h3_bindings import check_anchor,check_admission,check_config,config_intent
from dacn_s02.h3_policy import admit
from h2_checkpoint_fixtures import ScopedCase
from h3_fixtures import setup,view,selector_rows,bind_work
from test_h3_a_contracts import admission,config

def anchor_fixture(tmp_path):
    case=ScopedCase(tmp_path);case.bootstrap();case.advance(1);first=case.parent
    firstpair=list(case.pair);case.advance(2);second=case.parent
    with case.repo._read() as c:
        records,blobs,commands,events,stages=case.repo._check(c)
        owners={x['id']:x['session_id'] for x in c.execute('SELECT id,session_id FROM records')}
        profiles={x['id']:x['profile_id'] for x in c.execute('SELECT id,profile_id FROM records')}
        ops={x['command_id']:x['profile_id'] for x in c.execute('SELECT command_id,profile_id FROM operations')}
    raw=encode(dict(format=REGISTRY,purpose='synthetic_historical_evidence_only',registry_id='Empty',store_id=case.store_id,required_issue_ids=[],reviews=[]))
    b=Budget();reg=ReviewRegistry.parse(raw,ReviewTrustContext('external.json',sha256(raw).hexdigest(),'Empty',case.store_id),b)
    h=HistoryData(records=records,record_profiles=profiles,owners=owners,commands=commands,operation_profiles=ops,events=events,stages=stages,blobs=blobs,registry=reg,store_id=case.store_id,budget=b)
    v=h.view(commands[second]['session_id'],case.pair,case.pair)
    def plan_for(cmd):
        finals=next(e for (c,_),e in events.items() if c==cmd and e['kind']=='finalized')
        cfg=records[commands[cmd]['reserved_run_id']]['body']['config_artifact_id']
        aid=next(p['artifact_id'] for p in finals['payload']['promotions'] if p['artifact_id']!=cfg and records[p['artifact_id']]['body']['purpose']=='config')
        return aid,decode(blobs[aid])
    aid,p=plan_for(second);oldaid,oldplan=plan_for(first)
    outputs=[]
    for step,cmd in ((1,first),(2,second)):
        entry=p['admission']['progress_by_unit'][case.v]['outputs'][str(step)]
        outputs.append(dict(unit_id=case.v,step=step,origin_command_id=cmd,output_ids=entry['local_ids'],raw_sha256=entry['raw_sha256'],source_refs=entry['source_refs'],aliases=entry['aliases']))
    anchor=dict(version=ANCHOR,command_id=second,plan_artifact_id=aid,plan_sha256=sha256(blobs[aid]).hexdigest(),published_pair=case.pair,
        source_context_id=v.context.source.context_id,snapshot_id=v.context.source.snapshot_id,transitions=[],transition_hashes=[],outputs=outputs)
    return case,v,anchor,(oldaid,oldplan,first,firstpair,p)



@pytest.mark.parametrize('field',['base_pair','from_pair','to_pair','result_pair','published_pair','latest_checked_pair','head'])
def test_each_private_pair_counts_both_uses(field):
    assert references({field:['M','AS']})==2
    assert references({field:None})==0


def test_atomic_refs_and_prose_are_not_extra_id_uses():
    value=dict(base_pair=['M','AS'],source_ref=dict(snapshot_id='S',input_pointer='/title'),
        stage_ref=dict(command_id='C',blob_id='B'),handle=dict(base_handle='A'),
        reason='M AS C B',text='not an ID',aliases={'h':dict(id='A',kind='Action')})
    # Pair 2 + SourceRef 1 + StageRef 1 + handle 1 + alias key/id 2.
    assert references(value)==7


@pytest.mark.parametrize('cap',[3,4,5])
def test_pair_boundary_and_repeated_slots(cap):
    b=Budget(limits=replace(DEFAULTS,refs=cap));raw=encode(dict(base_pair=['M','AS']))
    b.parse(raw,slot='registry');b.parse(raw,slot='registry');assert b.input_refs==2
    if cap<4:
        with pytest.raises(S02Error,match='refs'):b.parse(raw,slot='history')
    else:
        b.parse(raw,slot='history');assert b.input_refs==4
    with pytest.raises(S02Error):b.parse(encode(dict(base_pair=['Different','AS'])),slot='registry')


def test_reference_aggregate_registry_history_config_plan_authority():
    b=Budget(limits=replace(DEFAULTS,refs=9))
    for name in ('registry','history','config','plan'):
        b.parse(encode(dict(base_pair=['M','AS'])),kind='raw' if name=='history' else name,slot=name)
    assert b.input_refs==8
    with pytest.raises(S02Error,match='refs'):b.parse(encode(dict(result_pair=['M','AS'])),kind='authority',slot='authority')


@pytest.mark.parametrize('branch,assessment',[('DIRECT',None),('CARRY','applicable'),('CARRY','undetermined'),('REPLACEMENT','complete'),('REPLACEMENT','incomplete')])
def test_summary_requires_canonical_branch_assessment_and_unique_inventory(foundation,branch,assessment):
    g=setup(foundation)
    if branch=='CARRY':g.carry(assessment)
    if branch=='REPLACEMENT':g.carry('not_applicable','human_review');g.replacement(assessment=='complete')
    v=view(g);q=v.issue('Question2');a=admission(v)
    summary=dict(issue_key='Question2',branch=branch,assessment=assessment,proof_record_id=q['id'],proof_sha256=digest(q),reason_codes=[])
    a['transitions']=[summary];assert check_admission(a,v)==a
    a['transitions']=[{**summary,'reason_codes':['Diagnostic retained']},summary]
    with pytest.raises(S02Error,match='transition_inventory'):check_admission(a,v)
    for field,bad in [('branch','DIRECT' if branch!='DIRECT' else 'CARRY'),('assessment','complete' if assessment!='complete' else None)]:
        a['transitions']=[{**summary,field:bad}]
        with pytest.raises(S02Error):check_admission(a,v)


@pytest.mark.parametrize('step',[2,3])
def test_full_anchor_proves_stage_two_and_only_allows_unfinished_step(tmp_path,step):
    case,v,anchor,extra=anchor_fixture(tmp_path);proof=check_anchor(anchor,v);rows=selector_rows(v)
    assert proof.payload()[case.v]['work_completed_through']==2
    assert proof.payload()[case.v]['assessment_state']=='current'
    tasks=[];state=v.history._state
    for key,origin in extra[-1]['admission']['tasks'].items():
        command=origin['origin_command_id']
        final=next(e for (c,_),e in state['events'].items() if c==command and e['kind']=='finalized')
        cfg=state['records'][state['commands'][command]['reserved_run_id']]['body']['config_artifact_id']
        aid=next(x['artifact_id'] for x in final['payload']['promotions'] if x['artifact_id']!=cfg and state['records'][x['artifact_id']]['body']['purpose']=='config')
        tasks.append({**origin,'issue_key':key,'issue_id':v.issue(key)['id'],'origin_plan_sha256':state['records'][aid]['body']['sha256']})
        row=next(x for x in rows if x['issue_key']==key);row.update(target_step=origin['target_step'],code_task_role=origin['role'])
    a=admission(v);a['progress_by_unit']=proof.payload()
    a['selectors']={row['issue_key']:row for row in rows};a['tasks']={o['issue_key']:o for o in tasks}
    assert check_admission(a,v,progress=proof)==a
    with pytest.raises(S02Error,match='progress_provenance'):check_admission(a,v)
    def pins(b):
        b.update(store_id=v.history.store_id,progress_before_sha256=digest(proof.payload()),anchor_sha256=proof.anchor_sha256)
    w=bind_work(v,rows,step=step,selected=[case.v],binding_change=pins)
    result=admit(v,rows,*w[:4],candidate_raw=w[4],progress=proof,task_origins=tasks)
    if step==2:assert result.allowed_units==() and 'PROGRESS_NOT_CURRENT' in result.reason_codes
    else:assert result.allowed_units==(case.v,) and not result.blocked_units


@pytest.mark.parametrize('mutation',['raw','origin','prefix','duplicate'])
def test_anchor_raw_origin_and_complete_inventory_cannot_be_self_claimed(tmp_path,mutation):
    case,v,a,_=anchor_fixture(tmp_path)
    if mutation=='raw':a['outputs'][0]['raw_sha256']='0'*64
    if mutation=='origin':a['outputs'][0]['origin_command_id']=case.parent
    if mutation=='prefix':a['outputs'].pop()
    if mutation=='duplicate':a['outputs'].append({**a['outputs'][0],'origin_command_id':case.parent})
    with pytest.raises(S02Error):check_anchor(a,v)


def test_config_valid_no_anchor_metadata_is_inspectable_but_cannot_build(foundation):
    v=view(setup(foundation));c=config(v);a=admission(v)
    c.update(mode='step',step=1,goal='build',parent_metadata=a)
    c['inputs']['candidate']=dict(stage_ref=dict(command_id=c['command_id'],blob_id='Candidate'),sha256=digest({}),byte_length=2,media_type='application/json')
    c['authority_binding'].update(operation='step',step=1,goal='build',candidate_sha256=digest({}),candidate_length=2,progress_before_sha256=digest(a['progress_by_unit']))
    c['intent_sha256']=digest(config_intent(c));assert check_config(c,v)==c
    rows=selector_rows(v);w=bind_work(v,rows);result=admit(v,rows,*w[:4],candidate_raw=w[4]);assert result.allowed_units==()
    c['parent_metadata']['progress_by_unit'][next(iter(a['progress_by_unit']))]['assessment_state']='current'
    c['intent_sha256']=digest(config_intent(c))
    with pytest.raises(S02Error):check_config(c,v)


def test_unit_without_domain_output_can_start_step_one(tmp_path,monkeypatch):
    import helpers
    from helpers import Foundation
    original=helpers.source
    def source():
        value=original();value['functional_requirements'].append(dict(id='R2',text='Independent obligation with no existing output',priority=None,acceptance_criteria=[]));return value
    original_model=helpers.model
    def model(*args,**kw):
        value=original_model(*args,**kw);sid=value['body']['actors'][0]['trace']['source_refs'][0]['snapshot_id']
        value['body']['mappings'].append(dict(id='EmptyRow',source_ref=dict(snapshot_id=sid,input_pointer='/functional_requirements/1'),parts=[],assessment='not_assessed',issue_ids=['Q2']))
        for action in value['body']['actions']:action['initiator']='internal'
        return value
    with monkeypatch.context() as patch:
        patch.setattr(helpers,'source',source);patch.setattr(helpers,'model',model)
        f=Foundation(tmp_path);f.initial(True)
    from profile_fixtures import Graph
    from h3_fixtures import e1
    with f.repo._read() as c:records,blobs,commands,events,stages=f.repo._check(c)
    g=e1(Graph(records,dict.fromkeys(records,E1),dict.fromkeys(records,f.session),commands,dict.fromkeys(commands,E1),events,stages,blobs,f.session,f.context,f.config,f.snapshot,model_id='M1',set_id='AS1',current_issue='Q2'))
    v=view(g);uid=next(f.unit_id for f in v.context.source.families if f.pointer=='/functional_requirements/1')
    from dacn_s02.h3_policy import unassessed_progress
    assert unassessed_progress(v)[uid]['actual_output_ids']==[]
    rows=selector_rows(v);w=bind_work(v,rows,selected=[uid]);r=admit(v,rows,*w[:4],candidate_raw=w[4])
    assert r.allowed_units==(uid,) and r.blocked_units==() and r.global_blocked  # R1 is still held


def test_actual_assessment_chain_transport_is_accepted_but_guard_stays_held(tmp_path):
    case,old,anchor,extra=anchor_fixture(tmp_path);base=list(case.pair);baseplan=extra[-1]
    case.advance(3,proof=False)  # existing H2 AS-only guard; no new completed stage
    assert case.pair[0]==base[0] and case.pair[1]!=base[1]
    with case.repo._read() as c:
        records,blobs,commands,events,stages=case.repo._check(c)
        owners={x['id']:x['session_id'] for x in c.execute('SELECT id,session_id FROM records')}
        profiles={x['id']:x['profile_id'] for x in c.execute('SELECT id,profile_id FROM records')}
        ops={x['command_id']:x['profile_id'] for x in c.execute('SELECT command_id,profile_id FROM operations')}
    b=Budget();raw=encode(dict(format=REGISTRY,purpose='synthetic_historical_evidence_only',registry_id='Empty',store_id=case.store_id,required_issue_ids=[],reviews=[]))
    reg=ReviewRegistry.parse(raw,ReviewTrustContext('external.json',sha256(raw).hexdigest(),'Empty',case.store_id),b)
    h=HistoryData(records=records,record_profiles=profiles,owners=owners,commands=commands,operation_profiles=ops,events=events,stages=stages,blobs=blobs,registry=reg,store_id=case.store_id,budget=b)
    v=h.view(old.session_id,case.pair,case.pair)
    final=next(e for (c,_),e in events.items() if c==case.parent and e['kind']=='finalized')
    cfgid=records[commands[case.parent]['reserved_run_id']]['body']['config_artifact_id']
    aid=next(x['artifact_id'] for x in final['payload']['promotions'] if x['artifact_id']!=cfgid and records[x['artifact_id']]['body']['purpose']=='config')
    result=decode(blobs[aid]);assert result['candidate_outcome']=='guard_only'
    from dacn_s02.validation import index_model
    elements,parts=index_model(records[base[0]]);objects={**elements,**parts}
    ids={i for x in anchor['outputs'] for i in x['output_ids']}
    correspondence=[dict(from_id=i,to_id=i,kind='part' if i in parts else 'element',relation='unchanged',from_context_sha256=digest(objects[i]),to_context_sha256=digest(objects[i]),reason='Same immutable Model and IDs') for i in sorted(ids)]
    from dacn_s02.h2_graph import ModelContext,impact
    delta=impact(ModelContext(records[base[0]],v.context.source,b),v.context)
    t=dict(command_id=case.parent,from_pair=base,to_pair=case.pair,source_context_id=v.context.source.context_id,snapshot_id=v.context.source.snapshot_id,
        parent_assessment_sha256=digest(baseplan['admission']['progress_by_unit']),result_assessment_sha256=digest(result['admission']['progress_by_unit']),
        diff_sha256=digest(dict(elements=sorted(delta.changed_elements),parts=sorted(delta.changed_parts),rows=sorted(delta.changed_rows),source_changed=delta.source_changed)),
        closure_sha256=digest(dict(before=delta.before.scope(),after=delta.after.scope())),correspondence=correspondence)
    anchor.update(transitions=[t],transition_hashes=[digest(t)])
    proof=check_anchor(anchor,v).payload()[case.v]
    assert proof['work_completed_through']==2 and proof['assessment_state']=='needs_revalidation'
    assert proof['outputs']==anchor['outputs']
    bad=deepcopy(anchor);bad['transitions'][0]['result_assessment_sha256']='0'*64;bad['transition_hashes']=[digest(bad['transitions'][0])]
    with pytest.raises(S02Error,match='assessment_chain_hashes'):check_anchor(bad,v)


@pytest.mark.parametrize('cap',[7,8,9])
def test_all_remaining_closed_id_uses_and_mixed_ref_boundary(cap):
    value=dict(unresolved_keys=['Q','Q'],store_key='S01',s01_store_key='S01',analysis_key='A',
        edge=dict(id='E',**{'from':'N','to':'N'},guard='N is prose, not a ref',trace=dict(source_refs=[dict(snapshot_id='S',input_pointer='/title')])))
    # Two unresolved-key uses + store/dispatch/analysis keys + two Edge endpoints + SourceRef.
    assert references(value)==8
    assert references(dict(reason='ordinary prose',**{'from':'text','to':'text'}))==0
    b=Budget(limits=replace(DEFAULTS,refs=cap))
    if cap<8:
        with pytest.raises(S02Error,match='refs'):b.inspect(value,input_lane=True,slot='history')
    else:
        b.inspect(value,input_lane=True,slot='history');assert b.input_refs==8
        b.inspect(value,input_lane=True,slot='history');assert b.input_refs==8
