# 2A-H1 — sửa S02-2A-H1-01/02, dacn-s02 0.5.0a2

**Đã sửa, chờ audit lại.** Chỉ hai findings H1, fresh E1/full scope offline/synthetic. Không tự đóng findings, nghiệm thu H1, H2/H3 hoặc live. Không stage/commit/push.

**Wheel S02 duy nhất để audit:** [dacn_s02-0.5.0a2-py3-none-any.whl](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h1-fixes-0.5.0a2-2026-10-24/final/wheels/dacn_s02-0.5.0a2-py3-none-any.whl).

SHA-256: **012a398d9c3aa3d085508bb8b2a60600a0c8f8211992f2bdd5396e8e618c4f11**.

Đây là byte copy đúng ZIP đã cài non-editable trong môi trường mới; [selection/direct URL proof](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h1-fixes-0.5.0a2-2026-10-24/final-wheel-selection.json), [source–wheel–installed](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h1-fixes-0.5.0a2-2026-10-24/package-evidence-final/manifest.json). Các initial build/rebuild copies chỉ là bằng chứng, không là wheel audit khác.

## Đọc theo thứ tự

1. [Phản hồi từng finding, nguyên nhân/cách sửa/compatibility/giới hạn](FINDINGS_RESPONSE.md).
2. [Kết quả C/Python mới](TEST_RESULTS.md), [FINAL_RESULTS](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h1-fixes-0.5.0a2-2026-10-24/FINAL_RESULTS.json), [instrumentation](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h1-fixes-0.5.0a2-2026-10-24/instrumentation-summary.json).
3. **[Harness notes riêng](HARNESS_NOTES.md)**: timeout worker trong audit a1; logger tuple trong v3; P2 historical setup failure. Không đổi assertions hoặc timeout để làm pass.
4. [Diff so đúng state trước sửa](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h1-fixes-0.5.0a2-2026-10-24/implementation.diff.patch), [before inventory](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h1-fixes-0.5.0a2-2026-10-24/before.inventory.json), [bảo toàn](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h1-fixes-0.5.0a2-2026-10-24/protected-verification.json), [input/code hashes](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h1-fixes-0.5.0a2-2026-10-24/implementation.inventory.json), [patch replay](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h1-fixes-0.5.0a2-2026-10-24/patch-verification.json).
5. [Tái lập vào output mới](REPRODUCE.md), [commands/cwd/env/exit](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h1-fixes-0.5.0a2-2026-10-24/commands/), [evidence index](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h1-fixes-0.5.0a2-2026-10-24/EVIDENCE_INDEX.md).
6. [SHA256SUMS](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h1-fixes-0.5.0a2-2026-10-24/SHA256SUMS), [seal](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h1-fixes-0.5.0a2-2026-10-24/SEAL.json), [Git/index cuối](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h1-fixes-0.5.0a2-2026-10-24/final-git-state.json).

Ref guard tính đủ finding_handles/questions/finding_handle occurrences, giữ inclusive50.000 và SourceRef atomic. Mỗi unassigned-action gap có Issue giữ hold riêng, không mượn nonblocking Issue hoặc miễn trừ pending-mapping; giữ history/current lineage.

**V3 nguyên byte không đạt toàn bộ:** fixed **9 pass + 1 logger failure/backend**. Logger đưa tuple từ Repository.heads() vào exact codec, trước assertions của ca xuyên suốt; lỗi cũng có trên a1. File/hash giữ nguyên. Regression riêng chứng minh baseline50.001 completed sai và fixed rejection/no-publication/raw/head/reopen đúng, có positive50.000. Không tuyên bố v3 đạt10/10 hoặc thay oracle bằng regression.

Full S02 **769 pass/backend**, gồm **103 H1** (18 mới); full S01 **986 pass/backend**, không skip/xfail. Sáu P1 oracle **27 pass/backend**; P2 v2+boundaries **17 pass/backend**, P3 a3 boundaries **4 pass/backend**. Bốn P3 bundle oracle **22 pass/backend** + CLI controls **14 pass/backend**. Differential L1 **413/413 outcomes** bằng baseline a3 trên cả hai backend. Không cộng các bộ có ca trùng thành coverage độc nhất.

Timeout worker **không tái hiện trong lượt full mới**, không có focused retry để viết lại full outcome. Kết quả lịch sử và logger/P2 harness failures giữ riêng trong TEST_RESULTS/HARNESS_NOTES.

S01/locks/canonical schemas/registry/repository/DB2 và evidence lịch sử giữ nguyên byte. Package/handler version mới a2; finalized a1 đọc lịch sử, unfinalized a1 từ chối execution/version, không rebuild bằng handler mới. Mọi evidence vào output mới bắt đầu24/10, bàn giao25/10; [bàn giao a1](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h1-0.5.0a1-2026-10-24/EVIDENCE_INDEX.md) giữ nguyên.
