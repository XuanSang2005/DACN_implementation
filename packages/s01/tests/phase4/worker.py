"""Subprocess harness: instrument installed CLI without product test flags."""

import json
import os
from pathlib import Path
import runpy
import socket
import sys
from importlib.metadata import version

import dacn_s01
import simplejson
from simplejson import encoder
from dacn_s01 import cli, local_io, repository

backend, evidence_file, control_fd, behavior = sys.argv[1:5]
arguments = sys.argv[5:]
options = json.loads(behavior)
simplejson._toggle_speedups(backend == "c")
counts = {"c": 0, "python": 0}
if backend == "c":
    original_c = encoder.c_make_encoder
    assert original_c is not None

    def observed_c(*args, **kwargs):
        counts["c"] += 1
        return original_c(*args, **kwargs)

    encoder.c_make_encoder = observed_c
original_python = encoder._make_iterencode


def observed_python(*args, **kwargs):
    counts["python"] += 1
    return original_python(*args, **kwargs)


encoder._make_iterencode = observed_python
control = socket.socket(fileno=int(control_fd)) if control_fd != "-" else None
events = []


def point(name):
    if name in options.get("pause", []):
        event = {"event": name, "pid": os.getpid()}
        events.append(event)
        control.sendall(json.dumps(event).encode() + b"\n")
        assert control.recv(1) == b"+", "parent failed to release synchronized point"


cli._cli_hook = point
local_io._publish_hook = point
original_init = repository.Repository.__init__


def init(self, *args, **kwargs):
    kwargs["_hook"] = lambda name, connection: point(name)
    original_init(self, *args, **kwargs)


repository.Repository.__init__ = init
if "fsync_fail" in options:
    original_fsync = os.fsync
    fsync_calls = 0

    def fail_fsync(fd):
        global fsync_calls
        fsync_calls += 1
        if fsync_calls == options["fsync_fail"]:
            raise OSError("synthetic fsync failure")
        return original_fsync(fd)

    os.fsync = fail_fsync

if options.get("link_fail"):
    def fail_link(*args, **kwargs):
        raise OSError("synthetic link failure")
    os.link = fail_link

sys.argv = ["dacn_s01", *arguments]
try:
    runpy.run_module("dacn_s01", run_name="__main__")
finally:
    Path(evidence_file).write_text(json.dumps({"backend": backend, "counts": counts,
        "package": version("dacn-s01"), "import_path": dacn_s01.__file__, "events": events}) + "\n")
    if control:
        control.close()
