# H2-B 0.7.0a2 — sửa hai findings, chờ audit lại

Người dùng giao riêng ngày 29/10/2026: S02-2A-H2-B-01/02 của [audit a1](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-2a-h2-b-0.7.0a1-2026-10-28/AUDIT_REPORT.md). Đây là implementation local/synthetic để audit lại, chưa phải auditor đóng finding hoặc người dùng nghiệm thu. [Bàn giao mới](../reports/s02-phase2/2a-h2-b-fixes-0.7.0a2-2026-10-29/START_HERE.md).

API/CLI, phạm vi fresh E1/cùng checked S01 snapshot/bước 1–4, LocalSyntheticAuthority, receipt/T0/seal/T3/CAS và limits tiếp tục theo [hướng dẫn a1](S02_2A_H2_B_IMPLEMENTATION.md) và H2 draft.2. Không có command/flag, canonical schema, registry, DB2, owner profile hoặc dependency mới. Handler pin phát hành là `s02-2a-h2-b/0.7.0a2`; không tự reinterpret pending/sealed work có handler version khác. Handoff a1/wheel/evidence vẫn giữ để đối chiếu.

## Gate Issues mới

Sau build full candidate, code kiểm bounds của Model và toàn Issues, scope/type/current Model của Issues mới cùng selector không thu hẹp blocking refs. Từng selector được rematerialize bằng cùng closure H2-A trên full candidate và base; physical IDs mới chỉ bị loại khi chiếu về graph base nơi chúng chưa tồn tại. Logical source families vẫn giữ nguyên.

Gate đối chiếu source và physical blockers với union units được chọn, retained domain outputs từ bước 2 trở đi, cùng meaningful reverse impact cả hai phía. Part closure giữ toàn action_ids; workflow/Support/context dùng thuật toán hiện hành. Source U không được dùng để bỏ qua blocking action/Part V. Unknown/thiếu impact proof vẫn fail closed. Candidate bị chặn tạo guard-only AS trên base, không Model/Change/Parts dự kiến hoặc tăng completed stage; giữ raw và failed context.

Bước 1 là source inspection. Hold mới thuộc U không tự trở thành blocker cho V độc lập chỉ vì U đã có output inspection. Progress vẫn ghi U held; affected context không được biến thành blocking uses. Unresolved keys nay đối chiếu nguồn và physical closure, gắn đúng result Model/AS. Khi đọc sealed plan/T3, result check kiểm correspondence này và từ chối selected completed output còn business/gap/guard blocker.

## Construction tasks trong batch

H2-A `ConstructionPermit.valid_for` giữ nguyên key và unit set của task. Adapter `_building_task` chấp nhận thêm trường hợp task `await_builder` có toàn unit set nằm trong batch, nhưng vẫn gọi `valid_for` trên chính unit set gốc, đúng Issue ID/key/kind/role/target/provenance pins. Nó chỉ miễn đúng code task đang dựng. Không sửa permit thành unit set của cả batch, không miễn Issue cùng kind/prefix và không chia command thành nhiều publication.

Các task ngoài batch, business/gap/guard và toàn union vẫn được kiểm. Task chỉ resolved bằng predicate builder hiện hành; global mapping task chỉ resolved khi đủ toàn inventory, không vì U/V đã xong riêng. Whole-candidate/CAS vẫn một batch trên một base pair.

## Counters và bảo toàn

`HoldSelector.parse` thêm keyword nội bộ `input_lane` mặc định true; mọi caller cũ giữ hành vi. Typed selector dẫn xuất ở result dùng result bounds, tránh cộng lại như caller input. Cùng Budget 30 giây mỗi invocation; không reset/nới caps hoặc bỏ reference occurrences. Trace blockers mới ghi `unit_id`/`issue_key` để counter hiện hành nhận đủ refs.

Delta pure H2-A giới hạn ở adapter exemption và lựa chọn lane kiểm typed result selector; policy/contract/limits versions cùng canonical schemas giữ nguyên. Xem FINDINGS_RESPONSE, diff và kiểm hồi quy trong bàn giao. Fixtures/approvals/semantic dispositions đều synthetic; các tests là kiểm phần mềm thực thi trên installed wheel, không bằng chứng chất lượng LLM hoặc nghiệp vụ. H2-C/H3/LLM/renderer/live/migration operational nằm ngoài đợt sửa này.
