# S22+ ML008: kernel initialization-thread progress; healthy original-A recovery

Status: **RETAINED_STAGE_OBSERVED; NO_PROOF for RAM userspace PID1/USB;
ANDROID_CLOSED_HEALTHY**.

ML008 recovered five intact records from immediately after the kthreadd wait
in `kernel_init`. At least one candidate attempt reached that kernel
initialization-thread recording point beyond `rest_init`. No record from the
second site, immediately after `async_synchronize_full`, was recovered. Its
absence does not establish non-execution, a failure interval or a reset cause.
The operator reports the same boot-loop interval as earlier experience;
no numeric period was measured.

The operator returned the exact attended 1800-second/one-operation approval
on 2026-10-30 KST. Candidate N and original A were each transferred once.
First final rooted Android health and the same-returned-boot retained-log
read passed. The task is consumed and closed, without an unresolved F1 owner
or follow-on grant. A90 and S20+ were untouched.

## Observed behavior and proof limits

The [qualified ML008 candidate](S22PLUS_MAINLINE_ML008_INIT_THREAD_MARKERS_H0_2026-10-30.md)
used the reviewed V6 marker capability and backend v17 through the unchanged
terminal worker. Both calls are in `kernel_init`: after
`wait_for_completion(&kthreadd_done)` returns, and after
`async_synchronize_full` returns, before init-memory freeing. Both V5 sites
are absent. The guarded writer, fixed two-slot bound and existing original-A
recovery route are unchanged. No Linux storage, installed Debian or watchdog
experiment was added.

| Observation | Result |
| --- | --- |
| Candidate N transfer | Completed once |
| Fixed USB observation | All 116 captured snapshots show endpoint absence; original 120-second window expired |
| Authenticated userspace PID1 request/response | Not reached; no request attempt record |
| Post-kthreadd-wait marker | Five intact candidate-bound records |
| Post-async-sync marker | No recovered record; occurrence remains unproved |
| Damaged or foreign marker candidates | Zero |
| Operator observation | Same-interval boot loop; numeric period unavailable |
| Original-A transfer and final rooted Android health | Completed once, healthy; no health-only continuation |

The fixed D0 collector acquired **2,097,136 bytes** from `/proc/last_kmsg`,
with producer exit zero and empty stderr. Both raw health brackets match the
exact returned Android boot. Production decoding and a separate implementation
of V6 frame, identity and integrity checks agree on all five records and their
offsets. The production USB consumer separately rederived endpoint absence
from all 116 complete preserved snapshots with acquisition blocked.

The positive record establishes the first named recording point after the
wait returned. It does not prove that the wait slept, a particular scheduling
invocation, working timer ticks or actual interrupt delivery. The exact
source and H0 qualification bind this call to the preemptible kernel PID1
initialization task, but static physical records contain no live PID, CPU,
preemption-count or DAIF fields. This progress is distinct from authenticated
userspace PID1 execution and USB service, which remain unproved.

This first marker does not prove its own later cleanup or return. Without a
second positive, this run adds no positive witness that `kernel_init_freeable`
or `async_synchronize_full` returned. The missing record does not establish
that either failed or did not run: the helper may skip recording, or retained
bytes may be lost. It cannot localize a failure inside initcalls or exclude
an earlier nonfatal/deferred driver defect. No historical candidate's removed
helper acquires a return claim from this run.

Five records are not five boots. They establish no shared-boot pairing, last
attempt, reset period or reset cause. The operator's relative timing report
remains separate from machine measurement. The USB/userspace PID1 terminal
stays `NO_PROOF`; diagnostic progress is `RETAINED_STAGE_OBSERVED`.

## Recovery and audit

USB timeout stopped the host experiment procedure and preserved the original
attended recovery owner. It did not prove candidate CPU quiescence. The
operator answered the physical Download request with “복구 완료 같은 간격
부트루프 확인”. That answer was retained as operator evidence, not Android
health proof. The reviewed recovery entry verified the exact Download endpoint,
transferred original A once and obtained the first complete seven-read final
health bracket without a health-only continuation.

All 646 retained task captures have successful producer status; no failed
boot-wait read occurred. Recovery was operator-assisted. Automatic recovery
remains unproved, and Android health does not inspect or repair `native_data`.

Task closure was rederived before the fixed retained-log read. The subsequent
H0 audit blocked subprocess/socket/device acquisition while rederiving the
production closure and retained projection. It checked 646 task captures and
38 frozen execution-source records. The 14-row operation journal and all 20
protected task/grant/terminal/closure/journal files stayed byte-identical.
Canonical `candidate_boot_ready` remains `NOT_PROVED`, because it denotes
live USB evidence rather than the later retained-marker result.

## Canonical timeline

Seconds are elapsed host BOOTTIME from opening the original grant.

| Event | Seconds |
| --- | ---: |
| Grant opens | 0.000 |
| Android Download request | 2.241 |
| Candidate N transfer starts | 16.069 |
| Candidate N transfer completes | 17.562 |
| USB observation expires; host procedure stops | 135.990 |
| Original-A recovery transfer starts | 221.409 |
| Original-A transfer completes | 222.829 |
| Final Android health and session close | 269.848 |

## Retained evidence and next distinction

Private root:
`workspace/private/outputs/s22plus-mainline-ml008-h0-20261030-1/`.
The exact approval, finite grant, consumption, raw captures, terminal,
closure and timeline remain under `task-1/`. The response to the physical
Download request is in `operator-download-confirmation.json`; the boot-loop
observation is in `operator-observation.json`, without an invented numeric
period. `retention-1/` contains the raw log and both health brackets.
`audit-run.py`, `run-audit-1.json` and `usb-projection-1.json` retain the offline
checks and source identities.

| Receipt | SHA-256 |
| --- | --- |
| Closed task | `c9a16c3e50a30d7e4a892c77528b9cc8439738cf579e6e8c2c78b83c49a91ff3` |
| Healthy terminal | `bb17ac828b3e8d2f712049563ce4ebb3808a0da0782269f7dea2ed295bf80f0f` |
| Retained-stage result | `1148520f0e8e8ea1f1b09f2f4186696c9bbc7110877f78b25f96da5b41096592` |
| Raw retained log | `ef66ec8c2950ce0926cf01de4f16067a25b03996b8b685a26f79612090e4569d` |
| H0 run audit | `5b30c089ea813f236320389eff75ace715cc230f77d6dd8b4d06181754ddf729` |

The next bounded H0 question is how to obtain useful positive progress evidence
through the later kernel initialization path. Candidate design must consider
both functional progress and whether its recording path can leave a witness;
ML008's missing second record supplies no failure location. This report selects
no successor image or device action and adds no reset-cause-analysis gate.
