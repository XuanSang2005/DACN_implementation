# Coverage mới và safety B chưa chạy

| Case / control | Path/phase | C | Python | Oracle |
| --- | --- | --- | --- | --- |
| diagnostic accepted-plan/publisher | Pure proposed AS-only plan, không writer | 1 pass | 1 pass | Existing A2 positive check_plan nhận, `_published` reject `publisher_assessment`; graph/Record/promotion refs được fixture dựng hợp lệ |
| diagnostic honest assessment | Pure result metadata, không writer | 1 pass | 1 pass | Stage0/outputs rỗng nguyên; Progress/Admission shape nhận, check_admission reject `admission_progress_provenance` |
| diagnostic H2 full anchor | Existing H2 fixture publication, read-only H3 A checks | 1 pass | 1 pass | Actual promoted H2 plan/current pair; full steps1/2 anchor được nhận, transported assessments null |

Đây là **implementer diagnostics**, không auditor controls và không runtime B. Fixture helper/oracle/expected strings giữ nguyên ở output mới. C/Python processes tuần tự; bên trong setup race không sửa. Không cộng ba repeats thành B safety coverage.

| Gate bắt buộc sau audit delta | Phases/path phải triển khai và kiểm | Trạng thái lượt này |
| --- | --- | --- |
| S1 / E20 | ≥2 OS processes same-command preparers/resumers, same-intent convergence/different-intent conflict, concurrent seal/finalize | NOT RUN; chưa B writer |
| S2 / E20 | Paired CAS với AS-only opponent và valid Model+AS opponent; loser stale không planned Records | NOT RUN |
| S3 / E21 | T0/seal/T3 before-COMMIT rollback/kill; after-COMMIT kill/lost ACK/unknown; fresh checked reopen | NOT RUN |
| S4 / E18/HR-P | External all-store registry trước mọi checked read; mất/tamper/ancestor/other-session sau T0/seal, original restore, finalized report | NOT RUN; chỉ contract/spec reviewed |
| S5 | Adopt, AS-only revalidate có permitted successor/guard, blocked/global holds/rejection; không completed output edit | NOT RUN |
| S6 | Actual IDs/raw/config/plan/registry/time allocations/promotions/events/Record bytes/application counts trước-sau/replay | NOT RUN |
| E06/E09/E14/E19/E22/E23/E24 B | No-anchor, stale pair/history/source, proof/assessment/current refs, unsupported entry, mixed A2 histories | Chỉ three pure contract diagnostics ở trên; chưa B runtime |

Sau delta audit, mỗi test B phải có case→phase/path/backend/oracle, PID/barrier/argv, real DB + sidecars/readbacks/actual event-publication counts. Reuse H1/H2 harness không thay assertions; không dùng pass pure hoặc H2 setup để claim B gate pass. Safety không hoãn D, C vẫn cần lặp trên own Model+A2 path khi được giao.
