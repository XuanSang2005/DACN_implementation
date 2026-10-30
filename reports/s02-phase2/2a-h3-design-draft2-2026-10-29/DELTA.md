# Delta draft.1 → draft.2 — phạm vi docs-only

Proposal version tăng từ `s02-2a-h3-history/0.1.0-draft.1` sang `s02-2a-h3-history/0.1.0-draft.2`. Private H3 config/plan/admission markers đề nghị tăng draft.2 vì thêm historical_reviews_pin; protocol registry mới có version riêng `s02-h3-historical-reviews/0.1.0-draft.1`. Không phải package release hoặc đổi canonical schemas/DB2/registry/locks.

1. D01: thêm §2.3 chọn concrete file protocol/API/trust tuple, all-store required Issue-ID registry/dependency hashes, canonical digest verification, loader trước checked read, T0/intent/plan pins và immutable lifetime; walkthrough HR-P + negative outcomes. Cập nhật preconditions, checkpoint/envelopes/E18 và D1/D2/D4/D5.
2. D02: §6 E20/E21 phân bổ bắt buộc B-AS/C-Model+A2; §7 gates tương ứng và §7.1 S1–S6 quy định core processes/phase/fault/DB oracles, effects classes và replay. D chỉ mở rộng CLI/four-worker/stress. Có harness/case reuse mapping, không chạy hoặc sửa tests.
3. Navigation `AGENTS.md`, root/docs/S02/reports README chỉ đổi nhãn H3 draft.2 và thêm handoff mới/trạng thái chờ audit. Hồ sơ H2-C, H2-B/V01 và toàn handoff draft.1 giữ byte. Không reset working tree, không discard docs hợp lệ cũ.

Các quyết định còn chờ:

- D1: entry riêng/fresh E1 cùng nguồn, bắt buộc external registry tuple trước inspect/read, không generic bridge.
- D2: structural-only, registry do trusted caller pin ngoài DB, inventory toàn store và **R cố định khi pending**. Nếu external writer tạo historical human-review Issue mới thì invocation fail closed; không hỗ trợ online registry upgrade cho command cũ trong scope này. Không tự giải quyết điều kiện đó bằng decisions từ DB.
- D3: append công việc chưa xong/giữ output có evidence, không domain repair hoặc fake stage.
- D4: private envelopes/pins/loader và safety E20/E21 ngay writer B/C; closed schemas/error mapping cụ thể hóa trong H3-A sau audit/người dùng giao riêng.
- D5: registry ≤1MiB, all-store history/entry ref occurrences trong cùng caps/Budget, không nới limits/liveness claim.

[DRAFT1_TO_DRAFT2.patch](DRAFT1_TO_DRAFT2.patch) gồm đúng proposal + navigation sửa trong lượt này; phần before của navigation tái dựng từ HEAD và patch draft.1 rồi đối chiếu SHA với STATE_BEFORE trước khi diff. Không dùng HEAD làm “before draft.1” của proposal untracked. Mọi file mới của handoff này được inventory riêng trong MANIFEST; patch loại chính handoff để tránh tự tham chiếu.

Không tự đóng D01/D02, không gắn trạng thái đã audit hoặc người dùng đã phê duyệt D1–D5. Dừng ở bàn giao draft.2 chờ auditor. Không stage/commit/push hoặc chạy suites/build/LLM/live.
