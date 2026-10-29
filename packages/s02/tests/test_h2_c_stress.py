"""Handwritten H2-C publication oracles; no algorithm-produced expectations."""
from copy import deepcopy
from hashlib import sha256
from uuid import uuid4

import pytest

from h2_c_fixtures import ManyCase, finish_worker, join_workers
from test_h2_checkpoint_processes import spec, final
from dacn_s02.codec_boundary import encode
from dacn_s02.errors import S02Error
from dacn_s02.h2_service import H2Service
from dacn_s02.h2_store import ScopeStore
from dacn_s02.h2_limits import Budget
from dacn_s02.repository import Repository


def digest(value):
    return sha256(encode(value)).hexdigest()


def historical(result):
    """Current head is a live observation, not part of the finalized outcome."""
    value=deepcopy(result)
    value['result'].pop('current_head')
    value['result'].pop('is_current')
    return value


def published(case, command):
    view, plan = final(case, command)
    assert not any(r['type'] in ('answer','review','bundle','handoff','application')
                   for r in view['state']['records'].values())
    # The plan is an intent. Independently compare each domain Record against
    # actual committed records, not merely the planned head/status.
    domain = [r for r in plan['batch']['records'] if r['type'] not in ('run', 'artifact')]
    stale = view['command']['run']['body']['status'] == 'stale'
    assert domain
    for record in domain:
        if stale:
            assert record['id'] not in view['state']['records']
        else:
            assert view['state']['records'][record['id']] == record
    assert len([r for r in plan['batch']['records'] if r['type'] == 'analysis_set']) == 1
    if stale:
        body = view['command']['run']['body']
        assert body['result_model_id'] is None and body['result_analysis_set_id'] is None
    return view, plan


def invariant(case, expected_stages, old_model=None, old_progress=None):
    result = case.last['result']
    body = result['model']['body']
    # Source oracle: 5 FR x (requirement + 2 criteria), one NFR, one constraint.
    expected = {f'/functional_requirements/{i}'+suffix for i in range(5)
                for suffix in ('', '/acceptance_criteria/0', '/acceptance_criteria/1')}
    expected |= {'/non_functional_requirements/0', '/constraints/0'}
    assert {r['source_ref']['input_pointer'] for r in body['mappings']} == expected
    assert len(body['mappings']) == 17
    assert case.snapshot['input'] == dict(case.source,schema_version='1.0.0')
    assert case.source['operating_conditions'] == dict.fromkeys([
        'critical_scenarios','expected_load','peak_load','data_volume','growth','resource_budget'])
    assert [x['name'] for x in body['actors']] == ['Operator']
    assert len(body['actions']) == sum(stage >= 2 for stage in expected_stages.values())
    assert len(body['responsibilities']) == sum(stage >= 3 for stage in expected_stages.values())
    for i, stage in expected_stages.items():
        p = case.meta['progress_by_unit'][case.unit(i)]
        assert p['work_completed_through'] == stage
        assert p['latest_checked_pair'] == case.pair
        assert p['assessment']['result_pair'] == case.pair
        assert p['assessment']['result_model_sha256'] == digest(result['model'])
        assert p['assessment']['output_refs'] == p['outputs']
        rows = [r for r in body['mappings'] if r['source_ref']['input_pointer'].startswith(f'/functional_requirements/{i}')]
        assert len(rows) == 3
        assert all(r['assessment'] == ('proposed' if stage == 4 else 'not_assessed') for r in rows)
        assert all(len(r['parts']) == (1 if stage == 4 else 0) for r in rows)
        if old_progress:
            previous = old_progress[case.unit(i)]
            assert p['assessment']['parent_assessment_sha256'] == digest(previous['assessment'])
            for completed, output in previous['outputs'].items():
                assert p['outputs'][completed] == output
    u = case.meta['progress_by_unit'][case.u]
    assert u['work_completed_through'] == 1 and u['assessment_state'] == 'assessed_held'
    business = [q for q in result['issues'] if q['body']['kind'] == 'business']
    assert len(business) == 1 and business[0]['body']['status'] == 'open'
    assert business[0]['body']['answer_ids'] == [] and business[0]['body']['resolution'] is None
    assert all(q['body']['status'] == 'open' for q in result['issues']
               if case.meta['tasks'].get(q['body']['issue_key'], {}).get('role') == 'global_mapping')
    if old_model:
        # Existing domain entities are byte-preserved. Mapping issue IDs may
        # be rebound; row ID/source association and existing Parts may not.
        for coll in ('actors', 'actions', 'components', 'responsibilities'):
            current = {e['id']:e for e in body[coll]}
            for entity in old_model['body'][coll]:
                assert current[entity['id']] == entity
        current = {r['id']:r for r in body['mappings']}
        for row in old_model['body']['mappings']:
            assert current[row['id']]['source_ref'] == row['source_ref']
            if row['parts']:
                assert current[row['id']] == row
    assert result['eligibility_authorized_in_process'] is False


def test_twenty_plus_explicit_checkpoints_four_process_cas_and_stale_resubmission(tmp_path):
    c = ManyCase(tmp_path, independent=4)
    c.bootstrap()
    c.observe(c.parent, '01 bootstrap')
    work, authority = c.work(1)
    c.execute(work, authority, '02 inspect full inventory; U held')
    expected = {1:1,2:1,3:1,4:1}
    invariant(c, expected)
    base = c.pair[:]
    original_parent = c.parent
    pending = []
    for i in (1,2,3,4):
        work, authority = c.unit_work(2, i)
        command = str(uuid4())
        H2Service(Repository(c.repo.path), authority=authority).prepare(
            command, original_parent, store_id=c.store_id, **work)
        pending.append((i, command, work, authority))
    # Four OS processes reach before_finalize with plans sealed at the SAME
    # pair. There is no sequential worker pool or thread substitute.
    workers = [finish_worker(c, spec(c, cmd, work, auth,
               barrier_point='before_finalize', barrier=str(tmp_path/'four-domain-workers')))
               for _, cmd, work, auth in pending]
    assert len({p.pid for p in workers}) == 4
    results = join_workers(workers)
    assert sorted(r['status'] for r in results) == ['blocked','stale','stale','stale']
    assert len(list((tmp_path/'four-domain-workers').iterdir())) == 4
    winner = next(item for item, r in zip(pending, results) if r['status'] == 'blocked')
    c.reopen(winner[1])
    expected[winner[0]] = 2
    assert c.pair[0] != base[0] and c.pair[1] != base[1]
    assert len(c.last['result']['model']['body']['actions']) == 1
    for item, r in zip(pending, results):
        i, command, work, authority = item
        view, plan = published(c, command)
        assert plan['admission']['base_pair'] == base
        c.observe(command, f'race V{i}: {r["status"]}')
        if command == winner[1]:
            continue
        before = c.repo.path.read_bytes()
        replay=H2Service(Repository(c.repo.path)).resume(command)
        assert historical(replay) == historical(r)
        assert replay['result']['current_head'] == c.pair and replay['result']['is_current'] is False
        assert c.repo.path.read_bytes() == before
        old_operation = deepcopy(c.repo.lookup_command(command))
        new_work, new_authority = c.unit_work(2, i)
        assert new_work['expected_pair'] == c.pair and new_work['expected_pair'] != work['expected_pair']
        assert new_work['analysis'] != work['analysis'] and new_work['candidate'] != work['candidate']
        assert new_authority.expected_sha256 != authority.expected_sha256
        # Old approval cannot authorize new input/current pair; no T0 effect.
        denied = str(uuid4())
        with pytest.raises(S02Error):
            H2Service(c.repo, authority=authority).prepare(denied, c.parent, store_id=c.store_id, **new_work)
        assert c.repo.lookup_command(denied) is None
        old_model = deepcopy(c.last['result']['model'])
        old_progress = deepcopy(c.meta['progress_by_unit'])
        result = c.execute(new_work, new_authority, f'explicit resubmit V{i} stage 2')
        assert result['command_id'] != command and result['result']['candidate_outcome'] == 'valid'
        assert c.repo.lookup_command(command) == old_operation
        expected[i] = 2
        invariant(c, expected, old_model, old_progress)
    # Named fixed script, not autonomous iterations: 20 published checkpoints
    # = bootstrap + inspection + 4*(2,3,4) + two*(guard,missing,complete proof).
    schedule = [(1,3),(1,4),(2,3),(2,4),(3,3),(3,4),(4,3),(4,4)]
    retained_batches = {(3,3):(1,2), (4,3):(1,2,3)}
    for number, step in schedule:
        if (number,step) in retained_batches:
            assessed = retained_batches[number,step]
            retained = deepcopy(c.last['result']['model'])
            outputs = deepcopy(c.meta['progress_by_unit'][c.v]['outputs'])
            already_resolved = {q['body']['issue_key']:deepcopy(q) for q in c.last['result']['issues']
                                if q['body']['issue_key'] in c.meta['guards'] and q['body']['status']=='resolved'}
            result = c.execute(*c.unit_work(step,number,proof=False), f'guard before V{number} stage {step}')
            assert result['result']['candidate_outcome'] == 'guard_only'
            assert c.last['result']['model'] == retained
            assert c.meta['progress_by_unit'][c.v]['assessment_state'] == 'needs_revalidation'
            guards = [q['body']['issue_key'] for q in c.last['result']['issues']
                      if q['body']['issue_key'] in c.meta['guards'] and q['body']['status']=='open']
            assert len(guards) == 1
            business = next(q for q in c.last['result']['issues'] if q['body']['kind']=='business')
            last_guard = next(q for q in c.last['result']['issues'] if q['body']['issue_key']==guards[0])
            for proof, status in ((False,'open'), (True,'resolved')):
                result = c.execute(*c.work(4,units=[c.unit(i) for i in assessed],
                                          mode='revalidate',goal='retained_output',guards=guards,proof=proof),
                                   f'retained {assessed} {status}')
                assert result['status'] == 'blocked' and result['result']['candidate_outcome'] == 'revalidated'
                current = next(q for q in c.last['result']['issues'] if q['body']['issue_key']==guards[0])
                assert current['body']['status'] == status and current['body']['supersedes_id'] == last_guard['id']
                assert next(q for q in c.last['result']['issues'] if q['id']==business['id']) == business
                assert c.last['result']['model'] == retained
                assert c.meta['progress_by_unit'][c.v]['outputs'] == outputs
                assert c.meta['progress_by_unit'][c.v]['work_completed_through'] == 4
                assert all(c.meta['progress_by_unit'][c.unit(i)]['work_completed_through']==4 for i in assessed)
                assert all(c.meta['progress_by_unit'][c.unit(i)]['assessment_state']==
                           ('current' if proof else 'needs_revalidation') for i in assessed)
                for key, old_guard in already_resolved.items():
                    assert next(q for q in c.last['result']['issues'] if q['body']['issue_key']==key)==old_guard
                _, plan = published(c, result['command_id'])
                assert not any(r['type'] in ('model','change') for r in plan['batch']['records'])
                last_guard = current
        old_model = deepcopy(c.last['result']['model'])
        old_progress = deepcopy(c.meta['progress_by_unit'])
        result = c.execute(*c.unit_work(step,number), f'V{number} stage {step}')
        assert result['status'] == 'blocked' and result['result']['candidate_outcome'] == 'valid', result
        expected[number] = step
        invariant(c, expected, old_model, old_progress)
        published(c, result['command_id'])
    assert expected == {1:4,2:4,3:4,4:4}
    assert all(c.meta['progress_by_unit'][c.unit(i)]['assessment_state']=='current' for i in (1,2,3,4))
    assert len(c.checkpoints) == 23
    assert sum(row['status'] != 'stale' for row in c.checkpoints) == 20
    assert len(c.meta['guards'])==2
    assert all(q['body']['status']=='resolved' for q in c.last['result']['issues'] if q['body']['issue_key'] in c.meta['guards'])
    c.repo.verify()


def test_four_process_as_only_cas_preserves_retained_outputs(tmp_path):
    c = ManyCase(tmp_path)
    c.bootstrap()
    c.execute(*c.work(1), 'inspect')
    c.execute(*c.unit_work(2,1), 'V1 action')
    c.execute(*c.unit_work(3,1), 'V1 responsibility')
    c.execute(*c.unit_work(4,1,proof=False), 'guard')
    model = deepcopy(c.last['result']['model'])
    outputs = deepcopy(c.meta['progress_by_unit'][c.v]['outputs'])
    base = c.pair[:]
    work, auth = c.unit_work(3,1,mode='revalidate',goal='retained_output',guards=list(c.meta['guards']))
    commands = [str(uuid4()) for _ in range(4)]
    sealed={}
    class Sealed(Exception):pass
    def stop(point):
        if point=='after_seal':raise Sealed()
    for command in commands:
        H2Service(Repository(c.repo.path),authority=auth).prepare(command,c.parent,store_id=c.store_id,**work)
        # Isolate AS-only T3 contention from the separate domain race's
        # concurrent build/seal workload. Each original plan is sealed through
        # the actual handler before four fresh processes compete for CAS.
        with pytest.raises(Sealed):
            H2Service(Repository(c.repo.path),authority=auth,_hook=stop).resume(command)
        store=ScopeStore(Repository(c.repo.path),Budget())
        view=store.load(command)
        plans=store.plans(view['command'],view['state'])
        assert view['command']['state']=='prepared' and len(plans)==1
        assert view['current_head']==base
        sealed[command]=plans[0][1]['sha256']
    workers = [finish_worker(c,spec(c,command,work,auth,barrier_point='before_finalize',
                                  barrier=str(tmp_path/'four-as-workers'))) for command in commands]
    assert len({w.pid for w in workers}) == 4
    results = join_workers(workers)
    assert sorted(r['status'] for r in results) == ['blocked','stale','stale','stale']
    winner = next(r['command_id'] for r in results if r['status']=='blocked')
    c.reopen(winner)
    assert c.pair[0] == base[0] and c.pair[1] != base[1]
    assert c.last['result']['model'] == model
    assert c.meta['progress_by_unit'][c.v]['outputs'] == outputs
    assert c.meta['progress_by_unit'][c.v]['work_completed_through'] == 3
    for command, result in zip(commands,results):
        view, plan = published(c,command)
        assert ScopeStore(Repository(c.repo.path),Budget()).plans(view['command'],view['state'])[0][1]['sha256']==sealed[command]
        assert not any(r['type'] in ('model','change') for r in plan['batch']['records'])
        before = c.repo.path.read_bytes()
        assert H2Service(Repository(c.repo.path)).resume(command) == result
        assert c.repo.path.read_bytes() == before
