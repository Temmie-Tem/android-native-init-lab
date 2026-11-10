# ML048 USB first response with the cable continuously attached

ML048 tested whether the S22+ running the ML047 V12 configuration would
appear on the selected host USB path and authenticate during the original
120-second observation window with the cable continuously attached. The
operator explicitly selected the existing no-cue branch. In a separate
reply after the window expired, the operator confirmed that the cable and
buttons had been untouched for the entire observation.

**No USB endpoint or authenticated first response was observed in this run.**
The offline audit reopened all 88 first-window census receipts. Every command
succeeded, with an empty stderr, and reported ENOENT for the selected sysfs
path with zero related children. The first sealed sample ended at N+3.502
seconds and the last at N+118.969 seconds. The owner journal recorded the
original first-window expiry. There was no attach cue, endpoint selection,
network profile, socket request, same-boot witness, UFS permit or link command.

## Comparison

| Run | Physical condition | First observation |
| --- | --- | --- |
| [ML041](S22PLUS_MAINLINE_ML041_RUN_2026-11-10.md) | V6, operator instructed to leave cable and buttons untouched | 88 absent samples, no response |
| [ML044](S22PLUS_MAINLINE_ML044_RUN_2026-11-11.md) | No cue issued, operator later recalled probably reconnecting | Authenticated at N+116.258 seconds, physical timing unknown |
| [ML047](S22PLUS_MAINLINE_ML047_RUN_2026-11-11.md) | V12, one operator-reported reconnect | Authenticated at N+55.762 seconds, physical timing unknown |
| ML048 | Same reviewed V12 capability as ML047, operator-confirmed untouched cable and buttons | 88 absent samples, no response before expiry |

The persistent absence prevented this run from reaching the UFS experiment.
The host observation does not identify guest PID 1 state, the Type-C/USB
failure mechanism or whether an endpoint could have appeared after the
observation window. This comparison establishes the outcome for one fresh
V12 candidate under the stated condition.

## Candidate and evidence

Fresh boot-only N used the ML047 kernel, DT, module, observer producer,
capability and independent review with a new key and derived identity.
Qualification reproduced the observer and verified AP/boot/loader/runtime
joins, including actual ARM64 loader tests. All seven current Android
health reads passed before the operator returned the exact attended
one-operation, 1800-second approval. The experiment used the v48 terminal
backend and its existing recovery owner.

## Return and final health

The original owner observed an exact new-generation Download endpoint at
**N+588.979 seconds** inside its 660-second bound. The sole original-A
transfer launched at **N+590.433 seconds**. No physical Download fallback was
requested or reported. The automatic arrival and transfer are verified. The
guest-side trigger remains unknown because no authenticated first response or
child-arm receipt was available.

The first recovery-health ADB read failed after durable A completion. Its raw
failure is retained. The same owner's health-only continuation passed all
seven final reads. No network profile had been created. The canonical timeline
records candidate transfer at grant +24.372 to +26.181 seconds,
original-A transfer at +614.414 to +615.943, and healthy closure at
+696.533. The candidate boot-ready time is unobserved.

After owner release, the existing reviewed paged finalizer and offline audit
verified 7,005 raw captures over 28 pages, the source snapshots, original
deadline, Download generation, both transfer receipts and terminal health.
The preserved ADB read was the only nonzero capture. The connector reports
`CLOSED_BY_ORIGINAL_OWNER` and `ANDROID_CLOSED_HEALTHY`. ML048 is consumed
with UFS `NO_PROOF`.

Private evidence is retained under
`workspace/private/outputs/s22plus-ml048-no-replug-h0-20261111-1/`.
It includes the no-cue plan, the operator's post-window account,
`first-window-audit-1.json`, `run-audit-1.json`, the paged raw index and the
canonical timeline.
