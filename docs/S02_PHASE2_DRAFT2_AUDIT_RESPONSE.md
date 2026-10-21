# Phản hồi audit — proposal S02 Đợt 2 draft.2

**Trạng thái: proposed — đã phản hồi audit, chưa audit lại/chưa được duyệt implementation.**

Ngày 21/10/2026. Proposal `s02-phase2-plan/0.1.0-draft.2`; addendum hẹp `s02-phase2-amendment/0.1.0-draft.1`. Baseline S01 a6/S02 a3, contract S02 draft.3 và nghiệm thu kỹ thuật Đợt 1 không đổi. Vai trò: Astra sửa thiết kế; auditor review độc lập; người dùng quyết định cấp quyền implementation/nghiệp vụ. Không tự ghi findings đã đóng.

## 1. Đối chiếu finding và quyết định

| Finding / yêu cầu | Bằng chứng đã đọc | Phản hồi đề xuất | Vị trí / ví dụ | Kiểm thử dự kiến, chưa chạy |
| --- | --- | --- | --- | --- |
| **S02-P2-01 P1**: S01 unchanged không apply được theo proposal cũ | Audit C/Python: giữ Context + analysis_edit bị application_selected_s01_result; Context mới + analysis_edit bị analysis_edit_source; switch cùng snapshot bị requirements_switch_snapshot | **A1** thêm observed_source_context_id cho archive run S01; so Sobserved với Smodel sau CAS, không theo result_kind. Same snapshot giữ Cmodel + analysis_edit, khác snapshot dùng Cobserved + requirements_switch. Interpretation/consent/observation giữ nguyên | [Addendum §2](S02_PHASE2_CONTRACT_AMENDMENT_PROPOSAL.md), [plan §8.3–8.5/11/14](S02_PHASE2_IMPLEMENTATION_PLAN_PROPOSAL.md), [JSON 05](examples/s02-phase2/05-unchanged-application.json), JSON 03 cập nhật | Positive cùng snapshot và khác snapshot dù unchanged phải commit thật; archive nguồn run khác origin; reopen; hash/request/consent/run/snapshot sai reject; stale M/AS không app; recovery không S01 resubmit |
| **S02-P2-02 P1**: Issue resolved không clone/rebind qua Model | Root application tại M2 đạt; Q2-carried ở M3 bị issue_resolution_target. Chọn Q2 cũ không cùng Model AS3 | **A2** DIRECT giữ đúng event target/model gốc. CARRY successor cùng key/current lineage giữ Answer/event refs, thêm resolution_carry proof; applicable hoặc resolution_pending_revalidation; không ứng dụng Answer lần hai | [Addendum §3–4](S02_PHASE2_CONTRACT_AMENDMENT_PROPOSAL.md), [plan §2.2/5/8.4–8.5/11/14](S02_PHASE2_IMPLEMENTATION_PLAN_PROPOSAL.md), [JSON 06](examples/s02-phase2/06-resolved-issue-carry-forward.json) | M2→M3 applicable; independent edit có proof; nguồn đổi pending/blocked; sai key/lineage/root/event kind/current set hoặc thiếu proof reject; same Answer race và recovery giữ applied=1; checked-read kiểm chain |
| **G2**, cần bảng gate trước 2A | Audit yêu cầu phân biệt đọc/publish/advance/review và tránh cần Parts trước components | Manifest per-step đọc/ngữ nghĩa cần cho bước tiếp, khác Mapping.assessment bước 4; holds có source selector và materialize lại trên graph mới. Không cấp accepted_scope | [Plan §7.1–7.2](S02_PHASE2_IMPLEMENTATION_PLAN_PROPOSAL.md), [JSON 01 admission_walkthroughs](examples/s02-phase2/01-clinic-steps-1-4.json) | Synthetic nguồn rõ đi 1→2→3→4 dù Parts chưa đầy đủ; unknown quyền/constraint còn hold sau actions/components/Parts mới; không fake Review |
| Dependency 2A–2E | Nền tảng accepted không đủ cho các đường mới | 2A builder carry chờ A2; 2C chờ A1+A2+G6; compatibility/profile/migration cần review; 2B G3/G4 riêng; 2D/2E không ready khi dependency chưa duyệt | Plan §14; addendum §4 | Sau quyền implementation mới có regression/migration/concurrency evidence. Offline sub-scope phải giao riêng, không tự coi toàn batch đủ |

Hai P1 được ghi là **đã phản hồi thiết kế, chờ audit lại**. Không sửa invariant a3, chạy probes hoặc sửa assertions để tạo kết quả pass.

## 2. Giới hạn semantics và các quyết định mở

A1 giữ analysis_edit cùng Context, requirements_switch khác snapshot; source archive của run mới không bị bỏ khi Model giữ nguồn. Exact consent hash so với **run source bytes**, không origin/snapshot JSON. Request base/mode/spec và toàn event chain được đối chiếu; cùng result_kind không đủ để phân nhánh.

A2 giữ lịch sử application thật tại root; không xóa answer_ids/evidence, không sửa event gốc, không clone một Answer để apply lại, không tự mở câu hỏi chỉ để qua validator. Invariant thay thế có kiểm DIRECT root, predecessor được base set chọn, lineage không cycle/fork, nguồn và scope impact, status/blocker propagation. History refs chỉ được ngoại lệ tại các field carry đã chỉ rõ; không nới SourceRef hoặc current-selection toàn cục.

Các quyết định còn chờ: shape/status A1/A2 và kiểm typed history refs; tiêu chí structural reuse so với human review; compatibility legacy/extended schema profile và DB marker/migration copy; G1 đầy đủ/G2 admission; G3 capture/G4 ledger/G5 usage/G6 orchestration; data/model/budget và live pilot. Phạm vi addendum chỉ A1/A2, không thay toàn bộ contract hoặc tự gộp G3/G4 vào migration.

## 3. File thay đổi và cách bảo toàn lịch sử

- [AGENTS.md](../AGENTS.md): thêm một bullet giới hạn tương thích và trạng thái sửa proposal; không đổi nghiệm thu Đợt 1.
- [Plan](S02_PHASE2_IMPLEMENTATION_PLAN_PROPOSAL.md): draft.2/status, sửa hai luồng, admission table/walkthrough và dependencies/tests dự kiến.
- [Addendum mới](S02_PHASE2_CONTRACT_AMENDMENT_PROPOSAL.md): current→proposed rules, schema/resolvers/invariants, compatibility và negative cases.
- Ví dụ [01](examples/s02-phase2/01-clinic-steps-1-4.json) thêm admission walkthrough; [03](examples/s02-phase2/03-consent-and-s01-recovery.json) sửa branch/application archive/carry. Ví dụ [02](examples/s02-phase2/02-cancel-permission-and-new-actor.json) và [04](examples/s02-phase2/04-stale-and-dispatch-unknown.json) chỉ đổi proposal version marker.
- Ví dụ mới [05](examples/s02-phase2/05-unchanged-application.json), [06](examples/s02-phase2/06-resolved-issue-carry-forward.json) là projections **không hợp export a3**, dùng nguồn/consent/evaluation giả định, không kết quả chạy.
- Báo cáo phản hồi này và [STATIC_CHECKS_DRAFT2.json](examples/s02-phase2/STATIC_CHECKS_DRAFT2.json) mới. [STATIC_CHECKS.json draft.1](examples/s02-phase2/STATIC_CHECKS.json) giữ nguyên; hashes draft.1 mô tả thời điểm draft.1, không được ghi đè để hợp files draft.2.

## 4. Bằng chứng và phạm vi kiểm tra tĩnh

Lần này chỉ đọc audit/code và kiểm tĩnh bằng Python stdlib: JSON strict không duplicate keys, bindings/JSON Pointers, typed cross-refs trong **projections**, so snapshot branch/Context/Change, root/carry lineage và preservation fields, full input/hash consent, Markdown local targets, hash trước/sau. Các expected invalid mutations là mô tả kiểm thử tương lai; không chạy S02 để chứng minh chúng bị từ chối. Kiểm script tài liệu không là kiểm thử ứng dụng hay nghiệm thu semantics của full graph.

Manifest draft.2 ghi counts, danh sách binding/ref, kết quả đối chiếu và inventory/hash cụ thể; không tuyên bố toàn filesystem/dataset ngoài phạm vi inventory. Nó kiểm lại cả bytes STATIC_CHECKS draft.1 và các file audit độc lập, production code/tests/schema/locks/wheels/báo cáo lịch sử được liệt kê. Chỉ sáu file cũ được phép sửa (AGENTS, plan và JSON 01–04); năm file mới là addendum, phản hồi, JSON 05–06 và manifest. Hai lỗi cú pháp ở script biên tập tài liệu tạm đã được sửa trước khi script chạy được; chúng không thực thi application hoặc làm thay đổi các file bảo vệ.

Bằng chứng audit draft.1 đã đọc: [report](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-phase2-proposal-draft1-2026-10-21/AUDIT_REPORT.md), [result](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-phase2-proposal-draft1-2026-10-21/AUDIT_RESULT.json), [C](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-phase2-proposal-draft1-2026-10-21/compatibility-c.json), [Python](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-phase2-proposal-draft1-2026-10-21/compatibility-python.json), [probe script](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-phase2-proposal-draft1-2026-10-21/probe_compatibility.py). Sáu compatibility cases/backend và kết quả của chúng là **của audit trước**, không phải test run mới trong lượt này.

**Dừng để auditor audit draft.2; chưa implement Đợt 2.**
