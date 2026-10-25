# Delta tài liệu và hướng audit

**Trạng thái:** H1 đã nghiệm thu kỹ thuật trong đúng phạm vi audit a2; H2 draft.1 chờ audit thiết kế. Lượt này chỉ sửa tài liệu. Không thực hiện application tests, build/install, bootstrap, migration, LLM, renderer hoặc live; không stage/commit/push.

## 1. Delta so đúng trạng thái đầu lượt

Chụp HEAD/index/status và inventory trước sửa tại [before.inventory.json](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/designs/s02-2a-h2-draft1-2026-10-25/before.inventory.json); snapshot nội dung visible tại `before/` trong cùng output. HEAD bắt đầu `4c7e69719dbd1a6e4215cfd01764c6750962ee7f`, index rỗng. Working tree đã có code/tests/docs H1 chưa commit. Diff của lượt này so snapshot trước sửa, **không dùng diff HEAD để nhận cả code H1 là thay đổi mới**.

| Nhóm | Nội dung |
| --- | --- |
| 7 tài liệu hiện hành | AGENTS.md, README.md, docs/README.md, reports/README.md, docs/S02_2A_H1_IMPLEMENTATION.md, docs/s02/README.md, docs/BOOTSTRAP.md: ghi nghiệm thu H1 a2, scope/erratum đúng, navigation H2 pending; phân biệt bootstrap P3 với driver H1 |
| 5 files acceptance mới | 4 bản sao nguyên byte audit/biên bản/erratum/oracle-correction và SOURCES.json riêng. Không sửa acceptance index/evidence cũ, không chép/sửa oracle Python |
| Proposal mới | [H2 draft.1](../../../docs/S02_2A_H2_PARTIAL_SCOPE_DESIGN_PROPOSAL.md), private contracts đề nghị, chưa canonical schema/code |
| 3 tài liệu bàn giao mới | START_HERE, tài liệu này và COMMIT_PREPARATION |

Production/tests/locks/tooling, S01, canonical schemas/registry/DB2 và mọi file lịch sử trong inventory phải bằng SHA-256 đầu lượt. Proposal execution draft.2 và bàn giao H1 a1/a2 không chỉnh trạng thái hồi tố. `STATIC_CHECKS.json` ghi số thực, ngoại lệ chỉ gồm 7 docs nêu trên; phần còn lại phải nguyên byte. Không quét dataset hoặc mở store ứng dụng.

## 2. Nội dung thiết kế cần auditor đối chiếu

- Đối chiếu §1–3 với LaTeX và G2 plan §7.1: inspected từng requirement/criterion/constraint, `advance` không là review/accepted_scope. Không lấy not_assessed hoặc graph chưa có edges làm proof độc lập.
- §4 giữ source selector khi graph lớn; closure/reverse impact trên base lẫn candidate tới fixed point; Part–mapping row–source gắn cùng ngữ cảnh. Shared component không kéo mọi action; Part/workflow/Support thực sự liên quan thì mở hết. Unknown applicability giữ all_source_uses.
- §5 kiểm full Model/current Issues/union; không chỉ cộng kết quả scope. Thay pair cần derived proof hoặc revalidation; không copy cờ done. Giữ task mapping toàn cục và mỗi gap hold riêng như H1 a2.
- §6 giữ receipt-only/not_prepared, T0 intent pins, một seal/plan, CAS cặp Model+AS, finalized authority, crash/lost ACK/unknown và dispatch H1. Scope disjoint vẫn cạnh tranh một head; bên stale phải tạo command mới explicit.
- §7–9 có invariants, phản ví dụ/positive controls và tiêu chí phần mềm. Đây là kế hoạch kiểm tương lai, không kết quả thực thi H2.
- §10 chia H2-A pure policy, H2-B writer + toàn safety ngay entry đầu, H2-C merge/stress. Không trì hoãn safety của H2-B, không nhập Answer/A2 history/H3 hoặc 2B/2C.

## 3. Quyết định còn thiếu, không tự chốt

| ID | Đề nghị | Rủi ro nếu chưa chốt |
| --- | --- | --- |
| D1 | Evidence ngữ nghĩa từ caller/provider tin cậy ngoài candidate; rebind đúng hashes mỗi process execute chưa finalized; CLI không lấy JSON tự khai trusted làm authority | Không có positive independence đáng tin; thiếu binding không execute/publish |
| D2 | Candidate hợp cấu trúc nhưng merge thiếu impact proof: AS guard-only trên base, Run blocked, không publish Model hoặc tăng progress | Không được tự release, sửa/thu nhỏ scope để qua gate; cần duyệt semantics guard và oracle |
| D3 | Requirement family; fresh same-source append-only; entry/config/plan/CLI H2 riêng, scope canonical null không cấp quyền; H1 bootstrap tối thiểu chỉ nếu duyệt | Không lén nhận historical/A2, thay meaning WorkRequest/handler cũ hay auto rebase |
| D4 | Giữ H1 bounds, bound chung candidate+analysis và serialized config/plan; stress 4 workers/≥20 checkpoints là đề nghị | Không nới limits hoặc nhận input không bounded trong implementation |

Nếu auditor yêu cầu sửa canonical schema/DB2 hoặc A2 semantics để thực hiện các phương án trên, ghi xung đột và đưa review riêng. Không coi proposal này tự mở rộng contract đã nghiệm thu hoặc cấp quyền triển khai.

## 4. Bằng chứng và giới hạn

[Commands/exit codes/logs](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/designs/s02-2a-h2-draft1-2026-10-25/commands/), [kiểm tĩnh](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/designs/s02-2a-h2-draft1-2026-10-25/STATIC_CHECKS.json), [bảo toàn](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/designs/s02-2a-h2-draft1-2026-10-25/protected-verification.json), [diff](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/designs/s02-2a-h2-draft1-2026-10-25/documentation.diff.patch), [inventory tài liệu](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/designs/s02-2a-h2-draft1-2026-10-25/documentation.inventory.json), [commit candidates](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/designs/s02-2a-h2-draft1-2026-10-25/COMMIT_CANDIDATES.json), [seal](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/designs/s02-2a-h2-draft1-2026-10-25/SEAL.json). Kiểm local links không kiểm availability của URL Internet; hashes chứng minh bytes, không chứng minh thiết kế đúng. Inventory bảo vệ bao gồm visible tracked/untracked và các reports lịch sử, không phải toàn filesystem/runtime/dataset.

Số S02 769/backend, S01 986/backend, V4 10/backend được dẫn ở hướng dẫn H1 là **lượt audit độc lập a2**, không chạy lại ở đây. V3 logger tuple/erratum và timeout a1 không viết lại. Lượt này không tái chứng minh C/Python, crash/DB behavior hoặc source–wheel–installed; dùng nghiệm thu H1 làm baseline và yêu cầu kiểm mới khi có implementation H2. Không có wheel H2.

Kiểm replay diff tĩnh lượt đầu thất bại vì script chưa ghi marker “No newline at end of file” cho oracle-correction.json nguyên bản. Đã sửa **script kiểm ngoài checkout**, không thêm newline vào bản sao/audit gốc; giữ attempt01 và chạy lại kiểm. Đây là lỗi harness diff tài liệu, không phải application test hay finding implementation.
