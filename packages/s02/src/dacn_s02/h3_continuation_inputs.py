"""Pure C input/binding/read scope. No I/O, ID allocation or semantic grant inference."""
from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
from .codec_boundary import encode
from .h3_limits import need,digest
from .h3_policy import SemanticTrustContext
from .h3_checkpoint_checks import workflow_members,normalized_aliases
from .h3_continuation_contracts import validate,BINDING,POLICY


def refs(source,pointers):
    return [dict(snapshot_id=source.snapshot_id,input_pointer=p) for p in sorted(pointers)]


def read_context(base,metadata):
    ctx=base.context;elements,parts=ctx.source_seed(ctx.source.selected(metadata['selected_units']))
    elements=set(elements);parts=set(parts);issues={q['id'] for q in base.issues};members=workflow_members(ctx)
    for row in metadata['progress_by_unit'].values():
        ids=set(row['actual_output_ids'])|{i for o in row['outputs'] for i in o['output_ids']}
        elements.update(ids&ctx.elements.keys());parts.update(ids&ctx.parts.keys())
        for w in ctx.body['workflows']:
            if any(x['id'] in ids for k in ('nodes','edges') for x in w[k]):elements.add(w['id'])
    foot=ctx.closure(elements,parts)
    # Supplied actors are checked S01 context, needed by the initial action
    # builder even before there is an action footprint. Arbitrary candidates or
    # unknown actors never gain this context allowance from their name/alias.
    actors={a['id'] for a in ctx.body['actors'] if a['kind']=='supplied' and
            all(r['input_pointer'].startswith('/actors/') for r in a['trace']['source_refs'])}
    ids=set(foot.elements)|set(foot.parts)|issues|actors
    for w in ctx.body['workflows']:
        if w['id'] in ids:ids.update(x['id'] for k in ('nodes','edges') for x in w[k])
    ctx.budget.inspect(dict(read_context_ids=sorted(ids)))
    return frozenset(ids)


def intent(base,metadata,*,mode,step,units,goal,aliases):
    read=read_context(base,dict(metadata,selected_units=units))
    return dict(mode=mode,step=step,unit_ids=list(units),goal=goal,aliases_sha256=digest(aliases),
        current_selectors_sha256=digest(sorted(metadata['selectors'].values(),key=lambda r:r['issue_key'])),
        progress_before_sha256=digest(metadata['progress_by_unit']),read_context_ids=sorted(read),
        write_source_refs=refs(base.context.source,base.context.source.selected(units)))


def binding(base,metadata,*,provider_id,mode,step,units,goal,aliases,candidate,analysis):
    source=base.context.source;v=intent(base,metadata,mode=mode,step=step,units=units,goal=goal,aliases=aliases)
    return validate('Binding',dict(version=BINDING,purpose='synthetic_test_only',provider_id=provider_id,provider_version='local-synthetic/1',policy_version=POLICY,
        store_id=base.history.store_id,session_id=base.session_id,parent_command_id=base.parent_command_id,source_context_id=source.context_id,snapshot_id=source.snapshot_id,
        archive_sha256=source.archive_sha256,base_pair=base.pair,base_model_sha256=digest(base.context.model()),base_analysis_set_sha256=digest(base.analysis_set),
        operation=mode,goal=goal,step=step,unit_ids=list(units),aliases_sha256=v['aliases_sha256'],current_selectors_sha256=v['current_selectors_sha256'],
        progress_before_sha256=v['progress_before_sha256'],retained_assessment_hashes=sorted({digest(p['assessment']) for p in metadata['progress_by_unit'].values() if p['assessment'] is not None}),
        read_write_intent_sha256=digest(v),candidate_sha256=sha256(candidate).hexdigest() if candidate is not None else None,candidate_length=len(candidate or b''),
        analysis_sha256=sha256(analysis).hexdigest(),analysis_length=len(analysis),history_sha256=digest(base.history.binding(base)),anchor_sha256=None,
        historical_reviews_pin=base.history.registry.pin()),base.history.budget)


def inspections(raw,cfg,base):
    source=base.context.source;b=base.history.budget
    value=validate('Analysis',b.parse(raw,kind='raw',slot='c.analysis.'+cfg['command_id']),b)
    need(value['base_pair']==base.pair and value['source_context_id']==source.context_id and value['snapshot_id']==source.snapshot_id and
         value['unit_ids']==cfg['unit_ids'] and value['selectors_sha256']==cfg['authority_binding']['current_selectors_sha256'],'c_analysis_binding')
    rows={};pairs={};keys={q['body']['issue_key'] for q in base.issues}
    for row in value['inspections']:
        ptr=source.source(row['source_ref'],obligation=True);need(ptr not in rows,'c_inspection_duplicate');basis=source.refs(row['basis_source_refs'])
        need(row['verdict']=='held' or row['read']=='inspected' and ptr in basis and not row['needed_facts'],'c_inspection_basis');rows[ptr]=row
    need(set(rows)==source.obligations,'c_inspection_inventory')
    for row in value['independence']:
        k=row['issue_key'],row['unit_id'];need(k not in pairs and k[0] in keys and k[1] in source.units,'c_independence_refs');source.refs(row['basis_source_refs']);pairs[k]=row
    return rows,pairs


@dataclass(frozen=True)
class ContinuationGrant:
    binding_sha256: str
    control_sha256: str
    provider_id: str
    decision: str


def authorize(raw,trust,value,budget):
    need(type(trust) is SemanticTrustContext,'c_external_authority_tuple');validate('Binding',value,budget)
    need(type(raw) is bytes and sha256(raw).hexdigest()==trust.expected_sha256,'c_authority_hash')
    control=validate('Authority',budget.parse(raw,kind='authority',slot='c.authority'),budget)
    need(control['provider_id']==value['provider_id']==trust.provider_id and control['provider_version']==value['provider_version']==trust.provider_version,'c_authority_provider')
    rows=[r for r in control['approvals'] if encode(r['binding'])==encode(value)]
    return ContinuationGrant(digest(value),trust.expected_sha256,trust.provider_id,rows[0]['decision'] if len(rows)==1 else 'deny')


def h2_aliases(aliases):
    result=deepcopy(aliases)
    for a in result.values():a['kind']={'WorkflowNode':'Node','WorkflowEdge':'Edge'}.get(a['kind'],a['kind'])
    return result
