# H3-A 0.9.0a2 — nghiệm thu pure policy local/synthetic

Người dùng nghiệm thu ngày 31/10/2026 theo [biên bản](S02_2A_H3_A_ACCEPTANCE.json). [Audit độc lập](AUDIT_REPORT.md) đóng findings01/02/03 trên wheel SHA `483c9b960c481653b35c0efbae0d5c194d46e6d6895790e69205dbb193ad0e15`. Auditor tự chạy mới mỗi backend C/Python: focused129, oracle gốc13, controls bổ sung8, không fail/error/skip. Full1106/986/backend là supporting evidence implementer; auditor không chạy lại full.

Phạm vi là contracts/pure checks/history policy local/synthetic. Chưa nghiệm thu runtime loader/writer/checkpoint/CAS/resume H3-B/C/D, nghiệp vụ, LLM/live hoặc toàn S02. Người dùng giao riêng H3-B; contract delta cần audit trước phần writer phụ thuộc, và S1–S6 §7.1 vẫn bắt buộc.

[SOURCES](SOURCES.json) pin các bản sao nguyên byte. Link tương đối bên trong báo cáo audit gốc trỏ evidence tại original audit root được SOURCES ghi rõ; không phải artifacts đã copy đầy đủ vào Git. Trạng thái “người dùng chưa nghiệm thu” trong bản audit là lịch sử lúc audit xuất bản, không sửa bản gốc.

[Observation I02](WORKTREE_DRIFT.json) và [diff ngoài release](WORKTREE_DRIFT.patch) giữ nguyên. Hai thay đổi cleanup không thuộc phạm vi nghiệm thu H3-A; [đối soát riêng](../../../reports/s02-phase2/2a-h3-b-contract-review-2026-10-31/I02_RECONCILIATION.md) ghi nguồn từ lượt cleanup bị ngắt, không tự rollback/đóng observation hoặc rewrite commit đã có.
