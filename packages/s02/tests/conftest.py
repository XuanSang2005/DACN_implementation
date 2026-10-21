"""Independent synthetic sources and real encoder instrumentation."""
import sys
import os
from pathlib import Path
import pytest
import simplejson
import simplejson.encoder as encoder

# Test helpers only; never add s02/src or S01/src to sys.path.
sys.path.insert(0,str(Path(__file__).parent))
from helpers import Foundation

def pytest_addoption(parser): parser.addoption('--encoder-backend',choices=('c','python'),default='c')
def pytest_configure(config):
    backend=config.getoption('--encoder-backend');simplejson._toggle_speedups(backend=='c')
    os.environ['S02_TEST_CODEC_BACKEND']=backend  # Test workers only; never a product setting.
    if backend=='c' and encoder.c_make_encoder is None: raise RuntimeError('Requested C encoder unavailable')
    counts={'c':0,'python':0}
    if backend=='c':
        original=encoder.c_make_encoder
        def observed(*a,**kw): counts['c']+=1;return original(*a,**kw)
        encoder.c_make_encoder=observed
    py=encoder._make_iterencode
    def observed_py(*a,**kw): counts['python']+=1;return py(*a,**kw)
    encoder._make_iterencode=observed_py;config.backend_counts=counts
def pytest_terminal_summary(terminalreporter,exitstatus,config):
    terminalreporter.write_line(f'S02_ENCODERS selected={config.getoption("--encoder-backend")} calls={config.backend_counts}')
@pytest.fixture
def foundation(tmp_path): return Foundation(tmp_path)
