# Audit độc lập 2A-P3 — dacn-s02 0.4.0a3

Ngày kết luận: 2026-10-23T13:07:27.152423+07:00. **Nghiệm thu kỹ thuật 2A-P3 trong phạm vi local/synthetic đã kiểm. S02-2A-P3-02 đóng; S02-2A-P3-01 tiếp tục đóng. Không có finding mới.**

Đây là mốc hoàn thành P3 để người dùng commit checkpoint. Việc dọn phần sẽ đưa lên GitHub là bước riêng tiếp theo; audit chưa cleanup, commit hoặc push. Không nghiệm thu toàn S02, nghiệp vụ, LLM/live hoặc cấp quyền migration operational/cutover.

## Đối tượng và thay đổi thực tế

Wheel duy nhất: `/Users/macbookpro/Documents/DACN_implementation/reports/s02-phase2/2a-p3-fix02-0.4.0a3-2026-10-23/release/dacn_s02-0.4.0a3-py3-none-any.whl`; SHA-256 `fa50f818ae572d2139daeafb60de2f395b92adddce5c4e18cc4d9de8c3a95214`. Checkout có sẵn dirty state: nghiệm thu ghim wheel/hashes, không lấy Git HEAD thay release. Đọc AGENTS hiện hành, bàn giao, diff, source, tests và các findings trước. AGENTS/README hiện còn trạng thái a2 chờ audit; chưa sửa trong đợt fix hẹp, cần cập nhật navigation hiện hành ở bước cleanup và giữ báo cáo lịch sử nguyên trạng.

Chỉ ba payload Python đổi so a2: version, migration.py và reservation.py. `check_paths` áp dụng policy `writable` cho namespace/marker, chặn source và aliases, symlink components, marker không regular hoặc nhiều hardlinks. Gọi ở constructor, đầu copy/resume trước receipt effects, sau khi lấy shared lock và ngay trước publish. Guard không tự di chuyển, xóa hoặc repair namespace. DDL/schema, registry, L1/E1 validators, repository/CLI và locks giữ bytes.

Auditor tự so 28 function bodies với wheel a2: giữ nguyên toàn bộ AST/thứ tự cũ sau khi bỏ đúng bốn guard calls mới và hai policy arguments của publish; không bỏ invariant khác để làm so sánh đạt. Cơ chế khóa/durability của fix 01 giữ nguyên. Chi tiết đóng findings ở [FINDINGS.md](FINDINGS.md).

## Kết quả thực chạy mới

Mỗi số là mỗi backend C hoặc Python; suites có overlap, không cộng thành coverage độc nhất.

| Bộ kiểm | C | Python |
| --- | --- | --- |
| Bốn oracle P3 nguyên bản | 22 pass | 22 pass |
| Reservation regressions: 34 cũ + 43 mới | 77 pass | 77 pass |
| CLI policy controls có instrumentation subprocess | 14 pass | 14 pass |
| Oracle kiểm biên độc lập thêm trong audit a3 | 4 pass | 4 pass |
| Full S02 trên wheel phát hành | 666 pass | 666 pass |
| Full S01 a6 | 986 pass | 986 pass |

Không fail, error hoặc skip trong các suites trên. JUnit, argv/cwd/environment/exit, encoder counts và observations mới được lưu tại các thư mục tương ứng. Ba venv fresh từ locks offline, cài **đúng wheel phát hành non-editable trước tests**, không dùng rebuild thay candidate và không thêm production source vào Python path. Runtime CPython 3.13.16 GIL/SQLite 3.53.1/macOS arm64. Full C/Python ở hai process riêng; nhóm focused/artifacts chạy song song với full, output/temp riêng.

Oracle CLI lịch sử gọi executable mặc định: lặp trong hai pytest lanes không tự chứng minh backend subprocess. 14 CLI supplement dùng cli_probe hiện hành: 12 exit 3 đúng refusal, 2 exit 0 đúng allowed control mỗi backend, encoder selected có calls và backend còn lại 0. Auditor kiểm trực tiếp observations này.

Full suite chạy lại nguồn mode=ro/hot journal, source lock, eligibility, raw preservation/owner L1, receipt/identity, activation CAS/races, các invariants P1/P2, partial refusal và reservation path policy. Observations mới gồm 3 hot-journal phases, 5 migration kills, 3 activation races, 12 reservation kill cases, 8 migration-first races, fresh-first race, 5 P2 races và 4 P2 process terminations mỗi backend. Hook exceptions và SIGKILL được phân biệt.

## Package, compatibility và evidence

- Differential L1 **thực chạy mới 413/413 outcomes khớp**, giữa phase1 a3, P1 a3 và candidate a3 trên C/Python: 67 accepted/346 rejected. L1 contract nguyên byte so wheel phase1 a3; corpus hữu hạn không chứng minh equivalence mọi input.
- Source–wheel–installed đạt 26 payload S02 và 16 S01, cùng METADATA/WHEEL/direct URL; pip check đạt. Rebuild từ copy sạch khớp toàn bộ 30 ZIP entries, gồm RECORD. Không ép SHA ZIP rebuild trùng artifact lịch sử.
- Đối chiếu đầu/cuối: 161 artifacts bàn giao a3, 101 source/tool/test inputs, bốn oracle nguyên bản, seal/wheel SHA và tất cả producer execution manifests được công bố đều đúng. Giữ 4.111 artifacts bàn giao a2, 8.783 protected files, 125 current-code inputs a2 ngoài bốn file được phép sửa; audit a1/a2 cùng manifest lịch sử không đổi. `integrity-final.json` ghi counts chính xác từng nhóm; các nhóm có overlap.
- Toàn bộ input/artifact hashes trước–sau bằng nhau. Git HEAD đổi trong lúc audit từ `8ec70356999db31dff303f2eea15e46d267d83f2` sang `d1c7dd22726f20e046e6168879fbe6cc15a618e7`, status đổi tương ứng; auditor không thực hiện commit/push. Việc commit không thay source/wheel/oracle/evidence đã pin. Không sửa implementation, dataset, operational store hoặc historical evidence. Các source/sentinel mang tên dataset/checkout trong tests đều là fixture synthetic mới.

Không chạy lại baseline a2 để tái hiện 7 failures trong lượt auditor a3; đó là kết quả mới của audit a2 đã niêm phong và kết quả producer riêng, không tính vào tests auditor mới. Không chạy riêng toàn bộ oracle P1/P2 trong đợt fix hẹp này; các bộ riêng đã chạy ở audit a2, full S02 a3 chạy lại regressions hiện hành. Lỗi setup P2 oracle lịch sử (checked heads ngoài pytest.raises) vẫn là lỗi harness đã ghi nhận, không tuyên bố nguyên file đó đạt trên a3 khi chưa chạy lại.

Finalizer đầu tiên dừng ở assertion yêu cầu cả Git HEAD/status bất biến. Đây là thay đổi Git trong lúc audit, không phải failure của implementation hoặc drift bytes. Script v3 giữ toàn bộ kiểm hash/test/package, tách Git metadata để ghi nhận riêng; các output đã tạo được đối chiếu bằng nhau và giữ nguyên, không overwrite. Lưu script v1/v2/v3, FINALIZATION_NOTE.json, FINALIZATION_NOTE_V3.json và git-during-audit.json. Lượt kiểm seal ngay sau lần dừng chưa thể chạy vì seal chưa được tạo; chỉ kiểm seal thành công sau finalization v3 mới là bằng chứng cuối. V2 dừng ở phép so output JSON đã lưu vì keys số của exit-code được JSON chuyển thành chuỗi; v3 so cùng biểu diễn JSON, giữ nguyên giá trị/assertions và không thay test/production.

## Phạm vi nghiệm thu và giới hạn

Nghiệm thu implementation P3 offline/local: copy DB1→DB2 mới, giữ nguồn chỉ đọc/legacy bytes và identity, receipt/manifest, explicit activation/reconcile, migration lookup và guards; cùng hồi quy fix 01/02 trên fixture synthetic. Baseline P1/P2 và S01 giữ phạm vi nghiệm thu cũ. Audit thiết kế, implementation tested bằng fixture và xác nhận nghiệp vụ không đồng nhất.

**Partial a1 cũ thiếu marker/metadata phải tiếp tục cách ly; không init, retro-fit hoặc tự repair.** Bảo vệ cooperating processes trên filesystem local đã pin, không chống raw SQL/executable cũ, xóa marker, đổi parent inode hoặc di chuyển stores ngoài protocol. Chưa chứng minh hardware power loss, disk-full thật, network FS, performance hoặc authentication người review. Source lock không thay vận hành offline/fencing sau release.

Không cấp quyền 2B/2C, LLM/live, operational migration, tự cutover/config hoặc nghiệm thu toàn S02. Biên bản máy đọc: [S02_2A_P3_ACCEPTANCE.json](S02_2A_P3_ACCEPTANCE.json).

## Bước tiếp theo

Dọn phần codebase đưa lên GitHub theo yêu cầu người dùng: archive evidence kèm inventory/hash/restore trước khi thay tracking; giữ immutable artifacts cần tái lập; thống nhất README/AGENTS/docs hiện hành; bootstrap được từ checkout sạch với artifact bundle đã kiểm hash. Không xóa tests/locks hoặc refactor production trong bước này. Prompt ngắn ở [NEXT_PROMPT.md](NEXT_PROMPT.md). Sau cleanup cần báo riêng mốc sẵn sàng commit/push; hiện mới hoàn tất mốc kỹ thuật P3.
