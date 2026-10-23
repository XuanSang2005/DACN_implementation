# DACN implementation — S01 và S02

Trạng thái hiện hành 23/10/2026: P1 `0.2.0a3` và P2 `0.3.0a2` đã nghiệm thu kỹ thuật local; findings P1 01–04 và P2 01/02 đã đóng theo [audit P2 a2](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-2a-p2-0.3.0a2-2026-10-23-015238/AUDIT_REPORT.md). Người dùng giao riêng [P3 migration local](docs/S02_2A_P3_IMPLEMENTATION.md), `0.4.0a2`: **Đã sửa, chờ audit lại**. [Bàn giao mới](reports/s02-phase2/2a-p3-fix01-0.4.0a2-2026-10-23/START_HERE.md). Chỉ thử trên kho synthetic/test; không migration operational, 2B/2C hoặc live. Bàn giao cũ giữ nguyên trạng thái lịch sử.

Code hiện hành nằm trong [`packages/s01/`](packages/s01/) và [`packages/s02/`](packages/s02/). Root là workspace, không phải package S01; không chạy `pip install .` ở root. Namespace, distribution và CLI không đổi.

| Giai đoạn | Baseline / trạng thái | Căn cứ |
| --- | --- | --- |
| S01 | `dacn-s01 0.1.0a6`, đã nghiệm thu kỹ thuật CLI local; input 1.0.0, output draft.2 | [S01_ACCEPTANCE.json](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s01-phase4-0.1.0a6/S01_ACCEPTANCE.json) |
| S02 | `dacn-s02 0.1.0a3`, contract draft.3; **đã sửa S02-05, chờ audit**, chưa nghiệm thu Đợt 1. S02-01–04 đóng trên a2 | [Bàn giao a3](reports/s02-phase1/fixes-0.1.0a3/IMPLEMENTATION_REPORT.md), [audit a2](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-phase1-0.1.0a2-2026-10-19/AUDIT_REPORT.md) |

[Audit layout](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/repository-layout-2026-10-19/AUDIT_REPORT.md) xác nhận đạt mục tiêu, kèm LAYOUT-01 ở wrappers. [Bản sửa wrappers](reports/repository-layout/fixes-LAYOUT-01-2026-10-19/IMPLEMENTATION_REPORT.md) được giữ và kiểm lại cùng S02 a3; cả hai finding **đã sửa, chờ audit**, chưa tự đóng. [Bàn giao layout gốc](reports/repository-layout/2026-10-19/IMPLEMENTATION_REPORT.md) giữ nguyên. S01 a6/source/schema/locks và lịch sử không đổi; chưa triển khai S02 Đợt 2.

## Tìm code và tài liệu

| Nội dung | Vị trí |
| --- | --- |
| Source, schema resources, tests, cấu hình S01 | [`packages/s01/`](packages/s01/) |
| Source, schema resources, tests, cấu hình S02 | [`packages/s02/`](packages/s02/) |
| Build/check/collect toàn workspace | [`tools/`](tools/) |
| Entry points cho từng package | `packages/<stage>/tools/run_checks.py`, `collect_evidence.py` |
| Công cụ bàn giao cũ, không phải lệnh hiện hành | [`S01 legacy`](packages/s01/tools/legacy/README.md), [`S02 legacy`](packages/s02/tools/legacy/README.md) |
| Contract/examples/hướng dẫn | [`docs/README.md`](docs/README.md), [`S01`](docs/s01/README.md), [`S02`](docs/s02/README.md) |
| Báo cáo và cách tra bằng chứng | [`reports/README.md`](reports/README.md) |

Không có package common, orchestration framework hoặc implementation S03–S07. Dataset là tài nguyên bên ngoài chỉ đọc. **DB, receipts, exports và operational state đặt ngoài checkout**, tách kho S01/S02; không dùng thư mục reports làm state vận hành. DB trong reports là bằng chứng synthetic đã lưu, không mở để chạy tiếp.

## Chuẩn bị môi trường sạch từ locks

Các lệnh sau chạy từ root workspace, trên baseline macOS arm64 / CPython 3.13.16 / SQLite 3.53.1. Runtime và wheelhouse đã có, không tải hoặc nâng dependency. Cần terminal khác khi đổi interpreter; không dựa vào kích hoạt venv ngầm.

```sh
DACN_ROOT="$PWD"
DACN_ENV_ROOT=$(mktemp -d -t dacn-environment)
DACN_PY="$DACN_ENV_ROOT/venv/bin/python"
"$DACN_ROOT/.runtime/python/bin/python3.13" -B -m venv --without-pip "$DACN_ENV_ROOT/venv"
"$DACN_ROOT/.tools/uv" pip install --python "$DACN_PY" \
  --no-index --find-links "$DACN_ROOT/.tools/wheelhouse" \
  --find-links "$DACN_ROOT/dist" --require-hashes \
  -r "$DACN_ROOT/packages/s02/requirements-dev.lock"
"$DACN_PY" -B -m pip install --no-index --no-deps \
  "$DACN_ROOT/reports/s02-phase1/fixes-0.1.0a3/builds/dacn_s02-0.1.0a3-py3-none-any.whl"
"$DACN_PY" -B -m pip check
```

S02 dev lock chứa runtime/test/build dependencies và S01 a6 với **hash wheel lịch sử**; `--find-links dist` là cần thiết. Chỉ dùng S01: thay lock bằng `packages/s01/requirements-dev.lock`, bỏ bước cài S02 và cài `dist/dacn_s01-0.1.0a6-py3-none-any.whl` bằng `--no-deps`. Với môi trường chỉ dùng CLI, dùng `requirements.lock` thay dev lock; pip/build/test tools có thể không có trong runtime-only env.

[`tools/requirements-tools.lock`](tools/requirements-tools.lock) là **bản authoritative duy nhất** pin bootstrap uv 0.13.0; không phải dependency nghiệp vụ của S01/S02. `.tools/uv` đã có, không cần cài uv vào mỗi venv. Nếu cần bootstrap lại tool, dùng pip đã có để cài offline lock này từ `.tools/wheelhouse` vào một môi trường tools mới. Không thay manager hoặc tự resolve/nâng versions. Locks S01 và S02 có hash sets khác nhau theo cách lập lock trước đây; cả hai giữ nguyên bytes.

Không di chuyển venv. Root [`.venv/`](.venv/) và [`s02/.venv/`](s02/.venv/) vẫn là môi trường legacy; runtime, wheelhouse và wheels lịch sử giữ nguyên. Hướng dẫn hiện hành ưu tiên môi trường sạch ở ngoài checkout.

## Build hai package

```sh
DACN_RESULTS=$(mktemp -d -t dacn-results)
"$DACN_PY" -B "$DACN_ROOT/tools/build_packages.py" \
  --package all --output-dir "$DACN_RESULTS/builds"
```

Có thể chọn `--package s01` hoặc `s02`. Build offline bằng setuptools/wheel đã pin; output directory phải chưa tồn tại. Không ghi vào `dist/` hay `s02/dist/` lịch sử. Phiên bản hiện tại a6/a3; hash ZIP rebuild có thể khác do metadata archive. S01 phải giữ payload/METADATA/WHEEL baseline. S02 a3 có diff được giải thích với a2, không yêu cầu payload hai phiên bản bằng nhau.

Trước thay wheel S01 đã cài từ hash lock bằng bản rebuild, kiểm payload (lệnh read-only, không imports production source):

```sh
"$DACN_PY" -B - "$DACN_ROOT" "$DACN_RESULTS/builds" <<'PY'
from pathlib import Path
from zipfile import ZipFile
import sys
root, builds = map(Path, sys.argv[1:])
for ns, version, old_dir in [('dacn_s01','0.1.0a6',root/'dist')]:
    name = f'{ns}-{version}-py3-none-any.whl'
    def payload(path):
        with ZipFile(path) as z:
            return {n:z.read(n) for n in z.namelist() if n.startswith(ns+'/') or n.endswith(('/METADATA','/WHEEL'))}
    assert payload(builds/name) == payload(old_dir/name), ns
print('Payloads equal; ZIP hash equality not required')
PY
"$DACN_PY" -B -m pip install --no-index --no-deps --force-reinstall \
  "$DACN_RESULTS/builds/dacn_s01-0.1.0a6-py3-none-any.whl" \
  "$DACN_RESULTS/builds/dacn_s02-0.1.0a3-py3-none-any.whl"
"$DACN_PY" -B -m pip check
"$DACN_PY" -B "$DACN_ROOT/tools/collect_evidence.py" --package all \
  --baseline-wheel "s02=$DACN_ROOT/s02/dist/dacn_s02-0.1.0a2-py3-none-any.whl" \
  --wheel-dir "$DACN_RESULTS/builds" --report-dir "$DACN_RESULTS/package-verification"
```

Collector đối chiếu đầy đủ inventory/hash source → installed → wheel cùng version, kiểm site-packages, non-editable direct URL/hash và METADATA/WHEEL. Baseline cùng version phải bằng nhau; baseline khác version được ghi diff riêng (a2 → a3). Với a3, truyền `--baseline-wheel s02=<wheel a2>` cả khi gọi collector wrapper S02. Không có baseline thì báo lỗi, không bỏ qua so sánh. Việc thay S01 bằng ZIP rebuild được ghi riêng, không tuyên bố ZIP mới khớp hash trong lock; không sửa lock để hợp thức hóa rebuild.

## Chạy CLI và kiểm thử

S01: [`python -m dacn_s01`](docs/s01/README.md) có init/submit/lookup. S02: [`python -m dacn_s02`](docs/s02/README.md) mới có init/start intake/lookup; không có lệnh chạy LLM hay toàn flow S02.

```sh
"$DACN_PY" -B "$DACN_ROOT/packages/s01/tools/run_checks.py" \
  --report-dir "$DACN_RESULTS/s01-checks"
"$DACN_PY" -B "$DACN_ROOT/packages/s02/tools/run_checks.py" \
  --report-dir "$DACN_RESULTS/s02-checks"
# Hoặc một entry point cho cả workspace, mỗi suite vẫn là process riêng:
"$DACN_PY" -B "$DACN_ROOT/tools/run_checks.py" --package all \
  --report-dir "$DACN_RESULTS/workspace-checks"
```

Chọn cách chạy phù hợp, không cần lặp cả ba lệnh. Runner chạy C/Python và đo factory thực; cwd test ở ngoài checkout, không đưa production src vào PYTHONPATH. Không gom tests S01/S02 trong một pytest process vì hai conftest cùng đăng ký `--encoder-backend`. Mỗi thư mục báo cáo phải mới; không tự ghi đè lần trước.

Wrappers runner/collector trong `packages/<stage>/tools/` cố định package: không nhận `--package`, dạng `--package=...` hoặc viết tắt. Chọn package qua tooling ở root với tên option đầy đủ; parser runner/collector không chấp nhận viết tắt option. Kiểm hồi quy ranh giới này: `python -B -m unittest discover -s tools/tests -p test_package_wrappers.py -v` (stdlib, không chạy suite sản phẩm).

Audit ngoài: dùng `packages/s02/tools/run_checks.py --audit-only --audit-file /path/to/test_independent_audit.py --audit-file /path/to/test_followup_boundaries.py --report-dir <mới>`. Adapter chỉ thêm helpers S02 mới vào sys.path; file/assertions audit giữ nguyên và được kiểm hash trước/sau. Trên a2, suite S02-05 có **2 passed + 2 failed/backend**; yêu cầu bản sửa a3 là **4 passed/backend** nhờ từ chối đúng dữ liệu sai. Kết quả thực của a3 ở [báo cáo kiểm thử](reports/s02-phase1/fixes-0.1.0a3/TEST_RESULTS.md); không bỏ tests, skip/xfail hay đổi kỳ vọng để làm xanh.

[`tools/check_layout.py`](tools/check_layout.py) kiểm CLI smoke, resources/examples, guard workspace/package, links hướng dẫn và từ chối overwrite reports: chạy với `--report-dir <mới>`. Bằng chứng layout đã chạy tại [báo cáo mới](reports/repository-layout/2026-10-19/IMPLEMENTATION_REPORT.md); không chạy lại vào thư mục đó. Các lệnh README là hướng dẫn tái lập, logs mới là bằng chứng thực chạy.
