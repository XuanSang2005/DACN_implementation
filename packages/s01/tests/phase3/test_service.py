from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal, localcontext
import sqlite3

import pytest

from dacn_s01.codec import parse_json, serialize_json
from dacn_s01.envelope import check_envelope
from dacn_s01.repository import IntegrityError, Repository
from dacn_s01.service import Service

CREATE = {'mode': 'create', 'spec_id': None, 'base_revision': None}


def update(snapshot, base=None):
    return {'mode': 'update', 'spec_id': snapshot['spec_id'],
            'base_revision': snapshot['revision'] if base is None else base}


def counts(repository):
    with sqlite3.connect(repository.path) as con:
        return {table: con.execute(f'SELECT count(*) FROM {table}').fetchone()[0]
                for table in ('sources', 'runs', 'snapshots', 'specs', 'schema_artifacts')}


def test_lifecycle_reopen_reuse_edit_reorder_return_to_old(payload, repository):
    original = serialize_json(payload)
    first = Service(repository).submit(original, CREATE)
    check_envelope(first)
    assert first['status'] == 'validated' and first['result_kind'] == 'new_spec'
    s1 = first['snapshot']
    assert s1['revision'] == 1 and s1['parent_snapshot_id'] is None
    legacy = deepcopy(payload)
    del legacy['schema_version']
    second = Service(Repository(repository.path)).submit(serialize_json(legacy), update(s1))
    assert second['result_kind'] == 'unchanged' and second['snapshot'] == s1
    assert second['run']['source'] != first['run']['source']
    assert second['run']['normalizations'] == [{'operation':'add', 'input_pointer':'/schema_version',
                                              'value':'1.0.0', 'reason':'LEGACY_SCHEMA_VERSION'}]
    payload['functional_requirements'][0]['priority'] = 'should'
    third = Service(Repository(repository.path)).submit(serialize_json(payload), update(s1))
    payload['actors'].reverse()
    fourth = Service(Repository(repository.path)).submit(serialize_json(payload), update(third['snapshot']))
    fifth = Service(Repository(repository.path)).submit(original, update(fourth['snapshot']))
    for previous, current, revision in ((first, third, 2), (third, fourth, 3), (fourth, fifth, 4)):
        assert current['result_kind'] == 'new_revision'
        assert current['snapshot']['revision'] == revision
        assert current['snapshot']['parent_snapshot_id'] == previous['snapshot']['snapshot_id']
    assert fifth['snapshot']['input'] == s1['input'] and fifth['snapshot']['snapshot_id'] != s1['snapshot_id']
    reopened = Repository(repository.path)
    for output in (first, second, third, fourth, fifth):
        assert reopened.get_run(output['run']['run_id']) == output
        assert reopened.get_snapshot(output['snapshot']['snapshot_id']) == output['snapshot']
    assert reopened.get_source(s1['origin_source_id']) == original
    assert reopened.get_head(s1['spec_id']) == fifth['snapshot']
    assert counts(repository) == dict(sources=5, runs=5, snapshots=4, specs=1, schema_artifacts=1)


def test_exact_storage_and_representation_only_unchanged(payload, repository):
    payload['constraints'][0]['constraint']['value'] = {
        'big': Decimal('9' * 5001), 'fraction': Decimal('0.123456789012345678901234567890123456789'),
        'huge': Decimal('1e400'), 'zero': Decimal('-0'), 'one': Decimal('1.0'),
        'unknown': None, 'literal': ' e\u0301 ', 'bool': True}
    raw = b' \n' + serialize_json(payload) + b'\n '
    with localcontext() as ctx:
        ctx.prec = 2
        first = Service(repository).submit(raw, CREATE)
    assert first['status'] == 'validated'
    reopened = Repository(repository.path)
    assert reopened.get_source(first['run']['source']['source_id']) == raw
    stored = reopened.get_snapshot(first['snapshot']['snapshot_id'])['input']
    for key in ('big', 'fraction', 'huge', 'zero', 'one'):
        assert stored['constraints'][0]['constraint']['value'][key].as_tuple() == payload['constraints'][0]['constraint']['value'][key].as_tuple()
    reordered = dict(reversed(list(payload.items())))
    reordered['constraints'][0]['constraint']['value']['zero'] = 0
    reordered['constraints'][0]['constraint']['value']['one'] = 1
    second = Service(reopened).submit(serialize_json(reordered), update(first['snapshot']))
    assert second['result_kind'] == 'unchanged' and second['snapshot'] == first['snapshot']
    assert reopened.get_source(second['run']['source']['source_id']) == serialize_json(reordered)


@pytest.mark.parametrize('change', ['bool-number', 'missing-null', 'string-space', 'unicode', 'criteria-order'])
def test_semantic_tree_changes_create_revision(payload, service, change):
    payload['constraints'][0]['constraint']['value'] = {'x': True, 'text': 'é'}
    first = service.submit(serialize_json(payload), CREATE)
    if change == 'bool-number': payload['constraints'][0]['constraint']['value']['x'] = 1
    if change == 'missing-null': payload['project_details'] = None
    if change == 'string-space': payload['title'] += ' '
    if change == 'unicode': payload['constraints'][0]['constraint']['value']['text'] = 'e\u0301'
    if change == 'criteria-order': payload['functional_requirements'][0]['acceptance_criteria'].reverse()
    result = service.submit(serialize_json(payload), update(first['snapshot']))
    assert result['status'] == 'validated' and result['result_kind'] == 'new_revision'


def test_identical_create_does_not_merge_specs(payload, service):
    a, b = [service.submit(serialize_json(payload), CREATE) for _ in range(2)]
    assert a['snapshot']['spec_id'] != b['snapshot']['spec_id']
    assert a['snapshot']['revision'] == b['snapshot']['revision'] == 1


@pytest.mark.parametrize('raw,code', [(b'{', 'INVALID_JSON'), (b'{"a":1,"a":2}', 'DUPLICATE_JSON_KEY'),
                                    (b'\xff\x00\xfe\x81\xff', 'INVALID_JSON'),
                                    (b'[]', 'TYPE_MISMATCH'), (b'1e999999999999999999999999', 'PROCESSING_FAILED')])
def test_invalid_input_still_archived_before_request_checks(raw, code, repository):
    request = {'bad': Decimal('123456789.12345678901234567890123456789')}
    result = Service(repository).submit(raw, request)
    assert result['status'] == ('failed' if code == 'PROCESSING_FAILED' else 'rejected')
    assert result['run']['request'] is None and result['run']['validation']['checks']['revision'] == 'not_run'
    assert result['run']['validation']['errors'][0]['code'] == code
    assert Repository(repository.path).get_source(result['run']['source']['source_id']) == raw
    assert Repository(repository.path).get_request(result['run']['run_id']) == request
    assert counts(repository)['snapshots'] == counts(repository)['specs'] == 0


@pytest.mark.parametrize('context,paths,projected', [
    ({}, ['/base_revision','/mode','/spec_id'], None),
    ({'mode':'wrong','spec_id':None,'base_revision':None}, ['/mode'], None),
    ({'mode':'update','spec_id':None,'base_revision':None}, ['/base_revision','/spec_id'], 'original'),
    ({'mode':'create','spec_id':'s','base_revision':1}, ['/base_revision','/spec_id'], 'original'),
])
def test_request_errors_persist_original(payload, repository, context, paths, projected):
    result = Service(repository).submit(serialize_json(payload), context)
    assert result['status'] == 'rejected' and result['snapshot'] is None
    assert result['handoff'] == {'eligible_for_s02':False, 'snapshot_id':None}
    assert result['run']['request'] == (context if projected else None)
    assert result['run']['validation']['checks'] == dict(parse='passed', schema='passed', cross_field='passed', revision='failed')
    errors = result['run']['validation']['errors']
    assert [e['pointer'] for e in errors] == paths
    assert all(e['code'] == 'INVALID_REQUEST' and e['stage'] == 'revision' and e['target'] == 'request' for e in errors)
    assert Repository(repository.path).get_request(result['run']['run_id']) == context


def test_unknown_spec_and_stale_payload_equal_new_head(payload, service):
    missing = service.submit(serialize_json(payload), {'mode':'update','spec_id':'absent','base_revision':1})
    assert missing['run']['validation']['errors'][0]['details'] == {'spec_id':'absent'}
    assert missing['run']['validation']['errors'][0]['code'] == 'SPEC_NOT_FOUND'
    a = service.submit(serialize_json(payload), CREATE)
    payload['title'] = 'Changed'
    b = service.submit(serialize_json(payload), update(a['snapshot']))
    stale = service.submit(serialize_json(payload), update(a['snapshot']))
    assert b['snapshot']['revision'] == 2 and stale['status'] == 'rejected'
    assert stale['run']['validation']['errors'][0]['details'] == {'expected_revision':2, 'provided_revision':1}
    assert stale['run']['validation']['errors'][0]['code'] == 'REVISION_CONFLICT'


def test_clock_rollback_ids_collision_and_lookup_absent(payload, repository):
    clock = iter([datetime(2026,10,17,12,tzinfo=timezone.utc), datetime(2026,10,16,12,tzinfo=timezone.utc)])
    first = Service(repository, _clock=lambda: next(clock)).submit(serialize_json(payload), CREATE, run_id='known-before-commit')
    assert first['run']['completed_at'] == first['run']['received_at']
    assert repository.get_run('absent') is None
    assert repository.get_source('absent') is None
    assert repository.get_snapshot('absent') is None
    assert repository.get_head('absent') is None
    ids = {'source': iter([first['run']['source']['source_id'], 'new-source']),
           'spec': iter([first['snapshot']['spec_id'], 'new-spec']),
           'snapshot': iter([first['snapshot']['snapshot_id'], 'new-snapshot'])}
    second = Service(repository, _ids=lambda kind: next(ids[kind])).submit(serialize_json(payload), CREATE, run_id='new-run')
    assert second['status'] == 'validated' and second['snapshot']['spec_id'] == 'new-spec'
    before = counts(repository)
    collision = Service(repository).submit(serialize_json(payload), CREATE, run_id='known-before-commit')
    assert collision['status'] == 'failed' and collision['handoff']['eligible_for_s02'] is False
    assert repository.get_run('known-before-commit') == first and counts(repository) == before


def test_lookup_does_not_rewrite_timestamps_or_build(payload, repository):
    first = Service(repository).submit(serialize_json(payload), CREATE)
    before = counts(repository)
    for _ in range(2):
        assert Repository(repository.path).get_run(first['run']['run_id']) == first
    assert counts(repository) == before


def test_raw_utf16_and_precise_invalid_request_details(payload, repository):
    raw = (' \n' + serialize_json(payload).decode()).encode('utf-16')
    context = {'mode':'update','spec_id':'unknown','base_revision':Decimal('1.23456789012345678901234567890123456789')}
    result = Service(repository).submit(raw, context)
    assert result['status'] == 'rejected'
    assert Repository(repository.path).get_source(result['run']['source']['source_id']) == raw
    assert result['run']['validation']['errors'][0]['details']['actual'].as_tuple() == context['base_revision'].as_tuple()


def test_allocate_run_id_has_no_storage_effect_and_can_be_supplied(payload, repository):
    service = Service(repository)
    identifier = service.allocate_run_id()
    assert repository.get_run(identifier) is None
    assert counts(repository)['runs'] == 0
    output = service.submit(serialize_json(payload), CREATE, run_id=identifier)
    assert output['status'] == 'validated' and output['run']['run_id'] == identifier
