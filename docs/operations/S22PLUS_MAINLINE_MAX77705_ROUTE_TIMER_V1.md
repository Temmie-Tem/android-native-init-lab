# S22+ one attended no-touch MAX77705 route run with timed return

Status: **REVIEW_GATED_CAPABILITY**

This scope asks one question for one boot of SM-S906N / g0q / FYG8: does the
whole mainline cycle complete without physical action? The cycle is:
1. Android to Download, then one boot-only candidate (N);
2. the reviewed one-write USB route and the authenticated evidence exchange;
3. an automatic return to Download from the candidate itself;
4. one original-A transfer and rooted Android health.

It is the first unit of the
[hands-off cycle plan](../plans/S22PLUS_MAINLINE_USB_ROUTER_AND_HANDSOFF_CYCLE_2026-11-26.md).
It combines two capabilities that were each reviewed and run separately:
- the [Stage 2 route observer](S22PLUS_MAINLINE_MAX77705_ROUTE_V1.md), whose
  [run](../reports/S22PLUS_MAINLINE_MAX77705_ROUTE_RUN_2026-11-26.md)
  enumerated without a replug;
- the [ML050 timed return](S22PLUS_MAINLINE_RAM_V1.md#ml050-timed-udc-return),
  whose [run](../reports/S22PLUS_MAINLINE_ML050_UDC_AUTO_RETURN_RUN_2026-11-11.md)
  returned with the cable untouched.

The existing mainline RAM owner runs one Android-origin operation. Every
condition of that owner applies unchanged:
- physical attendance;
- effect-time identity and health;
- the fixed observation window;
- original-A return;
- no replay.

The operator stays present and keeps physical Download available as the
fallback, but is asked to perform no action. **There is no attach cue for
this scope**, and no cue dialog is started.

**Board artifact.** The kernel Image and the loader-handed DT are the
Stage 2 ones. The DT already carries the `nvmem-reboot-mode` node with
`mode-download = <0x15>` and the PMK8350 SDAM cell that the timer child
checks. Only the RAM observer differs. It is staged by
[`max77705_route_timer_h0.py`](../../workspace/public/src/mainline/s22plus_canary_h0/max77705_route_timer_h0.py)
from the unchanged Stage 2 producer
[`max77705-usb-route.h`](../../workspace/public/src/mainline/s22plus_canary_h0/max77705-usb-route.h).
The wrapper makes two changes:
- it gives the profile its own wire identity: schema
  `s22plus-fyg8-debian-max77705-route-timer-v1`, its own domain and its own
  `G0QX` magics. A route-timer record never verifies as a Stage 2 record,
  and a Stage 2 record never verifies as a route-timer record;
- it applies the ML050 timer composition.

**Timer.** The packaged SysVinit starts the observer as its direct child.
After its mount setup, and before the route observer's first bus access and
before USB setup, the observer calls the reviewed
[`recovery_begin()`](../../workspace/public/src/mainline/s22plus_ufs_link_h0/recovery.h).
That call checks the exact reboot-mode driver and the OF cell and magic.
It then forks the independent child before USB setup and before guest
BOOTTIME 120 s, and completes one local arm challenge. The observer then closes
its IPC end, so no early commit is reachable.

The child alone owns one ordinary `RESTART2("download")` at guest BOOTTIME
555 s, never at or after 570 s. The wire protocol has no Download command.
If arming fails, the observer parks before USB setup and no authenticated
response can exist. An authenticated response therefore implies an armed child. That
response does not prove that the later reset happened, or where it landed.

**Bus effects.** These are the Stage 2 effects, unchanged. On `0x25` the
observer sends only three things:
- `CONTROL1_R` mailbox commands;
- the mailbox start strobe;
- at most one gated `CONTROL1_W(COM_USB)`.

It writes no register value to the PMIC or the FSA4480. The write gate is
the Stage 2 gate, unchanged. The child's only effect is the ordinary
reboot-mode request through the qualified SDAM cell. That request preserves
bit 0, and the existing SCM shutdown path requests NODUMP.

**Return.** After one durable N launch, the original owner waits for a new
Download generation of the exact target. It accepts one only within the
fixed N-launch-plus-660-second window. It then transfers original A once
and obtains rooted Android health. This uses the same deadline, host boot,
target identity, USB generation and effect-time checks as ML050.

Two paths lead to that return:
- **Evidence received.** A successful evidence exchange leads directly into
  this wait.
- **Evidence step stopped.** A stopped evidence step leads into the same
  wait through the owner's stop path. Examples are no USB, a refused
  request, or an expired window.

An existing A intent permits only reconstruction and health. If the window
expires, the arrival is ambiguous, or the automatic wait fails, the existing
attended physical fallback applies within the original owner's bounds.

**Outcomes.** The record verdict comes from the Stage 2 decoder. The return
is reported separately.

| Record verdict | Outcome |
|---|---|
| `ROUTE_CONFIGURED_WITHOUT_REPLUG` | Observed: the route write removed the replug dependency in this boot. No cue exists, so the host asked for no action. |
| `ROUTE_CONFIGURED_AFTER_REPLUG`, `ROUTE_PARTIAL_ENUMERATION`, `ROUTE_WRITE_NOT_HELD` | Observed, with the reading the [design report](../reports/S22PLUS_MAINLINE_MAX77705_ROUTE_H0_2026-11-25.md#outcomes) gives. A replug in this scope is an unrequested physical action. |
| `ENUMERATED_BEFORE_WRITE`, `SKIP_INITIAL_COM_USB`, `SKIP_PREWRITE_NOT_OPEN` | Observed state; the write was not needed or not reached. |
| Any inconclusive verdict, `EVENTS_DROPPED`, any other `SKIP_*` | Inconclusive for the route; the record is retained. |
| `NO_PROOF_*`, missing or rejected evidence | The route stays unproved. |

| Return | Outcome |
|---|---|
| `automatic_original_a_dispatched`, healthy Android, and the operator's post-run statement that no physical action was taken | No-touch return observed. The terminal sets the flag only when the sole A launch is the automatic owner's, bound to the automatic window's deadline. A physical or attended recovery A carries its own bound. The reset caller is not proved: the child is the only reset path this image contains, but no record shows that it ran. |
| As above, with a health-only continuation of the same original A | As above. The continuation is reported. |
| Exact Download observed, but A dispatched by the attended fallback | Not a no-touch cycle. The arrival is reported. |
| Any physical Download or recovery action, or no operator statement | Not a no-touch cycle. The original attended path is followed and reported. |

Arrival facts are rederived against the host epoch the window recorded, so
a later host reboot does not change a sealed terminal.

**Closure.** The automatic wait records many endpoint captures, and ML050
exceeded the single 2 MiB raw index. Task closure therefore uses the
reviewed paged H0 finalizer
[`s22plus_mainline_close_h0_v2.py`](../../workspace/public/src/scripts/analysis/s22plus_mainline_close_h0_v2.py)
with its independent reporting review, after durable healthy closure.

**Scope of the result.** A verdict describes this one boot. A no-touch
return covers only the failure classes this boot exercised. It is one input
to the evidence ladder in the plan. It does not activate Conditional
Autonomous F1.

**Target adoption.** The [target contract](targets/S22PLUS_FYG8_TARGET_CONTRACT.md)
adopts this scope as a **REVIEW_GATED_CAPABILITY**. Each run requires:
- the selected route-timer review at `PASS_GO` for the exact owner closure,
  checked before candidate code is imported;
- one of the exact board qualifications named by the binding module. The
  binding module also requires that the qualified observer was built from
  the reviewed guest sources, with the fixed compile flags;
- the [common-contract](DEVICE_ACTION_CONTRACT_DETAILS.md) delegation of
  the timed reset and automatic original-A return to this exact observer;
- current target identity and a usable original-A recovery path;
- the existing fixed foreground preapproval D0 on a fresh task;
- one new finite attended mainline RAM grant under the
  [mainline RAM policy](S22PLUS_MAINLINE_RAM_V1.md);
- the operator's presence, with physical Download available, through
  healthy Android closure.

It grants none of the following:
- a cue;
- any other `CONTROL1_W` value, or a second write;
- a PMIC, charger, PD or FSA4480 write;
- a Download command on the wire;
- early commit, or any change to the timer's arming, deadlines or owner;
- a hardware or hypervisor watchdog;
- Linux storage or installed-root access;
- unattended execution, retry or replay.

Preparing a task is H0.

**Repeat builds.** The candidate registry consumes each AP once, so each
normal run needs its own board build. A repeat build uses the same reviewed
guest sources, Image, DT and staging, and gets its own run ID and key. It
passes the same board checks:
- the rebuilt observer is byte-identical to the shipped member;
- the producer verdicts verify, and the fixture rejections hold;
- the binding substitutions and guest drift are rejected.

The binding module lists each qualification. Adding one is a reviewed
module change. Each repeat run is a separate attended grant on a fresh task.
The connector requires a healthy predecessor closure for the same target and
original A. Running the repeats in order, each chained to the latest closure,
is the operator's sequencing; the code does not enforce it.

## Successor reviews and adoption

This scope is published together with these changes:
- its hooks in the shared mainline modules: the profile, access, session,
  task and automatic-recovery modules, the gateway closure and the cutover
  checker. `timed_udc` becomes `timed_return`, which selects ML050 and this
  board;
- its target adoption.

The v61 set first adopted this scope (`1e12f415a2`). The v62 set
(`1074da5b1c`) added the two repeat-build qualifications. The v63 set
(`ff8a7cde8d`) made the mainline original-A readiness wait treat
`error: closed` like `device not found`. The v64 set requires readiness to
hold on one ADB transport and boot ID for 10 s before health starts, and adds
two repeat-build qualifications (r4, r5). Both readiness changes are
described in the
[mainline RAM policy](S22PLUS_MAINLINE_RAM_V1.md#return-interruption-and-evidence).
The v65 set lets the automatic-recovery observation take a new census when
a usbfs node departs while Odin lists no endpoint, instead of stopping. The
[UFS capability policy](S22PLUS_MAINLINE_UFS_CAPABILITY_V2.md) describes it.
The v66 set adds three repeat-build qualifications (r6 to r8), to test
whether the cycle repeats.
The v67 set adds the UFS V13 route composition, which selects this
scope's route write for the late-UFS experiment
([policy](S22PLUS_MAINLINE_UFS_ROUTE_V1.md)). It changes nothing in this scope.
The branch selects six pending records under
`workspace/public/src/device-action/bindings/`:
- `s22plus_approved_terminal_persistent_v67_review.json`
- `s22plus_loader_android_timing_v3_cue_v11_review.json`
- `s22plus_mainline_scm_ordinary_cue_v12_review.json`
- `s22plus_mainline_max77705_usb_v10_review.json`
- `s22plus_mainline_max77705_route_v8_review.json`
- `s22plus_mainline_max77705_route_timer_v7_review.json`

After independent review of the exact bytes, publish in one squash on the
operating HEAD:
- the scope;
- all six `PASS_GO` records;
- the task selectors;
- the gateway selector pin for the approved v67 receipt.

Keep the published receipts and task evidence. Then follow the
[shared cutover procedure](../reports/S22PLUS_MAINLINE_ORDINARY_CUE_H0_2026-11-22.md#integration-hold-and-atomic-adoption),
under the existing admission lock and target session lease:
1. close old owners and tasks with their original reviews;
2. resolve staged approvals;
3. run the read-only checker against the exact squash;
4. switch the operating checkout.
