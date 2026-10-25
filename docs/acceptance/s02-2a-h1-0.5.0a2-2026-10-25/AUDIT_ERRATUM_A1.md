# Đính chính phân loại một failure trong audit H1 a1

Ngày 25/10/2026. Đính chính báo cáo audit độc lập `dacn-s02 0.5.0a1` ngày 24/10, do auditor lập. Giữ nguyên báo cáo, oracle và evidence lịch sử; văn bản này bổ sung cách đọc đúng các kết quả đó.

Oracle V3 nguyên byte có 4 pass và 6 fail/backend trên a1. **Một trong sáu failure là lỗi logger của auditor**, không phải assertion phát hiện lỗi implementation: `test_over_ref_limit_keeps_raw_and_rejects_without_publication` truyền `head_before/head_after` kiểu tuple vào exact JSON encoder. Encoder từ chối tuple đúng contract trước khi chạy các assertions về rejected/head. Năm failures còn lại là ba parser refs và hai hold/admission failures của implementation.

Báo cáo a1 đã diễn giải cả sáu failures của V3 thành failures implementation, và nói V3 đã thực thi tới assertions xuyên suốt. Phần phân loại này không chính xác. Tôi nhận trách nhiệm về lỗi logger và cách diễn giải đó. S01 codec, Repository.heads() và oracle lịch sử không cần bị thay đổi để làm phép kiểm pass.

Oracle V4 trong thư mục audit a2 chỉ chuyển hai tuple thành list tại lời gọi ghi evidence. Không đổi input, production hoặc assertions; so AST xác nhận tất cả assertions giống V3. Diff hai dòng và hashes ở `oracle-v3-v4.diff` / `oracle-correction.json`. V3 nguyên bản vẫn được chạy riêng và giữ nguyên SHA-256 `9b7d8379a6551e1bc4c868cf46e98b1de47940010346b83ce7a9fccb766e3f9e`.

Lượt chạy độc lập mới trên wheel a1, môi trường mới, cho V4 4 pass/6 fail ở cả C/Python. Lần này ca xuyên suốt đi qua logger và fail đúng assertion `completed != rejected`: candidate có đúng 50.001 ref occurrences đã công bố AS head. Vì vậy finding S02-2A-H1-01 vẫn có căn cứ; lỗi logger không phủ định lỗi implementation, nhưng không được dùng failure logger như bằng chứng assertion. Kết quả bản sửa a2 nằm trong báo cáo audit mới và logs riêng.

Lỗi timeout migration trong full Python a1 và lỗi setup P2 lịch sử là các mục khác, không liên quan tuple logger. Không viết lại kết quả full/historical dựa trên retry hoặc bản sửa oracle.
