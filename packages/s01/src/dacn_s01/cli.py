"""Local adapter. Requirement validation and revision belong to Service."""

import argparse
from decimal import Decimal, DecimalException
import os
from pathlib import Path
import re
import sqlite3
import sys
import tomllib

from .codec import CodecError, serialize_json
from .envelope import EnvelopeInvariantError
from .local_io import LocalError, Paths, load_settings, publish_new, read_receipt, receipt_bytes, resolved, same_location, text_argument
from .repository import Repository, RepositoryError
from .service import Service


class UsageError(Exception):
    pass


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise UsageError(message)


def number(text):
    if re.fullmatch(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?", text) is None:
        raise argparse.ArgumentTypeError("expected a JSON numeric token")
    try:
        value = Decimal(text)
        if not value.is_finite():
            raise ValueError
        return value
    except (DecimalException, ValueError) as exc:
        raise argparse.ArgumentTypeError("number cannot be represented exactly") from exc


def parser():
    result = Parser(prog="python -m dacn_s01", allow_abbrev=False)
    result.add_argument("--config")
    result.add_argument("--state-dir")
    commands = result.add_subparsers(dest="command", required=True, parser_class=Parser)
    commands.add_parser("init", allow_abbrev=False)
    submit = commands.add_parser("submit", allow_abbrev=False)
    submit.add_argument("--mode", required=True)
    submit.add_argument("--input", required=True)
    submit.add_argument("--receipt", required=True)
    submit.add_argument("--spec-id")
    submit.add_argument("--base-revision", type=number)
    submit.add_argument("--output")
    run = commands.add_parser("show-run", allow_abbrev=False)
    selector = run.add_mutually_exclusive_group(required=True)
    selector.add_argument("--run-id")
    selector.add_argument("--receipt")
    run.add_argument("--output")
    snapshot = commands.add_parser("show-snapshot", allow_abbrev=False)
    snapshot.add_argument("--snapshot-id")
    snapshot.add_argument("--spec-id")
    snapshot.add_argument("--revision", type=number)
    snapshot.add_argument("--output")
    source = commands.add_parser("show-source", allow_abbrev=False)
    source.add_argument("--source-id", required=True)
    source.add_argument("--output", required=True)
    runs = commands.add_parser("list-runs", allow_abbrev=False)
    runs.add_argument("--spec-id", required=True)
    runs.add_argument("--output")
    return result


def _cli_hook(point):
    """Private test synchronization seam, unavailable through product flags."""


def _stderr(message):
    try:
        sys.stderr.write("S01: " + message + "\n")
        sys.stderr.flush()
    except (OSError, UnicodeError):
        pass


def _stdout(raw):
    try:
        written = sys.stdout.buffer.write(raw)
        if written != len(raw):
            raise OSError("Incomplete stdout write")
        sys.stdout.buffer.flush()
    except OSError:
        # Prevent Python's shutdown flush from replacing exit 3 with exit 120.
        with open(os.devnull, "wb") as sink:
            os.dup2(sink.fileno(), sys.stdout.fileno())
        raise


def main(argv=None):
    recovery = None
    phase = "configuration"
    try:
        args = parser().parse_args(argv)
        if args.command == "show-snapshot":
            by_id = args.snapshot_id is not None
            by_pair = args.spec_id is not None and args.revision is not None
            if by_id == by_pair or (by_id and (args.spec_id is not None or args.revision is not None)):
                raise UsageError("choose --snapshot-id or both --spec-id and --revision")
            if by_pair and (args.revision < 1 or args.revision != args.revision.to_integral_value()):
                raise UsageError("--revision must be a positive integer")
        settings = load_settings(args.config, args.state_dir)
        receipt = None
        if args.command == "show-run" and args.receipt is not None:
            receipt = read_receipt(resolved(args.receipt))
            if settings.state_dir is not None and not same_location(settings.state_dir, Path(receipt["state_dir"])):
                raise LocalError("Configured state directory conflicts with receipt; specify the original store")
        state = settings.state_dir or (Path(receipt["state_dir"]) if receipt else None)
        if state is None:
            raise LocalError("No state directory: supply --state-dir, TOML state_dir or show-run --receipt")
        reads = [settings.config_path]
        if args.command == "submit":
            reads.append(resolved(args.input))
        elif receipt:
            reads.append(resolved(args.receipt))
        paths = Paths(settings, state, reads)
        paths.check_store()
        repository = Repository(paths.db, timeout=settings.busy_timeout_ms / 1000)
        if args.command == "init":
            if not paths.state_dir.exists():
                paths.writable(paths.state_dir)
                paths.state_dir.mkdir(mode=0o700)  # Existing parent required; no hidden tree creation.
            paths.check_store()
            repository.initialize()
            _stdout(serialize_json({"state_dir": str(paths.state_dir), "database": str(paths.db)}) + b"\n")
            return 0
        output = paths.artifact(args.output) if getattr(args, "output", None) else None
        if args.command == "submit":
            # Syntax belongs to argparse; semantically wrong but representable
            # routing stays in the original request for Service to reject.
            context = {"mode": args.mode, "spec_id": args.spec_id, "base_revision": args.base_revision}
            for value in (args.mode, args.spec_id):
                if value is not None:
                    value.encode("utf-8", "strict")
            serialize_json(context)
            source_path = resolved(args.input)
            if not source_path.is_file():
                raise LocalError("Input must be a readable regular file")
            receipt_path = paths.artifact(args.receipt)
            if output == receipt_path:
                raise LocalError("Receipt and export paths must differ")
            repository.verify()  # Missing/foreign stores are never initialized.
            raw = source_path.read_bytes()
            service = Service(repository)
            run_id = service.allocate_run_id()
            recovery = f"Reconcile with show-run --receipt {ascii(str(receipt_path))}; run_id={run_id}. Do not resubmit automatically."
            phase = "receipt publication/flush (no S01 submit started)"
            publish_new(receipt_path, receipt_bytes(run_id, paths.state_dir), paths)
            _cli_hook("receipt_ready")
            paths.check_store()
            phase = "submission; commit outcome may require lookup"
            value = service.submit(raw, context, run_id=run_id, source_kind="json_file", source_label=str(source_path))
            _cli_hook("after_submit")
            code = {"validated": 0, "rejected": 2, "failed": 3}[value["status"]]
        else:
            phase = "lookup"
            if args.command == "show-run":
                identifier = receipt["run_id"] if receipt else text_argument(args.run_id)
                value = repository.get_run(identifier)
            elif args.command == "show-snapshot":
                if args.snapshot_id is not None:
                    value = repository.get_snapshot(text_argument(args.snapshot_id))
                else:
                    # SQLite revisions cannot exceed signed 64-bit storage.
                    spec = text_argument(args.spec_id)
                    if args.revision > 9223372036854775807:
                        repository.verify()
                        value = None
                    else:
                        value = repository.get_snapshot_revision(spec, int(args.revision))
            elif args.command == "show-source":
                value = repository.get_source(text_argument(args.source_id))
            else:
                value = repository.list_runs(text_argument(args.spec_id))
            if value is None:
                _stderr("Record not found. This does not prove a previous submission failed; it may still be running or need commit reconciliation.")
                return 4
            code = 0
        phase = "result delivery; stored records are unchanged"
        raw = value if args.command == "show-source" else serialize_json(value) + b"\n"
        _cli_hook("before_output")
        if output is not None:
            publish_new(output, raw, paths)
        if args.command != "show-source":
            _stdout(raw)
        return code
    except UsageError as exc:
        _stderr("Usage error: " + str(exc))
        return 64
    except (LocalError, OSError, UnicodeError, CodecError, EnvelopeInvariantError,
            RepositoryError, sqlite3.Error, tomllib.TOMLDecodeError, ValueError) as exc:
        detail = str(exc) if isinstance(exc, LocalError) else type(exc).__name__
        _stderr(f"{phase} failed: {detail}.")
        if recovery:
            _stderr(recovery)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
