"""Explicit H2 command surface; receipt-only resume never accepts new work."""
from pathlib import Path
from .codec_boundary import decode
from .errors import require
from .local_io import read_receipt,write_receipt
from .h2_authority import LocalSyntheticAuthority
from .h2_service import H2Service,output
from .h2_limits import DEFAULTS,need
from .h2_contracts import hash64
from hashlib import sha256

COMMANDS=('scoped-bootstrap','scoped-step','prepare-scope-work','scoped-resume','scoped-progress','scoped-revalidate','scope-plan')


def add_arguments(parser,sub):
    parser.add_argument('--h2-authority-file');parser.add_argument('--expect-h2-authority-sha256')
    for name in COMMANDS:
        p=sub.add_parser(name,allow_abbrev=False)
        if name!='scope-plan':p.add_argument('--receipt',required=True)
        if name not in ('scoped-resume','scoped-progress'):p.add_argument('--from-receipt',required=True)
        if name=='prepare-scope-work':p.add_argument('--mode',choices=('bootstrap','step','revalidate'),required=True)
        if name in ('scoped-step','scoped-revalidate','prepare-scope-work','scope-plan'):
            required=name!='prepare-scope-work'
            p.add_argument('--step',type=int,choices=range(1,5),required=required)
            p.add_argument('--unit',action='append',required=required)
            if name!='scope-plan':
                p.add_argument('--expect-model',required=required);p.add_argument('--expect-analysis-set',required=required)
                p.add_argument('--analysis',required=required);p.add_argument('--expect-analysis-sha256',required=required)
        if name in ('scoped-step','prepare-scope-work'):
            p.add_argument('--mock-response',required=name=='scoped-step');p.add_argument('--expect-sha256',required=name=='scoped-step')
        if name in ('scoped-revalidate','prepare-scope-work'):
            p.add_argument('--goal',choices=('admission','retained_output'),required=name=='scoped-revalidate')
            p.add_argument('--guard-key',action='append',required=name=='scoped-revalidate')


def validate_args(parser,args):
    if bool(args.h2_authority_file)!=bool(args.expect_h2_authority_sha256):parser.error('Both global H2 authority flags are required together')
    if args.command=='prepare-scope-work':
        fields=('step','unit','expect_model','expect_analysis_set','analysis','expect_analysis_sha256')
        if args.mode=='bootstrap':
            if any(getattr(args,k,None) is not None for k in (*fields,'mock_response','expect_sha256','goal','guard_key')):parser.error('bootstrap takes no semantic work flags')
        else:
            if any(getattr(args,k,None) is None for k in fields):parser.error('semantic prepare requires full original intent')
            if args.mode=='step':
                if args.mock_response is None or args.expect_sha256 is None or args.goal is not None or args.guard_key is not None:parser.error('step requires candidate/hash and forbids revalidation flags')
            elif args.mock_response is not None or args.expect_sha256 is not None or args.goal is None or args.guard_key is None:parser.error('revalidation requires goal/guards and no candidate')


def run(args,settings,repo):
    budget=None
    try:
        authority=LocalSyntheticAuthority(args.h2_authority_file,args.expect_h2_authority_sha256) if args.h2_authority_file else None
        service=H2Service(repo,authority=authority);budget=service.budget()
        if args.command in ('scoped-resume','prepare-scope-work'):
            claimed=decode(Path(args.receipt).read_bytes());require(type(claimed) is dict,'receipt_fields')
            read_receipt(settings,args.receipt,store_id=claimed.get('store_id'))
            from .h1_recovery import reconcile
            reconcile(repo,claimed.get('store_id'))
        store_id=repo.store_info()['metadata']['store_id']
        def receipt(path):return read_receipt(settings,path,store_id=store_id)['command_id']
        if args.command in ('scoped-resume','scoped-progress'):
            cmd=receipt(args.receipt)
            return service.resume(cmd,store_id=store_id,_budget=budget) if args.command=='scoped-resume' else service.report(cmd,progress=True,_budget=budget)
        parent=receipt(args.from_receipt)
        if args.command=='scope-plan':
            report=service.report(parent,progress=True,_budget=budget)
            need(report['result'].get('is_current'),'h2_preview_current')
            need(set(args.unit)<=report['result']['progress_by_unit'].keys(),'h2_preview_units')
            return report
        repo.assert_writable()
        mode=args.mode if args.command=='prepare-scope-work' else {'scoped-bootstrap':'bootstrap','scoped-step':'step','scoped-revalidate':'revalidate'}[args.command]
        def raw(path,expected):
            hash64(expected)
            with Path(path).open('rb') as stream:data=stream.read(DEFAULTS.raw_bytes+1)
            budget.cap('raw_bytes',len(data));need(sha256(data).hexdigest()==expected,'h2_input_sha256');return data
        candidate=raw(args.mock_response,args.expect_sha256) if mode=='step' else None
        analysis=raw(args.analysis,args.expect_analysis_sha256) if mode!='bootstrap' else None
        kw=dict(mode=mode,step=args.step if mode!='bootstrap' else 0,unit_ids=args.unit if mode!='bootstrap' else (),
                expected_pair=[args.expect_model,args.expect_analysis_set] if mode!='bootstrap' else [None,None],goal=args.goal if mode=='revalidate' else 'build',
                guard_keys=args.guard_key if mode=='revalidate' else (),candidate=candidate,analysis=analysis)
        if args.command=='prepare-scope-work':cmd=receipt(args.receipt);pre=None
        else:
            pre=service.preflight(parent,budget=budget,**kw)
            cmd=repo.allocate_id();write_receipt(settings,args.receipt,cmd,store_id=store_id)
        result=service.prepare(cmd,parent,store_id=store_id,_budget=budget,_preflight=pre,**kw)
        if args.command=='prepare-scope-work' or result['status']!='prepared':return result
        return service.resume(cmd,_budget=budget)
    except FileNotFoundError:return output(None,'not_found',dict(reason='Input or receipt not found'))
