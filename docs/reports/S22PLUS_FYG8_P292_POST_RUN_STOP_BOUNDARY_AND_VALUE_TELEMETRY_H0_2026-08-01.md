# S22+ FYG8 P2.92 Post-Run-Stop Boundary And Value Telemetry H0

Date: 2026-08-01 KST

## Verdict

`PASS_P292_POST_RUN_STOP_BOUNDARY_AND_VALUE_TELEMETRY_H0`

P2.92 is the first controlled-suspend successor to advance beyond inherited
generation 88. It proves the complete deep-suspend, restart, PHY reinit,
parent-peripheral, exact-UDC, configfs-bind, and direct-run-stop prefix through
terminal generation 106. This is real progress, but it does not create a new
functional frontier beyond the older P2.80 electrical boundary: P2.80 had
already proved nested `run_stop(1) == 0`, `DSTS.DEVCTRLHLT == 0`, and a final
UDC state of `not attached`.

P2.92 reaches that same boundary by a materially different path. The child is
already runtime-active before configfs bind, so the authoritative trace sees a
direct rather than runtime-resume-nested `run_stop(1)`. Both paths end with no
host attach. This rules out the placement of run-stop inside versus outside a
child runtime-resume as the sole cause.

The tentative claim that the bare-PID1 module set never establishes software
session-valid is also rejected for this explicit role path. Exact FYG8 source
shows that the candidate's `mode=peripheral` write itself sets
`vbus_active=true`, derives `B_SESS_VLD`, enters the peripheral state, and
programs the UTMI VBUS-valid override. What remains open is the interval after
those software predicates and a running DWC3 controller but before a physical
host attach/reset.

No device was contacted by this H0 unit. It grants no D0, D1, or F1 authority.

## Evidence Binding

The selected P2.92 materialized candidate patch has SHA256
`09cff962f81cc650aa5b1fbafdc9f74da8b5016a0ca6ae9e31682837a586c116`.
Its only patched source paths are the common arm64 GKI defconfig, `init/Kconfig`,
and `init/main.c`; it does not modify either DWC3 implementation reviewed here.

The exact FYG8 sources are:

| Source | SHA256 |
|---|---|
| `msm-kernel/drivers/usb/dwc3/dwc3-msm-core.c` | `1c8a3cea43337eebaf0601e01fe3a17e1260f2f768298b16f723534eee433021` |
| `common/drivers/usb/dwc3/gadget.c` | `c121003d37f4fc9ab951f5d8811fe32736b21dadab985214996606578160c730` |

The MSM glue hash matches the pinned extracted FYG8 input. The common and MSM
copies of `gadget.c` are byte-identical. The live facts remain those recorded
by the closed P2.92 report: generation 105 is
`stage=0x92/item=0/PROGRESS/detail=0`, and generation 106 is
`stage=0x92/item=1/FAILURE/detail=0x0d00`.

## Candidate Enumeration History

The answer depends on which candidate architecture is meant.

- A candidate has enumerated in the broader project. O1.1 completed 128 framed
  exchanges over a host ACM endpoint, but it preserved the stock kernel and
  Magisk `/init` and deliberately used Android's already-running USB stack.
  It is a stock-USB control candidate, not direct-PID1 USB bring-up.
- No direct/minimal PID1 candidate has proven host enumeration. M34 S6, O3,
  and O3F all recorded no candidate USB add/bind/tty event. The later E3 line
  likewise has no accepted endpoint.
- A scan of the 27 root Process-v2 live results finds zero
  `candidate_observer_accepted=true`, eight explicit false results, all
  `endpoint-timeout`, and nineteen older-schema results without that typed
  field. Four of the older results passed marker-only acceptance; those prove
  their retained checkpoint boundary, not host enumeration.

Therefore P2.92 `not attached` is not a regression from a proven direct-PID1
enumeration. It is also not the first exact observation of the wall. P2.80
already classified `run-stop-zero-no-bus-state`; P2.92 proves that the full
controlled power-cycle and reinitialization strategy returns to that same
post-run-stop boundary.

This is the first honest view of the functional E3 wall for the direct-PID1
line: that line has never crossed from a running DWC3 controller to host
enumeration. More control-flow reshaping is not a justified response. P2.80
and P2.92 reached the same boundary through nested and direct run-stop paths,
respectively; the next discriminator must measure state at the digital-to-
physical boundary.

The known-good comparison remains P2.83 stock Android. Both its SuperSpeed and
high-speed physical reconnect controls completed the shared parent-resume,
HS-PHY resume/init, `run_stop(1)`, and notify-connect suffix and then enumerated.
That positive control includes a real cable edge and the stock Type-C/USB
coordination stack, so it does not prove which missing side effect matters to
bare PID1.

## Exact Software Session And Run-Stop Path

The exact FYG8 glue establishes this path:

```text
mode_store("peripheral")
  -> dwc3_msm_set_role(USB_ROLE_DEVICE)
       vbus_active = true
       id_state = DWC3_ID_FLOAT
  -> dwc3_ext_event_notify()
       B_SESS_VLD = 1 when not EUD-spoof-disconnected
  -> dwc3_otg_sm_work()
       B_SESS_VLD selects DRD_STATE_PERIPHERAL
  -> dwc3_otg_start_peripheral(..., 1)
       dwc3_override_vbus_status(..., true)
         HS_PHY_CTRL_REG.UTMI_OTG_VBUS_VALID = 1
       HSPHY notify-connect
       child role = DEVICE
```

P2.92's authoritative restart trace proves the start-peripheral path and
notify-connect completed. The manual role write therefore does not depend on
`usb_notifier_qcom.ko` merely to create `vbus_active` or `B_SESS_VLD`.
Stock notifier, PDIC, orientation, redriver, or physical-cable side effects
can still matter; this H0 does not promote any one of them to root cause.

The exact `dwc3_gadget_pullup(true)` source then:

1. obtains a positive child runtime-PM reference;
2. performs core soft reset, event-buffer setup, and gadget start when the
   child is already active; and
3. calls `dwc3_gadget_run_stop(dwc, true)`.

The P2.92 parser requires `on=1` for both pullup and run-stop and classifies
the trace as direct only when no runtime-resume pair contains run-stop.
`dwc3_gadget_run_stop()` reads DCTL, sets bit 31 `RUN_STOP`, writes DCTL, and
polls DSTS bit 22 `DEVCTRLHLT`. A zero return requires the halted bit to clear
before the bounded timeout. Its runtime-suspended early return is inconsistent
with the preceding positive runtime-PM reference, the already-active child,
and the direct trace. The safe DCTL writer only clears link-state-change
request bits; it does not suppress `RUN_STOP`.

The proven boundary is consequently stronger than “the helper returned”:

```text
software DEVICE session valid
  + wrapper UTMI VBUS-valid write
  + child runtime-active
  + DCTL.RUN_STOP write
  + DSTS.DEVCTRLHLT clear
  + no UDC attach and no host endpoint
```

It still does not prove D+ pull-up voltage, physical VBUS, PHY line state,
cable continuity at the transceiver, a host reset, or descriptor traffic.

## Stock Known-Good Baseline D0

A connected read-only D0 addressed the sole attached S22+ FYG8 target. No A90
was present or contacted. The stock Android preconditions were:

```text
build             S906NKSS7FYG8
boot_completed    1
USB state/config  mtp,conn_gadget,adb
controller        a600000.dwc3
UDC state         configured
UDC speed         super-speed
parent runtime PM active
child runtime PM  active
mode              peripheral
root context      u:r:magisk:s0
```

This establishes the correct connected/configured sampling condition and
confirms that reading a mounted DWC3 register surface would not need to wake a
suspended child. It does not yet provide the register vector.

`CONFIG_DEBUG_FS=y`, `CONFIG_USB_DWC3=y`, and debugfs support are present, but
debugfs is not mounted. Only tracefs is mounted. Consequently
`/sys/kernel/debug/usb/a600000.dwc3/{regdump,link_state}` does not exist in the
current D0 state. Mounting debugfs and later unmounting it are transient state
changes, so the remaining baseline read is D1, not D0. It requires a separately
designed exact command, fresh approval, bounded read, cleanup, and return-health
check. No mount was attempted by this unit.

## Value Telemetry Capacity

The current retained ABI is sufficient. It has two slots and a `u16 detail`.
Mechanical enumeration of the P2.92 contract gives 107 positions and 15,013
currently accepted detail values, including the three exact publication-errno
bands `0x4001..0x4fff`, `0x5001..0x5fff`, and `0x6001..0x6fff`.

The largest unused ranges include:

| Range | Free values |
|---|---:|
| `0x0f37..0x4000` | 12,490 |
| `0x7000..0xffff` | 36,864 |

The clean successor reservation is `0x8000..0xbfff`: a tagged 14-bit payload
that does not overlap any current detail. This proves capacity only. The bit
allocation must not be frozen until the stock known-good vector is captured.
The current candidate field inventory is:

| Payload bits | Value |
|---|---|
| 0 | DCTL `RUN_STOP` readback |
| 1 | DSTS `DEVCTRLHLT` |
| 2..5 | DSTS `USBLNKST` |
| 6..8 | DSTS `CONNECTSPD` |
| 9 | wrapper `UTMI_OTG_VBUS_VALID` readback |
| 10..11 | GCTL port capability |
| 12 | GUSB2PHYCFG `SUSPHY` |
| 13 | DSTS `COREIDLE` |

The eventual tag can prove that capture completed, so no separate valid bit
should be needed. A full raw 32-bit DCTL word does not fit; the stock vector
must determine which fields distinguish known-good state before any subset is
made load-bearing. Splitting raw words across records is undesirable because
only the newest two slots survive.

No new position marker is required. Capture the values at the successful
run-stop boundary, retain the packed word in the cycle result, and publish it
as the existing generation-105 `final_sampling_started` progress detail.
Generation 106 can remain the terminal final tuple. The two surviving slots
then intentionally contain exactly one value snapshot and one terminal result.

`0x8000..0xbfff` is only a design reservation today. A successor must add it
at the exact `(stage=0x92,item=0)` route across the SoT, kernel writer,
userspace client, model, decoder, producer-route gate, and continuous
accept-to-resume walk. Current validators must reject it until that coherent
change exists.

Source-level inspection confirms that current kernel and client acceptance
only names the generated exact rules, final tuple range, and publication errno
ranges through `0x6fff`. The P2.92 evidence layer selects the P2.92 repair
decoder, which delegates record validity to the same model. A compiled
all-values cross-layer rejection audit was then attempted, but its first two
invocations failed before testing any candidate byte: first an incorrect local
module name was assumed, then `verify_authority()` was passed a path although
its source requires a parsed manifest object. These are two occurrences of the
same actual-input-shape failure class. AGENTS.md rule 7 therefore stops that
audit without a third invocation. Full kernel/client/model/decoder/evidence
rejection of all 16,384 proposed values remains a required pre-intent gate; it
is not claimed complete here.

## Deterministic Interpretation Requirement

The successor must make both outcomes useful:

1. If any sampled field differs from stock, the decoder must name the exact
   mismatching field or mismatch bitmask.
2. If every sampled field equals the stock vector, the decoder must emit an
   explicit `digital-state-matches-stock` conclusion. Equality must not render
   as an empty or generic no-proof value.

The second result closes the checkpoint channel's useful scope for this wall:
register equality cannot prove D+ pull-up voltage or other analog line state.
If it occurs, the next unit must change instrument class under a separate
design and safety review rather than add another checkpoint marker or digital
register read. This report does not authorize an electrical probe or relax the
EUD/UART and partition boundaries.

## Capture Constraint

The existing DWC3 debugfs files are not a load-bearing sampler. `link_state`
calls `pm_runtime_resume_and_get()`, and the generic `regdump` path calls
`pm_runtime_get_sync()`. Reading either after the failed bind can resume or
otherwise perturb the controller whose exact state is being diagnosed.

The values must instead be captured inside or immediately adjacent to the
successful run-stop path, before runtime-PM release, then transported through
the already-bounded trace/result pipeline. A source-level generated capture
helper with stable arguments is preferable to LTO register-allocation or
objdump-spelling assumptions. The exact helper/trace design remains a separate
pre-intent H0 unit and must prove byte-level source binding and capture timing
before it enters a candidate identity.

An independent host USB/udev sidecar can corroborate whether any connect,
reset, or descriptor event appeared, but it cannot replace the device-side
register snapshot.

## Next Bound

Do not add more location markers and do not request another F1 yet. The order
is now:

1. separately design and approve one stock-active D1 that mounts debugfs,
   captures the exact known-good DWC3 vector, unmounts it, and rechecks health;
2. select the 14-bit field layout from that measured vector;
3. repair and preflight the stopped all-values cross-layer audit using its
   actual manifest fixture before one new execution;
4. fault-validate both mismatch and exact-stock-match conclusions; and
5. only then consider a new identity, Full-LTO A/B, manifest, D0, and fresh F1
   approval.

The candidate value can still reuse generation 105 while generation 106
remains the terminal classifier, but that layout is not selected today.
