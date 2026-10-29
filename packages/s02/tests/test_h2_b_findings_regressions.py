"""H2-B audit 01/02 regressions; expected effects come from handwritten fixtures."""
from copy import deepcopy
from dataclasses import replace
import pytest
from h2_checkpoint_fixtures import ScopedCase
from test_h2_checkpoint_processes import final
from h2_fixtures import context,current_issue,unit,R0,R1,HASH,trace
from dacn_s02.h2_checkpoint import selector,selectors,blocking_keys
from dacn_s02.h2_contracts import ConstructionPermit
from dacn_s02.h2_limits import digest
from dacn_s02.h2_policy import _building_task
from dacn_s02.h2_service import H2Service


def usable(candidate,analysis):
    if candidate:
        for row in candidate['inspection']:row.update(verdict='usable',needed_facts=[])
        candidate['proposals']['findings']=[];candidate['questions']=[];candidate['unrepresented_source_refs']=[]
    for row in analysis['inspections']:row.update(verdict='usable',needed_facts=[])
    for row in analysis['independence']:row['verdict']='independent'


def actions(case):
    def change(candidate,analysis):
        usable(candidate,analysis)
        row=deepcopy(candidate['proposals']['actions'][0])
        row.update(handle='u-action',name='U operation',trace=case.tr('/functional_requirements/0'))
        candidate['proposals']['actions'].append(row)
    return change


def responsibilities(case,units):
    def change(candidate,analysis):
        usable(candidate,analysis);aliases={v['id']:h for h,v in case.aliases().items()}
        by_source={a['trace']['source_refs'][0]['input_pointer']:a for a in case.last['result']['model']['body']['actions']}
        component=deepcopy(candidate['proposals']['components'][0]);responsibility=deepcopy(candidate['proposals']['responsibilities'][0])
        candidate['proposals']['components']=[];candidate['proposals']['responsibilities']=[]
        for i,u in enumerate(units):
            ptr='/functional_requirements/'+('0' if u==case.u else '1')
            co=deepcopy(component);co.update(handle='component-'+str(i),trace=case.tr(ptr))
            re=deepcopy(responsibility);re.update(handle='responsibility-'+str(i),component_id={'local_handle':co['handle']},action_ids=[{'base_handle':aliases[by_source[ptr]['id']]}],trace=case.tr(ptr))
            candidate['proposals']['components'].append(co);candidate['proposals']['responsibilities'].append(re)
    return change


@pytest.mark.parametrize('step',[2,4])
def test_new_cross_source_blocker_leaves_no_domain_records_or_completed_work(tmp_path,step):
    c=ScopedCase(tmp_path);c.bootstrap()
    for prior in range(1,step):assert c.advance(prior,change=usable)['result']['candidate_outcome']=='valid'
    base=deepcopy(c.last['result']['model']);pair=c.pair[:];outputs=deepcopy(c.meta['progress_by_unit'][c.v]['outputs'])
    def block(candidate,analysis):
        usable(candidate,analysis)
        handle='view' if step==2 else candidate['proposals']['mappings'][0]['parts'][0]['handle']
        candidate['proposals']['findings']=[dict(handle='cross-source',kind='business',question='U blocks V',reason='Explicit V physical blocker with U provenance',trace=c.tr('/functional_requirements/0'),affected_refs=[{'local_handle':handle}],blocking_refs=[{'local_handle':handle}],impact_known=True)]
    r=c.advance(step,change=block);view,plan=final(c,r['command_id'])
    assert r['result']['candidate_outcome']=='guard_only' and c.pair[0]==pair[0] and c.pair[1]!=pair[1]
    assert c.last['result']['model']==base
    assert c.meta['progress_by_unit'][c.v]['work_completed_through']==step-1
    assert c.meta['progress_by_unit'][c.v]['outputs']==outputs
    assert not any(x['type'] in ('model','change') for x in plan['batch']['records'])
    assert any(q['body']['issue_key'] in c.meta['guards'] for q in r['result']['issues'])
    assert H2Service(c.repo).resume(r['command_id'])==r
    assert view['current_head']==c.pair


def test_affected_context_without_physical_blocker_does_not_blanket_block_v(tmp_path):
    c=ScopedCase(tmp_path);c.bootstrap();c.advance(1,change=usable)
    def context_only(candidate,analysis):
        usable(candidate,analysis)
        candidate['proposals']['findings']=[dict(handle='u-context',kind='business',question='U fact remains open',reason='V is affected context, not a blocking use',trace=c.tr('/functional_requirements/0'),affected_refs=[{'local_handle':'view'}],blocking_refs=[],impact_known=True)]
    r=c.advance(2,change=context_only)
    assert r['result']['candidate_outcome']=='valid'
    assert c.meta['progress_by_unit'][c.v]['work_completed_through']==2
    assert c.meta['progress_by_unit'][c.v]['assessment_state']=='current'
    assert c.meta['progress_by_unit'][c.u]['assessment_state']=='assessed_held'
    c.repo.verify()


@pytest.mark.parametrize('step',[3,4])
def test_independent_batch_has_one_model_change_and_keeps_other_construction_tasks(tmp_path,step):
    c=ScopedCase(tmp_path);c.bootstrap();c.advance(1,change=usable);c.advance(2,units=[c.u,c.v],change=actions(c))
    if step==4:
        c.advance(3,units=[c.u,c.v],change=responsibilities(c,[c.u,c.v]))
    base=deepcopy(c.last['result']['model']);before=c.pair[:]
    def mappings(candidate,analysis):
        usable(candidate,analysis);aliases={v['id']:h for h,v in c.aliases().items()}
        by_source={a['trace']['source_refs'][0]['input_pointer']:a['id'] for a in base['body']['actions']}
        by_action={a:r['id'] for r in base['body']['responsibilities'] for a in r['action_ids']}
        for row in candidate['proposals']['mappings']:
            family='/'.join(row['source_ref']['input_pointer'].split('/')[:3]);aid=by_source[family]
            for part in row['parts']:part.update(action_ids=[{'base_handle':aliases[aid]}],primary_responsibility_ids=[{'base_handle':aliases[by_action[aid]]}])
    r=c.advance(step,units=[c.u,c.v],change=responsibilities(c,[c.u,c.v]) if step==3 else mappings)
    view,plan=final(c,r['command_id']);model=r['result']['model']
    assert r['result']['candidate_outcome']=='valid' and model['body']['parent_model_id']==before[0]
    assert model['body']['revision']==base['body']['revision']+1
    assert sum(x['type']=='model' for x in plan['batch']['records'])==1
    assert sum(x['type']=='change' for x in plan['batch']['records'])==1
    assert all(c.meta['progress_by_unit'][u]['work_completed_through']==step for u in (c.u,c.v))
    for q in r['result']['issues']:
        task=c.meta['tasks'].get(q['body']['issue_key'])
        if not task:continue
        if task['role']=='global_mapping':assert q['body']['status']=='open'
        elif int(task['target_step'])==step:
            assert q['body']['status']==('resolved' if set(task['unit_ids'])<={c.u,c.v} else 'open')
    assert view['current_head']==c.pair


@pytest.mark.parametrize('mutation',['foreign-unit','wrong-step','wrong-role','wrong-key','business','gap','guard'])
def test_batch_exemption_is_only_the_matching_code_task(mutation):
    ctx=context();u=unit(ctx,R1);v=unit(ctx,R0);units=frozenset([u,v])
    key='h2.construct.'+digest(['Cmd',[u],3,'await_builder'])
    q=current_issue(ctx.model(),key=key,kind='verification');q['body']['trace']=trace('SNAP',R1)
    s=selector(q,ctx.source,role='await_builder',target=3)
    p=ConstructionPermit(q['id'],key,'Cmd','Run',HASH,frozenset([u]),3,'await_builder')
    assert _building_task(p,q,s,units,3)
    if mutation=='foreign-unit':units=frozenset([v])
    elif mutation=='wrong-step':p=replace(p,target_step=2)
    elif mutation=='wrong-role':s=replace(s,code_task_role='global_mapping')
    elif mutation=='wrong-key':q['body']['issue_key']='other-key'
    else:q['body']['kind']='business' if mutation=='business' else 'analysis_omission'
    assert not _building_task(p,q,s,units,3)


@pytest.mark.parametrize('physical',['action','part','source-only'])
def test_progress_blockers_follow_physical_closure_beyond_source_provenance(physical):
    ctx=context();u=unit(ctx,R0);v=unit(ctx,R1)
    q=current_issue(ctx.model(),elements=('A2',) if physical=='action' else (),parts=('P2',) if physical=='part' else ())
    s=selector(q,ctx.source)
    result=blocking_keys(ctx,[q],[s],[u,v])
    assert result[u]==[q['body']['issue_key']]
    assert result[v]==([] if physical=='source-only' else [q['body']['issue_key']])


def test_derived_result_selectors_keep_input_counters_and_bounds_separate():
    ctx=context();q=current_issue(ctx.model());s=selector(q,ctx.source)
    meta={'selectors':{s.issue_key:s.payload(ctx.source)}}
    assert selectors(meta,[q],ctx.source,ctx.budget)==(s,)
    before=ctx.budget.input_values,ctx.budget.input_refs
    assert selectors(meta,[q],ctx.source,ctx.budget,derived=True)==(s,)
    assert before==(ctx.budget.input_values,ctx.budget.input_refs)
