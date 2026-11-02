"""LP-01 journal: immutable inputs/capture, atomic reserve/claim, no slot refunds."""
from contextlib import contextmanager
from pathlib import Path
import os
import sqlite3
import stat
import time

from .codec_boundary import encode, decode
from .errors import storage_error, require
from .repository import digest
from .validation import integer

VERSION = 's02-local-journal/1'
LIMITS = dict(max_calls=4, timeout_seconds=120, num_predict=4096, num_ctx=32768,
              retry=0, repair=0, body_bytes=1048576)
DDL = (
    'CREATE TABLE meta (id INTEGER PRIMARY KEY CHECK(id=1), value BLOB NOT NULL, sha TEXT NOT NULL)',
    'CREATE TABLE flow (id INTEGER PRIMARY KEY CHECK(id=1), value BLOB NOT NULL, sha TEXT NOT NULL, s01_claimed INTEGER NOT NULL DEFAULT 0 CHECK(s01_claimed IN (0,1)))',
    'CREATE TABLE work (command TEXT PRIMARY KEY, session TEXT NOT NULL, step INTEGER NOT NULL CHECK(step BETWEEN 0 AND 4), config BLOB NOT NULL, config_sha TEXT NOT NULL, request BLOB NOT NULL, request_sha TEXT NOT NULL, prompt BLOB NOT NULL, prompt_sha TEXT NOT NULL, claimed_ns INTEGER, capture BLOB, capture_sha TEXT, body BLOB, body_sha TEXT, UNIQUE(session,step))',
)


def _regular(path):
    for suffix in ('', '-journal', '-wal', '-shm'):
        p = Path(str(path) + suffix)
        if os.path.lexists(p):
            st = p.lstat()
            if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1:
                raise storage_error('Local journal/sidecar must be regular without links')


class Journal:
    def __init__(self, path, store_id):
        self.path = Path(path)
        self.store_id = store_id

    def initialize(self):
        _regular(self.path)
        fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
        os.close(fd)
        with sqlite3.connect(self.path, isolation_level=None) as c:
            c.execute('PRAGMA synchronous=FULL')
            c.execute('BEGIN IMMEDIATE')
            for sql in DDL:
                c.execute(sql)
            raw = encode(dict(version=VERSION, store_id=self.store_id, limits=LIMITS))
            c.execute('INSERT INTO meta VALUES (1,?,?)', (raw, digest(raw)))
            c.commit()
        c.close()
        directory = os.open(self.path.parent, os.O_RDONLY)
        try: os.fsync(directory)
        finally: os.close(directory)

    @contextmanager
    def connection(self, write=False):
        _regular(self.path)
        if not self.path.is_file():
            raise storage_error('Local journal missing; never recreated on resume')
        c = sqlite3.connect(self.path.as_uri() + ('?mode=rw' if write else '?mode=ro'),
                            uri=True, isolation_level=None, timeout=5)
        c.row_factory = sqlite3.Row
        try:
            c.execute('PRAGMA synchronous=FULL')
            c.execute('BEGIN IMMEDIATE' if write else 'BEGIN')
            self.check(c)
            yield c
            self.check(c)
            c.commit()
        except Exception:
            c.rollback()
            raise
        finally:
            c.close()

    def check(self, c):
        actual = {r[0] for r in c.execute("SELECT sql FROM sqlite_master WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%'")}
        require(actual == set(DDL), 'local_journal_ddl')
        rows = c.execute('SELECT * FROM meta').fetchall()
        require(len(rows) == 1, 'local_journal_meta')
        row = rows[0]
        require(digest(row['value']) == row['sha'], 'local_journal_meta_hash')
        require(encode(decode(row['value'])) == encode(dict(version=VERSION, store_id=self.store_id, limits=LIMITS)), 'local_journal_binding')
        for f in c.execute('SELECT * FROM flow'):
            require(digest(f['value']) == f['sha'], 'local_flow_hash')
        calls = 0
        for w in c.execute('SELECT * FROM work'):
            for field in ('config', 'request', 'prompt'):
                require(digest(w[field]) == w[field + '_sha'], 'local_work_hash')
            cfg = decode(w['config'])
            require(cfg['command_id'] == w['command'] and cfg['session_id'] == w['session'] and cfg['step'] == w['step'], 'local_work_identity')
            require(cfg['store_id'] == self.store_id and encode(cfg['limits']) == encode(LIMITS), 'local_work_store_limits')
            require(cfg['request_sha256'] == w['request_sha'] and cfg['prompt_sha256'] == w['prompt_sha'], 'local_work_input_pins')
            require((w['capture'] is None) == (w['body'] is None), 'local_capture_pair')
            if w['capture'] is not None:
                require(w['claimed_ns'] is not None and digest(w['capture']) == w['capture_sha'] and digest(w['body']) == w['body_sha'], 'local_capture_hash')
                meta = decode(w['capture'])
                require(meta['command_id'] == w['command'] and meta['request_sha256'] == w['request_sha'] and meta['body_sha256'] == w['body_sha'], 'local_capture_binding')
                require(len(w['body']) <= LIMITS['body_bytes'], 'local_capture_cap')
            calls += w['step'] != 0
        require(calls <= LIMITS['max_calls'], 'local_campaign_cap')

    def flow(self, value=None):
        with self.connection(write=value is not None) as c:
            row = c.execute('SELECT * FROM flow').fetchone()
            if row is None and value is not None:
                raw = encode(value)
                c.execute('INSERT INTO flow(id,value,sha) VALUES(1,?,?)', (raw, digest(raw)))
                return value
            if row is None: return None
            old = decode(row['value'])
            if value is not None: require(encode(old) == encode(value), 'local_campaign_flow_conflict')
            return old

    def claim_s01(self):
        with self.connection(True) as c:
            return c.execute('UPDATE flow SET s01_claimed=1 WHERE id=1 AND s01_claimed=0').rowcount == 1

    def reserve(self, cfg, request=b'', prompt=b''):
        require(integer(None,cfg['step']) and 0 <= cfg['step'] <= 4, 'local_step_integer')
        raw = encode(cfg)
        with self.connection(True) as c:
            prior = c.execute('SELECT * FROM work WHERE command=?', (cfg['command_id'],)).fetchone()
            if prior:
                require(prior['config'] == raw and prior['request'] == request and prior['prompt'] == prompt, 'local_reserve_conflict')
                return
            require(cfg['step'] == 0 or c.execute('SELECT COUNT(*) FROM work WHERE step>0').fetchone()[0] < LIMITS['max_calls'], 'local_budget_exhausted')
            c.execute('INSERT INTO work(command,session,step,config,config_sha,request,request_sha,prompt,prompt_sha) VALUES(?,?,?,?,?,?,?,?,?)',
                      (cfg['command_id'], cfg['session_id'], int(cfg['step']), raw, digest(raw), request, digest(request), prompt, digest(prompt)))

    def get(self, command):
        with self.connection() as c:
            row = c.execute('SELECT * FROM work WHERE command=?', (command,)).fetchone()
            return dict(row) if row else None

    def claim(self, command):
        with self.connection(True) as c:
            require(c.execute('SELECT 1 FROM work WHERE command=? AND step>0', (command,)).fetchone() is not None, 'local_claim_work')
            return c.execute('UPDATE work SET claimed_ns=? WHERE command=? AND claimed_ns IS NULL', (time.time_ns(), command)).rowcount == 1

    def capture(self, command, meta, body):
        raw = encode(meta)
        with self.connection(True) as c:
            row = c.execute('SELECT * FROM work WHERE command=?', (command,)).fetchone()
            require(row is not None and row['claimed_ns'] is not None, 'local_capture_after_claim')
            if row['capture'] is not None:
                require(row['capture'] == raw and row['body'] == body, 'local_capture_immutable')
                return
            c.execute('UPDATE work SET capture=?,capture_sha=?,body=?,body_sha=? WHERE command=?', (raw,digest(raw),body,digest(body),command))
