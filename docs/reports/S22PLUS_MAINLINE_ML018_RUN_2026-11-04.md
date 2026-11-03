# ML018: both early V1 records observed; original A closed healthy

Result: **Consumed `RETAINED_STAGE_OBSERVED` / `ANDROID_CLOSED_HEALTHY`**.
The RAM-PID1/USB result remains **`NO_PROOF`**, as expected for this early-park
diagnostic.

The operator returned the exact 1800-second, one-operation attended approval
and confirmed usable physical Download recovery. Refreshed fixed preapproval
health, the [qualified parked candidate](S22PLUS_MAINLINE_ML018_ENTRY_PARK_H0_2026-11-04.md),
current mainline capability, backend V27 and unchanged stable worker passed
their bindings. N and original Android A each transferred once. One initial
Android-to-Download control completed, with no transfer/control replay.

## Observed result and limits

The full **2,097,136-byte** returned log contains one exact ML018 V1
loader-handoff frame and one exact kernel-entry frame. The production decoder
and an independent reconstruction of both candidate-specific HMAC frames agree;
wrong-key frames do not match. There are no damaged or foreign V1 candidates.
The read completed with return code zero and empty stderr. Both surrounding
seven-read health brackets match the final original-A Android boot.

| Observation | Result |
| --- | --- |
| Loader-handoff V1 record | 1, verified |
| Kernel-entry V1 record | 1, verified |
| Damaged or foreign V1 candidates | 0 |
| Authenticated RAM PID1 / USB | Unproved; intentionally unreachable in this candidate |
| Original-A return and final health | Passed |

This demonstrates at-least-once occurrence of both stages for the fresh
ordinary-route candidate and survival of their bytes to the returned snapshot.
The candidate's fixed source places WFE/back-branch immediately after its
entry writer and before `record_mmu_state`. The static frames do **not** prove
physical stop PC, continuous WFE, a unique attempt or a same-boot pair. This
positive does not establish that downstream execution caused ML012–ML017's
zeros or identify their failure point. It does show that the ordinary-route
channel can return these records in this candidate/return combination.

The fixed 120-second USB observation expired. All **116** complete raw
snapshots show endpoint absence and no related interface; no authenticated
request was attempted. The execution owner stopped candidate work and retained
its original-A recovery authority. USB absence was expected by design and adds
no diagnosis beyond the retained stage observations.

## Original-A recovery and health

After the operator completed physical Download entry, the stopped original
owner transferred A once. Initial health failed at `03-health.capture.json`:
ADB reported the selected device missing, with return code one and empty
stdout. The preceding successful properties read ended after 122 bytes, with
a complete boot UUID and four firmware identity fields. That prefix is
diagnostic identity evidence, not a complete health bracket.

Raw transfer evidence proved A completion. The existing owner's single
health-only continuation then passed all final checks. Four initial readiness
IDs, the partial-properties UUID, one continuation readiness ID, two final
health IDs and four post-closure D0 IDs agree: **12 accepted identity
observations, one observed Android boot**. Their original inventory/topology
bindings and distinction from complete health remain explicit. Earlier unseen
boots and the ADB disappearance's cause remain unproved.

| Canonical event | Seconds from original grant |
| --- | ---: |
| live_session_start | 0.000 |
| candidate_flash_start | 14.441 |
| candidate_flash_done | 15.939 |
| candidate_boot_ready | Not proved |
| rollback_flash_start | 672.246 |
| rollback_flash_done | 673.652 |
| rollback_boot_ready | 755.930 |
| live_session_end | 755.930 |

## Closure and next selection

Task closure and the canonical timeline are rederived from durable original
evidence. The raw index retains **625** task captures, including the preserved
failed health read. The fixed post-closure D0 evidence is separate. Offline
checks with acquisition blocked rederive closure, return identity, the full
retained capture and frame authentication. Frozen execution sources, the
current capability/backend and protected task/grant/journal files remain
unchanged.

The candidate and its operation budget are consumed; no F1 owner remains.
Original A is healthy. There is no successor or new grant. A90, S20+,
native_data and unrelated work are untouched. Automatic recovery, full
mainline PID1/USB and installed Debian remain unproved.

The one-park unit is complete. Further selection returns to full-progress
work with a concrete source-backed hypothesis. This result neither calls for
another park candidate nor authorizes an unchanged repeat.

Private run, raw evidence and timeline:
`workspace/private/outputs/s22plus-mainline-ml018-h0-20261104-1/`.
