# S22+ ML009: pre-basic-setup progress; healthy original-A recovery

Status: **RETAINED_STAGE_OBSERVED; NO_PROOF for RAM userspace PID1/USB;
ANDROID_CLOSED_HEALTHY**.

ML009 recovered five intact records from immediately before `do_basic_setup`
in `kernel_init_freeable`. At least one candidate attempt reached that point
after the preceding early initcall, SMP/scheduler, workqueue/async/padata and
late page-allocator preparation path returned. No post-basic-setup record was
recovered. Its absence does not establish non-execution, a failure inside
basic setup or a reset cause. The operator again reports a boot loop at the
same interval as earlier experience, without a numeric period measurement.

The operator returned the exact attended 1800-second/one-operation approval
on 2026-10-30 KST and later confirmed physical Download entry. Candidate N
and original A were each transferred once. First final rooted Android health
and the same-returned-boot retained-log read passed. The task is consumed and
closed, without an unresolved F1 owner or follow-on grant. A90 and S20+ were
untouched.

## Observed behavior and proof limits

The [qualified ML009 candidate](S22PLUS_MAINLINE_ML009_BASIC_SETUP_MARKERS_H0_2026-10-30.md)
used the reviewed V7 marker capability and backend v18 through the unchanged
terminal worker. Its two calls bracket the sole `do_basic_setup` call in
`kernel_init_freeable`; linked qualification accounts for the inlined basic
setup and regular initcall loops. Both V6 sites are absent. The writer,
two-slot bound and original-A recovery path are unchanged. No Linux storage,
installed Debian or watchdog experiment was added.

| Observation | Result |
| --- | --- |
| Candidate N transfer | Completed once |
| Fixed USB observation | All 115 complete snapshots show endpoint absence; original 120-second window expired |
| Authenticated userspace PID1 request/response | Not reached; no request attempt record |
| Pre-basic-setup marker | Five intact candidate-bound records |
| Post-basic-setup marker | No recovered record; occurrence remains unproved |
| Damaged or foreign marker candidates | Zero |
| Operator observation | Same-interval boot loop; numeric period unavailable |
| Original-A transfer and final rooted Android health | Completed once, healthy; no health-only continuation |

The fixed D0 collector acquired **2,097,136 bytes** from `/proc/last_kmsg`,
with producer exit zero and empty stderr. Both raw health brackets match the
exact returned Android boot. Production decoding and an independent
implementation of V7 frame, identity and integrity checks agree on all five
records and their offsets. Offline USB validation used the production parser
and separately checked the raw absent-node condition in all 115 snapshots;
none merely had a present device without a ready NCM interface.

The pre-basic positive establishes the named point after the earlier
kernel-thread preparation and early/pre-SMP initcall loop returned. It is
not a point before all initcalls. Returned preparation calls do not establish
successful initialization, actual interrupt delivery or working timer ticks.
The bound source and H0 evidence qualify the kernel PID1 task context, but
static physical frames contain no live PID, CPU, preemption or DAIF fields.
Authenticated userspace PID1 and USB service remain unproved.

The first frame does not prove its own later helper cleanup or return, nor
entry into basic setup. This run adds no positive witness that driver-model
setup, the regular initcall traversal or their cleanup returned. The missing
post-basic frame could reflect non-arrival, guard/mapping/header rejection,
incomplete recording or later retention loss; none of those explanations is
established. It does not locate a failure inside a driver or initcall and does
not exclude an earlier nonfatal/deferred defect. The removed ML008 helper
receives no new return claim from this candidate.

Five records are not five boots. They establish no last attempt, same-boot
pairing, numeric reset period or reset cause. The operator's timing observation
is separate from machine measurement. The live USB/userspace PID1 terminal
stays `NO_PROOF`; diagnostic progress is `RETAINED_STAGE_OBSERVED`.

## Recovery and audit

USB timeout stopped the host experiment procedure and preserved the original
attended recovery owner. It did not prove candidate CPU quiescence. The
operator reported “같은 간격 부트루프 관측 다운로드 모드진입”. The reviewed
recovery entry checked the exact Download endpoint, transferred original A
once and obtained the first complete seven-read final-health bracket, without
a health-only continuation.

All 644 retained task captures have successful producer status; no failed
boot-wait read occurred. Recovery was operator-assisted. Automatic recovery
remains unproved, and Android health does not inspect or repair `native_data`.

Task closure was rederived before the fixed retained-log read. The subsequent
H0 audit blocked subprocess/socket/device acquisition while rederiving the
production closure and retained projection. It checked all 644 task captures
and 38 frozen execution-source records. The 14-row operation journal and all
20 protected task/grant/terminal/closure/journal files stayed byte-identical.
Canonical `candidate_boot_ready` remains `NOT_PROVED`, because it denotes live
USB evidence rather than the later retained-marker result.

## Canonical timeline

Seconds are elapsed host BOOTTIME from opening the original grant.

| Event | Seconds |
| --- | ---: |
| Grant opens | 0.000 |
| Android Download request | 2.240 |
| Candidate N transfer starts | 15.972 |
| Candidate N transfer completes | 17.498 |
| USB observation expires; host procedure stops | 135.886 |
| Original-A recovery transfer starts | 212.612 |
| Original-A transfer completes | 214.013 |
| Final Android health and session close | 261.324 |

## Retained evidence and next distinction

Private root:
`workspace/private/outputs/s22plus-mainline-ml009-h0-20261030-1/`.
The exact approval, finite grant, consumption, raw captures, terminal,
closure and timeline remain under `task-1/`. The exact operator statement is
retained in `operator-download-confirmation.json` and `operator-observation.json`,
without an invented numeric period. `retention-1/` contains the raw log and
both health brackets. `audit-run.py`, `run-audit-1.json` and
`usb-projection-1.json` retain the offline checks and source identities.

| Receipt | SHA-256 |
| --- | --- |
| Closed task | `9feafacd120cad37138efb082033eae64b2ef92a17c969e8c5ded3e1f812fa24` |
| Healthy terminal | `c3771b2bb44183b4f3ffdca8f8d143f30f1d662b8ec992e3fb985b07c3eb0d69` |
| Retained-stage result | `ede15a0075c6fc49b7c6f48b28ad9c74b24966cc9cbe80cc012e0eaaf987f07f` |
| Raw retained log | `e2081b0163bbf34c7788d65e2b2c90e5da914a3c726c7048ea40bf701b673385` |
| H0 run audit | `cc942fabc23a5220838e56a9a277d2c47a12e9246d992af70426cacdbe1063db` |

The next bounded H0 question is useful positive progress evidence through
driver-model setup and regular initcall traversal, while retaining a qualified
recording path. The current positive advances the demonstrated prefix; the
missing later frame supplies no failure interval. This report selects no
successor image or device action and adds no reset-cause-analysis gate.
