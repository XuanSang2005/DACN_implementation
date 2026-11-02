# Failures và giới hạn — mốc contract H3-C

Lượt này không có C product code/writer/wheel. Bản dùng để đo diagnostics là B a2 nguyên byte. Không kết luận product C đạt/chưa đạt safety từ diagnostics.

| Backend | Tests | Pass | Failure | Error | Skip | Thời gian pytest |
| --- | --- | --- | --- | --- | --- | --- |
| C | 9 | 8 | 1 | 0 | 0 | 30.745s |
| Python | 9 | 8 | 1 | 0 | 0 | 35.785s |

Failure mới ở `test_H2_scope_request_hash_has_no_H3_binding_definition`, dòng112 file diagnostic bên ngoài repo. Tôi đặt `pytest.raises(S02Error,match='scope_intent_fields')` nhưng `str(S02Error)` H2 chỉ là `H2 pure policy rejected input`; reason được API giữ ở `error.details.reason`. Helper **đã reject** H3 Binding như dự kiến; assertion regex là lỗi harness tôi viết. Không sửa test/giảm assertion/rerun hoặc đổi failure thành pass. Giữ nguyên file nguồn, workspace copy, DBs/logs/JUnit và exit1 cho cả hai backend.

Probe mới `observe_scope_error.py` lấy original Binding từ positive-control observation, ghi cả exception string và structured error. C/Python đều `H2_CONTRACT_INVALID`, stage schema, details.reason=`scope_intent_fields`. Probe có commands/logs riêng, không pytest, không cộng vào counts hoặc thay JUnit. Nó làm rõ nguyên nhân failure, không chứng minh C có implementation hash domain.

Hai Model+A2 positive controls chỉ dựng explicit detached fixture từ existing helpers/canonical validators, giữ old records/events/application count. Không append công việc domain mới, không raw-to-builder fidelity, không persistence writer/hook/recovery/CAS; không coi chúng là E01/E03 runtime C hoặc S5. Một fixture có REPLACEMENT human-reviewed từ synthetic controller; không người thật đã xác nhận.

B full stage2 anchor→AS-only result→publisher→next-config control pass chỉ kiểm B unchanged. Các negatives pass nghĩa là current boundaries được tái lập đúng, không phải C đã vượt gate. New schema snapshot chỉ kiểm cú pháp JSON Schema; chưa kiểm Config/result crosschecks hoặc accepted design semantics C.

Chưa G-C1–4, C safety S1–S6, E18/HR-P Model+A2, actual C publication/replay, wheel C hoặc full S02/S01. Full regression được để tới wheel C cuối ổn định theo yêu cầu, không chạy lại sau từng chỉnh tài liệu. Không LLM/renderer/CLI/live, stress D, operational/data effects hoặc liveness claim.

Audit B a2/finding01 CLOSED là lịch sử đọc từ biên bản;7/7 mỗi backend của auditor và implementer B a2 không trở thành regression C. B a1 full1217/986 và A/H2 counts không phải kết quả mới của lượt này. Không sửa/reseal lịch sử hoặc external oracles.
