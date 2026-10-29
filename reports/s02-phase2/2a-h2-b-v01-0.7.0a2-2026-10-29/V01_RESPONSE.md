# S02-2A-H2-B-V01 — kết luận implementer

**Đề nghị auditor xem xét bằng chứng bổ sung và harness mới; giữ V01 chờ quyết định độc lập. Không kết luận production có lỗi persistence/identity mới, cũng không chứng nhận full gate sạch.**

## Đã xác minh

1. Stack lịch sử: H2Service.resume → report sau finalize → ScopeStore.published_plan → primary/config cap → Budget.check. PERSISTENCE_FAILED bọc H2_LOCAL_LIMIT. Tổng thời gian test85.099s không phải thời gian Budget30s. DB từ chính lần full fail không có trong evidence còn lại.
2. File release-boundary nguyên byte chạy với timing wrappers gọi hàm gốc đúng một lần, return/rethrow nguyên kết quả:3/3/backend. Caps, timeout worker45s/barrier20s, race concurrency/assertions giữ nguyên. Wrappers chỉ ghi timing vào RAM trong invocation; snapshots ở ngoài invocation, trước tạo Budget hoặc sau return/raise. Đây là đo có instrumentation, không phải benchmark không overhead. Mỗi resume tự nhiên đúng một Budget; report dùng tiếp Budget ấy.
3. C recovery invocation:3.193s wall/3.186s CPU, report0.672s. Python:21.866s wall/21.833s CPU, report4.677s. Python vào report ở17.189s; report load2.173s, published_plan2.504s. Seal7.169s, build3.206s, finalize2.610s. Các hàm lồng nhau đo inclusive, không cộng chồng. Wall gần CPU trong lượt mới không giải thích scheduling/nhiệt của lượt cũ.
4. Hai control wall-clock/backend dùng bản sao byte-for-byte hot DB+journal từ crash fixture gốc, giữ40actors×12.000ký tự/store/command/reserved ID. Không fake journal. Read-only/wrong-store đều từ chối, giữ bytes. Một control chờ hết deadline tại after_seal; một chờ tại đầu published_plan sau finalize, tái hiện đúng nhánh primary/config cap của stack lịch sử. Đồng hồ thực monotonic, đúng một Budget30s; sleep hữu hạn tới deadline+0.05s, không reset/tăng cap.
5. DB được lưu ngay sau exception **trước mọi checked readback**. Repository mới verify, ScopeStore với Budget của phép đọc mới. Trước publication: head[null,null], chưa finalized, một sealed plan, output IDs chưa có. Sau publication: head đúng planned pair, reserved Run duy nhất, một finalized event. Fresh report không đổi bytes; fresh resume/replay giữ plan bytes/hash, primary config hash, raw hashes, Run/command/head. Control sau publication giữ cả DB hash. Retry là invocation mới đúng contract, không reset Budget trong invocation cũ.
6. Hai oracle deadline auditor copy nguyên byte chạy mới2/2/backend, kiểm non-null analysis raw step1 và plan/identity/history. Control chết trước ghi đạt1/1/backend: không hot header, DB giữ bytes, progress thấy prepared/no plan/no head, retry giữ reserved ID.
7. Harness nhỏ hơn đạt hai CAS và hot recovery3/3/backend;10 assert AST gốc nguyên vẹn. Fixture40×2.000ký tự; worker seal cache32pages×4096bytes; crash thực trước COMMIT. Hot header/readonly refusal/wrong-store refusal/bytes/final plan+event+Run đều bắt buộc. Python recovery4.228s/report0.889s; C1.056s/report0.222s. Không đặt ngưỡng performance mới.

## Phân loại và giới hạn

Bằng chứng ủng hộ **hạn chế của cách fixture cũ ép journal bằng payload lớn**: nó đồng thời tiêu tốn nhiều Budget trong whole-state/model/plan checks. Có thể kiểm invariant crash/recovery với workload nhỏ hơn và hot journal được kiểm trực tiếp. Harness mới là đề xuất cho gate chuyên biệt, không thay full, không bỏ bài tải lớn: bản gốc/số đo vẫn được giữ.

Chưa có cơ sở sửa production chỉ để test xanh. Deadline sau commit là nhánh ACK/report thất bại có thật; code không trả thành công giả, retry giữ publication identity. Nhánh chèn delay đã được đọc DB trực tiếp; **không phải DB của lần full fail cũ**, delay nhân tạo **không chứng minh nguyên nhân tự nhiên cũ**. Không kết luận chỉ do nhiệt/scheduler/encoder; không đo riêng từng codec call và không có telemetry lịch sử.

Giữ a2 nguyên byte. Không rerun full vì không có production delta và mục tiêu là chẩn đoán/kiểm recovery có kiểm soát. Auditor/người dùng cần quyết định chấp nhận harness đề xuất và giới hạn thiếu DB lịch sử, hoặc giao gate bổ sung. Đợt này không tự đóng V01/nghiệm thu.

[RESULTS.json](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-b-v01-0.7.0a2-2026-10-29/RESULTS.json) dẫn tới traces wall/CPU/JUnit/bốn readbacks. [wall-deadlines-v3](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-b-v01-0.7.0a2-2026-10-29/wall-deadlines-v3) có traces/after_seal-readback và traces/published_plan-readback mỗi backend: hot-before, deadline-before-any-readback, sealed-plan.bin, after-fresh-retry, readback.json. Copy DB/journal sang workspace mới trước khi mở; không ghi snapshots đã seal.

## Pha phát hiện deadline trong controls mới

[PHASE_DEADLINES.json](/Users/macbookpro/.codex/.chatgpt-projects/g-p-68c38c8799f48191a101e19a975ca4f9/outputs/implementations/s02-2a-h2-b-v01-0.7.0a2-2026-10-29/PHASE_DEADLINES.json) giữ stack và mốc đầu tiên ném exception. Sau seal: primary/config cap ở30.224s(C),30.930s(Python), sau phần checked load; chưa publication. Sau finalize: primary trong published_plan ở30.053s(C),30.053s(Python); đúng một publication đã tồn tại. Các mốc tính từ Budget creation, không từ đầu test. Đây là hết hạn có sleep chủ đích, không tái hiện tự nhiên failure full lịch sử.
