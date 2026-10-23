# Phản hồi ba findings P1 — dacn-s02 0.2.0a2

Ngày 22/10/2026. Astra đã sửa trong phạm vi P1, **chờ audit lại**. Chưa ghi nhận auditor đóng S02-2A-P1-01/02/03 hoặc nghiệm thu P1. Căn cứ là [audit a1](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-2a-p1-0.2.0a1-2026-10-22-150954/AUDIT_REPORT.md), addendum A1/A2 §3.6 và TaskAttestation trong contract draft.3. Đường dẫn tuyệt đối và hash các oracle nằm trong [audit-inputs.json](audit-inputs.json).

## S02-2A-P1-01 — scope TaskAttestation

**Nguyên nhân:** a1 dùng `subset(hold, evidence_scope)`; hold mô tả toàn replacement, không phải task. Do đó lọt task có Actor nhưng evidence thiếu Actor; đồng thời từ chối evidence A1 hợp lệ cho task A1.

**Sửa:** [resolution.py:274](../../../packages/s02/src/dacn_s02/resolution.py#L274) vận chuyển scope task lịch sử, và [dòng 393](../../../packages/s02/src/dacn_s02/resolution.py#L393) dùng scope task để kiểm evidence. Cùng Model kiểm đúng task, gồm element_ids và mapping_part_ids. Khác Model phải đi qua từng cạnh ancestry bằng `element_pairs` trong chuỗi resolution đã được validate. Giữ mọi đích của quan hệ nhiều–nhiều và thành viên cũ còn tồn tại; không suy correspondence từ ID evidence hoặc same-ID. Thiếu correspondence, removed hoặc thiếu evidence current-model không được complete. Task/Change bất biến và coverage replacement ở dòng 369–370 giữ riêng.

**Trước/sau đã chạy:** hai oracle audit tương ứng thất bại trên a1 và pass trên a2, cả C/Python. Audit ca thiếu Actor chuyển từ DID NOT RAISE sang reject; ca task A1/evidence A1 chuyển từ `replacement_task_scope` sang accept.

**Regression:** [test_p1_audit_regressions.py](../../../packages/s02/tests/test_p1_audit_regressions.py) kiểm task A1/A2, thiếu một action/Actor, hai cạnh Model, missing/removed/unrelated correspondence, Part khác action, modified pair với evidence mới và synthetic review; kiểm không mutate graph/task lịch sử. Evidence rộng của target vẫn phải phủ hold độc lập.

**Giới hạn:** correspondence ngoài chuỗi resolution đã validate, task trước root không có đủ chuỗi proof hoặc task bị xóa chưa có cơ chế completion riêng trong P1 này; validator giữ không đủ điều kiện complete. Không tự biến removal thành hoàn tất. Phù hợp bước và chất lượng nội dung tái phân tích vẫn cần người review; code chỉ kiểm cấu trúc/version/scope.

## S02-2A-P1-02 — footprint target của structural continuation

**Nguyên nhân:** a1 bỏ affected/blocking khỏi `meaning()`, trong khi scope_unchanged chỉ chứng minh phạm vi replacement. Target mở rộng Actor vẫn được giữ complete bằng structural_check.

**Sửa:** [resolution.py:314](../../../packages/s02/src/dacn_s02/resolution.py#L314) và [dòng 412](../../../packages/s02/src/dacn_s02/resolution.py#L412) kiểm target predecessor/successor riêng: tập affected/blocking, footprint forward/reverse impact, tình trạng closure và exact values của mọi thành viên. Model pin có thể đổi theo lineage; structural correspondence chỉ được giữ khi identity, giá trị, source/trace và footprint đủ bằng chứng không đổi. Thứ tự scope không mang nghĩa nên reorder không bị từ chối. Đổi/rename thành viên cần nhánh review; không mượn scope proof của replacement để bỏ qua target.

**Trước/sau đã chạy:** oracle target-expanded thiếu review từ DID NOT RAISE trên a1 sang reject trên a2, cả hai backend. Controls audit incomplete+hold và complete+review mới vẫn pass. Không tạo HumanReviewEvidence trong production.

**Regression:** unchanged/reordered/expanded/incomplete/review/stale-review trên cùng Model và Model kế tiếp; target có Actor ngoài hold của replacement nhưng giá trị Actor thay đổi phải bị chặn. Giữ đường structural continuation khi target không đổi. Digest review cũ không thể cấp quyền cho successor mới.

## S02-2A-P1-03 — command identity/reserved Run

**Nguyên nhân:** a1 chỉ kiểm inventory/profile/shape operations, chưa kiểm map key bằng command_id và chưa áp uniqueness cho reserved_run_id của operation chưa finalized.

**Sửa:** [profile_graph.py:19](../../../packages/s02/src/dacn_s02/profile_graph.py#L19) kiểm hai invariants trước mọi `get_profile`/dispatch/lineage. Uniqueness áp trên toàn commands map, không phụ thuộc session/profile hoặc có Run cuối hay chưa. Vi phạm trả S02Error; owner-profile dispatch tường minh giữ nguyên.

**Trước/sau đã chạy:** hai ca audit DID NOT RAISE trên a1 chuyển thành reject trên a2. Control DB1 vẫn từ chối reserved Run trùng. Regression bổ sung collision với Run đã publish và giữa hai prepared operations, L1/E1, cùng unknown-profile để chứng minh identity được kiểm trước dispatch.

Không sửa repository, SQL, CAS, claims hoặc DB format. Đây là kiểm consistency thuần memory.

## Kiểm chứng, oracle và phạm vi

Xem [TEST_RESULTS](TEST_RESULTS.md), [execution-summary.json](execution-summary.json), [implementation.diff](implementation.diff), [protected-inventory.json](protected-inventory.json) và [oracle-preservation.json](oracle-preservation.json). Diff so đúng trạng thái dirty trước sửa, không chỉ so Git HEAD. Sáu file hiện hữu được sửa có bản trước tại `before/`; thêm một file regression. Không sửa bất kỳ file tests a1/a3 hoặc ba file audit gốc.

Contract/profile/rules IDs giữ nguyên: L1 draft.3/legacy-a3, E1 draft.4/a1a2-v1. Đây là sửa validator thực thi các điều kiện đã chốt, không đổi schema semantics. Package tăng a1 → a2 để phân biệt artifacts. Hash code thực cập nhật tại [rules-bundle.json](rules-bundle.json); schema L1/E1/registry nguyên byte.

Đã thực thi tests code trên fixtures synthetic và S01/S02 DB tạm. Synthetic reviews chỉ là inputs kiểm binding, không phải người thật xác nhận. Chưa chứng minh chất lượng nghiệp vụ, completeness ngữ nghĩa, E1 persistence, atomic CAS/claims, DB2/migration/cutover/activation, 2C hoặc live. Không mở operational store, không sửa dataset, không gọi LLM/renderer. Nghiệm thu S01 a6 và S02 a3 Đợt 1 giữ nguyên.
