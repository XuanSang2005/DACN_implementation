# Tái lập 2A-P1

Dùng thư mục mới cho mọi lần chạy; không ghi đè evidence này. Các files `*.command.json` và logs cùng tên ghi argv/cwd/exit code thực chạy. Runtime CPython/macOS arm64 và dependencies từ locks hiện hành; không thêm production source vào sys.path.

```sh
DACN_ROOT=/Users/macbookpro/Documents/DACN_implementation
DACN_CHECK=$(mktemp -d -t dacn-p1-review)
DACN_PY="$DACN_CHECK/venv/bin/python"
DACN_HANDOFF="$DACN_ROOT/reports/s02-phase2/2a-p1-2026-10-22"
"$DACN_ROOT/.runtime/python/bin/python3.13" -B -m venv --without-pip "$DACN_CHECK/venv"
"$DACN_ROOT/.tools/uv" pip install --python "$DACN_PY" --no-index \
  --find-links "$DACN_ROOT/.tools/wheelhouse" --find-links "$DACN_ROOT/dist" \
  --require-hashes -r "$DACN_ROOT/packages/s02/requirements-dev.lock"
"$DACN_PY" -B -m pip install --no-index --no-deps \
  "$DACN_HANDOFF/release/dacn_s02-0.2.0a1-py3-none-any.whl"
"$DACN_PY" -B -m pip check
"$DACN_PY" - "$DACN_ROOT/dist/dacn_s01-0.1.0a6-py3-none-any.whl" "$DACN_HANDOFF/release/dacn_s01-0.1.0a6-py3-none-any.whl" <<'PYVERIFY'
import sys
from zipfile import ZipFile
def payload(path):
    with ZipFile(path) as z:
        return {n:z.read(n) for n in z.namelist() if n.startswith('dacn_s01/') or n.endswith(('/METADATA','/WHEEL'))}
assert payload(sys.argv[1]) == payload(sys.argv[2])
print('S01 payload/METADATA/WHEEL equal before replacement')
PYVERIFY
"$DACN_PY" -B -m pip install --no-index --no-deps --force-reinstall \
  "$DACN_HANDOFF/release/dacn_s01-0.1.0a6-py3-none-any.whl"
cd "$DACN_CHECK"
unset PYTHONPATH PYTEST_ADDOPTS PYTEST_PLUGINS
"$DACN_PY" -B "$DACN_ROOT/tools/run_checks.py" --package all --report-dir "$DACN_CHECK/checks"
"$DACN_PY" -B "$DACN_ROOT/tools/collect_evidence.py" --package all \
  --wheel-dir "$DACN_HANDOFF/release" \
  --baseline-wheel "s02=$DACN_ROOT/reports/s02-phase1/fixes-0.1.0a3/builds/dacn_s02-0.1.0a3-py3-none-any.whl" \
  --report-dir "$DACN_CHECK/package-evidence"
"$DACN_PY" -B "$DACN_HANDOFF/verify_fixtures.py"
```

S01 lock cài wheel lịch sử a6 từ `dist/`. Nếu collector yêu cầu đúng ZIP/direct_url của wheel rebuild trong `release/`, đối chiếu payload/METADATA/WHEEL với wheel đã cài trước khi reinstall cùng version. Lượt bàn giao đã có [bằng chứng trước thay wheel](s01-before-wheel-replacement.json) và [lệnh thay wheel](install-rebuilt-s01.command.json). Không sửa lock để thêm hash rebuild. Có thể dùng đúng wheel lịch sử ở thư mục kiểm chứng mới để collector so same-version; phải trỏ wheel-dir tới wheel thực cài và giữ payload equality.

Audit regressions giữ nguyên file gốc và assertions, dùng adapter chỉ chỉ đường test helpers:

```sh
DACN_AUDITS=/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits
"$DACN_PY" -B "$DACN_ROOT/tools/run_checks.py" --package s02 --audit-only \
  --audit-file "$DACN_AUDITS/s02-phase1-0.1.0a1-2026-10-19/test_independent_audit.py" \
  --audit-file "$DACN_AUDITS/s02-phase1-0.1.0a2-2026-10-19/test_followup_boundaries.py" \
  --report-dir "$DACN_CHECK/audit-regressions"
```

Đây là chạy lại oracle lịch sử trên package mới, không phải audit độc lập P1.

Differential L1: cài wheel a3 và wheel P1 trong **hai venv riêng** từ cùng locks; chạy `differential_l1.py c <file mới>` và `differential_l1.py python <file mới>` bằng từng interpreter. Script đọc fixture L1 cố định `canonical-fixtures/l1-root.json`; so toàn `outcomes`, gồm valid/invalid, diagnostics và schema-walk paths. Số counts encoder có thể khác giữa version; backend được instrument thật, acceptance/error phải khớp. Script chỉ ghi output do caller chọn, không sửa fixture.

Canonical E1 mới dùng `canonical-fixtures-final/`. Các bản trong `canonical-fixtures/` là intermediate và không phải bộ E1 bàn giao cuối; fixture L1 ở đó giữ nguyên làm corpus differential. `verify_fixtures.py` chỉ đọc bộ cuối và không ghi lại. Generator `create_fixtures.py` create-only; muốn tái sinh hãy copy script cùng layout vào thư mục mới hoặc sửa **bản sao** output path, không chạy trên thư mục evidence đã có.

Build lại cần **copy src package + pyproject + workspace builder vào cây mới**, giữ relative paths `packages/s02/` và `tools/build_packages.py`, rồi chạy builder trong cây đó. Không build trực tiếp trên cache `packages/s02/build/`/egg-info cũ. `build_isolated.py` minh họa việc copy, manifest hash input nằm trong `release-build-provenance.json`; script tự ghi provenance cạnh chính nó nên dùng bản sao khi tái lập. Wheel handoff duy nhất là `release/`, các build khác là lịch sử tự kiểm trong lượt P1.

Không cần DB vận hành, dataset, credentials hoặc mạng. Tests dùng synthetic nguồn và state tạm ngoài checkout; P1 không có đường ghi E1 hoặc migration. Kết quả review giả định trong fixtures không phải quyết định người dùng.
