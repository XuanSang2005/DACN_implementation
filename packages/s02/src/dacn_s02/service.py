"""Phase-1 intake/session service only. Does not analyze requirements."""
from .repository import record,digest
from .codec_boundary import encode
from .s01_adapter import intake
from .errors import require,storage_error

def staged(command_id,blob_id,purpose,raw,media_type='application/json'):
    return (dict(command_id=command_id,blob_id=blob_id,media_type=media_type,purpose=purpose,
                 sha256=digest(raw),byte_length=len(raw)),raw)

def artifact(identity,purpose,raw,producer=None,created_at=None,media_type='application/json'):
    return record('artifact',identity,dict(media_type=media_type,sha256=digest(raw),byte_length=len(raw),
                                         purpose=purpose,producer_run_id=producer),created_at)

class Service:
    def __init__(self,repository): self.repository=repository

    def allocate_command_id(self): return self.repository.allocate_id()

    def start(self,s01_path,store_key,s01_run_id,*,expected_snapshot_id=None,command_id=None):
        """Receipt is caller's precondition before this method has any effects.

        Failed checked intake creates no trusted SourceContext. A receipt with no
        operation is not evidence that a different store has no operation.
        """
        repo=self.repository;cmd=command_id or self.allocate_command_id()
        existing=repo.get_command(cmd)
        if existing is not None: raise storage_error('Command ID already exists; use checked lookup, not start retry')
        selected=intake(s01_path,s01_run_id,expected_snapshot_id)
        chosen={cmd}
        def fresh():
            for _ in range(8):
                i=repo.allocate_id()
                if i not in chosen: chosen.add(i);return i
            raise storage_error('ID generator collided within intake batch')
        session,runid,ctxid,configblob,configid=[fresh() for _ in range(5)]
        started=repo._clock();env=selected.envelope;snap=env['snapshot']
        operation=dict(command_id=cmd,session_id=session,parent_command_id=None,reserved_run_id=runid,
                       request=dict(kind='start',store_key=store_key,s01_run_id=s01_run_id,expected_snapshot_id=expected_snapshot_id))
        config=encode(dict(contract_version='s02/0.1.0-draft.3',scope='phase1_intake_only',store_key=store_key))
        repo.prepare(operation,session_spec=snap['spec_id'],staged=[staged(cmd,configblob,'config',config)])
        records=[];blobs={}
        def archive(purpose,raw):
            i=fresh();records.append(artifact(i,purpose,raw,created_at=started));blobs[i]=raw;return i
        env_id=archive('s01_envelope',selected.envelope_bytes)
        raw_id=archive('s01_run_source',selected.run_source)
        origin_id=raw_id if env['run']['source']['source_id']==snap['origin_source_id'] else archive('s01_origin_source',selected.origin_source)
        schema_id=archive('schema',selected.schema)
        records.append(record('source_context',ctxid,dict(store_key=store_key,s01_run_id=s01_run_id,snapshot_id=snap['snapshot_id'],envelope_artifact_id=env_id,run_source_artifact_id=raw_id,origin_source_artifact_id=origin_id,schema_artifact_id=schema_id),started))
        records.append(artifact(configid,'config',config,runid,started));blobs[configid]=config
        run=record('run',runid,dict(mode='live',source_context_id=ctxid,config_artifact_id=configid,base_model_id=None,base_analysis_set_id=None,command_id=cmd,result_analysis_set_id=None,steps=[],status='completed',result_model_id=None,started_at=started,completed_at=max(started,repo._clock()),attempts=[],errors=[]),started)
        records.append(run)
        result=repo.finalize(cmd,records,blobs=blobs,promotions=[dict(stage_ref=dict(command_id=cmd,blob_id=configblob),artifact_id=configid)])
        return dict(command_id=cmd,session_id=session,run_id=result['id'],source_context_id=ctxid,snapshot_id=snap['snapshot_id'])
