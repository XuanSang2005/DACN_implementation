"""Local migration reservation, outside SQLite transactions and target directories.

The existing parent directory inode is the lock: no lock-file creation/removal
race. All cooperating init/copy callers hold it through their first effects.
The create-only reservation survives rollback and process death; it is never
removed by normal init or migration recovery.
"""
from contextlib import contextmanager
import fcntl
import os
import stat
import time

from .errors import S02Error, storage_error
from .local_io import writable, within


NAMESPACE='.dacn-s02-migration-reservations'


def namespace(destination):return destination.parent/NAMESPACE


def marker(destination):
    # Preserve the leaf name: case/Unicode aliases must resolve to the SAME
    # reservation on filesystems that consider those directory names equal.
    return namespace(destination)/destination.name


def check_paths(settings,destination,source):
    """Guard derived writes too, including existing filesystem aliases.

    Validate the original components before resolving for the shared policy.
    Keep the original leaf spelling for case/Unicode reservation identity.
    Nothing here creates, moves, repairs, or removes an existing namespace.
    """
    for path in (namespace(destination),marker(destination)):
        if any(p.is_symlink() for p in (path,*path.parents)):
            raise S02Error('MIGRATION_PATH_INVALID','persistence',
                           'Symbolic reservation path components are not allowed')
        checked=writable(settings,path)
        if within(checked,source):
            raise S02Error('MIGRATION_PATH_INVALID','persistence',
                           'Migration reservation must be outside the source')
    leaf=marker(destination)
    if os.path.lexists(leaf):
        info=leaf.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink!=1:refuse()


def reserved(destination):
    # Even an incomplete/invalid marker is a reservation, never fresh state.
    return os.path.lexists(marker(destination))


def refuse():
    raise S02Error('MIGRATION_PARTIAL','persistence',
                   'Migration reservation forbids fresh initialization; no reset performed')


@contextmanager
def guard(destination,timeout):
    fd=None
    try:
        try:fd=os.open(destination.parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        except OSError as exc:raise storage_error('Initialization/reservation filesystem guard failed') from exc
        deadline=time.monotonic()+timeout
        while True:
            try:
                fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic()>=deadline:
                    raise storage_error('Initialization/reservation guard busy; retry same operation')
                time.sleep(.01)
        space=namespace(destination)
        if destination.name.casefold()==NAMESPACE.casefold():refuse()
        if os.path.lexists(space) and not stat.S_ISDIR(space.lstat().st_mode):refuse()
        yield fd
    finally:
        if fd is not None:os.close(fd)  # releases flock, including on process death


def read(destination):
    fd=os.open(marker(destination),os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd,'rb') as stream:
        s=os.fstat(stream.fileno())
        if not stat.S_ISREG(s.st_mode) or s.st_nlink!=1:refuse()
        return stream.read()


def publish(destination,raw,directory,hook,*,settings,source):
    """Caller holds guard; partial publication also permanently blocks fresh init."""
    check_paths(settings,destination,source)
    space=namespace(destination)
    if not space.exists():
        space.mkdir()
        hook('reservation_namespace_created',None)
    folder=os.open(space,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:
        fd=os.open(marker(destination),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'wb') as stream:
            hook('reservation_created',None)
            stream.write(raw);stream.flush();os.fsync(stream.fileno())
        hook('reservation_before_dir_sync',None)
        os.fsync(folder);os.fsync(directory)
        if read(destination)!=raw:refuse()
        hook('reservation_durable',None)
    finally:os.close(folder)
