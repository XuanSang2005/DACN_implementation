# Báo riêng harness — không trộn với findings implementation

## Timeout ở audit a1

[Audit a1](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-2a-h1-0.5.0a1-2026-10-24/AUDIT_REPORT.md) ghi full S02 Python **750 pass + 1 timeout** tại test_migration_holds_guard_against_concurrent_init[reservation_durable-cli]: worker chờ parent 30 giây, “Missing parent release”. Auditor chạy riêng nguyên case/nguyên timeout ba lần pass; đó là **kết quả lịch sử của auditor**, không phải lượt chạy mới này.

Đợt sửa không đổi worker, thời hạn 30 giây, barriers, production migration/reservation, assertions hoặc locks. H1 compute budget cũng là 30 giây nhưng là cơ chế khác, không dùng để giải thích worker timeout. Kết quả full mới và mọi focused retry nếu có nằm trong [TEST_RESULTS](TEST_RESULTS.md) / FINAL_RESULTS. Không suy retry pass thành full suite pass, không tăng timeout để che lỗi.

**Lượt mới này:** full S02 C/Python đều **769 pass**, ca reservation_durable-cli pass nguyên timeout ở cả hai backend. Không tái hiện timeout, không chạy focused retry để làm sạch số. Chưa có kết luận root cause/timing của failure lịch sử; một lượt pass không được dùng để tự đóng vấn đề harness.

## Logger của oracle v3 nguyên byte

SHA-256 v3: **9b7d8379a6551e1bc4c868cf46e98b1de47940010346b83ce7a9fccb766e3f9e**. Repository.heads() trả tuple; evidence() tại dòng15 gọi exact encode cho head_before/head_after mà không chuyển tuple thành JSON array. Codec S01 a6 vốn từ chối tuple; không được sửa codec/DB2 API đã pin để làm logger pass.

Baseline a1: v3 **4 pass/6 fail/backend**, trong đó ca test_over_ref_limit_keeps_raw_and_rejects_without_publication fail ở logger, trước assertions. Fixed a2: **9 pass/1 logger fail/backend**. Các lỗi parser/hold đã hết trong v3, nhưng không tuyên bố nguyên oracle đạt 10/10.

Phản chứng tối thiểu: gọi **chính evidence() nguyên bản** với tuple từ heads() trên synthetic store; cả a1/a2 đều PROCESSING_FAILED, Unsupported internal JSON type: tuple. Không monkeypatch production hoặc logger; không sửa/skip/xfail file. [Baseline proof](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h1-fixes-0.5.0a2-2026-10-24/original-logger-proof-baseline.json), [fixed proof](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h1-fixes-0.5.0a2-2026-10-24/original-logger-proof-candidate.json), [script](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h1-fixes-0.5.0a2-2026-10-24/check_original_logger.py), [v3 fixed logs/JUnit](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h1-fixes-0.5.0a2-2026-10-24/fixed-oracle-v3/checks/).

Regression mới test_ref_limit_end_to_end_raw_head_and_reopen có assertions raw/rejection/no-publication/head/reopen và positive 50.000; logger riêng đổi head tuple thành list khi in. Baseline a1 mới chạy 1 pass/1 fail thực ở status completed thay vì rejected; fixed full lane kiểm lại cả hai. Đây là regression bổ sung, **không thay thế hoặc âm thầm sửa oracle v3**. Cần auditor review logger và xuất phiên bản oracle mới riêng nếu yêu cầu v3-case đi qua logger tới assertions.

## Oracle P2 lịch sử

Ba files P2 gốc giữ expected16 pass/1 fail/backend do heads() sau corruption ngoài pytest.raises, đã được [audit P2 a2](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-2a-p2-0.3.0a2-2026-10-23-015238/AUDIT_REPORT.md) xác nhận. Không làm yếu checked read; v2/boundaries chạy riêng. Báo số thực trong TEST_RESULTS, không gộp thành zero failures.

## Setup/evidence development

Collector lần đầu so direct_url hash của wheel rebuild đã cài với ZIP initial build khác timestamp nên từ chối đúng, dù toàn payload bằng nhau. Không nới collector: final/wheels là **byte copy** đúng ZIP đã cài từ candidate-environment/build/wheels; final collector kiểm SHA/direct_url, source/wheel/installed và METADATA/WHEEL đạt. [Selection proof](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h1-fixes-0.5.0a2-2026-10-24/final-wheel-selection.json), [final collector](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h1-fixes-0.5.0a2-2026-10-24/package-evidence-final/manifest.json). Initial release/rebuild outputs và failure log được giữ riêng.

Inventory worker đầu được dừng vì gọi git ls-files lặp cho từng file; chụp lại một lượt trước mọi source edit. Đây không phải application crash/timeout. Các development/setup logs giữ nguyên, không tính vào regression pass/fail hoặc đổi evidence lịch sử.
