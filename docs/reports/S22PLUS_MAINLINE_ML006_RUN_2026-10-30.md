# S22+ ML006: physical architecture and timer-init return; healthy original-A recovery

Status: **RETAINED_STAGE_OBSERVED; NO_PROOF for RAM PID1/USB;
ANDROID_CLOSED_HEALTHY**.

ML006's post-`setup_arch` and post-`time_init` markers were recovered after
physical Download and original-A restoration: six intact records at each
site. The later point proves at-least-once return from `setup_arch`, the
preceding recording helper call and `time_init` along this candidate's
sequential path. Its intervening core memory, scheduler and IRQ initialization
calls returned. This does not prove interrupt delivery, working timer ticks,
ordinary IRQ enablement, later initialization or PID1/USB.

The operator returned the exact attended 1800-second/one-operation approval
on 2026-10-30 KST and subsequently confirmed physical Download entry. One
candidate N and one original-A transfer completed. First final rooted Android
health and the same-returned-boot log read passed. The task is consumed and
closed with no unresolved F1 owner or replay grant. A90 and S20+ were untouched.

## Observed behavior and proof limits

The [qualified ML006 candidate](S22PLUS_MAINLINE_ML006_CORE_MARKERS_H0_2026-10-30.md)
used the reviewed V4 mainline capability and unchanged terminal worker with
backend v15. Both C calls are in `start_kernel`, immediately after their named
function returns, before `random_init` and ordinary IRQ enablement. The earlier
V3 sites are absent; the same guarded two-slot writer is retained. No Linux
storage, installed Debian or watchdog experiment was added.

| Observation | Result |
| --- | --- |
| Exact candidate N transfer | Completed once |
| Fixed USB observation | Original 120-second window expired without the required USB evidence |
| Authenticated PID1 request/response | Not reached; no request attempt record |
| Post-setup-arch marker | Six intact candidate-bound records |
| Post-time-init marker | Six intact candidate-bound records |
| Damaged or foreign marker candidates | Zero |
| Original-A transfer and rooted Android health | Completed once, healthy |

The fixed D0 collector acquired **2,097,136 bytes** from `/proc/last_kmsg`,
with producer exit zero and empty stderr. Both raw health brackets match the
exact returned Android boot. Production decoding and a separate H0
implementation of V4 frame, identity and integrity checks agree on all twelve
records and their offsets.

A later positive establishes return from the earlier helper call in an attempt
of this candidate. That helper may have skipped mapping or writing; it does
not establish execution of both unmap calls. Neither record proves its own
later cleanup/return. The separate earlier-stage record need not come from
that same attempt.

Six records per stage are not a count of six boots or six paired attempts.
Raw retained-log offsets do not encode a sampled ring index, reset time or
last attempt. Static records have no per-boot identity, and logger restoration
can repackage retained data. Reset period and cause remain unproved. Earlier
ML003/ML004/ML005 observations keep their original meanings.

The live USB/PID1 terminal remains `NO_PROOF`; the separate diagnostic result
is `RETAINED_STAGE_OBSERVED`. The latter is not a full-boot or peripheral-health
verdict.

## Recovery and audit

The USB timeout stopped the host experiment procedure and retained the original
attended recovery owner; it did not prove that the candidate CPU had stopped.
After physical Download confirmation, the reviewed recovery entry transferred
exact original A once. During its bounded Android readiness polling, one boot
read returned the exact target-not-found diagnostic after inventory had seen
the target. The existing `wait_ready` branch preserved that failure and took
fresh bounded inventory/boot observations. It did not repeat a transfer or
control action. The first separate seven-read final-health bracket then passed;
no health-only continuation was needed.

This was operator-assisted recovery. Automatic recovery remains unproved,
and Android health does not inspect or repair `native_data`.

Task closure was rederived before the fixed retained-log read. A subsequent
H0 audit blocked subprocess/socket/device acquisition while rederiving the
production closure and retained projection. It checked 645 preserved task
captures, including the one expected failed boot-wait read, and 38 frozen
execution-source records. The 14-row operation journal and all 20 protected
task/grant/terminal/closure/journal files stayed byte-identical. Canonical
`candidate_boot_ready` remains `NOT_PROVED`, because it belongs to live USB
evidence rather than the later retained-marker projection.

## Canonical timeline

Seconds are elapsed host BOOTTIME from opening the original grant.

| Event | Seconds |
| --- | ---: |
| Grant opens | 0.000 |
| Android Download request | 2.363 |
| Candidate N transfer starts | 16.012 |
| Candidate N transfer completes | 17.529 |
| USB observation expires; host procedure stops | 135.929 |
| Original-A recovery transfer starts | 447.180 |
| Original-A transfer completes | 448.570 |
| Final Android health and session close | 495.485 |

## Retained evidence and next distinction

Private root:
`workspace/private/outputs/s22plus-mainline-ml006-h0-20261030-1/`.
The exact approval, one-shot grant, consumption, raw captures, terminal,
closure and timeline remain under `task-1/`. Physical Download confirmation
is separately retained in `operator-download-confirmation.json`.
`retention-1/` contains the raw log and both health brackets. `audit-run.py`
and `run-audit-1.json` retain the independent H0 projection and audit result.

| Receipt | SHA-256 |
| --- | --- |
| Closed task | `f451ef6b74ad0e3a4490ec464edde162fd44c7ca06c8bfe1ecc69ab87d3170fc` |
| Healthy terminal | `f0b27e76ca11696487910f618b1d35f570d9f2129d7b0adae4dacf41d8358bfa` |
| Retained-stage result | `5a166ecb1c41f117afd310eed137f2dea0c9d7ec3e3ae029a5cbce5babdb4c29` |
| Raw retained log | `b87fba3485c86152c1412c56612c031a791bface29de03a049ed436e0f41d7b8` |
| H0 run audit | `e7c1d2fc8952a5ab0daca4dec26e58ec844d2965429e25e68f12458428468a8a` |

The next bounded H0 question is a positive progress witness after `time_init`,
toward IRQ enablement, timer-tick-dependent work and later boot. Any later
recording point needs qualification of its actual mapping lifetime and
concurrency context. Missing records would still not locate a failure.
This report selects no new candidate or device action.
