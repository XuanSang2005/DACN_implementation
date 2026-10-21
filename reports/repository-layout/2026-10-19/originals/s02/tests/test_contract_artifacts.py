"""Documentation examples are shape checks only, never trusted intake fixtures."""
from pathlib import Path
import json
from dacn_s02.validation import shape,SCHEMA

def test_document_record_shapes():
    root=Path(__file__).resolve().parents[2]
    found=[]
    def walk(value):
        if type(value) is dict:
            if value.keys()=={'id','type','created_at','body'}:
                shape(value);found.append(value['type'])
            for v in value.values():walk(v)
        elif type(value) is list:
            for v in value:walk(v)
    for path in sorted((root/'docs/examples/s02').glob('*.json')):walk(json.loads(path.read_bytes()))
    assert len(found)==33
    # Artifact references in these docs are bindings, not persisted Artifact records.
    assert {'model','analysis_set','answer','issue','change','source_context','run'}<=set(found)

def test_materialized_schema_all_record_and_event_types():
    assert {k[:-6] for k in SCHEMA['$defs'] if k.endswith('Record')}=={'source_context','artifact','run','issue','answer','model','scenario','characteristic','analysis_set','change','view','diagram','validation','bundle','review','handoff',''}
    # Common Record is a union, not an object. Every concrete record/body is closed.
    for name,s in SCHEMA['$defs'].items():
        if s.get('type')=='object' and name!='Error':
            assert s['additionalProperties'] is False and set(s['required'])==set(s['properties'])
