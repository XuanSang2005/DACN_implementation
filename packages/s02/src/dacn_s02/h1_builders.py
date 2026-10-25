"""H1 pure canonical builders. No tests, provider, S01 writes or human review."""
from copy import deepcopy

from .codec_boundary import encode
from .errors import require
from .repository import record
from .profiles import E1
from .scope import make_scope
from .validation import COLLECTIONS, index_model, inventory, shape, validate_record
from .h1_candidates import KINDS,published_alias
from .h1_limits import model_limits, cap


def allscope(model):
    es, ps = index_model(model)
    return make_scope(model['id'], es, ps)


def trace(refs, rationale='Synthetic mock proposal; no business confirmation'):
    return dict(origin='inferred', source_refs=deepcopy(refs), answer_refs=[], rationale=rationale, issue_ids=[])


def part_has_gap(part):
    return part['assignment']!='proposed' or part['covered_portion'] is None or part['remaining_gap'] is not None


class Builder:
    def __init__(self, view, fresh, now, budget):
        self.view=view; self.fresh=fresh; self.now=now; self.budget=budget
        self.cfg=view['config']; self.op=view['command']['operation']; self.step=self.cfg['step']
        self.snapshot=view['snapshot']; self.refs=[dict(snapshot_id=self.snapshot['snapshot_id'],input_pointer=p) for p in sorted(inventory(self.snapshot))]
        self.aliases=deepcopy(self.cfg['aliases']); self.issues=[]; self.task_key=self.cfg['mapping_task_key']

    def issue(self, model, refs, question, *, key=None, parent=None, kind='verification', blocking=True, identity=None):
        scope=allscope(model)
        return record('issue',identity or self.fresh(),dict(issue_key=key or self.fresh(),supersedes_id=parent,
            model_id=model['id'],detected_step=self.step if self.step!='bootstrap' else 1,
            kind=kind,question=question,reason='H1 draft: source facts and unrepresented work remain visible',
            trace=trace(refs),affected=scope,blocking=scope if blocking else make_scope(model['id']),
            status='open',answer_ids=[],resolution_event_refs=[],resolution=None,
            resolution_carry=None,resolution_replacement=None),self.now)

    def bootstrap(self):
        cap('obligations',len(self.refs)); self.task_key=self.fresh()
        model=record('model',self.fresh(),dict(revision=1,parent_model_id=None,change_id=None,
            source_context_id=self.cfg['source_context_id'],created_by_run_id=self.op['reserved_run_id'],
            **{k:[] for k in COLLECTIONS},mappings=[]),self.now)
        for i,name in enumerate(self.snapshot['input']['actors']):
            identity=self.fresh(); model['body']['actors'].append(dict(id=identity,name=name,kind='supplied',state='draft',
                trace=trace([dict(snapshot_id=self.snapshot['snapshot_id'],input_pointer='/actors/'+str(i))],'Supplied actor preserved from checked S01')))
            model['body']['actors'][-1]['trace']['origin']='explicit'
            self.aliases['supplied-actor.'+str(i)]=dict(id=identity,kind='Actor')
        task=self.issue(model,self.refs,'Provide a proposed candidate mapping for every source obligation',key=self.task_key)
        self.issues=[task]; self.aliases['pending-mapping']=dict(id=task['id'],kind='Issue')
        for source in self.refs:
            model['body']['mappings'].append(dict(id=self.fresh(),source_ref=source,parts=[],assessment='not_assessed',issue_ids=[task['id']]))
        return self.finish(model,True,[],None,[],False)

    def analyze(self, candidate, linker):
        base=self.view['base_model']; oldset=self.view['base_set']; p=candidate['proposals']
        new_model = self.step in (2,3) and any(p.get(k) for k in KINDS)
        if self.step==4:
            oldrows={m['source_ref']['input_pointer']:m for m in base['body']['mappings']}
            new_model=any(m['parts'] or m['finding_handles'] or m['assessment']!=oldrows.get(m['source_ref']['input_pointer'],{}).get('assessment') for m in p['mappings'])
        model=deepcopy(base); changes=[]
        if new_model:
            model.update(id=self.fresh(),created_at=self.now)
            model['body'].update(revision=int(base['body']['revision'])+1,parent_model_id=base['id'],
                created_by_run_id=self.op['reserved_run_id'],change_id=self.fresh())
        remap={}
        for old in self.view['issues']:
            current=deepcopy(old)
            if new_model:
                current.update(id=self.fresh(),created_at=self.now)
                current['body'].update(model_id=model['id'],supersedes_id=old['id'])
                remap[old['id']]=current['id']
            self.issues.append(current)
        for alias in linker.aliases.values():
            if alias['kind']=='Issue':alias['id']=remap.get(alias['id'],alias['id'])
        self.aliases=deepcopy(linker.aliases)
        def rebind(value):
            if type(value) is dict:
                for key,child in value.items():
                    if key=='issue_ids':value[key]=[remap.get(i,i) for i in child]
                    else:rebind(child)
            elif type(value) is list:
                for child in value:rebind(child)
        rebind(model['body'])
        for item in self.issues:rebind(item['body'])
        {1:self.clarify,2:self.operations,3:self.components,4:self.mapping}[self.step](model,candidate,linker)
        # Candidate findings retain their meaning; H1 materializes conservative
        # full scopes rather than claiming a partial continuation.
        for f in p['findings']:
            for ref in [*f['affected_refs'],*f['blocking_refs']]:
                identity=linker.ref(ref); es,ps=index_model(model)
                require(identity in es or identity in ps,'finding_scope_member')
            q=self.issue(model,f['trace']['source_refs'],f['question'],identity=linker.findings[f['handle']],kind=f['kind'],
                blocking=(not f['impact_known'] or bool(f['blocking_refs']) or f['kind'] in ('business','quality_target')))
            q['body'].update(reason=f['reason'],trace=linker.convert(f['trace']))
            self.issues.append(q)
        # The assignment gap owns a hold independently of its cited finding.
        # Keep cited Issues immutable (or their normal Model successors); never
        # borrow the code mapping task's exemption for unassigned actions.
        actions={a['id']:a for a in model['body']['actions']}
        for gap in p.get('unassigned_actions',[]):
            action_id=linker.ref(gap['action'],'Action');finding_id=linker.finding(gap['finding_handle'])
            require(action_id in actions and any(q['id']==finding_id for q in self.issues),'unassigned_current_refs')
            hold=self.issue(model,actions[action_id]['trace']['source_refs'],
                'Assign a proposed responsibility for action '+action_id,kind='analysis_omission')
            hold['body']['reason']=gap['gap'];hold['body']['trace']['issue_ids']=[finding_id]
            self.issues.append(hold)
        if self.step==2:
            for action in model['body']['actions']:
                if action['initiator']=='unknown':
                    # An explicit unknown is retained and surfaced, never filled
                    # with a supplied actor or turned into permission by code.
                    q=self.issue(model,action['trace']['source_refs'],'Inspect the pinned source for the explicitly unknown initiator before requesting business clarification.',kind='analysis_omission')
                    self.issues.append(q);action['state']='needs_clarification';action['trace']['issue_ids'].append(q['id'])
        holds={r['source_ref']['input_pointer'] for r in candidate['inspection'] if r['verdict']=='held'}
        holds.update(r['input_pointer'] for r in candidate['unrepresented_source_refs'])
        for ptr in sorted(holds):
            self.issues.append(self.issue(model,[dict(snapshot_id=self.snapshot['snapshot_id'],input_pointer=ptr)],
                'Keep this source obligation held until the missing analysis or facts are supplied',kind='analysis_omission'))
        task=next(q for q in self.issues if q['body']['issue_key']==self.task_key)
        mapped=self.step==4 and all(m['parts'] and m['assessment']=='proposed' for m in model['body']['mappings'])
        if mapped:
            task['body'].update(status='resolved',resolution='Code checked presence of candidate Parts for every obligation; no semantic acceptance',blocking=make_scope(model['id']))
        for q in self.issues:
            q['body']['affected']=allscope(model)
            if q['body']['blocking']['element_ids'] or q['body']['blocking']['mapping_part_ids']:
                q['body']['blocking']=allscope(model)
            else:q['body']['blocking']=make_scope(model['id'])
        for row in model['body']['mappings']:
            if not row['parts'] or row['assessment']=='not_assessed':
                if task['id'] not in row['issue_ids']:row['issue_ids'].append(task['id'])
            for part in row['parts']:
                if part_has_gap(part):
                    matches=[q for q in self.issues if q['body']['status']=='open' and row['source_ref'] in q['body']['trace']['source_refs']]
                    if not matches:
                        q=self.issue(model,[row['source_ref']],'Candidate mapping retains a gap',kind='analysis_omission');self.issues.append(q);matches=[q]
                    part['issue_ids']=list(dict.fromkeys([*part['issue_ids'],*[q['id'] for q in matches]]))
        for h,value in linker.local.items():
            alias=published_alias(self.step,h);require(alias not in self.aliases,'candidate_published_alias_collision')
            self.aliases[alias]=deepcopy(value)
        blocked=any(q['body']['status']=='open' and (q['body']['blocking']['element_ids'] or q['body']['blocking']['mapping_part_ids'])
                    and (q['body']['issue_key']!=self.task_key or self.step==4) for q in self.issues)
        if new_model:
            oe,op=index_model(base); ne,np=index_model(model)
            for i in sorted((ne.keys()|np.keys())-(oe.keys()|op.keys())):changes.append(dict(kind='add',element_id=i,reason='H1 candidate proposal'))
            for i in sorted((ne.keys()|np.keys())&(oe.keys()|op.keys())):
                if encode(ne.get(i,np.get(i)))!=encode(oe.get(i,op.get(i))):changes.append(dict(kind='replace',element_id=i,reason='H1 current trace/context'))
        return self.finish(model,new_model,changes,oldset,candidate['inspection'],blocked)

    def clarify(self,model,candidate,linker):
        """Step 1 only contributes findings/inspection; source/model stay pinned."""

    def entities(self,model,proposals,linker,keys):
        for key in keys:
            values=linker.convert(proposals[key])
            if key=='actors':
                for actor in values:actor['kind']='candidate'
                model['body'][key].extend(values)
            else:
                require(not model['body'][key],'h1_no_successful_step_edit');model['body'][key]=values

    def operations(self,model,candidate,linker):
        """Step 2: preserve supplied actors, add typed operation/data/rule graph."""
        self.entities(model,candidate['proposals'],linker,('actors','actions','workflows','data','rules'))

    def components(self,model,candidate,linker):
        """Step 3: propose grouping/responsibilities and account for every action."""
        p=candidate['proposals'];self.entities(model,p,linker,('components','responsibilities'))
        assigned={a for r in model['body']['responsibilities'] for a in r['action_ids']};unassigned=set()
        for gap in p['unassigned_actions']:
            unassigned.add(linker.ref(gap['action'],'Action'));linker.finding(gap['finding_handle'])
        require({a['id'] for a in model['body']['actions']}<=assigned|unassigned,'responsibility_action_inventory')

    def mapping(self,model,candidate,linker):
        """Step 4: retain row identities/source binding and report every gap."""
        rows={m['source_ref']['input_pointer']:m for m in model['body']['mappings']};seen=[];gaps=set()
        for row in candidate['proposals']['mappings']:
            linker.source(row['source_ref']);ptr=row['source_ref']['input_pointer'];seen.append(ptr)
            require(ptr in rows,'mapping_obligation')
            converted=linker.convert(row);current=rows[ptr]
            current.update(parts=converted['parts'],assessment=converted['assessment'],issue_ids=converted['issue_ids'])
            if current['assessment']=='not_assessed' or not current['parts'] or any(part_has_gap(x) for x in current['parts']):gaps.add(ptr)
        require(len(seen)==len(set(seen)) and set(seen)==set(rows),'mapping_candidate_inventory')
        require(gaps<={r['input_pointer'] for r in candidate['unrepresented_source_refs']},'mapping_gaps_reported')

    def finish(self,model,new_model,operations,oldset,inspection,blocked):
        self.budget.check(); model_limits(model['body'],self.issues)
        selected=[q['id'] for q in self.issues]
        prior=set(oldset['body']['issue_ids']) if oldset and not new_model else set()
        aset=record('analysis_set',self.fresh(),dict(model_id=model['id'],revision=1 if new_model else int(oldset['body']['revision'])+1,
            parent_set_id=None if new_model else oldset['id'],scenario_ids=[],characteristic_ids=[],issue_ids=selected,
            changed_record_ids=[i for i in selected if i not in prior],affected=allscope(model)),self.now)
        records=[q for q in self.issues if q['id'] not in prior]+[aset]
        if new_model:
            records.append(model)
            if model['body']['change_id']:
                records.append(record('change',model['body']['change_id'],dict(base_model_id=self.cfg['base_model_id'],new_model_id=model['id'],
                    kind='analysis_edit',old_source_context_id=self.cfg['source_context_id'],new_source_context_id=self.cfg['source_context_id'],
                    reason='Synthetic H1 proposal; no source change or business confirmation',source_record_ids=[],application_event_refs=[],
                    operations=operations,affected=allscope(model),reused=[],reevaluate=[],invalidated_bundle_ids=[]),self.now))
        for item in records:shape(item,profile=E1)
        self.budget.check()
        return dict(records=records,head=[model['id'],aset['id']],result_model_id=model['id'] if new_model else None,
                    result_analysis_set_id=aset['id'],status='blocked' if blocked else 'completed',aliases=self.aliases,
                    admission=dict(source_context_id=self.cfg['source_context_id'],base_pair=[self.cfg['base_model_id'],self.cfg['base_analysis_set_id']],
                        result_pair=[model['id'],aset['id']],inspection=inspection,mapping_task_key=self.task_key,
                        completed_steps=[] if self.step=='bootstrap' else [*self.cfg['completed_steps'],self.step],
                        holds=[q['id'] for q in self.issues if q['body']['status']=='open' and q['body']['issue_key']!=self.task_key
                               and (q['body']['blocking']['element_ids'] or q['body']['blocking']['mapping_part_ids'])]))
