# Đáp ứng điểm F04 còn lại — S02 draft.3

**proposed — chưa audit lại/chưa được duyệt** · Astra · 19/10/2026.

Contract: `s02/0.1.0-draft.3`; kế hoạch: `s02-plan/0.1.0-draft.3`. Chỉ sửa closure của mapping part nhiều actions. **Chưa implement S02; chưa tự đóng F04.**

## Căn cứ và phạm vi

Đã đọc AGENTS và [audit draft.2](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-proposal-draft2-2026-10-18/AUDIT_REPORT.md), cùng `counterexample-F04.json`, `static-checks.json`, `audit-evidence.json`. Các đầu vào hiện tại khớp hash audit trước khi sửa. Theo kết luận audit đó, **F01/F02/F03/F05 đã đóng ở mức đặc tả**; lượt này giữ nguyên quyết định và ví dụ của chúng, chỉ đồng bộ version.

Không thay flow chín bước, bước 6, bước 8.1–8.5, ranh giới S02/S03 hoặc baseline S01. Giữ nguyên AGENTS, code/tests/dependencies, tài liệu/ví dụ S01, nguồn/dataset, audit nguồn và hai artifacts bàn giao draft.2.

## Quy tắc được sửa

| Điểm còn thiếu | Quyết định draft.3 | Vị trí |
| --- | --- | --- |
| Part phát hiện giữa vòng lặp chưa bắt buộc thêm đủ actions | Mọi part components mới, từ seed hoặc phát hiện qua action/workflow/dependency, thêm **toàn bộ** Part.action_ids cùng primary/supporting responsibilities. Các actions mới tiếp tục qua workflow/rules/dependencies/parts. Không mở rộng toàn component/responsibility/interface chung. | [Contract §9.1, bước 1](/Users/macbookpro/Documents/DACN_implementation/docs/S02_OUTPUT_CONTRACT_PROPOSAL.md:242), [bước 3](/Users/macbookpro/Documents/DACN_implementation/docs/S02_OUTPUT_CONTRACT_PROPOSAL.md:244) |
| Điều kiện dừng chưa bao gồm part→actions | Lặp đến khi mọi tập ổn định và không còn action/part mới chưa xử lý; mỗi part phải có toàn bộ actions trong closure. Theo dõi ID đã xử lý trên model hữu hạn; chỉ xét gate sau closure đầy đủ. | [Bước 6](/Users/macbookpro/Documents/DACN_implementation/docs/S02_OUTPUT_CONTRACT_PROPOSAL.md:247) |
| Hợp closure có thể đưa part chưa đủ hoặc blocked vào kết quả | Kiểm lại allowed_scope đóng dưới mọi quan hệ, gồm Part.action_ids. Phần mới bổ sung phải được kiểm acceptance/blockers; không tự chấp nhận hoặc bỏ actions để giữ eligible. | [Bước 7](/Users/macbookpro/Documents/DACN_implementation/docs/S02_OUTPUT_CONTRACT_PROPOSAL.md:248) |
| Chưa có ví dụ/kiểm thử dự kiến cho part nhiều actions | Thêm ba graph projections; kế hoạch unit/contract Đợt 1 yêu cầu oracle độc lập cho ba biến thể và tính đóng của hợp cuối. | [Plan §8.1](/Users/macbookpro/Documents/DACN_implementation/docs/S02_IMPLEMENTATION_PLAN_PROPOSAL.md:199), [Đợt 1](/Users/macbookpro/Documents/DACN_implementation/docs/S02_IMPLEMENTATION_PLAN_PROPOSAL.md:249) |

Part vẫn là đơn vị nghĩa vụ chưa được chia nhỏ. Muốn A1 độc lập với A2 phải tách P12 có căn cứ trong model trước review; không tự chia bằng prose tại gate. Không thêm loại record, field production, error code hoặc cơ chế acceptance mới.

## Ba ví dụ mới và kết quả mong đợi

Trong [08-scope-closure.json](examples/s02/08-scope-closure.json), tên ngắn A1/P1 dưới đây tương ứng các IDs `F04-multipart-*`. Bảy graph `/scenarios/0` đến `/scenarios/6` giữ nguyên.

| Pointer | Dữ liệu / diễn biến | Expected outcome |
| --- | --- | --- |
| `/scenarios/7` | P1={A1}; phát hiện P12={A1,A2}; sau khi thêm A2 phát hiện P2={A2}; Q2 chặn A2/P2. Hai actions có workflows/trách nhiệm riêng, không dependency khác nối chúng. | Required actions={A1,A2}, parts={P1,P12,P2}; P1 cũng blocked; `BLOCKED_SCOPE/revision`, allowed rỗng. Không dừng ở {A1}/{P1,P12}. Phạm vi xin review không phải bằng chứng approval hợp lệ. |
| `/scenarios/8` | Cùng quan hệ part/actions; không blocker, giả định toàn bộ closure đã được review đúng model/set và mọi gate khác đạt. | Allowed giữ **đủ** A1/A2 và P1/P12/P2 cùng context hỗ trợ. Không trả only-A1 kèm P12 chưa được xét hết. Đây là expected có điều kiện, không handoff thật. |
| `/scenarios/9` | Model mới thay P12 bằng P12-A1 và P12-A2 có căn cứ độc lập; Q2 vẫn chặn A2. Giữ logical action/workflow/responsibility IDs, không carry approval model cũ. | Trước review mới: handoff false. Sau review mới hợp lệ và đủ các gate giả định: A1 cùng P1/P12-A1 có thể allowed; A2/P2/P12-A2 vẫn blocked. |

Các graph chỉ là projection synthetic phục vụ review đặc tả; không bổ sung nghiệp vụ phòng khám, không phải Model exports đã commit hoặc kết quả chạy S02. Phần tách P12 phải bảo toàn nghĩa vụ/coverage khi implementation; ví dụ không tự xác nhận tính độc lập nghiệp vụ.

## Files thay đổi/thêm

- [S02_OUTPUT_CONTRACT_PROPOSAL.md](S02_OUTPUT_CONTRACT_PROPOSAL.md): version/ngày/trạng thái audit; sửa riêng §9.1 và dẫn ví dụ.
- [S02_IMPLEMENTATION_PLAN_PROPOSAL.md](S02_IMPLEMENTATION_PLAN_PROPOSAL.md): version/ngày/phạm vi bàn giao; bổ sung hàng kiểm thử và điều kiện bàn giao Đợt 1 cho F04.
- [01](examples/s02/01-source-and-model.json), [02](examples/s02/02-analysis-and-review-package.json), [03](examples/s02/03-revision-scenarios.json), [04](examples/s02/04-review-and-rejection-scenarios.json), [05](examples/s02/05-analysis-freshness.json), [06](examples/s02/06-artifact-lifecycle.json), [07](examples/s02/07-answer-application.json): **chỉ** đổi contract_version sang draft.3.
- [08](examples/s02/08-scope-closure.json): đổi version, thêm ba scenarios; giữ bảy scenarios cũ.
- Báo cáo này và [S02_DRAFT3_STATIC_CHECKS.json](S02_DRAFT3_STATIC_CHECKS.json): artifacts bàn giao mới; không sửa bằng chứng draft.2.

## Kiểm tra tĩnh đã thực hiện và giới hạn

| Kiểm tra artifacts | Kết quả |
| --- | --- |
| JSON parse, key trùng, version/nhãn minh họa | 8 file đạt, exact draft.3; không key trùng. |
| Bindings file/JSON Pointer | 105 resolve, targets là full Record được kiểm ID/type. |
| StageRef/EventRef và payload lưu tạm | 21/20 refs resolve; 15 payloads đúng SHA-256 và độ dài bytes. Đây là hồi quy liên kết tài liệu, không làm lại thiết kế F02/F03. |
| Graph projections | 10 graphs kiểm ID/reference/entry/endpoint/part/action/support và expected scope; allowed/blocked parts không giao nhau. |
| Ba tập expected mới | Đối chiếu tĩnh quan hệ part→đủ actions và action→parts; trace cuối khớp required sets; case không blocker giữ đủ closure; case tách model không carry approval. Không chạy production closure. |
| Không sửa bốn finding đã đóng | Hash các vùng quy tắc contract §2–trước §9.1, §10–trước §12 và plan §2–trước §8 không đổi sau chuẩn hóa riêng chuỗi version. |
| Hồi quy ví dụ cũ | Hash nội dung bảy JSON 01–07 không đổi ngoài version; hash canonical của bảy scenarios đầu file08 không đổi. |

Các phép kiểm ad hoc dùng Python stdlib, chế độ `-B`, chỉ đọc/đối chiếu artifacts; không tạo script/schema/DDL thực thi. Một lần thu thập đầu vào bị giới hạn độ dài output nên chưa tạo được baseline từ lần đó; đã thu lại inventory/hash gọn và kiểm khớp audit **trước mọi chỉnh sửa**. Không mất hoặc ghi đè dữ liệu từ lần thu thập này.

Inventory bảo vệ mới gồm **185 file**: 179 file đúng tập bàn giao draft.2 + hai artifacts `S02_DRAFT2_*` + bốn file audit draft.2. Đã chụp baseline mới đầu lượt và đối chiếu sau, **185/185 cùng hash**. JSON bằng chứng chứa từng path và before/after SHA-256, timestamps UTC, hashes deliverables và đối chiếu các vùng quy tắc. Tập kiểm cụ thể không bao gồm toàn filesystem/venv/cache hoặc toàn dataset; không suy rộng từ con số185. Các timestamps UTC trong bằng chứng tương ứng ngày19/10 theo Asia/Ho_Chi_Minh.

Không chạy tests ứng dụng/S01 suites, validator S02, DB/concurrency/fault tests, LLM, renderer hoặc đánh giá dataset; không cài dependency, tạo source/snapshot thật hay thao tác Git. Kế hoạch kiểm thử vẫn là kế hoạch. Những quyết định live model/ngân sách/toolchain/đánh giá giữ nguyên trạng thái trước lượt này, không cần mở lại để sửa F04.

Audit tiếp theo cần kiểm phần F04 được bổ sung: mọi part được phát hiện đều mở rộng đủ; vòng lặp và hợp cuối thực sự đóng; ba expected outcomes đúng điều kiện review. Không tự ghi finding đã được auditor đóng.

**Draft.3 vẫn proposed, đang chờ audit lại; chưa implement S02.**
