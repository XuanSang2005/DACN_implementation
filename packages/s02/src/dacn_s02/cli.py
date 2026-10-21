"""Minimal init/intake/lookup CLI; no arbitrary record imports."""
import argparse
import sys
from .codec_boundary import encode
from .errors import S02Error,storage_error
from .local_io import settings,check_store,write_receipt,read_receipt
from .repository import Repository
from .service import Service

class Parser(argparse.ArgumentParser):
    def error(self,message):
        self.print_usage(sys.stderr);self.exit(64,f'{self.prog}: {message}\n')

def main(argv=None):
    parser=Parser(prog='dacn-s02');parser.add_argument('--config',required=True)
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('init');start=sub.add_parser('start')
    start.add_argument('--store-key',required=True);start.add_argument('--s01-run-id',required=True)
    start.add_argument('--expect-snapshot');start.add_argument('--receipt',required=True)
    show=sub.add_parser('show-command');group=show.add_mutually_exclusive_group(required=True);group.add_argument('--receipt');group.add_argument('--id')
    show=sub.add_parser('show-record');show.add_argument('--id',required=True)
    args=parser.parse_args(argv);cmd=None
    try:
        s=settings(args.config);check_store(s);repo=Repository(s.state/'s02.sqlite3',timeout=s.timeout/1000)
        result=None;record_ids=[];status='completed';exit_code=0
        if args.command=='init':
            s.state.mkdir(parents=True,exist_ok=True);check_store(s);repo.initialize()
        elif args.command=='start':
            repo.verify()
            if args.store_key not in s.stores: raise storage_error('Unknown S01 store alias')
            service=Service(repo);cmd=service.allocate_command_id();write_receipt(s,args.receipt,cmd)
            result=service.start(s.stores[args.store_key],args.store_key,args.s01_run_id,expected_snapshot_id=args.expect_snapshot,command_id=cmd)
            record_ids=[result['run_id'],result['source_context_id']]
        elif args.command=='show-command':
            cmd=read_receipt(s,args.receipt)['command_id'] if args.receipt else args.id
            result=repo.get_command(cmd)
            if result: record_ids=[result['run']['id']] if result['run'] else []
        else:
            result=repo.get_record(args.id);record_ids=[args.id] if result else []
        if args.command.startswith('show-') and result is None: status='not_found';exit_code=4
        output=dict(command_id=cmd,status=status,record_ids=record_ids,errors=[])
        if result is not None: output['result']=result
    except (S02Error,OSError,ValueError,TypeError) as exc:
        error=exc.error if isinstance(exc,S02Error) else storage_error('Local configuration or I/O failed').error
        rejected=error['stage'] in ('intake','schema','references','revision','parse','review') and error['code']!='PROCESSING_FAILED'
        output=dict(command_id=cmd,status='rejected' if rejected else 'failed',record_ids=[],errors=[error]);exit_code=2 if rejected else 3
    try: sys.stdout.buffer.write(encode(output)+b'\n');sys.stdout.buffer.flush()
    except (BrokenPipeError,OSError): return 3
    return exit_code
