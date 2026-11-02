"""CLI entry for the LP-01 fresh local draft lane; no mock/provider overrides."""
from .errors import require
from .local_io import writable
from .local_provider import LocalDaemon
from .local_service import LocalService


def add_arguments(sub):
    analyze=sub.add_parser('local-analyze',allow_abbrev=False)
    analyze.add_argument('--receipt',required=True)
    analyze.add_argument('--store-key',required=True)
    analyze.add_argument('--llm-config',required=True)
    group=analyze.add_mutually_exclusive_group(required=True)
    group.add_argument('--input');group.add_argument('--s01-run-id')
    analyze.add_argument('--expect-snapshot')
    report=sub.add_parser('local-report',allow_abbrev=False);report.add_argument('--receipt',required=True)
    resume=sub.add_parser('local-resume',allow_abbrev=False);resume.add_argument('--receipt',required=True)
    resume.add_argument('--llm-config')


def run(args,settings):
    provider=None
    try:
        if getattr(args,'llm_config',None):
            provider=LocalDaemon(args.llm_config,writable(settings,settings.state/'local-daemon-logs'))
        service=LocalService(settings,provider)
        if args.command=='local-report':return service.report(receipt=args.receipt)
        if args.command=='local-resume':return service.resume(receipt=args.receipt)
        require(args.s01_run_id is not None or args.expect_snapshot is None,'local_input_no_snapshot_flag')
        return service.analyze(receipt=args.receipt,store_key=args.store_key,input_path=args.input,s01_run_id=args.s01_run_id,expected_snapshot=args.expect_snapshot)
    finally:
        if provider is not None:provider.close()
