# S22+ ML003: physical mainline entry observed; USB unproved; healthy return

Status: **RETAINED_STAGE_OBSERVED; NO_PROOF for RAM PID1/USB;
ANDROID_CLOSED_HEALTHY**.

ML003's fresh candidate-bound loader-handoff and mainline `primary_entry`
markers were recovered after physical Download and original-A restoration.
This proves that this candidate reached both early code sites on the selected
S22+ FYG8. The operator again reported a boot loop; reset cause, later kernel
initialization, PID 1 and authenticated USB remain unproved.

The operator returned the exact attended 1800-second/one-operation approval
on 2026-10-30 KST. One N and one original-A transfer completed. Final rooted
Android health and the subsequent same-boot retained-log read passed. The task
is consumed and closed; there is no replay or follow-on grant. A90 and S20+
were untouched.

## Scientific evidence and limits

The [qualified ML003 artifacts](S22PLUS_MAINLINE_ML003_RETAINED_MARKERS_H0_2026-10-29.md)
ran through the existing reviewed mainline owner and backend v12. No storage,
installed Debian or watchdog experiment was added.

| Observation | Result |
| --- | --- |
| Exact candidate N transfer | Completed once |
| Fixed USB2 observation | All 116 captures showed absence through the original 120-second window |
| Socket request / authenticated PID1 response | Not reached; no request attempt record |
| Operator observation | Boot loop like the preceding experiment; no numeric interval measured |
| Loader pre-branch marker | Six intact matching records recovered |
| Mainline `primary_entry` marker | Six intact matching records recovered |
| Damaged or foreign marker candidates | Zero |
| Original-A restoration and final Android health | Completed |

The fixed D0 collector acquired **2,097,136 bytes** from `/proc/last_kmsg`,
with producer exit 0 and empty stderr. Both raw health brackets match the
exact returned Android boot. The production decoder and a separate H0
projection agree on the twelve complete candidate-bound records.

The loader record proves its point immediately before the final branch; it
does not by itself prove that branch executed. The kernel record independently
proves entry into this mainline image's `primary_entry`, before
`record_mmu_state`. It establishes early kernel progress even though USB was
absent. It does not prove `start_kernel`, any later initcall, PID 1, userspace,
USB initialization, kernel stability or a watchdog diagnosis.

Six records of each kind are **not a proved count of six boots**. The records
are static per candidate, have no unique boot identity, and may be overwritten
or retained across multiple attempts. Their observed proximity does not supply
a same-boot-pair proof. They establish at-least-once occurrence during ML003's
attempts, not the last attempt or the point where a reset occurred. ML001 and
ML002 retain their original NO_PROOF meanings; this new observation does not
retroactively locate those earlier failures.

The existing operation terminal stays `NO_PROOF` for the RAM PID1/USB success
criterion. The separate retained-stage result is `RETAINED_STAGE_OBSERVED`;
it does not rewrite that terminal into a full-boot PASS.

## Recovery and closure

After the observation window expired, the owner stopped research and retained
only the original attended A recovery. The operator reported physical Download
entry and continued attendance. The exact original A was transferred once.

Its first health bracket stopped at the root/partition read with exit 1,
empty stdout and the exact selected-target ADB `device not found` diagnostic.
There was no timeout, overflow or producer exception. The failed raw prefix
remains preserved; the cause of the ADB disappearance is not inferred.

The reviewed health-only continuation first rederived the completed A transfer,
then obtained fresh complete Android health. It performed no second transfer
or new candidate control. Terminal: `ANDROID_CLOSED_HEALTHY`, recovered and
research closed. This is physical operator-assisted recovery, not demonstrated
automatic recovery. Android health does not inspect or repair `native_data`.

Task closure was rederived with process/socket acquisition blocked. The
post-closure collector then performed its one fixed read and two health
brackets. A further H0 audit checked 627 preserved task captures, including the
one failed health capture, and 38 frozen execution-source records. It verified
all 116 absent USB captures and rederived the marker result without device I/O.
The 15-row operation journal, terminal, grant and closed-task bytes were
unchanged by that audit. No unresolved F1 owner remains.

## Canonical timeline

Seconds are elapsed host BOOTTIME from the original grant opening.

| Event | Seconds |
| --- | ---: |
| Grant opens | 0.000 |
| Android Download request | 2.202 |
| Candidate N transfer starts | 14.695 |
| Candidate N transfer completes | 16.206 |
| USB window expires; research stops | 134.617 |
| Original-A recovery transfer starts | 233.259 |
| Original-A transfer completes | 234.659 |
| Health-only continuation proves final Android health | 320.537 |

The canonical `candidate_boot_ready` event remains `NOT_PROVED`: the early
marker result is a separate post-return observation, not a replacement for
the original live USB success event.

## Retained evidence and next distinction

Private root:
`workspace/private/outputs/s22plus-mainline-ml003-h0-20261029-1/`.
`task-1/` retains actual approval/grant bindings, both readiness observations,
the consumed operation, raw captures, terminal, closure and canonical timeline.
`operator-observations-ml003.json` preserves the reported boot loop and physical
Download action. `retention-1/` contains the bounded raw log, both health
brackets and the decoded result; `run-audit-1.json` records H0 rederivation.

| Receipt | SHA-256 |
| --- | --- |
| Closed task | `7d3c4228333930cd2b2a91059d24c6f077f29595fa08a41ea1bf61ac6bcde0d9` |
| Healthy operation terminal | `fe4c958c88cd72b39598afb3512df86f2a062c7929af5fcfeefde7c33178a28f` |
| Retained-stage result | `bedcf21ba2720aeab40cb4f20c94c41930916bd3123fbb21380d6fe7093a84a0` |
| Raw retained log | `30ad798244e3147cc0609eef68124b54f54112dea8b8e966b2e91d9a104d7581` |
| H0 run audit | `4d806b1c3166e5c451d614afe6fe0e6a1543ef8cde85215f152f4cf586c5c922` |

The useful next H0 distinction is progress after `primary_entry`, using the
actual kernel's startup path. This run identifies no reset cause and does not
select another physical candidate. The existing watchdog UID mismatch remains
a separate hypothesis, not a measured explanation of ML003.
