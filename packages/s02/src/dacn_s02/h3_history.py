"""Pure H3 historical registry and graph projections, never a storage adapter.

Inputs are detached caller data. No filesystem load, Repository factory, implicit
trust source, decision creation, allocation, clock, or application effects.
"""
from copy import deepcopy
from dataclasses import dataclass
from types import MappingProxyType
from hashlib import sha256
import json
from .codec_boundary import encode
from .h3_contracts import Contract, validate, REGISTRY, HISTORY
from .h3_limits import Budget, need, digest
from .profiles import E1, blocking_statuses, get_profile
from .validation import shape, fields, index_model, scope_sets
from .resolution import HumanReviewEvidence, review_digest, source_basis
from .profile_graph import validate_graph
from .s01_adapter import verify_archive
from .h2_contracts import SourceInventory
from .h2_graph import ModelContext


@dataclass(frozen=True)
class ReviewTrustContext:
    path: str  # External caller locator only. This module never opens it.
    expected_sha256: str
    expected_registry_id: str
    expected_store_id: str


@dataclass(frozen=True)
class ReviewRegistry:
    raw: bytes
    trust: ReviewTrustContext

    @classmethod
    def parse(cls, raw, trust, budget):
        need(type(trust) is ReviewTrustContext, 'external_review_trust_required')
        need(type(trust.path) is str and bool(trust.path.strip()), 'external_registry_locator')
        budget.inspect(dict(path=trust.path,registry_id=trust.expected_registry_id,store_id=trust.expected_store_id,
            raw_sha256=trust.expected_sha256),input_lane=True,slot='h3.review_trust')
        need(type(raw) is bytes, 'registry_bytes')
        budget.cap('registry_bytes',len(raw))
        need(sha256(raw).hexdigest()==trust.expected_sha256,'registry_external_sha256')
        try:text=raw.decode('utf-8')
        except UnicodeError:need(False,'registry_utf8')
        contract=Contract.parse('Registry',raw,budget);v=contract.payload()
        # The shared exact codec supports more JSON encodings. This protocol is
        # specifically UTF-8 JSON: NUL-padded UTF-16 without BOM must not pass
        # merely because those bytes also decode as a UTF-8 string.
        try:json.loads(text)
        except ValueError:need(False,'registry_utf8_json')
        budget.check()
        need(v['registry_id']==trust.expected_registry_id and v['store_id']==trust.expected_store_id,'registry_external_identity')
        ids=v['required_issue_ids'];entries=v['reviews'];keys=[e['issue_id'] for e in entries]
        need(ids==sorted(set(ids)) and keys==ids,'registry_required_issue_inventory')
        return cls(raw,trust)

    def payload(self):
        from .codec_boundary import decode
        return decode(self.raw)

    def pin(self):
        v=self.payload()
        return dict(format=REGISTRY,registry_id=v['registry_id'],store_id=v['store_id'],
            raw_sha256=sha256(self.raw).hexdigest(),required_issue_ids_sha256=digest(v['required_issue_ids']),
            reviews_sha256=digest(v['reviews']))

    def reviews(self):
        return MappingProxyType({e['issue_id']:HumanReviewEvidence(e['reviewer'],e['dependency_sha256'],e['assessment'])
                                  for e in self.payload()['reviews']})

    def verify(self,records,snapshots,profiles,store_id,budget):
        # Re-verify external bytes even if someone constructed the dataclass directly.
        checked=ReviewRegistry.parse(self.raw,self.trust,budget)
        need(store_id==checked.trust.expected_store_id,'registry_store_identity')
        required=[]
        for identity,r in records.items():
            budget.check();shape(r,profile=profiles[identity])
            if r['type']!='issue' or profiles[identity]!=E1:continue
            p=r['body']['resolution_carry'] or r['body']['resolution_replacement']
            if p is not None and p['evaluation']['method']=='human_review':required.append(identity)
        v=checked.payload();need(sorted(required)==v['required_issue_ids'],'registry_whole_store_required_ids')
        for identity,decision in checked.reviews().items():
            budget.check();r=records[identity];p=r['body']['resolution_carry'] or r['body']['resolution_replacement']
            need(decision.reviewer==p['evaluation']['evaluator'] and decision.assessment==p['assessment'],'registry_decision_binding')
            # Existing canonical algorithm, no new decision derived from this hash.
            need(decision.dependency_sha256==review_digest(r,records,snapshots,profiles),'registry_dependency_hash')
            budget.check()
        return checked.pin()


class HistoryData:
    """Pure whole-graph verification; it cannot prove an operational head/lookup.

    Records are verified by their explicit owner profiles. A future B adapter must
    obtain these bytes/head/store identity through checked reads, not JSON claims.
    """
    def __init__(self, *, records, record_profiles, owners, commands, operation_profiles,
                 events, stages, blobs, registry, store_id, budget):
        need(type(budget) is Budget and type(registry) is ReviewRegistry,'typed_history_inputs')
        self.budget=budget;self.registry=registry;self.store_id=store_id
        s=dict(records=records,record_profiles=record_profiles,owners=owners,commands=commands,
            operation_profiles=operation_profiles,events=events,stages=stages,blobs=blobs)
        need(all(type(x) is dict for x in s.values()),'history_map_types')
        need(all(type(v) is dict for k in ('records','commands','events','stages') for v in s[k].values()),'history_object_types')
        # Count complete store occurrences, including other sessions and ancestors.
        projected=dict(records=list(s['records'].values()),commands=list(s['commands'].values()),
            events=list(s['events'].values()),owner_ids=list(s['owners'].values()),
            record_ids=list(s['record_profiles']),command_ids=list(s['operation_profiles']),
            stages=[{k:v for k,v in x.items() if k!='bytes'} for x in s['stages'].values()])
        budget.inspect(projected,input_lane=True)
        s=deepcopy(s)
        need(set(s['records'])==set(s['record_profiles'])==set(s['owners']),'history_owner_inventory')
        need(set(s['commands'])==set(s['operation_profiles']),'history_command_inventory')
        for profile in [*s['record_profiles'].values(),*s['operation_profiles'].values()]:get_profile(profile)
        for i,r in s['records'].items():
            budget.check();shape(r,profile=s['record_profiles'][i])
        # Referenced history is also bounded: JSON nesting alone does not bound
        # a long supersedes/from chain. Reuse the existing depth ceiling, no new
        # larger cap and no recursive walk before canonical validators.
        for identity,r in s['records'].items():
            if r['type']!='issue':continue
            cursor=identity;seen=set();depth=0
            while cursor is not None:
                budget.check();depth+=1;budget.cap('depth',depth)
                need(cursor not in seen,'history_lineage_cycle');seen.add(cursor)
                prior=s['records'].get(cursor)
                need(prior is not None and prior['type']=='issue' and s['owners'][cursor]==s['owners'][identity] and
                     prior['body']['issue_key']==r['body']['issue_key'],'history_typed_lineage')
                proof=prior['body'].get('resolution_carry') or prior['body'].get('resolution_replacement')
                if proof is not None:need(proof['from_issue_id']==prior['body']['supersedes_id'],'history_proof_predecessor')
                cursor=prior['body']['supersedes_id']
        snapshots={r['body']['snapshot_id']:verify_archive(r,s['records'],s['blobs'])
                   for r in s['records'].values() if r['type']=='source_context'}
        registry.verify(s['records'],snapshots,s['record_profiles'],store_id,budget)
        budget.check();verified=validate_graph(**s,reviews=registry.reviews());budget.check()
        need(verified==snapshots,'history_snapshot_inventory')
        self._state=s;self._snapshots=deepcopy(snapshots)

    def payload(self):return deepcopy(self._state)
    def snapshots(self):return deepcopy(self._snapshots)

    def view(self,session_id,expected_pair,observed_pair):
        from .validation import valid_id
        need(type(expected_pair) in (list,tuple) and type(observed_pair) in (list,tuple) and len(expected_pair)==len(observed_pair)==2 and all(valid_id(i) for i in expected_pair) and list(expected_pair)==list(observed_pair),'history_pair_stale')
        mid,sid=expected_pair;s=self._state;records=s['records'];budget=self.budget
        need(mid in records and sid in records and records[mid]['type']=='model' and records[sid]['type']=='analysis_set','history_pair_types')
        need(s['owners'][mid]==s['owners'][sid]==session_id and records[sid]['body']['model_id']==mid,'history_pair_session')
        need(all(p==E1 for i,p in s['record_profiles'].items() if s['owners'][i]==session_id),'history_entry_e1_session')
        need(all(s['operation_profiles'][i]==E1 for i,c in s['commands'].items() if c['session_id']==session_id),'history_entry_e1_operations')
        aset=records[sid];model=records[mid];body=model['body']
        need(not body['interfaces'] and not body['dependencies'] and not aset['body']['scenario_ids'] and not aset['body']['characteristic_ids'],'history_steps_1_4_only')
        need(not any(r['type'] in ('review','bundle','scenario','characteristic') for i,r in records.items() if s['owners'][i]==session_id),'history_review_bundle_out_of_scope')
        publishers=[r for i,r in records.items() if r['type']=='run' and s['owners'][i]==session_id and r['body']['result_analysis_set_id']==sid]
        need(len(publishers)==1 and publishers[0]['body']['status'] in ('completed','blocked'),'history_parent_publication')
        source_context=records[body['source_context_id']];snapshot=self._snapshots[source_context['body']['snapshot_id']]
        archive=records[source_context['body']['envelope_artifact_id']]['body']['sha256']
        source=SourceInventory(snapshot,source_context['id'],archive,budget)
        context=ModelContext(model,source,budget)
        issues=[deepcopy(records[i]) for i in aset['body']['issue_ids']]
        return HistoryView(self,session_id,list(expected_pair),context,deepcopy(aset),issues,publishers[0]['body']['command_id'])

    def binding(self,view):
        need(type(view) is HistoryView and view.history is self,'history_view_binding')
        s=self._state;records=s['records'];budget=self.budget
        snapshots=[]
        for sid,value in sorted(self._snapshots.items()):
            archive_hashes={records[r['body']['envelope_artifact_id']]['body']['sha256'] for r in records.values() if r['type']=='source_context' and r['body']['snapshot_id']==sid}
            # More than one checked S01 envelope may refer to one snapshot. Pin each
            # envelope via the records/blobs pins; select a stable archive hash here.
            snapshots.append(dict(snapshot_id=sid,sha256=digest(value),archive_sha256=sorted(archive_hashes)[0]))
        v=dict(version=HISTORY,owner_profiles_sha256=digest(dict(records=s['record_profiles'],operations=s['operation_profiles'],owners=s['owners'])),
            records=[dict(record_id=i,sha256=digest(r)) for i,r in sorted(records.items())],
            events=[dict(command_id=c,event_id=e,sha256=digest(v)) for (c,e),v in sorted(s['events'].items())],
            snapshots=snapshots,current_issues={q['body']['issue_key']:q['id'] for q in view.issues},historical_reviews_pin=self.registry.pin())
        return validate('History',v,budget)


@dataclass(frozen=True)
class HistoryView:
    history: HistoryData
    session_id: str
    pair: list
    context: ModelContext
    analysis_set: dict
    issues: list
    parent_command_id: str

    def issue(self,key):
        records=self.history._state['records']
        need(self.issues==[records[i] for i in records[self.pair[1]]['body']['issue_ids']],'history_view_current_selection')
        found=[q for q in self.issues if q['body']['issue_key']==key]
        need(len(found)==1,'history_current_key')
        return deepcopy(found[0])

    def projection(self,key):
        q=self.issue(key);b=q['body'];p=b['resolution_carry'] or b['resolution_replacement']
        records=self.history._state['records'];budget=self.history.budget
        chain=[];cursor=q['id'];seen=set()
        while cursor is not None:
            budget.check();need(cursor not in seen,'history_lineage_cycle');seen.add(cursor);chain.append(cursor)
            old=records[cursor];need(old['body']['issue_key']==key,'history_lineage_key');cursor=old['body']['supersedes_id']
        basis,scope,known=source_basis(q,records,self.history._snapshots,self.history._state['events']);budget.check()
        return dict(issue_key=key,current_issue_id=q['id'],branch='CARRY' if b['resolution_carry'] else 'REPLACEMENT' if b['resolution_replacement'] else 'DIRECT',
            status=b['status'],assessment=p['assessment'] if p else None,origin_issue_id=p['origin_issue_id'] if p else q['id'],
            from_issue_id=p['from_issue_id'] if p else b['supersedes_id'],obsolete_issue_id=p.get('obsolete_issue_id') if p else None,
            replacement_issue_id=p.get('replacement_issue_id') if p else None,lineage=chain,
            answer_ids=deepcopy(b['answer_ids']),resolution_event_refs=deepcopy(b['resolution_event_refs']),
            source_basis=[dict(snapshot_id=a,input_pointer=z) for a,z in sorted(basis)],footprint=scope,impact_known=known,
            blocks=b['status'] in blocking_statuses(E1))


def project_current_refs(record,target_model_id,issue_map,budget):
    """Detached field projection only, not a canonical successor Record builder.

    Return a copied body with current Scope/ElementRef/model/Issue refs rebound.
    Preserve historical paths (including predecessor/root/base/source/event refs).
    No Record ID, status, proof assessment, Answer or human evidence is created.
    """
    budget.inspect(record);shape(record,profile=E1)
    need(record['type'] in ('model','issue'),'projection_record_kind')
    validate('History',dict(version=HISTORY,owner_profiles_sha256='0'*64,records=[],events=[],snapshots=[],
        current_issues=issue_map,historical_reviews_pin=dict(format=REGISTRY,registry_id='shape',store_id='shape',raw_sha256='0'*64,required_issue_ids_sha256='0'*64,reviews_sha256='0'*64)),budget)
    from .validation import valid_id
    need(valid_id(target_model_id),'projection_target_model')
    value=deepcopy(record);history_paths=[]
    nodes=list(fields(value,profile=E1))
    for _,spec,path,_ in nodes:
        if spec.get('x-history'):history_paths.append(path)
    for v,spec,path,name in nodes:
        budget.check()
        if any(path==h or path.startswith(h+'/') for h in history_paths):continue
        if path=='/body/supersedes_id':continue
        tokens=path.split('/')[1:];parent=value
        for t in tokens[:-1]:parent=parent[int(t)] if type(parent) is list else parent[t]
        if not tokens:continue
        k=int(tokens[-1]) if type(parent) is list else tokens[-1]
        if path=='/body/model_id':parent[k]=target_model_id
        elif name in ('Scope','ElementRef'):v['model_id']=target_model_id
        elif spec.get('x-record')=='issue':
            need(v in issue_map,'projection_missing_current_issue')
            parent[k]=issue_map[v]
    return value['body']
