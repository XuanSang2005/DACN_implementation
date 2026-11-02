# Failures và giới hạn — H3-C 0.11.0a1

Đây là evidence implementer local/synthetic; không phải audit runtime hoặc nghiệm thu. Mỗi lượt có thư mục mới. Failure cũ giữ logs/JUnit/DB/source snapshots/wheel tương ứng; kết quả sau sửa không thay counts lượt trước.

| Lượt phát triển | Mỗi backend C / Python | Phân loại và xử lý |
| --- | --- | --- |
| pure-r1 | 16 fail | C checked-view phải kiểm lại fixed-point cache hợp lệ; cache sai vẫn reject |
| pure-r2 | 7 pass / 9 fail | H2 parser slot candidate dùng lại giữa command lịch sử. Namespace slot C theo command, giữ shared Budget/counters |
| pure-r3 | 10 pass / 6 fail | Model bất biến còn current-role refs tới ancestor sau AS-only; rebind qua checked lineage cùng key/session, giữ historical refs |
| pure-r4; pure-r5; pure-task-fallback | 16 pass; 40 pass; 1 pass | Khác lượt; mốc pure trước writer là 40+1 distinct controls/backend |
| runtime-smoke-r1 | 1 fail | Harness thiếu thư mục cha DB fixture. Sửa fixture mkdir, giữ assertions |
| runtime-smoke-r2; runtime-effects-r1; safety-smoke-r1 | 1; 8; 8 pass | Focused trên developmental installed wheels; không phải final regression |
| identity-boundaries-r1 | 2 fail | C bug: event ID nội bộ vượt128 ký tự với command hợp lệ dài tối đa; collision set đọc thêm namespace sau T0. Không domain T3 ở ca lỗi, T0 còn pending |
| identity-faults-r2 | 11 pass | Event ID hash có giới hạn; allocation namespace frozen T0. Giữ assertions/caps/timeouts |
| completed-path-r1 | 2 fail | Fixture mapping trống thiếu Issue ref bắt buộc; canonical validator chặn trước C. Thêm Q2/current successor hợp lệ vào fixture, không sửa validator |
| completed-path-r2 | 2 pass | Model+A2 Run completed và T3 lost ACK, bổ sung các đường blocked |
| anchored-tasks-r1 | 1 fail | Harness gán held cho technical construction tasks như câu hỏi nghiệp vụ. Analysis mới phân biệt TaskOrigin đã pin; không bỏ semantic hold |
| anchored-tasks-r2 | 1 fail | C bug: task bước3 đã resolved bị guard khi bước4 thêm Parts. Recheck chính predicate/unit đã pin trên whole current Model, giữ resolution cũ; false predicate vẫn guard |
| anchored-tasks-pure-r3; anchored-tasks-api-r3 | 1; 1 pass | Detached result→publisher→next Config trước API delta; full anchor giữ outputs/task origin qua bước3→4 |
| corrected-recovery/c, python | 1 exit failure/script | Explicit-prepare recovery đã qua assertions/T3/providerless replay; reporter đưa float elapsed_seconds vào exact codec nên encode report bị từ chối. Giữ nguyên scripts/logs/DB đã finalized; read_recovered_identity.py chỉ đọc DB ấy, dùng elapsed_ns integer, không chạy lại recovery |
| recovery-readbacks/c, python | PASS read-only controls | So original failed DB mode=ro, exact config/raw/reserved/times/old records/applications/claims, one seal/finalized event và providerless replay; cả original/copy DB hashes không đổi |
| final-regression/failed-DB-recovery-c, -python | 1 exit failure/script | Control phụ copy DB/receipt nhưng receipt còn bind state_dir cũ. receipt_store_binding từ chối đúng trước T3. Corrected control riêng dùng explicit same-command prepare tạo receipt mới cho bản sao, giữ T0/raw/config/reserved identity; không sửa receipt/validator để vượt gate |

Full S02/S01/tooling và corrected recovery ghi riêng ở kết quả final. Script tổng original vẫn giữ exit failure của hai control receipt; không chạy lại full để đổi aggregate thành pass.

Giới hạn: synthetic/mock, current fresh E1/A2 cùng source, unfinished steps1–4; external historical registry pin toàn store và semantic authority local/synthetic riêng. Chưa đánh giá nghiệp vụ/LLM/provider thật/renderer/CLI H3-D/four-worker hay large-history stress/steps5–9/dataset/operational migration/toàn S02. C không tạo human decision, Answer, application, Validation hoặc TaskAttestation; fixture controller dựng lịch sử synthetic trước C để kiểm.

Limits/Budget giữ nguyên; history hợp lệ quá lớn hoặc contention có thể fail closed. Không hứa liveness mọi contention/caps. Không retry, skip, giảm assertions hoặc tăng timeout/caps để đổi failure thành pass. Legacy regression là kết quả mới trên wheel C; không phải full B a2 hoặc audit độc lập mới. B a2 lịch sử chỉ7 ca/backend trong lượt sửa delta.

Historical cross-snapshot human proof giữ nguyên; thiếu canonical structural from/to identity thì successor undetermined/full hold. V độc lập vẫn có thể tiến với proof; human evidence lịch sử không là quyết định mới. No-anchor actual outputs tiếp tục unassessed/held. Unknown direct pending Answer thiếu proof thu hẹp phạm vi giữ global hold; mixed-current control không ép Model publication.

Các developmental wheels/DBs phải được đối chiếu với đúng source/wheel hash của lượt ấy. Chỉ một wheel C cuối trong delivery là release candidate bàn giao. Không diễn giải kết quả development trên payload cũ thành kết quả của wheel cuối.

Timing: cùng lượt full có khoảng wall-clock gap từ tối01/11 UTC sang03:37 UTC02/11, nguyên nhân không xác định trong scope này. Driver elapsed_seconds giữ nguyên và gồm gap; không dùng nó làm benchmark. Xem TIMING_NOTE.json, timestamps/JUnit/process logs. Không sửa timestamps/caps để làm đẹp thời lượng.
