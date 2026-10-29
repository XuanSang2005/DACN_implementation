"""External, bounded synthetic approval adapter. Never restored from a plan."""
from pathlib import Path
from hashlib import sha256
from .errors import S02Error
from .h2_contracts import (AuthorityContext, AuthorityGrant, BindingRequest, closed,
                           ident, hash64, text)
from .h2_limits import need

FORMAT = 's02-h2-local-authority/0.1.0-draft.2'


def unavailable(reason):
    raise S02Error('H2_AUTHORITY_UNAVAILABLE', 'persistence', reason)


class LocalSyntheticAuthority:
    def __init__(self, path, expected_sha256):
        self.path = Path(path)
        self.expected_sha256 = hash64(expected_sha256)

    def read(self, budget):
        try:
            budget.check()
            with self.path.open('rb') as stream:
                raw = stream.read(budget.limits.authority_bytes + 1)
            budget.cap('authority_bytes', len(raw))
            need(sha256(raw).hexdigest() == self.expected_sha256, 'authority_sha256')
            value = budget.parse(raw, slot='authority')
            closed(value, 'format provider_id provider_version purpose approvals', 'authority')
            need(value['format'] == FORMAT and value['purpose'] == 'synthetic_test_only', 'authority_format')
            context = AuthorityContext(value['provider_id'], value['provider_version'], self.expected_sha256)
            need(type(value['approvals']) is list, 'authority_approvals')
            approvals = {}
            for row in value['approvals']:
                budget.check()
                closed(row, 'binding decision reason', 'approval')
                # The entire control file already counts every occurrence. Use
                # a non-input validation view, never another compute budget.
                binding = binding_in_control(row['binding'], budget)
                b = binding.payload()
                need(b['provider_id'] == context.provider_id and b['provider_version'] == context.provider_version, 'approval_provider')
                need(binding.key not in approvals, 'duplicate_approval')
                need(row['decision'] in ('allow', 'deny'), 'approval_decision')
                text(row['reason']);approvals[binding.key] = row
            budget.check()
            return context, approvals
        except (OSError, S02Error, ValueError, TypeError) as exc:
            unavailable('External synthetic authority unavailable or invalid: ' + (exc.error['code'] if isinstance(exc, S02Error) else type(exc).__name__))

    def authorize(self, binding, budget, *, expected_context=None):
        context, approvals = self.read(budget)
        if expected_context is not None and context != expected_context:
            unavailable('Original external authority context differs')
        row = approvals.get(binding.key)
        b = binding.payload()
        decision = row['decision'] if row and b['provider_id'] == context.provider_id and b['provider_version'] == context.provider_version else 'deny'
        grant = AuthorityGrant(binding.key, context.provider_id, context.provider_version, context.control_sha256,
                               decision, row['reason'] if row else 'No exact approval for binding')
        if not grant.matches(binding, context):
            raise S02Error('H2_AUTHORITY_DENIED', 'review', 'External synthetic authority denied the exact binding')
        return context, grant


class _ControlBudget:
    """Validation delegate: control occurrences counted once in its outer slot."""
    def __init__(self, budget): self.budget = budget
    def inspect(self, value, **unused): return self.budget.inspect(value)


def binding_in_control(value, budget):
    return BindingRequest.parse(value, _ControlBudget(budget))
