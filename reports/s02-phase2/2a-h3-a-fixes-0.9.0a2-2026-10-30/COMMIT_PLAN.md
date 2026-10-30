# Commit plan — chưa thực hiện

Người dùng review sau audit; giữ HEAD b0d6ff26c2912c01ceea7a2d8f6a3fa163d3ce57, index không stage. Không reset working tree, không tự commit/push.

Gợi ý message: `fix(s02): bind H3-A progress provenance and typed history checks`.

- Review riêng delta từ working tree a1 tại STATE_BEFORE: h3_bindings/h3_policy/h3_limits/h3_contracts, package/init version0.9.0a2; new fixes controls + corrected E06 fixtures/expectations; current docs/navigation và a2 handoff.
- h3_history/canonical profiles/schemas/registry/DB2/H1/H2/S01/locks và tests/tooling cũ giữ byte. Original auditor oracles/helper và sealed a1 handoff/snapshots/patches/hashes/evidence không đưa vào fix hoặc reseal.
- Delta đầy đủ/snapshot inventory/protected verification được pin trong START_HERE. Toàn diff từ HEAD gồm work hợp lệ có trước a2; không nhầm nó với a2-only delta hoặc dùng `git add .`. JSON/evidence có thể ignored; không force-stage thay người dùng hoặc sửa ignore.
- Raw logs/JUnit/DB/builds/venvs/caches/wheel/manifest/seal ở external evidence; chỉ docs/source/tests được người dùng chọn commit. Không đưa dataset/runtime vào repo.

Các findings vẫn chờ auditor đóng độc lập, người dùng nghiệm thu cuối. Commit không mở H3-B/C/D hoặc operational/LLM/live.
