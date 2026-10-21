"""Actual SQLite constraints/locks plus explicitly labelled injected failures."""

import hashlib
import json
import sqlite3

import pytest

from dacn_s01.codec import ProcessingError, serialize_json
from dacn_s01.envelope import EnvelopeInvariantError
from dacn_s01.repository import IntegrityError, Repository
from dacn_s01.service import Service
from dacn_s01.storage_schema import DDL

CREATE = {'mode':'create', 'spec_id':None, 'base_revision':None}


def state(repository):
    with sqlite3.connect(repository.path) as connection:
        return {name: connection.execute(f'SELECT count(*) FROM {name}').fetchone()[0]
                for name in ('runs','sources','snapshots','specs','schema_artifacts')}


def evidence(case, repository, **details):
    print('PHASE3_EVIDENCE ' + json.dumps({'case':case, 'final_counts':state(repository), **details}))


def test_db_configuration_and_repeated_initialization(repository):
    repository.initialize()
    with repository._read() as connection:
        assert connection.autocommit is True
        assert connection.execute('PRAGMA foreign_keys').fetchone()[0] == 1
        assert connection.execute('PRAGMA synchronous').fetchone()[0] == 2
        assert connection.execute('PRAGMA journal_mode').fetchone()[0] == 'delete'
        assert connection.execute('PRAGMA user_version').fetchone()[0] == 1


@pytest.mark.parametrize('kind', ['newer', 'foreign', 'missing-trigger'])
def test_unsupported_structure_is_never_reset(tmp_path, kind):
    path = tmp_path/'foreign.sqlite3'
    repo = Repository(path)
    if kind != 'foreign': repo.initialize()
    with sqlite3.connect(path) as connection:
        if kind == 'newer': connection.execute('PRAGMA user_version=99')
        elif kind == 'foreign': connection.execute('CREATE TABLE private_data (value TEXT)')
        else: connection.execute('DROP TRIGGER sources_no_update')
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(IntegrityError): repo.initialize()
    with pytest.raises(IntegrityError): repo.get_run('unknown')
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before


@pytest.mark.parametrize('table', ['schema_artifacts','sources','runs','snapshots'])
@pytest.mark.parametrize('operation', ['UPDATE','DELETE'])
def test_immutable_records_block_sql_mutation(repository, payload, table, operation):
    output = Service(repository).submit(serialize_json(payload), CREATE)
    columns = {'schema_artifacts':'digest', 'sources':'source_id', 'runs':'run_id', 'snapshots':'snapshot_id'}
    column = columns[table]
    with sqlite3.connect(repository.path) as connection:
        with pytest.raises(sqlite3.IntegrityError, match='immutable'):
            connection.execute(f'UPDATE {table} SET {column}={column}' if operation == 'UPDATE' else f'DELETE FROM {table}')
    assert repository.get_run(output['run']['run_id']) == output


def test_foreign_keys_unique_and_cross_spec_parent_head(repository, payload):
    service = Service(repository)
    a = service.submit(serialize_json(payload), CREATE)
    b = service.submit(serialize_json(payload), CREATE)
    sa, sb = a['snapshot'], b['snapshot']
    con = sqlite3.connect(repository.path, autocommit=True)
    con.execute('PRAGMA foreign_keys=ON')
    try:
        with pytest.raises(sqlite3.IntegrityError, match='FOREIGN KEY'):
            con.execute('INSERT INTO runs VALUES (?,?,?,?,?,?)', ('orphan','missing','{}','{}',None,None))
        with pytest.raises(sqlite3.IntegrityError, match='UNIQUE'):
            con.execute('INSERT INTO sources SELECT * FROM sources LIMIT 1')
        with pytest.raises(sqlite3.IntegrityError, match='UNIQUE'):
            con.execute('INSERT INTO snapshots VALUES (?,?,?,?,?,?,?)', ('other-snapshot',sa['spec_id'],1,None,
                sa['origin_source_id'],'uncommitted-run','{}'))
        with pytest.raises(sqlite3.IntegrityError, match='parent'):
            con.execute('INSERT INTO snapshots VALUES (?,?,?,?,?,?,?)', ('bad-parent',sa['spec_id'],2,sb['snapshot_id'],
                sa['origin_source_id'],a['run']['run_id'],'{}'))
        with pytest.raises(sqlite3.IntegrityError, match='head'):
            con.execute('UPDATE specs SET head_snapshot_id=? WHERE spec_id=?', (sb['snapshot_id'],sa['spec_id']))
        with pytest.raises(sqlite3.IntegrityError, match='deleted'):
            con.execute('DELETE FROM specs')
    finally:
        con.close()
    assert repository.get_head(sa['spec_id']) == sa


@pytest.mark.parametrize('point', ['before_insert','after_source_insert','after_snapshot_insert','before_commit'])
def test_injected_precommit_failure_rolls_back_then_archives_failed(repository, payload, point):
    fired = False
    def hook(where, connection):
        nonlocal fired
        if where == point and not fired:
            fired = True
            raise sqlite3.OperationalError('Injected storage fault')
    failing = Repository(repository.path, _hook=hook)
    result = Service(failing).submit(serialize_json(payload), CREATE)
    assert fired and result['status'] == 'failed'
    assert result['run']['validation']['errors'][-1]['code'] == 'PERSISTENCE_FAILED'
    assert result['snapshot'] is None and result['handoff']['eligible_for_s02'] is False
    assert state(repository) == dict(runs=1,sources=1,snapshots=0,specs=0,schema_artifacts=1)
    assert Repository(repository.path).get_run(result['run']['run_id']) == result
    evidence('injected-'+point, repository, kind='fault injection', rollback_verified=True)


def test_lost_commit_ack_reconciles_same_run_on_new_connection(repository, payload):
    def hook(point, connection):
        if point == 'after_commit':
            assert connection.in_transaction is False
            raise OSError('Injected lost commit acknowledgement')
    result = Service(Repository(repository.path, _hook=hook)).submit(serialize_json(payload), CREATE, run_id='lost-ack')
    assert result['status'] == 'validated'
    assert Repository(repository.path).get_run('lost-ack') == result
    assert state(repository) == dict(runs=1,sources=1,snapshots=1,specs=1,schema_artifacts=1)
    evidence('injected-lost-ack', repository, kind='fault injection', reconciled=True)


@pytest.mark.parametrize('point', ['after_snapshot_insert','after_records','before_commit'])
def test_update_fault_preserves_existing_head_and_history(repository, payload, point):
    first = Service(repository).submit(serialize_json(payload), CREATE)
    head = first['snapshot']
    payload['title'] = 'Changed'
    fired = False
    def hook(where, connection):
        nonlocal fired
        if where == point and not fired:
            fired = True
            raise sqlite3.OperationalError('Injected update failure')
    result = Service(Repository(repository.path, _hook=hook)).submit(serialize_json(payload),
        {'mode':'update','spec_id':head['spec_id'],'base_revision':1})
    assert result['status'] == 'failed'
    assert Repository(repository.path).get_head(head['spec_id']) == head
    assert Repository(repository.path).get_run(first['run']['run_id']) == first
    assert state(repository) == dict(runs=2,sources=2,snapshots=1,specs=1,schema_artifacts=1)
    evidence('injected-update-'+point, repository, kind='fault injection', head_revision=1)


def test_unresolved_commit_never_overwrites_committed_result(repository, payload, monkeypatch):
    failing = Repository(repository.path, _hook=lambda p,c: (_ for _ in ()).throw(OSError('lost ack')) if p == 'after_commit' else None)
    monkeypatch.setattr(failing, 'get_run', lambda _: (_ for _ in ()).throw(sqlite3.OperationalError('unavailable')))
    result = Service(failing).submit(serialize_json(payload), CREATE, run_id='uncertain')
    assert result['status'] == 'failed' and result['snapshot'] is None
    assert 'unresolved' in result['run']['validation']['errors'][-1]['details']['reason']
    stored = Repository(repository.path).get_run('uncertain')
    assert stored['status'] == 'validated'
    assert state(repository)['runs'] == 1
    evidence('injected-unresolved-commit', repository, kind='fault injection', response='failed', stored='validated')


def test_real_begin_lock_timeout_is_persistence_failure(repository, payload):
    locker = sqlite3.connect(repository.path, autocommit=True)
    locker.execute('BEGIN IMMEDIATE')
    try:
        result = Service(Repository(repository.path, timeout=0)).submit(serialize_json(payload), CREATE)
        assert result['status'] == 'failed'
        assert [e['code'] for e in result['run']['validation']['errors']] == ['PERSISTENCE_FAILED']
        assert result['run']['validation']['checks']['revision'] == 'not_run'
    finally:
        locker.execute('ROLLBACK'); locker.close()
    assert state(repository) == dict(runs=0,sources=0,snapshots=0,specs=0,schema_artifacts=0)
    evidence('real-begin-lock-timeout', repository, kind='actual SQLite lock')


def test_real_commit_busy_rolls_back_open_transaction(repository, payload):
    reader = sqlite3.connect(repository.path, autocommit=True)
    reader.execute('BEGIN')
    reader.execute('SELECT * FROM specs').fetchall()  # SHARED lock blocks writer COMMIT, not BEGIN IMMEDIATE.
    attempted = []
    def hook(point, connection):
        if point == 'before_commit': attempted.append(connection.in_transaction)
    try:
        result = Service(Repository(repository.path, timeout=0, _hook=hook)).submit(serialize_json(payload), CREATE)
        assert result['status'] == 'failed' and attempted == [True, True]
    finally:
        reader.execute('ROLLBACK'); reader.close()
    assert state(repository) == dict(runs=0,sources=0,snapshots=0,specs=0,schema_artifacts=0)
    evidence('real-commit-busy', repository, kind='actual SQLite reader lock', rollback_verified=True)


def test_injected_serialization_failure_is_processing_not_rejection(repository, payload, monkeypatch):
    import dacn_s01.repository as module
    original = module._text
    fired = False
    def fail_snapshot(value):
        nonlocal fired
        if isinstance(value, dict) and 'parent_snapshot_id' in value and not fired:
            fired = True
            raise ProcessingError('Injected serializer failure')
        return original(value)
    monkeypatch.setattr(module, '_text', fail_snapshot)
    result = Service(repository).submit(serialize_json(payload), CREATE)
    assert result['status'] == 'failed' and result['snapshot'] is None
    assert result['run']['validation']['errors'][-1]['code'] == 'PROCESSING_FAILED'
    assert state(repository)['snapshots'] == 0


@pytest.mark.parametrize('corruption', ['handoff', 'source', 'snapshot', 'request', 'schema'])
def test_checked_lookup_rejects_inconsistent_records(repository, payload, corruption):
    result = Service(repository).submit(serialize_json(payload), CREATE)
    run_id = result['run']['run_id']
    table = {'handoff':'runs', 'source':'sources', 'snapshot':'snapshots', 'request':'runs', 'schema':'schema_artifacts'}[corruption]
    # Deliberate test tampering bypasses an immutable trigger; normal SQL cannot do this.
    # Restore structure to test record guards independently of the structure guard.
    with sqlite3.connect(repository.path) as con:
        con.execute(f'DROP TRIGGER {table}_no_update')
        if corruption == 'handoff':
            result['handoff']['snapshot_id'] = 'invented'
            con.execute('UPDATE runs SET envelope_json=?', (serialize_json(result).decode(),))
        elif corruption == 'source': con.execute('UPDATE sources SET raw_input=?', (b'{}',))
        elif corruption == 'snapshot': con.execute("UPDATE snapshots SET snapshot_json='{}'")
        elif corruption == 'request': con.execute("UPDATE runs SET request_json='{}'")
        else: con.execute('UPDATE schema_artifacts SET raw_schema=?', (b'{}',))
        con.execute(DDL[f'{table}_no_update'])
    with pytest.raises((IntegrityError, EnvelopeInvariantError)):
        Repository(repository.path).get_run(run_id)


def test_bad_candidate_is_rejected_before_commit(repository, payload, monkeypatch):
    original = repository.store
    fired = False
    def bad_candidate(connection, raw, context, envelope, schema):
        nonlocal fired
        if not fired:
            fired = True
            envelope['handoff']['snapshot_id'] = 'wrong'
        return original(connection, raw, context, envelope, schema)
    monkeypatch.setattr(repository, 'store', bad_candidate)
    result = Service(repository).submit(serialize_json(payload), CREATE)
    assert result['status'] == 'failed' and result['snapshot'] is None
    assert state(repository)['snapshots'] == 0
