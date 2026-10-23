"""Materialize E1 from byte-pinned L1; no runtime patches or storage writes."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'src/dacn_s02'
L1_SHA = 'dd32824ab03c5e4d5faae3eb3888bdea3cacd5ba4735a4a5df19416b024f70b7'
def ref(n): return {'$ref': '#/$defs/' + n}
def obj(**kw): return dict(type='object',properties=kw,required=list(kw),additionalProperties=False)
def arr(s): return dict(type='array',items=s,minItems=0,uniqueItems=True)
def null(s): return {'anyOf':[s,{'type':'null'}]}
def enum(*v): return {'enum':list(v)}
def materialize():
    raw=(ROOT/'schemas/contract.json').read_bytes()
    assert hashlib.sha256(raw).hexdigest()==L1_SHA
    s=json.loads(raw);d=s['$defs'];s['$id']='urn:dacn:s02:0.1.0-draft.4'
    text={'type':'string','format':'s02-text'}
    idspec=deepcopy(d['issueBody']['properties']['model_id']);idspec.pop('x-record')
    def rid(t,history=False): return {**idspec,'x-record':t,**({'x-history':True} if history else {})}
    evaluation=obj(method=enum('structural_check','human_review'),evaluator=text,rule_version=text,evidence_record_ids=arr(rid('*')),reason=text)
    d['ResolutionEvaluation']=evaluation
    d['ResolutionScopeCheck']=obj(from_scope={**ref('Scope'),'x-history':True},to_scope=ref('Scope'),element_pairs=arr(obj(**{'from':{**ref('ElementRef'),'x-history':True},'to':null(ref('ElementRef'))},relation=enum('unchanged','modified','removed'),reason=text)),reason=text)
    common=dict(origin_issue_id=rid('issue',True),from_issue_id=rid('issue',True),base_analysis_set_id=rid('analysis_set',True),change_id=null(rid('change')))
    d['ResolutionCarry']=obj(**common,assessment=enum('applicable','undetermined','not_applicable'),source_checks=arr(obj(from_ref={**ref('SourceRef'),'x-history':True},to_ref=null(ref('SourceRef')),relation=enum('equal_value','changed','removed'),reason=text)),scope_check=ref('ResolutionScopeCheck'),evaluation=ref('ResolutionEvaluation'))
    d['ResolutionReplacement']=obj(**common,obsolete_issue_id=rid('issue',True),replacement_issue_id=rid('issue'),assessment=enum('complete','incomplete'),obligation_checks=arr(obj(old_ref={**ref('SourceRef'),'x-history':True},current_ref=null(ref('SourceRef')),disposition=enum('replaced','removed'),evidence_record_ids=arr(rid('*')),reason=text)),scope_check=ref('ResolutionScopeCheck'),evaluation=ref('ResolutionEvaluation'))
    base=d['issueBody'];branches=[]
    for branch in ('Direct','Carry','Replacement'):
        b=deepcopy(base);p=b['properties']
        p['resolution_carry']=ref('ResolutionCarry') if branch=='Carry' else {'type':'null'}
        p['resolution_replacement']=ref('ResolutionReplacement') if branch=='Replacement' else {'type':'null'}
        b['required']+=['resolution_carry','resolution_replacement']
        if branch=='Carry': p['status']=enum('resolved','resolution_pending_revalidation')
        if branch=='Replacement': p['status']=enum('resolution_replaced','resolution_pending_revalidation')
        d['issue'+branch+'Body']=b;branches.append(ref('issue'+branch+'Body'))
    d['issueBody']={'oneOf':branches}
    payload=d['application_appliedEvent']['properties']['payload']
    payload['properties']['observed_source_context_id']=null(rid('source_context'))
    payload['required'].append('observed_source_context_id')
    # E1 records have no legacy/mixed export. Export v2 remains P2+ work.
    d['Export']=False
    return (json.dumps(s,ensure_ascii=True,indent=2)+'\n').encode()

def resources():
    e1=materialize()
    descriptors=[]
    for name,contract,rules,caps,raw in [
        ('legacy-a3','s02/0.1.0-draft.3','legacy-a3',['foundation-draft3'],(ROOT/'schemas/contract.json').read_bytes()),
        ('a1a2-v1','s02/0.1.0-draft.4','a1a2-v1',['foundation-draft3','observed-s01-context-v1','issue-carry-v1','issue-replacement-v1','typed-history-refs-v1'],e1)]:
        descriptors.append(dict(profile_id='s02-profile/'+name,contract_version=contract,rules_id='s02-rules/'+rules,required_capabilities=caps,schema_sha256=hashlib.sha256(raw).hexdigest()))
    return {'schemas/profiles/a1a2-v1/contract.json':e1,'schemas/profiles/registry.json':(json.dumps(descriptors,indent=2)+'\n').encode()}
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--write-new',action='store_true');args=p.parse_args()
    for path,raw in resources().items():
        target=ROOT/path
        if args.write_new:
            target.parent.mkdir(parents=True,exist_ok=True)
            with target.open('xb') as out:out.write(raw)
        else: assert target.read_bytes()==raw,path
        print(path,hashlib.sha256(raw).hexdigest())
