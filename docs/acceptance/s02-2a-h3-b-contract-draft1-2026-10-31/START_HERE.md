# H3-B B-P01 draft.1 — PASS thiết kế, chưa runtime

**Chấp nhận thiết kế tách stage/output provenance khỏi checkpoint result assessment, B checker/parent chain/versioned semantics riêng.** Người dùng chốt B-P01 trước implementation phụ thuộc. Chưa có B checker/writer/wheel/safety được nghiệm thu; H3-A findings01/02/03 không mở lại.

- [AUDIT_REPORT](AUDIT_REPORT.md): luận điểm, giới hạn và **G1–G4 trước writer/safety**. Pure round-trip + version/authority separation + T0 dependency checks phải có trước writer.
- [Prompt tiếp tục B](NEXT_PROMPT.txt): để người dùng gửi, chưa dispatch.
- Auditor tự tái lập **3/3 diagnostics mỗi backend C/Python**,0 pytest failure/error/skip; [commands](DIAGNOSTIC_COMMANDS.json), [C log](diagnostics/c/pytest.log), [Python log](diagnostics/python/pytest.log). Pass nghĩa confirmed contract mismatch trên unchanged A a2, không B runtime pass. [Launcher erratum](LAUNCH_ERRATUM.txt) là lỗi locator trước pytest của auditor, không bị che thành zero attempts.
- [Input verification](INPUT_VERIFICATION.json):869 entries/431 final files khớp; [static](STATIC_VERIFICATION.json):277 links; [package](PACKAGE_VERIFICATION.json):accepted wheel A a2 nguyên bản, source–wheel–installed khớp. [Proposal snapshot](proposal-draft1.snapshot.md).
- [Final integrity](FINAL_INTEGRITY.json), [manifest](MANIFEST.json), [seal](SEAL.json).

Proposal SHA `5ec9de7796faf7b752b04dfdf2c167896990abe910e72e05ab4d3f8652dc0a02`. Current HEAD9a1a44e giữ nguyên; source/tests/locks/history không sửa. Không B implementation, stage/commit/push/automation/dispatch/LLM/live hoặc operational/dataset writes. User quyết định cuối.
