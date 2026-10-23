# Phản hồi audit draft.2 — S02 Đợt 2 proposal draft.3

**Trạng thái: proposed — đã phản hồi audit, chưa audit lại/chưa được duyệt implementation.**

Ngày 21/10/2026; plan `s02-phase2-plan/0.1.0-draft.3`, addendum `s02-phase2-amendment/0.1.0-draft.2`. Chỉ sửa A2-R1/R2 theo [audit độc lập draft.2](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-phase2-proposal-draft2-2026-10-21/AUDIT_REPORT.md). S02-P2-01 đóng ở mức thiết kế; G2 đã rõ theo audit đó. Không tự đóng S02-P2-02 hoặc suy nghiệm thu kỹ thuật Đợt 1 thành quyền implement Đợt 2.

## Đối chiếu hai điểm cần sửa

| Finding | Quyết định đề xuất | Vị trí / ví dụ | Kiểm thử dự kiến sau khi được giao implementation — chưa chạy |
| --- | --- | --- | --- |
| A2-R1, P2 | Đổi method đề xuất structural_reuse → structural_check. Code có thể ghi undetermined khi nguồn đổi/thiếu proof. Điều kiện cùng snapshot, footprint không đổi và proof đầy đủ chỉ áp vào kết luận applicable. Human review chưa diễn ra không được ghi human_review | [Addendum §3.2–3.3](S02_PHASE2_CONTRACT_AMENDMENT_PROPOSAL.md); [JSON 06](examples/s02-phase2/06-resolved-issue-carry-forward.json) có năm graphs: đủ proof, nguồn đổi có/chưa review, cùng nguồn thiếu proof, pending rồi review cùng Model | Matrix method × assessment: positive undetermined không reviewer; reject applicable thiếu điều kiện, structural_check/not_applicable hoặc human_review giả; CARRY successor giữ root/count=1, không auto hoàn tất tasks |
| A2-R2, P1 | Thêm nhánh REPLACEMENT, field resolution_replacement và status resolution_replaced. Old key/evidence vẫn hiện hành; target key mới xử lý nghĩa vụ nguồn mới. Incomplete vẫn chặn; complete chỉ sau target resolved đúng Model/source, đủ coverage/tái phân tích và review quan hệ thay thế. Resolution cũ vẫn not_applicable | [Addendum §3.6](S02_PHASE2_CONTRACT_AMENDMENT_PROPOSAL.md); [JSON 07](examples/s02-phase2/07-resolution-replacement.json): Q3 pending → quyết định/Answer mới + S01 S4 → Q4-pending → Q5-replaced | Publication T3 + set-only review, source-only variant, giữ cả keys; Answer_old/app=1, Answer_new/app≤1; reject thiếu coverage/task evidence, sai lineage/key/current target, vòng, prose-only hoặc CAS stale. Reopen/kill/recovery không resend S01/app lại; source đổi về sau tái hold nếu target không đủ |

Giải pháp không nới application_pending_issue để nhận old revalidation Issue: Answer mới thuộc key mới, application vẫn kiểm pending/current/lineage/backlinks như a3. `supersedes_answer_id=null` khi khác key. Checkpoint sau application mới có thể vẫn chặn old key cho tới review; đây là trạng thái hợp lệ và có recovery riêng. Không tạo DIRECT root mới trên key cũ bằng cách xóa evidence, không coi metadata/ref hợp lệ là proof ngữ nghĩa.

## Phạm vi giữ nguyên

- Toàn mục 2 A1 trong addendum và toàn mục 7 G2/admission trong plan giữ nguyên bytes, được đối chiếu hash từng section với bản đầu lượt. JSON 01–05 chỉ đổi version markers (proposal và amendment khi có); nội dung A1/G2 và consent payload không đổi.
- Contract S02 draft.3, production code/tests/schema, S01 a6/S02 a3, dependencies/locks/DB/artifacts và audit/acceptance lịch sử không sửa. Bằng chứng draft.1 và draft.2 cùng báo cáo phản hồi draft.2 giữ nguyên bytes.
- G3/G4, provider/model/live budget và migration implementation không mở rộng trong lượt này. Profile tương lai phải version các fields/enum A2 mới; chưa tạo migration hay sửa kho.

## Danh sách file thay đổi

- [AGENTS.md](../AGENTS.md): chỉ cập nhật bullet trạng thái audit và phạm vi A2-R1/R2.
- [Plan](S02_PHASE2_IMPLEMENTATION_PLAN_PROPOSAL.md): draft.3, trạng thái audit, A2 lifecycle, kiểm thử dự kiến/dependencies phần liên quan, links bằng chứng mới.
- [Addendum](S02_PHASE2_CONTRACT_AMENDMENT_PROPOSAL.md): draft.2, matrix method/assessment, replacement schema/transitions/invariants/compatibility; A1 giữ nguyên.
- JSON [01](examples/s02-phase2/01-clinic-steps-1-4.json), [02](examples/s02-phase2/02-cancel-permission-and-new-actor.json), [03](examples/s02-phase2/03-consent-and-s01-recovery.json), [04](examples/s02-phase2/04-stale-and-dispatch-unknown.json), [05](examples/s02-phase2/05-unchanged-application.json): chỉ version markers.
- [JSON 06](examples/s02-phase2/06-resolved-issue-carry-forward.json): method mới, nullable replacement field, hai graphs/checkpoints bổ sung và ca âm R1.
- [JSON 07](examples/s02-phase2/07-resolution-replacement.json), báo cáo này và [STATIC_CHECKS_DRAFT3.json](examples/s02-phase2/STATIC_CHECKS_DRAFT3.json): mới.

## Bằng chứng và giới hạn

Baseline hashes được lấy trước chỉnh sửa. Manifest draft.3 ghi inventory trước/sau, file được phép đổi/file mới, kiểm bytes các sections A1/G2, version-only examples 01–05, JSON strict không duplicate keys, bindings/SourceRefs/projection refs, payload bytes/hash/consent, từng trạng thái được minh họa và local links. Dùng Python stdlib trong script tạm ngoài repository; không import ứng dụng hoặc chạy tests/probes. Các assertions quan hệ trong JSON là **kiểm tra artifacts tĩnh**, không phải bằng chứng thuật toán CAS, persistence, authorization người review hoặc hiệu quả phân tích nghiệp vụ.

Ví dụ 07 dùng dữ liệu synthetic, quyết định mới/reviewer/commit/attestations đều giả định. Fields bị lược được ghi rõ trong wrapper; không phải full canonical export hợp a3. Các ca âm, race và recovery chỉ được mô tả kỳ vọng, chưa thực thi. Số refs resolve không chứng minh thay thế nghĩa vụ đúng; điều đó cần audit thiết kế, kiểm thử implementation và đánh giá ngữ nghĩa riêng.

## Quyết định còn chờ

Auditor cần xem matrix R1, ba nhánh DIRECT/CARRY/REPLACEMENT, điều kiện complete và tái hold, identity/current-key/history refs, source-only alternative và negative cases. Người dùng cần duyệt amendment/schema/profile/version/migration và giao batch implementation phù hợp trước khi code. Lần complete đầu tiên yêu cầu review quan hệ thay thế là lựa chọn bảo thủ đề xuất, không tự xác nhận nghiệp vụ.

**Dừng để audit draft.3; S02-P2-02 chưa được ghi nhận đã đóng. Chưa implement S02 Đợt 2.**
