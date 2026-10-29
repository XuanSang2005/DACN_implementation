# Bản đồ expected outcomes H2-C

Các kỳ vọng dưới đây do implementer viết từ topology/source/script synthetic, không gọi thuật toán đang kiểm để tạo expected. Đây không phải audit độc lập hoặc xác nhận nghiệp vụ. Kết quả thực chạy, kể cả failure, xem [TEST_RESULTS](TEST_RESULTS.md).

| Yêu cầu / invariant | Oracle mới và expected |
| --- | --- |
| I1 inventory/unknowns | `test_h2_c_stress.invariant`:17 rows =5 FR ×3 +NFR +constraint, snapshot chỉ thêm schema_version1.0.0 theo S01, supplied actor/criteria/order/nulls giữ nguyên |
| I2 current Issue keys/lineage | Guard open→open successor→resolved successor; business ID/bytes giữ trên AS-only, không Answer/A2, global mapping task vẫn open |
| I3 selectors/unknown | Unknown applicability trên empty graph chặn V6 mới, revalidation không thu hẹp business all_source_uses bằng claim independence |
| I4 fixed point | Chuỗi12 actions trước Parts bằng workflow và sau Parts bằng11 bridges; seed đầu phải tới action cuối. Support required/null/empty có outcomes riêng |
| I5 context negatives | Shared component không kéo scope của V1 vào V2; affected-only khác physical blocker; giữ current V1 và output IDs |
| I6 union/context | New mapping bridge có quyền append vẫn chạm U và guard_required. Part payload/tổng sources giữ nhưng swap row sources/reparent phải tạo impact; sửa proposed row rejected |
| I7 append/retained | Entities, row IDs/source association, Parts đã công bố, output refs giữ byte/nội dung. Candidate mới chạm retained output bị bỏ toàn bộ, không publish phần V2 hợp lệ |
| I8 tasks/gaps | Giữ nguyên các tests H2-B findings và suite hiện hành; global mapping task không resolved khi U còn not_assessed. Không dùng task kind/prefix làm exemption |
| I9 derived assessment | Từng checkpoint có parent assessment SHA, base/result pair, Model hash, output refs. Batches retained V1–V2 và V1–V3 chỉ đổi assessment; cuối trace bốn V current/stage4, U assessed_held/stage1 |
| I10 CAS/identity | Bốn OS PIDs/barrier cùng base; một blocked publication, ba stale. So từng planned domain Record với records thực, stale không có planned Model/Change/Issue/AS; một finalized event/reserved Run/plan |
| I11 selected/global | Bốn V tiến dù U held; mọi semantic successful command vẫn globally blocked. Read-only report không cấp eligibility |
| I12 bounds/integrity | Giữ toàn caps/Budget/conftest/oracles hiện hành, không reset theo unit/phase, không truncate hoặc auto-iterations; full regression và independent historical controls chạy riêng |
| I13 authority | Stale chỉ resubmit tường minh command/current pair/candidate/analysis/approval mới. Old approval không authorize input mới và không tạo T0. Finalized replay providerless không đổi outcome |
| I14 P_guard | Thiếu proof giữ open; đủ proof technical resolve nhưng business hold/global task vẫn tồn tại; bridge candidate cũ không được replay tự động |
| I15 AS-only/current | Retained revalidation không tăng stage/sửa Model/Change; race bốn AS-only publishers giữ Model, chỉ một AS thắng, plan bytes giữ nguyên sau reopen/resume |

Kịch bản23 commands có20 publication: bootstrap1 +inspection1 +bốn V ×3 stage +hai vòng(guard +missing-proof revalidation +complete-proof revalidation). Ba stale có final Run/artifacts nhưng không tính là domain/AS checkpoint thành công. Intake S02 không tính vào ngưỡng20. Bốn V đầu tranh CAS trong bốn process ở build/seal/T3; ba thua phải resubmit riêng. AS-only race là trace khác, seal trước qua handler rồi bốn process mới tranh T3; không đánh tráo hai workload.

Pure graph tests có Dependencies/Support để kiểm closure; chúng không được ghi vào step1–4 stores và không chứng minh đã implement bước5. Mock projections/authority/semantic dispositions đều synthetic. Số passes từ nhóm overlap không cộng thành số unique full suite.
