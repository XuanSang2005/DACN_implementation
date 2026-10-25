"""Receipt-bound SQLite rollback-journal reconciliation for H1 only.

The immutable connection reads ONLY immutable identity/DDL/registry/activation,
never Records, heads or eligibility. SQLite itself restores an interrupted
transaction; this module has no row repair, init, activation or migration SQL.
Ordinary progress/legacy checked reads remain read-only and unchanged.
"""
import sqlite3
import stat
from pathlib import Path

from .errors import require,storage_error,S02Error
from . import reservation,store_profiles


def reconcile(repo,store_id):
    if store_id is None:return
    journal=Path(str(repo.path)+'-journal')
    if not journal.exists():return
    for path in (repo.path,journal):
        info=path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink!=1:raise storage_error('H1 recovery requires regular unaliased DB/journal')
    with journal.open('rb') as stream:header=stream.read(8)
    if header!=bytes.fromhex('d9d505f920a163d7'):return
    if reservation.reserved(repo.path.parent):raise storage_error('H1 recovery refuses migration-reserved state')
    identity=None;connection=None
    try:
        identity=sqlite3.connect(repo.path.as_uri()+'?mode=ro&immutable=1',uri=True,autocommit=True,timeout=repo.timeout)
        identity.row_factory=sqlite3.Row
        require(repo._structure(identity)==2,'h1_recovery_db2')
        metadata=identity.execute('SELECT store_id,origin_kind FROM store_metadata').fetchall()
        require(len(metadata)==1 and metadata[0]['origin_kind']=='fresh','h1_recovery_fresh_only')
        info=store_profiles.check(identity,path=repo.path,writable=True)
        require(info['metadata']['store_id']==store_id,'receipt_store_identity')
        identity.close();identity=None
        # The engine obtains recovery locks and rolls back a hot journal before
        # any H1 work. No canonical value from the identity view is published.
        connection=repo._connect(write=True);connection.execute('BEGIN IMMEDIATE')
        repo._write_gate(connection)
        checked=store_profiles.check(connection,path=repo.path,writable=True)
        require(checked['metadata']['store_id']==store_id and checked['metadata']['origin_kind']=='fresh','h1_recovery_identity')
        repo._check(connection)
        connection.execute('ROLLBACK')
    except S02Error:raise
    except (sqlite3.Error,OSError) as exc:
        raise storage_error('H1 hot journal reconciliation outcome unknown; keep receipt identity') from exc
    finally:
        if identity:identity.close()
        if connection:
            if connection.in_transaction:connection.execute('ROLLBACK')
            connection.close()
