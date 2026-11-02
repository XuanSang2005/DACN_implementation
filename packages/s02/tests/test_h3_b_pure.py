"""G1-G3: projected canonical round trips precede any B writer code."""
from copy import deepcopy
import pytest
from dacn_s02.codec_boundary import encode
from dacn_s02.errors import S02Error
from dacn_s02.h3_limits import Budget,digest
from dacn_s02 import h3_contracts as A
from dacn_s02.h3_checkpoint_contracts import validate,CONFIG,PLAN,POLICY,BINDING,AUTHORITY
from dacn_s02.h3_checkpoint_checks import CheckpointVerifier,dependencies,check_checkpoint_result
from h3_b_fixtures import setup_history,config_for,project,anchor_for,history


@pytest.fixture(scope='module')
def source_case(tmp_path_factory):return setup_history(tmp_path_factory.mktemp('b-pure'))


@pytest.fixture
def base_case(source_case):
    case,original=source_case
    h=history(original.history.payload(),original.history.store_id)
    return case,h.view(original.session_id,original.pair,original.pair)


@pytest.mark.parametrize('marker',['s02-h3-config/0.1.0-draft.2','s02-h3-config/unknown'])
def test_g2_unknown_or_old_publisher_marker_cannot_fall_back_to_generic_history(base_case,marker):
    from dacn_s02.codec_boundary import decode
    from hashlib import sha256
    _,base=base_case;s=base.history.payload();cid=base.parent_command_id;op=s['commands'][cid]
    aid=s['records'][op['reserved_run_id']]['body']['config_artifact_id'];cfg=decode(s['blobs'][aid]);cfg['marker']=marker;raw=encode(cfg)
    s['blobs'][aid]=raw;s['records'][aid]['body'].update(sha256=sha256(raw).hexdigest(),byte_length=len(raw))
    final=next(e for (c,_),e in s['events'].items() if c==cid and e['kind']=='finalized')
    ref=next(p['stage_ref'] for p in final['payload']['promotions'] if p['artifact_id']==aid)
    s['stages'][cid,ref['blob_id']].update(bytes=raw,sha256=sha256(raw).hexdigest(),byte_length=len(raw))
    h=history(s,base.history.store_id);v=h.view(base.session_id,base.pair,base.pair)
    with pytest.raises(S02Error,match='b_publisher_version_unsupported'):CheckpointVerifier(h).selector_seed(v)


@pytest.fixture
def projected(base_case):
    case,base=base_case;cfg,raw=config_for(base);h,b,r,p=project(base,cfg,raw)
    return case,cfg,raw,h,b,r,p


def test_g1_no_anchor_result_publisher_revalidate_round_trip(projected):
    case,cfg,raw,h,base,result,plan=projected
    assert check_checkpoint_result(cfg,plan,base,result)==plan
    verifier=CheckpointVerifier(h);parent=verifier.published(cfg['command_id'])
    assert parent.plan()==plan and parent.config()==cfg
    assert result.context.model()==base.context.model()
    assert [q['id'] for q in result.issues]==[q['id'] for q in base.issues]
    # Handwritten source topology: V has one existing Action, no proven stage;
    # U has a business hold. Neither may get a completed stage from its shape.
    pv=plan['admission']['progress_by_unit'][case.v]
    assert pv['work_completed_through']==0 and pv['outputs']==[]
    model=case.last['result']['model']['body']
    assert pv['actual_output_ids']==sorted([model['actors'][0]['id'],model['actions'][0]['id']])
    assert pv['assessment_state']=='needs_revalidation'
    assert 'PROGRESS_PROOF_REQUIRED' in plan['admission']['full_hold_reasons']
    src=base.context.source;meta=plan['admission']
    assert set(meta['tasks'])==set(case.meta['tasks'])
    for key,old in case.meta['tasks'].items():
        actual=meta['tasks'][key];current=base.issue(key)
        assert actual['issue_id']==current['id'] and actual['issue_key']==key
        assert all(actual[k]==old[k] for k in ('origin_command_id','root_issue_id','unit_ids','target_step','role','predicate'))
        state=base.history._state;origin=actual['origin_command_id'];rr=state['records'][state['commands'][origin]['reserved_run_id']]
        final=next(e for (c,_),e in state['events'].items() if c==origin and e['kind']=='finalized')
        aid=next(p['artifact_id'] for p in final['payload']['promotions'] if p['artifact_id']!=rr['body']['config_artifact_id'] and state['records'][p['artifact_id']]['body']['purpose']=='config')
        assert actual['origin_plan_sha256']==state['records'][aid]['body']['sha256']
        assert meta['selectors'][key]['code_task_role']==old['role'] and meta['selectors'][key]['target_step']==old['target_step']
    independently_unstarted=[p for u,p in meta['progress_by_unit'].items() if not p['actual_output_ids'] and not p['unresolved_keys']]
    assert independently_unstarted and all(p['work_completed_through']==0 and p['outputs']==[] and p['assessment_state']=='current' for p in independently_unstarted)
    expected_source=digest(dict(source_context_id=src.context_id,snapshot_id=src.snapshot_id,archive_sha256=src.archive_sha256,
        obligations=[dict(snapshot_id=src.snapshot_id,input_pointer=p) for p in sorted(src.obligations)]))
    empty=dict(model_id=base.pair[0],element_ids=[],mapping_part_ids=[])
    roles=[]
    for q in result.issues:
        proof=q['body']['resolution_carry'] or q['body']['resolution_replacement']
        roles.append(dict(issue_key=q['body']['issue_key'],predecessor_issue_id=q['body']['supersedes_id'],current_issue_id=q['id'],
            origin_issue_id=proof['origin_issue_id'] if proof else None,obsolete_issue_id=proof.get('obsolete_issue_id') if proof else None,
            replacement_issue_id=proof.get('replacement_issue_id') if proof else None))
    assert meta['issue_roles']==sorted(roles,key=lambda x:x['issue_key']) and meta['transitions']==[]
    expected_proof=digest(dict(history_sha256=digest(cfg['history_binding']),analysis_sha256=cfg['inputs']['analysis']['sha256'],authority_binding_sha256=digest(cfg['authority_binding']),
        historical_reviews_pin=cfg['historical_reviews_pin'],anchor_sha256=None,issue_roles=sorted(roles,key=lambda x:x['issue_key']),transitions=[],full_hold_reasons=meta['full_hold_reasons'],
        stage_inventory={u:dict(work_completed_through=0,outputs=[],actual_output_ids=p['actual_output_ids']) for u,p in sorted(meta['progress_by_unit'].items())}))
    for p in plan['admission']['progress_by_unit'].values():
        assert p['latest_checked_pair']==result.pair and p['assessment'] is not None
        assert p['assessment']['result_pair']==result.pair
        assert p['assessment']['parent_assessment_sha256'] is None
        assert p['assessment']['result_model_sha256']==digest(base.context.model())
        assert p['assessment']['result_analysis_set_sha256']==digest(result.analysis_set)
        assert p['assessment']['diff_sha256']==digest(dict(elements=[],parts=[],rows=[],source_changed=False))
        assert p['assessment']['source_sha256']==expected_source and p['assessment']['context_sha256']==digest(base.context.model())
        assert p['assessment']['closure_sha256']==digest(dict(before=empty,after=empty))
        assert p['assessment']['proof_sha256']==expected_proof
    cfg2,raw2=config_for(result,command='BCommand2',parent=parent)
    h2,b2,r2,p2=project(result,cfg2,raw2,parent)
    verified=CheckpointVerifier(h2).published('BCommand2')
    assert verified.plan()==p2
    for unit,p in p2['admission']['progress_by_unit'].items():
        old=plan['admission']['progress_by_unit'][unit]
        assert p['work_completed_through']==old['work_completed_through']==0
        assert p['outputs']==old['outputs']==[] and p['actual_output_ids']==old['actual_output_ids']
        assert p['assessment']['parent_assessment_sha256']==digest(old['assessment'])
    assert cfg2['parent_metadata']==plan['admission']


def test_g1_full_h2_stage2_provenance_survives_result_assessment(base_case):
    case,base=base_case;anchor=anchor_for(case,base);cfg,raw=config_for(base,command='BAnchored',anchor=anchor)
    h,b,r,p=project(base,cfg,raw);parent=CheckpointVerifier(h).published('BAnchored')
    pv=p['admission']['progress_by_unit'][case.v]
    assert pv['work_completed_through']==2
    assert [row['step'] for row in pv['outputs']]==[1,2]
    assert pv['outputs']==[o for o in anchor['outputs'] if o['unit_id']==case.v]
    assert pv['assessment']['output_refs']==pv['outputs']
    cfg2,raw2=config_for(r,command='BAnchoredAgain',parent=parent)
    h2,_,_,p2=project(r,cfg2,raw2,parent)
    assert CheckpointVerifier(h2).published('BAnchoredAgain').plan()==p2
    assert p2['admission']['progress_by_unit'][case.v]['work_completed_through']==2
    assert p2['admission']['progress_by_unit'][case.v]['outputs']==pv['outputs']


def test_g1_B_anchor_through_AS_transition_uses_B_reader_not_A_projection(base_case):
    from dacn_s02.h3_contracts import ANCHOR
    from dacn_s02.h3_bindings import check_anchor
    case,base=base_case;cfg,raw=config_for(base,command='BTransport1',anchor=anchor_for(case,base));h,_,r1,p1=project(base,cfg,raw)
    parent=CheckpointVerifier(h).published(cfg['command_id']);cfg2,raw2=config_for(r1,command='BTransport2',parent=parent);h2,_,r2,p2=project(r1,cfg2,raw2,parent)
    outputs=deepcopy(p1['admission']['progress_by_unit'][case.v]['outputs']);tracked={i for o in outputs for i in o['output_ids']}|{a['id'] for o in outputs for a in o['aliases'].values()}
    pairs=[]
    for i in sorted(tracked):
        before=r1.context.elements[i];after=r2.context.elements[i]
        pairs.append(dict(from_id=i,to_id=i,kind='element',relation='unchanged',from_context_sha256=digest(before),to_context_sha256=digest(after),reason='Exact retained domain value'))
    empty=dict(model_id=base.pair[0],element_ids=[],mapping_part_ids=[])
    transition=dict(command_id=cfg2['command_id'],from_pair=r1.pair,to_pair=r2.pair,source_context_id=base.context.source.context_id,snapshot_id=base.context.source.snapshot_id,
        parent_assessment_sha256=digest(p1['admission']['progress_by_unit']),result_assessment_sha256=digest(p2['admission']['progress_by_unit']),
        diff_sha256=digest(dict(elements=[],parts=[],rows=[],source_changed=False)),closure_sha256=digest(dict(before=empty,after=empty)),correspondence=pairs)
    anchor=dict(version=ANCHOR,command_id=cfg['command_id'],plan_artifact_id=p1['allocation']['plan_artifact_id'],plan_sha256=digest(p1),published_pair=r1.pair,
        source_context_id=base.context.source.context_id,snapshot_id=base.context.source.snapshot_id,transitions=[transition],transition_hashes=[digest(transition)],outputs=outputs)
    proof=CheckpointVerifier(h2).anchor(anchor,r2)
    assert proof.payload()[case.v]['work_completed_through']==2 and proof.payload()[case.v]['outputs']==outputs
    assert proof.payload()[case.u]['work_completed_through']==0
    with pytest.raises(S02Error):check_anchor(anchor,r2)
    cfg3,raw3=config_for(r2,command='BTransport3',anchor=anchor);h3,_,r3,p3=project(r2,cfg3,raw3)
    assert CheckpointVerifier(h3).published(cfg3['command_id']).plan()==p3
    assert p3['admission']['progress_by_unit'][case.v]['work_completed_through']==2
    for field in ('parent_assessment_sha256','result_assessment_sha256','closure_sha256'):
        bad=deepcopy(anchor);bad['transitions'][0][field]='0'*64;bad['transition_hashes']=[digest(bad['transitions'][0])]
        with pytest.raises(S02Error):CheckpointVerifier(h2).anchor(bad,r2)


@pytest.mark.parametrize('mutation',['assessment_hash','assessment_parent','assessment_null','stage','state','from_pair','branch','output_ids'])
def test_g1_fake_result_metadata_is_rejected_not_accepted_by_shape(projected,mutation):
    case,cfg,raw,h,base,result,p=projected;bad=deepcopy(p);row=bad['admission']['progress_by_unit'][case.v]
    if mutation=='assessment_hash':row['assessment']['result_analysis_set_sha256']='0'*64
    elif mutation=='assessment_parent':row['assessment']['parent_assessment_sha256']='0'*64
    elif mutation=='assessment_null':row.update(assessment=None,latest_checked_pair=None)
    elif mutation=='stage':row['work_completed_through']=1
    elif mutation=='state':row['assessment_state']='current';row['assessment']['state']='current'
    elif mutation=='from_pair':bad['admission']['from_pair']=result.pair
    elif mutation=='branch':bad['admission']['transitions']=[dict(issue_key=result.issues[0]['body']['issue_key'],branch='CARRY',assessment='applicable',proof_record_id=result.issues[0]['id'],proof_sha256=digest(result.issues[0]),reason_codes=[])]
    else:row['actual_output_ids']=[]
    with pytest.raises(S02Error):check_checkpoint_result(cfg,bad,base,result)


def test_g1_mutable_view_indices_and_allocation_clock_are_not_capabilities(projected):
    from dataclasses import replace
    from copy import copy
    _,cfg,_,h,base,result,plan=projected
    fake=replace(base,context=copy(base.context));fake.context.maps=deepcopy(base.context.maps);fake.context.maps['actions']={}
    with pytest.raises(S02Error,match='b_view_context_indices'):check_checkpoint_result(cfg,plan,fake,result)
    bad=deepcopy(plan);bad['allocation']['created_at']='2026-10-31T00:01:00.000Z'
    with pytest.raises(S02Error,match='b_run_times_mode'):check_checkpoint_result(cfg,bad,base,result)


@pytest.mark.parametrize('mutation',['prefix','raw','parent','omitted_unit'])
def test_g1_bad_anchor_or_omitted_unit_does_not_get_progress(base_case,mutation):
    case,base=base_case;anchor=anchor_for(case,base)
    if mutation=='prefix':anchor['outputs']=[o for o in anchor['outputs'] if o['unit_id']!=case.v or o['step']==1]
    elif mutation=='raw':anchor['outputs'][-1]['raw_sha256']='0'*64
    elif mutation=='parent':anchor['published_pair']=[base.pair[0],'WrongSet']
    else:anchor['outputs']=[o for o in anchor['outputs'] if o['unit_id']!=case.v]
    if mutation!='omitted_unit':
        with pytest.raises(S02Error):config_for(base,anchor=anchor)
    else:
        cfg,raw=config_for(base,command='BOmitted',anchor=anchor);_,_,_,p=project(base,cfg,raw)
        row=p['admission']['progress_by_unit'][case.v]
        assert row['work_completed_through']==0 and row['outputs']==[]
        assert row['actual_output_ids'] and row['assessment_state']=='needs_revalidation'


@pytest.mark.parametrize('kind,field,old',[('Config','marker',A.CONFIG),('Plan','marker',A.PLAN),('Config','handler_version',A.HANDLER),('Config','policy_version',A.POLICY),('Binding','version',A.BINDING),('Authority','format',A.AUTHORITY),('Config','goal','retained_output'),('Binding','goal','retained_output')])
def test_g2_old_or_mixed_versions_not_B_approval(projected,kind,field,old):
    _,cfg,_,_,_,_,plan=projected
    values={'Config':cfg,'Plan':plan,'Binding':cfg['authority_binding'],'Authority':dict(format=AUTHORITY,provider_id='BTestController',provider_version='local-synthetic/1',purpose='synthetic_test_only',approvals=[dict(binding=cfg['authority_binding'],decision='allow',reason='Synthetic only')])}
    value=deepcopy(values[kind]);validate(kind,value,Budget());value[field]=old
    with pytest.raises(S02Error):validate(kind,value,Budget())


@pytest.mark.parametrize('step',[1,2,3,4])
def test_g1_retained_goal_requires_actual_requested_stage_not_external_claim(base_case,step):
    case,base=base_case;cfg,raw=config_for(base,command='BGoalBase',anchor=anchor_for(case,base));h,_,result,plan=project(base,cfg,raw)
    parent=CheckpointVerifier(h).published(cfg['command_id']);assert plan['admission']['progress_by_unit'][case.v]['work_completed_through']==2
    kwargs=dict(command='BRetainedGoal',parent=parent,step=step,unit_ids=[case.v],goal='retained_output')
    if step<=2:
        cfg,raw=config_for(result,**kwargs)
        assert CheckpointVerifier(h).config(cfg,result,raw,parent)[0][case.v]['work_completed_through']==2
    else:
        with pytest.raises(S02Error,match='b_retained_stage_proof_required'):config_for(result,**kwargs)


@pytest.mark.parametrize('field',['scope','config_artifact_id'])
def test_g1_own_operation_request_is_exact_not_an_unchecked_scope_claim(projected,field):
    _,cfg,_,h,base,result,plan=projected;op=h._state['commands'][cfg['command_id']];old=deepcopy(op['request'])
    op['request'][field]=dict(model_id=base.pair[0],element_ids=[],mapping_part_ids=[]) if field=='scope' else h._state['records'][h._state['commands'][base.parent_command_id]['reserved_run_id']]['body']['config_artifact_id']
    try:
        with pytest.raises(S02Error,match='b_operation_request'):check_checkpoint_result(cfg,plan,base,result)
    finally:op['request']=old


def test_g3_dependencies_are_frozen_after_own_and_unrelated_append(projected):
    _,cfg,_,h,base,result,plan=projected
    original=encode(cfg['history_binding']);assert dependencies(cfg['history_binding'],base)==cfg['history_binding']
    assert encode(cfg['history_binding'])==original

    assert cfg['command_id'] not in {p['command_id'] for p in cfg['history_binding']['events']}
    assert len(h._state['events'])==len(cfg['history_binding']['events'])+3
    # Own prepare/seal/finalized facts must match exact protocol, not be ignored.
    altered=deepcopy(plan);altered['bindings']['primary_config_stage_ref']['blob_id']='Other'
    with pytest.raises(S02Error):check_checkpoint_result(cfg,altered,base,result)
    # Pinned Record fact edits/missing are refused even if a caller offers its
    # own fresh history hash; canonical graph validation is an additional gate.
    identity=cfg['history_binding']['records'][0]['record_id'];old=h._state['records'][identity]
    try:
        h._state['records'][identity]=deepcopy(old);h._state['records'][identity]['created_at']='2026-10-31T01:00:00.000Z'
        with pytest.raises(S02Error,match='b_dependency_record'):dependencies(cfg['history_binding'],base)
        del h._state['records'][identity]
        with pytest.raises(S02Error,match='b_dependency_record'):dependencies(cfg['history_binding'],base)
    finally:h._state['records'][identity]=old
    assert encode(cfg['history_binding'])==original



def test_g3_full_store_other_session_append_keeps_original_pin(projected):
    from profile_fixtures import Graph
    from h3_fixtures import add_other_session_human_history
    _,cfg,_,h,base,result,plan=projected;s=deepcopy(h._state)
    g=Graph(**s,session=base.session_id,context=base.context.source.context_id,
        config=h._state['records'][h._state['commands'][base.parent_command_id]['reserved_run_id']]['body']['config_artifact_id'],
        snapshot=base.context.source.snapshot_id,model_id=result.pair[0],set_id=result.pair[1])
    add_other_session_human_history(g)
    kw={k:v for k,v in g.kwargs().items() if k!='reviews'}
    extended=history(kw,h.store_id,registry=h.registry)
    v=extended.view(base.session_id,base.pair,base.pair)
    assert len(extended._state['commands'])==2*len(h._state['commands'])
    assert dependencies(cfg['history_binding'],v)==cfg['history_binding']
    assert CheckpointVerifier(extended).published(cfg['command_id']).plan()==plan


def test_g2_exact_b_authority_positive_and_old_approval_rejected(projected):
    from hashlib import sha256
    from dacn_s02.h3_policy import SemanticTrustContext
    from dacn_s02.h3_checkpoint_checks import authorize
    _,cfg,_,_,_,_,_=projected;value=cfg['authority_binding']
    obj=dict(format=AUTHORITY,provider_id='BTestController',provider_version='local-synthetic/1',purpose='synthetic_test_only',approvals=[dict(binding=value,decision='allow',reason='Independent synthetic B control')])
    raw=encode(obj);trust=SemanticTrustContext('BTestController','local-synthetic/1',sha256(raw).hexdigest())
    grant=authorize(raw,trust,value,Budget());assert grant.decision=='allow' and grant.binding_sha256==digest(value)
    obj['approvals'][0]['binding']=deepcopy(value);obj['approvals'][0]['binding']['version']=A.BINDING
    wrong=encode(obj)
    with pytest.raises(S02Error):authorize(wrong,SemanticTrustContext('BTestController','local-synthetic/1',sha256(wrong).hexdigest()),value,Budget())
    obj['approvals']=[];raw=encode(obj)
    assert authorize(raw,SemanticTrustContext('BTestController','local-synthetic/1',sha256(raw).hexdigest()),value,Budget()).decision=='deny'


def test_g1_guard_successor_requires_real_origin_and_keeps_other_issues(tmp_path):
    case,base=setup_history(tmp_path,guard=True)
    cfg,raw=config_for(base,command='BGuardAdopt');h,_,adopted,first=project(base,cfg,raw);parent=CheckpointVerifier(h).published(cfg['command_id'])
    cfg2,raw2=config_for(adopted,command='BGuardRevalidate',parent=parent);h2,b,r,p=project(adopted,cfg2,raw2,parent)
    assert CheckpointVerifier(h2).published(cfg2['command_id']).plan()==p
    keys=set(first['admission']['guards']);assert len(keys)==1
    old={q['body']['issue_key']:q for q in b.issues};new={q['body']['issue_key']:q for q in r.issues}
    for key in old:
        if key in keys:
            assert new[key]['id']!=old[key]['id'] and new[key]['body']['supersedes_id']==old[key]['id']
            assert new[key]['body']['status']=='resolved'
        else:assert new[key]==old[key]
    assert r.context.model()==b.context.model()
