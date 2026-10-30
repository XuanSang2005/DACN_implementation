from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import pytest
from dacn_s02.codec_boundary import encode
from dacn_s02.errors import S02Error
from dacn_s02.h3_limits import Budget
from dacn_s02.h3_history import ReviewRegistry,project_current_refs
from dacn_s02.h3_policy import admit,materialize_hold,retained_output,transition
from h3_fixtures import setup,view,data,control,selector_rows,bind_work,multi_setup,add_other_session_human_history


def test_whole_store_registry_includes_another_session_not_only_command(foundation):
    g=setup(foundation);g.carry('applicable','human_review');mapping=add_other_session_human_history(g)
    b=Budget();raw,t=control(g);r=ReviewRegistry.parse(raw,t,b);h=data(g,b,r)
    assert set(r.reviews())=={g.current_issue,mapping[g.current_issue]}
    h.view(g.session,[g.model_id,g.set_id],[g.model_id,g.set_id])
    v=r.payload();v['required_issue_ids']=[g.current_issue];v['reviews']=[e for e in v['reviews'] if e['issue_id']==g.current_issue]
    raw=encode(v)
    with pytest.raises(S02Error):
        budget=Budget();data(g,budget,ReviewRegistry.parse(raw,replace(t,expected_sha256=sha256(raw).hexdigest()),budget))


def test_direct_answer_history_and_independent_output_with_u_hold(tmp_path,monkeypatch):
    g=multi_setup(tmp_path,monkeypatch,held=True);v=view(g);rows=selector_rows(v)
    second=next(f.unit_id for f in v.context.source.families if f.pointer=='/functional_requirements/1')
    first=next(f.unit_id for f in v.context.source.families if f.pointer=='/functional_requirements/0')
    work=bind_work(v,rows,mode='revalidate');before=deepcopy(g.kwargs());result=admit(v,rows,*work[:4],candidate_raw=work[4])
    assert result.allowed_units==(second,) and result.blocked_units==(first,) and result.global_blocked
    assert g.kwargs()==before
    assert v.context.body['responsibilities'][1]['component_id']=='C1'
    assert sum(e['kind']=='application_applied' for e in g.events.values())==1


@pytest.mark.parametrize('mutation',['missing_inspection','wrong_snapshot','missing_independence','not_inspected'])
def test_source_and_semantic_proof_negative_controls(tmp_path,monkeypatch,mutation):
    g=multi_setup(tmp_path,monkeypatch,held=True);v=view(g);rows=selector_rows(v)
    second=next(f.unit_id for f in v.context.source.families if f.pointer=='/functional_requirements/1')
    def change(e):
        if mutation=='missing_inspection':e['inspections'].pop()
        if mutation=='wrong_snapshot':e['inspections'][0]['source_ref']['snapshot_id']='Wrong'
        if mutation=='missing_independence':e['independence']=[]
        if mutation=='not_inspected':e['inspections'][0].update(read='not_inspected',verdict='held')
    if mutation in ('missing_inspection','wrong_snapshot'):
        with pytest.raises(S02Error):
            w=bind_work(v,rows,selected=[second],analysis_change=change);admit(v,rows,*w[:4],candidate_raw=w[4])
    else:
        w=bind_work(v,rows,selected=[second],analysis_change=change);result=admit(v,rows,*w[:4],candidate_raw=w[4])
        assert result.allowed_units==() and second in result.blocked_units


def test_unknown_source_hold_survives_empty_graph_and_growth():
    from h2_fixtures import graph,snapshot,current_issue,R0,HASH
    from dacn_s02.h2_contracts import SourceInventory
    from dacn_s02.h2_graph import ModelContext
    b=Budget();src=SourceInventory(snapshot(),'SRC',HASH,b)
    empty=ModelContext(graph(skeleton=True),src,b);q=current_issue(empty.model(),elements=(),parts=())
    row=dict(issue_id=q['id'],issue_key=q['body']['issue_key'],target_step=1,kind='all_source_uses',
        source_refs=deepcopy(q['body']['trace']['source_refs']),element_ids=[],mapping_part_ids=[],impact_known=False,code_task_role=None)
    first=materialize_hold(empty,row,q);assert first.elements=={'Actor'} and not first.actions and not first.parts
    grown=ModelContext(graph(),src,b);second=materialize_hold(grown,row,q)
    assert second.actions=={'A1','A2'} and second.parts=={'P1','PCriterion','P2','PN','PC'}


def test_retention_checks_part_row_source_context_not_only_part_payload(tmp_path,monkeypatch):
    g=multi_setup(tmp_path,monkeypatch);b=Budget();before=view(g,b)
    second=next(f.unit_id for f in before.context.source.families if f.pointer=='/functional_requirements/1')
    q=g.carry('undetermined',new_model=True);p=q['body']['resolution_carry'];p['source_checks']=[]
    # Explicit complete footprint for this handwritten four-Part topology.
    elements=['A1','A2','W1','W2','C1','C2','RS1','RS2'];parts=['P1','PC0','P2','PC1'];old=before.pair[0];new=g.model_id
    p['scope_check'].update(from_scope=dict(model_id=old,element_ids=elements,mapping_part_ids=parts),
        to_scope=dict(model_id=new,element_ids=elements,mapping_part_ids=parts),
        element_pairs=[dict(**{'from':dict(model_id=old,element_id=i),'to':dict(model_id=new,element_id=i)},relation='unchanged',reason='Explicit same payload, context must still be checked') for i in elements+parts])
    q['body']['affected']=deepcopy(p['scope_check']['to_scope']);q['body']['blocking']=deepcopy(q['body']['affected'])
    rows=g.records[new]['body']['mappings'];old_parts=deepcopy([r['parts'] for r in rows]);rows[0]['source_ref'],rows[2]['source_ref']=rows[2]['source_ref'],rows[0]['source_ref']
    after=view(g,b);r=retained_output(before,after,second)
    assert [x['parts'] for x in rows]==old_parts
    assert r['state']=='needs_revalidation' and r['work_completed_through'] is None
    with pytest.raises(S02Error,match='retained_row_source'):transition(before,after,step=4,unit_ids=list(before.context.source.units))


def test_application_count_and_source_only_pending_answer_mixed_history(foundation):
    from helpers import issue
    from dacn_s02.repository import record
    from dacn_s02.scope import make_scope
    g=setup(foundation);g.carry();g.carry('undetermined');g.carry('not_applicable','human_review');g.replacement(False,method='structural_check')
    m=g.records[g.model_id];pending=issue(m,'PendingAnswerIssue',key='PendingAnswerKey',status='answered_pending_application')
    pending['body'].update(answer_ids=['PendingAnswer'],resolution_carry=None,resolution_replacement=None)
    answer=record('answer','PendingAnswer',dict(issue_id=pending['id'],supersedes_answer_id=None,respondent='SYNTHETIC',recorded_by='Fixture controller',text='Existing synthetic pending answer',interpretation='points_to_existing_source',existing_source_refs=deepcopy(pending['body']['trace']['source_refs'])))
    direct=issue(m,'SourceOnly',key='SourceOnlyKey',status='resolved');direct['body'].update(resolution='Fixture source-only historical resolution',blocking=make_scope(g.model_id),resolution_carry=None,resolution_replacement=None)
    selected=list(g.records[g.set_id]['body']['issue_ids']);g.publish([pending,answer,direct],selected+[pending['id'],direct['id']])
    v=view(g);assert {v.projection(k)['branch'] for k in ('Question2','NewDecision','PendingAnswerKey','SourceOnlyKey')}=={'DIRECT','REPLACEMENT'}
    assert v.projection('Question2')['blocks'] and v.projection('PendingAnswerKey')['blocks']
    assert not v.projection('SourceOnlyKey')['blocks']
    assert sum(e['kind']=='application_applied' for e in g.events.values())==1
    assert 'PendingAnswer' not in {e['payload']['answer_id'] for e in g.events.values() if e['kind']=='application_applied'}


def test_h3_does_not_allow_new_human_decisions_in_transition(foundation):
    g=setup(foundation);b=Budget();before=view(g,b);g.carry('applicable','human_review')
    # A new registry may verify a new graph, but it cannot rebind a pending H3
    # command or authorize a new decision as an H3-A transition.
    after=view(g,Budget())
    with pytest.raises(S02Error):transition(before,after)


def test_fabricated_progress_dictionary_is_not_provenance(foundation):
    g=setup(foundation);v=view(g);rows=selector_rows(v);w=bind_work(v,rows,step=2)
    fake={u:dict(work_completed_through=1,outputs=[],actual_output_ids=[],assessment_state='current',unresolved_keys=[],next_tasks=[2],latest_checked_pair=None,assessment=None) for u in v.context.source.units}
    with pytest.raises(S02Error,match='progress_provenance_required'):admit(v,rows,*w[:4],candidate_raw=w[4],progress=fake)


def test_existing_cross_snapshot_human_proof_is_history_not_new_decision(foundation):
    from profile_fixtures import observed_graph,source_ref
    from h3_fixtures import e1
    g,_,observed=observed_graph(foundation,switch=True);e1(g)
    old_sid=g.snapshot;g.context='ObservedContext';g.snapshot=observed['snapshot']['snapshot_id']
    q=g.carry('applicable','human_review');q['body']['resolution_carry']['source_checks']=[
        dict(from_ref=source_ref(sid),to_ref=source_ref(g.snapshot),relation='equal_value',reason='Explicit synthetic historical correspondence') for sid in (old_sid,g.snapshot)]
    g.review(q['id']);v=view(g);p=v.projection('Question2')
    assert p['status']=='resolved' and p['branch']=='CARRY'
    assert {r['snapshot_id'] for r in p['source_basis']}=={old_sid,g.snapshot}
    before=deepcopy(q['body']['resolution_carry']['source_checks']);projected=project_current_refs(q,'ProposedModel',{},Budget())
    assert projected['resolution_carry']['source_checks']==before
    assert sum(e['kind']=='application_applied' for e in g.events.values())==1


def test_pending_predecessor_cannot_be_structurally_released(foundation):
    g=setup(foundation);g.carry('undetermined');g.carry('applicable')
    with pytest.raises(S02Error,match='carry_structural_proof'):data(g)


def test_replacement_incomplete_transition_uses_preexisting_target_key(foundation):
    from helpers import issue
    from dacn_s02.scope import make_scope
    g=setup(foundation);g.carry('not_applicable','human_review')
    target=issue(g.records[g.model_id],'ExistingTarget',key='NewDecision',status='resolved',blocked=['A1','A2','W1','W2','C1','C2','RS1','RS2'],parts=['P1','P12','P2'])
    target['body'].update(kind='analysis_omission',resolution='Synthetic current source resolves the new obligation',resolution_carry=None,resolution_replacement=None,blocking=make_scope(g.model_id))
    g.publish([target],[g.current_issue,target['id']]);b=Budget();before=view(g,b)
    q,t=g.replacement(False,method='structural_check');t['body']['supersedes_id']=target['id'];after=view(g,b)
    result=transition(before,after)
    old=next(x for x in result if x['issue_key']=='Question2')
    assert old['branch']=='REPLACEMENT' and old['assessment']=='incomplete' and old['blocks']
    assert old['replacement_issue_id']==t['id'] and old['origin_issue_id']=='Q2-resolved'


def test_first_replacement_or_new_target_creation_is_not_h3_continuation(foundation):
    g=setup(foundation);g.carry('not_applicable','human_review');b=Budget();before=view(g,b)
    g.replacement(False,method='structural_check');after=view(g,b)
    with pytest.raises(S02Error,match='no_new_replacement_target_key'):transition(before,after)


def test_replacement_complete_needs_existing_task_evidence(foundation):
    from profile_fixtures import fullfoot
    g=setup(foundation);g.records['CH1']['body']['reevaluate']=[dict(step=1,scope=fullfoot('M2'),reason='Synthetic pending reevaluation',status='pending',evidence_record_ids=[])]
    g.carry('not_applicable','human_review');g.replacement(True)
    with pytest.raises(S02Error,match='replacement_task_attestation'):data(g)


def test_real_existing_h2_anchor_is_purely_checked_without_new_h3_io(tmp_path):
    from h2_checkpoint_fixtures import ScopedCase
    from dacn_s02.h3_history import ReviewTrustContext,ReviewRegistry,HistoryData
    from dacn_s02.h3_bindings import check_anchor
    from dacn_s02.h3_contracts import REGISTRY,ANCHOR
    case=ScopedCase(tmp_path);case.bootstrap();case.advance(1)
    with case.repo._read() as c:
        records,blobs,commands,events,stages=case.repo._check(c)
        owners={row['id']:row['session_id'] for row in c.execute('SELECT id,session_id FROM records')}
        record_profiles={row['id']:row['profile_id'] for row in c.execute('SELECT id,profile_id FROM records')}
        operation_profiles={row['command_id']:row['profile_id'] for row in c.execute('SELECT command_id,profile_id FROM operations')}
    raw=encode(dict(format=REGISTRY,purpose='synthetic_historical_evidence_only',registry_id='Empty',store_id=case.store_id,required_issue_ids=[],reviews=[]))
    trust=ReviewTrustContext('external-registry.json',sha256(raw).hexdigest(),'Empty',case.store_id);b=Budget()
    h=HistoryData(records=records,record_profiles=record_profiles,owners=owners,commands=commands,operation_profiles=operation_profiles,
        events=events,stages=stages,blobs=blobs,registry=ReviewRegistry.parse(raw,trust,b),store_id=case.store_id,budget=b)
    session=commands[case.parent]['session_id'];v=h.view(session,case.pair,case.pair)
    final=next(e for (cmd,_),e in events.items() if cmd==case.parent and e['kind']=='finalized')
    plan_id=next(p['artifact_id'] for p in final['payload']['promotions'] if records[p['artifact_id']]['body']['purpose']=='config' and p['artifact_id']!=records[commands[case.parent]['reserved_run_id']]['body']['config_artifact_id'])
    from dacn_s02.codec_boundary import decode
    plan=decode(blobs[plan_id]);origin=plan['admission']['progress_by_unit'][case.v]['outputs']['1']
    anchor=dict(version=ANCHOR,command_id=case.parent,plan_artifact_id=plan_id,plan_sha256=sha256(blobs[plan_id]).hexdigest(),
        published_pair=case.pair,source_context_id=v.context.source.context_id,snapshot_id=v.context.source.snapshot_id,transitions=[],transition_hashes=[],
        outputs=[dict(unit_id=case.v,step=1,origin_command_id=case.parent,output_ids=origin['local_ids'],raw_sha256=origin['raw_sha256'],source_refs=origin['source_refs'],aliases=origin['aliases'])])
    proof=check_anchor(anchor,v)
    assert proof.payload()[case.v]['work_completed_through']==1
    assert proof.payload()[case.u]['work_completed_through']==0
    assert proof.payload()[case.v]['outputs'][0]['raw_sha256']==origin['raw_sha256']
    bad=deepcopy(anchor);bad['outputs'][0]['raw_sha256']='0'*64
    with pytest.raises(S02Error):check_anchor(bad,v)


def test_hold_cannot_be_delayed_or_exempted_by_a_fake_construction_role(foundation):
    g=setup(foundation);g.carry('undetermined');v=view(g);rows=selector_rows(v)
    rows[0].update(target_step=4,code_task_role='global_mapping')
    with pytest.raises(S02Error,match='hold_target_requires_task_origin'):
        w=bind_work(v,rows);admit(v,rows,*w[:4],candidate_raw=w[4])


def test_existing_h2_task_and_guard_provenance_is_not_a_role_string(tmp_path):
    from h2_checkpoint_fixtures import ScopedCase
    from dacn_s02.h3_bindings import verify_task_origin,verify_guard_origin
    from dacn_s02.h3_history import HistoryData,ReviewRegistry,ReviewTrustContext
    from dacn_s02.h3_contracts import REGISTRY
    from dacn_s02.codec_boundary import decode
    case=ScopedCase(tmp_path);case.bootstrap();case.advance(1);case.advance(2,proof=False)
    with case.repo._read() as c:
        records,blobs,commands,events,stages=case.repo._check(c)
        owners={x['id']:x['session_id'] for x in c.execute('SELECT id,session_id FROM records')}
        profiles={x['id']:x['profile_id'] for x in c.execute('SELECT id,profile_id FROM records')}
        op_profiles={x['command_id']:x['profile_id'] for x in c.execute('SELECT command_id,profile_id FROM operations')}
    raw=encode(dict(format=REGISTRY,purpose='synthetic_historical_evidence_only',registry_id='Empty',store_id=case.store_id,required_issue_ids=[],reviews=[]))
    b=Budget();reg=ReviewRegistry.parse(raw,ReviewTrustContext('external-control.json',sha256(raw).hexdigest(),'Empty',case.store_id),b)
    h=HistoryData(records=records,record_profiles=profiles,owners=owners,commands=commands,operation_profiles=op_profiles,events=events,stages=stages,blobs=blobs,registry=reg,store_id=case.store_id,budget=b)
    v=h.view(commands[case.parent]['session_id'],case.pair,case.pair)
    def origin_hash(cmd):
        final=next(e for (c,_),e in events.items() if c==cmd and e['kind']=='finalized')
        return next(records[p['artifact_id']]['body']['sha256'] for p in final['payload']['promotions'] if records[p['artifact_id']]['body']['purpose']=='config' and p['artifact_id']!=records[commands[cmd]['reserved_run_id']]['body']['config_artifact_id'])
    key,task=next(iter(case.meta['tasks'].items()));task={**deepcopy(task),'issue_key':key,'issue_id':v.issue(key)['id'],'origin_plan_sha256':origin_hash(task['origin_command_id'])}
    assert verify_task_origin(task,v)==task
    key,guard=next(iter(case.meta['guards'].items()))
    g=dict(issue_key=key,issue_id=v.issue(key)['id'],origin_command_id=guard['origin_command_id'],root_issue_id=guard['root_issue_id'],
        source_context_id=v.context.source.context_id,base_pair=guard['base_pair'],failed_candidate_sha256=guard['candidate_sha256'],
        failed_analysis_sha256=guard['analysis_sha256'],predicate=guard['predicate'],origin_plan_sha256=origin_hash(guard['origin_command_id']))
    assert verify_guard_origin(g,v)==g
    fake=deepcopy(task);fake['predicate']='pretend_completeness'
    with pytest.raises(S02Error):verify_task_origin(fake,v)
    fake=deepcopy(g);fake['failed_candidate_sha256']='0'*64
    with pytest.raises(S02Error):verify_guard_origin(fake,v)
