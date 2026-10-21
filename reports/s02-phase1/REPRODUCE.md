# Tái lập Đợt 1 S02

Phạm vi local macOS arm64, CPython **3.13.16 có GIL**, SQLite **3.53.1**. Các lệnh dưới đây là hướng dẫn tái lập; lệnh thực đã chạy, working directory và exit code nằm trong `*-commands.json`, `manifest.json` và logs. Không dùng dataset hoặc kho S01 thật để chạy tests.

## Môi trường riêng và wheel

Từ root implementation, đặt `DACN_ROOT` theo checkout đang audit. Dùng interpreter baseline đã kiểm, không ghi đè `.venv` hoặc locks S01.

```sh
DACN_ROOT=/Users/macbookpro/Documents/DACN_implementation
cd "$DACN_ROOT"
"$DACN_ROOT/.venv/bin/python" -B -m venv --without-pip s02/.audit-venv
"$DACN_ROOT/.tools/uv" pip install \
  --python "$DACN_ROOT/s02/.audit-venv/bin/python" \
  --no-index --find-links "$DACN_ROOT/.tools/wheelhouse" \
  --find-links "$DACN_ROOT/dist" --require-hashes \
  -r "$DACN_ROOT/s02/requirements-dev.lock"
"$DACN_ROOT/s02/.audit-venv/bin/python" -B -m pip wheel \
  --no-index --no-deps --no-build-isolation \
  --wheel-dir "$DACN_ROOT/s02/audit-dist" "$DACN_ROOT/s02"
"$DACN_ROOT/s02/.audit-venv/bin/python" -B -m pip install \
  --no-index --no-deps "$DACN_ROOT/s02/audit-dist/dacn_s02-0.1.0a1-py3-none-any.whl"
"$DACN_ROOT/s02/.audit-venv/bin/python" -B -m pip check
```

Chỉ tạo `.audit-venv`/`audit-dist` mới. Nếu đã tồn tại, chọn tên mới để không ghi đè artifacts audit. Lock có hashes của các wheels baseline dành cho macOS arm64/CPython 3.13; không tuyên bố lock portable cho OS/ABI khác. S01 được cài từ `dist/dacn_s01-0.1.0a6-py3-none-any.whl`, không editable install. Dependency trực tiếp S02 là S01 a6 và jsonschema 4.26.0; simplejson 4.2.0 đi qua S01. Không SDK LLM/renderer.

Build lại có thể đổi metadata ZIP/timestamp và hash toàn wheel. Đối chiếu nội dung package qua manifest, không lấy hash toàn ZIP khác nhau làm bằng chứng source khác. Wheel bàn giao có hash riêng trong `manifest.json`.

## Chạy tests ngoài checkout

Runner tự tạo cwd tạm **ngoài checkout**, bỏ `PYTHONPATH/PYTEST_ADDOPTS/PYTEST_PLUGINS`, tắt plugin autoload/cache và bytecode, chạy package installed. Tests không thêm `src` vào sys.path; chỉ thêm thư mục helpers của tests.

```sh
"$DACN_ROOT/s02/.audit-venv/bin/python" -B \
  "$DACN_ROOT/s02/tools/run_checks.py" --suite s02
"$DACN_ROOT/s02/.audit-venv/bin/python" -B \
  "$DACN_ROOT/s02/tools/run_checks.py" --suite s01
```

Runner này ghi logs vào `reports/s02-phase1/`. Auditor muốn giữ nguyên bằng chứng bàn giao nên chạy lệnh pytest trực tiếp dưới đây và chuyển stdout/stderr sang thư mục audit riêng, hoặc dùng bản sao workspace. Không sửa các báo cáo audit độc lập ở thư mục bên ngoài.

```sh
AUDIT_WORK=$(mktemp -d)
cd "$AUDIT_WORK"
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 \
  "$DACN_ROOT/s02/.audit-venv/bin/python" -B -m pytest \
  -c "$DACN_ROOT/s02/pyproject.toml" "$DACN_ROOT/s02/tests" \
  --encoder-backend=c -s -v --tb=short -p no:cacheprovider
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 \
  "$DACN_ROOT/s02/.audit-venv/bin/python" -B -m pytest \
  -c "$DACN_ROOT/s02/pyproject.toml" "$DACN_ROOT/s02/tests" \
  --encoder-backend=python -s -v --tb=short -p no:cacheprovider
```

Đối với S01, thay config bằng `$DACN_ROOT/pyproject.toml`, thư mục tests bằng `$DACN_ROOT/tests`; chạy cả hai backends. Bỏ các biến `PYTHONPATH`, `PYTEST_ADDOPTS`, `PYTEST_PLUGINS` nếu shell audit đang đặt chúng. `S02_TEST_EVIDENCE_DIR` chỉ là tùy chọn của test harness để giữ DB synthetic; không là option runtime. Instrumentation quan sát encoder factory; process con/CLI harness có số đếm riêng. Decoder S01 dùng stdlib JSON, không có lựa chọn decoder C/Python của simplejson.

## Init, intake và lookup

Ví dụ config **do người vận hành tạo ngoài checkout/dataset**, không là config production đi kèm package:

```toml
state_dir = "s02-state"
busy_timeout_ms = 5000
dataset_roots = ["/path/to/existing/read-only-dataset"]
protected_roots = ["/path/to/implementation"]

[s01_stores]
selected = "/path/to/separate-s01-state/s01.sqlite3"
```

Relative paths tính từ directory chứa config. `s01_stores` chứa **DB file**, `state_dir` là directory S02. Các roots bảo vệ phải tồn tại; không để placeholder nguyên dạng rồi chạy. Bỏ `dataset_roots` nếu không dùng dataset; tests dùng kho S01 synthetic tạm được tạo bằng public Service API. Không có lệnh import JSON tự nhận validated.

```sh
"$DACN_ROOT/s02/.audit-venv/bin/python" -B -m dacn_s02 --config /path/to/s02.toml init
"$DACN_ROOT/s02/.audit-venv/bin/python" -B -m dacn_s02 --config /path/to/s02.toml start \
  --store-key selected --s01-run-id SELECTED_RUN \
  --expect-snapshot SELECTED_SNAPSHOT --receipt /path/to/new-receipt.json
"$DACN_ROOT/s02/.audit-venv/bin/python" -B -m dacn_s02 --config /path/to/s02.toml show-command \
  --receipt /path/to/new-receipt.json
"$DACN_ROOT/s02/.audit-venv/bin/python" -B -m dacn_s02 --config /path/to/s02.toml show-record \
  --id RECORD_ID
```

`start` chỉ archive nguồn đã checked lookup, tạo session và Run `steps=[]`, không tạo model hoặc chạy phân tích. `--expect-snapshot` tùy chọn; khi có phải khớp snapshot của run được chọn. Run unchanged vẫn archive riêng run source/origin source. Receipt create-only có `receipt_version=s02/1`, command ID và absolute state directory, ghi/fsync trước intake/T0. Không retry `start` bằng receipt cũ. `show-command` chỉ lookup; không có command trong store đã kiểm vẫn không chứng minh hiệu ứng ở một store khác chưa xảy ra.

Stdout là một JSON object; thông báo argparse/usage ở stderr. Exit: 0 init/intake/lookup thành công; 2 rejected/stale; 3 failed; 4 không tìm thấy; 64 usage. Exit 5 được dành cho lệnh blocked ở các đợt sau, chưa có command phân tích trả blocked trong CLI tối thiểu. Lookup command trả trạng thái bền vững của command bên trong `result`; exit 0 của lookup không đổi outcome rejected/stale lịch sử thành completed.

## API nền tảng và recovery

- `Repository.initialize/verify`, `get_record/get_blob/get_stage/get_command/heads`: kiểm DB, JSON/cột, refs và hashes. Không tìm thấy trả `None`; corruption/lỗi kho trả `S02Error` có kiểm soát.
- `Service.allocate_command_id/start`: chỗ cấp ID trước receipt; không tự đổi ID đã công bố. `start` từ chối ID đã có, yêu cầu lookup.
- `Repository.prepare/append_event/finalize`: **API nội bộ cho code được tin cậy**, không route import cho người dùng/LLM. Candidate generation/selection và consent thật sẽ thuộc Đợt 2. Một batch phải có Run đúng reserved ID; chỉ commit thành công mới trả kết quả.
- `get_record` giữ record lịch sử nguyên vẹn. Muốn dùng Validation/Bundle/Review/Handoff như kết quả hiện hành phải gọi `check_freshness`; lookup lịch sử không tự mang nghĩa được phép chuyển S03.
- `get_command.state=captured`: lấy chính staged bytes qua `get_stage`; không gửi lại. `dispatch_unknown` giữ unknown. Recovery intent riêng có parent command; finalization vẫn dùng command/reserved Run gốc. Chưa có CLI `recover` hay transport/API trong đợt này.

`collect_evidence.py` cài lại từ locks + wheel trong venv tạm mới, kiểm imports/pip/CLI init, so source–installed–wheel và kiểm inventory bảo vệ. Nó ghi reports mới; chạy bằng môi trường installed phù hợp, không dùng để sửa baseline hoặc dataset.
