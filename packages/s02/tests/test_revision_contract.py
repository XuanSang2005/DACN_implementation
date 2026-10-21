from copy import deepcopy
import pytest
from dacn_s02.repository import Repository,record
from dacn_s02.errors import S02Error
from dacn_s02.validation import shape
from helpers import model,aset,issue,run,trace,allscope,evidence
from test_repository import validation

def revision(f,base,number,mutate):
    op=f.operation();f.repo.prepare(op);m=deepcopy(base);m['id']='M'+str(number)
    m['body'].update(revision=number,parent_model_id=base['id'],change_id='CH'+str(number),created_by_run_id=op['reserved_run_id'])
    mutate(m)
    change=record('change','CH'+str(number),dict(base_model_id=base['id'],new_model_id=m['id'],kind='analysis_edit',old_source_context_id=f.context,new_source_context_id=f.context,reason='Synthetic ordered revision',source_record_ids=[],application_event_refs=[],operations=[dict(kind='replace',element_id='A1',reason='Synthetic content change')],affected=allscope(m),reused=[],reevaluate=[],invalidated_bundle_ids=[]))
    a=aset(m,'AS-M'+str(number));r=run(op,f.context,f.config,model_id=m['id'],set_id=a['id'])
    f.repo.finalize(op['command_id'],[m,a,change,r],head=(m['id'],a['id']))
    f.repo=Repository(f.repo.path);assert f.repo.get_record(m['id'])==m
    return m,a

def test_revision_chain_reopen_reorder_back_to_old(foundation):
    f=foundation;m1,a1=f.initial()
    m2,_=revision(f,m1,2,lambda m:m['body']['actions'][0].update(name='Changed name'))
    m3,_=revision(f,m2,3,lambda m:m['body']['actions'].reverse())
    m4,a4=revision(f,m3,4,lambda m:m['body'].update(actions=deepcopy(m1['body']['actions'])))
    assert m4['body']['actions']==m1['body']['actions'];assert m4['body']['parent_model_id']=='M3'
    assert f.repo.heads(f.session)==('M4','AS-M4')
    assert f.repo.get_record('M1')==m1
    evidence('model_revision_chain',heads=['M1','M2','M3','M4'],final_heads=f.repo.heads(f.session),reopened_between=True)

def test_stale_base_even_no_model_change(foundation):
    f=foundation;m,a=f.initial();old=f.operation();f.repo.prepare(old)
    revision(f,m,2,lambda v:v['body']['actions'][0].update(name='Changed'))
    r=f.repo.finalize(old['command_id'],[run(old,f.context,f.config)])
    assert r['body']['status']=='stale';assert r['body']['errors'][0]['code']=='MODEL_CONFLICT'
    assert f.repo.heads(f.session)==('M2','AS-M2')

def scenario(m,identity,key='ScenarioKey',supersedes=None):
    snapshot=m['body']['actors'][0]['trace']['source_refs'][0]['snapshot_id']
    return record('scenario',identity,dict(analysis_key=key,supersedes_id=supersedes,model_id=m['id'],name='Synthetic walkthrough',trace=trace(snapshot),scope=allscope(m),trigger='Synthetic',conditions=[],expected_obligations=[dict(snapshot_id=snapshot,input_pointer='/functional_requirements/0')],walkthrough=[],assessment='not_assessed',issue_ids=[],verification_obligations=['Not executed']))

def characteristic(m,identity,scenario_id,supersedes=None):
    snapshot=m['body']['actors'][0]['trace']['source_refs'][0]['snapshot_id']
    return record('characteristic',identity,dict(analysis_key='QualityKey',supersedes_id=supersedes,model_id=m['id'],name='Synthetic quality',trace=trace(snapshot),scope=allscope(m),goal=None,conditions=[],priority=None,scenario_ids=[scenario_id],boundary_effects=[],options=[dict(id='Keep',action='keep',description='Proposed only',benefits=[],costs=[],other_characteristic_impacts=[],constraint_refs=[],precondition_issue_ids=[])],recommendation='undecided',recommended_option_id=None,issue_ids=[],risks=[],verification_obligations=['Not measured']))

def test_current_scenario_successor_requires_characteristic_successor(foundation):
    f=foundation;m,a=f.initial();op=f.operation();f.repo.prepare(op)
    s=scenario(m,'SC1');ch=characteristic(m,'CHAR1','SC1');a2=aset(m,'AS2',a,scenarios=['SC1'],characteristics=['CHAR1'])
    f.repo.finalize(op['command_id'],[s,ch,a2,run(op,f.context,f.config,set_id='AS2')],head=('M1','AS2'))
    op=f.operation();f.repo.prepare(op);s2=scenario(m,'SC2',supersedes='SC1');a3=aset(m,'AS3',a2,scenarios=['SC2'],characteristics=['CHAR1'],changed=['SC2'])
    with pytest.raises(S02Error) as e:f.repo.finalize(op['command_id'],[s2,a3,run(op,f.context,f.config,set_id='AS3')],head=('M1','AS3'))
    assert e.value.error['details']['invariant']=='analysis_scenario_ref_current'
    ch2=characteristic(m,'CHAR2','SC2',supersedes='CHAR1');a3['body'].update(characteristic_ids=['CHAR2'],changed_record_ids=['SC2','CHAR2'])
    f.repo.finalize(op['command_id'],[s2,ch2,a3,run(op,f.context,f.config,set_id='AS3')],head=('M1','AS3'))
    assert f.repo.heads(f.session)==('M1','AS3')

def test_bundle_pins_set_and_becomes_stale_without_model_change(foundation):
    f=foundation;m,a=f.initial();op=f.operation();f.repo.prepare(op)
    view=record('view','View',dict(model_id='M1',name='Synthetic view',component_ids=['C1','C2'],interface_ids=[],dependency_ids=[],omitted_element_ids=[],scope_note='No render has run',config_artifact_id=f.config))
    diagram=record('diagram','Diagram',dict(model_id='M1',view_id='View',converter_version='not_run',toolchain_artifact_id=f.config,status='not_run',puml_artifact_id=None,svg_artifact_id=None,aliases=[],validation_id=None))
    v=validation(m,a);v['body'].update(view_id='View',diagram_id='Diagram')
    bundle=record('bundle','Bundle',dict(model_id='M1',analysis_set_id='AS1',source_context_id=f.context,scenario_ids=[],characteristic_ids=[],issue_ids=[],answer_ids=[],change_ids=[],view_id='View',diagram_id='Diagram',validation_id='V1',status='preparing_review',disclosures=['No render or review performed']))
    f.repo.finalize(op['command_id'],[view,diagram,v,bundle,run(op,f.context,f.config)])
    assert f.repo.check_freshness('Bundle')==bundle
    op=f.operation();f.repo.prepare(op);q=issue(m);a2=aset(m,'AS2',a,issues=['Q2'])
    f.repo.finalize(op['command_id'],[q,a2,run(op,f.context,f.config,set_id='AS2')],head=('M1','AS2'))
    with pytest.raises(S02Error) as e:f.repo.check_freshness('Bundle')
    assert e.value.error['code']=='ANALYSIS_STALE';assert f.repo.get_record('Bundle')==bundle

@pytest.mark.parametrize('bad',[{},None,{'type':None},{'type':True},{'type':12}])
def test_malformed_record_type_controlled(bad):
    with pytest.raises(S02Error):shape(bad)

def test_cross_session_record_reference_rejected(foundation):
    f=foundation;m,a=f.initial();from dacn_s02.service import Service
    other=Service(f.repo).start(f.s01.path,'synthetic',f.s01env['run']['run_id'])
    op=f.operation();f.repo.prepare(op);wrong=run(op,other['source_context_id'],f.config)
    with pytest.raises(S02Error):f.repo.finalize(op['command_id'],[wrong])
    assert f.repo.get_record(op['reserved_run_id']) is None

def test_typed_source_kinds_do_not_accept_same_text_elsewhere(foundation):
    f=foundation;m,a=f.initial();snapshot=deepcopy(f.s01env['snapshot']);snapshot['input']['title']='Operator'
    m['body']['actors'][0]['trace']['source_refs'][0]['input_pointer']='/title'
    from dacn_s02.validation import validate_model,validate_record
    creator=f.repo.get_record(m['body']['created_by_run_id'])
    with pytest.raises(S02Error) as e:validate_model(m,{m['id']:m,creator['id']:creator},snapshot)
    assert e.value.error['details']['invariant']=='supplied_actor_source'
    s=scenario(m,'SC');ch=characteristic(m,'CHAR','SC')
    ch['body']['options'][0]['constraint_refs']=[dict(snapshot_id=f.snapshot,input_pointer='/functional_requirements/0')]
    records={r['id']:r for r in [m,s,ch,f.repo.get_record(f.context)]}
    with pytest.raises(S02Error) as e:validate_record(ch,records,{f.snapshot:snapshot})
    assert e.value.error['details']['invariant']=='option_constraint_source_kind'

def test_walk_element_ref_must_match_scenario_model(foundation):
    f=foundation;m1,a=f.initial();m2,a2=revision(f,m1,2,lambda m:m['body']['actions'][0].update(name='changed'))
    op=f.operation();f.repo.prepare(op);s=scenario(m2,'SC2')
    s['body']['walkthrough']=[dict(order=1,element_refs=[dict(model_id='M1',element_id='A1')],observation='Wrong revision')]
    new=aset(m2,'AS2-next',a2,scenarios=['SC2'])
    with pytest.raises(S02Error) as e:f.repo.finalize(op['command_id'],[s,new,run(op,f.context,f.config,set_id='AS2-next')],head=('M2','AS2-next'))
    assert e.value.error['details']['invariant']=='nested_reference_model'

def test_run_cannot_claim_old_set_as_new_result(foundation):
    f=foundation;m,a=f.initial();op=f.operation();f.repo.prepare(op)
    with pytest.raises(S02Error) as e:f.repo.finalize(op['command_id'],[run(op,f.context,f.config,set_id=a['id'])])
    assert e.value.error['details']['invariant']=='run_without_publication'
    with pytest.raises(S02Error) as e:f.repo.finalize(op['command_id'],[run(op,f.context,f.config,set_id=a['id'])],head=(m['id'],a['id']))
    assert e.value.error['details']['invariant']=='run_published_set'
