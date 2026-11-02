"""G-C1..4 installed-wheel detached controls. No C writer is imported or used."""
from copy import deepcopy
from hashlib import sha256
import pytest
from dacn_s02.codec_boundary import encode
from dacn_s02.errors import S02Error
from dacn_s02.h3_limits import Budget,digest
from dacn_s02 import h3_continuation_contracts as C
from dacn_s02.h3_continuation_checks import ContinuationVerifier
from dacn_s02.h3_continuation_inputs import authorize
from dacn_s02.h3_policy import SemanticTrustContext
from h3_c_fixtures import b_parent,request,projected,units


@pytest.fixture
def direct(tmp_path,monkeypatch):return b_parent(tmp_path,monkeypatch)[2]


def test_G_C1_schema_parent_bridge_and_exact_C_authority(direct):
    cfg,raw=request(direct);C.validate('Config',cfg,Budget())
    assert cfg['parent_metadata']['marker']=='s02-h3-admission/0.1.0-draft.3'
    assert cfg['parent_metadata']==ContinuationVerifier(direct.history).published(direct.parent_command_id).plan()['admission']
    control=encode(dict(format=C.AUTHORITY,provider_id='CTestController',provider_version='local-synthetic/1',purpose='synthetic_test_only',approvals=[dict(binding=cfg['authority_binding'],decision='allow',reason='Explicit synthetic controller')]))
    trust=SemanticTrustContext('CTestController','local-synthetic/1',sha256(control).hexdigest());grant=authorize(control,trust,cfg['authority_binding'],Budget());assert grant.decision=='allow'
    old=deepcopy(cfg['authority_binding']);old['version']='s02-h3-work/0.1.0-draft.3'
    with pytest.raises(S02Error):authorize(control,trust,old,Budget())
    bad=deepcopy(cfg);bad['parent_metadata']['marker']=C.ADMISSION
    with pytest.raises(S02Error):ContinuationVerifier(direct.history).config(bad,direct,raw)


@pytest.mark.parametrize('field',['unexpected','anchor','mode','step','candidate'])
def test_G_C1_closed_shapes_and_mode_inputs(direct,field):
    cfg,raw=request(direct)
    if field=='unexpected':cfg['unexpected']=True
    elif field=='anchor':cfg['anchor']={}
    elif field=='mode':cfg['mode']='adopt'
    elif field=='step':cfg['step']=0
    else:cfg['inputs']['candidate']=None
    with pytest.raises(S02Error):C.validate('Config',cfg,Budget())


def test_G_C3_stage1_B_to_C_and_C_to_C_progress_without_Model_edit(direct):
    cfg,raw=request(direct);h,b,r,p=projected(direct,cfg,raw);uid=units(r)['/functional_requirements/1'];u=units(r)['/functional_requirements/0']
    assert p['batch']['head'][0]==direct.pair[0] and r.issues==b.issues
    assert p['admission']['progress_by_unit'][uid]['work_completed_through']==1
    assert p['admission']['progress_by_unit'][uid]['outputs'][0]['output_ids']==[]
    assert p['admission']['progress_by_unit'][u]['work_completed_through']==0
    assert p['admission']['progress_by_unit'][u]['actual_output_ids']==cfg['parent_metadata']['progress_by_unit'][u]['actual_output_ids']
    cfg2,raw2=request(r,mode='revalidate');h2,b2,r2,p2=projected(r,cfg2,raw2)
    assert cfg2['parent_metadata']==p['admission'] and p2['admission']['progress_by_unit'][uid]['work_completed_through']==1
    assert p2['admission']['progress_by_unit'][uid]['assessment']['parent_assessment_sha256']==digest(p['admission']['progress_by_unit'][uid]['assessment'])


@pytest.mark.parametrize('branch,assessment',[('direct','applicable'),('carry','applicable'),('pending','undetermined'),('replacement','complete'),('incomplete','incomplete')])
def test_G_C2_Model_A2_successors_keep_root_history_and_allow_independent_V(tmp_path,monkeypatch,branch,assessment):
    _,g,base=b_parent(tmp_path,monkeypatch,branch);oldroot=deepcopy(g.records['Q2-resolved']);oldcurrent=base.issue('Question2');events=deepcopy(base.history._state['events']);oldrecords=deepcopy(base.history._state['records'])
    cfg,raw=request(base);_,_,middle,p1=projected(base,cfg,raw)
    cfg2,raw2=request(middle,step=2);h,b,r,p=projected(middle,cfg2,raw2)
    assert p['candidate_outcome']=='valid' and r.pair[0]!=b.pair[0]
    q=r.issue('Question2');proof=q['body']['resolution_carry'] or q['body']['resolution_replacement']
    assert proof['assessment']==assessment and proof['from_issue_id']==b.issue('Question2')['id'] and proof['origin_issue_id']=='Q2-resolved'
    assert q['body']['supersedes_id']==b.issue('Question2')['id']
    assert q['body']['answer_ids']==oldroot['body']['answer_ids'] and q['body']['resolution_event_refs']==oldroot['body']['resolution_event_refs']
    assert all(h._state['records'][i]==v for i,v in oldrecords.items()) and all(h._state['events'][k]==v for k,v in events.items())
    assert sum(e['kind']=='application_applied' for e in h._state['events'].values())==1
    change=h._state['records'][r.context.body['change_id']]['body'];assert change['kind']=='analysis_edit' and change['application_event_refs']==[]
    assert set(change['source_record_ids'])==set(b.analysis_set['body']['issue_ids'])
    assert len(r.context.body['actions'])==3 and r.context.body['actions'][:2]==b.context.body['actions']
    assert p['admission']['progress_by_unit'][units(r)['/functional_requirements/1']]['work_completed_through']==2
    if assessment in ('undetermined','incomplete'):assert q['body']['status']=='resolution_pending_revalidation' and q['body']['blocking']['element_ids']


def test_G_C4_step1_through4_retains_unassessed_U_without_overwrite(direct):
    current=direct;plans=[]
    for step in range(1,5):
        cfg,raw=request(current,step=step);h,b,current,p=projected(current,cfg,raw);plans.append(p);assert p['candidate_outcome']=='valid'
    uid=units(current)['/functional_requirements/1'];u=units(current)['/functional_requirements/0']
    assert plans[-1]['admission']['progress_by_unit'][uid]['work_completed_through']==4
    assert [int(o['step']) for o in plans[-1]['admission']['progress_by_unit'][uid]['outputs']]==[1,2,3,4]
    assert plans[-1]['admission']['progress_by_unit'][u]['work_completed_through']==0 and plans[-1]['admission']['progress_by_unit'][u]['assessment_state']=='needs_revalidation'
    assert current.context.body['actions'][:2]==direct.context.body['actions']


@pytest.mark.parametrize('target',[False,True])
def test_G_C2_not_applicable_never_carries_or_first_completes(tmp_path,monkeypatch,target):
    _,g,base=b_parent(tmp_path,monkeypatch,'obsolete',target);cfg,raw=request(base);_,_,middle,_=projected(base,cfg,raw)
    cfg,raw=request(middle,step=2);h,b,r,p=projected(middle,cfg,raw)
    assert p['candidate_outcome']==('valid' if target else 'guard_only')
    q=r.issue('Question2')
    if target:
        assert q['body']['resolution_carry'] is None and q['body']['resolution_replacement']['assessment']=='incomplete'
        assert q['body']['resolution_replacement']['replacement_issue_id']==r.issue('ExistingTarget')['id']
    else:assert r.pair[0]==b.pair[0] and q==b.issue('Question2')


def test_G_C3_guard_own_null_then_inherited_actual_SHA(direct):
    cfg,raw=request(direct);_,_,middle,_=projected(direct,cfg,raw)
    def unknown_action(c,a):c['proposals']['actions'][0]['initiator']='unknown'
    cfg,raw=request(middle,step=2,mutate=unknown_action);h,b,r,p=projected(middle,cfg,raw)
    assert p['candidate_outcome']=='guard_only' and r.pair[0]==b.pair[0]
    guard=next(g for g in p['admission']['guards'].values() if g.get('version')==C.GUARD)
    assert guard['origin_plan_sha256'] is None and guard['origin_plan_artifact_id']==p['allocation']['plan_artifact_id']
    cfg2,raw2=request(r,mode='revalidate');h2,b2,r2,p2=projected(r,cfg2,raw2)
    inherited=p2['admission']['guards'][guard['issue_key']];assert inherited['origin_plan_sha256']==digest(p)
    assert cfg2['parent_metadata']['guards'][guard['issue_key']]['origin_plan_sha256'] is None


def test_G_C2_G_C3_anchored_tasks_keep_pinned_predicates_through_detached_steps3_4(tmp_path):
    from h3_b_runtime_fixtures import BCase,baseline
    from h3_b_fixtures import state_of
    from dacn_s02.h3_review_io import LocalSyntheticHistoricalReviews
    from dacn_s02.h3_history import HistoryData
    path=tmp_path/'source';path.mkdir();source=baseline(path);source.historical_entries=[];case=BCase(tmp_path/'adopt',source);case.execute(*case.work(anchor=case.anchor()))
    budget=Budget();reg=LocalSyntheticHistoricalReviews.load(case.trust,budget);repo=reg.open_repository(case.db);h=HistoryData(**state_of(repo),registry=reg.registry,store_id=case.store_id,budget=budget)
    session=h._state['commands'][case.parent]['session_id'];current=h.view(session,case.pair,case.pair);completed={}
    for step in (3,4):
        cfg,raw=request(current,step=step);h,b,current,p=projected(current,cfg,raw);assert p['candidate_outcome']=='valid'
        for key,t in p['admission']['tasks'].items():
            if t['unit_ids']==[source.v] and int(t['target_step'])<=step:
                q=current.issue(key);assert q['body']['status']=='resolved'
                if key in completed:assert q['body']['resolution']==completed[key]
                completed[key]=q['body']['resolution']
        assert p['admission']['progress_by_unit'][source.v]['work_completed_through']==step
    assert completed and current.context.body['actions']==b.context.body['actions']
