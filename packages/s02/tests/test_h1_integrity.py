"""Synthetic corruption fixtures exercise private-plan failure boundaries."""
import sqlite3
from uuid import uuid4
import pytest

from dacn_s02.codec_boundary import decode,encode
from dacn_s02.errors import S02Error
from dacn_s02.repository import Repository,digest
from dacn_s02.service import staged
from dacn_s02.storage_schema import DDL
from dacn_s02.h1_store import WorkStore,logical
from dacn_s02.h1_service import H1Service
from h1_fixtures import Case


def sealed(case):
    cmd=case.prepare('bootstrap')
    def pause(point):
        if point=='after_seal':raise RuntimeError('paused')
    with pytest.raises(RuntimeError):H1Service(case.repo,_hook=pause).resume(cmd)
    view=WorkStore(case.repo).load(cmd)
    plan,stage=WorkStore(case.repo).checked_plan(view['command'],view['state'],view['config'],view['primary'],view['raw'])
    return cmd,view,plan,stage


def corrupt_stage(repo,stage,transform,*,bad_hash=False):
    raw=encode(transform(decode(stage['bytes'])))
    with sqlite3.connect(repo.path) as c:
        c.execute('DROP TRIGGER immutable_staged_blobs_update')
        c.execute('UPDATE staged_blobs SET bytes=?,sha256=?,byte_length=? WHERE command_id=? AND blob_id=?',
            (raw,stage['sha256'] if bad_hash else digest(raw),len(raw),stage['command_id'],stage['blob_id']))
        c.execute(DDL['immutable_staged_blobs_update'])


@pytest.mark.parametrize('kind',['version','binding','type','hash','multiple','unknown_marker'])
def test_bad_plan_never_rebuilt_or_repaired(tmp_path,kind):
    case=Case(tmp_path);cmd,view,plan,stage=sealed(case)
    if kind=='multiple':
        case.repo.append_event(cmd,'log',dict(message='SYNTHETIC extra plan fault'),staged=[staged(cmd,str(uuid4()),'config',encode(plan))])
    else:
        def mutate(value):
            if kind=='version':value['plan_version']='unsupported-future'
            if kind=='binding':value['bindings']['source_context_id']='wrong'
            if kind=='type':value['allocation']=[]
            if kind=='hash':value['diagnostics']=[];value['candidate_outcome']='blocked'
            if kind=='unknown_marker':value['marker']='unsupported-marker'
            return value
        corrupt_stage(case.repo,stage,mutate,bad_hash=kind=='hash')
    with sqlite3.connect(case.repo.path) as c:before=c.execute('SELECT count(*) FROM staged_blobs').fetchone()[0]
    with pytest.raises(S02Error) as caught:H1Service(Repository(case.repo.path)).resume(cmd)
    assert caught.value.error['stage']=='persistence'
    with sqlite3.connect(case.repo.path) as c:
        assert c.execute('SELECT count(*) FROM staged_blobs').fetchone()[0]==before
        assert c.execute('SELECT count(*) FROM operation_events WHERE command_id=? AND kind="finalized"',(cmd,)).fetchone()[0]==0


@pytest.mark.parametrize('kind',['handler','limits_version','limits_reset'])
def test_config_versions_and_limits_cannot_be_reset(tmp_path,kind):
    case=Case(tmp_path);cmd=case.prepare('bootstrap');view=WorkStore(case.repo).load(cmd)
    def mutate(value):
        if kind=='handler':value['handler_version']='future'
        if kind=='limits_version':value['limits_version']='future'
        if kind=='limits_reset':value['limits']['entities']+=1;value['limits_sha256']=digest(encode(value['limits']))
        value['intent_sha256']=digest(encode(logical(value)));return value
    corrupt_stage(case.repo,view['primary'],mutate)
    with pytest.raises(S02Error) as caught:H1Service(case.repo).resume(cmd)
    assert caught.value.error['stage']=='persistence'
    assert case.repo.get_command(cmd)['state']=='prepared'


def test_finalize_between_outer_lookup_and_seal_does_not_append(tmp_path):
    case=Case(tmp_path);cmd=case.prepare('bootstrap');winner=[]
    def race(point):
        if point=='before_seal':winner.append(H1Service(Repository(case.repo.path)).resume(cmd))
    result=H1Service(case.repo,_hook=race).resume(cmd)
    assert result==winner[0]
    view=WorkStore(case.repo).load(cmd)
    assert len(WorkStore(case.repo).plans(view['command'],view['state']))==1
    assert sum(e['kind']=='finalized' for e in view['command']['events'])==1


def test_finalized_run_authority_ignores_unpromoted_future_plan(tmp_path):
    case=Case(tmp_path);result=case.advance('bootstrap');cmd=case.parent;view=WorkStore(case.repo).load(cmd)
    plan,stage=WorkStore(case.repo).checked_plan(view['command'],view['state'],view['config'],view['primary'],view['raw'])
    plan['plan_version']='unsupported-future'
    case.repo.append_event(cmd,'log',dict(message='SYNTHETIC future metadata'),staged=[staged(cmd,str(uuid4()),'config',encode(plan))])
    assert H1Service(Repository(case.repo.path)).resume(cmd)==result
