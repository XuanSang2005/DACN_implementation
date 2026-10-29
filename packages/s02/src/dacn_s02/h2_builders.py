"""Append-only scoped builders with a separate raw projection and rebind phase."""
from copy import deepcopy
from .codec_boundary import encode
from .repository import record
from .scope import make_scope
from .validation import COLLECTIONS, index_model, shape
from .profiles import E1
from .h1_builders import trace, allscope, part_has_gap
from .h1_candidates import Linker, KINDS
from .h1_limits import model_limits
from .h2_contracts import HoldSelector
from .h2_graph import ModelContext
from .h2_checkpoint import selector, empty_progress
from .h2_limits import digest, need


class ScopedBuilder:
    def __init__(self,view,source,fresh,now,budget):
        self.view=view;self.cfg=view['config'];self.source=source;self.fresh=fresh;self.now=now;self.budget=budget
        self.step=self.cfg['step'];self.run=self.cfg['reserved_run_id'];self.aliases=deepcopy(self.cfg['aliases'])
        self.meta=deepcopy(self.cfg['parent_metadata']) if self.cfg['parent_metadata'] else dict(selectors={},tasks={},guards={},progress_by_unit=empty_progress(source))
        self.model=deepcopy(view['base_model']);self.issues=deepcopy(view['issues']);self.new_model=False
        self.new_output={};self.new_selectors={};self.origin=self.cfg['command_id']

    def refs(self,ptrs):return [dict(snapshot_id=self.source.snapshot_id,input_pointer=p) for p in sorted(ptrs)]

    def issue(self,refs,question,*,kind='verification',key=None,unknown=False,role=None,target=1,identity=None,elements=(),parts=()):
        mid=self.model['id'];scope=make_scope(mid,elements,parts)
        q=record('issue',identity or self.fresh(),dict(issue_key=key or self.fresh(),supersedes_id=None,model_id=mid,
            detected_step=self.step or 1,kind=kind,question=question,reason='Synthetic H2 code assessment; no business confirmation',trace=trace(refs),
            affected=scope,blocking=deepcopy(scope),status='open',answer_ids=[],resolution_event_refs=[],resolution=None,resolution_carry=None,resolution_replacement=None),self.now)
        self.issues.append(q)
        self.new_selectors[q['body']['issue_key']]=selector(q,self.source,role=role,target=target,unknown=unknown)
        return q

    def task(self,units,step,role,predicate):
        key='h2.construct.'+digest([self.origin,sorted(units),step,role])
        q=self.issue(self.refs(self.source.selected(units)), 'Build and account scoped stage '+str(step),key=key,role=role,target=step)
        self.meta['tasks'][key]=dict(origin_command_id=self.origin,root_issue_id=q['id'],unit_ids=sorted(units),target_step=step,role=role,predicate=predicate)
        return q

    def bootstrap(self):
        self.model=record('model',self.fresh(),dict(revision=1,parent_model_id=None,change_id=None,source_context_id=self.source.context_id,
            created_by_run_id=self.run,**{k:[] for k in COLLECTIONS},mappings=[]),self.now);self.new_model=True
        for i,name in enumerate(self.view['snapshot']['input']['actors']):
            actor=dict(id=self.fresh(),name=name,kind='supplied',state='draft',trace=trace(self.refs(['/actors/'+str(i)]),'Supplied actor from checked S01'))
            actor['trace']['origin']='explicit';self.model['body']['actors'].append(actor);self.aliases['supplied-actor.'+str(i)]=dict(id=actor['id'],kind='Actor')
        global_task=self.task(set(self.source.units),4,'global_mapping','h2.all_mapping/1')
        for unit in self.source.units:
            self.task({unit},3,'await_builder','h2.unit_responsibility/1')
            self.task({unit},4,'await_builder','h2.unit_mapping/1')
        for ptr in sorted(self.source.obligations):
            self.model['body']['mappings'].append(dict(id=self.fresh(),source_ref=self.refs([ptr])[0],parts=[],assessment='not_assessed',issue_ids=[global_task['id']]))
        self.materialize_selectors()

    def build(self,candidate):
        """Produce a full candidate using original current Issue refs for union."""
        v=candidate.payload();p=v['proposals'];linker=Linker(v,self.aliases,self.view['snapshot'],self.fresh)
        new = self.step in (2,3,4)
        if new:
            self.model.update(id=self.fresh(),created_at=self.now)
            self.model['body'].update(revision=int(self.model['body']['revision'])+1,parent_model_id=self.view['base_model']['id'],change_id=self.fresh(),created_by_run_id=self.run)
            self.new_model=True
        for coll,kind in KINDS.items():
            for row in p.get(coll,[]):
                converted=linker.convert(row)
                if coll=='actors':converted['kind']='candidate'
                self.model['body'][coll].append(converted)
        if self.step==4:
            rows={r['source_ref']['input_pointer']:r for r in self.model['body']['mappings']}
            for row in p['mappings']:
                current=rows[row['source_ref']['input_pointer']]
                need(current['assessment']=='not_assessed' and not current['parts'],'h2_mapping_append_only')
                converted=linker.convert(row)
                current.update(parts=converted['parts'],assessment=converted['assessment'],issue_ids=converted['issue_ids'])
        for f in p['findings']:
            es,ps=index_model(self.model)
            affected={linker.ref(r) for r in f['affected_refs']};blocking={linker.ref(r) for r in f['blocking_refs']}
            need(blocking<=affected and affected<=es.keys()|ps.keys(),'h2_finding_scope')
            q=self.issue(f['trace']['source_refs'],f['question'],kind=f['kind'],identity=linker.findings[f['handle']],unknown=not f['impact_known'],elements=blocking&es.keys(),parts=blocking&ps.keys())
            q['body'].update(reason=f['reason'],trace=linker.convert(f['trace']))
            q['body']['affected']=make_scope(self.model['id'],affected&es.keys(),affected&ps.keys())
        # Every uncovered output owns its own genuine hold, separate from tasks.
        actions={a['id']:a for a in self.model['body']['actions']}
        for gap in p.get('unassigned_actions',[]):
            aid=linker.ref(gap['action'],'Action');fid=linker.finding(gap['finding_handle'])
            q=self.issue(actions[aid]['trace']['source_refs'],'Assign responsibility for action '+aid,kind='analysis_omission',elements=[aid]);q['body']['reason']=gap['gap'];q['body']['trace']['issue_ids']=[fid]
        for action in self.model['body']['actions']:
            if action['initiator']=='unknown' and action['id'] in {x['id'] for x in linker.local.values()}:
                q=self.issue(action['trace']['source_refs'],'Inspect unknown initiator',kind='analysis_omission',elements=[action['id']]);action['trace']['issue_ids'].append(q['id']);action['state']='needs_clarification'
        held={r['source_ref']['input_pointer'] for r in v['inspection'] if r['verdict']=='held'}|{r['input_pointer'] for r in v['unrepresented_source_refs']}
        covered={r['input_pointer'] for q in self.issues if q['body']['status']=='open' and q['body']['issue_key'] not in self.meta['tasks'] for r in q['body']['trace']['source_refs']}
        for ptr in sorted(held-covered):self.issue(self.refs([ptr]),'Source obligation remains held',kind='analysis_omission')
        for row in self.model['body']['mappings']:
            for part in row['parts']:
                if part_has_gap(part) and part['id'] in {x['id'] for x in linker.local.values()}:
                    q=self.issue([row['source_ref']],'Candidate mapping retains a gap',kind='analysis_omission',parts=[part['id']]);part['issue_ids'].append(q['id'])
        for h,value in linker.local.items():
            alias='scope.'+digest([candidate.namespace,self.step,h])
            need(alias not in self.aliases,'h2_alias_collision');self.aliases[alias]=deepcopy(value)
        owners={}
        for coll in KINDS:
            for entity in p.get(coll,[]):
                handles=[entity['handle']]
                if coll=='workflows':handles += [x['handle'] for k in ('nodes','edges') for x in entity[k]]
                for handle in handles:owners[handle]={r['input_pointer'] for r in entity['trace']['source_refs']}
        for row in p.get('mappings',[]):
            for part in row['parts']:owners[part['handle']]={row['source_ref']['input_pointer']}
        for finding in p['findings']:owners[finding['handle']]={r['input_pointer'] for r in finding['trace']['source_refs']}
        for unit in self.cfg['unit_ids']:
            refs=self.source.units[unit].obligations
            local_ids=sorted(linker.local[h]['id'] for h,ptrs in owners.items() if ptrs & refs)
            self.new_output[unit]=dict(stage=self.step,local_ids=local_ids,raw_sha256=candidate.sha256,
                                       source_refs=self.refs(refs),aliases={h:x for h,x in self.aliases.items() if x['id'] in local_ids})
        self.meta['projection']=dict(candidate_sha256=candidate.sha256,local_bindings=deepcopy(linker.local))
        return self.model

    def resolve_tasks(self):
        rows=self.model['body']['mappings'];assigned={a for r in self.model['body']['responsibilities'] for a in r['action_ids']}
        for q in self.issues:
            key=q['body']['issue_key'];task=self.meta['tasks'].get(key)
            if not task or q['body']['status']=='resolved':continue
            refs=self.source.selected(task['unit_ids']);target=int(task['target_step'])
            if target!=self.step:continue
            if task['role']!='global_mapping' and not set(task['unit_ids'])<=set(self.cfg['unit_ids']):continue
            if target==4:done=all(r['parts'] and r['assessment']=='proposed' for r in rows if r['source_ref']['input_pointer'] in refs)
            else:
                relevant={a['id'] for a in self.model['body']['actions'] if any(r['input_pointer'] in refs for r in a['trace']['source_refs'])}
                gap_actions={i for hold in self.issues if hold['body']['status']=='open' and hold['body']['kind']=='analysis_omission' and hold['body']['issue_key'] not in self.meta['tasks'] for i in hold['body']['blocking']['element_ids']}
                done=relevant<=assigned|gap_actions
            if done:
                self.successor(q)
                q['body'].update(status='resolved',resolution='Code checked '+task['predicate']+'; synthetic, not semantic acceptance',blocking=make_scope(self.model['id']))

    def successor(self,q):
        if q['id'] in self.view['state']['records']:
            old=q['id'];q.update(id=self.fresh(),created_at=self.now);q['body'].update(supersedes_id=old,model_id=self.model['id'])

    def rebind(self):
        remap={}
        old_by_key={q['body']['issue_key']:q['id'] for q in self.view['issues']}
        for q in self.issues:
            if self.new_model:self.successor(q)
            old=old_by_key.get(q['body']['issue_key'])
            if old and old!=q['id']:remap[old]=q['id']
        def walk(v):
            if isinstance(v,list):
                for x in v:walk(x)
            elif isinstance(v,dict):
                for k,x in v.items():
                    if k=='issue_ids':v[k]=[remap.get(i,i) for i in x]
                    elif k=='model_id':v[k]=self.model['id']
                    else:walk(x)
        walk(self.model['body'])
        for q in self.issues:walk(q['body'])
        for alias in self.aliases.values():
            if alias['kind']=='Issue':alias['id']=remap.get(alias['id'],alias['id'])
        self.materialize_selectors()
        return remap

    def materialize_selectors(self):
        from .h2_policy import materialize
        context=ModelContext(self.model,self.source,self.budget)
        for q in self.issues:
            key=q['body']['issue_key'];old=self.new_selectors.get(key)
            if old is None:
                p=self.meta['selectors'][key]
                old=HoldSelector(p['issue_id'],key,int(p['target_step']),p['kind'],self.source.refs(p['source_refs']),frozenset(p['element_ids']),frozenset(p['mapping_part_ids']),p['impact_known'],p['code_task_role'])
            current=HoldSelector(q['id'],key,old.target_step,old.kind,old.sources,old.elements,old.parts,old.impact_known,old.code_task_role)
            if q['body']['status']=='open':
                footprint=materialize(context,current,q)
                q['body']['affected']=make_scope(self.model['id'],footprint.elements|set(q['body']['affected']['element_ids']),footprint.parts|set(q['body']['affected']['mapping_part_ids']))
                q['body']['blocking']=make_scope(self.model['id'],footprint.uses|current.elements,footprint.active_parts|current.parts)
            else:
                q['body']['affected']['model_id']=self.model['id'];q['body']['blocking']=make_scope(self.model['id'])
            # Store logical sources and actual current canonical blockers together.
            current=HoldSelector(q['id'],key,current.target_step,current.kind,current.sources,frozenset(q['body']['blocking']['element_ids']),frozenset(q['body']['blocking']['mapping_part_ids']),current.impact_known,current.code_task_role)
            self.meta['selectors'][key]=current.payload(self.source)

    def records(self):
        model_limits(self.model['body'],self.issues);self.budget.inspect(dict(model=self.model,current_issues=self.issues))
        oldset=self.view['base_set'];prior=set(oldset['body']['issue_ids']) if oldset and not self.new_model else set()
        aset=record('analysis_set',self.fresh(),dict(model_id=self.model['id'],revision=1 if self.new_model else int(oldset['body']['revision'])+1,
            parent_set_id=None if self.new_model else oldset['id'],scenario_ids=[],characteristic_ids=[],issue_ids=[q['id'] for q in self.issues],
            changed_record_ids=[q['id'] for q in self.issues if q['id'] not in prior],affected=allscope(self.model)),self.now)
        records=[q for q in self.issues if q['id'] not in prior]+[aset]
        if self.new_model:
            records.append(self.model)
            if self.model['body']['change_id']:
                before,bp=index_model(self.view['base_model']);after,ap=index_model(self.model)
                ops=[dict(kind='add',element_id=i,reason='Scoped synthetic proposal') for i in sorted((after.keys()|ap.keys())-(before.keys()|bp.keys()))]
                ops += [dict(kind='replace',element_id=i,reason='Code-owned current Issue reference rebinding') for i in sorted((after.keys()|ap.keys())&(before.keys()|bp.keys())) if encode(after.get(i,ap.get(i)))!=encode(before.get(i,bp.get(i)))]
                records.append(record('change',self.model['body']['change_id'],dict(base_model_id=self.view['base_model']['id'],new_model_id=self.model['id'],kind='analysis_edit',old_source_context_id=self.source.context_id,new_source_context_id=self.source.context_id,reason='Scoped synthetic append and current refs',source_record_ids=[],application_event_refs=[],operations=ops,affected=allscope(self.model),reused=[],reevaluate=[],invalidated_bundle_ids=[]),self.now))
        for r in records:shape(r,profile=E1)
        return records,aset
