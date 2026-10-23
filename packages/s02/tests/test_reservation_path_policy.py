"""P3-02: derived writes, resumed operations, and filesystem alias controls.

All stores/roots are new synthetic fixtures. Inventory includes filenames and
bytes, so a refusal that silently adds a marker or receipt is a failure.
"""
from dataclasses import replace
from hashlib import sha256
import json
import os
import pytest

from dacn_s02 import reservation
from dacn_s02.errors import S02Error
from dacn_s02.migration import Migration
from helpers import evidence
from migration_fixtures import make_migration


def inventory(root):
    result={}
    for path in sorted(root.rglob('*')):
        name=str(path.relative_to(root))
        if path.is_symlink():result[name]=('symlink',os.readlink(path))
        elif path.is_dir():result[name]=('directory',)
        else:result[name]=('file',sha256(path.read_bytes()).hexdigest())
    return result


def prepare(tmp_path,phase):
    m,receipt,_=make_migration(tmp_path,empty=True)
    if phase=='receipt_only':
        def stop(point,connection):
            if point=='receipt_durable':raise OSError('synthetic receipt ACK loss')
        m.hook=stop
        with pytest.raises(S02Error) as caught:m.copy(receipt,offline=True)
        assert caught.value.error['code']=='MIGRATION_RECEIPT_INVALID'
        assert isinstance(caught.value.__cause__,OSError)
        assert receipt.is_file() and not reservation.namespace(m.destination).exists()
        m.hook=lambda *args:None
    elif phase=='committed':
        assert m.copy(receipt,offline=True)['status']=='committed_inactive'
    return m,receipt


@pytest.mark.parametrize('phase',['fresh','receipt_only','committed'])
@pytest.mark.parametrize('kind',['protected','s01','checkout'])
@pytest.mark.parametrize('instance',['new','reused'])
def test_namespace_policy_refuses_before_effects_on_copy_and_resume(tmp_path,phase,kind,instance):
    m,receipt=prepare(tmp_path,phase)
    space=reservation.namespace(m.destination);space.mkdir(exist_ok=True)
    (space/'sentinel').write_bytes(b'SYNTHETIC protected content')
    settings=m.settings
    if kind=='protected':settings=replace(settings,protected=(space,))
    elif kind=='s01':settings=replace(settings,stores={'synthetic':space/'s01.sqlite3'})
    else:
        (space/'AGENTS.md').write_text('Synthetic checkout fixture\n')
        (space/'pyproject.toml').write_text('[tool.synthetic]\n')
    before=inventory(tmp_path)
    with pytest.raises(S02Error):
        if instance=='new':m=Migration(settings,m.source)
        else:m.settings=settings
        m.copy(receipt,offline=True,resume=phase!='fresh')
    assert inventory(tmp_path)==before
    evidence('reservation_policy_refusal',phase=phase,guard_kind=kind,instance=instance,unchanged=True)


@pytest.mark.parametrize('placement',['namespace','marker'])
@pytest.mark.parametrize('resume',[False,True])
def test_source_directory_is_never_a_reservation_write_path(tmp_path,placement,resume):
    m,receipt,_=make_migration(tmp_path,empty=True)
    # Build an independent synthetic receipt for the final fixture layout. It
    # has valid IDs/fingerprint; refusal must not rely on a malformed receipt.
    fingerprint=m.inspect(offline=True)['source_inventory_sha256']
    space=reservation.namespace(m.destination)
    if placement=='marker':space.mkdir()
    source=space if placement=='namespace' else reservation.marker(m.destination)
    m.source.rename(source)
    if resume:
        receipt.write_text(json.dumps(dict(receipt_version='s02-migration/1',
            plan_version='s02-2a-storage-plan/0.1.0-draft.2',source_state_dir=str(source),
            destination_state_dir=str(m.destination),source_inventory_sha256=fingerprint,
            migration_id='00000000-0000-4000-8000-000000000001',
            target_store_id='00000000-0000-4000-8000-000000000002',
            activation_id='00000000-0000-4000-8000-000000000003'))+'\n')
    before=inventory(tmp_path)
    with pytest.raises(S02Error):
        Migration(m.settings,source).copy(receipt,offline=True,resume=resume)
    assert inventory(tmp_path)==before
    evidence('reservation_source_refusal',placement=placement,resume=resume,unchanged=True)


@pytest.mark.parametrize('name,alias',[('CaseRoot','caseroot'),('caf\u00e9','cafe\u0301')])
@pytest.mark.parametrize('phase',['fresh','receipt_only','committed'])
@pytest.mark.parametrize('kind',['protected','s01'])
def test_forbidden_root_filesystem_aliases_are_refused(tmp_path,name,alias,phase,kind):
    base=tmp_path/name;base.mkdir()
    m,receipt=prepare(base,phase)
    space=reservation.namespace(m.destination);space.mkdir(exist_ok=True)
    alias_space=tmp_path/alias/space.name
    assert alias_space.samefile(space),'Pinned filesystem must support this alias'
    settings=replace(m.settings,protected=(alias_space,)) if kind=='protected' else replace(
        m.settings,stores={'synthetic':alias_space/'s01.sqlite3'})
    before=inventory(tmp_path)
    with pytest.raises(S02Error):Migration(settings,m.source).copy(receipt,offline=True,resume=phase!='fresh')
    assert inventory(tmp_path)==before
    evidence('reservation_forbidden_alias',name=name,alias=alias,guard_kind=kind,phase=phase,unchanged=True)


@pytest.mark.parametrize('placement',['namespace','marker','hardlinked_marker'])
@pytest.mark.parametrize('phase',['fresh','receipt_only'])
def test_derived_link_alias_refuses_without_following_or_repairing(tmp_path,placement,phase):
    m,receipt=prepare(tmp_path,phase)
    space=reservation.namespace(m.destination)
    if placement=='namespace':space.symlink_to(m.source,target_is_directory=True)
    else:
        space.mkdir()
        leaf=reservation.marker(m.destination)
        if placement=='marker':leaf.symlink_to(m.source/'s02.sqlite3')
        else:os.link(m.source/'s02.sqlite3',leaf)
    before=inventory(tmp_path)
    # Reuse a previously constructed instance to exercise the operation guard.
    with pytest.raises(S02Error):m.copy(receipt,offline=True,resume=phase!='fresh')
    assert inventory(tmp_path)==before
    evidence('reservation_link_refusal',placement=placement,phase=phase,unchanged=True)


@pytest.mark.parametrize('name,alias',[('CaseTarget','casetarget'),('caf\u00e9','cafe\u0301')])
def test_allowed_name_alias_keeps_identity_and_resume(tmp_path,name,alias):
    old,receipt,_=make_migration(tmp_path,empty=True)
    m=Migration(replace(old.settings,state=old.destination.with_name(name)),old.source)
    first=m.copy(receipt,offline=True)
    assert reservation.marker(m.destination.with_name(alias)).samefile(reservation.marker(m.destination))
    # Receipt binds the original spelling. Repeated copy uses that identity and
    # leaves all bytes intact; the alias still refers to the same reservation.
    before=inventory(tmp_path)
    assert Migration(m.settings,m.source).copy(receipt,offline=True,resume=True)==first
    assert inventory(tmp_path)==before
    evidence('reservation_allowed_alias_resume',name=name,alias=alias,status=first['status'],unchanged=True)


def test_publish_rechecks_policy_after_before_reserve_checkpoint(tmp_path):
    m,receipt,_=make_migration(tmp_path,empty=True)
    space=reservation.namespace(m.destination)
    def protect(point,connection):
        if point=='before_reserve':
            space.mkdir()
            (space/'AGENTS.md').write_text('Synthetic checkpoint fixture\n')
            (space/'pyproject.toml').write_text('[tool.synthetic]\n')
    m.hook=protect
    with pytest.raises(S02Error):m.copy(receipt,offline=True)
    assert sorted(p.name for p in space.iterdir())==['AGENTS.md','pyproject.toml']
    assert not m.destination.exists()
    evidence('reservation_publish_recheck',no_marker=True,no_destination=True)
