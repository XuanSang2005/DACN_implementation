# Phản hồi audit H2-D01 / H2-D02 — draft.2

Trạng thái từng finding: **đã sửa đề xuất thiết kế, chờ auditor kiểm lại**. Đây không là runtime fix hoặc kết quả thực chạy. [Proposal](../../../docs/S02_2A_H2_PARTIAL_SCOPE_DESIGN_PROPOSAL.md) là căn cứ mới; [audit đầu vào](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-2a-h2-design-draft1-2026-10-25/AUDIT_REPORT.md) giữ nguyên.

## H2-D01 — adapter/authority/restart

**Trước:** draft.1 đòi provider ngoài payload nhưng chưa xác định invoker/config/API/CLI/tuple, vì vậy positive receipt-only resume và negative provider không có oracle rõ.

**Sau:** proposal §3.1 chọn builtin LocalSyntheticAuthority generic, không import fixture/plugin hay gọi network. Invoker cấp path+expected SHA trực tiếp qua global flags/API ngoài candidate/analysis/DB/config tự khai. File approvals đóng, version/purpose synthetic, allow/deny exact tuple, không wildcard/default/timestamp. ScopeAnalysisEvidence vẫn là basis riêng; approval JSON không tự chứng minh nghiệp vụ. Bản file bất biến, thêm approval cho command mới dùng bản mới, pending command giữ context gốc.

Binding tuple pin store/session/source/snapshot/archive, cả Model+AS/hash, operation/goal/step/units, current selectors/progress/retained basis, read-write intent/candidate/analysis hashes, guard key/current IDs, policy/provider versions. AuthorityDecision allow/deny/unavailable/invalid có expected exit/effects. Đòi authority trước receipt/T0 semantic work, mỗi process chưa finalized và trước seal/T3. Bootstrap code-only không cấp independence là ngoại lệ rõ. Checked absence/finalized read không cần dựng trust mới. Plan sealed giữ nguyên identities; thiếu authority không rebuild/finalize/đổi identity.

**Gate đề nghị đóng thiết kế:** §8.1/§11 có positive prepare→seal→kill→process mới với receipt+trust context cũ→resume một publication; negatives missing/denied/wrong base/AS/scope/evidence/policy/provider/version/hash, file đổi sau seal, thay analysis trong resume, finalized history không cần authority. Từng case có codes0/2/3/5/64 và effects cụ thể tại §3.1/§6.1. Chạy thực trên C/Python thuộc H2-B nếu được giao, không có kết quả runtime ở lượt docs này.

## H2-D02 — guard/progress/revalidation

**Trước:** có guard AS-only và needs_revalidation nhưng chưa có command/predicate để guard giữ/mở rộng/được resolved đúng, dễ hiểu thành dead end hoặc miễn hold. Quy tắc build một lần chưa tách đánh giá lại output khỏi sửa output.

**Sau:** §5.1–5.3 chốt origin/provenance/guard key có cap, current lineage và selectors; guard không đưa vào Model trace để AS-only đúng nghĩa. scoped-revalidate là command mới với current pair, goal admission/retained_output, analysis+approval mới; không thay input của resume, không candidate/domain delta. P_guard kiểm coverage toàn guard/inventory/failure context, impacts/closure/union, current basis, giữ business/gap/task predicates và output cũ. Thiếu proof tạo open successor/AS mới, đủ proof tạo resolved successor có source-only reason/private assessment; current keys/Records lịch sử luôn giữ. Cần sửa output thì terminal_out_of_scope/blocked2, không hứa sửa trong H2.

Progress giữ work_completed lịch sử; đánh giá lại không tăng stage. Assessment bind base→code-owned result pair/hashes không vòng hash. Current progress từ unique actual AS publisher qua promoted plan Artifact + batch/head/Run/actual Records, không timestamp hoặc grant JSON. T3 CAS cặp head cả AS-only; stale không publish successor dự kiến. Guard resolved không authorize candidate cũ và không resolve U/business, unassigned gap hoặc global mapping task.

**Gate đề nghị đóng thiết kế:** §8.2/§11 có ba traces bắt buộc: thiếu proof→hold; đủ proof→guard kỹ thuật xử lý→V command mới tiếp tục/U vẫn hold; retained output→needs_revalidation→assessment-only hoặc terminal nếu cần domain edit. Thêm repeat receipt/lost ACK/kill/T3/stale AS/provider missing và fake task/kind exemptions. Tests union/bridge/derived correctness phải có ngay B cùng writer safety, C chỉ mở rộng stress.

## D1–D4 và điều chưa được quyết định thay người dùng

D1–D4 đã có phương án cụ thể: provider §3.1, lifecycle §5, entry/CLI §2/§6.1, aggregate limits/provider/worklist/Budget §6.2. Các versions private draft.2 chỉ phục vụ thiết kế; không thay canonical profiles/schema/registry/DB2 hoặc legacy behavior. Auditor còn phải kiểm đủ/nhất quán; người dùng còn phải phê duyệt phương án và giao riêng từng scope code H2-A/B/C. Authentication/semantic quality thật, sửa domain output/history/H3/LLM/live vẫn ngoài phạm vi.
