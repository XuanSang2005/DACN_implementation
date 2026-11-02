"""C-P01 draft.4 private contracts. Frozen A/B/canonical schemas stay unchanged."""
from copy import deepcopy
from . import h3_contracts as A
from . import h3_checkpoint_contracts as B
from .h3_limits import Budget, need, digest
from .validation import Validator, FORMATS

HANDLER = 's02-2a-h3-c/0.11.0a1'
CONFIG = 's02-h3-config/0.1.0-draft.4'
PLAN = 's02-h3-plan/0.1.0-draft.4'
ADMISSION = 's02-h3-admission/0.1.0-draft.4'
POLICY = 's02-h3-history-policy/0.1.0-draft.4'
BINDING = 's02-h3-work/0.1.0-draft.4'
AUTHORITY = 's02-h3-local-authority/0.1.0-draft.4'
ANALYSIS = 's02-h3-analysis/0.1.0-draft.4'
GUARD = 's02-h3-guard-origin/0.1.0-draft.1'
PREDICATE = 'h3.continuation_union/1'
VERSIONS = dict(zip((B.HANDLER,B.CONFIG,B.PLAN,B.ADMISSION,B.POLICY,B.BINDING,B.AUTHORITY,B.ANALYSIS),
                    (HANDLER,CONFIG,PLAN,ADMISSION,POLICY,BINDING,AUTHORITY,ANALYSIS)))


def _definitions():
    old = B.schema('Config')['$defs']
    def convert(v, legacy=False):
        if type(v) is list: return [convert(x,legacy) for x in v]
        if type(v) is dict:
            return {k: x.replace('#/$defs/','#/$defs/B_',1) if legacy and k=='$ref' and x.startswith('#/$defs/') else
                    VERSIONS.get(x,x) if not legacy and k=='const' and type(x) is str else convert(x,legacy) for k,x in v.items()}
        return v
    d=convert(old); d.update({'B_'+k:convert(v,True) for k,v in old.items()})
    p=d['Config']['properties'];p['mode']={'enum':['step','revalidate']};p['step']={'type':'integer','minimum':1,'maximum':4};p['anchor']={'type':'null'}
    p['parent_metadata']={'oneOf':[{'$ref':'#/$defs/B_Admission'},{'$ref':'#/$defs/Admission'}]}
    p=d['Binding']['properties'];p['operation']={'enum':['step','revalidate']};p['step']={'type':'integer','minimum':1,'maximum':4}
    model={'allOf':[{'$ref':'#/$defs/Record'},{'type':'object','properties':{'type':{'const':'model'}}}]}
    d['CandidateProjection']=A.obj(candidate_sha256=deepcopy(A.HASH),local_bindings=A.mapping(A.ref('Alias')),
        pre_successor_model=A.nullable(model),pre_successor_model_sha256=A.nullable(deepcopy(A.HASH)))
    d['Plan']['properties']['candidate_projection']=A.nullable(A.ref('CandidateProjection'));d['Plan']['required'].append('candidate_projection')
    d['CGuardOrigin']=deepcopy(d['GuardOrigin']);p=d['CGuardOrigin']['properties'];p.update(version={'const':GUARD},origin_plan_artifact_id=deepcopy(A.ID),origin_plan_sha256=A.nullable(deepcopy(A.HASH)))
    d['CGuardOrigin']['required']=list(p)
    d['Admission']['properties']['guards']['additionalProperties']={'oneOf':[A.ref('GuardOrigin'),A.ref('CGuardOrigin')]}
    return d

_DEFS=_definitions()


def schema(kind):
    need(kind in (*A.KINDS,'CGuardOrigin','CandidateProjection'),'c_contract_kind')
    return {'$schema':'https://json-schema.org/draft/2020-12/schema','$ref':'#/$defs/'+kind,'$defs':deepcopy(_DEFS)}


def validate(kind,value,budget):
    need(type(budget) is Budget,'shared_h3_budget');budget.inspect(value)
    error=next(Validator(schema(kind),format_checker=FORMATS).iter_errors(value),None)
    need(error is None,'c_'+kind+'_shape'+(':'+ '/'.join(map(str,error.absolute_path)) if error else ''))
    if kind in ('Config','Binding'):
        mode=value['mode'] if kind=='Config' else value['operation']
        need(mode in ('step','revalidate') and 1<=value['step']<=4,'c_mode_step')
        need(value['unit_ids']==sorted(set(value['unit_ids'])) and bool(value['unit_ids']),'c_units')
        need((mode=='step')==(value['goal']=='build'),'c_mode_goal')
        if kind=='Config':
            need((value['inputs']['candidate'] is not None)==(mode=='step'),'c_candidate_mode')
            need(value['anchor'] is None and value['parent_metadata'] is not None,'c_parent_required')
        else:
            need((value['candidate_sha256'] is not None)==(mode=='step') and (value['candidate_length']>0)==(mode=='step'),'c_candidate_mode')
    if kind=='Authority':
        keys=[]
        for row in value['approvals']:
            validate('Binding',row['binding'],budget);keys.append(digest(row['binding']))
            need(row['binding']['provider_id']==value['provider_id'],'c_provider')
        need(len(keys)==len(set(keys)),'c_duplicate_approval')
    if kind=='Progress':A.validate(kind,value,budget)
    if kind=='CandidateProjection':
        model=value['pre_successor_model'];need(value['pre_successor_model_sha256']==(digest(model) if model else None),'c_projection_model_hash')
        ids=[v['id'] for v in value['local_bindings'].values()];need(len(ids)==len(set(ids)),'c_projection_unique_ids')
    budget.check();return deepcopy(value)
