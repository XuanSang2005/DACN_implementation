"""Controlled errors with diagnostics that never echo unrepresentable input."""
from dacn_s01.codec import serialize_json


class S02Error(Exception):
    def __init__(self, code, stage, message, *, record_id=None, pointer=None, details=None, related_ids=()):
        self.error = dict(code=code, stage=stage, record_id=record_id, pointer=pointer,
                          related_ids=list(related_ids), message=message, details=details or {})
        try:
            serialize_json(self.error)
        except Exception:
            self.error = dict(code="PROCESSING_FAILED",stage="schema",record_id=None,pointer=None,
                              related_ids=[],message="Diagnostic cannot be represented exactly",
                              details={"reason":"Unrepresentable diagnostic"})
        super().__init__(self.error["message"])


def require(condition, invariant, *, record_id=None, pointer=None):
    if not condition:
        raise S02Error("SCHEMA_INVARIANT", "schema", invariant, record_id=record_id,
                       pointer=pointer, details={"invariant":invariant})


def storage_error(reason):
    return S02Error("PERSISTENCE_FAILED", "persistence", reason, details={"reason":reason})
