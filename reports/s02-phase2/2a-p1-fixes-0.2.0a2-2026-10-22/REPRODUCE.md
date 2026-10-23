# Tái lập bản sửa P1 a2

Tạo thư mục mới; không chạy scripts có output cạnh file vào handoff đã niêm phong. Mỗi `*.command.json` ghi argv/cwd/environment/exit thực, log cùng tên. Runner tạo report-dir mới, chạy từng package/backend trong process/cwd tạm riêng và instrument encoder thực.

```sh
DACN_ROOT=/Users/macbookpro/Documents/DACN_implementation
DACN_HANDOFF="$DACN_ROOT/reports/s02-phase2/2a-p1-fixes-0.2.0a2-2026-10-22"
DACN_CHECK=$(mktemp -d /tmp/dacn-p1-a2-review.XXXXXX)
DACN_PY="$DACN_CHECK/venv/bin/python"
DACN_AUDIT=/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-2a-p1-0.2.0a1-2026-10-22-150954
"$DACN_ROOT/.runtime/python/bin/python3.13" -B -m venv --without-pip "$DACN_CHECK/venv"
"$DACN_ROOT/.tools/uv" pip install --python "$DACN_PY" --no-index \
  --find-links "$DACN_ROOT/.tools/wheelhouse" --find-links "$DACN_ROOT/dist" \
  --require-hashes -r "$DACN_ROOT/packages/s02/requirements-dev.lock"
"$DACN_PY" -B -m pip install --no-index --no-deps --force-reinstall \
  "$DACN_HANDOFF/release/dacn_s02-0.2.0a2-py3-none-any.whl" \
  "$DACN_HANDOFF/release/dacn_s01-0.1.0a6-py3-none-any.whl"
cd "$DACN_CHECK"
unset PYTHONPATH PYTEST_ADDOPTS PYTEST_PLUGINS
"$DACN_PY" -B "$DACN_ROOT/tools/run_checks.py" --package all --report-dir "$DACN_CHECK/regression"
"$DACN_PY" -B "$DACN_ROOT/tools/run_checks.py" --package s02 --audit-only \
  --audit-file "$DACN_AUDIT/test_independent_p1.py" \
  --audit-file "$DACN_AUDIT/test_independent_p1_followup.py" \
  --audit-file "$DACN_AUDIT/test_independent_p1_controls.py" \
  --report-dir "$DACN_CHECK/audit"
"$DACN_PY" -B "$DACN_ROOT/tools/collect_evidence.py" --package all \
  --wheel-dir "$DACN_HANDOFF/release" \
  --baseline-wheel "s02=$DACN_ROOT/reports/s02-phase2/2a-p1-2026-10-22/release/dacn_s02-0.2.0a1-py3-none-any.whl" \
  --report-dir "$DACN_CHECK/package-evidence"
```

Wheel S01 trong release là **bản sao nguyên ZIP wheel lịch sử** từ dist, không rebuild. Cài lại bằng đường dẫn cụ thể để có direct_url cho collector; không thay payload/hash đã pin trong lock. Bản a1 dùng để tái hiện: `reports/s02-phase2/2a-p1-2026-10-22/release/dacn_s02-0.2.0a1-py3-none-any.whl`. Baseline được cài trong môi trường mới riêng và chạy nguyên ba audit files trước sửa; kỳ vọng 5 fail/7 pass mỗi backend.

Differential: tạo venv a3 từ cùng locks, cài wheel `reports/s02-phase1/fixes-0.1.0a3/builds/dacn_s02-0.1.0a3-py3-none-any.whl`. Chạy `differential_l1.py c <output mới>` và `python <output mới>` bằng interpreter a3 và a2; đối chiếu toàn `outcomes`, không chỉ counts. Script đọc corpus cố định; không sửa corpus. Lệnh đã chạy nằm trong `differential-*.command.json`.

Build lại: copy src/pyproject S02 và `tools/build_packages.py` sang cây mới giữ layout. Chạy builder bằng dependencies trong locks, output mới. `build_isolated.py` ghi provenance cạnh bản script nên phải copy script vào evidence directory mới nếu tái dùng. Không build trong cache package, không ghi đè wheel a1/a2 đã bàn giao. So payload + METADATA/WHEEL; không yêu cầu ZIP hash rebuild bằng ZIP release.

`verify_and_seal.py` là script tạo evidence **create-only**, không chạy lại tại handoff này. Nó kiểm inventory trước/sau, nguyên byte oracle, kết quả runner, input hashes và diff. `MANIFEST.json` liệt kê mọi file handoff trừ chính manifest; kiểm hash trước khi dùng evidence.
