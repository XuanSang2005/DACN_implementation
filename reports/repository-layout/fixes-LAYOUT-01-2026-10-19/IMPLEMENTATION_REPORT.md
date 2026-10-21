# LAYOUT-01 — sửa wrappers cố định package

**Đã sửa và kiểm thử, chờ audit lại.** Chỉ sửa tooling và hướng dẫn; không thay production source, schema, locks, package versions, S02-05 hoặc triển khai Đợt 2. S01 vẫn `0.1.0a6`, S02 `0.1.0a2`. Layout được giữ theo [kết luận audit](</Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/repository-layout-2026-10-19/AUDIT_REPORT.md>); việc đóng LAYOUT-01 cần audit bản sửa này.

## Nguyên nhân và thay đổi

Wrapper cũ chỉ chặn token `--package` rồi chèn selector vào đầu argv. Parser dùng giá trị cuối và cho phép viết tắt, nên `--package=s02` hoặc `--pack=s02` có thể đổi package của wrapper S01.

- Bốn wrappers `packages/{s01,s02}/tools/{run_checks,collect_evidence}.py` gọi `main(fixed_package=...)` qua tham số nội bộ; không chèn selector vào argv nữa.
- Hai workspace tools nhận `fixed_package` tùy chọn. Khi được cố định, parser **không đăng ký option package**. Khi gọi trực tiếp từ root tool, `--package {s01,s02,all}` vẫn bắt buộc. Cả hai parser dùng `allow_abbrev=False`; option phải viết đầy đủ.
- Selector không hợp lệ bị argparse từ chối với exit **2**, trước tạo thư mục report hoặc chạy suite/import package để thu bằng chứng. Exit trước đây của riêng `--package` tách token là 1; đổi sang lỗi cú pháp thống nhất 2. Lệnh chuẩn trong README giữ nguyên.
- Thêm `tools/tests/test_package_wrappers.py`; cập nhật root README và mục lục reports. Không sửa AGENTS, tests sản phẩm hoặc báo cáo cũ. [Diff](changes.patch) giữ tám file chỉnh nội dung; `originals/` giữ bản trước để đối chiếu, không phải tooling hiện hành.

## Kiểm chứng thực chạy

[Kết quả máy đọc](results.json), [lệnh tooling](tooling-commands.json) và [log hồi quy](regression.log) ghi kết quả của lượt sửa. Bộ unittest stdlib có **339 tests passed**: 336 tổ hợp selector (bốn wrappers × bảy tên/prefix × ba giá trị × hai cú pháp × hai vị trí), cộng ba nhóm kiểm help và parser workspace. Các tổ hợp kiểm bằng subprocess thật, exit 2, thông báo unrecognized arguments, stdout rỗng và **không có file/thư mục output**. Ba nhóm bổ sung có subtests cho cả hai loại tool/package. Không mock parser hoặc đổi expectations để đạt.

Hai collector package chạy thật, manifest lần lượt chỉ chứa S01 hoặc S02. Collector workspace với `--package all` vẫn chứa cả hai. [Manifest S01](s01-package-verification/manifest.json), [S02](s02-package-verification/manifest.json), [workspace](workspace-package-verification/manifest.json) đối chiếu đủ **16 + 14 files** source = installed = wheel rebuild layout = historical wheel; kiểm phiên bản, non-editable import/site-packages, direct URL/hash và METADATA/WHEEL. `pip check` đạt.

Hai runner package được chạy thật, process/backend và cwd tạm riêng, không truyền selector từ CLI:

| Wrapper / suite | Backend C | Backend Python | Exit |
| --- | ---: | ---: | ---: |
| S01 | 986 passed | 986 passed | 0 |
| S02 | 189 passed | 189 passed | 0 |

Không errors/skipped/failures. [Lệnh S01](s01-runner-command.json), [S02](s02-runner-command.json) lưu argv/cwd/exit; `s01-checks/` và `s02-checks/` giữ logs/JUnit/commands/observations và bằng chứng synthetic race/kill của suite. Instrumentation vẫn xác nhận C/Python đúng backend. Lệnh runner S01 chỉ tạo hai kết quả S01; S02 chỉ tạo hai kết quả S02.

Môi trường **dùng lại venv kiểm layout trước**, không gọi là venv mới của lượt này. Interpreter CPython 3.13.16, SQLite 3.53.1; versions/dependencies/imports đầy đủ trong manifests mới. Tests từ wheels non-editable đã cài, cwd ngoài checkout, không production source trên PYTHONPATH. Không build lại hoặc cài/nâng dependency vì product bytes và metadata không đổi. Dữ liệu kiểm là synthetic; không dùng dataset nghiệp vụ.

## Bảo toàn, tái lập và giới hạn

[Baseline đầu lượt](baseline.json) chụp 7.547 file/symlink entries workspace và 3.826 file thuộc audit layout bên ngoài. [Đối chiếu](preservation.json): tám file sửa được kê khai, **7.539 entries còn lại và 3.826 file audit giữ hash**, không thay đổi ngoài dự kiến. Source/schema/locks/wheels và toàn bộ evidence lịch sử trong inventory giữ nguyên. Đây là phạm vi inventory, không tuyên bố kiểm toàn dataset hoặc filesystem. [Manifest bàn giao](artifact-manifest.json) ghi hashes của artifacts mới và files tooling/hướng dẫn được sửa/thêm.

Tái lập bằng interpreter đã cài wheels/locks như README, tại cwd ngoài checkout, dùng đường dẫn tuyệt đối và các thư mục kết quả **chưa tồn tại**:

```sh
"$DACN_PY" -B -m unittest discover -s "$DACN_ROOT/tools/tests" -p test_package_wrappers.py -v
"$DACN_PY" -B "$DACN_ROOT/packages/s01/tools/run_checks.py" --report-dir "$DACN_RESULTS/s01-checks"
"$DACN_PY" -B "$DACN_ROOT/packages/s02/tools/run_checks.py" --report-dir "$DACN_RESULTS/s02-checks"
"$DACN_PY" -B "$DACN_ROOT/packages/s01/tools/collect_evidence.py" --wheel-dir "$DACN_WHEELS" --report-dir "$DACN_RESULTS/s01-manifest"
"$DACN_PY" -B "$DACN_ROOT/packages/s02/tools/collect_evidence.py" --wheel-dir "$DACN_WHEELS" --report-dir "$DACN_RESULTS/s02-manifest"
"$DACN_PY" -B "$DACN_ROOT/tools/collect_evidence.py" --package all --wheel-dir "$DACN_WHEELS" --report-dir "$DACN_RESULTS/workspace-manifest"
```

`DACN_WHEELS` phải trỏ bộ wheels đang được cài (collector kiểm direct URL/hash); lượt này dùng bộ rebuild layout trước, đường dẫn chính xác có trong commands. Không ghi đè kết quả của lượt bàn giao. Test regression dùng vùng tạm ngoài checkout, không cần dependencies ngoài stdlib.

Chưa chạy lại audit S02 bên ngoài, CLI/guard smoke hoặc build trong lượt sửa hẹp này; các kết quả ấy ở audit layout là **kết quả trước bản sửa**, không trình bày như vừa đo lại. S02-05 vẫn còn mở theo audit: không thay source hay chạy lại để tuyên bố đóng finding. Không kiểm LLM/renderer/ngữ nghĩa hoặc triển khai S02 Đợt 2. Agent audit cần kiểm selector không thể đổi package ở bốn wrappers, parser workspace vẫn cho chọn package bằng tên option đầy đủ và đối chiếu logs/manifests mới.
