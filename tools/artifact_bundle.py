"""Verified local bundles; create-only extraction, no network or replacement."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
from collections import deque
import unicodedata
import shutil
import tarfile


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def safe_name(name):
    path=PurePosixPath(name)
    if not name or '\\' in name or '\x00' in name or path.is_absolute() or str(path)!=name or any(p in ('','.','..') for p in name.split('/')):
        raise ValueError('Unsafe bundle member: '+repr(name))
    return path



def checked_links(entries,root=None):
    """Resolve prospective links component by component, before any writes.

    Missing internal targets are allowed. Names that alias by Unicode/case are
    matched conservatively; ambiguous inventory leaves are refused. Existing
    destination links also participate in restore preflight. Forty expansions
    per path bound cycles and expanding loops without touching outside root.
    """
    def key(parts):return tuple(unicodedata.normalize('NFD',p).casefold() for p in parts)
    def target_parts(target):
        if (not isinstance(target,str) or not target or '\\' in target or '\x00' in target
                or PurePosixPath(target).is_absolute()):
            raise ValueError('Unsafe symlink target')
        return target.split('/')
    known={}
    for name,info in entries.items():
        path=safe_name(name)
        if info['kind'] not in ('file','symlink'):raise ValueError('Unsupported member type')
        identity=key(path.parts)
        if identity in known:raise ValueError('Ambiguous bundle member alias')
        known[identity]=info
        if info['kind']=='symlink':target_parts(info['target'])
    for name in entries:
        for parent in PurePosixPath(name).parents:
            if known.get(key(parent.parts),{}).get('kind') in ('file','symlink'):
                raise ValueError('Member has a non-directory parent')
    for name,info in entries.items():
        if info['kind']!='symlink':continue
        pending=deque(PurePosixPath(name).parts);resolved=[];expansions=0
        while pending:
            part=pending.popleft()
            if part in ('','.'):continue
            if part=='..':
                if not resolved:raise ValueError('Symlink escapes bundle root')
                resolved.pop();continue
            candidate=(*resolved,part);node=known.get(key(candidate))
            existing=root.joinpath(*candidate) if root is not None else None
            target=None
            if node is not None and node['kind']=='symlink':target=node['target']
            elif node is None and existing is not None and existing.is_symlink():target=os.readlink(existing)
            if target is not None:
                expansions+=1
                if expansions>40:raise ValueError('Symlink cycle or expansion limit exceeded')
                pending.extendleft(reversed(target_parts(target)))
                continue
            resolved.append(part)
            if pending and ((node is not None and node['kind']=='file') or
                    (node is None and existing is not None and existing.exists() and not existing.is_dir())):
                raise ValueError('Symlink traverses a non-directory')


def verify(archive,descriptor,inventory=None):
    archive=Path(archive);descriptor=Path(descriptor)
    spec=json.loads(descriptor.read_text())
    if spec['format']!=1:raise ValueError('Unknown bundle format')
    if archive.stat().st_size!=spec['size'] or digest(archive)!=spec['sha256']:
        raise ValueError('Bundle SHA-256/size mismatch')
    inventory=Path(inventory) if inventory else archive.parent/spec['inventory']
    if digest(inventory)!=spec['inventory_sha256']:raise ValueError('Inventory SHA-256 mismatch')
    entries=json.loads(inventory.read_text())
    if len(entries)!=spec['members']:raise ValueError('Inventory count mismatch')
    checked_links(entries)
    seen=set()
    with tarfile.open(archive,'r:gz') as package:
        for member in package:
            if member.name in seen or member.name not in entries:raise ValueError('Unexpected/duplicate member')
            seen.add(member.name);info=entries[member.name]
            if member.mode!=info['mode']:raise ValueError('Member mode mismatch')
            if info['kind']=='symlink':
                if not member.issym() or member.linkname!=info['target']:raise ValueError('Symlink mismatch')
            else:
                if not member.isfile() or member.size!=info['size']:raise ValueError('File type/size mismatch')
                h=hashlib.sha256()
                with package.extractfile(member) as stream:
                    for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
                if h.hexdigest()!=info['sha256']:raise ValueError('Member SHA-256 mismatch: '+member.name)
    if seen!=set(entries):raise ValueError('Missing bundle members')
    return spec,entries


def restore(archive,root,entries):
    root=Path(root).resolve()
    checked_links(entries,root)
    # Preflight every destination before creating anything. Existing equal
    # files may be reused; mismatches are never repaired or overwritten.
    for name,info in entries.items():
        path=root/name
        for parent in (root,*[root/str(p) for p in PurePosixPath(name).parents if str(p)!='.']):
            if os.path.lexists(parent) and (parent.is_symlink() or not parent.is_dir()):
                raise ValueError('Unsafe destination parent: '+str(parent))
        if os.path.lexists(path):
            if info['kind']=='symlink':equal=path.is_symlink() and os.readlink(path)==info['target']
            else:equal=not path.is_symlink() and path.is_file() and digest(path)==info['sha256'] and path.stat().st_mode&0o777==info['mode']
            if not equal:raise ValueError('Existing destination differs: '+str(path))
    root.mkdir(parents=True,exist_ok=True)
    with tarfile.open(archive,'r:gz') as package:
        for member in package:
            path=root/member.name;info=entries[member.name]
            if os.path.lexists(path):continue
            path.parent.mkdir(parents=True,exist_ok=True)
            if info['kind']=='symlink':path.symlink_to(info['target'])
            else:
                fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,info['mode'])
                with os.fdopen(fd,'wb') as output,package.extractfile(member) as source:shutil.copyfileobj(source,output)
                path.chmod(info['mode'])
    for name,info in entries.items():
        path=root/name
        if info['kind']=='file':
            if digest(path)!=info['sha256']:raise ValueError('Restored file differs: '+name)
        elif not path.is_symlink() or os.readlink(path)!=info['target']:raise ValueError('Restored symlink differs')
