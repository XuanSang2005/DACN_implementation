# Tái lập H2-C — offline, installed wheel, output mới

Evidence root: `/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-c-0.8.0a1-2026-10-29` (gọi là `$EVIDENCE` bên dưới). Đây là provenance local; thay các đường dẫn bằng vị trí artifact đã kiểm hash trên máy tái lập.

1. Đọc [START_HERE](START_HERE.md), seal/manifest và diff đúng baseline `ecc51bc`. Không dùng các thư mục kiểm đã có làm đích.
2. Dùng `reproduce_environment.py` trong evidence root, bản copy nguyên byte từ driver H2-B a2. Truyền `--checkout <checkout> --output <mới ngoài checkout> --expected-wheel <H2-B a2 wheel>`. Có thể thêm `--bundle <bundle đã pin>`. Driver kiểm bundle inventory trước khi dùng runtime/wheelhouse, tạo ba venv mới từ locks, build hai source copies, chứng minh toàn ZIP entries S01 bằng a6 trước cài lại rebuild cùng version và S02 hai builds bằng payload. Không resolve online hoặc cài editable.
3. Baseline diff là H2-B `0.7.0a2`, wheel SHA `b5fcdba097c7fec74d87cd5a548c550764fdc05827301944bfa9bcbff307fb76`. Không ép ZIP a1 bằng a2 và không thay hash baseline. Root `tools/bootstrap.py` vẫn P3 accepted-only.
4. Chạy runner [H2-C](../../../packages/s02/tools/run_h2_c_checks.py) với Python candidate, `--environment <environment.json> --scope focused --report-dir <mới>`. Có `--group stress|merge|fixed_point` cho kiểm chọn lọc. `--scope full` luôn lấy toàn suite, không nhận group con. C rồi Python tuần tự, giữ bốn workers bên trong concurrency tests.
5. `release_checks.py` trong evidence root ghi các commands/logs; chạy full S02 qua E1 adapter, S01, wrappers/layout, original P1/P2/P3/H1/H2-A/H2-B và L1 differential. Driver có paths provenance; cập nhật riêng bản copy/đích output khi tái lập. Script không retry và không đổi failures thành pass. Xem `final/COMMANDS.json` và `final/JUNIT_SUMMARY.json` để đánh giá từng gate, bao gồm original harness failures đã biết.
6. Cài đúng delivery ZIP từ `final/wheels`, rồi collector dùng chính wheel-dir đó để đối chiếu source/wheel/installed/METADATA/WHEEL/direct URL. `environment-v1/build/wheels` có cùng payload nhưng không mặc định là ZIP identity bàn giao nếu sau này rebuild ở máy khác.

Runner mới giữ toàn test workspace, argv/cwd/env/exit/log/JUnit và basetemp/DB/journals sau failure. Không chạy lại pytest vào cùng basetemp vì pytest có thể xóa nội dung cũ. `process-artifacts` lưu specs/PID/encoder counts/stdout/stderr/phase timings của workers. Các command đời cũ đã finalized chỉ replay outcome cũ; current_head là quan sát tại thời điểm đọc và có thể đã thay đổi.

`failed-race-readback/READBACK.json` là kiểm trực tiếp SQLite read-only trên bản sao những DB của lượt thử lỗi, không phải một lần test pass thay thế. `inspect_failed_races.py` giữ hash DB nguồn. Không dùng những DB này làm operational state. Không sửa, bỏ hoặc chạy đè logs/JUnit lỗi từ `focused-v1`, `focused-v2`.

Mọi fixtures/approvals/analysis là synthetic software controls. Chạy pass không thay audit độc lập, nghiệm thu người dùng hoặc chứng minh chất lượng nghiệp vụ/LLM/renderer. Full lịch sử H2-B vẫn C959/959, Python958/959.
