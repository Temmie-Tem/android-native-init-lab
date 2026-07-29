# S22+ FYG8 P2.84 stock outer-work D1 refined design and D0

Date: 2026-07-29 KST

Scope: host-only source/module analysis, an immutable stock-D1 trace
specification, and connected read-only D0 checks. No role write, tracefs
mutation, property change, `adbd` restart, reboot, payload, partition action,
or F1 action occurred.

## Verdict

`STATIC_DESIGN_PASS; TCP_ADB_UNAVAILABLE; D1_NOT_AUTHORIZED`

The proposed `perf_vote_work` same-ordered-workqueue self-deadlock is ruled out
for the exact FYG8 source and module. It cannot remain the first-ranked
boundary merely because it is the only obviously unbounded primitive under
that premise: the premise is false, the same cancellation already returned
inside the proven stop helper, and no intervening enable exists.

The D1 design now:

- ranks all eight parent-suspend boundaries from exact evidence;
- reproduces the P2.84 userspace order without pre-write trace gating;
- suppresses challenge when the control exposes no quantitatively usable
  overlap window;
- records `mode_store` caller `comm` and PID to detect Android interference;
- uses exact module-qualified symbols and instruction-verified in-body
  offsets; and
- excludes TCP ADB because the connected device has no usable network address.

A fresh exact D1 approval is still required before any live mutation.

## Frozen P2.84 identity was not touched

Before host edits, all 60 paths or generated values in
`post-b-source-contract.json` matched the frozen
`identity_preimage.sources` receipts and `git status --short` was empty.
The new specification, tests, name-gate extension, and reports are outside
those `SOURCE_KEYS`. No P2.84 candidate source, verifier, decoder, packager,
or source-bound document was modified. P2.84 is neither rebuilt nor replayed.

The exact artifacts used for this analysis are:

- base source archive SHA256
  `86e2f73412c65fadff0b15bbf0eac9140610f70250514ac0bddbf3b53fb5f7bf`;
- FYG8 source delta SHA256
  `23ef2b27de8843e271d41405b3c0b1a71bfa668615c8f0f12a1e5c4395ec851a`;
- stock `dwc3-msm.ko` SHA256
  `8913b050419e88699033e957d927beef86742ed035f531dc5c4729f50cea60f1`;
  and
- stock `phy-msm-snps-hs.ko` SHA256
  `22a866320ba0de46619484efafaf0cf7ea3f7ba387cee7c3dd085f3a82492e94`.

The FYG8 delta does not replace the audited DWC3 or workqueue source files.

## `perf_vote_work` queue topology

Exact source establishes:

1. `sm_work` is initialized with `dwc3_otg_sm_work`;
2. its submissions use `queue_delayed_work(mdwc->sm_usb_wq, ...)`;
3. `sm_usb_wq` is the ordered `k_sm_usb` workqueue;
4. `perf_vote_work` is initialized with `msm_dwc3_perf_vote_work`; and
5. every submission of that work uses `schedule_delayed_work()`, which targets
   `system_wq`, not `sm_usb_wq`.

The final module independently agrees: `msm_dwc3_perf_vote_work` remains at
`0xae94`, and its queueing call carries a relocation to `system_wq`.
Consequently an outer SM worker cannot deadlock by synchronously cancelling a
work item pending behind itself on the same ordered queue.

There is a second, stronger state argument. The stop branch of
`dwc3_otg_start_peripheral(..., 0)` first calls
`msm_dwc3_perf_vote_enable(..., false)`, whose false branch executes
`cancel_delayed_work_sync`. Retained P2.84 `0x8e` proves that complete stop
function returned. Nothing reenables the perf work before the outer suffix
calls parent runtime suspend. Under workqueue cancellation semantics, that
later parent cancellation has neither pending nor executing work to join.

This does not remove its marker. It demotes the hypothesis so a contrary live
observation remains detectable.

## Ranked parent-suspend boundaries

The ranks are diagnostic priorities, not asserted causes:

| Rank | Boundary | Why it has this rank |
| ---: | --- | --- |
| 1 | acquire `suspend_resume_mutex` | unbounded mutex wait; the first marker localizes the entry-to-post-lock interval, whose only sleeping operation is acquisition |
| 2 | `disable_irq(PWR_EVNT_IRQ)` | synchronous IRQ drain has no local deadline; the expected non-LPM handler is finite, so a stall would be surprising but decisive |
| 3 | clock disable/rate framework | provider callbacks and framework locks have no local deadline |
| 4 | GDSC/regulator collapse | generic framework waits remain possible; the exact GDSC hardware poll itself is bounded to 1.5 ms |
| 5 | `icc_set_bw` bus votes | exact RPMh waits have a 10-second bound; ordinary write returns `-ETIMEDOUT` and batch write BUGs, which does not fit silent 270-second survival |
| 6 | HS/SS PHY callbacks | the child path already suspended both PHYs; both exact parent callbacks fast-return when already suspended |
| 7 | cancel `perf_vote_work` | distinct queue, prior synchronous cancellation returned, no re-enable |
| 8 | wake-IRQ setup | skipped when both `in_device_mode` and `in_host_mode` are false, as in this stop state |

`dwc3_msm_prepare_suspend()` is also marked even though it is not one of the
eight disputed boundaries. It immediately returns when both modes are false;
its alternative L2 loop is bounded to 5 ms.

## Exact trace attachments

`s22plus_fyg8_p284_stock_outer_d1_spec.py` defines a `p284stock` trace group
and instance, a 128-KiB buffer, and monotonic trace clock. Connected D0
confirmed that `mono` is supported.

Module-qualified entry/return probes cover:

- `dwc3_msm:mode_store`;
- `dwc3_msm:dwc3_otg_sm_work`;
- `dwc3_msm:dwc3_otg_start_peripheral`;
- core `dwc3_runtime_suspend`;
- `phy_msm_snps_hs:msm_hsphy_set_suspend`;
- `phy_msm_snps_hs:msm_hsphy_enable_power`;
- `dwc3_msm:dwc3_msm_runtime_suspend`; and
- `dwc3_msm:dwc3_msm_suspend`.

`dwc3_msm_suspend` is at `0x8ef0`, size `0x73c`. Inlined and otherwise
non-symbolized boundary probes use these exact offsets:

| Completion marker | Offset |
| --- | ---: |
| mutex acquired | `+0x044` |
| perf cancellation done | `+0x064` |
| prepare-suspend done | `+0x13c` |
| PWR event IRQ disabled | `+0x144` |
| HS PHY done | `+0x180` |
| SS PHY block done | `+0x2e0` |
| clocks done | `+0x358` |
| GDSC done | `+0x3e4` |
| bus vote done | `+0x3f0` |
| wake-IRQ block done or skipped | `+0x610` |
| suspend mutex released | `+0x680` |

Every offset is AArch64 instruction-aligned, lies inside the exact function,
and was checked against a frozen 32-bit instruction word read directly from
the exact module. The permanent attachment-name gate accepts every new
descriptor with zero issues. A label suggesting a source helper that was
inlined, or calling `mode_store` an Android writer without proving its caller,
fails the gate.

Tracefs text headers carry task `comm` and PID. Each lane records its exact
writer PID and the frozen trace-visible comm `p284-lane` before the first role
write. The long-lived lane process performs its own `open` and `write`; it must
not fork `echo` or a shell-redirection helper whose identity would change. Any
`mode_store` entry whose pair differs is classified
`ANDROID_EXTERNAL_WRITER_OBSERVED`, makes the lane no-proof, and stops the
transaction after cleanup. This observes Android interference instead of
assuming its absence.

## Control and challenge lanes

One fresh approval may authorize at most one control followed conditionally by
one challenge. There is no same-approval retry.

The control sequence is:

```text
write NONE once
poll child runtime_status every 100 ms until exact "suspended"
wait up to 15 s for actual outer-sm-work return
perform one final suspended read, then immediately write PERIPHERAL once
verify role/child/Android/root health
classify the already-complete trace
```

The final read-to-write restoration path calibrates the userspace reaction
latency without racing the still-running outer work.

Define:

- `T0`: timestamp immediately before the NONE write;
- `Ts`: completion of the first exact suspended read;
- `To`: outer-work return trace timestamp;
- `R`: control restoration latency from its final suspended-read completion
  to the lane-owned `mode_store` entry; and
- `W = To - Ts`: the observed intervention window.

Challenge is eligible only if:

```text
W > 0
W >= max(10 ms, 4 * R)
```

If outer return precedes the first suspended observation, if the NONE-to-outer
interval is too short to expose a usable window, or if the margin fails, the
result is `CONTROL_WINDOW_TOO_SHORT`; challenge is not executed. If outer
return is absent at 15 seconds, that is already a positive stock non-return
reproduction and challenge is also not executed.

The eligible challenge exactly reproduces P2.84's userspace ordering:

```text
write NONE once
poll child runtime_status every 100 ms until exact "suspended"
write PERIPHERAL once immediately after the successful read
only after return or recovery, classify whether outer return preceded,
overlapped, or followed the PERIPHERAL mode_store entry
```

There is no trace-buffer poll, outer-return test, or trace-dependent branch
between the suspended read and PERIPHERAL write. Trace is solely retrospective
classification.

## Bounded failure and recovery

The capture and lane state must be detached on-device and durably flushed
before the USB role transition. A detached watchdog is armed for each risky
stage and disarmed or rearmed only after its completion; at most one watchdog
may actually invoke the approved reboot. The fixed time bounds are:

- each role write: 15 seconds;
- child-suspended observation: 15 seconds;
- control outer return: 15 seconds;
- detached normal-reboot watchdog: 20 seconds; and
- final Android/root health: 240 seconds.

If control non-return or challenge write non-return occurs, no later lane
action is attempted. The predeclared detached watchdog performs one normal
Android reboot, which is the recoverable P2.81 D1 precedent. Physical
attendance is required. A spontaneous reboot, panic evidence, ambiguous trace
identity, cleanup failure, or failed final health stops the unit; it does not
permit a second reboot or challenge retry under the approval.

The trace instance and events are removed after a returned lane or after
recovery. Final checks require the exact FYG8 identity, boot completion,
stopped boot animation, root UID 0, parent `peripheral`, child `active`, and no
remaining `p284stock` trace object.

## TCP ADB D0

The connected read-only check found:

- exactly one target matching `SM-S906N/g0q/S906NKSS7FYG8`;
- healthy Android boot, stopped boot animation, and root UID 0;
- parent `peripheral` and child runtime `active`;
- readable tracefs/kprobe substrate and unique module-qualified target
  symbols;
- exact live module hashes matching the source contract;
- Wi-Fi enabled in framework state, but no usable `wlan0` link in the final
  snapshot and zero global IPv4 or IPv6 addresses; and
- unset `service.adb.tcp.port`, `persist.adb.tcp.port`, and
  `service.adb.listen_addrs`.

TCP ADB is therefore unavailable for this D1. Setting a listen port and
restarting `adbd` without a network address would add mutation without a
transport benefit. Both actions are excluded from the current approval
candidate.

If a future read-only D0 finds a reachable Wi-Fi address, the design may be
rebound under a new exact approval to the volatile
`service.adb.tcp.port` change and one `adbd` restart. It must never set
`persist.adb.tcp.port`; the volatile setting must be documented as reboot
cleared. That future possibility grants no authority now.

## One-way result interpretation

- Outer non-return in control, or a challenge PERIPHERAL write blocked while
  the prior outer work lacks a return, is decisive positive evidence for the
  shared stock vendor mechanism.
- A completed challenge with proven temporal overlap and no external writer
  is useful negative evidence for stock Android only. It does not clear the
  bare-PID1 context.
- No eligible control window, any external `mode_store` writer, a lost event,
  an unverified attachment, or a recovery ambiguity is no-proof.
- A trace-free negative is never accepted.

## Host validation and authority

- Python compilation passes for the specification, attachment-name gate, and
  their tests.
- All 18 directly touched specification/name-gate tests pass; the combined
  P2.80/P2.82/new trace-contract set passes 41 tests.
- All eight P2.84 source-contract tests pass, and all 60 frozen source receipts
  remain exact.
- Every new trace descriptor passes the permanent attachment-name gate.
- All 11 in-body marker instruction words match the exact module.
- The connected actions in this unit were D0 reads only.

No D1 has been approved or executed. No successor candidate, F1 manifest, or
F1 authority is created.
