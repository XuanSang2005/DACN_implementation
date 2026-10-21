# Kết quả kiểm chứng layout thực chạy

Môi trường sạch, wheels non-editable từ layout mới; tests chạy ngoài checkout. Dữ liệu test/smoke là synthetic.

| Suite | Passed | Failed | Errors / skipped | Exit | Phân loại |
| --- | ---: | ---: | --- | ---: | --- |
| [s01-c](suites/s01-c.log) | 986 | 0 | 0 / 0 | 0 | Đạt |
| [s01-python](suites/s01-python.log) | 986 | 0 | 0 / 0 | 0 | Đạt |
| [s02-c](suites/s02-c.log) | 189 | 0 | 0 / 0 | 0 | Đạt |
| [s02-python](suites/s02-python.log) | 189 | 0 | 0 / 0 | 0 | Đạt |
| [audit-1-c](independent-audits/audit-1-c.log) | 7 | 0 | 0 / 0 | 0 | Đạt |
| [audit-1-python](independent-audits/audit-1-python.log) | 7 | 0 | 0 / 0 | 0 | Đạt |
| [audit-2-c](independent-audits/audit-2-c.log) | 2 | 2 | 0 / 0 | 1 | S02-05 |
| [audit-2-python](independent-audits/audit-2-python.log) | 2 | 2 | 0 / 0 | 1 | S02-05 |

Audit-2 failures là hai assertions config mismatch **đã biết S02-05**, không phải lỗi layout. JUnit và commands giữ failed/exit 1; không xfail/skip, không sửa assertions. Không phát hiện regression mới trong các kiểm đã chạy.

Instrumentation process chính:

- s01-c: `Observed real encoder factory calls: {'c': 6597, 'python': 0}; selected=c`.
- s01-python: `Observed real encoder factory calls: {'c': 0, 'python': 6597}; selected=python`.
- s02-c: `S02_ENCODERS selected=c calls={'c': 71681, 'python': 0}`.
- s02-python: `S02_ENCODERS selected=python calls={'c': 0, 'python': 71681}`.

Worker observations nằm riêng trong [observations](suites/observations.json), không gộp ngầm vào counts process chính. S02 có 18 observations race/kill (5 races + 4 kill points trên mỗi backend), DB mới lưu riêng trong `suites/process-artifacts/`. S01 vẫn chạy mọi lịch/lock/kill/receipt/export của 986 tests.

CLI/guard/schema/docs: [18 lệnh thực](layout-checks/checks.json), gồm 7 CLI smoke S01→S02, 6 guards, 1 materializer check và 4 ca từ chối overwrite. 15 JSON examples parse được qua codec chính xác; 33 S02 Record minh họa qua shape, không tuyên bố toàn graph là gói nghiệp vụ đã xác nhận. 85 links hướng dẫn resolve được.

Package payload: đủ 16 S01 + 14 S02 files, inventory/hash bằng nhau ở source, wheel rebuild, installed và wheel lịch sử; METADATA/WHEEL cũng bằng nhau. [Manifest](package-verification/manifest.json) giữ versions/import paths/dependencies/direct URL non-editable. [Preservation](preservation.json) giữ trước/sau từng file, không dùng số lượng tests thay chứng cứ bảo toàn.

Phần chưa làm: sửa S02-05, S02 Đợt 2, LLM/renderer, full clarification/review, S03, dataset semantic evaluation và power-loss/disk-full.
