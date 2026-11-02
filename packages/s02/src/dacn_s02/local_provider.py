"""One owned, cloud-disabled Ollama daemon and a conservative pinned Qwen bound."""
from pathlib import Path
import hashlib
import os
import re
import socket
import struct
import subprocess
import time
import tomllib

from .codec_boundary import decode
from .errors import require, storage_error
from .local_journal import LIMITS
from .local_transport import exchange, Exchange

QWEN_MANIFEST='845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e'
QWEN_TEMPLATE='eb4402837c7829a690fa845de4d7f3fd842c2adee476d5341da8a46ea9255175'


def file_sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def gguf_metadata(path):
    """Read bounded GGUF v3 metadata only; never load tensor data into Python."""
    with Path(path).open('rb') as f:
        def read(n):
            require(0<=n<=32*1024*1024 and f.tell()+n<=64*1024*1024,'local_gguf_metadata_cap')
            raw=f.read(n);require(len(raw)==n,'local_gguf_eof');return raw
        def scalar(fmt):return struct.unpack('<'+fmt,read(struct.calcsize('<'+fmt)))[0]
        def string():return read(scalar('Q')).decode('utf-8')
        formats={0:'B',1:'b',2:'H',3:'h',4:'I',5:'i',6:'f',7:'?',10:'Q',11:'q',12:'d'}
        def value(kind,depth=0):
            require(depth<2,'local_gguf_depth')
            if kind==8:return string()
            if kind==9:
                sub=scalar('I');n=scalar('Q');require(n<=1000000,'local_gguf_array_cap')
                return [value(sub,depth+1) for _ in range(n)]
            require(kind in formats,'local_gguf_type');return scalar(formats[kind])
        require(read(4)==b'GGUF' and scalar('I')==3,'local_gguf_v3')
        scalar('Q');n=scalar('Q');require(n<=10000,'local_gguf_keys')
        out={}
        for _ in range(n):
            key=string();require(key not in out,'local_gguf_duplicate');out[key]=value(scalar('I'))
        return out


def byte_alphabet():
    ordinary=list(range(ord('!'),ord('~')+1))+list(range(0xa1,0xad))+list(range(0xae,0x100))
    chars=dict(zip(ordinary,ordinary));extra=0
    for b in range(256):
        if b not in chars:chars[b]=256+extra;extra+=1
    return {chr(chars[b]) for b in range(256)}


class LocalDaemon:
    origin='provider_local'
    def __init__(self, config, log_dir):
        p=Path(config).resolve();data=tomllib.loads(p.read_text())
        require(set(data)=={'endpoint','model','model_digest','runtime_version','ollama_binary','models_dir'},'local_provider_config_fields')
        require(re.fullmatch(r'http://127\.0\.0\.1:([1-9][0-9]{0,4})',data['endpoint']) is not None,'local_provider_loopback')
        require(1<=int(data['endpoint'].rsplit(':',1)[1])<=65535,'local_provider_port')
        require(data['model']=='qwen2.5:7b' and data['model_digest']==QWEN_MANIFEST,'local_supported_installed_model')
        require(data['runtime_version']=='0.33.2','local_vetted_runtime')
        self.cfg=dict(data,ollama_binary=str((p.parent/data['ollama_binary']).resolve()),models_dir=str((p.parent/data['models_dir']).resolve()))
        self.log_dir=Path(log_dir);self.proc=None;self.log=None;self.log_path=None;self.weight_signature=None;self.proof=None

    def configuration(self):return dict(self.cfg)

    def pin(self):
        models=Path(self.cfg['models_dir']);manifest=models/'manifests/registry.ollama.ai/library/qwen2.5/7b'
        raw=manifest.read_bytes();require(hashlib.sha256(raw).hexdigest()==self.cfg['model_digest'],'local_manifest_digest')
        value=decode(raw);layers=value['layers']
        def layer(kind):
            matches=[x for x in layers if x['mediaType']=='application/vnd.ollama.image.'+kind]
            require(len(matches)==1,'local_layer_inventory');item=matches[0]
            require(re.fullmatch('sha256:[0-9a-f]{64}',item['digest']) is not None,'local_layer_digest')
            path=models/'blobs'/item['digest'].replace(':','-');require(path.is_file() and path.stat().st_size==item['size'],'local_layer_present')
            return path,item['digest'][7:]
        template,template_hash=layer('template');require(template_hash==QWEN_TEMPLATE and file_sha(template)==template_hash,'local_template_pin')
        weights,weights_hash=layer('model');st=weights.stat();signature=(str(weights),st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns)
        if signature!=self.weight_signature:
            require(file_sha(weights)==weights_hash,'local_weights_hash')
            metadata=gguf_metadata(weights)
            tokens=metadata.get('tokenizer.ggml.tokens',[])
            self.proof=dict(method='qwen2-byte-bpe-conservative/1',tokenizer_model=metadata.get('tokenizer.ggml.model'),pretokenizer=metadata.get('tokenizer.ggml.pre'),byte_alphabet_complete=byte_alphabet()<=set(tokens),context_length=metadata.get('qwen2.context_length'),add_bos=metadata.get('tokenizer.ggml.add_bos_token'),add_eos=metadata.get('tokenizer.ggml.add_eos_token'),template_sha256=template_hash,template_bytes=template.stat().st_size,weights_sha256=weights_hash)
            self.weight_signature=signature
        return dict(model=self.cfg['model'],model_digest=self.cfg['model_digest'],endpoint=self.cfg['endpoint'],runtime_version=self.cfg['runtime_version'],binary_sha256=file_sha(self.cfg['ollama_binary']),template_sha256=template_hash,weights_sha256=weights_hash)

    def bound(self,messages):
        proof=dict(self.proof or {})
        # This allowlist binds the proof to the inspected Qwen2 tokenizer and
        # exact Go chat template. BPE merges cannot increase the initial one
        # symbol per UTF-8 byte count. Special tokens reduce that count. With
        # exactly system+user, no tools/history, template literals fit within
        # twice the entire template file; 64 covers BOS/EOS/control overhead.
        supported=(proof.get('tokenizer_model')=='gpt2' and proof.get('pretokenizer')=='qwen2'
                   and proof.get('byte_alphabet_complete') and proof.get('context_length')==32768
                   and proof.get('add_bos') in (False,None) and proof.get('add_eos') in (False,None)
                   and len(messages)==2 and [m.get('role') for m in messages]==['system','user']
                   and all(set(m)=={'role','content'} and type(m['content']) is str for m in messages))
        upper=sum(len(m['content'].encode('utf-8')) for m in messages)+2*proof.get('template_bytes',0)+64 if supported else None
        return dict(proof=proof,input_upper_bound=upper,output_reserved=LIMITS['num_predict'],context_limit=LIMITS['num_ctx'],eligible=bool(supported and upper+LIMITS['num_predict']<=LIMITS['num_ctx']),reason='conservative upper bound, not actual token count' if supported else 'tokenizer/template proof unavailable')

    def start(self, deadline):
        if self.proc is not None:
            require(self.proc.poll() is None,'local_owned_daemon_alive');return
        port=int(self.cfg['endpoint'].rsplit(':',1)[1])
        with socket.socket() as sock:
            try:sock.bind(('127.0.0.1',port))
            except OSError:raise storage_error('Endpoint occupied; refusing to attach to an unowned daemon')
        self.log_dir.mkdir(parents=True,exist_ok=True)
        self.log_path=self.log_dir/('ollama-'+str(time.time_ns())+'.log');self.log=self.log_path.open('xb')
        env={k:os.environ[k] for k in ('PATH','HOME','USER','TMPDIR') if k in os.environ}
        env.update(OLLAMA_HOST=f'127.0.0.1:{port}',OLLAMA_NO_CLOUD='1',OLLAMA_MODELS=self.cfg['models_dir'],OLLAMA_NUM_PARALLEL='1')
        self.proc=subprocess.Popen([self.cfg['ollama_binary'],'serve'],cwd=self.log_dir,env=env,stdout=self.log,stderr=subprocess.STDOUT)
        while time.monotonic()<deadline:
            require(self.proc.poll() is None,'local_daemon_start_failed')
            result=exchange(self.cfg['endpoint'],method='GET',path='/api/version',body=b'',timeout_seconds=min(1,max(.001,deadline-time.monotonic())),response_limit_bytes=65536)
            if result.complete_body and result.status==200:
                require(decode(result.body).get('version')==self.cfg['runtime_version'],'local_runtime_pin')
                require(b'Ollama cloud disabled: true' in self.log_path.read_bytes(),'local_cloud_disabled_log')
                return
            time.sleep(.05)
        raise TimeoutError('Local daemon readiness deadline')

    def send(self,raw,remaining):
        deadline=time.monotonic()+remaining
        try:
            self.start(deadline)
            tags=exchange(self.cfg['endpoint'],method='GET',path='/api/tags',body=b'',timeout_seconds=max(.001,deadline-time.monotonic()),response_limit_bytes=LIMITS['body_bytes'])
            require(tags.complete_body and tags.status==200,'local_tags_preflight')
            found=[m for m in decode(tags.body)['models'] if m['name']==self.cfg['model']]
            require(len(found)==1 and found[0]['digest'].removeprefix('sha256:')==self.cfg['model_digest'],'local_runtime_model_pin')
            left=deadline-time.monotonic()
            if left<=0:raise TimeoutError()
            return exchange(self.cfg['endpoint'],method='POST',path='/api/chat',body=raw,timeout_seconds=left,response_limit_bytes=LIMITS['body_bytes'])
        except (TimeoutError,OSError):return Exchange(None,(),b'',False,False,'timeout',max(0,int(remaining*1000)))

    def close(self):
        if self.proc is not None:
            self.proc.terminate()
            try:self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:self.proc.kill();self.proc.wait(timeout=5)
            self.proc=None
        if self.log is not None:self.log.close();self.log=None
