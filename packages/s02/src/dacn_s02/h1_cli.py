"""Receipt-first CLI adapter for the explicitly authorized H1 work surface."""
from pathlib import Path
import re

from .errors import require
from .codec_boundary import decode
from .repository import digest
from .local_io import read_receipt, write_receipt
from .h1_limits import DEFAULTS, cap
from .h1_service import H1Service


def run(args,settings,repo):
    service=H1Service(repo)
    try:
        if args.command in ('resume','prepare-work'):
            # Preliminary format/state binding, then compare the asserted ID to
            # immutable store identity before SQLite recovery can have effects.
            claimed=decode(Path(args.receipt).read_bytes())
            require(type(claimed) is dict,'receipt_fields')
            read_receipt(settings,args.receipt,store_id=claimed.get('store_id'))
            from .h1_recovery import reconcile
            reconcile(repo,claimed.get('store_id'))
        info=repo.store_info();store_id=info.get('metadata',{}).get('store_id')
        def receipt(path):return read_receipt(settings,path,store_id=store_id)['command_id']
        if args.command in ('resume','progress'):
            cmd=receipt(args.receipt)
            return service.resume(cmd,store_id=store_id) if args.command=='resume' else service.report(cmd,progress=True)
        repo.assert_writable();parent=receipt(args.from_receipt)
        step='bootstrap' if args.command=='bootstrap' else args.step if args.step=='bootstrap' else int(args.step)
        raw=None
        if step!='bootstrap':
            require(re.fullmatch('[0-9a-f]{64}',args.expect_sha256) is not None,'h1_expected_sha256')
            with Path(args.mock_response).open('rb') as stream:raw=stream.read(DEFAULTS['raw_bytes']+1)
            cap('raw_bytes',len(raw));require(digest(raw)==args.expect_sha256,'h1_mock_hash')
        if args.command=='prepare-work':cmd=receipt(args.receipt)
        else:
            cmd=repo.allocate_id();write_receipt(settings,args.receipt,cmd,store_id=store_id)
        result=service.prepare(cmd,parent,step,raw,store_id)
        if args.command=='prepare-work' or result['status']!='prepared':return result
        return service.resume(cmd)
    except FileNotFoundError:
        return dict(command_id=None,status='not_found',record_ids=[],errors=[],result=dict(reason='Input or receipt file not found; no substitute created'))
