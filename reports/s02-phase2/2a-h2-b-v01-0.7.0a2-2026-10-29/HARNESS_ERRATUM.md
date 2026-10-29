# Erratum và phạm vi harness V01

Bản gốc và mọi lần thất bại giữ nguyên. Không chuyển failure thành pass; các bản mới chỉ ở ngoài checkout production/tests.

## Harness release đề xuất

- [Gốc nguyên byte](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-b-v01-0.7.0a2-2026-10-29/test_original.py) bằng repo test và audit unchanged oracle.
- [Đề xuất](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-b-v01-0.7.0a2-2026-10-29/test_release_boundaries_v02.py): [fixture diff](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-b-v01-0.7.0a2-2026-10-29/test_release_boundaries_v01.py.diff), [import diff](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-b-v01-0.7.0a2-2026-10-29/test_release_boundaries_v02.py.diff).
- [Worker](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-b-v01-0.7.0a2-2026-10-29/v01_worker_v2.py): [SQLite diff](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-b-v01-0.7.0a2-2026-10-29/v01_worker.py.diff), [helper path diff](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-b-v01-0.7.0a2-2026-10-29/v01_worker_v2.py.diff).
- [Launcher](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-b-v01-0.7.0a2-2026-10-29/v01_launch_v2.py) trích launch cũ, chỉ đổi tên worker. Timeout45s/process/backend/assert exit-counts giữ nguyên. Worker barrier20s/concurrency giữ nguyên. Import path chỉ thêm copied test helpers, không production source.
- [Assert AST/hash check](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-b-v01-0.7.0a2-2026-10-29/assertion-preservation.json):10 assertions gốc không đổi. Cache chỉ áp dụng connection seal khi test spec yêu cầu; không product config/flag, không đổi journal_mode/synchronous. Pragmas được ghi thực tế và hot header d9d505f920a163d7 là bắt buộc.

Đề xuất tách storage crash khỏi tải payload lớn, không chứng minh cache_size là nguyên nhân duy nhất tạo journal. Body nhỏ vẫn phải chứng minh hot journal/controls; không coi process kill đơn thuần là hot recovery.

## Các lỗi/thử nghiệm mới được giữ

| Lượt | Kết quả mỗi backend | Phân loại |
| --- | --- | --- |
| hot-wall-deadlines | 2fail | Sau assertions DB/retry, json.dumps không serialize Decimal canonical |
| final-controls (wall v2 + oracle + no-write) | 3pass,2fail | Exact codec từ chối float timing khi ghi evidence; assertions đã qua nhưng toàn test vẫn fail |
| wall-deadlines-v3 | 2pass | Report writer dùng simplejson/use_decimal hỗ trợ Decimal canonical và float đo thời gian |
| corrected-harness v1 | 4fail | Worker mới thiếu import path process_worker; child workloads chưa chạy |
| corrected-harness-v2 | 3pass,1fail | Ba ca release đạt; giả thuyết cache_spill=OFF⇒không hot header bị phản bác trên runtime này |

Diff writer [v2](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-b-v01-0.7.0a2-2026-10-29/test_hot_deadline_v2.py.diff)/[v3](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-b-v01-0.7.0a2-2026-10-29/test_hot_deadline_v3.py.diff) giữ assertions/caps. Serializer chỉ ghi report, không làm input production. Lỗi writer là lỗi harness **mới của lượt V01**, không phải accessor/setup P2/H2-A lịch sử và không giải thích full failure Python auditor.

Negative cache_spill=OFF giữ nguyên DB/JUnit/assertion fail: giả thuyết đó không hợp lệ làm oracle absence-of-journal. Nguyên nhân SQLite cụ thể không nghiên cứu thêm trong phạm vi này. [Control chết trước ghi](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-b-v01-0.7.0a2-2026-10-29/test_before_write_control.py) là kiểm riêng với trigger after_begin; không đổi file fail thành pass. Nó chứng minh fixture âm thật không hot, so với ca dương before_commit có hot. Read-only/wrong-store negatives trong ca dương vẫn là assertions gốc.
