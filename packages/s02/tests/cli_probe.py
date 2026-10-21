"""Test harness selects/observes encoder before invoking the installed CLI."""
import json
from pathlib import Path
import sys
from process_worker import observe_backend
mode,counts=observe_backend()
from dacn_s02.cli import main
output_path=Path(sys.argv[1])
status=main(sys.argv[2:])
output_path.write_text(json.dumps(dict(backend=mode,encoder_calls=counts)))
raise SystemExit(status)
