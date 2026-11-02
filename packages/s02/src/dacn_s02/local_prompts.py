"""Pure, versioned prompt rendering; no source lookup, authority or LLM call.

The future service must supply checked source/base/Issues/aliases and bind these
exact rendered bytes. This function cannot turn caller data into trusted input.
"""
from hashlib import sha256
from importlib.resources import files

from .codec_boundary import encode
from .h1_candidates import schema


VERSION = 's02-local-prompts/1'


def render(step, context):
    if type(step) is not int or step not in (1, 2, 3, 4):
        raise ValueError('only steps 1 through 4')
    if type(context) is not dict:
        raise ValueError('context must be a caller-supplied checked context')
    root = files('dacn_s02').joinpath('prompts', 'local_v1')
    common = root.joinpath('common.txt').read_bytes()
    task = root.joinpath(f'step{step}.txt').read_bytes()
    # JSON-encode the complete user message as data; no str.format/substitution
    # of source text into the system instructions and no truncation/normalizing.
    payload = encode(dict(context=context, output_schema=schema(step))).decode('utf-8')
    messages = [dict(role='system', content=(common + b'\n' + task).decode('utf-8')),
                dict(role='user', content=payload)]
    raw = encode(messages)
    return dict(version=VERSION, step=step, messages=messages, messages_bytes=raw,
                messages_sha256=sha256(raw).hexdigest(),
                template_sha256=dict(common=sha256(common).hexdigest(), step=sha256(task).hexdigest()))


def reachable_schema(step):
    """Remove only unreachable definitions, retaining the same accepted language."""
    value=schema(step);definitions=value.pop('$defs');needed=set()
    def walk(node):
        if type(node) is dict:
            if '$ref' in node:
                reference=node['$ref']
                if not reference.startswith('#/$defs/'):
                    raise ValueError('unexpected external schema reference')
                name=reference.removeprefix('#/$defs/')
                if name not in needed:
                    needed.add(name);walk(definitions[name])
            for child in node.values():walk(child)
        elif type(node) is list:
            for child in node:walk(child)
    walk(value)
    value['$defs']={name:definitions[name] for name in definitions if name in needed}
    return value


def render_compact(step,context):
    """Same v1 template/source, separately versioned reachable-schema renderer."""
    result=render(step,context)
    result['template_version']=result['version']
    result['version']='s02-local-reachable-renderer/1'
    result['messages'][1]['content']=encode(dict(context=context,output_schema=reachable_schema(step))).decode('utf-8')
    raw=encode(result['messages'])
    result.update(messages_bytes=raw,messages_sha256=sha256(raw).hexdigest())
    return result
