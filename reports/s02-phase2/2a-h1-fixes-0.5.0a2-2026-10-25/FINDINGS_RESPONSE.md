# Phản hồi S02-2A-H1-01/02 — 0.5.0a2

**Đã sửa, chờ audit lại.** Không tự đóng findings hoặc nghiệm thu H1. Task bắt đầu 24/10, bàn giao 25/10/2026. Căn cứ [audit a1](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/audits/s02-2a-h1-0.5.0a1-2026-10-24/AUDIT_REPORT.md), proposal execution draft.2 và AGENTS hiện hành. Chỉ thay thực thi H1, không H2/H3/LLM/live, không stage/commit/push.

## 01 — finding refs bị bỏ sót

Trước sửa, ref_count chỉ nhận SourceRef/local/base Ref và tên field _id/_ids; finding_handles, questions và finding_handle không được tính. Candidate vượt trần có thể vào linker/build. Mức 50.000 là occurrences, không phải unique handles.

Sửa [h1_limits.py](/Users/macbookpro/Documents/DACN_implementation/packages/s02/src/dacn_s02/h1_limits.py:74): tính len của finding_handles/questions và một occurrence cho finding_handle; giữ SourceRef/typed Ref atomic, không đếm handle/id khai báo hoặc text giống ID. Không đổi defaults, candidate/limits version hoặc codec. Parse vẫn kiểm trước linker; result Model + current Issues vẫn qua cùng guard, gồm issue_ids/source refs và cả keys resolved được chọn.

Trên wheel a1 mới cài: nguyên v3 có 4 pass/6 fail mỗi backend; breakdown đúng là **3 failures parser refs + 2 failures hold + 1 logger failure trước assertions của ca xuyên suốt**. Không phủ nhận finding01: regression xuyên suốt riêng trên a1 chứng minh 50.000 completed, 50.001 **completed sai** và AS head đổi. Raw không vượt byte/value limits, không patch trần hoặc validator.

Sau sửa, v3 parser controls tại 50.000/50.001 đều pass. Ca xuyên suốt v3 vẫn vướng logger tuple nguyên bản; không gọi đó là implementation pass hoặc sửa oracle. Regression mới kiểm đầy đủ: raw giữ byte, 50.000 completed, 50.001 rejected/LOCAL_LIMIT_EXCEEDED(refs), không result pair/head mutation, reopen/resume ổn định. Thêm step3 boundary có **finding_handle đơn** để chống chỉ vá ba dữ liệu audit, mixed refs/declaration/atomic SourceRef và result/current-Issue refs.

Evidence: [baseline v3](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h1-fixes-0.5.0a2-2026-10-24/baseline-oracle-v3/checks/), [fixed v3](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h1-fixes-0.5.0a2-2026-10-24/fixed-oracle-v3/checks/), [baseline xuyên suốt C](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h1-fixes-0.5.0a2-2026-10-24/baseline-ref-integration-c.xml), [Python](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h1-fixes-0.5.0a2-2026-10-24/baseline-ref-integration-python.xml), full regression/new tests và [harness notes](HARNESS_NOTES.md).

## 02 — mượn Issue cũ hoặc mapping task để bỏ qua hold

Trước sửa, force_block chỉ tác động findings mới. Old nonblocking Issue không có blocking scope; pending-mapping có exemption code-owned đến bước4. components() chỉ resolve handle/inventory nên có gap vẫn completed và prepare4 thành công.

Sửa [h1_builders.py](/Users/macbookpro/Documents/DACN_implementation/packages/s02/src/dacn_s02/h1_builders.py:93): bỏ việc thay nghĩa finding được trích dẫn để giữ hold; mỗi unassigned_actions entry tạo **Issue DIRECT analysis_omission riêng**, source refs từ action hiện hành, reason giữ gap, trace.issue_ids trỏ đúng current finding mới/cũ hoặc current mapping task. Issue mới có key riêng và full current Model scope, không được miễn gate của mapping task. Hold này làm Run blocked, next_step=null và không cho prepare4.

Issue được trích dẫn giữ nguyên trạng thái/nghĩa; khi có Model successor vẫn theo lineage hiện có, không sửa record trước. Nếu step3 không có component/responsibility mới thì giữ Model, tạo AS successor + gap Issues. Không tự tạo Review, Answer, consent hoặc sửa semantics/schema E1; không mở partial G2.

Controls mới có local/base/pending-mapping × Model-change/AS-only; kiểm old Records nguyên byte, current issue keys/supersedes, reopen/resume và từ chối bước4. Hai actions dùng chung mapping task vẫn có hai holds riêng. Fully assigned control vẫn completed đến bước4 với verification Issue không chặn còn open, không bị nâng thành hold.

Nguyên v3 cả ba local/base/pending-mapping nay pass ở mỗi backend. New regression giữ controls độc lập với đúng fixture audit; không sửa assertions/helpers của oracle.

## Version và compatibility

Release dacn-s02 **0.5.0a2**, handler pin **s02-2a-h1/0.5.0a2** để prepared work/plan a1 không bị thực thi lại bằng semantics sửa. Candidate/config/plan/limits versions và canonical contract/profile/rules IDs không đổi. Finalized a1 vẫn đọc outcome lịch sử đúng bytes, không reinterpret/repair; unfinalized a1 trả unsupported version, không rebuild/append/finalize. [Proof trên synthetic a1 checkpoints](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h1-fixes-0.5.0a2-2026-10-24/version-compatibility/RESULT.json).

Production delta chỉ h1_limits.py, h1_builders.py, handler version trong h1_candidates.py và package version. CLI/repository, S01, shared L1/E1 validators, schemas/registry, DB2 và locks không đổi. Added tests riêng; các test cũ/conftest/oracles giữ bytes. Diff so **snapshot thực trước task**, không so HEAD thiếu toàn bộ H1 chưa commit. [Diff](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h1-fixes-0.5.0a2-2026-10-24/implementation.diff.patch), [bảo toàn](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h1-fixes-0.5.0a2-2026-10-24/protected-verification.json).

## Phần chưa chứng minh

Chỉ local/synthetic, không chứng minh chất lượng phân tích nghiệp vụ/LLM, renderer, H2/H3, stress vượt matrix H1, power loss hoặc disk-full thật. V3 nguyên bản còn logger failure, auditor cần xem phản chứng và phát hành logger correction riêng nếu muốn ca đó chạy tới assertions; implementation không tự sửa/nới oracle. Timeout harness được báo riêng, không dùng focused retry để viết lại kết quả full.
