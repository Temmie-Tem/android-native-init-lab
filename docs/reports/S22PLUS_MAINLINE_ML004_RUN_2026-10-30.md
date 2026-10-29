# S22+ ML004: physical MMU and early-C progress; healthy original-A return

Status: **RETAINED_STAGE_OBSERVED; NO_PROOF for RAM PID1/USB;
ANDROID_CLOSED_HEALTHY**.

ML004's pre-MMU and early-C markers were recovered after physical Download
and original-A restoration. The early-C record proves that the selected
mainline kernel enabled the MMU and reached the recording point in
`setup_arch`, after `early_ioremap_init` and before `setup_machine_fdt`.
This includes earlier entry to `start_kernel`. It does not prove completion
of the recorder's subsequent unmapping/return, FDT setup or later boot stages.

The operator returned the exact attended 1800-second/one-operation approval
on 2026-10-30 KST. One candidate N and one original-A transfer completed.
Final rooted Android health and the same-returned-boot log read passed.
The task is consumed and closed with no unresolved F1 owner or replay grant.
A90 and S20+ were untouched.

## Observed behavior

The [qualified ML004 candidate](S22PLUS_MAINLINE_ML004_MMU_MARKERS_H0_2026-10-30.md)
ran through the reviewed mainline owner and unchanged terminal worker, with
backend v13. Its optional V2 markers replaced the V1 sites within the same
two-slot write bound. No storage, installed Debian or watchdog experiment was
added.

| Observation | Result |
| --- | --- |
| Exact candidate N transfer | Completed once |
| Fixed USB observation | Original 120-second window expired without the required USB evidence |
| Authenticated PID1 request/response | Not reached; no request attempt record |
| Operator observation | Repeated reboot after an interval during ML004, before physical Download; no numeric period measured |
| Pre-MMU marker | Six intact candidate-bound records |
| Early-C marker | Six intact candidate-bound records |
| Damaged or foreign marker candidates | Zero |
| Original-A transfer and rooted Android health | Completed once, healthy |

The fixed D0 collector acquired **2,097,136 bytes** from `/proc/last_kmsg`,
with producer exit zero and empty stderr. Both raw health brackets match the
exact returned Android boot. The production decoder and a separate H0
implementation of the V2 frame/identity/integrity checks agree on all twelve
records and their offsets.

The pre-MMU record identifies the start of `__primary_switch` before its
`__enable_mmu` call. The early-C writer independently requires the current
EL's MMU enabled and uses the qualified Normal-NC temporary mapping path.
The observed record reaches its committed-frame point inside that writer;
the unmap calls follow the commit and remain beyond the observed boundary.
The physical exception level is not encoded in these frames.

Six copies of each frame are **not a proved count of six boots**. These static
candidate-bound records have no per-boot identity and can be retained across
multiple attempts. Their proximity is not a same-boot-pair proof. They prove
at-least-once stage occurrence during this candidate's attempts, not the last
attempt, exact reset point or reset cause. The operator's periodic-reboot
observation is preserved separately and does not establish a watchdog cause.
ML001/ML002/ML003 keep their original evidence and meanings.

The USB/PID1 operation terminal remains `NO_PROOF`. The separate diagnostic
result is `RETAINED_STAGE_OBSERVED`; it is not full-boot, userspace or USB PASS.

## Recovery and audit

The observation timeout stopped candidate work and retained the original
attended recovery owner. After the operator confirmed physical Download,
the reviewed recovery entry transferred exact original A once and completed
its first final-health bracket. No health-only retry or additional transfer
was needed. This was operator-assisted recovery, not demonstrated automatic
recovery. Android health does not inspect or repair `native_data`.

The exact task closure was rederived before the fixed retained-log read.
A subsequent H0 audit blocked subprocess/socket/device acquisition while
rederiving the production close and retained projection. It checked all 612
preserved task captures and 38 frozen execution-source records; those captures
have no producer failure. The 14-row operation journal and the task, grant,
terminal and closed-task records stayed byte-identical throughout the audit.
The canonical `candidate_boot_ready` event remains `NOT_PROVED` because it
belongs to live USB evidence, not the later diagnostic marker projection.

## Canonical timeline

Seconds are elapsed host BOOTTIME from opening the original grant.

| Event | Seconds |
| --- | ---: |
| Grant opens | 0.000 |
| Android Download request | 2.120 |
| Candidate N transfer starts | 15.977 |
| Candidate N transfer completes | 17.500 |
| USB observation expires; research stops | 135.891 |
| Original-A recovery transfer starts | 303.485 |
| Original-A transfer completes | 304.881 |
| Final Android health and session close | 351.698 |

## Retained evidence and next distinction

Private root:
`workspace/private/outputs/s22plus-mainline-ml004-h0-20261030-1/`.
The exact approval, one-shot grant, consumption, raw captures, terminal,
closure and timeline remain under `task-1/`. Operator text is separately
preserved in `operator-observations-ml004.json`. `retention-1/` contains the
bounded raw log and both health brackets; `audit-run.py` and `run-audit-1.json`
retain the independent H0 projection and its result.

| Receipt | SHA-256 |
| --- | --- |
| Closed task | `3b2fe8c12d77c9eaa45049c43d26fd838aacec26b690eb64694ef213611f4575` |
| Healthy terminal | `a085459fe2021055a177550460e44bb14058cf7876e22086063b8ab769af39eb` |
| Retained-stage result | `65b4caf30aeef81ca00eb769c669f770f8042ed562a0727dfedd7b64c43e3d14` |
| Raw retained log | `6ee69948ed882d8169770932a1f92d4ebda2cf423aeb320c03b77623c5c07ecb` |
| H0 run audit | `f7367b02b08b34ff3c87d21ea3bbf7948480cad1b518a751a718f4601248a8aa` |

The next bounded H0 question is whether execution returns from the early-C
recorder and completes `setup_machine_fdt`, then proceeds into later
architecture setup. It must retain positive-only evidence and the same
recovery boundaries. This report selects no new image, grant or device action.
