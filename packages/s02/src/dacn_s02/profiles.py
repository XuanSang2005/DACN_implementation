"""Packaged, closed profile registry. No storage, import, or runtime patching.

DB1 callers default to L1. An E1 caller must supply authoritative owner maps;
this module does not infer metadata from payload shape or accept feature flags.
"""
from dataclasses import dataclass
from hashlib import sha256
from importlib.resources import files
import json
from types import MappingProxyType
from .errors import require

L1 = 's02-profile/legacy-a3'
E1 = 's02-profile/a1a2-v1'
REGISTRY_SHA256 = 'd36d80be7f768dd84ccd64306f8f7a32a5f9734be6332961a2daf0ed4cf50f7e'
PATHS = MappingProxyType({L1:'schemas/contract.json',E1:'schemas/profiles/a1a2-v1/contract.json'})

@dataclass(frozen=True)
class Profile:
    profile_id: str
    schema_bytes: bytes
    descriptor_bytes: bytes

    @property
    def schema(self):
        # Fresh trees: a caller cannot mutate a schema shared by another request.
        return json.loads(self.schema_bytes)

    @property
    def descriptor(self): return json.loads(self.descriptor_bytes)
    @property
    def schema_sha256(self): return sha256(self.schema_bytes).hexdigest()
    @property
    def descriptor_sha256(self): return sha256(self.descriptor_bytes).hexdigest()


def _load():
    root=files('dacn_s02');raw=root.joinpath('schemas/profiles/registry.json').read_bytes()
    require(sha256(raw).hexdigest()==REGISTRY_SHA256,'packaged_registry_hash')
    result={}
    for descriptor in json.loads(raw):
        pid=descriptor['profile_id'];schema=root.joinpath(PATHS[pid]).read_bytes()
        require(sha256(schema).hexdigest()==descriptor['schema_sha256'],'packaged_schema_hash')
        # Descriptor bytes are canonical compact ASCII, independent of registry layout.
        data=json.dumps(descriptor,sort_keys=True,separators=(',',':')).encode('ascii')
        result[pid]=Profile(pid,schema,data)
    require(set(result)==set(PATHS),'packaged_profile_inventory')
    return MappingProxyType(result)

REGISTRY = _load()

def get_profile(profile=L1):
    if isinstance(profile,Profile):
        require(profile.profile_id in REGISTRY and profile==REGISTRY[profile.profile_id],'profile_descriptor')
        return REGISTRY[profile.profile_id]
    require(type(profile) is str and profile in REGISTRY,'unknown_profile')
    return REGISTRY[profile]

def check_descriptor(descriptor, *, schema_bytes=None, descriptor_bytes=None):
    """Compare a future storage descriptor to the packaged allowlist only."""
    require(type(descriptor) is dict,'profile_descriptor')
    p=get_profile(descriptor.get('profile_id'))
    require(descriptor==p.descriptor,'profile_descriptor')
    if schema_bytes is not None: require(schema_bytes==p.schema_bytes,'profile_schema_bytes')
    if descriptor_bytes is not None: require(descriptor_bytes==p.descriptor_bytes,'profile_descriptor_bytes')
    return p

def owner_profiles(records, owner, profile_map):
    p=get_profile(owner)
    if profile_map is None:
        require(p.profile_id==L1,'explicit_record_profiles_required')
        return {i:L1 for i in records}
    require(set(profile_map)==set(records),'record_profile_inventory')
    return {i:get_profile(v).profile_id for i,v in profile_map.items()}

def blocking_statuses(profile=L1):
    return ('open','answered_pending_application') + (('resolution_pending_revalidation',) if get_profile(profile).profile_id==E1 else ())
