"""Test-only process protocol over pipes; never a product CLI or receipt."""

import base64
import json
import sqlite3
import sys
import time

import simplejson
import simplejson.encoder as encoder

from dacn_s01.codec import parse_json
from dacn_s01.repository import Repository
from dacn_s01.service import Service


def main():
    config = json.loads(sys.stdin.readline())
    mode = config['backend']
    simplejson._toggle_speedups(mode == 'c')
    calls = {'c':0, 'python':0}
    factory_name = 'c_make_encoder' if mode == 'c' else '_make_iterencode'
    original = getattr(encoder, factory_name)
    assert original is not None
    def factory(*args, **kwargs):
        calls[mode] += 1
        return original(*args, **kwargs)
    setattr(encoder, factory_name, factory)

    def emit(event, **data):
        print(json.dumps({'event':event, 'role':config['role'], 'time_ns':time.monotonic_ns(), **data}), flush=True)

    def hook(point, connection):
        emit(point)
        if point == 'before_begin':
            connection.set_trace_callback(lambda sql: emit('sql_begin_attempt') if sql == 'BEGIN IMMEDIATE' else None)
            if config.get('probe_busy'):
                connection.execute('PRAGMA busy_timeout=0')
                try:
                    connection.execute('BEGIN IMMEDIATE')
                except sqlite3.OperationalError as exc:
                    assert exc.sqlite_errorcode == sqlite3.SQLITE_BUSY
                    emit('busy_observed', sqlite_errorcode=exc.sqlite_errorcode)
                else:
                    raise AssertionError('Expected a real competing writer lock')
                finally:
                    connection.execute('PRAGMA busy_timeout=5000')
        if point == config.get('stop_at'):
            assert sys.stdin.readline().strip() == 'continue'

    repository = Repository(config['database'], _hook=hook)
    result = Service(repository).submit(base64.b64decode(config['raw']),
        parse_json(config['request_json'].encode()), run_id=config['run_id'])
    emit('result', envelope=json.loads(__import__('dacn_s01.codec', fromlist=['serialize_json']).serialize_json(result)),
         encoder_calls=calls, backend=mode)


if __name__ == '__main__':
    main()
