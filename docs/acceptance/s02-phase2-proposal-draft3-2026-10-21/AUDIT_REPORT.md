# Audit S02 Đợt 2 — plan draft.3 / addendum draft.2

Ngày: 21/10/2026. Phạm vi: audit lại A2-R1/R2 ở mức thiết kế, đối chiếu ví dụ và bằng chứng tĩnh. Không sửa repository implementation.

## Kết luận

**Đóng A2-R1, A2-R2 và finding cha S02-P2-02 ở mức thiết kế.** Không phát hiện finding chặn mới trong phạm vi này. S02-P2-01/A1 tiếp tục đóng ở mức thiết kế; kết luận trước về G2 được giữ nguyên.

Kết luận áp dụng đúng các file có hash trong [artifact-hashes.json](artifact-hashes.json). Đây không phải nghiệm thu implementation A1/A2, migration, toàn bộ Đợt 2 hoặc xác nhận nghiệp vụ. Baseline S01 a6/S02 Đợt 1 a3 giữ nguyên phạm vi nghiệm thu cũ; a3 chưa hỗ trợ amendment.

## A2-R1 — đóng ở mức thiết kế

Căn cứ: [addendum §3.2](/Users/macbookpro/Documents/DACN_implementation/docs/S02_PHASE2_CONTRACT_AMENDMENT_PROPOSAL.md:114) và [JSON 06](/Users/macbookpro/Documents/DACN_implementation/docs/examples/s02-phase2/06-resolved-issue-carry-forward.json).

`structural_check` là phương pháp kiểm tra, không đồng nghĩa kết quả tái sử dụng đã đạt. Bảng mới cho phép `undetermined` trên cùng hoặc khác snapshot khi thiếu bằng chứng; chỉ `applicable` mới đòi đủ điều kiện cùng snapshot, predecessor đã áp dụng được, basis/footprint không đổi và proof đầy đủ. `not_applicable` thuộc human review trong profile hẹp này. Tham chiếu hỏng vẫn bị từ chối, không được che bằng undetermined.

Đã kiểm sáu trạng thái CARRY trong năm graph của JSON 06: applicable cùng snapshot; not_applicable sau đổi nguồn; undetermined khác snapshot; undetermined cùng snapshot nhưng thiếu proof; pending rồi human review trên cùng Model tạo successor applicable. Chúng giữ root event, Answer, lineage, current selection và blocking tương ứng. Nhánh review không tạo application thứ hai.

## A2-R2 — đóng ở mức thiết kế

Căn cứ: [addendum §3.6](/Users/macbookpro/Documents/DACN_implementation/docs/S02_PHASE2_CONTRACT_AMENDMENT_PROPOSAL.md:164), [JSON 07](/Users/macbookpro/Documents/DACN_implementation/docs/examples/s02-phase2/07-resolution-replacement.json) và contract hiện hành về [TaskAttestation](/Users/macbookpro/Documents/DACN_implementation/docs/S02_OUTPUT_CONTRACT_PROPOSAL.md:222).

Thiết kế đã có đường kết thúc blocker mà không sửa lịch sử hoặc tuyên bố resolution cũ trở lại đúng:

1. Q3 ghi resolution cũ not_applicable, giữ hold.
2. QN1 thuộc key mới xử lý quyết định/nghĩa vụ hiện tại. Answer mới có lineage riêng, không supersede Answer khác key.
3. Consent/input đầy đủ đi qua S01; application mới tạo QN2 resolved và Model M4. Q4-pending trên key cũ vẫn giữ hold.
4. Sau bằng chứng tái phân tích và review quan hệ thay thế trên phiên bản hiện tại, successor Q5-replaced cùng M4 kết thúc hold của key cũ. AnalysisSet vẫn giữ cả hai keys; task và event lịch sử không bị sửa.

Điều kiện complete đã bao gồm current target cùng Model/session, kiểm root/obsolete/predecessor, coverage toàn nghĩa vụ và scope, task evidence, review lần đầu, CAS hai head. Target không được là REPLACEMENT tự chứng minh. Thiếu proof/target hết hiệu lực khiến successor trở lại incomplete và materialize hold. Lịch sử not_applicable vẫn giữ nguyên. Quy tắc recovery tách application mới khỏi review sau đó, không apply lại Answer cũ hoặc mới.

Đã đối chiếu graph JSON 07: root/history cốt lõi khớp JSON 06; một event cho Answer cũ và một event cho Answer mới; đúng current keys/Model tại từng head transition; Q4 còn blocking sau application; Q5 chỉ clear blocking với human_review và VALID4; VALID4 trỏ task CH3/CH4 vẫn pending bất biến và evidence trên M4. Consent mới được đối chiếu hash và request riêng. Đây là kiểm quan hệ trong projection, chưa chứng minh code chạy hoặc reviewer thật đã xem.

Nhánh source-only, source bị loại bỏ, target hết hiệu lực lần nữa, race và recovery đã có quy tắc/ca dự kiến. Chưa có thực thi để xác nhận các hành vi này. Khi triển khai, chúng là nghĩa vụ kiểm thử bắt buộc của phạm vi tương ứng, không phải kết quả đã đạt.

## Kiểm tra độc lập đã thực hiện

Script: [check_documents.py](check_documents.py). Kết quả: [document-checks.json](document-checks.json).

| Hạng mục | Kết quả |
| --- | --- |
| JSON scenario, kiểm duplicate keys/non-finite và parse số Decimal | 7 file đọc được |
| Bindings và JSON Pointer | 13 resolve được |
| SourceRef theo snapshot trong từng graph | 118 resolve được |
| Payload bytes/hash/length | 7 khớp |
| Liên kết local trong AGENTS/plan/addendum/response | 77 tồn tại |
| Inventory file được bảo vệ | 4.608/4.608 hash và kích thước khớp |
| Artifact hiện hành | 11 hash khớp manifest; thêm hash chính manifest vào bàn giao audit |
| JSON 01–05 | Đảo riêng version markers tái tạo đúng hash draft.2 |
| A1 và G2 sections | Hash hiện tại khớp baseline section được producer khai báo |
| Source so với wheel S01 a6/S02 a3 | 16/14 payload khớp byte |
| Hồ sơ audit draft.2 | Các file khớp hash audit đã lưu |

Before hashes của các file sửa khớp manifest draft.2. Bằng chứng này xác nhận các đối chiếu được nêu; không có bản sao toàn văn section trước sửa trong audit để tự dựng diff A1/G2 độc lập với baseline section producer. Inventory không bao phủ các thư mục đã loại trừ được ghi trong manifest, nên không suy ra toàn filesystem bất biến.

Đã đọc các điều kiện proof, identity, admission, replacement và planned negatives. Không tái hiện toàn bộ 981 projected crossrefs mà producer khai báo; kiểm độc lập toàn SourceRefs và các liên kết A1/A2 chính. Ví dụ là projection có lược trường, không phải export canonical có thể import bằng validator a3.

Không chạy tests ứng dụng, compatibility probes, concurrency/fault tests, LLM, renderer, build/install hoặc migration. Không dùng số tests của Đợt 1 như kết quả thực chạy trong audit này.

## Bước tiếp theo

Không cần thêm một vòng sửa A2-R1/R2. Trước khi giao implementation 2A có persistence/carry, nên chốt gói kỹ thuật nhỏ cho schema profile/version/capability, compatibility đọc dữ liệu cũ và cách migration/copy theo §4. Gói này phải thể hiện DIRECT/CARRY/REPLACEMENT, history refs, current target selection, fail-closed reader cũ và các test oracle bắt buộc. Đây là gate đã có trong plan §11/§13, không phải finding mới.

Có thể tách pure handlers offline nếu người dùng giao phạm vi đó; chưa gọi toàn 2A hoàn thành khi thiếu A2/profile. G3 capture, G4 ledger, các phụ thuộc G5 và quyền dữ liệu/model/ngân sách live vẫn theo gate riêng của plan. Audit này không cấp quyền triển khai toàn Đợt 2. Không sửa AGENTS hoặc proposal để tự ghi trạng thái thay người triển khai; báo cáo này là căn cứ cập nhật trạng thái ở lượt tiếp theo.
