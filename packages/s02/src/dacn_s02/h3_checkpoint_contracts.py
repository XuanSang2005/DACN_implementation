"""B-P01 private draft.3 dispatch. A draft.2 checkers remain unchanged."""
from copy import deepcopy
from . import h3_contracts as A
from .h3_limits import Budget, need, digest
from .validation import Validator, FORMATS

HANDLER = 's02-2a-h3-b/0.10.0a1'
CONFIG = 's02-h3-config/0.1.0-draft.3'
PLAN = 's02-h3-plan/0.1.0-draft.3'
ADMISSION = 's02-h3-admission/0.1.0-draft.3'
POLICY = 's02-h3-history-policy/0.1.0-draft.3'
BINDING = 's02-h3-work/0.1.0-draft.3'
AUTHORITY = 's02-h3-local-authority/0.1.0-draft.3'
ANALYSIS = 's02-h3-analysis/0.1.0-draft.3'
VERSIONS = {A.HANDLER:HANDLER,A.CONFIG:CONFIG,A.PLAN:PLAN,A.ADMISSION:ADMISSION,
            A.POLICY:POLICY,A.BINDING:BINDING,A.AUTHORITY:AUTHORITY,
            's02-h3-analysis/0.1.0-draft.2':ANALYSIS}


def schema(kind):
    def convert(v):
        if type(v) is dict:
            return {k:VERSIONS.get(x,x) if k=='const' and type(x) is str else convert(x) for k,x in v.items()}
        if type(v) is list:return [convert(x) for x in v]
        return v
    return convert(A.schema(kind))


def validate(kind,value,budget):
    need(type(budget) is Budget,'shared_h3_budget')
    budget.inspect(value)
    error=next(Validator(schema(kind),format_checker=FORMATS).iter_errors(value),None)
    need(error is None,'b_'+kind+'_shape'+(':'+ '/'.join(map(str,error.absolute_path)) if error else ''))
    if kind in ('Config','Binding'):
        mode=value['mode'] if kind=='Config' else value['operation']
        need(mode in ('adopt','revalidate'),'b_as_only_mode')
        need(bool(value['unit_ids']) and len(value['unit_ids'])==len(set(value['unit_ids'])),'b_units')
        need((mode=='adopt')==(value['step']==0) and value['goal'] in ('admission','retained_output'),'b_mode_goal')
        need(mode!='adopt' or value['goal']=='admission','b_adopt_admission_goal')
        if kind=='Config':
            need(value['inputs']['candidate'] is None,'b_no_candidate')
            need((value['parent_metadata'] is None)==(mode=='adopt'),'b_parent_metadata')
        else:need(value['candidate_sha256'] is None and value['candidate_length']==0,'b_no_candidate')
    if kind=='Authority':
        keys=[]
        for row in value['approvals']:
            validate('Binding',row['binding'],budget);keys.append(digest(row['binding']))
            need(row['binding']['provider_id']==value['provider_id'],'b_provider')
        need(len(keys)==len(set(keys)),'b_duplicate_approval')
    if kind in ('Progress','Anchor'):A.validate(kind,value,budget)
    budget.check()
    return deepcopy(value)
