# Bàn giao delta thiết kế 2A H1 — draft.2

Ngày 23/10/2026. **Đã sửa proposal, chờ audit lại.** Chỉ tài liệu; chưa implementation, chưa tự đóng D01/D02 hoặc nghiệm thu H1.

Đọc [proposal draft.2](../../../docs/S02_2A_STEPS_1_4_EXECUTION_DESIGN_PROPOSAL.md), rồi [diff draft.1 → draft.2](DRAFT1_TO_DRAFT2.patch). [Diff mục lục](README_TO_DRAFT2.patch) chỉ cập nhật version/trạng thái của đường dẫn hiện có.

Hai patch là artifacts local được ignore theo policy reports hiện hành; không sửa .gitignore hoặc force-add. Bàn giao này dùng file local đúng hashes dưới đây, chưa phải gói đã publish lên GitHub.

Căn cứ là [audit draft.1](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-2a-h1-design-draft1-2026-10-23/AUDIT_REPORT.md), [kết quả audit](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-2a-h1-design-draft1-2026-10-23/DESIGN_AUDIT_RESULT.json) và [snapshot nguyên byte được audit](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-2a-h1-design-draft1-2026-10-23/PROPOSAL_SNAPSHOT.md). Proposal trước lượt sửa khớp snapshot này; diff không lấy Git HEAD làm bản draft.1 giả định, vì proposal vẫn chưa tracked.

| Mục audit | Phần sửa để auditor kiểm lại |
| --- | --- |
| **D01** — gate H1 không nhất quán | §7/§7.1 đặt core resume/concurrency/crash/lost-ACK/T0–seal–T3/stale Model và AS/version/reopen trong nghiệm thu H1. Mỗi ca yêu cầu raw/plan hashes, IDs/timestamps, head trước/sau và connection/process độc lập; happy path + resume tuần tự chưa đủ. H2 chỉ partial G2/stress ngoài tập tối thiểu |
| **D02** — receipt-only chưa có thao tác rõ | §5.1 chọn **policy A**: resume trả not_prepared/5 khi đã checked absence; explicit prepare-work dùng cùng receipt/command, nhập lại parent/step/raw/hash, đối soát intent dưới transaction. T0 commit đầu tiên pin input; receipt-only không chứng minh intent/kind cũ. Race cùng intent dùng operation thắng; khác intent rejected/2; lookup/commit unknown failed/3, không cấp identity thay thế |
| Plan seal | §5.2 nêu marker/version, envelope/bindings, 0/1/nhiều plan, một primary config trong prepared event; plan thêm sau T0. Sau finalized, checked Run/event/head quyết định outcome, không dùng IDs dự kiến trong plan làm publication |
| Limits/candidate | §8 đề xuất bảng bytes/depth/count/graph/compute và hành vi vượt trước/sau T0, pin limits vào config/plan. Số chưa được benchmark/nghiệm thu. §3 làm rõ required fields/types/nullability/nested refs, không mở arbitrary dict |

Giữ mốc **snapshot S01 + bốn mock → Model/mapping/Issues** trên E1 test fresh/full scope. Không partial continuation trong H1, không Answer/application/history A2 entry point mới, 2B/2C, LLM hoặc renderer. Hai helper prepare/seal vẫn là thiết kế cần audit; không đổi storage/schema/registry đã nghiệm thu trong lượt này.

## Đối chiếu bảo toàn đã thực hiện

- HEAD giữ `4c7e69719dbd1a6e4215cfd01764c6750962ee7f`; trước sửa có proposal chưa tracked và docs/README.md modified, staged diff rỗng. Giữ nguyên công việc đó, chỉ cập nhật phần tài liệu được giao.
- Inventory trước sửa gồm **278 input files**: các file tracked hiện hữu, proposal và 9 file audit draft.1. Ngoài hai tài liệu được sửa, **276/276** khớp SHA-256; bao gồm production/tests/locks và evidence lịch sử nằm trong inventory. Không suy phép kiểm này thành inventory toàn filesystem hoặc mọi artifact ignored.
- Diff so đúng snapshot draft.1; kiểm liên kết local, whitespace, patch dựng lại tài liệu và `git diff --check`; index không có staged diff. Không sửa code/tests/locks, không stage/commit/push.
- Không chạy pipeline, application tests, bootstrap/build/install, migration, LLM/renderer. Ma trận H1 là yêu cầu thực thi sau khi thiết kế được audit và người dùng giao implementation; không phải kết quả tests của lượt tài liệu này.

## SHA-256 để ghim vòng audit lại

| Tài liệu | SHA-256 |
| --- | --- |
| Proposal draft.1 / snapshot audit | `e78ea130d8534c2e5b3686df9f79a10f321e70ecd20195e6f04728186f75bb6c` |
| Proposal draft.2 | `28a43ae1bea4cf6b0106537293472a82fc4de9867f144c6c97e10b165f863e3b` |
| docs/README.md sau sửa | `0f2f86f6519203dfe16df94731a74bf62fe39c357308b5db693e680715f637c4` |
| DRAFT1_TO_DRAFT2.patch | `e43b13b42e32a7d0fec8e2dc7674043a1b181f06ea96ed559b3725095edb1b63` |
| README_TO_DRAFT2.patch | `086c713d3e3e92f3fadb6ea673095be192e6093a63596c91b22c8f346c25037c` |

Auditor cần quyết định phần delta đã đáp ứng D01/D02 hay chưa, cùng contract prepare/seal, CLI/exit codes và defaults limits. Chưa có bằng chứng implementation cho các bảo đảm mới; không coi việc sửa tài liệu là findings đã đóng hoặc cấp quyền code.
