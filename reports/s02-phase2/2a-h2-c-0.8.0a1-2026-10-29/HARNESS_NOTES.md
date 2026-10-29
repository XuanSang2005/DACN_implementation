# Lịch sử thử nghiệm và giới hạn — không ghi đè failures

Mọi đường dẫn tương đối dưới đây thuộc evidence root trong [START_HERE](START_HERE.md). Toàn bộ fixtures/control approvals/analysis là synthetic. Không gọi kết quả này là audit độc lập hoặc xác nhận nghiệp vụ.

| Lượt | C | Python | Diễn giải |
| --- | --- | --- | --- |
| `focused-v1` |0/2 pass |0/2 pass | Oracle snapshot chưa tính S01 tự thêm schema_version; AS-only race thấy barrier timeout. Bản harness này mới thu stdout/stderr của worker đầu tiên lỗi nên chưa đủ chẩn đoán các worker còn lại |
| `focused-v2` |15/17 pass |15/17 pass | Pure/merge controls pass; oracle stale replay còn so current_head sau khi head tiến. Thu đủ bốn logs đã chỉ ra một AS-only worker hết SQLite lock timeout5s tại seal; ba worker khác hết barrier20s |
| `stress-v3` |2/2 pass |2/2 pass | Workload phát triển U +6 V +NFR/constraint,26 finalized commands/23 publication trong trace chính; AS-only case seal trước rồi bốn process mới tranh T3. Chưa phải snapshot tests cuối cùng |

Không tăng timeout/caps, skip/xfail hoặc sửa oracle lịch sử. Hai sửa oracle mới: snapshot expected thêm schema_version1.0.0 theo contract S01, và replay so outcome bất biến riêng với current_head/is_current quan sát tại lần đọc. Bản harness mới luôn join/thu diagnostics cả bốn workers và ghi phase times. Các failures ở trên vẫn nguyên log/JUnit/DB/input hashes; không đổi thành pass.

`failed-race-readback/READBACK.json` đọc trực tiếp SQLite mode=ro trên copies của bốn DB AS-only lỗi: mỗi DB có4 command chưa finalized,3 plan sealed và1 chưa seal; không promotions, không planned domain Records và head vẫn ở base. Hash nguồn kiểm trước/sau. Đây là bằng chứng không publication ở các snapshots ấy, không phải rerun pass và không khẳng định mọi trường hợp lock contention sẽ tự hoàn tất. `focused-v1` thiếu log worker thứ tư nên không tự gán nguyên nhân chính xác; chẩn đoán SQLite lock timeout có log đầy đủ ởv2.

AS-only test cuối **seal từng plan qua handler trước**, rồi bốn process mới resume đồng thời tới T3. Trace domain vẫn chạy build/seal/T3 trong bốn workers. Phân biệt hai workload này: không quảng cáo AS-only là bốn concurrent builders hoặc tăng timeout để đạt. Concurrent-seal ở trạng thái lớn có thể fail closed; caller phải xử lý pending work tường minh, không auto-rebase/resubmit stale.

Trong `stress-v3`, max worker resume quan sát được khoảng28,77s C và29,33s Python, gần Budget30s. Đây là wall time có instrumentation/barrier, không SLA hoặc benchmark CPU. Để kịch bản chính bám ngưỡng yêu cầu và kiểm lifecycle guard sâu hơn, snapshot cuối dùng U +4 V +NFR/constraint,17 obligations và **hai** vòng guard/missing-proof/complete-proof:23 finalized commands, đúng20 publication và3 stale. Batches retained V1–V2 rồi V1–V3 trở lại current; cuối trace bốn V stage4/current, U stage1/held. Workload sáu V giữ nguyên kết quả riêng, không bị thay thế bằng workload nhỏ hơn rồi gọi cùng một kết quả.

Full lịch sử H2-B do auditor báo vẫn C959/959, Python958/959. V01 xác minh safety không phải full pass mới. Full H2-C, S01 và external original oracles phải đọc riêng ở [TEST_RESULTS](TEST_RESULTS.md), không cộng những nhóm overlap thành unique full suite. Original P2/H2-A harness diagnostics đã biết cũng giữ nguyên file/hash/assertions và báo kết quả riêng.
