# Phản hồi S02-2A-P1-04 — dacn-s02 0.2.0a3

Ngày 22/10/2026. **Đã sửa, chờ audit lại.** Auditor đã đóng 01/02/03 trên a2 trong phạm vi lỗi đã báo; chưa đóng 04, P1 chưa nghiệm thu. Căn cứ [audit a2](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-2a-p1-0.2.0a2-2026-10-22-214859/AUDIT_REPORT.md), contract mapping §5.1 và addendum A2 §3.2/§3.6. Đây là sửa thực thi điều kiện đã chốt, không đổi contract/profile/rules IDs hoặc schema.

## Nguyên nhân và cách sửa

`validation.index_model` tách Part khỏi mapping row. Khi dùng Part JSON rời làm giá trị so sánh, hoán đổi source_ref giữa rows không làm thay đổi Part hoặc tập refs tổng; code nhầm đó là cùng quan hệ mapping. CARRY và target REPLACEMENT đều dùng phép so thiếu ngữ cảnh ấy.

Giữ **nguyên byte** `validation.py:index_model`, toàn closure/reverse-impact và các helper legacy. Chỉ bổ sung comparison values trong module E1 [resolution.py:139](/Users/macbookpro/Documents/DACN_implementation/packages/s02/src/dacn_s02/resolution.py:139), [dòng 146](/Users/macbookpro/Documents/DACN_implementation/packages/s02/src/dacn_s02/resolution.py:146): mỗi Part đi cùng payload của nó và mapping context gồm row ID, source_ref (snapshot + pointer), assessment, issue_ids và tập Part IDs thuộc row. Do đó chuyển Part giữa rows, đổi nguồn, đổi membership/assessment/identity không còn bị che bằng cùng tập refs tổng.

Các danh sách ID mang nghĩa tập của Part và mapping issue_ids được chuẩn hóa **trong phép so E1**, không sửa input. Thứ tự rows/Parts không tham gia identity. Không sắp xếp acceptance criteria trong source hoặc workflow sequence; không nối criterion theo text/index xuyên revisions. Các trường nguồn và nội dung còn lại được giữ nguyên kiểu/giá trị.

Áp dụng ở ba chỗ:

1. [_scope_proof:174](/Users/macbookpro/Documents/DACN_implementation/packages/s02/src/dacn_s02/resolution.py:174), đặc biệt dòng 190: pair vẫn kiểm payload Part; structural `unchanged` còn phải có cùng mapping context. Pair nói payload unchanged không tự chứng minh quan hệ nguồn unchanged. Vì thế controls review/hold với payload còn nguyên vẫn hợp lệ; structural release không được dựa vào nhãn pair ấy.
2. [Tập changed/impact:196](/Users/macbookpro/Documents/DACN_implementation/packages/s02/src/dacn_s02/resolution.py:196): dùng cùng contextual identity để đưa thay đổi liên kết vào reverse impact. Closure vẫn mở mọi Part/action theo thuật toán đã chốt; thay đổi không cần nằm ngay trong seed ban đầu mới bị xét.
3. [Target footprint:351](/Users/macbookpro/Documents/DACN_implementation/packages/s02/src/dacn_s02/resolution.py:351): cùng comparison index cho từng Part trong affected/blocking footprint của target predecessor/successor, độc lập với proof replacement.

Không sửa record/task/Change bất biến, không tạo review và không triển khai persistence. Human review phải là evidence bên ngoài payload ghim đúng dependency graph và vẫn qua toàn bộ coverage checks; fixtures chỉ dùng synthetic bindings.

## Điều kiện trước và sau đã thực thi

Trên wheel a2, hai file audit mới có **8 pass/2 fail mỗi backend**, đúng hai DID NOT RAISE; hai graph phản ví dụ replay qua script gốc đều accepted. Kết quả mới ở `baseline-audit/` và `baseline-replay-*.log`.

Trên release a3, hai files mới đạt 10/10 mỗi backend; ba files audit a1 đạt 12/12 mỗi backend. Replay nguyên byte không import helpers: CARRY bị `carry_structural_proof`, REPLACEMENT bị `replacement_structural_continuation` trên cả C/Python. Exit 1 ở các replay release là **kỳ vọng reject**, không phải harness crash; summary kiểm đúng exception/invariant. Các controls unchanged, review mới, undetermined/incomplete giữ hold đều pass. Không đổi oracle để đạt kết quả.

39 regression mới trong [test_mapping_structural_identity.py](/Users/macbookpro/Documents/DACN_implementation/packages/s02/tests/test_mapping_structural_identity.py) bao gồm requirement và criterion nguồn riêng biệt; swap nguồn; reparent Part; row identity/assessment; reorder rows/Parts và ID lists; revision pin mới; review stale/fresh và hold; Part được tìm qua closure/shared Part/reverse impact; target affected/blocking được kiểm độc lập. Test whole-graph kiểm input không bị mutate. Các unit footprint tests kiểm riêng invariants, không được trình bày như graph đã hoàn tất whole-graph validation.

## Bảo toàn và giới hạn

[Diff](implementation.diff) so actual dirty state trước sửa, không chỉ Git HEAD. Năm file hiện hữu thay đổi: resolution, version ở pyproject/__init__, AGENTS và hướng dẫn P1; thêm một test file. [Inventory](protected-inventory.json), [oracle/helpers](oracle-preservation.json), [source–wheel–installed](package-evidence/manifest.json) và [rules hashes](rules-bundle.json) cho phép đối chiếu. Tất cả tests/helpers lịch sử và năm oracle audit nguyên byte; adapter runner chỉ định vị test helpers.

L1 schema và semantics baseline S02 **0.1.0a3** giữ nguyên; không nhầm với package P1 mới **0.2.0a3**. Schema E1/registry, DB1/repository, S01 a6, locks/dependencies, caches và artifacts lịch sử nằm trong inventory bảo toàn. Full regressions và differential được chạy mới, không lấy số cũ làm bằng chứng.

Comparison kiểm quan hệ đã biểu diễn; không chứng minh requirement→responsibility đúng nghiệp vụ hoặc mô hình không bỏ sót nghĩa vụ. Row identity/context thay đổi được xử lý bảo thủ, không tự suy nghĩa tương đương từ prose. Không xác thực có người thật review từ synthetic bindings. Corpus differential hữu hạn không chứng minh equivalence mọi graph. Không triển khai P2/P3, E1 persistence, DB2/migration, CAS/claims mới, 2C/live; không mở operational store, không sửa dataset, không gọi LLM/renderer. Xem [TEST_RESULTS](TEST_RESULTS.md) và [REPRODUCE](REPRODUCE.md).
