"""Local/synthetic external trust adapters. No DB-derived trust fallback."""
from dataclasses import dataclass
from pathlib import Path
from hashlib import sha256
from .errors import S02Error
from .repository import Repository
from .h3_history import ReviewTrustContext,ReviewRegistry,HistoryData
from .h3_policy import SemanticTrustContext
from .h3_limits import need
from .h3_checkpoint_contracts import validate
from .h3_checkpoint_checks import authorize
from .h1_store import WorkStore
from . import store_profiles


def unavailable(lane,exc):
    raise S02Error('H3_'+lane.upper()+'_UNAVAILABLE','persistence',
        'Original external local/synthetic '+lane+' control unavailable or invalid: '+
        (exc.error['code'] if isinstance(exc,S02Error) else type(exc).__name__)) from exc


def bounded(path,budget,kind):
    budget.check()
    with Path(path).open('rb') as stream:raw=stream.read(getattr(budget.limits,kind+'_bytes')+1)
    budget.cap(kind+'_bytes',len(raw));budget.check()
    return raw


@dataclass(frozen=True)
class FrozenReviewRegistry:
    registry: ReviewRegistry

    def rehash(self,budget):
        try:
            raw=bounded(self.registry.trust.path,budget,'registry')
            need(sha256(raw).hexdigest()==self.registry.trust.expected_sha256 and raw==self.registry.raw,'b_original_registry_changed')
        except (OSError,S02Error) as exc:unavailable('historical_reviews',exc)

    def open_repository(self,path,**options):
        need('reviews' not in options,'b_factory_review_map_not_caller_dict')
        return Repository(path,reviews=self.registry.reviews(),**options)

    def checked(self,repo,connection,budget):
        self.rehash(budget)
        info=store_profiles.check(connection,path=repo.path)
        need(info['metadata']['origin_kind']=='fresh' and info['metadata']['store_id']==self.registry.trust.expected_store_id,'b_fresh_store_identity')
        state=WorkStore(repo).state(connection)  # _check with external map already installed
        h=HistoryData(**state,registry=self.registry,store_id=info['metadata']['store_id'],budget=budget)
        return h,info


class LocalSyntheticHistoricalReviews:
    @staticmethod
    def load(trust,budget):
        try:
            need(type(trust) is ReviewTrustContext,'b_external_review_tuple_required')
            raw=bounded(trust.path,budget,'registry')
            return FrozenReviewRegistry(ReviewRegistry.parse(raw,trust,budget))
        except (OSError,S02Error,TypeError,ValueError) as exc:unavailable('historical_reviews',exc)


class LocalSyntheticCheckpointAuthority:
    def __init__(self,path,trust):
        need(type(trust) is SemanticTrustContext,'b_external_semantic_tuple_required')
        self.path=Path(path);self.trust=trust

    def read(self,budget):
        try:
            raw=bounded(self.path,budget,'authority')
            need(sha256(raw).hexdigest()==self.trust.expected_sha256,'b_authority_control_hash')
            value=validate('Authority',budget.parse(raw,kind='authority',slot='b.authority'),budget)
            need(value['provider_id']==self.trust.provider_id and value['provider_version']==self.trust.provider_version,'b_authority_control_provider')
            return raw
        except (OSError,S02Error,TypeError,ValueError) as exc:unavailable('semantic_authority',exc)

    def authorize(self,value,budget):
        raw=self.read(budget);grant=authorize(raw,self.trust,value,budget)
        need(grant.decision=='allow','b_semantic_authority_denied')
        return grant
