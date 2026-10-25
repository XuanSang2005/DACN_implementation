"""Closed, typed projections for H1 mock candidates, separate from Records."""
from copy import deepcopy
from hashlib import sha256

from .codec_boundary import encode
from .errors import S02Error, require
from .profiles import E1, get_profile
from .validation import Validator, FORMATS, inventory, resolve_pointer, escape
from .h1_limits import cap, ref_count, bounded_decode

VERSION = 's02-2a-candidate/0.1.0-draft.1'
HANDLER_VERSION = 's02-2a-h1/0.5.0a2'
KINDS = {'actors': 'Actor', 'actions': 'Action', 'workflows': 'Workflow',
         'data': 'Data', 'rules': 'Rule', 'components': 'Component',
         'responsibilities': 'Responsibility'}
TARGETS = dict(actor_ids='Actor', permission_rule_ids='Rule', rule_ids='Rule',
               read_data_ids='Data', write_data_ids='Data', workflow_ids='Workflow',
               action_ids='Action', component_id='Component',
               primary_responsibility_ids='Responsibility', supporting_responsibility_ids='Responsibility',
               entry_node_id='Node', action_id='Action', node_id='Node', **{'from': 'Node', 'to': 'Node'})


def published_alias(step,handle):
    ordinary='step'+str(step)+'.'+handle
    return ordinary if len(ordinary)<=128 else 'step'+str(step)+'-long.'+sha256(handle.encode('ascii')).hexdigest()


def obj(properties):
    return dict(type='object', properties=properties, required=list(properties), additionalProperties=False)


def array(items): return dict(type='array', items=items)


def schema(step):
    """A new detached schema; canonical E1 bytes and validators never change."""
    canonical = get_profile(E1).schema['$defs']; defs = {}
    handle = dict(type='string', format='s02-id', pattern=canonical['Actor']['properties']['id']['pattern'])
    text = dict(type='string', format='s02-text')
    ref = {'oneOf': [obj({key: handle}) for key in ('local_handle', 'base_handle')]}
    defs['SourceRef'] = deepcopy(canonical['SourceRef'])
    defs['Trace'] = obj(dict(origin={'enum': ['explicit', 'inferred']},
                            source_refs=array({'$ref': '#/$defs/SourceRef'}), rationale=text,
                            finding_handles=array(handle)))
    for name in (*KINDS.values(), 'Node', 'Edge', 'BranchPoint', 'Part'):
        value = deepcopy(canonical[name]); props = value['properties']
        if 'id' in props:
            del props['id']; props['handle'] = handle
        if name == 'Actor': del props['kind']
        if 'state' in props: props['state'] = {'enum': ['draft', 'needs_clarification']}
        if 'issue_ids' in props:
            del props['issue_ids']; props['finding_handles'] = array(handle)
        for key in list(props):
            if key in TARGETS:
                old = props[key]
                props[key] = array(ref) if old.get('type') == 'array' else (
                    {'anyOf': [ref, {'type': 'null'}]} if 'anyOf' in old else ref)
        value['required'] = list(props); defs[name] = value
    finding = obj(dict(handle=handle, kind={'enum': ['business','quality_target','analysis_omission','design_choice','verification']},
                       question=text, reason=text, trace={'$ref': '#/$defs/Trace'},
                       affected_refs=array(ref), blocking_refs=array(ref), impact_known={'type': 'boolean'}))
    proposals = dict(findings=array(finding))
    if step == 2: proposals.update({k: array({'$ref': '#/$defs/'+v}) for k,v in KINDS.items() if k not in ('components','responsibilities')})
    if step == 3:
        proposals.update({k: array({'$ref': '#/$defs/'+KINDS[k]}) for k in ('components','responsibilities')})
        proposals['unassigned_actions'] = array(obj(dict(action=ref, gap=text, finding_handle=handle)))
    if step == 4:
        proposals['mappings'] = array(obj(dict(source_ref={'$ref': '#/$defs/SourceRef'},
            assessment={'enum': ['not_assessed','proposed']}, parts=array({'$ref': '#/$defs/Part'}), finding_handles=array(handle))))
    result = obj(dict(candidate_version={'const': VERSION}, step={'const': step, 'type':'integer'},
        proposals=obj(proposals), questions=array(handle),
        inspection=array(obj(dict(source_ref={'$ref': '#/$defs/SourceRef'}, read={'enum':['inspected','not_inspected']},
            verdict={'enum':['usable','held','not_relevant_with_reason']}, needed_facts=array(text),
            evidence_source_refs=array({'$ref':'#/$defs/SourceRef'}), finding_handles=array(handle), reason=text))),
        unrepresented_source_refs=array({'$ref':'#/$defs/SourceRef'})))
    result['$defs'] = defs
    return result


class Linker:
    def __init__(self, candidate, aliases, snapshot, fresh):
        self.aliases = deepcopy(aliases); self.local = {}; self.findings = {}; self.snapshot = snapshot
        proposals = candidate['proposals']
        def add(value, kind):
            handle = value['handle']; require(handle not in self.local, 'candidate_duplicate_handle')
            self.local[handle] = dict(id=fresh(), kind=kind)
        for k, kind in KINDS.items():
            for v in proposals.get(k, []):
                add(v,kind)
                if kind == 'Workflow':
                    for field,typ in (('nodes','Node'),('edges','Edge')):
                        for node in v[field]: add(node,typ)
        for m in proposals.get('mappings', []):
            for p in m['parts']: add(p,'Part')
        for finding in proposals['findings']:
            add(finding,'Issue'); self.findings[finding['handle']] = self.local[finding['handle']]['id']
        for question in candidate['questions']: self.finding(question)

    def ref(self, value, kind=None):
        table = self.local if 'local_handle' in value else self.aliases
        h = value.get('local_handle', value.get('base_handle')); item = table.get(h)
        require(item is not None and (kind is None or item['kind'] == kind), 'candidate_typed_ref')
        return item['id']

    def finding(self, handle):
        if handle in self.findings: return self.findings[handle]
        return self.ref({'base_handle': handle}, 'Issue')

    def source(self, ref):
        require(ref['snapshot_id'] == self.snapshot['snapshot_id'], 'candidate_snapshot')
        try: resolve_pointer(self.snapshot['input'], ref['input_pointer'])
        except (ValueError,IndexError,KeyError):
            raise S02Error('SOURCE_REF_INVALID','references','Candidate source does not resolve') from None

    def convert(self, value):
        if type(value) is list: return [self.convert(v) for v in value]
        if type(value) is not dict: return value
        if set(value) == {'snapshot_id','input_pointer'}: self.source(value); return deepcopy(value)
        if set(value) in ({'local_handle'}, {'base_handle'}): return self.ref(value)
        result = {}
        for k,v in value.items():
            if k == 'handle': result['id'] = self.local[v]['id']
            elif k == 'finding_handles': result['issue_ids'] = [self.finding(h) for h in v]
            elif k in TARGETS and v is not None:
                result[k] = [self.ref(x,TARGETS[k]) for x in v] if type(v) is list else self.ref(v,TARGETS[k])
            else: result[k] = self.convert(v)
        if 'origin' in result:
            require(bool(result['source_refs']), 'candidate_trace_source')
            result['answer_refs'] = []
        return result


def parse(raw, step, snapshot, aliases, fresh, budget):
    candidate = bounded_decode(raw,budget)
    error = next(Validator(schema(step),format_checker=FORMATS).iter_errors(candidate),None)
    if error:
        raise S02Error('CANDIDATE_INVALID','schema','Candidate violates closed H1 projection',
                       pointer=''.join('/'+escape(p) for p in error.absolute_path), details={'keyword':error.validator})
    cap('findings',len(candidate['proposals']['findings'])); cap('refs',ref_count(candidate))
    linker = Linker(candidate,aliases,snapshot,fresh)
    expected = inventory(snapshot); seen = []
    for row in candidate['inspection']:
        linker.source(row['source_ref']); seen.append(row['source_ref']['input_pointer'])
        for source in row['evidence_source_refs']: linker.source(source)
        for h in row['finding_handles']: linker.finding(h)
        require(row['read'] != 'not_inspected' or row['verdict'] == 'held','inspection_unread_held')
        if row['verdict'] != 'held': require(bool(row['evidence_source_refs']),'inspection_evidence')
    require(len(seen)==len(set(seen)) and set(seen)==expected,'inspection_inventory')
    refs = candidate['unrepresented_source_refs']
    for source in refs:
        linker.source(source); require(source['input_pointer'] in expected,'unrepresented_inventory')
    require(len({r['input_pointer'] for r in refs})==len(refs),'unrepresented_unique')
    budget.check()
    return candidate, linker
