# S22+ ML015 V2 calibration run

Status: **Consumed `NO_PROOF`; `ANDROID_CLOSED_HEALTHY`**.

The operator returned the exact ML015 finite attended approval and later
confirmed physical Download entry. The
[fresh V2 qualification](S22PLUS_MAINLINE_ML015_V2_CALIBRATION_H0_2026-11-03.md),
independent exact-artifact review and fixed preapproval D0 were complete.
The existing capability, backend V22, worker and public execution-critical
sources were reused unchanged.

One candidate N and one original Android A transferred. All 116 USB snapshots
show actual endpoint absence, and no candidate request was attempted.
Original-A transfer completed once. The first return-health attempt stopped
during readiness, before starting the seven-read health bracket:
`wait-077-boot` returned code 1, empty stdout and the exact 14-byte diagnostic
`error: closed` followed by newline. The failed raw capture was preserved.

One permitted health-only continuation completed a new readiness observation
and the full seven-read health bracket. The operation closed healthy, without
repeating a transfer or control. No unresolved F1 owner remains.

## Retained result

The fixed post-closure D0 acquired the complete 2,097,136-byte retained log
with return code 0 and empty stderr. Both health brackets match the accepted
final Android boot. The production V2 decoder and a separate reconstruction
of the fresh candidate's two HMAC frames agree:

| Observation | Result |
| --- | --- |
| Pre-MMU record at `__primary_switch` | 0 |
| Early-C record after `early_ioremap_init` | 0 |
| Damaged or foreign V2 candidates | 0 |
| V10 magic candidates in the returned bytes | 0 |
| Authenticated RAM-userspace PID1 / USB | Unproved |
| Original-A return and complete health | Passed |

This V2 candidate contains neither the V10 global latch nor its large frame
table and deferred/TLMM hooks. Its zero result leaves both early sites
unproved in this candidate. It does not eliminate V10's possible contribution
to older results, locate a kernel stop, prove a GPIO effect, or identify
header eligibility, earlier unseen boots or later retention loss. No new
watchdog, Linux storage, installed-root or GPIO-reversal action was added.

## Observed Android return identity

Three successful readiness captures before the error (`wait-074` through
`wait-076`) contain the same complete Android boot ID, with boot completion
still unset. The failed `wait-077` supplied no stdout or accepted identity.
No initial full-health properties prefix exists because that bracket had
not started.

Those three IDs match the continuation's readiness ID, both accepted final
properties reads and all four post-closure D0 properties reads: **ten accepted
observations, one observed Android boot ID**. Readiness observations retain
their inventory/serial binding and do not inherit missing topology or health
evidence. No failed capture was combined with the later complete bracket.

No different boot identity was observed across the covered return window.
That does not identify why ADB closed or exclude a boot before the earliest
observation. It also does not establish that either candidate record was
ever written or erased.

## Canonical timeline

Times are seconds from this grant's opening, from the durable journal.

| Event | Seconds |
| --- | ---: |
| Android Download intent | 2.154 |
| N transfer intent / completion | 14.502 / 16.035 |
| Observation stopped; recovery owner retained | 134.421 |
| Original-A transfer intent / completion | 250.606 / 251.982 |
| First return-health attempt began | 251.998 |
| Health-only continuation began | 426.194 |
| Final health and durable close | 427.833 |

## Evidence closure

Offline rederivation checked all 610 task raw captures, 41 frozen execution
source records, complete V2 retention evidence and USB absence. The bytes of
21 protected task/grant/terminal/journal files remained unchanged with process,
socket and device acquisition blocked. The return-ID projection checks the
successful producers and preceding selector reads separately from complete
health. A console-formatting key error after that projection was published
was handled by verifying its existing structured result and source pin;
no acquisition or device action was repeated.

The consumed approval, grant, journals, raw failure, source snapshot,
canonical timeline and projections remain in the private ML015 output tree.
Earlier reviews and consumed owners were not repinned. A90 and S20+ were
untouched; unrelated initial work is unchanged. No successor or new grant
is armed. Healthy original-A closure grants neither replay nor automatic
recovery authority.
