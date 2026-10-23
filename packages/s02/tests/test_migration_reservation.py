"""Regression for P3-01: durable reservation and initialization arbitration."""
from dataclasses import replace
import json,multiprocessing as mp,os,signal
import pytest
from dacn_s02.errors import S02Error
from dacn_s02.repository import Repository
from dacn_s02 import reservation
from migration_fixtures import make_migration
from migration_worker import protocol
from reservation_worker import initialize
from test_migration import disk
from helpers import evidence

def state(path):return (path.exists(),disk(path) if path.exists() else None)

POINTS=['reservation_created','reservation_before_dir_sync','reservation_durable','destination_created','after_reserve','before_copy_commit']

def receive(pipe):
    assert pipe.poll(35),'worker deadline'
    return pipe.recv()

def stop(worker):
    if worker.is_alive():os.kill(worker.pid,signal.SIGKILL)
    worker.join(10)

@pytest.mark.parametrize('point',POINTS)
@pytest.mark.parametrize('entry',['api','cli'])
def test_kill_reservation_boundaries_are_never_fresh(tmp_path,point,entry):
    m,r,_=make_migration(tmp_path,empty=True);source=disk(m.source)
    ctx=mp.get_context('spawn');parent,child=ctx.Pipe();gate=ctx.Event()
    worker=ctx.Process(target=protocol,args=(m.settings,m.source,r,'copy',child,gate,point));worker.start()
    try:
        event=receive(parent);assert event['event']=='checkpoint' and event['point']==point
    finally:stop(worker)
    assert worker.exitcode==-signal.SIGKILL
    mark=reservation.marker(m.destination);assert mark.exists()
    raw=mark.read_bytes();receipt=r.read_bytes();before=state(m.destination)
    if entry=='api':
        # Also reject an alternate DB filename in the reserved state directory.
        for path in (m.target.path,m.destination/'alternate.sqlite3'):
            with pytest.raises(S02Error):Repository(path).initialize(create_parent=True)
    else:
        m.settings.path.write_text('state_dir = '+json.dumps(str(m.destination))+'\n')
        p,c=ctx.Pipe();g=ctx.Event();w=ctx.Process(target=initialize,args=(m.target.path,c,g,None,m.settings.path));w.start()
        assert receive(p)['event']=='started';result=receive(p);w.join(10)
        assert result['exit_code']!=0 and w.exitcode==0
    assert state(m.destination)==before and disk(m.source)==source
    assert mark.read_bytes()==raw and r.read_bytes()==receipt
    # A torn marker is fail-closed; a complete one reconciles as partial.
    if raw:assert m.reconcile(r,offline=True)['status']=='partial'
    with pytest.raises(S02Error):m.copy(r,offline=True,resume=True)
    assert mark.read_bytes()==raw and state(m.destination)==before
    evidence('reservation_kill',point=point,entry=entry,worker=event,exit_code=worker.exitcode,marker_size=len(raw),source_unchanged=True)

@pytest.mark.parametrize('entry',['api','cli'])
@pytest.mark.parametrize('point',['before_reserve','reservation_created','reservation_durable','after_reserve'])
def test_migration_holds_guard_against_concurrent_init(tmp_path,entry,point):
    m,r,_=make_migration(tmp_path,empty=True);settings=replace(m.settings,timeout=5000)
    settings.path.write_text('state_dir = '+json.dumps(str(m.destination))+'\n'+'busy_timeout_ms = 5000\n')
    ctx=mp.get_context('spawn');p,c=ctx.Pipe();gate=ctx.Event();w=ctx.Process(target=protocol,args=(settings,m.source,r,'copy',c,gate,point))
    p2,c2=ctx.Pipe();g2=ctx.Event();w2=ctx.Process(target=initialize,args=(m.target.path,c2,g2,None,settings.path if entry=='cli' else None))
    try:
        w.start();checkpoint=receive(p);assert checkpoint['event']=='checkpoint'
        before=state(m.destination);w2.start();assert receive(p2)['event']=='started'
        assert not p2.poll(.1),'init must wait for reservation guard'
        assert state(m.destination)==before
        gate.set();copied=receive(p);result=receive(p2)
        w.join(10);w2.join(10)
        assert w.exitcode==w2.exitcode==0 and copied['result']['status']=='committed_inactive'
        assert result['event']=='error' if entry=='api' else result['exit_code']!=0
        assert m.target.store_info()['metadata']['origin_kind']=='migration'
        with pytest.raises(S02Error):m.target.assert_writable()
        evidence('reservation_race_migration_first',point=point,entry=entry,checkpoint=checkpoint,copy=copied,init=result)
    finally:
        for worker in (w,w2):
            if worker.pid:stop(worker)

def test_fresh_init_wins_before_migration_reservation(tmp_path):
    m,r,_=make_migration(tmp_path,empty=True);ctx=mp.get_context('spawn')
    p,c=ctx.Pipe();gate=ctx.Event();w=ctx.Process(target=initialize,args=(m.target.path,c,gate,'before_fresh_init'))
    p2,c2=ctx.Pipe();g2=ctx.Event();w2=ctx.Process(target=protocol,args=(replace(m.settings,timeout=5000),m.source,r,'copy',c2,g2))
    try:
        w.start();assert receive(p)['event']=='started';checkpoint=receive(p);assert checkpoint['event']=='checkpoint'
        w2.start();assert not p2.poll(.3);assert not m.destination.exists()
        gate.set();fresh=receive(p);copy=receive(p2);w.join(10);w2.join(10)
        assert w.exitcode==w2.exitcode==0 and fresh['exit_code']==0 and copy['event']=='error'
        assert m.target.store_info()['metadata']['origin_kind']=='fresh';m.target.assert_writable()
        assert not reservation.reserved(m.destination)
        evidence('reservation_race_fresh_first',checkpoint=checkpoint,init=fresh,copy=copy)
    finally:
        for worker in (w,w2):
            if worker.pid:stop(worker)

@pytest.mark.parametrize('point',['before_reserve','reservation_durable'])
def test_exception_and_restart_preserve_reservation_boundary(tmp_path,point):
    m,r,_=make_migration(tmp_path,empty=True)
    def fault(p,c):
        if p==point:raise OSError('synthetic reservation ACK loss')
    m.hook=fault
    with pytest.raises(OSError):m.copy(r,offline=True)
    receipt=r.read_bytes();m.hook=lambda *a:None
    if point=='before_reserve':
        assert not reservation.reserved(m.destination)
        assert m.copy(r,offline=True,resume=True)['status']=='committed_inactive'
    else:
        assert not m.destination.exists() and reservation.reserved(m.destination)
        assert m.reconcile(r,offline=True)['status']=='partial'
        with pytest.raises(S02Error):m.target.initialize(create_parent=True)
        with pytest.raises(S02Error):m.copy(r,offline=True,resume=True)
    assert r.read_bytes()==receipt

@pytest.mark.parametrize('value',[b'',b'{}\n',b'not-json'])
def test_invalid_marker_blocks_missing_and_zero_database(tmp_path,value):
    m,r,_=make_migration(tmp_path,empty=True)
    reservation.namespace(m.destination).mkdir()
    reservation.marker(m.destination).write_bytes(value)
    for exists in (False,True):
        if exists:
            m.destination.mkdir();m.target.path.touch()
        before=state(m.destination)
        with pytest.raises(S02Error):m.target.initialize(create_parent=True)
        assert state(m.destination)==before and reservation.marker(m.destination).read_bytes()==value

def test_fresh_init_rollback_can_retry_without_migration_reservation(tmp_path):
    m,r,_=make_migration(tmp_path,empty=True)
    def fault(p,c):
        if p=='before_init_commit':raise OSError('synthetic fresh init rollback')
    with pytest.raises(S02Error):Repository(m.target.path,_hook=fault).initialize(create_parent=True)
    assert not reservation.reserved(m.destination)
    m.target.initialize();m.target.assert_writable()
    assert m.target.store_info()['metadata']['origin_kind']=='fresh'

def test_active_migration_requires_marker_binding_for_idempotent_init(tmp_path):
    m,r,_=make_migration(tmp_path,empty=True);m.copy(r,offline=True)
    m.activate(r,offline=True,confirm=True,operator='SYNTHETIC')
    before=state(m.destination);mark=reservation.marker(m.destination)
    body=json.loads(mark.read_bytes());body['target_store_id']='wrong'
    mark.write_text(json.dumps(body)+'\n')  # synthetic corruption, never an application repair
    with pytest.raises(S02Error):m.target.initialize()
    assert state(m.destination)==before

@pytest.mark.parametrize('name,alias',[('CaseTarget','casetarget'),('caf\u00e9','cafe\u0301')])
@pytest.mark.parametrize('point',['reservation_durable','after_reserve'])
def test_filesystem_name_aliases_share_reservation(tmp_path,name,alias,point):
    from dacn_s02.migration import Migration
    original,r,_=make_migration(tmp_path,empty=True)
    m=Migration(replace(original.settings,state=original.destination.with_name(name)),original.source)
    def stop(p,c):
        if p==point:raise OSError('synthetic reservation stop')
    m.hook=stop
    with pytest.raises(OSError):m.copy(r,offline=True)
    equivalent=m.destination.with_name(alias)
    # macOS baseline is case/normalization-insensitive; assert the premise,
    # never skip the alias case based on the implementation's path normalization.
    assert reservation.marker(equivalent).samefile(reservation.marker(m.destination))
    before=state(m.destination);raw=reservation.marker(m.destination).read_bytes()
    with pytest.raises(S02Error):Repository(equivalent/'s02.sqlite3').initialize(create_parent=True)
    assert state(m.destination)==before and reservation.marker(m.destination).read_bytes()==raw

def test_namespace_creation_kill_has_no_target_reservation_effects(tmp_path):
    m,r,_=make_migration(tmp_path,empty=True);ctx=mp.get_context('spawn')
    p,c=ctx.Pipe();gate=ctx.Event();w=ctx.Process(target=protocol,args=(m.settings,m.source,r,'copy',c,gate,'reservation_namespace_created'));w.start()
    try:assert receive(p)['event']=='checkpoint'
    finally:stop(w)
    assert w.exitcode==-signal.SIGKILL and not m.destination.exists()
    assert not reservation.reserved(m.destination)
    assert m.reconcile(r,offline=True)['status']=='missing'
    assert m.copy(r,offline=True,resume=True)['status']=='committed_inactive'

def test_receipt_identity_ignores_json_member_order_and_whitespace(tmp_path):
    m,r,_=make_migration(tmp_path,empty=True);expected=m.copy(r,offline=True)
    original=r.read_bytes();value=json.loads(original)
    alternate=r.with_name('same-identity.json')
    alternate.write_text(json.dumps(dict(reversed(list(value.items()))),indent=3)+'\n')
    raw=alternate.read_bytes();marker=reservation.marker(m.destination).read_bytes()
    assert m.reconcile(alternate,offline=True)==expected
    assert m.copy(alternate,offline=True,resume=True)==expected
    first=m.activate(alternate,offline=True,confirm=True,operator='SYNTHETIC')
    assert m.activate(r,offline=True,confirm=True,operator='SYNTHETIC retry')==first
    m.target.initialize()
    assert r.read_bytes()==original and alternate.read_bytes()==raw and reservation.marker(m.destination).read_bytes()==marker
