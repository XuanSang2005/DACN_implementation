"""Local-only path guards, TOML configuration and no-clobber artifact publication.

Directories must be controlled by the local user. Static symlinks/aliases are
checked; this is not a sandbox against concurrent hostile directory renames.
"""

from dataclasses import dataclass
import os
from pathlib import Path
import stat
import tomllib
from uuid import uuid4

from .codec import parse_json, serialize_json

DATABASE_NAME = "s01.sqlite3"
RECEIPT_VERSION = "1"


class LocalError(Exception):
    """A controlled operational error before intake or during delivery."""


def text_argument(value):
    if type(value) is not str or not value or "\x00" in value:
        raise LocalError("Expected a nonempty argument without NUL")
    try:
        value.encode("utf-8", "strict")
        serialize_json(value)
    except (UnicodeError, ValueError) as exc:
        raise LocalError("Argument cannot be represented exactly as operational metadata") from exc
    return value


def resolved(value, base=None):
    value = Path(text_argument(str(value)))
    path = ((base or Path.cwd()) / value).resolve()
    text_argument(str(path))
    return path


def same_location(left, right):
    """Include case/Unicode filesystem aliases without normalizing user text."""
    return left == right or (left.exists() and right.exists() and left.samefile(right))


def within(path, directory):
    return path.is_relative_to(directory) or any(same_location(parent, directory) for parent in (path, *path.parents))


@dataclass(frozen=True)
class Settings:
    state_dir: Path | None
    busy_timeout_ms: int
    dataset_roots: tuple[Path, ...]
    config_path: Path | None


def load_settings(config=None, state_dir=None):
    path = resolved(config) if config is not None else None
    values = tomllib.loads(path.read_text(encoding="utf-8")) if path else {}
    if values.keys() - {"state_dir", "busy_timeout_ms", "dataset_roots"}:
        raise LocalError("Unknown TOML configuration key")
    timeout = values.get("busy_timeout_ms", 5000)
    if type(timeout) is not int or not 0 <= timeout <= 2147483647:
        raise LocalError("busy_timeout_ms must be an integer from 0 to 2147483647")
    roots = values.get("dataset_roots", [])
    if type(roots) is not list or any(type(v) is not str or not v for v in roots):
        raise LocalError("dataset_roots must be an array of nonempty paths")
    base = path.parent if path else Path.cwd()
    configured = values.get("state_dir")
    if "state_dir" in values and (type(configured) is not str or not configured):
        raise LocalError("state_dir must be a nonempty path")
    state = resolved(state_dir) if state_dir is not None else resolved(configured, base) if configured else None
    datasets = tuple(resolved(v, base) for v in roots)
    if any(not root.is_dir() for root in datasets):
        raise LocalError("Each dataset root must be an existing directory so filesystem aliases can be checked")
    return Settings(state, timeout, datasets, path)


class Paths:
    def __init__(self, settings, state_dir, read_files=()):
        self.state_dir = resolved(state_dir)
        self.dataset_roots = settings.dataset_roots
        self.read_files = tuple(resolved(p) for p in read_files if p is not None)
        self.db = self.state_dir / DATABASE_NAME

    def writable(self, value):
        path = resolved(value)
        if any(within(path, root) for root in self.dataset_roots):
            raise LocalError("Write path is inside a declared dataset root")
        for source in self.read_files:
            if same_location(path, source):
                raise LocalError("Write path aliases an input, configuration or receipt source")
        return path

    def check_store(self):
        self.writable(self.state_dir)
        for suffix in ("", "-journal", "-wal", "-shm"):
            path = Path(str(self.db) + suffix)
            self.writable(path)
            if os.path.lexists(path):
                info = path.lstat()
                # SQLite may modify/recover these files even during lookup.
                # Reject all linked/nonregular sidecars, not just known inputs.
                if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                    raise LocalError("Database and sidecars must be regular files without symlink/hard-link aliases")

    def artifact(self, value):
        # Test the original entry as well as the resolved destination. Dangling
        # symlinks count as existing artifacts and must never be overwritten.
        original = Path(value).absolute()
        path = self.writable(original)
        if within(path, self.state_dir):
            raise LocalError("Receipt/export must be outside the state directory")
        if os.path.lexists(original) or os.path.lexists(path):
            raise LocalError("Artifact already exists; never overwrite it. For a receipt use show-run --receipt")
        if not path.parent.is_dir():
            raise LocalError("Artifact parent directory must already exist")
        self.writable(path.parent)
        return path


def _publish_hook(point):
    """Private harness seam; no environment variable or CLI flag enables it."""


def publish_new(path, raw, paths):
    """Publish complete bytes with link(2) create-only semantics, then fsync dir.

    Failure after link may leave a complete final file. Never unlink that file;
    its presence is not a success claim. Only this call's private temp is removed.
    """
    path = paths.artifact(path)
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    temporary = ".dacn-" + str(uuid4()) + ".tmp"
    created = False
    try:
        paths.writable(path.parent / temporary)
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                             0o600, dir_fd=directory)
        created = True
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
            stream.flush()
            _publish_hook("before_file_fsync")
            os.fsync(stream.fileno())
        _publish_hook("before_link")
        paths.artifact(path)
        os.link(temporary, path.name, src_dir_fd=directory, dst_dir_fd=directory, follow_symlinks=False)
        _publish_hook("after_link")
        os.unlink(temporary, dir_fd=directory)
        created = False
        _publish_hook("before_directory_fsync")
        os.fsync(directory)
        _publish_hook("published")
    finally:
        try:
            if created:
                os.unlink(temporary, dir_fd=directory)
        finally:
            os.close(directory)


def receipt_bytes(run_id, state_dir):
    return serialize_json({"receipt_version": RECEIPT_VERSION, "run_id": text_argument(run_id),
                           "state_dir": str(resolved(state_dir))}) + b"\n"


def read_receipt(path):
    value = parse_json(Path(path).read_bytes())
    if type(value) is not dict or value.keys() != {"receipt_version", "run_id", "state_dir"}:
        raise LocalError("Invalid receipt structure")
    if value["receipt_version"] != RECEIPT_VERSION:
        raise LocalError("Unsupported receipt version")
    text_argument(value["run_id"])
    text_argument(value["state_dir"])
    original = Path(value["state_dir"])
    if not original.is_absolute() or str(resolved(original)) != value["state_dir"]:
        raise LocalError("Receipt must name a resolved absolute state directory")
    return value
