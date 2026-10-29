# S22+ ML005: physical post-FDT and post-paging progress; healthy original-A return

Status: **RETAINED_STAGE_OBSERVED; NO_PROOF for RAM PID1/USB;
ANDROID_CLOSED_HEALTHY**.

Both ML005 markers survived physical Download and original-A restoration:
five intact `post-fdt` records and five intact `post-paging` records. They prove
at-least-once progress to the candidate's recording points after
`setup_machine_fdt` and after `paging_init`. The latter also proves return
from this candidate's preceding helper call along its sequential path; that
call need not have written a record. Neither record proves its own later
unmapping/return or subsequent initialization.

The operator returned the exact attended 1800-second/one-operation approval
on 2026-10-30 KST. One candidate N and one original-A transfer completed.
First final rooted Android health and the same-returned-boot log read passed.
The task is consumed and closed, with no unresolved F1 owner or replay grant.
A90 and S20+ were untouched.

## Observed behavior

The [qualified ML005 candidate](S22PLUS_MAINLINE_ML005_ARCH_MARKERS_H0_2026-10-30.md)
used the reviewed mainline owner and unchanged terminal worker with backend
v14. Its V3 C markers replaced both V2 sites within the same two-slot bound.
No Linux storage, installed Debian or watchdog experiment was added.

| Observation | Result |
| --- | --- |
| Exact candidate N transfer | Completed once |
| Fixed USB observation | Original 120-second window expired without the required USB evidence |
| Authenticated PID1 request/response | Not reached; no request attempt record |
| Post-FDT marker | Five intact candidate-bound records |
| Post-paging marker | Five intact candidate-bound records |
| Damaged or foreign marker candidates | Zero |
| Original-A transfer and rooted Android health | Completed once, healthy |

The fixed D0 collector acquired **2,097,136 bytes** from `/proc/last_kmsg`,
with producer exit zero and empty stderr. Both raw health brackets match the
exact returned Android boot. Production decoding and a separate H0
implementation of the V3 frame, identity and integrity checks agree on all
ten records and their offsets.

Five copies per stage do not establish five boots or five paired attempts.
The static records have no per-boot identity; adjacency does not prove that
two records came from the same boot. They establish at-least-once occurrence
during this candidate's attempts, not the last attempt, reset cause or a
failure location. After closure, the operator additionally reported that the
boot loop persisted during ML005. No numeric period was supplied; that
observation does not identify a reset cause or stage. Earlier
ML003/ML004 records retain their original meanings, including the limits on
their writers' later return.

The USB/PID1 terminal remains `NO_PROOF`. The separate diagnostic result is
`RETAINED_STAGE_OBSERVED`; it is not full-boot, userspace or USB PASS.

## Recovery and audit

The observation timeout stopped candidate work and retained its original
attended recovery owner. After the operator confirmed physical Download,
the reviewed recovery entry transferred exact original A once and completed
its first final-health bracket. No health-only continuation or extra transfer
was needed. This was operator-assisted recovery; automatic recovery remains
unproved. Android health does not inspect or repair `native_data`.

The exact task closure was rederived before the fixed retained-log read.
A subsequent H0 audit blocked subprocess/socket/device acquisition while
rederiving the production closure and retained projection. It checked all
657 preserved task captures and 38 frozen execution-source records; those
captures have no producer failure. The 14-row operation journal, task journal,
task, grant, terminal and closed-task records stayed byte-identical across
the audit. Canonical `candidate_boot_ready` remains `NOT_PROVED`, because it
belongs to live USB evidence, not the later retained-marker projection.

## Canonical timeline

Seconds are elapsed host BOOTTIME from opening the original grant.

| Event | Seconds |
| --- | ---: |
| Grant opens | 0.000 |
| Android Download request | 2.247 |
| Candidate N transfer starts | 14.975 |
| Candidate N transfer completes | 16.487 |
| USB observation expires; research stops | 134.889 |
| Original-A recovery transfer starts | 184.975 |
| Original-A transfer completes | 186.371 |
| Final Android health and session close | 233.457 |

## Retained evidence and next distinction

Private root:
`workspace/private/outputs/s22plus-mainline-ml005-h0-20261030-1/`.
The exact approval, one-shot grant, consumption, raw captures, terminal,
closure and timeline remain under `task-1/`. The physical Download confirmation
is preserved in `operator-observations-ml005.json`. The later boot-loop report
is preserved as `operator-observation.json` under
`workspace/private/outputs/s22plus-mainline-ml005-next-discussion-20261030-1/`;
the original observation and consumed records remain unchanged. `retention-1/` contains
the bounded raw log and both health brackets; `audit-run.py` and
`run-audit-1.json` retain the independent H0 projection and its result.

| Receipt | SHA-256 |
| --- | --- |
| Closed task | `1ca9cd548b066ade0401c5083643e6ce29530fed41556e252b5c4b30f1d6e5f0` |
| Healthy terminal | `c00688e065fca23a5afc95b883758059d3f5018d43baf4e91e4e16a396481c68` |
| Retained-stage result | `d37625e98eff4b1386f85854d0ccce02efd1ee72b51a66bd00e2dcdb60bf7660` |
| Raw retained log | `843e9ec44914f6c4383e653805bcbe75422742be32b29be3ab90143b5802d650` |
| H0 run audit | `c8ca7659de966567de8853a12cde6a57eb6f8eefa27dd4ad15dd9fdd7713a4f7` |

The next bounded H0 question is how to witness later `setup_arch` progress
after paging, including a positive boundary beyond the second writer's return.
The exact source next handles ACPI/DT expansion, boot memory and resources
before `early_ioremap_reset`. Those are candidate sites for analysis, not
proved failure locations or an already selected next image. This report opens
no new grant or device action.
