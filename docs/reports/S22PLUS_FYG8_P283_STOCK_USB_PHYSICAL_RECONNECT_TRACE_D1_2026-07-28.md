# S22+ FYG8 P2.83 stock USB physical-reconnect trace D1

Date: 2026-07-28 KST

Scope: one separately approved, attended physical USB disconnect/reconnect on
the rooted FYG8 stock Android boot while a bounded kprobe trace was armed. No
reboot, Download transition, Odin session, payload, partition write, EUD
write, UART action, driver unbind, or persistent setting change occurred.

## Verdict

`PASS_STOCK_PHYSICAL_RECONNECT_TRACE_CLEANUP_AND_HEALTH`

The run captured a usable known-good stock USB reconnection sequence. It is a
comparison for P2.82's unchanged vendor glue and femto-HS modules, not proof
that the rebuilt core kernel or bare-PID1 candidate follows the same sequence.

## Preconditions and authority

The immediately preceding D0 established:

- exactly one attached `SM-S906N`, `g0q`, FYG8 target;
- root and a mounted tracefs;
- `/sys/module/eud/parameters/enable == 0`;
- all requested probe symbols present exactly once; and
- byte-identical stock and P2.82 `dwc3-msm.ko` and
  `phy-msm-snps-hs.ko` identities.

The D1 created only the `p283phy` tracefs group and instance, using 18
entry/return events, a 64-KiB per-CPU buffer, and the `global` trace clock. The
operator disconnected the existing cable once and reconnected it to the same
host port.

## Exact observations

The trace contains 50 events with balanced entry/return counts. Host evidence
records a real disconnect followed by successful SuperSpeed enumeration. The
final UDC state is `configured` and its speed is `super-speed`.

The successful physical-reconnect suffix is:

1. parent `dwc3_msm_resume` entry;
2. femto-HS `set_suspend(0)`;
3. child `dwc3_runtime_resume` entry;
4. `msm_hsphy_init` entry and zero return;
5. femto-HS `set_suspend(0)` again;
6. `dwc3_gadget_run_stop(1)` and zero return;
7. child runtime-resume zero return; and
8. `msm_hsphy_notify_connect` entry and zero return.

That suffix completed in approximately 32.853 ms. It was followed by the
host's successful SuperSpeed discovery in the same reconnect interval.

The disconnect side also produced the expected inverse path: child suspend,
RUN_STOP off, femto-HS suspend, and parent suspend. Android attempted one
intermediate pull-up/resume cycle while the cable was absent, then suspended
again before the real reconnect.

## Interpretation

- EUD is not the positive-control mechanism; its enable parameter stayed
  zero.
- `msm_hsphy_init` is not limited to boot/probe time. Child DEVICE
  runtime-resume re-entered it twice after the trace was armed.
- The successful stock attach path includes child runtime-resume, full HS-PHY
  initialization, RUN_STOP on, and connect notification in that order.
- P2.82's controlled pre-bind child reinitialization targets a path that the
  stock positive control actually uses.
- Connect notification occurred after RUN_STOP and child resume in the
  successful suffix. It is not evidence that notify-connect must precede
  controller start.

The stock link negotiated SuperSpeed while P2.82 deliberately requests
high-speed and validates that exact speed. Therefore this run establishes the
shared runtime-resume/HS-PHY-init control path, but it does not by itself prove
that every speed-dependent CONNDONE or QMP-SS behavior is irrelevant to the
candidate. No SuperSpeed-only observation is promoted into the P2.82
acceptance contract.

The parent resume return probes produced values inconsistent with the source's
explicit zero-return contract. Those two values are not used. Parent
entry/order remains useful, while return-value interpretation is limited to
the other probes whose captured zero values and source contracts agree.

## Cleanup and health

All 18 events and the trace instance were removed. The verified remainder was:

- zero `p283phy` events;
- no `p283phy` instance;
- Android boot-complete;
- stopped boot animation; and
- root UID `0`.

Raw trace and host sidecars remain under
`workspace/private/outputs/s22plus_fyg8_p283_stock_trace_physical_d1_v1/`.
The host sidecar contains private device identity and must not be copied into a
tracked report.

## Effect on P2.82

Do not change or rebuild the P2.82 candidate because of this result. Its
primary F1 must keep the cable continuously connected and prove autonomous
native-init USB. A physical reconnect before the primary verdict would
confound that claim.

If the primary F1 remains a no-proof, physical-edge recovery can be designed
as a separate, predeclared diagnostic unit and classified as
`RECOVERED_AFTER_PHYSICAL_EDGE`, never as autonomous USB PASS.

## High-speed control

A later, separately approved D1 tested the speed-dependence explicitly. The
first bounded attempt correctly stopped before a physical action because
configfs rejects `max_speed` changes while a gadget is bound. Its 18 events
were removed and the original `super-speed-plus` value never changed. Source
review confirmed this is an intentional configfs guard.

After a fresh approval, the control used the required transient sequence:

`UDC unbind -> max_speed=high-speed -> same UDC rebind`

The detached on-device sequence survived the deliberate ADB transport loss.
Readback then proved a configured high-speed UDC. The trace was cleared, one
physical disconnect/reconnect was performed, and the host independently
observed a real high-speed enumeration.

The high-speed physical trace contains 32 events. Its successful reconnect
suffix is the same 14-event sequence as the SuperSpeed run:

`parent resume -> HS-PHY resume -> child resume -> msm_hsphy_init ->`
`HS-PHY resume -> RUN_STOP(1) -> child-resume return -> notify-connect`

The suffix completed in approximately 33.482 ms, versus 32.853 ms at
SuperSpeed. All authoritative returns in that suffix were zero. This directly
rules out the concern that P2.82's required child-resume/HS-PHY-init path was
only a SuperSpeed behavior. Speed-specific CONNDONE and QMP-SS work still
remain outside that shared prefix and are not generalized.

The D1 ended with the inverse transient sequence restoring
`max_speed=super-speed-plus` and the same UDC. Readback proved both the
original setting and an active `super-speed` link. All events and the
`p283h2` instance were removed, and Android/root health passed.

The high-speed raw evidence remains under
`workspace/private/outputs/s22plus_fyg8_p283_stock_trace_highspeed_d1_v2/`.
