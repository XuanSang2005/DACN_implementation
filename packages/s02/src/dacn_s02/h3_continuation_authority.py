"""External C-only local/synthetic exact authority; historical reviews stay separate."""
from pathlib import Path
from hashlib import sha256
from .h3_policy import SemanticTrustContext
from .h3_limits import need
from .h3_review_io import bounded,unavailable
from .errors import S02Error
from .h3_continuation_contracts import validate
from .h3_continuation_inputs import authorize


class LocalSyntheticContinuationAuthority:
    def __init__(self,path,trust):
        need(type(trust) is SemanticTrustContext,'c_external_semantic_tuple');self.path=Path(path);self.trust=trust
    def read(self,budget):
        try:
            raw=bounded(self.path,budget,'authority');need(sha256(raw).hexdigest()==self.trust.expected_sha256,'c_authority_control_hash')
            v=validate('Authority',budget.parse(raw,kind='authority',slot='c.authority'),budget)
            need(v['provider_id']==self.trust.provider_id and v['provider_version']==self.trust.provider_version,'c_authority_provider');return raw
        except (OSError,S02Error,TypeError,ValueError) as exc:unavailable('semantic_authority',exc)
    def authorize(self,value,budget):
        grant=authorize(self.read(budget),self.trust,value,budget);need(grant.decision=='allow','c_authority_denied');return grant
