# Audit S02 draft.3 — đóng F04

Ngày **19/10/2026**, múi giờ Asia/Ho_Chi_Minh. Contract `s02/0.1.0-draft.3`; kế hoạch `s02-plan/0.1.0-draft.3`.

## Kết luận

**Đóng F04 ở mức đặc tả. Toàn bộ F01–F05 đã được xử lý đủ trong phạm vi audit tài liệu. Chấp nhận draft.3 làm baseline thiết kế để giao Đợt 1 S02 — nền tảng và nối S01.** Không phát hiện điểm chặn còn lại trong phần sửa được audit.

Kết luận này xác nhận độ rõ và tính nhất quán của đề xuất, không phải nghiệm thu implementation S02. Đợt 1 sẽ cần kiểm thử code, lưu trữ, concurrency/recovery và các bất biến theo kế hoạch, rồi bàn giao audit riêng. Lượt hiện tại chỉ audit tài liệu và tạo bằng chứng; chưa implement.

## F04 đã được sửa đầy đủ

Các điều khoản mới giải quyết đúng phản ví dụ của draft.2:

- [Contract:242](/Users/macbookpro/Documents/DACN_implementation/docs/S02_OUTPUT_CONTRACT_PROPOSAL.md:242): quy tắc lấy toàn bộ Part.action_ids áp dụng cho mọi part vào closure, gồm cả part được phát hiện sau seed.
- [Contract:244](/Users/macbookpro/Documents/DACN_implementation/docs/S02_OUTPUT_CONTRACT_PROPOSAL.md:244): part mới thêm đầy đủ actions/trách nhiệm; actions mới tiếp tục qua workflow, rules, dependencies và mappings. Part không được tự cắt phạm vi bằng prose ở gate.
- [Contract:247](/Users/macbookpro/Documents/DACN_implementation/docs/S02_OUTPUT_CONTRACT_PROPOSAL.md:247): điều kiện dừng bao gồm part→actions và mọi công việc mới; bất biến `set(part.action_ids) ⊆ closure.actions` được nêu tường minh. Gate chỉ chạy khi closure đủ.
- [Contract:248](/Users/macbookpro/Documents/DACN_implementation/docs/S02_OUTPUT_CONTRACT_PROPOSAL.md:248): hợp cuối phải đóng và kiểm lại acceptance/blockers cho phần bổ sung; không để part thiếu phụ thuộc đi vào allowed_scope qua seed khác.
- [Kế hoạch:199](/Users/macbookpro/Documents/DACN_implementation/docs/S02_IMPLEMENTATION_PLAN_PROPOSAL.md:199) và [Đợt 1:249](/Users/macbookpro/Documents/DACN_implementation/docs/S02_IMPLEMENTATION_PLAN_PROPOSAL.md:249) đưa các trường hợp mới vào yêu cầu kiểm thử và bằng chứng bàn giao.

Việc mở rộng vẫn dựa trên quan hệ do Part khai báo, không kéo mọi action chỉ vì chung component/interface/responsibility. Điều này giữ được chính sách chấp nhận phần độc lập của S02.

## Ba ví dụ mới

Đã kiểm tra [file08](/Users/macbookpro/Documents/DACN_implementation/docs/examples/s02/08-scope-closure.json), scenarios 7–9. Tên ngắn dưới đây tương ứng các ID `F04-multipart-*`.

| Trường hợp | Tập cần xét | Kết luận theo điều kiện minh họa |
| --- | --- | --- |
| P1 phát hiện P12 nhiều actions; A2 bị chặn | Actions A1/A2; parts P1/P12/P2 | P1 bị chặn, allowed rỗng; không bỏ A2 |
| Cùng quan hệ, không blocker và đã review đủ | Actions A1/A2; parts P1/P12/P2 | Allowed chứa đủ closure cùng context hỗ trợ |
| Model mới tách P12 thành P12-A1/P12-A2 | Với seed P1: A1 và P1/P12-A1 | Chỉ có thể tiếp tục A1 sau review mới; A2/P2/P12-A2 vẫn bị chặn |

Đối chiếu độc lập dùng phép tìm tập liên thông trên quan hệ hai phía Part–Action cho đúng ba graph synthetic này. Mỗi workflow trong ba graph có một action, không có rule/dependency khác nối hai actions. Các tập tính được khớp required sets, trace cuối, allowed scope và blocker đã khai báo. Kiểm tra này không phải chạy thuật toán ứng dụng S02 và không chứng minh nghiệp vụ độc lập ngoài những giả định đã ghi.

Ví dụ tách part giữ `old_approval_carried=false` và `handoff_before_new_review=false`. Các kết quả eligible=true đều được giới hạn bởi preconditions review/validation giả định; không được trình bày như approval hoặc handoff thật.

## Hồi quy các phần đã đóng

Đã lấy lại nội dung draft.2 giữ từ lượt đọc audit trước, xác minh SHA-256 khớp bằng chứng audit độc lập, rồi đối chiếu với draft.3. Sau khi bỏ khác biệt chuỗi version:

- Các quy tắc contract trước §9.1 và từ §10 đến trước §12 giữ nguyên.
- Các lựa chọn kỹ thuật trong plan §2 đến trước §8 giữ nguyên.
- Bảy JSON 01–07 chỉ đổi contract_version; đổi ngược version tái tạo đúng hash draft.2 đã audit.
- File08 khi bỏ ba scenarios mới và trả version về draft.2 tái tạo đúng bytes/hash bản đã audit. Bảy graph cũ và các phần còn lại của file được bảo toàn.

Vì vậy F01/F02/F03/F05 tiếp tục đóng ở mức đặc tả; không cần mở lại chỉ vì đổi số draft. Bản diff chi tiết được lưu trong bằng chứng.

## Kiểm tra tĩnh và bảo vệ dữ liệu

| Nội dung | Kết quả |
| --- | --- |
| JSON examples | 8 file parse được, không key trùng, đúng version và nhãn minh họa |
| Bindings | 105 file/JSON Pointer resolve; full Record targets khớp ID/type |
| Staging/events | 21 StageRefs, 20 EventRefs resolve; 15 payloads khớp hash/byte length |
| Graph projections | 10 graph kiểm liên kết cơ bản; ba expected closure mới được đối chiếu độc lập |
| Deliverables | 11 file khớp hashes Astra bàn giao; audit pin thêm AGENTS và JSON bằng chứng của Astra |
| Protected inventory | 185/185 file hiện tại khớp before/after hashes đã cung cấp |

185 file là đúng tập inventory được công bố, không đại diện toàn filesystem hoặc toàn dataset. Audit xác minh bytes hiện tại và đối chiếu căn cứ đã giữ từ lượt trước; không tuyên bố tự quan sát thời điểm Astra chụp baseline. Baseline S01 và các artifacts audit cũ trong tập này giữ nguyên.

Chưa chạy application tests/S01 suites, runtime validator, DB/concurrency/fault tests, LLM, renderer hoặc dataset evaluation. Không cài dependency, thao tác Git, sửa proposal/AGENTS/source/tests hay ghi vào dataset. Chỉ thêm artifacts trong thư mục audit hiện tại.

## Phạm vi được dùng làm căn cứ tiếp theo

Đủ căn cứ để giao Astra **Đợt 1 theo kế hoạch draft.3**: package/locks S02 riêng; schema và typed refs; nối S01 bằng checked lookup; archive nguồn; repository cùng model/AnalysisSet heads; staging/events; nền tảng revision/clarification; scope closure thuần; CLI init/lookup/receipt tối thiểu. Bàn giao bằng chứng kiểm thử thật và audit trước khi sang Đợt 2.

Các quyết định live model/API, dữ liệu được phép gửi, ngân sách LLM, exact renderer toolchain và rubric/heldout vẫn được xử lý trước đợt sử dụng tương ứng. Kết luận thiết kế này không tự duyệt chi phí hay xác nhận nghiệp vụ phòng khám.

Các proposal hiện vẫn giữ nhãn do Astra ghi lúc bàn giao. Khi được giao Đợt 1, có thể đồng bộ AGENTS/trạng thái tài liệu để dẫn đúng biên bản này, phân biệt **baseline thiết kế đã audit** với **implementation chưa nghiệm thu**. Lượt audit này không sửa những file đó.

## Bằng chứng

- [static-checks.json](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-proposal-draft3-2026-10-19/static-checks.json).
- [Đối chiếu nội dung draft.2 → draft.3](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-proposal-draft3-2026-10-19/document-diff-verification.json).
- [Kết luận audit gắn hashes baseline](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-proposal-draft3-2026-10-19/audit-evidence.json).
