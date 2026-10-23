from copy import deepcopy
import pytest
from dacn_s02.errors import S02Error
from dacn_s02.profiles import E1
from dacn_s02.scope import permitted_scope
from profile_fixtures import graph,fullfoot

@pytest.mark.parametrize('new_model',[False,True])
def test_carry_keeps_root_application_and_full_part_closure(foundation,new_model):
    g=graph(foundation);before=deepcopy(g.records[g.current_issue]);events=deepcopy(g.events)
    q=g.carry(new_model=new_model);g.check()
    assert g.records[before['id']]==before
    assert all(g.events[k]==v for k,v in events.items())
    assert sum(e['kind']=='application_applied' for e in g.events.values())==1
    assert {'A1','A2'}<=set(q['body']['resolution_carry']['scope_check']['to_scope']['element_ids'])

@pytest.mark.parametrize('assessment,method,valid',[('applicable','structural_check',True),('undetermined','structural_check',True),('not_applicable','structural_check',False),('applicable','human_review',True),('undetermined','human_review',True),('not_applicable','human_review',True)])
def test_carry_method_matrix(foundation,assessment,method,valid):
    g=graph(foundation);g.carry(assessment,method)
    if valid:g.check()
    else:
        with pytest.raises(S02Error):g.check()

@pytest.mark.parametrize('mutation',['origin','from','base','cycle','answers','events','root_target','scope','source','trace_source','evidence_version','no_review','old_application_backlink','missing_source','missing_pairs'])
def test_carry_negative(foundation,mutation):
    g=graph(foundation);q=g.carry(method='human_review' if mutation=='no_review' else 'structural_check',new_model=True);b=q['body'];p=b['resolution_carry']
    if mutation=='origin':p['origin_issue_id']='Q2'
    if mutation=='from':p['from_issue_id']='Q2'
    if mutation=='base':p['base_analysis_set_id']='AS1'
    if mutation=='cycle':p['from_issue_id']=q['id'];b['supersedes_id']=q['id']
    if mutation=='answers':b['answer_ids']=[]
    if mutation=='events':b['resolution_event_refs']=[]
    if mutation=='root_target':
        r=b['resolution_event_refs'][0];g.events[r['command_id'],r['event_id']]['payload']['resolved_issue_id']=q['id']
    if mutation=='scope':p['scope_check']['to_scope']['element_ids'].remove('A2')
    if mutation=='source':p['source_checks'][0]['from_ref']['input_pointer']='/title'
    if mutation=='trace_source':b['trace']['source_refs'][0]['snapshot_id']='missing'
    if mutation=='evidence_version':p['evaluation']['evidence_record_ids']=['Q2']
    if mutation=='no_review':g.reviews.clear()
    if mutation=='old_application_backlink':g.records[p['change_id']]['body']['application_event_refs']=b['resolution_event_refs']
    if mutation=='missing_source':p['source_checks']=[]
    if mutation=='missing_pairs':p['scope_check']['element_pairs']=[]
    with pytest.raises(S02Error):g.check()


def test_undetermined_missing_proof_keeps_blocker(foundation):
    g=graph(foundation);q=g.carry('undetermined');p=q['body']['resolution_carry'];p['source_checks']=[];p['scope_check']['element_pairs']=[];g.check()
    result=permitted_scope(g.records[g.model_id],fullfoot(g.model_id),fullfoot(g.model_id),current_analysis_set_id=g.set_id,reviewed_analysis_set_id=g.set_id,issues=[q],profile=E1)
    assert result['allowed_scope']['mapping_part_ids']==[]
    assert 'BLOCKED_SCOPE' in result['reason_codes']
    q['body']['blocking']['element_ids']=[];q['body']['blocking']['mapping_part_ids']=[]
    with pytest.raises(S02Error):g.check()

@pytest.mark.parametrize('complete',[False,True])
def test_replacement_current_target_and_preserved_key(foundation,complete):
    g=graph(foundation);g.carry('not_applicable','human_review');q,t=g.replacement(complete);g.check()
    assert len(g.records[g.set_id]['body']['issue_ids'])==2
    assert q['body']['issue_key']!=t['body']['issue_key']
    assert sum(e['kind']=='application_applied' for e in g.events.values())==1
    assert q['body']['status']==('resolution_replaced' if complete else 'resolution_pending_revalidation')

@pytest.mark.parametrize('mutation',['pending_target','target_same_key','historic_target','no_review','structural_first','missing_coverage','missing_pairs','no_evidence','narrow_target','old_ref','cycle','drop_key'])
def test_replacement_negative(foundation,mutation):
    g=graph(foundation);g.carry('not_applicable','human_review');q,t=g.replacement(True);p=q['body']['resolution_replacement']
    if mutation=='pending_target':t['body']['status']='open';t['body']['resolution']=None
    if mutation=='target_same_key':t['body']['issue_key']=q['body']['issue_key']
    if mutation=='historic_target':p['replacement_issue_id']='Q2-resolved'
    if mutation=='no_review':g.reviews.pop(q['id'])
    if mutation=='structural_first':p['evaluation']['method']='structural_check'
    if mutation=='missing_coverage':p['obligation_checks']=[]
    if mutation=='missing_pairs':p['scope_check']['element_pairs']=[]
    if mutation=='no_evidence':p['obligation_checks'][0]['evidence_record_ids']=[]
    if mutation=='narrow_target':t['body']['affected']['element_ids']=['A1'];t['body']['affected']['mapping_part_ids']=['P1']
    if mutation=='old_ref':p['obligation_checks'][0]['old_ref']['input_pointer']='/title'
    if mutation=='cycle':p['replacement_issue_id']=q['id']
    if mutation=='drop_key':g.records[g.set_id]['body']['issue_ids']=[t['id']]
    if mutation!='no_review':g.review(q['id'])
    with pytest.raises(S02Error):g.check()


def test_pending_carry_can_be_reviewed_without_second_application(foundation):
    g=graph(foundation);old=g.carry('undetermined');oldbytes=deepcopy(old)
    new=g.carry('applicable','human_review');g.check()
    assert g.records[old['id']]==oldbytes
    assert new['body']['resolution_carry']['origin_issue_id']=='Q2-resolved'
    assert sum(e['kind']=='application_applied' for e in g.events.values())==1


def test_not_applicable_cannot_be_flipped_back(foundation):
    g=graph(foundation);g.carry('not_applicable','human_review');g.carry('applicable','human_review')
    with pytest.raises(S02Error,match='carry_obsolete_requires_replacement'):g.check()

@pytest.mark.parametrize('method,assessment,valid',[('structural_check','undetermined',True),('structural_check','applicable',False),('human_review','applicable',True)])
def test_cross_snapshot_carry_history_refs(foundation,method,assessment,valid):
    from profile_fixtures import observed_graph,source_ref
    g,app,env=observed_graph(foundation,switch=True)
    oldcontext=g.context;oldsid=g.snapshot;g.context='ObservedContext';g.snapshot=env['snapshot']['snapshot_id']
    q=g.carry(assessment,method,new_model=True);p=q['body']['resolution_carry']
    g.records[g.model_id]['body']['source_context_id']=oldcontext
    change=g.records[p['change_id']]['body'];change.update(kind='requirements_switch',new_source_context_id=oldcontext)
    def rebind(v):
        if type(v) is dict:
            if set(v)=={'snapshot_id','input_pointer'}:v['snapshot_id']=oldsid
            else:
                for x in v.values():rebind(x)
        elif type(v) is list:
            for x in v:rebind(x)
    rebind(g.records[g.model_id]);rebind(q['body']['trace'])
    p['source_checks']=[dict(from_ref=source_ref(sid),to_ref=source_ref(oldsid),relation='equal_value',reason='Synthetic explicit correspondence, no pointer retarget') for sid in [g.snapshot,oldsid]]
    for pair in p['scope_check']['element_pairs']:pair['relation']='modified'
    if method=='human_review':g.review(q['id'])
    if valid:g.check()
    else:
        with pytest.raises(S02Error):g.check()
    if valid:
        q['body']['trace']['source_refs'][0]['snapshot_id']=g.snapshot
        with pytest.raises(S02Error):g.check()

@pytest.mark.parametrize('target_pending',[False,True])
def test_replacement_continuation_or_rehold(foundation,target_pending):
    from dacn_s02.scope import make_scope
    g=graph(foundation);g.carry('not_applicable','human_review');old,t=g.replacement(True)
    q=deepcopy(old);q['id']='Replacement-next';q['body']['supersedes_id']=old['id'];p=q['body']['resolution_replacement']
    p.update(from_issue_id=old['id'],base_analysis_set_id=g.set_id)
    p['evaluation']['method']='structural_check';p['evaluation']['evaluator']='dacn-s02/0.2.0a1'
    items=[q];tid=t['id']
    if target_pending:
        nt=deepcopy(t);nt['id']='Target-pending';nt['body'].update(supersedes_id=t['id'],status='open',resolution=None,blocking=fullfoot(g.model_id));items.append(nt);tid=nt['id']
        p.update(replacement_issue_id=tid,assessment='incomplete');q['body'].update(status='resolution_pending_revalidation',blocking=fullfoot(g.model_id))
    g.publish(items,[q['id'],tid]);g.check()
    if target_pending:
        p['assessment']='complete';q['body'].update(status='resolution_replaced',blocking=make_scope(g.model_id))
        with pytest.raises(S02Error):g.check()


def test_replacement_requires_current_task_attestation(foundation):
    from test_repository import validation
    g=graph(foundation)
    g.records['CH1']['body']['reevaluate']=[dict(step=1,scope=fullfoot('M2'),reason='Synthetic analysis remains',status='pending',evidence_record_ids=[])]
    g.carry('not_applicable','human_review');q,t=g.replacement(True);p=q['body']['resolution_replacement']
    with pytest.raises(S02Error,match='replacement_task_attestation'):g.check()
    v=validation(g.records[g.model_id],g.records[g.set_id],'TaskValidation')
    v['body']['completed_change_tasks']=[dict(change_id='CH1',task_index=0,evidence_record_ids=[t['id']])];g.add(v)
    p['evaluation']['evidence_record_ids'].append(v['id']);g.review(q['id']);before=deepcopy(g.kwargs());g.check();assert g.kwargs()==before
    v['body']['completed_change_tasks'][0]['task_index']=1;g.review(q['id'])
    with pytest.raises(S02Error):g.check()


def test_current_issue_ref_is_not_a_history_exception(foundation):
    g=graph(foundation);q=g.carry();q['body']['trace']['issue_ids']=['Q2-resolved']
    with pytest.raises(S02Error,match='analysis_issue_ref_current'):g.check()


def test_full_criterion_inventory_not_just_requirement_parent(foundation):
    # Unit proof oracle: a requirement SourceRef must expand to each criterion.
    from dacn_s02.resolution import source_basis
    g=graph(foundation);snapshots=g.snapshots();snapshots[g.snapshot]['input']['functional_requirements'][0]['acceptance_criteria']=['Criterion A','Criterion B']
    basis,_,_=source_basis(g.records[g.current_issue],g.records,snapshots,g.events)
    assert {(g.snapshot,'/functional_requirements/0'),(g.snapshot,'/functional_requirements/0/acceptance_criteria/0'),(g.snapshot,'/functional_requirements/0/acceptance_criteria/1')}<=basis


def test_unique_application_graph_guard(foundation):
    from dacn_s02.profile_graph import validate_graph
    g=graph(foundation);g.carry();app=deepcopy(next(e for e in g.events.values() if e['kind']=='application_applied'))
    # A second application cannot target a carried Issue; root checks still apply.
    q=g.records[g.current_issue];app['payload']['resolved_issue_id']=q['id'];app['event_id']='duplicate';app['ordinal']=99
    g.events[app['command_id'],'duplicate']=app
    with pytest.raises(S02Error):g.check()


def test_removed_obligation_requires_changed_source_and_review(foundation):
    from profile_fixtures import observed_graph,source_ref
    g,_,env=observed_graph(foundation,switch=True,change_text=True)
    original_context=g.context;current_sid=g.snapshot;historical_sid=env['snapshot']['snapshot_id']
    g.context='ObservedContext';g.snapshot=historical_sid
    old=g.carry('not_applicable','human_review',new_model=True);cp=old['body']['resolution_carry']
    g.records[g.model_id]['body']['source_context_id']=original_context
    g.records[cp['change_id']]['body'].update(kind='requirements_switch',new_source_context_id=original_context)
    def rebind(v):
        if type(v) is dict:
            if set(v)=={'snapshot_id','input_pointer'}:v['snapshot_id']=current_sid
            else:
                for x in v.values():rebind(x)
        elif type(v) is list:
            for x in v:rebind(x)
    rebind(g.records[g.model_id]);rebind(old['body']['trace'])
    cp['source_checks']=[dict(from_ref=source_ref(sid),to_ref=source_ref(current_sid),relation='changed' if sid==historical_sid else 'equal_value',reason='Synthetic explicit changed source') for sid in [historical_sid,current_sid]]
    for pair in cp['scope_check']['element_pairs']:pair['relation']='modified'
    g.review(old['id']);g.context=original_context;g.snapshot=current_sid
    q,t=g.replacement(True);p=q['body']['resolution_replacement']
    p['obligation_checks'].append(dict(old_ref=source_ref(historical_sid),current_ref=None,disposition='removed',evidence_record_ids=[t['id']],reason='Synthetic human reviewed removal at source revision'))
    g.review(q['id']);g.check()
    p['evaluation']['method']='structural_check'
    with pytest.raises(S02Error):g.check()


def test_direct_root_cannot_use_prepared_event(foundation):
    g=graph(foundation);q=g.carry();root=g.records['Q2-resolved'];ref=root['body']['resolution_event_refs'][0]
    e=g.events[ref['command_id'],ref['event_id']];e.update(kind='prepared',payload=dict(stage_refs=[],attempt_id=None))
    with pytest.raises(S02Error):g.check()


def test_same_model_set_fork_rejected(foundation):
    g=graph(foundation);oldset=g.set_id;oldissue=g.current_issue;g.carry()
    g.set_id=oldset;g.current_issue=oldissue;g.carry()
    with pytest.raises(S02Error,match='graph_set_linearity'):g.check()


def test_model_switch_cannot_skip_existing_base_set(foundation):
    g=graph(foundation);oldset=g.set_id;oldissue=g.current_issue;g.carry()
    g.set_id=oldset;g.current_issue=oldissue;g.carry(new_model=True)
    with pytest.raises(S02Error,match='graph_model_switch_final_base_set'):g.check()
