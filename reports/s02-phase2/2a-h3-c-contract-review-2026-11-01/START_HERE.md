# H3-C — mốc contract trước writer

**CONTRACT_DELTA_ONLY, chờ audit C-P01; chưa có implementation/wheel C.** Đã đọc AGENTS/H3 §3–7.1 và E01–E24/B-P01/baseline B a2/audit B a2, kiểm đúng HEAD `9a1a44e8bebccda085604dc371b91c2db33b08f1` và giữ457 files working tree có trước lượt này nguyên byte. Không reset/stage/commit/push.

[Delta C-P01 draft.1](../../../docs/S02_2A_H3_C_CONTINUATION_CONTRACT_DELTA_PROPOSAL.md) đề nghị dispatch draft.4, exact B→C parent bridge, C authority/hash domain riêng, raw projection/result-stage checks và C guard origin không self-hash. C cần các semantics này trước pure result→publisher→next-command round-trip và writer. **PROPOSED**, không tự chấp thuận bởi việc người dùng đã giao scope C. Gate người dùng yêu cầu audit delta trước implementation phụ thuộc được giữ; không nới validators A/B/A2/H2.

Đã thực chạy diagnostics mới trên **B a2 nguyên byte**, fresh venv offline ngoài checkout, cài chính release ZIP non-editable. C rồi Python tuần tự, mỗi backend **9 tests:8 pass,1 failure,0 errors/skips**. Failure nằm ở regex của test diagnostic mới cho `S02Error`, reason thực ở structured details; giữ nguyên failure/test/log/JUnit, không sửa assertion hoặc rerun để xanh. Probe riêng xác nhận controlled rejection `scope_intent_fields`, không tính thành pass. [Failures/limits](FAILURES_AND_LIMITS.md).

Hai detached canonical controls Model DIRECT→CARRY và REPLACEMENT complete đã pass; không append domain output và không C builder/writer/safety. B AS-only result→publisher→next-config positive pass. Các boundary negatives xác nhận checker hiện hành từ chối step/self-claimed stage/relabelled parent/C guard predicate; không mở lại findings A/B đã đóng.

[Coverage matrix](COVERAGE_MATRIX.md) tách diagnostics đã thực thi với **G-C1–4/E01–E24/S1–S6 C chưa chạy**. [Reproduce](REPRODUCE.md) ghi commands/baseline/tooling; [review/commit](REVIEW_AND_COMMIT.md) giữ B working tree và điểm dừng. Chưa chạy full regression: không code production đổi, wheel C chưa đến mốc cuối ổn định. Không dùng7 ca B a2 hoặc counts B a1/A/H2 làm kết quả mới C.

Evidence root: `/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h3-c-contract-review-2026-11-01`.

Trong root có `STATE_BEFORE.json`/snapshot457 files, `WHEEL.json`, `SETUP_COMMANDS.json`, `DIAGNOSTIC_COMMAND.json`, `diagnostics-round1/commands.json`, C/Python logs/JUnit/fixture DBs/observations, `c-SCOPE_HASH_OBSERVATION.json`/Python tương ứng, `contract-draft1/C_PRIVATE_SCHEMA_DRAFT1.json` và syntax-check. Schema snapshot chỉ là **đề nghị review fields**, không product validator/capability; chưa behavioral-check G-C. `FINAL_INTEGRITY.json`, `HISTORICAL_MANIFEST_VERIFICATION.json`, diff/snapshot/MANIFEST/SEAL/SEAL_CHECK và marker ở cùng root. Những files tổng kết/marker chỉ có giá trị sau khi được ghi và verify cuối lượt.

Wheel dùng cho diagnostics vẫn **dacn-s02 0.10.0a2**,209806 bytes,SHA256 `5cf7079763a13da5bf58145f9cccf076934f116edb8c45e5c750718cbdfb8ce0`; không gọi nó là wheel C.58 ZIP entries bằng hai copied-source rebuilds; source–wheel–installed/direct URL/pip check đạt. S01 rebuild20 entries bằng accepted a6 trước same-version replacement. Không chạy suite S01 hay full S02 mới.

Mốc này sẵn sàng để **review/audit delta contract**, chưa sẵn sàng nghiệm thu implementation C. Sau auditor/người dùng chốt C-P01 mới tiếp tục code phụ thuộc và toàn safety Model+A2 ngay C, rồi wheel/full cuối. Không H3-D/CLI/four-worker stress/live, new human decisions/Answer/application/source switch/completed-output edits, dataset hoặc migration operational.

MANIFEST→SEAL→SEAL_CHECK được kiểm trước `AUDIT_READY`; marker có scope **CONTRACT_DELTA_ONLY** và là lần ghi cuối evidence root. Dừng sửa sau marker, chờ audit delta. Không tự nghiệm thu C.
