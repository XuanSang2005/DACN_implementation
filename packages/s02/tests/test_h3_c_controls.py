"""Adversarial pure C checks; expected sets are from explicit synthetic topology."""
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import pytest
from dacn_s02.codec_boundary import encode
from dacn_s02.errors import S02Error
from dacn_s02.h3_limits import Budget,digest
from dacn_s02.h3_history import HistoryData
from dacn_s02.h3_policy import SemanticTrustContext
from dacn_s02.h3_continuation_inputs import authorize,intent
from dacn_s02.h3_continuation_checks import ContinuationVerifier
from dacn_s02 import h3_continuation_contracts as C
from dacn_s02.h3_continuation_policy import touches
from dacn_s02.h2_graph import ModelContext
from h3_c_fixtures import b_parent,request,projected,units,history_graph,graph_case


@pytest.fixture(scope='module')
def seed(tmp_path_factory):
    with pytest.MonkeyPatch.context() as patch:return b_parent(tmp_path_factory.mktemp('C-control-source'),patch)[2]


@pytest.fixture
def base(seed):
    h=HistoryData(**seed.history.payload(),registry=seed.history.registry,store_id=seed.history.store_id,budget=Budget());return h.view(seed.session_id,seed.pair,seed.pair)


@pytest.mark.parametrize('mutation',['scope_hash','unknown_field','snapshot','unit_ids','base_handle','canonical_proof'])
def test_G_C1_G_C4_bad_raw_is_rejected_and_kept_exact_without_domain(base,mutation):
    cfg,raw=request(base);_,_,middle,_=projected(base,cfg,raw)
    def change(c,a):
        if mutation=='scope_hash':c['scope_request_sha256']='0'*64
        elif mutation=='unknown_field':c['unexpected']=True
        elif mutation=='snapshot':c['proposals']['actions'][0]['trace']['source_refs'][0]['snapshot_id']='WrongSnapshot'
        elif mutation=='unit_ids':c['unit_ids']=[units(middle)['/functional_requirements/0']]
        elif mutation=='base_handle':c['proposals']['actions'][0]['actor_ids']=[dict(base_handle='invented')]
        else:c['proposals']['resolution_carry']={'assessment':'applicable'}
    cfg,raw=request(middle,step=2,mutate=change);h,b,r,p=projected(middle,cfg,raw)
    assert r is None and p['candidate_outcome']=='rejected' and p['batch']['head'] is None and p['admission'] is None
    assert {r['type'] for r in p['batch']['records']}=={'artifact','run'}
    assert next(r for r in p['batch']['records'] if r['type']=='run')['body']['status']=='rejected'
    pin=cfg['inputs']['candidate'];stage=h._state['stages'][cfg['command_id'],pin['stage_ref']['blob_id']]
    assert stage['bytes']==raw['candidate'] and stage['sha256']==sha256(raw['candidate']).hexdigest()
    assert sum(e['kind']=='application_applied' for e in h._state['events'].values())==1


@pytest.mark.parametrize('mutation',['projection','model','assessment','stage','parent','guard'])
def test_G_C3_G_C4_tampered_sealed_claims_do_not_replace_raw_reconstruction(base,mutation):
    cfg,raw=request(base);_,_,middle,_=projected(base,cfg,raw)
    cfg,raw=request(middle,step=2);h,b,r,p=projected(middle,cfg,raw);bad=deepcopy(p)
    if mutation=='projection':
        m=bad['candidate_projection']['pre_successor_model'];m['body']['mappings'][0]['assessment']='not_assessed';bad['candidate_projection']['pre_successor_model_sha256']=digest(m)
    elif mutation=='model':next(v for v in bad['batch']['records'] if v['type']=='model')['body']['actions'][0]['name']='Edited completed U output'
    elif mutation=='assessment':next(iter(bad['admission']['progress_by_unit'].values()))['assessment']['proof_sha256']='0'*64
    elif mutation=='stage':bad['admission']['progress_by_unit'][units(r)['/functional_requirements/0']]['work_completed_through']=4
    elif mutation=='parent':bad['admission']['from_pair']=r.pair
    else:bad['candidate_outcome']='guard_only'
    with pytest.raises(S02Error):ContinuationVerifier(h).result(cfg,bad,b,r)


def test_G_C1_modified_raw_binding_cannot_borrow_original_grant(base):
    cfg,raw=request(base);bb=cfg['authority_binding'];control=encode(dict(format=C.AUTHORITY,provider_id=bb['provider_id'],provider_version='local-synthetic/1',purpose='synthetic_test_only',approvals=[dict(binding=bb,decision='allow',reason='Synthetic exact tuple')]))
    trust=SemanticTrustContext(bb['provider_id'],'local-synthetic/1',sha256(control).hexdigest());changed=deepcopy(bb);changed['candidate_sha256']=sha256(raw['candidate']+b' ').hexdigest();changed['candidate_length']+=1
    assert authorize(control,trust,changed,Budget()).decision=='deny'
    bad=deepcopy(cfg);bad['inputs']['candidate']['sha256']='0'*64
    with pytest.raises(S02Error):ContinuationVerifier(base.history).config(bad,base,raw)


def test_G_C1_cached_scope_is_recomputed_not_trusted(base):
    cfg,raw=request(base);ctx=base.context;ctx.closure(*ctx.source_seed(ctx.source.obligations));key=next(iter(ctx._cache));ctx._cache[key]=replace(ctx._cache[key],actions=frozenset())
    with pytest.raises(S02Error,match='c_context_cache_fixed_point'):ContinuationVerifier(base.history).config(cfg,base,raw)


@pytest.mark.parametrize('mutation',['from','origin','source','scope','false_release'])
def test_G_C2_corrupt_history_rejected_before_builder(tmp_path,monkeypatch,mutation):
    _,g=graph_case(tmp_path,monkeypatch,'pending');q=g.records[g.current_issue];p=q['body']['resolution_carry']
    if mutation=='from':p['from_issue_id']='Q2'
    elif mutation=='origin':p['origin_issue_id']='Q2'
    elif mutation=='source':p['source_checks'][0]['to_ref']['snapshot_id']='WrongSnapshot'
    elif mutation=='scope':p['scope_check']['to_scope']['element_ids']=[]
    else:p['source_checks']=[];p['assessment']='applicable';q['body']['status']='resolved';q['body']['blocking']['element_ids']=[];q['body']['blocking']['mapping_part_ids']=[]
    with pytest.raises(S02Error):history_graph(g)


def test_G_C4_unknown_hold_rematerializes_and_does_not_release_new_V(base):
    def finding(c,a):
        r=dict(snapshot_id=base.context.source.snapshot_id,input_pointer='/functional_requirements/0')
        c['proposals']['findings']=[dict(handle='unknown-impact',kind='business',question='Clarify unknown impact',reason='Synthetic unknown impact',trace=dict(origin='inferred',source_refs=[r],rationale='Unknown means global until proof',finding_handles=[]),affected_refs=[],blocking_refs=[],impact_known=False)]
        c['questions']=['unknown-impact']
        for row in a['inspections']:
            if row['source_ref']==r:row.update(verdict='held',needed_facts=['Unknown impact'])
        for row in c['inspection']:
            if row['source_ref']==r:row.update(verdict='held',needed_facts=['Unknown impact'],finding_handles=['unknown-impact'])
    cfg,raw=request(base,mutate=finding);h,b,middle,p=projected(base,cfg,raw)
    assert p['candidate_outcome']=='valid' and p['admission']['progress_by_unit'][units(middle)['/functional_requirements/1']]['work_completed_through']==1
    cfg,raw=request(middle,step=2);h,b,r,p=projected(middle,cfg,raw)
    assert p['candidate_outcome']=='guard_only' and r.pair[0]==b.pair[0]
    assert p['admission']['progress_by_unit'][units(r)['/functional_requirements/1']]['work_completed_through']==1
    assert len(r.context.body['actions'])==2


def test_G_C4_shared_component_is_context_but_real_Part_bridge_blocks(tmp_path,monkeypatch):
    from h3_fixtures import multi_setup,data
    g=multi_setup(tmp_path,monkeypatch,held=True);h=data(g);base=h.view(g.session,[g.model_id,g.set_id],[g.model_id,g.set_id]);q=base.issue('HoldU');source=base.context.source
    row=dict(issue_id=q['id'],issue_key='HoldU',target_step=1,kind='obligation_families',source_refs=[dict(snapshot_id=source.snapshot_id,input_pointer='/functional_requirements/0')],element_ids=['A1'],mapping_part_ids=['P1','PC0'],impact_known=True,code_task_role=None)
    v=next(u for u,f in source.units.items() if f.pointer=='/functional_requirements/1')
    assert not touches(base.context,q,row,v)
    model=base.context.model();model['body']['mappings'][0]['parts'][0]['action_ids']=['A1','A2'];model['body']['mappings'][0]['parts'][0]['primary_responsibility_ids']=['RS1','RS2'];ctx=ModelContext(model,source,base.history.budget)
    assert touches(ctx,q,row,v)
    fp=ctx.closure(['A2']);assert {'A1','A2'}<=fp.actions and {'P1','P2'}<=fp.parts


def test_G_C2_source_only_is_typed_clone_not_Answer_or_CARRY(tmp_path,monkeypatch):
    from dacn_s02.h3_history import project_current_refs
    _,_,base=b_parent(tmp_path,monkeypatch,'source_only');cfg,raw=request(base);_,_,middle,_=projected(base,cfg,raw)
    cfg,raw=request(middle,step=2);h,b,r,p=projected(middle,cfg,raw);old=b.issue('SourceOnly');current=r.issue('SourceOnly')
    remap={q['id']:r.issue(q['body']['issue_key'])['id'] for q in b.issues};expected=project_current_refs(old,r.pair[0],remap,b.history.budget);expected['supersedes_id']=old['id']
    assert current['body']==expected and current['body']['resolution_carry'] is None and current['body']['answer_ids']==[]
    assert p['candidate_outcome']=='valid'


@pytest.mark.parametrize('bridge',[False,True])
def test_G_C4_whole_candidate_guard_on_real_bridge_but_independent_mapping_progresses(tmp_path,monkeypatch,bridge):
    _,_,current=b_parent(tmp_path,monkeypatch,third=True);us=units(current);v=us['/functional_requirements/1'];w=us['/functional_requirements/2'];sid=current.context.source.snapshot_id
    cfg,raw=request(current,unit_ids=[v,w]);_,_,current,_=projected(current,cfg,raw)
    def both(c,a):
        c['proposals']['actions'][0]['trace']['source_refs']=[dict(snapshot_id=sid,input_pointer='/functional_requirements/1')]
        other=deepcopy(c['proposals']['actions'][0]);other['handle']='w-action';other['name']='Independent W';other['trace']['source_refs']=[dict(snapshot_id=sid,input_pointer='/functional_requirements/2')];c['proposals']['actions'].append(other)
    cfg,raw=request(current,step=2,unit_ids=[v,w],mutate=both);_,_,current,p=projected(current,cfg,raw);assert p['candidate_outcome']=='valid'
    aliases=ContinuationVerifier(current.history).published(current.parent_command_id).plan()['allocation']['aliases']
    va=next(k for k,a in aliases.items() if a['kind']=='Action' and a['id'] not in ('A1','A2') and current.context.elements[a['id']]['trace']['source_refs'][0]['input_pointer']=='/functional_requirements/1')
    def new_hold(c,a):
        r=dict(snapshot_id=sid,input_pointer='/functional_requirements/1')
        c['proposals']['findings']=[dict(handle='held-V',kind='business',question='Clarify V only',reason='Synthetic V rule remains unknown',trace=dict(origin='inferred',source_refs=[r],rationale='Explicit independent V hold',finding_handles=[]),affected_refs=[dict(base_handle=va)],blocking_refs=[dict(base_handle=va)],impact_known=True)];c['questions']=['held-V']
        for row in a['inspections']:
            if row['source_ref']==r:row.update(verdict='held',needed_facts=['V rule'])
        for row in c['inspection']:
            if row['source_ref']==r:row.update(verdict='held',needed_facts=['V rule'],finding_handles=['held-V'])
    cfg,raw=request(current,step=3,unit_ids=[w],mutate=new_hold);_,_,current,p=projected(current,cfg,raw);assert p['candidate_outcome']=='valid'
    def part(c,a):
        if bridge:c['proposals']['mappings'][0]['parts'][0]['action_ids'].append(dict(base_handle=va))
        for rows in (a['inspections'],c['inspection']):
            for row in rows:
                if row['source_ref']['input_pointer']=='/functional_requirements/1':row.update(verdict='held',needed_facts=['V rule'])
    cfg,raw=request(current,step=4,unit_ids=[w],mutate=part);h,b,r,p=projected(current,cfg,raw)
    assert p['candidate_outcome']==('guard_only' if bridge else 'valid')
    assert p['admission']['progress_by_unit'][w]['work_completed_through']==(3 if bridge else 4)
    if bridge:
        assert r.pair[0]==b.pair[0] and r.context.model()==b.context.model()
        assert p['candidate_projection']['pre_successor_model']['body']['mappings'][2]['parts'][0]['action_ids']
    else:assert r.pair[0]!=b.pair[0]


def test_G_C2_complete_replacement_falls_back_incomplete_without_new_attestation(tmp_path,monkeypatch):
    _,_,base=b_parent(tmp_path,monkeypatch,'replacement_tasks');old=base.issue('Question2')['body']['resolution_replacement'];assert old['assessment']=='complete'
    cfg,raw=request(base);_,_,middle,_=projected(base,cfg,raw)
    cfg,raw=request(middle,step=2);h,b,r,p=projected(middle,cfg,raw);q=r.issue('Question2');proof=q['body']['resolution_replacement']
    assert p['candidate_outcome']=='valid' and proof['assessment']=='incomplete' and q['body']['status']=='resolution_pending_revalidation'
    assert proof['obsolete_issue_id']==old['obsolete_issue_id'] and proof['origin_issue_id']==old['origin_issue_id'] and proof['from_issue_id']==b.issue('Question2')['id']
    assert proof['replacement_issue_id']==r.issue('NewDecision')['id'] and q['body']['blocking']['element_ids']
    assert not any(v['type']=='validation' for v in p['batch']['records'])


def test_E04_C_historical_switch_keeps_typed_sources_and_missing_structural_identity_held(tmp_path,monkeypatch):
    _,_,base=b_parent(tmp_path,monkeypatch,'switch');old=base.issue('Question2');assert old['body']['resolution_carry']['assessment']=='applicable'
    cfg,raw=request(base);_,_,middle,_=projected(base,cfg,raw)
    cfg,raw=request(middle,step=2);h,b,r,p=projected(middle,cfg,raw);q=r.issue('Question2');proof=q['body']['resolution_carry']
    assert p['candidate_outcome']=='valid' and r.pair[0]!=b.pair[0]
    assert proof['assessment']=='undetermined' and q['body']['status']=='resolution_pending_revalidation'
    assert len({c['from_ref']['snapshot_id'] for c in proof['source_checks']})==2
    assert all(c['to_ref']['snapshot_id']==r.context.source.snapshot_id and c['relation']=='equal_value' for c in proof['source_checks'])
    assert proof['origin_issue_id']==old['body']['resolution_carry']['origin_issue_id'] and proof['from_issue_id']==old['id']
    assert h._state['records'][old['id']]==old and p['admission']['progress_by_unit'][units(r)['/functional_requirements/1']]['work_completed_through']==2


def test_C_sealed_allocator_uses_only_pinned_T0_namespace_after_foreign_prepare(base):
    from dacn_s02.h3_continuation_plan import Allocator
    from dacn_s02.profiles import E1
    cfg,raw=request(base);role='allocation.2';identity=Allocator(cfg,base).key(role);state=base.history.payload()
    state['commands'][identity]=dict(command_id=identity,session_id=base.session_id,parent_command_id=base.parent_command_id,reserved_run_id='PostT0ForeignRun',request=dict(kind='work',source_context_id=base.context.source.context_id,base_model_id=base.pair[0],base_analysis_set_id=base.pair[1],scope=None,config_artifact_id=None))
    state['operation_profiles'][identity]=E1;state['events'][identity,'PostT0Prepared']=dict(event_id='PostT0Prepared',command_id=identity,ordinal=1,kind='prepared',payload=dict(stage_refs=[],attempt_id=None))
    h=HistoryData(**state,registry=base.history.registry,store_id=base.history.store_id,budget=Budget());later=h.view(base.session_id,base.pair,base.pair)
    assert Allocator(cfg,later).key(role)==identity
