# Limits / failures

- Phạm vi đã thực thi: 8 oracle/backend và 23 focused regression/control/backend trên wheel a2 installed noneditable, fixtures local synthetic. Không có build/test failure/error/skip/retry trong lượt sửa này. Không đánh giá nghiệp vụ, LLM, renderer hoặc acceptance.
- Không chạy full S01/S02/B, toàn safety S1–S6 hoặc stress theo giới hạn người dùng. Full/safety a1 và baseline B chỉ là evidence lịch sử; không tuyên bố chúng được chạy mới hoặc pass trên a2. Writer/CAS/canonical không đổi trong delta.
- Raw unread hoặc raw hold/unrepresented mâu thuẫn với usable analysis giữ toàn candidate dưới guard trên base. Không tự giải mâu thuẫn, auto-fill coverage, rebase hoặc ghi completed domain outputs. Compatible scoped U holds được kiểm riêng, không blanket block mọi V.
- Không sửa contract/handler protocol, old tests/oracles/evidence, dataset hoặc DB operational. Không H3-D/CLI/LLM/live, migration hoặc human decision/Answer/application mới.
- Diagnostic đọc evidence phụ có hai lỗi không ảnh hưởng build/tests: thử đọc `package-evidence/summary.json` (collector thực tế ghi `manifest.json`), và peek readback dùng key `head` không tồn tại (readback ghi Run/base/result IDs và `raw_sha256`). Các lần đọc này không ghi dữ liệu hay chạy lại oracle. Không dùng probe setup lỗi `test_audit_c_union.py` làm oracle.
- Findings01/02 vẫn OPEN theo audit a1; candidate sửa gửi re-audit, người dùng nghiệm thu cuối. Không tự đóng findings hoặc chuyển đợt tiếp theo.
