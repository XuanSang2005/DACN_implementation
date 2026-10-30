from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
from decimal import Decimal
import pytest
from dacn_s02.codec_boundary import encode
from dacn_s02.errors import S02Error
from dacn_s02.h3_contracts import (Contract,validate,schema,CONFIG,PLAN,ADMISSION,POLICY,HANDLER,ANCHOR)
from dacn_s02.h3_limits import Budget,DEFAULTS,VERSION,references,digest
from dacn_s02.h3_bindings import config_intent,check_config,check_admission,check_anchor
from h3_fixtures import setup,view,selector_rows,bind_work
from dacn_s02.h3_policy import unassessed_progress
from dacn_s02.profiles import E1,get_profile


def admission(v):
    qs={q['body']['issue_key']:q for q in v.issues};roles=[]
    for k,q in qs.items():
        p=q['body']['resolution_carry'] or q['body']['resolution_replacement']
        roles.append(dict(issue_key=k,predecessor_issue_id=q['body']['supersedes_id'],current_issue_id=q['id'],
            origin_issue_id=p['origin_issue_id'] if p else None,obsolete_issue_id=p.get('obsolete_issue_id') if p else None,
            replacement_issue_id=p.get('replacement_issue_id') if p else None))
    return dict(marker=ADMISSION,policy_version=POLICY,from_pair=v.pair,result_pair=v.pair,
        obligations=[dict(source_ref=r['source_ref'],mapping_row_id=r['id'],assessment=r['assessment'],mapping_part_ids=[p['id'] for p in r['parts']],issue_ids=r['issue_ids']) for r in v.context.body['mappings']],
        selectors={r['issue_key']:r for r in selector_rows(v)},tasks={},guards={},progress_by_unit=unassessed_progress(v),
        retained_assessments=[],issue_roles=roles,transitions=[],full_hold_reasons=[])


def config(v):
    rows=selector_rows(v);bb,*_=bind_work(v,rows);binding=bb.payload()
    analysis=b'{}';binding.update(operation='adopt',goal='admission',step=0,candidate_sha256=None,candidate_length=0,
        analysis_sha256=sha256(analysis).hexdigest(),analysis_length=2)
    pins=get_profile(E1).descriptor
    c=dict(profile_id=E1,contract_version=pins['contract_version'],rules_id=pins['rules_id'],marker=CONFIG,config_version=CONFIG,
        handler_version=HANDLER,policy_version=POLICY,limits_version=VERSION,limits=dict(vars(DEFAULTS)),store_id='Store',session_id=v.session_id,
        command_id='FutureCommand',parent_command_id=v.parent_command_id,reserved_run_id='ReservedRun',started_at='2026-10-29T00:00:00.000Z',
        mode='adopt',step=0,unit_ids=sorted(v.context.source.units),goal='admission',source_context_id=v.context.source.context_id,
        snapshot_id=v.context.source.snapshot_id,archive_sha256=v.context.source.archive_sha256,base_model_id=v.pair[0],base_analysis_set_id=v.pair[1],
        base_model_sha256=digest(v.context.model()),base_analysis_set_sha256=digest(v.analysis_set),anchor=None,parent_metadata=None,aliases={},
        inputs=dict(candidate=None,analysis=dict(stage_ref=dict(command_id='FutureCommand',blob_id='Analysis'),sha256=sha256(analysis).hexdigest(),byte_length=2,media_type='application/json')),
        historical_reviews_pin=v.history.registry.pin(),history_binding=v.history.binding(v),authority_binding=binding,intent_sha256='0'*64)
    c['intent_sha256']=digest(config_intent(c));return c


def test_closed_private_config_crosspins_and_pure_schema_copy(foundation):
    v=view(setup(foundation));c=config(v);original=deepcopy(c);checked=check_config(c,v)
    assert checked==c==original
    detached=schema('Config');detached['$defs']['Config']['additionalProperties']=True
    c['trusted']=True
    with pytest.raises(S02Error):validate('Config',c,Budget())
    assert schema('Config')['$defs']['Config']['additionalProperties'] is False


@pytest.mark.parametrize('path',[
 ('historical_reviews_pin',),('history_binding',),('authority_binding',),('inputs','analysis'),('inputs','analysis','stage_ref'),('limits',)
])
def test_nested_private_objects_are_closed(foundation,path):
    v=view(setup(foundation));c=config(v);d=c
    for key in path:d=d[key]
    d['unexpected']=True
    with pytest.raises(S02Error):validate('Config',c,Budget())


@pytest.mark.parametrize('path,value',[
 (('step',),True),(('step',),Decimal('1.5')),(('limits','compute_seconds'),31),
 (('inputs','analysis','media_type'),'text/plain'),(('historical_reviews_pin','raw_sha256'),'NOT-A-HASH'),
 (('mode',),'unknown'),(('started_at',),'yesterday'),(('unit_ids',),[]),
 (('aliases',),{'Handle':{'id':'A1','kind':'Unspecified'}})
])
def test_types_and_versions_do_not_coerce(foundation,path,value):
    v=view(setup(foundation));c=config(v);d=c
    for k in path[:-1]:d=d[k]
    d[path[-1]]=value
    with pytest.raises(S02Error):validate('Config',c,Budget())


@pytest.mark.parametrize('key',['base_model_sha256','base_analysis_set_sha256','archive_sha256','intent_sha256'])
def test_config_crosspins_are_not_shape_only(foundation,key):
    v=view(setup(foundation));c=config(v);c[key]='0'*64
    with pytest.raises(S02Error):check_config(c,v)


def test_admission_full_rows_current_roles_and_no_progress_inference(foundation):
    g=setup(foundation);g.carry('undetermined');v=view(g);a=admission(v);assert check_admission(a,v)==a
    a['obligations'].pop()
    with pytest.raises(S02Error,match='admission_obligation_inventory'):check_admission(a,v)


def test_anchor_shapes_order_and_no_self_claimed_progress(foundation):
    v=view(setup(foundation));a=dict(version=ANCHOR,command_id=v.parent_command_id,plan_artifact_id='MissingArtifact',plan_sha256='0'*64,
        published_pair=v.pair,source_context_id=v.context.source.context_id,snapshot_id=v.context.source.snapshot_id,transitions=[],transition_hashes=[],outputs=[])
    assert validate('Anchor',a,Budget())==a
    with pytest.raises(S02Error,match='anchor_plan_artifact'):check_anchor(a,v)
    a['transition_hashes']=['0'*64]
    with pytest.raises(S02Error,match='anchor_transition_hashes'):validate('Anchor',a,Budget())


def test_progress_cannot_claim_stage_four_from_empty_model_appearance(foundation):
    p=next(iter(unassessed_progress(view(setup(foundation))).values()));p['work_completed_through']=4
    with pytest.raises(S02Error,match='progress_proven_stages'):validate('Progress',p,Budget())


def test_ref_occurrences_include_historical_and_map_uses_not_unique_ids():
    value=dict(required_issue_ids=['Q','Q'],reviews=[dict(issue_id='Q')],current_issues={'Key':'Q'},
        progress_by_unit={'Unit':dict(outputs=[dict(output_ids=['A','A'])])},
        source_ref=dict(snapshot_id='S',input_pointer='/title'))
    # 2 required +1 entry + map key1/value1 + unit key1
    # +2 output refs +1 atomic SourceRef. Expected counts written explicitly.
    assert references(value)==9


@pytest.mark.parametrize('kind,raw',[('registry',b' '*8),('authority',b' '*8),('config',b' '*8),('plan',b' '*8)])
def test_each_exact_serialized_lane_has_its_own_cap(kind,raw):
    b=Budget(limits=replace(DEFAULTS,**{kind+'_bytes':7}))
    with pytest.raises(S02Error,match=kind+'_bytes'):b.parse(raw,kind=kind)


def test_shared_input_budget_cannot_reset_or_deduplicate_occurrences():
    b=Budget(limits=replace(DEFAULTS,refs=3))
    b.inspect(dict(issue_ids=['Q','Q']),input_lane=True,slot='one')
    with pytest.raises(S02Error,match='refs'):b.inspect(dict(answer_ids=['A','A']),input_lane=True,slot='two')
    with pytest.raises(S02Error):Budget(limits=replace(DEFAULTS,compute_seconds=31))


def test_time_depth_unicode_cycles_and_exact_codec_limits():
    clock=[0];b=Budget(clock=lambda:clock[0]);clock[0]=31
    with pytest.raises(S02Error,match='compute_seconds'):b.inspect({})
    cyclic=[];cyclic.append(cyclic)
    with pytest.raises(S02Error,match='cyclic_input'):Budget().inspect(cyclic)
    with pytest.raises(S02Error):Budget().parse(b'{"duplicate":1,"duplicate":2}')
    with pytest.raises(S02Error):Budget().inspect({'float':1.5})
    with pytest.raises(S02Error):Budget(limits=replace(DEFAULTS,depth=2)).parse(b'[[[]]]')
    with pytest.raises(S02Error):Budget().inspect({'bad':'\ud800'})


def test_ast_no_h3_filesystem_repository_network_or_clock_effects():
    # Source inspection complements behavioral tests; contracts cannot hide a
    # filesystem loader/Repository factory within this pure A release.
    import ast,importlib.util
    for module in ('h3_contracts','h3_history','h3_policy','h3_bindings'):
        path=importlib.util.find_spec('dacn_s02.'+module).origin
        tree=ast.parse(__import__('pathlib').Path(path).read_text())
        calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call)]
        assert not any(isinstance(n.func,ast.Name) and n.func.id in ('open','Repository') for n in calls)
        assert not any(isinstance(n.func,ast.Attribute) and n.func.attr in ('read_bytes','write_bytes','read_text','write_text','connect','urlopen','finalize') for n in calls)


@pytest.mark.parametrize('wrong_from',[False,True])
def test_positive_pure_plan_projection_and_exact_reserved_pins(foundation,wrong_from):
    from dacn_s02.service import artifact,staged
    from h3_fixtures import data
    from dacn_s02.h3_bindings import check_plan
    g=setup(foundation);budget=Budget();before=view(g,budget);c=config(before)
    op,aset=g.publish([],list(g.records[g.set_id]['body']['issue_ids']));cmd=op['command_id'];rid=op['reserved_run_id']
    op['parent_command_id']=before.parent_command_id
    c.update(command_id=cmd,reserved_run_id=rid,started_at=g.records[rid]['body']['started_at'])
    c['inputs']['analysis']['stage_ref']['command_id']=cmd;c['intent_sha256']=digest(config_intent(c))
    primary=staged(cmd,'PrimaryStage','config',encode(c));analysis=staged(cmd,'Analysis','llm_response',b'{}')
    rawarts=[artifact('H3Primary','config',encode(c),rid),artifact('H3Analysis','llm_response',b'{}',rid)]
    for a,(_,blob) in zip(rawarts,[primary,analysis]):g.add(a);g.blobs[a['id']]=blob
    g.records[rid]['body']['config_artifact_id']='H3Primary'
    for meta,blob in [primary,analysis]:g.stages[cmd,meta['blob_id']]={**meta,'bytes':blob}
    inputs=[dict(artifact_id=a['id'],stage_ref=dict(command_id=cmd,blob_id=x[0]['blob_id'])) for a,x in zip(rawarts,[primary,analysis])]
    g.events[cmd,'prep']['payload']['stage_refs']=[p['stage_ref'] for p in inputs];g.events[cmd,'final']['payload']['promotions']=inputs
    interim=view(g,budget);ad=admission(interim);ad['from_pair']=interim.pair if wrong_from else before.pair
    pins=get_profile(E1).descriptor
    plan=dict(profile_id=E1,contract_version=pins['contract_version'],rules_id=pins['rules_id'],marker=PLAN,plan_version=PLAN,
        bindings=dict(command_id=cmd,session_id=g.session,parent_command_id=before.parent_command_id,reserved_run_id=rid,
            primary_config_sha256=digest(c),primary_config_stage_ref=dict(command_id=cmd,blob_id='PrimaryStage'),intent_sha256=c['intent_sha256'],
            base_pair=before.pair,history_sha256=digest(c['history_binding']),anchor_sha256=None,authority_binding_sha256=digest(c['authority_binding']),historical_reviews_pin=c['historical_reviews_pin'],handler_version=HANDLER),
        allocation=dict(plan_blob_id='SealedPlan',plan_artifact_id='SealedPlanArtifact',created_at=c['started_at'],aliases={}),
        batch=dict(records=rawarts+[deepcopy(g.records[rid]),deepcopy(aset)],artifact_sources=inputs,head=[g.model_id,g.set_id]),
        promotions=inputs+[dict(artifact_id='SealedPlanArtifact',stage_ref=dict(command_id=cmd,blob_id='SealedPlan'))],
        admission=ad,candidate_outcome='adopted',diagnostics=[])
    raw=encode(plan);meta,_=staged(cmd,'SealedPlan','config',raw);g.stages[cmd,'SealedPlan']={**meta,'bytes':raw}
    a=artifact('SealedPlanArtifact','config',raw,rid);g.add(a);g.blobs[a['id']]=raw;g.events[cmd,'final']['payload']['promotions']=plan['promotions']
    after=view(g,budget)
    if wrong_from:
        with pytest.raises(S02Error,match='plan_admission_base_pair'):check_plan(plan,c,after)
        return
    assert check_plan(plan,c,after)==plan
    bad=deepcopy(plan);bad['bindings']['reserved_run_id']='DifferentRun'
    with pytest.raises(S02Error,match='plan_config_identity'):check_plan(bad,c,after)
    assert g.records[rid]['body']['result_model_id'] is None
    assert g.records[g.set_id]['body']['issue_ids']==before.analysis_set['body']['issue_ids']
