# P458 pre-transfer stop and original-A recovery

Status: **NO_PROOF**, with **ANDROID_CLOSED_HEALTHY** and the one-operation
grant closed. The exact attended P458 task was approved and dispatched once.
One Android-to-Download command ran; **N was never transferred or globally
claimed**. One original-A recovery completed, followed by a separate remaining
health-only continuation. There was no Debian reboot, Debian userspace start or
attempted native_data writable lifetime from this candidate. A90, S20+ and
server work remained untouched.

## Stop before N

The current fixed original-A/Android32 preflight passed. The Download producer
returned exit 0 with no stderr in 3772 ms. Its departure observer then reported
`bound USB generation did not depart` and retained the recovery owner.

The host evidence identifies a deadline-ordering defect. The 30-second
departure deadline was allocated before `Session.intent()` performed the full
current checks and its first `consume()` check. The durable intent was recorded
32.214537 seconds after that deadline's origin: the window was already expired
by **2.214537 seconds before dispatch intent**. After the command returned,
the observer's loop condition was false before its first sample. This is not
evidence that the physical USB endpoint failed to depart. Exit 0 alone does
not prove the transition either. No Download command or N attempt was replayed.

The fixed approved connector supported normal automatic-boot return and
post-A health, but lacked the stopped pre-A recovery entry. Its health branch
also accepted only an `install-android` A intent, excluding the existing
`recover-android` branch. The operator therefore invoked the original reviewed
`recover --attended` CLI once from an ordinary terminal. The connected worker
was subsequently unavailable; its disappearance has no established cause.

## Recovery and closure

The original A transfer completed once and was independently reconstructed
from its raw capture. During subsequent Android health, an ADB read returned
device-not-found after the boot-readiness observations. Its raw stdout/stderr
remain preserved. The operator invoked the same existing-A recovery branch
once more for health only. That branch reconstructed the completed A and
performed no additional transfer. Exact changed-boot rooted Android health,
GPT and Android32 capacity passed.

| Event | Seconds from original grant |
| --- | ---: |
| Download control intent | 392.659 |
| N transfer / Debian boot | Not reached |
| Original-A recovery transfer intent | 539.959 |
| Original-A transfer complete | 541.510 |
| Final Android health complete | 697.462 |
| H0 task closure | 819.411 |

Closure reopened **223 raw captures**, including the one failed health capture,
rederived the final recovery sequence and terminal, and verified all **10
journal rows** and the terminal unchanged. The complete canonical timeline
explicitly marks candidate-transfer and candidate-ready events as not reached.
The single operation is consumed and the global F1 owner is absent. The unused
N content is not a global consumed-candidate claim; this closed task and grant
still cannot be reused.

The source provenance is the exact working tree based on `edfca0f35c`, with
149 saved host/review rows and 168 runtime sources. Private evidence and the
raw-first closure audit remain under
`workspace/private/outputs/s22plus-debian-reboot-p458-h0-20261025-1/`.
No cleanup removed the failure, command, approval or recovery evidence.

## Next bounded work

H0 repair must keep expensive qualification outside the short departure
observation window, retain fresh source/artifact identity checks at effects,
and never renew a window after control intent. Merely moving deadline creation
does not address expensive guards inside the observer loop. Independent review
must cover both points and the unchanged no-replay boundary.

The reusable approved worker also needs the original stopped-owner A recovery
and raw-proved `recover-android` health continuation. Both must retain the
original task, actual approval, finite ownership and exact A, with no new grant,
native retry or uncertain transfer replay. This is prospective H0 work after
healthy closure. No second device experiment follows from this report.
