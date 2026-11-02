# H3-B 0.10.0a1 — frozen private delta và API

Implementation theo B-P01 đã được người dùng chấp thuận sau [audit thiết kế](../../../docs/acceptance/s02-2a-h3-b-contract-draft1-2026-10-31/README.md). Không tự ghi runtime B đạt audit hoặc nghiệm thu. [Proposal gốc](../../../docs/S02_2A_H3_B_CHECKPOINT_CONTRACT_DELTA_PROPOSAL.md) giữ byte/trạng thái tại thời điểm đề xuất; quyết định hiện hành nằm trong acceptance/navigation.

## Dispatch

| Lane | Version | Gate |
| --- | --- | --- |
| A input projection | Private draft.2 nguyên bản | Old checkers/oracles nguyên hành vi, không nhận B result |
| H2 historical origin | Config/Plan draft.2, handler H2 gốc | Actual promoted raw/config/plan/result reader; không giả history-free context |
| B Config/Plan/Admission | `s02-h3-{config,plan,admission}/0.1.0-draft.3` | Separate result/config/publisher checks, same closed field sets |
| B policy / work binding / authority / analysis | `s02-h3-history-policy`, `s02-h3-work`, `s02-h3-local-authority`, `s02-h3-analysis`, đều `/0.1.0-draft.3` | Exact external B tuple; old/mixed/unknown reject |
| B handler | `s02-2a-h3-b/0.10.0a1` | AS-only adopt/revalidate |
| Registry / anchor / limits / receipt | Existing versions | Không đổi protocol/caps/canonical schemas/DB2 |

Config mode chỉ adopt/revalidate, candidate null. Adopt step0/full inventory/goal admission; revalidate step1..4 với admission hoặc retained_output đã có actual stage proof. Không build/domain output mới. Pure B checks cũng buộc adopt goal=admission, retained_output phải có actual stage/output tương ứng của từng selected unit, và introducing work request exact scope/config_artifact_id=null như API/writer; external tuple đúng không thay stage proof hoặc cấp scope khác.

## Thuật toán và concretization

1. Pure checked stage evidence đến từ actual promoted H2/B plan và full output/origin/raw/source inventory; typed dataclass không tự thành capability. B publisher kiểm projected Run/finalized graph, exact batch/promotion/stage/clock/IDs. Parent Config revalidate lấy full promoted Admission, không projection A bị xóa assessment. Các hashes source/context/diff/closure/proof/parent được recompute đúng B-P01, không chứa chính assessment/plan.
2. No-anchor giữ stage0, output refs rỗng và actual output IDs/needs_revalidation. Full proof giữ completed stage và ordered historical output refs, không tăng stage qua adopt/revalidate. B result luôn có technical assessment/latest pair thật; assessment không thay stage proof, semantic authority hoặc historical human evidence. Equal assessment values được deduplicate trong `retained_assessments` (uniqueItems); per-unit map/parent hashes vẫn đầy đủ.
3. H2 Node/Edge locators được normalize thành WorkflowNode/WorkflowEdge trong private B transport sau actual raw/Model membership checks. Current Issue aliases rebind qua immutable issue_key; historical output alias snapshots giữ nguyên. B anchor chỉ transport AS-only transitions, actual parent/result assessment hashes/correspondence; không mở Model continuation H3-C.
4. T0 pin toàn store Records/events/snapshots và owner/profile inventories. Lần sau kiểm toàn immutable dependencies và current canonical graph riêng. Own command facts kiểm exact phases/stages/payload/promotions. Detached losing-plan witness chỉ loại post-T0 additions, không bỏ pinned dependency hoặc refresh intent. All-store R cố định, gồm ancestors/session khác.
5. Registry loader nhận ReviewTrustContext ngoài DB, bounded read, hash/version/required-ID inventory/dependency checks, dựng Repository với review map trước reconciliation/checked read. B semantic adapter nhận SemanticTrustContext riêng và chỉ B Authority. Không derive reviewer/assessment/expected SHA từ DB. Finalized report providerless vẫn cần original historical registry.
6. Admission bảo toàn typed TaskOrigin H2 bằng actual introducing plan/root/predicate/unit/target-step/current Issue ID/origin plan SHA. Không nhận kind/prefix làm task và không cấp construction permit B từ metadata này; task Records/blockers và target_step/role giữ nghĩa gốc; adopt kiểm bước1, không đẩy task bước sau về bước1, cũng không miễn task tại target step để build. Đây là concretization inventory của thiết kế đã chốt, không mở C.
7. Receipt trước T0; reserved Run/raw/config/start allocation một lần trong T0. Seal chọn một immutable plan gồm IDs/times/allocations. Resume đọc winning seal, T3 paired CAS. Stale loser chỉ giữ exact planned Artifacts và reserved Run với đúng CAS conflict transform; không planned AS/Issue. Registry/authority rehash trước commit; không rebuild/rebase sau seal. Unknown COMMIT cần explicit same-command recovery.

## API và errors

[Hướng dẫn API](../../../docs/S02_2A_H3_B_IMPLEMENTATION.md) và source `h3_service.HistoryService`: inspect/prepare/resume/report/adopt/revalidate, API Python trước CLI. Settings/receipt s02/2/canonical Repository giữ nguyên. Closed private validation trả H3_CONTRACT_INVALID/H3_LOCAL_LIMIT; unavailable external registry/authority trả persistence error riêng. Pending report là prepared/sealed; chưa T0 là not_prepared; publication completed/blocked hoặc CAS stale. Semantic status luôn synthetic_not_business_confirmation; report không cấp authorization hiện hành.

Không thay semantics ngoài B-P01/G1–G4. New modules không tạo human decision/Answer/application/Model/Change/source switch hoặc sửa completed outputs. Test-only controllers tạo lịch sử synthetic có sẵn/valid rival bằng infrastructure cũ; đó không là sản phẩm B tạo quyết định. H3-C/D/CLI/live vẫn cần scope và audit riêng.
