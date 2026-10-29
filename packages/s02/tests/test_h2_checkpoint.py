from h2_checkpoint_fixtures import ScopedCase
from dacn_s02.h2_service import H2Service


def test_scoped_u_held_v_to_four(tmp_path):
    case=ScopedCase(tmp_path);case.bootstrap()
    one=case.advance(1);assert one['status']=='blocked',one
    for step in (2,3,4):
        result=case.advance(step)
        assert result['status']=='blocked',result
        assert result['result']['progress_by_unit'][case.v]['work_completed_through']==step,result
    report=H2Service(case.repo).report(case.parent,progress=True)
    assert report['status']=='completed'
    assert report['result']['progress_by_unit'][case.u]['work_completed_through']==1
    model=report['result']['model'];rows=model['body']['mappings']
    assert len(rows)==8
    assert all(r['assessment']=='not_assessed' for r in rows if r['source_ref']['input_pointer'].startswith('/functional_requirements/0'))
    assert all(r['assessment']=='proposed' and len(r['parts'])==1 for r in rows if r['source_ref']['input_pointer'].startswith('/functional_requirements/1'))
    assert any(q['body']['status']=='open' and q['body']['kind']=='business' for q in report['result']['issues'])
    assert all(q['body']['status']=='open' for q in report['result']['issues'] if q['body']['issue_key'] in case.meta['tasks'] and case.meta['tasks'][q['body']['issue_key']]['role']=='global_mapping')
    assert H2Service(case.repo).resume(case.parent)['status']=='blocked'
    case.repo.verify()


def test_guard_missing_proof_then_resolution_new_command(tmp_path):
    case=ScopedCase(tmp_path);case.bootstrap();case.advance(1)
    model=case.pair[0]
    blocked=case.advance(2,proof=False)
    assert blocked['result']['candidate_outcome']=='guard_only',blocked
    assert case.pair[0]==model
    assert case.meta['progress_by_unit'][case.v]['work_completed_through']==1
    guards=list(case.meta['guards']);assert len(guards)==1
    business=next(q for q in case.last['result']['issues'] if q['body']['kind']=='business')
    missing=case.advance(2,mode='revalidate',goal='admission',guards=guards,proof=False)
    assert missing['result']['candidate_outcome']=='revalidated',missing
    assert next(q for q in missing['result']['issues'] if q['body']['issue_key']==guards[0])['body']['status']=='open'
    assert next(q for q in missing['result']['issues'] if q['id']==business['id'])==business
    cleared=case.advance(2,mode='revalidate',goal='admission',guards=guards)
    assert cleared['result']['candidate_outcome']=='revalidated',cleared
    assert next(q for q in cleared['result']['issues'] if q['body']['issue_key']==guards[0])['body']['status']=='resolved'
    assert case.pair[0]==model
    assert case.meta['progress_by_unit'][case.v]['work_completed_through']==1
    result=case.advance(2)
    assert result['result']['progress_by_unit'][case.v]['work_completed_through']==2,result
    assert case.pair[0]!=model
    assert H2Service(case.repo).resume(blocked['command_id'])['result']['result_pair'][0]==model
    case.repo.verify()


def test_provider_deny_absence_restart_and_finalized_history(tmp_path):
    import pytest
    from uuid import uuid4
    from dacn_s02.errors import S02Error
    case=ScopedCase(tmp_path);case.bootstrap()
    work,denied=case.work(1,decision='deny');cmd=str(uuid4())
    with pytest.raises(S02Error) as exc:H2Service(case.repo,authority=denied).prepare(cmd,case.parent,store_id=case.store_id,**work)
    assert exc.value.error['code']=='H2_AUTHORITY_DENIED'
    assert case.repo.lookup_command(cmd) is None
    work,authority=case.work(1);service=H2Service(case.repo,authority=authority)
    service.prepare(cmd,case.parent,store_id=case.store_id,**work)
    before=case.repo.lookup_command(cmd)
    with pytest.raises(S02Error):H2Service(case.repo).resume(cmd)
    assert case.repo.lookup_command(cmd)==before
    original=authority.path.read_bytes();authority.path.write_bytes(original+b' ')
    with pytest.raises(S02Error):service.resume(cmd)
    assert case.repo.lookup_command(cmd)==before
    authority.path.write_bytes(original)
    result=service.resume(cmd);assert result['status']=='blocked',result
    authority.path.unlink()
    assert H2Service(case.repo).resume(cmd)==result
    assert H2Service(case.repo).report(cmd,progress=True)['result']['eligibility_authorized_in_process'] is False


def test_sealed_plan_preserved_when_provider_disappears(tmp_path):
    import pytest
    from uuid import uuid4
    from dacn_s02.errors import S02Error
    case=ScopedCase(tmp_path);case.bootstrap();work,authority=case.work(1);cmd=str(uuid4())
    class Stop(Exception):pass
    def stop(point):
        if point=='after_seal':raise Stop()
    service=H2Service(case.repo,authority=authority,_hook=stop)
    service.prepare(cmd,case.parent,store_id=case.store_id,**work)
    with pytest.raises(Stop):service.resume(cmd)
    before=case.repo.lookup_command(cmd)
    with pytest.raises(S02Error):H2Service(case.repo).resume(cmd)
    assert case.repo.lookup_command(cmd)==before
    result=H2Service(case.repo,authority=authority).resume(cmd)
    assert result['status']=='blocked',result
    assert result['result']['run_id']==before['operation']['reserved_run_id']


def test_stale_as_only_cas_preserves_planned_domain_ids(tmp_path):
    from uuid import uuid4
    case=ScopedCase(tmp_path);case.bootstrap()
    work,authority=case.work(1)
    a,b=str(uuid4()),str(uuid4());service=H2Service(case.repo,authority=authority)
    service.prepare(a,case.parent,store_id=case.store_id,**work);service.prepare(b,case.parent,store_id=case.store_id,**work)
    first=service.resume(a);second=service.resume(b)
    assert first['status']=='blocked',first
    assert second['status']=='stale',second
    assert second['result']['result_pair'] is None
    assert case.repo.lookup_command(b)['run']['body']['result_analysis_set_id'] is None
    case.repo.verify()


def test_retained_output_guard_revalidation_and_domain_edit_limit(tmp_path):
    case=ScopedCase(tmp_path);case.bootstrap();case.advance(1);case.advance(2);case.advance(3)
    original=case.last['result']['model'];outputs=case.meta['progress_by_unit'][case.v]['outputs'].copy()
    guarded=case.advance(4,proof=False)
    assert guarded['result']['candidate_outcome']=='guard_only'
    guards=list(case.meta['guards'])
    result=case.advance(3,mode='revalidate',goal='retained_output',guards=guards)
    assert result['result']['candidate_outcome']=='revalidated',result
    assert result['result']['model']==original
    assert result['result']['progress_by_unit'][case.v]['outputs']==outputs
    assert result['result']['progress_by_unit'][case.v]['work_completed_through']==3
    result=case.advance(4)
    assert result['result']['progress_by_unit'][case.v]['work_completed_through']==4,result


def test_revalidate_never_resolves_business_or_global_task(tmp_path):
    import pytest
    from dacn_s02.errors import S02Error
    case=ScopedCase(tmp_path);case.bootstrap();case.advance(1)
    for key in [next(q['body']['issue_key'] for q in case.last['result']['issues'] if q['body']['kind']=='business'),next(iter(case.meta['tasks']))]:
        with pytest.raises(S02Error):case.work(2,mode='revalidate',goal='admission',guards=[key])


def test_new_hold_in_union_never_publishes_partial_candidate(tmp_path):
    from copy import deepcopy
    case=ScopedCase(tmp_path);case.bootstrap()
    def clear_u(candidate,analysis):
        for row in candidate['inspection']:
            row.update(verdict='usable',needed_facts=[])
        candidate['proposals']['findings']=[];candidate['questions']=[];candidate['unrepresented_source_refs']=[]
        for row in analysis['inspections']:row.update(verdict='usable',needed_facts=[])
    one=case.advance(1,change=clear_u);assert one['result']['candidate_outcome']=='valid',one
    def both(candidate,analysis):
        for row in analysis['inspections']:row.update(verdict='usable',needed_facts=[])
        u=deepcopy(candidate['proposals']['actions'][0]);u.update(handle='u-action',name='Synthetic U operation',trace=case.tr('/functional_requirements/0'))
        candidate['proposals']['actions'].append(u)
        candidate['proposals']['findings']=[dict(handle='hold-u',kind='business',question='Clarify U permission',reason='Explicit synthetic U hold',trace=case.tr('/functional_requirements/0'),affected_refs=[dict(local_handle='u-action')],blocking_refs=[dict(local_handle='u-action')],impact_known=True)]
    before=case.pair[:]
    two=case.advance(2,units=[case.u,case.v],change=both)
    assert two['result']['candidate_outcome']=='guard_only',two
    assert case.pair[0]==before[0] and case.pair[1]!=before[1]
    assert not case.last['result']['model']['body']['actions']
    assert case.meta['progress_by_unit'][case.v]['work_completed_through']==1


def test_foreign_source_and_outside_write_rejected_after_raw_capture(tmp_path):
    case=ScopedCase(tmp_path);case.bootstrap();case.advance(1)
    def outside(candidate,analysis):candidate['proposals']['actions'][0]['trace']['source_refs']=[case.src('/functional_requirements/0')]
    before=case.pair[:];result=case.advance(2,change=outside)
    assert result['status']=='rejected',result
    assert case.pair==before
    assert case.repo.lookup_command(result['command_id'])['state']=='finalized'


def test_unknown_global_finding_holds_future_graph(tmp_path):
    case=ScopedCase(tmp_path);case.bootstrap()
    def unknown(candidate,analysis):candidate['proposals']['findings'][0]['impact_known']=False
    one=case.advance(1,change=unknown);assert one['result']['candidate_outcome']=='valid'
    two=case.advance(2)
    assert two['result']['candidate_outcome']=='guard_only',two
    assert not two['result']['model']['body']['actions']


def test_builder_real_bridge_outside_write_and_disjoint_control(tmp_path):
    from copy import deepcopy
    case=ScopedCase(tmp_path);case.bootstrap()
    def clear(candidate,analysis):
        for row in candidate['inspection']:row.update(verdict='usable',needed_facts=[])
        candidate['proposals']['findings']=[];candidate['questions']=[];candidate['unrepresented_source_refs']=[]
        for row in analysis['inspections']:row.update(verdict='usable',needed_facts=[])
    case.advance(1,change=clear)
    def both(candidate,analysis):
        clear(candidate,analysis)
        u=deepcopy(candidate['proposals']['actions'][0]);u.update(handle='u-action',name='U operation',trace=case.tr('/functional_requirements/0'))
        candidate['proposals']['actions'].append(u)
    result=case.advance(2,units=[case.u,case.v],change=both)
    assert result['result']['candidate_outcome']=='valid',result
    ids={a['name']:a['id'] for a in case.last['result']['model']['body']['actions']};aliases={x['id']:h for h,x in case.aliases().items()}
    def bridge(candidate,analysis):
        clear(candidate,analysis)
        candidate['proposals']['responsibilities'][0]['action_ids']=[dict(base_handle=aliases[ids['Read independent V']]),dict(base_handle=aliases[ids['U operation']])]
    before=case.pair[:];rejected=case.advance(3,change=bridge)
    assert rejected['status']=='rejected',rejected
    assert case.pair==before
    def control(candidate,analysis):
        clear(candidate,analysis)
        candidate['proposals']['responsibilities'][0]['action_ids']=[dict(base_handle=aliases[ids['Read independent V']])]
    accepted=case.advance(3,change=control)
    assert accepted['result']['progress_by_unit'][case.v]['work_completed_through']==3,accepted
    assert accepted['result']['progress_by_unit'][case.u]['work_completed_through']==2


def test_revalidation_explicit_domain_edit_terminal(tmp_path):
    case=ScopedCase(tmp_path);case.bootstrap();case.advance(1);case.advance(2);case.advance(3)
    case.advance(4,proof=False);before=case.last['result']['model'];guards=list(case.meta['guards'])
    def edit(candidate,analysis):analysis['inspections'][0]['reason']='requires_domain_edit_outside_h2'
    result=case.advance(3,mode='revalidate',goal='retained_output',guards=guards,change=edit)
    assert result['status']=='blocked',result
    assert result['result']['model']==before
    assert result['result']['progress_by_unit'][case.v]['assessment_state']=='terminal_out_of_scope'
    assert all(q['body']['status']=='open' for q in result['result']['issues'] if q['body']['issue_key'] in guards)


def test_finalized_history_ignores_unpromoted_future_plan(tmp_path):
    from uuid import uuid4
    from dacn_s02.h2_store import ScopeStore
    from dacn_s02.h2_limits import Budget
    from dacn_s02.service import staged
    from dacn_s02.codec_boundary import encode
    case=ScopedCase(tmp_path);result=case.bootstrap();cmd=case.parent
    store=ScopeStore(case.repo,Budget());view=store.load(cmd);plan=store.published_plan(view['command'],view['state'])
    plan['plan_version']='unsupported-future'
    case.repo.append_event(cmd,'log',dict(message='Unpromoted metadata is not a historical publisher'),staged=[staged(cmd,str(uuid4()),'config',encode(plan))])
    assert H2Service(case.repo).resume(cmd)==result


def test_multiple_pending_plans_fail_integrity_without_rebuild(tmp_path):
    import pytest
    from uuid import uuid4
    from dacn_s02.errors import S02Error
    from dacn_s02.h2_store import ScopeStore
    from dacn_s02.h2_limits import Budget
    from dacn_s02.service import staged
    from dacn_s02.codec_boundary import encode
    case=ScopedCase(tmp_path);case.bootstrap();work,authority=case.work(1);cmd=str(uuid4())
    def stop(point):
        if point=='after_seal':raise RuntimeError('sealed')
    service=H2Service(case.repo,authority=authority,_hook=stop);service.prepare(cmd,case.parent,store_id=case.store_id,**work)
    with pytest.raises(RuntimeError):service.resume(cmd)
    store=ScopeStore(case.repo,Budget());view=store.load(cmd);plan,_=store.plans(view['command'],view['state'])[0]
    case.repo.append_event(cmd,'log',dict(message='Synthetic duplicate-plan fault'),staged=[staged(cmd,str(uuid4()),'config',encode(plan))])
    before=case.repo.lookup_command(cmd)
    with pytest.raises(S02Error) as error:H2Service(case.repo,authority=authority).resume(cmd)
    assert error.value.error['stage']=='persistence'
    assert case.repo.lookup_command(cmd)==before


def test_shared_component_context_does_not_expand_write_scope(tmp_path):
    from copy import deepcopy
    case=ScopedCase(tmp_path);case.bootstrap()
    def clear(candidate,analysis):
        for row in candidate['inspection']:row.update(verdict='usable',needed_facts=[])
        candidate['proposals']['findings']=[];candidate['questions']=[];candidate['unrepresented_source_refs']=[]
        for row in analysis['inspections']:row.update(verdict='usable',needed_facts=[])
        for pair in analysis['independence']:pair['verdict']='independent'
    case.advance(1,change=clear)
    def two(candidate,analysis):
        clear(candidate,analysis);u=deepcopy(candidate['proposals']['actions'][0]);u.update(handle='u-action',name='U operation',trace=case.tr('/functional_requirements/0'));candidate['proposals']['actions'].append(u)
    result=case.advance(2,units=[case.u,case.v],change=two);assert result['result']['candidate_outcome']=='valid',result
    ids={a['name']:a['id'] for a in case.last['result']['model']['body']['actions']};aliases={x['id']:h for h,x in case.aliases().items()}
    def u_component(candidate,analysis):
        clear(candidate,analysis)
        for k in ('components','responsibilities'):
            for e in candidate['proposals'][k]:e['trace']=case.tr('/functional_requirements/0')
        candidate['proposals']['responsibilities'][0]['action_ids']=[dict(base_handle=aliases[ids['U operation']])]
    result=case.advance(3,units=[case.u],change=u_component);assert result['result']['candidate_outcome']=='valid',result
    shared=case.alias('Component')
    def v_component(candidate,analysis):
        clear(candidate,analysis);candidate['proposals']['components']=[]
        candidate['proposals']['responsibilities'][0].update(component_id=dict(base_handle=shared),action_ids=[dict(base_handle=aliases[ids['Read independent V']])])
    result=case.advance(3,change=v_component)
    assert result['result']['candidate_outcome']=='valid',result
    assert len(result['result']['model']['body']['components'])==1
    assert len(result['result']['model']['body']['responsibilities'])==2


def test_authority_change_inside_publication_transaction_rolls_back(tmp_path):
    import pytest
    from uuid import uuid4
    from dacn_s02.repository import Repository
    from dacn_s02.errors import S02Error
    case=ScopedCase(tmp_path);case.bootstrap();work,authority=case.work(1);cmd=str(uuid4())
    H2Service(case.repo,authority=authority).prepare(cmd,case.parent,store_id=case.store_id,**work)
    original=authority.path.read_bytes();fired=[]
    def fault(point,connection):
        if point=='before_finalize_insert' and not fired:
            fired.append(point);authority.path.write_bytes(original+b' ')
    service=H2Service(Repository(case.repo.path,_hook=fault),authority=authority)
    with pytest.raises(S02Error):service.resume(cmd)
    assert fired and case.repo.lookup_command(cmd)['state']!='finalized'
    authority.path.write_bytes(original)
    result=H2Service(case.repo,authority=authority).resume(cmd)
    assert result['status']=='blocked',result
    assert sum(e['kind']=='finalized' for e in case.repo.lookup_command(cmd)['events'])==1


def test_finalize_between_prepare_preflight_and_transaction_returns_history(tmp_path):
    from uuid import uuid4
    from dacn_s02.repository import Repository
    case=ScopedCase(tmp_path);case.bootstrap();work,authority=case.work(1);cmd=str(uuid4());winner=[]
    def race(point):
        if point=='before_prepare':
            service=H2Service(Repository(case.repo.path),authority=authority)
            service.prepare(cmd,case.parent,store_id=case.store_id,**work)
            winner.append(service.resume(cmd))
    result=H2Service(case.repo,authority=authority,_hook=race).prepare(cmd,case.parent,store_id=case.store_id,**work)
    assert result==winner[0] and result['status']=='blocked'
    assert sum(e['kind']=='finalized' for e in case.repo.lookup_command(cmd)['events'])==1
