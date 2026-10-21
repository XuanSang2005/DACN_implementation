# Tái lập bản sửa S02 0.1.0a2

Các lệnh dưới đây là cách tái lập, không thay logs lệnh thực chạy. Lệnh/exit/cwd đã chạy nằm trong `fresh-test-environment.json`, `build-commands.json`, `s02-commands.json`, `s01-commands.json`, `audit-commands.json` và `manifest.json`. Chạy bằng CPython 3.13.16 macOS arm64, dùng wheels offline/locks hiện có; không editable install, không thêm source vào PYTHONPATH.

## Cài wheel vào venv mới, ngoài checkout

```sh
S02_REPO=/Users/macbookpro/Documents/DACN_implementation
S02_VERIFY_DIR=$(mktemp -d -t dacn-s02-a2-verify)
S02_RESULTS=$(mktemp -d -t dacn-s02-a2-results)
"$S02_REPO/s02/.venv/bin/python" -B -m venv --without-pip "$S02_VERIFY_DIR/venv"
"$S02_REPO/.tools/uv" pip install --python "$S02_VERIFY_DIR/venv/bin/python" \
  --no-index --find-links "$S02_REPO/.tools/wheelhouse" \
  --find-links "$S02_REPO/dist" --require-hashes \
  -r "$S02_REPO/s02/requirements-dev.lock"
"$S02_VERIFY_DIR/venv/bin/python" -B -m pip install --no-index --no-deps \
  "$S02_REPO/s02/dist/dacn_s02-0.1.0a2-py3-none-any.whl"
cd "$S02_VERIFY_DIR"
"$S02_VERIFY_DIR/venv/bin/python" -B -m pip check
"$S02_VERIFY_DIR/venv/bin/python" -B -c \
  'import dacn_s01,dacn_s02; print(dacn_s01.__file__); print(dacn_s02.__file__); print(dacn_s02.__version__)'
```

Kỳ vọng imports ở `venv/.../site-packages`, S02 a2/S01 a6. Wheel a2 SHA-256:

`0b8824cb38f06308b760e14f8a0c2a7584a73df87a8356d767cf7aa1ae7457a5`

Không ghi lại wheel a1 hoặc báo cáo a1/a2 bàn giao khi tái lập. Nếu muốn rebuild, dùng thư mục output mới; ZIP metadata có thể khác, đối chiếu đầy đủ package payload theo manifest thay vì khẳng định deterministic wheel bytes.

## Chạy các suite trên hai backend

```sh
"$S02_VERIFY_DIR/venv/bin/python" -B "$S02_REPO/s02/tools/run_checks.py" \
  --suite s02 --report-dir "$S02_RESULTS"
"$S02_VERIFY_DIR/venv/bin/python" -B "$S02_REPO/s02/tools/run_checks.py" \
  --suite s01 --report-dir "$S02_RESULTS"
S02_AUDIT_TEST=/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-phase1-0.1.0a1-2026-10-19/test_independent_audit.py
"$S02_VERIFY_DIR/venv/bin/python" -B "$S02_REPO/s02/tools/run_checks.py" \
  --suite audit --audit-file "$S02_AUDIT_TEST" --report-dir "$S02_RESULTS"
```

Mỗi runner chạy C rồi Python, cwd tạm ngoài checkout, bỏ PYTHONPATH/PYTEST_ADDOPTS/PYTEST_PLUGINS, tắt plugin autoload/cache/bytecode. Chỉ thêm thư mục helpers/tests vào sys.path; không thêm production src. Instrumentation đếm factory encoder thật, test workers tự bật backend tương ứng. Cần đọc counts/logs chứ không chỉ tên tham số. Audit test ngoài giữ nguyên absolute helper path của agent audit; bộ regression portable tương đương đã có trong full suite S02.

Kỳ vọng mỗi backend: S02 **189 passed**, S01 **986 passed**, audit **7 passed**, exit 0; không skips/errors/failures. JUnit, command JSON, logs và observations được lưu trong `$S02_RESULTS`. Hai backend S02 lưu tổng **18 DB** race/kill bên dưới `process-artifacts/`. Các test DB khác dùng vùng tạm riêng, không dataset.

Để đối chiếu package bằng collector, dùng một thư mục báo cáo mới có `baseline.json` chứa inventory/hash đầu lượt **của chính lượt tái lập** rồi chạy `collect_evidence.py --report-dir ... --version 0.1.0a2`. Không copy kết quả hash cũ rồi coi là baseline mới. Manifest bàn giao đã chứa source/installed/wheel cho đủ 14 file S02 và 16 file S01, exact file inventories, toàn dependency/runtime và commands smoke clean install.

## Kiểm lại lịch sử a1

`check_legacy_stores.py` trong thư mục bàn giao nhận `audit-evidence.json` và thư mục `process-artifacts` a1; nó copy từng DB synthetic sang vùng tạm, không ghi vào kho gốc. Nếu chạy lại, copy script sang thư mục kết quả mới trước vì script ghi JSON cạnh chính nó. Kỳ vọng: 12 lịch sử lỗi bị checked read từ chối, hai intermediate models còn đọc được nhưng gate không cấp scope, 18 DB hợp lệ đọc được. Hash gốc phải giữ nguyên.

Probe chỉ kiểm foundation trong phạm vi bốn findings. Không dùng kết quả này như audit độc lập mới hoặc nghiệm thu S02/LLM/renderer.
