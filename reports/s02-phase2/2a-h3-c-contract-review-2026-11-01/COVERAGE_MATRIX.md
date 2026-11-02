# Coverage — contract diagnostics khác implementation C

Chỉ cột diagnostic là kết quả đo mới. G-C/E/S bên dưới là **kế hoạch phải thực hiện sau chốt C-P01**, không test pass hoặc proof implementation. Backend counts giữ8 pass/1failure mỗi backend, không tổng hợp probe thành pass.

| Diagnostic mới | C / Python | Điều đã quan sát / giới hạn |
| --- | --- | --- |
| Existing B result→publisher→next Config | PASS / PASS | Full H2 stage2 anchor, B AS-only, exact parent; không Model C |
| B Config và Binding step/build | 2 PASS / 2 PASS | Reject `b_as_only_mode`; approval AS-only không cấp step |
| A nhận B parent/relabel B parent | PASS / PASS | Original version reject, relabel vẫn reject progress provenance; bytes B giữ |
| A self-claimed completed stage | PASS / PASS | Shape-valid claim không thay provenance; không công việc C thật |
| H2 scope hash với H3 Binding | FAIL / FAIL harness | Regex mismatch; structured probe riêng controlled rejection details.reason=scope_intent_fields; không sửa counts |
| H2 guard control/C predicate/null own hash | PASS / PASS | H2 positive, C predicate và null hash unsupported; self-hash dependency minh họa được ghi, không chứng minh fixed point bất khả về toán |
| Canonical Model DIRECT→CARRY | PASS / PASS | Detached existing fixture/validator, root/from/old application bất biến; không append output/C writer |
| Canonical Model REPLACEMENT complete | PASS / PASS | Detached structural continuation, current target/obsolete/root; không C handler hoặc new human decision |

| H3 matrix | Coverage C bắt buộc sau contract | Trạng thái C hiện tại |
| --- | --- | --- |
| E01–E05 | New output trên DIRECT/applied/multihop/same-current-snapshot historical switch/REPLACEMENT/source-only/Answer pending; planned→actual records, current refs | NOT RUN C; canonical controls chỉ supplementary |
| E06/E19 | No-anchor existing output stage0/unassessed/held; full verified B→C chain; fake/omitted/raw/parent/progress hashes reject, no overwrite | NOT RUN C |
| E07–E10 | Missing coverage→canonical held proof; malformed/false/skipped/cycle/stale reject; pending không auto release | NOT RUN C |
| E11–E14 | not_applicable target/no-target guard; incomplete không first complete; wrong/historical/chained/same-key target và source mismatch reject | NOT RUN C |
| E15–E17 | Part–row–source/context swap vs set reorder; base/candidate reverse fixed point; shared component vs bridge; unknown hold graph growth | NOT RUN C |
| E18/HR-P | External registry trước đọc, all-store R/ancestors/other sessions; original pins missing/tamper/restore/reopen, semantic authority riêng | NOT RUN C |
| E20 | Two-process same command/raw/intent/concurrent build-seal; two Model+A2 CAS; sealed loser gặp AS-only và Model+AS opponents | NOT RUN C |
| E21 | T0/seal/T3 rollback/kill/lost ACK/unknown; same-command recovery/providerless replay exact allocations/clocks/proofs/history refs | NOT RUN C |
| E22–E24 | AS-only/revalidate không tăng stage; multi-checkpoint C reader; unsupported5–9/L1/migrated; mixed full current selection/retained output/accounting | NOT RUN C |
| E25 | Four-worker/large-history/CLI stress mở rộng | Ngoài C, không triển khai D |

| Safety §7.1 | Required C path/phase và oracle | Trạng thái |
| --- | --- | --- |
| S1 | ≥2 OS preparers same/different intent; ≥2 resumers rendezvous trước seal/finalize trên DIRECT→CARRY và REPLACEMENT; một T0/plan/final event | NOT RUN C |
| S2 | Two Model+A2 commands cùng base; thêm sealed C loser sau valid AS-only và Model+AS winner; stale không Model/Change/Issue/AS planned Records | NOT RUN C |
| S3 | Prepare/seal/finalize × before-COMMIT rollback/kill, after-COMMIT kill/lost ACK/unknown, checked reopen. Không cần tích Descartes mọi topology; đủ C delta | NOT RUN C |
| S4 | Human ancestor + other-session registry HR-P prepare/seal/restart/resume; missing/tamper/subset/restore; finalized registry required, no authority/provider | NOT RUN C |
| S5 | DIRECT→CARRY, CARRY pending, REPLACEMENT complete và incomplete fallback, guard-only, rejection; mỗi effects class có before/after seal/T3 + T3 lost ACK | NOT RUN C |
| S6 | Exact raw/config/registry/reserved Run/plan SHA/IDs/times, planned→actual Model/Change/A2/AS, root/from/obsolete/current refs, old Answer/applications/claims/hash; finalized replay read-only | NOT RUN C |

Mỗi case C sau này phải có phase/PID/backend/argv/exit/JUnit/DB/stages/sidecars/readback, expected invariants độc lập với code đang kiểm. Gate G-C1–4 trong proposal phải đạt **trước writer**; S1–S6 phải đạt **ngay C**, B-AS historical pass không thay coverage và không chuyển sang D. Không dùng bảng này làm audit/acceptance C.
