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
    for name in ('bootstrap','analyze-step','prepare-work','resume','progress'):
        work=sub.add_parser(name,allow_abbrev=False);work.add_argument('--receipt',required=True)
        if name in ('bootstrap','analyze-step','prepare-work'):work.add_argument('--from-receipt',required=True)
        if name in ('analyze-step','prepare-work'):
            work.add_argument('--step',choices=('bootstrap','1','2','3','4') if name=='prepare-work' else ('1','2','3','4'),required=True)
            work.add_argument('--mock-response',required=name=='analyze-step');work.add_argument('--expect-sha256',required=name=='analyze-step')
    for name in ('migration-inspect','migration-copy','migration-reconcile','migration-activate','lookup-migrated'):
        mig=sub.add_parser(name);mig.add_argument('--source-state-dir',required=True)
        mig.add_argument('--offline-confirmed',action='store_true',help='All old writers stopped and kept stopped until manual cutover')
        if name!='migration-inspect':mig.add_argument('--migration-receipt',required=True)
        if name=='migration-copy':mig.add_argument('--resume',action='store_true')
        if name=='migration-activate':
            mig.add_argument('--confirm-activation',action='store_true');mig.add_argument('--operator',required=True)
        if name=='lookup-migrated':mig.add_argument('--receipt',required=True)
    args=parser.parse_args(argv);cmd=None
    if args.command=='prepare-work':
        if args.step=='bootstrap' and (args.mock_response is not None or args.expect_sha256 is not None):parser.error('bootstrap does not accept mock/hash flags')
        if args.step!='bootstrap' and (args.mock_response is None or args.expect_sha256 is None):parser.error('work step requires mock-response and expect-sha256')
    try:
        s=settings(args.config);check_store(s);repo=Repository(s.state/'s02.sqlite3',timeout=s.timeout/1000)
        result=None;record_ids=[];status='completed';exit_code=0;direct=None
        if args.command in ('bootstrap','analyze-step','prepare-work','resume','progress'):
            from .h1_cli import run
            from .h1_service import exit_code as work_exit
            direct=run(args,s,repo);cmd=direct['command_id'];exit_code=work_exit(direct)
        elif args.command.startswith('migration-') or args.command=='lookup-migrated':
            from .migration import Migration
            migration=Migration(s,args.source_state_dir);kw=dict(offline=args.offline_confirmed)
            if args.command=='migration-inspect':result=migration.inspect(**kw)
            elif args.command=='migration-copy':result=migration.copy(args.migration_receipt,resume=args.resume,**kw)
            elif args.command=='migration-reconcile':result=migration.reconcile(args.migration_receipt,**kw)
            elif args.command=='migration-activate':result=migration.activate(args.migration_receipt,confirm=args.confirm_activation,operator=args.operator,**kw)
            else:result=migration.lookup_migrated(args.receipt,args.migration_receipt,**kw)
        elif args.command=='init':
            repo.initialize(create_parent=True)
        elif args.command=='start':
            repo.assert_writable()
            if args.store_key not in s.stores: raise storage_error('Unknown S01 store alias')
            service=Service(repo);cmd=service.allocate_command_id();write_receipt(s,args.receipt,cmd,store_id=repo.store_info()['metadata']['store_id'])
            result=service.start(s.stores[args.store_key],args.store_key,args.s01_run_id,expected_snapshot_id=args.expect_snapshot,command_id=cmd)
            record_ids=[result['run_id'],result['source_context_id']]
        elif args.command=='show-command':
            info=repo.store_info();store_id=info.get('metadata',{}).get('store_id')
            cmd=read_receipt(s,args.receipt,store_id=store_id)['command_id'] if args.receipt else args.id
            result=repo.lookup_command(cmd)
            if result: record_ids=[result['run']['id']] if result['run'] else []
        else:
            result=repo.lookup_record(args.id);record_ids=[args.id] if result else []
        if args.command.startswith('show-') and result is None: status='not_found';exit_code=4
        output=dict(command_id=cmd,status=status,record_ids=record_ids,errors=[])
        if result is not None: output['result']=result
        if direct is not None:output=direct
    except (S02Error,OSError,ValueError,TypeError) as exc:
        error=exc.error if isinstance(exc,S02Error) else storage_error('Local configuration or I/O failed').error
        rejected=error['stage'] in ('intake','schema','references','revision','parse','review') and error['code']!='PROCESSING_FAILED'
        output=dict(command_id=cmd,status='rejected' if rejected else 'failed',record_ids=[],errors=[error]);exit_code=2 if rejected else 3
        if args.command in ('bootstrap','analyze-step','prepare-work','resume','progress') and error['stage']=='persistence' and any(w in error['message'].lower() for w in ('unknown','lookup','inspection')):
            output['result']=dict(reconciliation='unknown')
    try: sys.stdout.buffer.write(encode(output)+b'\n');sys.stdout.buffer.flush()
    except (BrokenPipeError,OSError): return 3
    return exit_code
