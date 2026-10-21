"""Local path/receipt protocol, independent from private S01 implementation."""
from dataclasses import dataclass
import os
from pathlib import Path
import stat
import tomllib
from uuid import uuid4
from .codec_boundary import encode,decode
from .errors import storage_error,require
from .validation import valid_id

def same(a,b): return a==b or a.exists() and b.exists() and a.samefile(b)
def within(path,root): return path.is_relative_to(root) or any(same(p,root) for p in (path,*path.parents))
def path_value(value,base):
    require(type(value) is str and bool(value) and '\x00' not in value,'path_value')
    value.encode('utf-8');return (base/Path(value)).resolve()

@dataclass(frozen=True)
class Settings:
    path: Path
    state: Path
    stores: dict
    protected: tuple
    timeout: int

def settings(path):
    p=Path(path).resolve();data=tomllib.loads(p.read_text('utf-8'))
    require(not data.keys()-{'state_dir','s01_stores','dataset_roots','protected_roots','busy_timeout_ms'},'config_unknown_fields')
    require('state_dir' in data,'config_state_required');state=path_value(data['state_dir'],p.parent)
    stores=data.get('s01_stores',{});require(type(stores) is dict and all(valid_id(k) for k in stores),'config_store_alias')
    stores={k:path_value(v,p.parent) for k,v in stores.items()}
    protected=[]
    for key in ('dataset_roots','protected_roots'):
        roots=data.get(key,[]);require(type(roots) is list,'config_roots')
        for v in roots:
            root=path_value(v,p.parent);require(root.is_dir(),'protected_root_exists');protected.append(root)
    timeout=data.get('busy_timeout_ms',5000);require(type(timeout) is int and 0<=timeout<=2147483647,'config_timeout')
    result=Settings(p,state,stores,tuple(protected),timeout);check_store(result);return result

def writable(s,path):
    path=Path(path).resolve()
    for root in (*s.protected,*[p.parent for p in s.stores.values()]):
        if within(path,root): raise storage_error('Write path is in a protected or S01 directory')
    if same(path,s.path): raise storage_error('Write path aliases configuration')
    # Protect a source checkout even when started from elsewhere.
    for parent in (path,*path.parents):
        if (parent/'AGENTS.md').is_file() and (parent/'pyproject.toml').is_file():
            raise storage_error('Write path is inside an implementation checkout')
    return path

def check_store(s):
    writable(s,s.state)
    for src in s.stores.values():
        if within(src,s.state): raise storage_error('S01 and S02 stores must be separate directories')
    for suffix in ('','-journal','-wal','-shm'):
        p=s.state/('s02.sqlite3'+suffix);writable(s,p)
        if os.path.lexists(p):
            info=p.lstat()
            if not stat.S_ISREG(info.st_mode) or info.st_nlink!=1: raise storage_error('Database/sidecar must be regular, without links')

def receipt_target(s,path):
    original=Path(path).absolute();p=writable(s,original)
    if within(p,s.state) or os.path.lexists(original) or os.path.lexists(p) or not p.parent.is_dir():
        raise storage_error('Receipt must be a new file outside the state directory')
    return p

def write_receipt(s,path,command_id):
    p=receipt_target(s,path);raw=encode(dict(receipt_version='s02/1',command_id=command_id,state_dir=str(s.state)))+b'\n'
    directory=os.open(p.parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW);temp='.s02-'+str(uuid4())+'.tmp';exists=False
    try:
        fd=os.open(temp,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600,dir_fd=directory);exists=True
        with os.fdopen(fd,'wb') as stream: stream.write(raw);stream.flush();os.fsync(stream.fileno())
        receipt_target(s,p)
        os.link(temp,p.name,src_dir_fd=directory,dst_dir_fd=directory,follow_symlinks=False)
        os.unlink(temp,dir_fd=directory);exists=False;os.fsync(directory)
    finally:
        if exists: os.unlink(temp,dir_fd=directory)
        os.close(directory)

def read_receipt(s,path):
    value=decode(Path(path).read_bytes())
    require(type(value) is dict and value.keys()=={'receipt_version','command_id','state_dir'},'receipt_fields')
    require(value['receipt_version']=='s02/1' and valid_id(value['command_id']),'receipt_version_id')
    require(value['state_dir']==str(s.state),'receipt_store_binding');return value
