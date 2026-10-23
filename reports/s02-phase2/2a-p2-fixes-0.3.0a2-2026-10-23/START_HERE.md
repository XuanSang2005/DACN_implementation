# Bàn giao sửa audit 2A-P2 — dacn-s02 0.3.0a2

**Đã sửa, chờ audit lại.** Ngày 23/10/2026. S02-2A-P2-01/02 chưa được auditor đóng; P2 chưa nghiệm thu. Chỉ sửa DB2/E1 review integrity, không mở P3/live.

## Wheel duy nhất cần audit

**[release/dacn_s02-0.3.0a2-py3-none-any.whl](release/dacn_s02-0.3.0a2-py3-none-any.whl)**

SHA-256: `608b5734af7bb88aa3b06b4c113b52749cf131229ad36e2b9a69dcc11bd09de2`.

DB structure 2; L1 `s02-profile/legacy-a3`, E1 `s02-profile/a1a2-v1`; contract/rules IDs, schemas và registry không đổi. DDL2/manifest reader cũng giữ nguyên byte. S01 wheel đi kèm nguyên ZIP a6. `rebuild/` là wheel chỉ để đối chiếu reproducibility; `audit-wheel/` chỉ chứa log build đầu thất bại, không có wheel bàn giao.

## Nội dung và điểm cần auditor xử lý

- [Phản hồi từng finding](FINDING_RESPONSE.md): nguyên nhân, điều kiện trước/sau, phạm vi DB2/E1, compatibility L1; [code/file/dòng](code-locations.json).
- **Một ca oracle nguyên bản vẫn fail trên mỗi backend vì bị từ chối sớm tại checked `heads()` ngoài `pytest.raises`.** Review selection 8/9 đạt; không gọi là 9/9. [Phản chứng, căn cứ yêu cầu và trace](ORACLE_EXCEPTION.md) để auditor quyết định. Không sửa oracle/assertions hoặc làm yếu checked read để lấy kết quả xanh.
- DB2 kiểm đầy đủ Review inventory và một chain/tip duy nhất theo bundle trên toàn L1+E1, kể cả revoked; chặn missing/stale selection, fork, cycle/multiple roots tại checked read và write boundaries. Giữ CAS/rollback và không repair.
- E1 revoked cần predecessor hợp lệ cùng bundle; root request_changes và successor revoked giữ đường hợp lệ. Lỗi revoked có từ P1 a3, được tái hiện lại riêng. DB1/L1 giữ behavior pin, không âm thầm đổi verifier legacy.

## Kết quả thực chạy mới — mỗi backend

| Lane | C | Python | Evidence |
| --- | ---: | ---: | --- |
| Full S02 a2, gồm 34 regression mới | 488 pass | 488 pass | [full-s02](full-s02/checks/commands.json) |
| S01 a6 | 986 pass | 986 pass | [s01-regression](s01-regression/commands.json) |
| Sáu oracle P1 trên a2 | 27 pass | 27 pass | [audit-p1](audit-p1/checks/commands.json) |
| Audit P2 selection trên a2 | **8 pass / 1 fail** | **8 pass / 1 fail** | [audit-p2](audit-p2/checks/commands.json), [oracle exception](ORACLE_EXCEPTION.md) |
| Audit revocation contract trên a2 | 2 pass | 2 pass | audit-p2, audit-2 logs/XML |
| Audit persistence v2 trên a2 | 6 pass | 6 pass | audit-p2, audit-3 logs/XML |
| Tái hiện a1 selection trước sửa | 3 pass / 6 fail | 3 pass / 6 fail | [before-p2](before-p2/checks/commands.json) |
| Tái hiện a1 revocation trước sửa | 1 pass / 1 fail | 1 pass / 1 fail | [before-review_contract](before-review_contract/checks/commands.json) |
| Controls a1 persistence v2 trước sửa | 6 pass | 6 pass | [before-persistence_v2](before-persistence_v2/checks/commands.json) |
| Revocation gap trên baseline P1 a3 | 1 pass / 1 fail | 1 pass / 1 fail | [before-p1-review-contract](before-p1-review-contract/commands.json) |
| Full baseline P1 a3 | 383 pass | 383 pass | [p1-regression](p1-regression/commands.json) |
| Sáu oracle trên baseline P1 a3 | 27 pass | 27 pass | [baseline-p1-oracles](baseline-p1-oracles/commands.json) |
| Full baseline Đợt 1 a3 | 217 pass | 217 pass | [legacy-regression](legacy-regression/commands.json) |
| Differential L1: Đợt 1 a3 = P1 a3 = a2 | 413 trùng | 413 trùng | [differential-summary](differential-summary.json): 67 accepted, 346 rejected |

[Execution summary](execution-summary.json) kiểm counts/failures/errors/skips từ JUnit và exit codes. [Test mapping](TEST_MAPPING.md), `ADAPTER.json` và [input preservation](test-input-preservation.json) công bố baseline/P2 lanes; test/helper lịch sử không sửa. 34 ca mới gồm fresh/mixed, full history, valid controls, read/write boundaries và rollback nguyên bytes. Không skip/xfail.

[Instrumentation](instrumentation.json) ghi encoder calls C/Python thực; [race/fault timelines](race-fault-timelines.json) giữ PID, IPC/barrier, before/after commit, killed processes, checked reopen và DB hashes. Không lấy counts lịch sử làm kết quả mới.

## Bảo toàn, đóng gói và tái lập

- [Actual before inventory](before-inventory.json), Git status/diff/HEAD và `before/` giữ công việc chưa commit. [Diff đúng trạng thái trước sửa](implementation.diff), [protected inventory](protected-inventory.json): 3.633 files trước sửa; 3.624 giữ nguyên byte, 9 files hiện hành thay đổi, một test file mới, không mất file.
- [Audit preservation](audit-preservation.json): inputs/logs/evidence audit và sáu oracle P1 nguyên byte. Toàn handoff a1 và artifacts lịch sử thuộc protected inventory; không ghi đè.
- [Legacy preservation](legacy-preservation.json): `_check_legacy` AST không đổi; `validate_record` chỉ thêm E1 branch; schemas L1/E1/registry, DDL1/DDL2, manifest và A1/A2 logic khác giữ nguyên byte. S01/locks/dependencies không đổi.
- [Source–wheel–installed](package-evidence-02/manifest.json), [test/verify environment equality](test-environment-comparison.json): 24 payload S02, 16 S01 cùng METADATA/WHEEL; non-editable wheel installs. [Rebuild từ copy sạch](rebuild-comparison.json), [build inputs](build-02-provenance.json), [runtime hashes thực](runtime-hashes.json), [release inputs](release-inputs.json). Pip check đạt.
- [Cách tái lập vào output mới và commands](REPRODUCE.md): `*.command.json/.log` cùng `commands.json`, XML và observations từng lane ghi argv/cwd/environment/exit codes. Giữ logs build/focused/collector lỗi harness, không tính thành pass. [Hashes toàn bàn giao](ARTIFACT_HASHES.json).

## Giới hạn

Phản chứng oracle cần auditor xem xét; chưa có kết luận độc lập đóng findings. L1 cố ý giữ các khoảng trống review baseline; bản sửa áp owner E1 và DB2 current-selection consistency, không repair kho DB1. Tests dùng dữ liệu/reviewer synthetic, không xác nhận nghiệp vụ hoặc quyền người review. Differential hữu hạn không chứng minh equivalence mọi đầu vào.

Không chạy migration trên operational store, sửa dataset, gọi LLM, triển khai P3/cutover/activation migrated, renderer hoặc live. Chưa chứng minh mất điện phần cứng, disk-full thật, hiệu năng quy mô lớn hoặc authentication/persistence người review. Manifest reader vẫn chỉ chứng minh nhất quán nội bộ theo phạm vi đã bàn giao a1.
