# S22+ ML007: pre-rest_init progress; healthy original-A recovery

Status: **RETAINED_STAGE_OBSERVED; NO_PROOF for RAM PID1/USB;
ANDROID_CLOSED_HEALTHY**.

ML007 recovered five intact pre-IRQ-enable and five intact pre-rest-init
records after physical Download and original-A restoration. At least one
candidate attempt reached the recording point immediately before `rest_init`,
after the IRQ-unmask instruction and intervening core initialization. This
proves neither entry to `rest_init`, actual IRQ delivery, working timer ticks,
nor PID1/USB. The operator reports a boot loop at the same interval as earlier
experience; no numeric period or reset cause is established.

The operator returned the exact attended 1800-second/one-operation approval
on 2026-10-30 KST and confirmed physical Download entry. Candidate N and
original A were each transferred once. First final rooted Android health and
the same-returned-boot log read passed. The task is consumed and closed with
no unresolved F1 owner or replay grant. A90 and S20+ were untouched.

## Observed behavior and proof limits

The [qualified ML007 candidate](S22PLUS_MAINLINE_ML007_BOOTSTRAP_MARKERS_H0_2026-10-30.md)
used the reviewed V5 marker capability and backend v16 through the unchanged
terminal worker. Its two calls are in `start_kernel`, immediately before
ordinary IRQ enablement and immediately before `rest_init`. V4 calls are
absent, and the same guarded two-slot writer is retained. No Linux storage,
installed Debian or watchdog experiment was added.

| Observation | Result |
| --- | --- |
| Candidate N transfer | Completed once |
| Fixed USB observation | All 116 captured snapshots show endpoint absence; original 120-second window expired |
| Authenticated PID1 request/response | Not reached; no request attempt record |
| Pre-IRQ-enable marker | Five intact candidate-bound records |
| Pre-rest-init marker | Five intact candidate-bound records |
| Damaged or foreign marker candidates | Zero |
| Operator observation | Boot loop at the same interval as earlier experience; numeric period unavailable |
| Original-A transfer and final rooted Android health | Completed once, healthy; no health-only continuation |

The fixed D0 collector acquired **2,097,136 bytes** from `/proc/last_kmsg`,
with producer exit zero and empty stderr. Both raw health brackets match the
exact returned Android boot. Production decoding and a separate implementation
of V5 frame, identity and integrity checks agree on all ten records and their
offsets. The production USB consumer also independently rederived absence
from all 116 complete preserved snapshots without new acquisition.

A pre-rest-init positive proves that this candidate's preceding helper call
returned along its sequential path; it may have skipped writing and some or
all cleanup. Neither record proves its own later unmap or return. The separate
earlier record need not come from that same attempt. The removed ML006 writer's
return is not proved by this candidate.

The later point follows the IRQ-unmask instruction, console initialization,
delay calibration and later core initialization. `calibrate_delay` can use
`lpj_fine` derived from timer frequency, so its completion is not a timer-tick
witness. Initial task, CPU, preemption and DAIF values were qualified in H0;
the static physical frames do not dynamically encode those fields. Neither
record proves that `rest_init` created a thread or scheduled PID1.

Five records per stage are not five boots or five paired attempts. Static
records have no per-boot identity; retained-log offsets and firmware's
restoration can repackage data. They do not establish the last attempt,
reset period or cause. The operator's relative timing observation remains
separate from machine measurement. Missing records would not locate a failure.
The USB/PID1 terminal remains `NO_PROOF`; diagnostic progress is separately
`RETAINED_STAGE_OBSERVED`.

## Recovery and audit

USB timeout stopped the host experiment procedure and retained the original
attended recovery owner. It did not prove candidate CPU quiescence. After
physical Download confirmation, the reviewed recovery entry transferred exact
original A once. The first seven-read final-health bracket passed without a
health-only continuation. All 612 retained task capture receipts have successful
producer status; no failed boot-wait read occurred in this run.

This was operator-assisted recovery. Automatic recovery remains unproved,
and Android health does not inspect or repair `native_data`.

Task closure was rederived before the fixed retained-log read. The subsequent
H0 audit blocked subprocess/socket/device acquisition while rederiving the
production closure and retained projection. It checked all 612 task captures
and 38 frozen execution-source records. The 14-row operation journal and all
20 protected task/grant/terminal/closure/journal files stayed byte-identical.
Canonical `candidate_boot_ready` remains `NOT_PROVED`, because it denotes live
USB evidence rather than the later retained-marker result.

## Canonical timeline

Seconds are elapsed host BOOTTIME from opening the original grant.

| Event | Seconds |
| --- | ---: |
| Grant opens | 0.000 |
| Android Download request | 2.093 |
| Candidate N transfer starts | 14.267 |
| Candidate N transfer completes | 15.779 |
| USB observation expires; host procedure stops | 134.195 |
| Original-A recovery transfer starts | 187.564 |
| Original-A transfer completes | 188.948 |
| Final Android health and session close | 235.922 |

## Retained evidence and next distinction

Private root:
`workspace/private/outputs/s22plus-mainline-ml007-h0-20261030-1/`.
The exact approval, finite grant, consumption, raw captures, terminal,
closure and timeline remain under `task-1/`. Physical Download confirmation
is in `operator-download-confirmation.json`. The operator's exact statement,
“같은 간격으로 부트루프”, is in `operator-observation.json`, with no invented
numeric period. `retention-1/` contains the raw log and both health brackets;
`audit-run.py` and `run-audit-1.json` retain the independent projection audit.

| Receipt | SHA-256 |
| --- | --- |
| Closed task | `6b51fcd1538afcbe01f5da7035aa711043c361d7b3cd9fa7675a411830b8d6ca` |
| Healthy terminal | `d6c77e63ffe5c53e3337c6fddf3783b719c8b840f262aa5aa143839612df8dcb` |
| Retained-stage result | `fec6f91e4cd1aa244475e22a1cfc63b35935c34439846feae415571ebbf27080` |
| Raw retained log | `5ed82b55b4903ce7f022cd9ed2efa5955e47b9d80de85c3e503f78a75c8ad08f` |
| H0 run audit | `65a0d356411e7aa57eb781d410cc6e2ac069db8e3bb94f3ba42d00ba4933f432` |

The next bounded H0 question is progress through `rest_init` into the kernel
initialization thread and later initialization. Such sites introduce different
task/preemption and possible worker/driver ownership contexts; their actual
mapping lifetime and reachable interference must be qualified. This report
selects no successor image or device action, and does not gate future progress
on open-ended reset-cause analysis.
