# Tái lập bằng output mới

Không chạy lại scripts create-only tại thư mục đã niêm phong. Copy harness sang thư mục mới hoặc chọn report/output/venv path mới. Không dùng wheel trong build-01/02/03, release, manifest-build làm đối tượng audit cuối.

Wheel audit duy nhất của S02: `audit-wheel/dacn_s02-0.3.0a1-py3-none-any.whl`. S01 đi kèm là bản sao nguyên ZIP a6 historical, không build lại hoặc đổi dependency.

1. Dùng runtime CPython đã pin `.runtime/python/bin/python3.13`; tạo venv mới ngoài source. Cài `packages/s02/requirements-dev.lock` offline bằng `.tools/uv`, wheelhouse `.tools/wheelhouse` và `dist`, `--require-hashes`. Cài hai wheels non-editable bằng đường dẫn explicit, `--no-index --no-deps`. Lệnh/exit/log đầy đủ ở `audit-venv`, `audit-locks`, `audit-install` `.command.json/.log`.
2. `build_isolated.py` copy đúng source/build inputs sang directory mới, dùng builder workspace; outputs ở audit-wheel và audit-rebuild. Provenance/hash từng input ở `audit-build-provenance.json`, `audit-rebuild-provenance.json`; compare payload/METADATA/WHEEL, không ép ZIP hashes.
3. Tạo venv baseline riêng: phase1 S02 0.1.0a3, P1 0.2.0a3 và S01 a6 từ locks. `baseline_campaign.py` ghi từng command. Baseline copies tests ở `/tmp/dacn-p2-20261022/{p1,legacy}-workspace`; evidence snapshot trước sửa trong `before/` là nguồn tái tạo, không cần dùng lại venv cũ.
4. P2: `packages/s02/tools/run_p2_checks.py --report-dir <mới> --baseline-python <P1-venv/bin/python> --baseline-helpers <frozen-P1-tests> --legacy-python <phase1-venv/bin/python>`. Không resolve symlink executable ra ngoài venv. Runner process/cwd độc lập cho C và Python, không PYTHONPATH source. `--audit-only --audit-file <file nguyên bản>` cho từng oracle; file audit nằm ngoài test-helper directory để không double-load conftest.
5. Toàn S01: `tools/run_checks.py --package s01 --report-dir <mới>`. Các files audit gốc và replay được liệt kê/hashes ở oracle-inputs/replay-inputs; replay_runner chỉ instrument codec, không sửa graph/script.
6. `differential_l1.py <c|python> <output-mới.json>` trong venv legacy và candidate, cùng canonical-fixtures/l1-root.json. Corpus 413 outcomes; so toàn accepted/error/walk outputs, không chỉ counts.
7. `tools/collect_evidence.py --package all --wheel-dir <release-dir> --baseline-wheel s02=<P1-a3-wheel> --report-dir <mới>`. Collector gồm source, installed, wheel, METADATA/WHEEL/direct URL; `pip check` riêng.

Nguồn lệnh thực: mọi `*.command.json` ở đây, `commands.json` dưới từng checks directory, và `ADAPTER.json` (input hashes + diff). Các runner đặt PYTHONDONTWRITEBYTECODE=1, bỏ PYTHONPATH/PYTEST_ADDOPTS/PYTEST_PLUGINS, PYTEST_DISABLE_PLUGIN_AUTOLOAD=1. Backend chính được instrument qua conftest; process workers ghi encoder counts và PID/timing trong observations.

Các thao tác đọc/copy inventory và bootstrap development đầu tiên được thực hiện trực tiếp bằng tool trong phiên; không có wall-clock/command transcript riêng cho mọi lệnh `cat`/`cp`. Before inventory, git status/diff/HEAD, snapshot bytes và toàn release commands được lưu. Các output thất bại của harness/development giữ nguyên và không tính là release pass. Không có kiểm mất điện phần cứng, disk-full thật, performance scale, migration production, auth người review hoặc LLM quality.
