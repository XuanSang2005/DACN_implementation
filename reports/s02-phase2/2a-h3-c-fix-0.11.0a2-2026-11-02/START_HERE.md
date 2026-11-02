# H3-C fix candidate 0.11.0a2 — chờ re-audit

Sửa riêng S02-2A-H3-C-01/02 theo [audit a1](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-2a-h3-c-0.11.0a1-2026-11-02/AUDIT_REPORT.md). Findings vẫn OPEN theo kết luận độc lập hiện có; implementer không tự đóng hoặc nghiệm thu C.

Production delta: pure C union gate đọc negative facts trong candidate bên cạnh analysis; bước4 dùng `part_has_gap` hiện có, gồm `covered_portion=null`. Không đổi writer/CAS, contract C-P01/private draft.4, canonical validators/schemas/registry/DB2 hoặc locks. Raw và projection không bị sửa để vượt gate. Handler protocol tag a1 giữ nguyên, distribution phát hành a2.

Kết quả mới: **8/8 oracle nguyên bản + 7/7 regression mới + 16/16 controls bị ảnh hưởng =31/31 mỗi backend**, C rồi Python tuần tự; không failure/error/skip/retry. Thời gian wall: c: 222.215s; python: 249.172s. Có hai oracle/backend qua API và DB Model+A2 thật với fixtures synthetic; providerless report/reopen không ghi DB. Đây không phải kiểm nghiệp vụ/LLM hoặc nghiệm thu.

Wheel duy nhất: [dacn_s02-0.11.0a2-py3-none-any.whl](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h3-c-fix-0.11.0a2-2026-11-02/delivery/wheels/dacn_s02-0.11.0a2-py3-none-any.whl) (242788 bytes). SHA-256: `34c9b6c68f83c73471e4fde092fa073330f9b00ba4a8aff4a3003e95401d8704`. Fresh offline venv non-editable ngoài checkout; source–wheel–installed bằng nhau. S01 accepted a6 cài từ lock, payload bằng source/installed, không rebuild.

- [FINDINGS_RESPONSE](FINDINGS_RESPONSE.md): thay đổi, chứng cứ và trạng thái từng finding.
- [COVERAGE_MATRIX](COVERAGE_MATRIX.md): từng case/phase/backend, không dùng counts lịch sử như kết quả mới.
- [REPRODUCE](REPRODUCE.md): commands/logs/JUnit, wheel/source diff/inventory và DB readbacks.
- [LIMITS](LIMITS.md): phạm vi chưa chạy, giới hạn guard và lỗi diagnostic phụ.
- [Evidence mới](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h3-c-fix-0.11.0a2-2026-11-02/RESULTS.json), [diff](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h3-c-fix-0.11.0a2-2026-11-02/fix.diff), [inventory](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h3-c-fix-0.11.0a2-2026-11-02/AFTER.json), [seal](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h3-c-fix-0.11.0a2-2026-11-02/SEAL.json), [AUDIT_READY sau seal](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h3-c-fix-0.11.0a2-2026-11-02/AUDIT_READY).

Handoff a1, audit/oracles và evidence cũ giữ nguyên. Full/safety a1 là lịch sử supporting evidence; lượt sửa này không chạy full S02/S01/B, toàn safety hoặc stress. HEAD/index giữ nguyên; không stage/commit/push. Dừng sửa chờ auditor và người dùng nghiệm thu cuối.
