# Failures, giới hạn và những phần chưa chạy

Evidence root được pin tại START_HERE. Mọi JUnit/log/DB của các vòng dưới giữ nguyên; không biến precursor hoặc aborted run thành pass của wheel delivery.

| Lượt | Kết quả thực đã ghi | Disposition |
| --- | --- | --- |
| Focused v1 | C 57 pass/20 fail trên77; Python57/20 trên77, no skip | Các controls mới có kỳ vọng regex reason chưa có trong diagnostics H3; fixture positive dùng initiator unknown; projection test so toàn carry dù current to_scope phải rebind; stale-binding negative cố đổi raw trong cùng immutable slot. Thêm reason vào diagnostics, sửa fixtures/expected typed-path claims đúng contract, dựng stale tuple trước first parse. Không sửa assertions/tests cũ/caps |
| Focused v2 | C94 pass/1 fail trên95; Python94/1 trên95, no skip | Existing-target fixture successor đổi source-only resolution prose; policy từ chối đúng. Sửa fixture giữ nguyên kind/scope/resolution meaning cho target cũ, không nới policy |
| Focused v3 | 99/99 mỗi backend | Precursor payload, chưa phải wheel delivery. Sau review bổ sung strict UTF-8 JSON (kể cả UTF-16-no-BOM), trust tuple counters và bounded origin-plan/config parsing |
| Focused v4 | 99/99 mỗi backend | Precursor trước phần bounded origin-plan/config parsing. Full v4 bị dừng bằng SIGINT để rebuild payload cuối; `PROVISIONAL_FULL_V4_ABORTED.json` ghi rõ. Partial logs/JUnit/DB còn, không full pass, Python full chưa được count |
| Delivery v5 | Focused99/99 mỗi backend; regression và gates cụ thể tại TEST_RESULTS/START_HERE | Đây là payload authoritative duy nhất, source–wheel–installed được kiểm riêng, không dùng counts lịch sử làm kết quả mới |

Các lỗi v1/v2 là trong implementation/controls mới của đợt này, không findings auditor đã đóng. Logs/JUnit thật được giữ, không retry vào cùng output/basetemp hoặc xóa failed evidence. Source/tests/locks/historical evidence có trước lượt được kiểm hash; chỉ source/version/docs mới thuộc scope A được sửa. Không skip/xfail/hạ assertions hoặc tăng timeout/caps.

Giới hạn:

- Đây là pure local/synthetic H3-A. Whole-graph data validation không thay checked DB/store lookup, active/fresh profile guard, receipt/head identity, filesystem loader hay Repository factory. Chưa có H3 CLI/work writer, seal/CAS/restart publication runtime B/C.
- Registry chỉ nhận bytes/data + external typed trust tuple; all-store R cố định. Không suy reviewer/assessment từ DB hoặc dùng semantic authority thay registry; không real authentication/network/UI. External human-decision growth không có online upgrade/recovery trong scope này.
- CARRY not_applicable thiếu target hợp lệ vẫn chặn Model transition; incomplete/undetermined giữ hold. Không tạo first human replacement complete, Answer/application/source switch hoặc current task evidence mới để lách blocker.
- No-anchor không suy stage; private shape chỉ là shape. Progress/anchor/task/guard cần provenance checks, không tự coi metadata SHA đúng là semantic independence. H3-A không sinh canonical successor/IDs/Run; canonical candidate/proof builder và raw-to-builder fidelity thuộc C.
- Bounds/shared Budget cooperative, không hard I/O/CPU timeout/liveness/performance SLA. Thời gian wall-clock của các runs có khoảng gián đoạn lớn; không dùng làm benchmark hoặc gán nguyên nhân khi không có bằng chứng hệ thống.
- E20/E21/E25 H3 runtime chưa chạy; safety gates B-AS/C-Model+A2 §7.1 vẫn cần thực thi đúng đợt. H2 native fixtures và regression runtime cũ không thay proof safety H3 mới.
- Không chạy external historical audit oracle sets P1/P2/P3/H1/H2-A/H2-B trong đợt A; original oracles/files/assertions giữ nguyên, không phân loại chúng pass mới. Không benchmark semantic quality/LLM/renderer/live, physical power-loss, operational migration/cutover hoặc dataset evaluation.

H3-D01/D02 đóng **design-only** theo audit draft.2; implementation H3-A chờ auditor kiểm độc lập và người dùng nghiệm thu. Quan sát H3-I01 về NEXT_PROMPT draft.1 được giữ, không restore/reseal hoặc dùng file đó làm authority.
