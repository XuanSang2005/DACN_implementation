# H3-B — contract delta cần audit trước writer

**Chưa implementation/wheel/runtime H3-B.** Đã chốt hồ sơ nghiệm thu H3-A theo quyết định người dùng và tái lập một khoảng trống result-assessment trong private checks A a2. Theo gate người dùng “Nếu cần đổi contract đã chốt, trình delta để audit trước khi dùng trong writer”, lượt này dừng trước writer phụ thuộc; không tự thay contract để triển khai B.

- [Proposal delta B-P01 draft.1](../../../docs/S02_2A_H3_B_CHECKPOINT_CONTRACT_DELTA_PROPOSAL.md): vấn đề, version/API/result-assessment/parent chain, giữ stage provenance và controls trước writer; **PROPOSED**, chưa audit/accept.
- [Nghiệm thu A a2](../../../docs/acceptance/s02-2a-h3-a-0.9.0a2-2026-10-31/README.md): auditor đóng findings01/02/03; người dùng nghiệm thu pure local/synthetic. Auditor focused129/oracle13/controls8 mỗi backend; implementer full1106/986 supporting, không auditor full.
- [I02 đối soát riêng](I02_RECONCILIATION.md): cleanup ngoài A release, HEAD hiện đã chứa; không rollback hoặc gộp vào nghiệm thu A.
- [Coverage/safety](COVERAGE_MATRIX.md), [reproduce](REPRODUCE.md), [limits/failures](FAILURES_AND_LIMITS.md), [commit plan](COMMIT_PLAN.md).

**Kết quả mới của implementer:** 3/3 diagnostics mỗi backend C rồi Python, 0 failure/error/skip, venv mới offline/non-editable, exact release a2. Hai cases xác nhận mismatch giữa check_plan/admission và reader publisher; một existing H2 full-anchor positive. Pass ở đây nghĩa là phản chứng tái lập đúng, **không phải B đã sửa hoặc đạt safety**. Không H3 writer/CAS/resume test nào được nhận từ setup H2. Không chạy full/regression mới khi code production không đổi.

Evidence root: `/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h3-b-contract-review-2026-10-31`.

`test_h3_b_contract_diagnostics.py`, `DIAGNOSTIC_COMMANDS.json`, diagnostic-c/python.log, diagnostics/{c,python}/junit.xml + DB/sidecars, environment build/package logs, STATE_BEFORE, final inventory/diff/static checks, MANIFEST/SEAL nằm tại root đó. Runtime/venvs/cache được exclude rõ trong seal. Marker AUDIT_READY ở đây có scope **CONTRACT_DELTA_ONLY**, không H3-B implementation-ready.

Wheel được dùng để tái lập là **A a2**, 183910 bytes, SHA `483c9b960c481653b35c0efbae0d5c194d46e6d6895790e69205dbb193ad0e15`; không phát hành version/wheel B trước khi delta qua gate audit. Production/tests/locks/canonical/H1/H2/S01/proposal/handoffs cũ giữ nguyên byte so baseline đầu B. Baseline audit `b0d6ff2`; HEAD hiện `9a1a44e`, không reset. Không stage/commit/push, LLM/live/dataset/H3-C/D/CLI.

**Bước cần review:** auditor kiểm B-P01 và diagnostics, người dùng chốt delta; sau đó mới triển khai B theo toàn gates §7.1. Ba findings A đã đóng không bị tự mở lại; đây là contract gap của path runtime B chưa được A nghiệm thu.
