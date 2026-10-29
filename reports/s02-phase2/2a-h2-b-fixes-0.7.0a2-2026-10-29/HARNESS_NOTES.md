# Nhật ký kiểm chứng bản sửa

- Baseline và audit inputs được giữ; dùng oracle chính publication gate và batch/history **v2**. Không dùng v1 có kỳ vọng telemetry sai hoặc Part draft chưa chạy làm gate chính.
- Focused v1: hai oracle chính 7/7 pass/backend; regression mới phát hiện một failure/backend ở affected-context control. Đây là lỗi chặn quá rộng trong implementation thử nghiệm, không phải lỗi oracle/harness. Bản sửa phân biệt source inspection bước 1 với retained domain output, giữ assertions và log cũ. V2 thêm ca kiểm counters và chạy lại; kết quả thực tế ở TEST_RESULTS.
- File test repo dùng làm focused oracle được copy nguyên byte ra ngoài checkout, giữ hash. Dùng E1 adapter/helpers để tránh lỗi nạp conftest hai lần đã được auditor ghi ở HARNESS_NOTES gốc. Không sửa fixture/assertions/conftest lịch sử.
- Expected-wheel là absolute path; collector delivery dùng cùng ZIP đã cài, giữ source–wheel–installed/direct URL assertions. Runner full S02 chỉ tee stdout ngoài checkout, có diff/hash, không đổi argv/assertions/timeout.
- Oracle P2 original chạy mới tái hiện đúng lỗi gọi checked heads() trước pytest.raises; original H2 limits chạy mới tái hiện hai lỗi accessor `.value.code`. TEST_RESULTS/JUnit ghi outcome thực tế: P2 16 pass/1 fail, H2 limits gốc 2 pass/2 fail mỗi backend; corrected/current boundary oracles đạt. Các expected harness failures không được đổi thành pass.

Không tăng timeout, skip/xfail/retry, reset Budget/caps hoặc sửa oracle lịch sử để viết lại outcome.
