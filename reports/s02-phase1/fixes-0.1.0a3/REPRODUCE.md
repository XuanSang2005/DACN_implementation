# Tái lập bản sửa S02 a3

Chạy trên runtime đã pin ở workspace macOS arm64, không cài editable và không thêm production src vào PYTHONPATH. Chọn thư mục output mới; không ghi lên report này. Các lệnh dưới đây là hướng dẫn; argv thực của lượt bàn giao nằm trong JSON commands liên kết ở [báo cáo](IMPLEMENTATION_REPORT.md).

```sh
DACN_ROOT=/Users/macbookpro/Documents/DACN_implementation
DACN_ENV_ROOT=$(mktemp -d -t dacn-a3-recheck)
DACN_PY="$DACN_ENV_ROOT/venv/bin/python"
DACN_RESULTS="$DACN_ENV_ROOT/results"
DACN_WHEELS="$DACN_ROOT/reports/s02-phase1/fixes-0.1.0a3/builds"
"$DACN_ROOT/.runtime/python/bin/python3.13" -B -m venv --without-pip "$DACN_ENV_ROOT/venv"
"$DACN_ROOT/.tools/uv" pip install --python "$DACN_PY" --no-index \
  --find-links "$DACN_ROOT/.tools/wheelhouse" --find-links "$DACN_ROOT/dist" \
  --require-hashes -r "$DACN_ROOT/packages/s02/requirements-dev.lock"
"$DACN_PY" -B -m pip install --no-index --no-deps --force-reinstall \
  "$DACN_ROOT/dist/dacn_s01-0.1.0a6-py3-none-any.whl" \
  "$DACN_WHEELS/dacn_s02-0.1.0a3-py3-none-any.whl"
"$DACN_PY" -B -m pip check
cd "$DACN_ENV_ROOT"
unset PYTHONPATH PYTEST_ADDOPTS PYTEST_PLUGINS
"$DACN_PY" -B "$DACN_ROOT/tools/collect_evidence.py" --package all \
  --wheel-dir "$DACN_WHEELS" \
  --baseline-wheel "s02=$DACN_ROOT/s02/dist/dacn_s02-0.1.0a2-py3-none-any.whl" \
  --report-dir "$DACN_RESULTS/packages"
"$DACN_PY" -B "$DACN_ROOT/packages/s01/tools/run_checks.py" --report-dir "$DACN_RESULTS/s01"
"$DACN_PY" -B "$DACN_ROOT/packages/s02/tools/run_checks.py" --report-dir "$DACN_RESULTS/s02"
"$DACN_PY" -B -m unittest discover -s "$DACN_ROOT/tools/tests" -p 'test_*.py' -v
"$DACN_PY" -B "$DACN_ROOT/tools/check_layout.py" --report-dir "$DACN_RESULTS/smoke"
```

Pin hai đường dẫn audit gốc sau rồi chạy, không copy sửa assertions:

```sh
DACN_AUDITS=/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits
"$DACN_PY" -B "$DACN_ROOT/packages/s02/tools/run_checks.py" --audit-only \
  --audit-file "$DACN_AUDITS/s02-phase1-0.1.0a1-2026-10-19/test_independent_audit.py" \
  --audit-file "$DACN_AUDITS/s02-phase1-0.1.0a2-2026-10-19/test_followup_boundaries.py" \
  --report-dir "$DACN_RESULTS/audits"
```

Runner tạo process riêng/backend, dùng cwd/DB tạm ngoài checkout và instrumentation thật. Archive DB synthetic trong report mới không phải state vận hành. Kỳ vọng: S01 986, S02 217, audit a1 7, audit S02-05 4 passed mỗi backend; tooling 344 tests. Không skip/xfail hoặc đổi expected để đạt. Các ca `S02_05_rollback` / `S02_05_checked_read` có trong `s02/observations.json`; ca checked-read tự dựng DB lỗi trong fixture riêng rồi phục hồi validator trước đọc, không sửa DB bằng chứng gốc.

Build lại: `tools/build_packages.py --package s02 --output-dir <mới>` hoặc sao chép nguyên bytes src/pyproject và builder giữ relative layout sang vùng tạm như [build-input-provenance.json](build-input-provenance.json), rồi chạy builder ở bản sao. Không đổi version để ép hash ZIP; so payload/metadata đầy đủ. Nếu dùng wheel rebuild mới, cài nó trước collector và trỏ `--wheel-dir` tới thư mục chứa đúng wheel đã cài; bổ sung bản sao S01 a6 nguyên bytes nếu chọn `--package all`. Collector kiểm ZIP hash qua direct URL; không sửa lock để thêm ZIP mới. Giữ diff a2 → a3 để audit, không so a3 bằng a2 hoặc bỏ baseline.

Wrappers không nhận `--package`, `--package=...`, `--pack=...`; cần selector thì dùng entry point root. Collector wrapper S02 vẫn cần `--baseline-wheel s02=...`. Không ghi vào `dist`, `s02/dist`, báo cáo cũ, dataset hoặc audit gốc. Không triển khai Đợt 2 từ các lệnh này.
