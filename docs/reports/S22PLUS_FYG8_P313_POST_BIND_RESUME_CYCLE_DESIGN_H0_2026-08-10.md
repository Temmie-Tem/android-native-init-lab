# S22+ FYG8 P3.13 Post-Bind Resume-Cycle Design H0

Date: 2026-08-10 KST

Target: Samsung Galaxy S22+ FYG8 (`SM-S906N` / `g0q` /
`S906NKSS7FYG8`)

Verdict: `DESIGN_COMPLETE_P313_POST_BIND_RESUME_CYCLE_HOST_ONLY`

## Outcome

P3.13 is frozen as a userspace-only successor design. It tests one post-bind
parent-role cycle:

```text
bound peripheral
  -> none
  -> child and parent suspended
  -> peripheral
  -> child and parent active
  -> runtime-resume-nested gadget start and RUN_STOP
```

The question is whether moving the already-bound gadget from the measured
direct pullup path into the standard runtime-resume path changes device-side
state or host visibility. The cycle is attempted only after a same-boot direct
path fence proves that the original bind did not enumerate late.

P3.13 does not alter the fixed Image, kernel patch, module plan, rollback,
transfer machinery, or Carrier-v2 size. Implementation is limited to the
native-init runtime, generated trace descriptor, candidate-specific telemetry
model/decoder, and host qualification. Full-LTO is not required while those
kernel and artifact inputs remain byte-identical.

This document freezes design only. No candidate has been built, no F1 is
armed, and it grants no device authority. The consumed P3.12 candidate is not
replayed.

## Question and Limits

P3.13 answers:

> With the gadget still bound, does one standard `none -> peripheral` cycle
> produce a valid runtime-resume-nested gadget start and change either exact
> device-side USB state or host-visible enumeration?

It does not prove that a USB2 pull-up reached the connector. A clean
post-cycle `not attached` / `UNKNOWN` result with an unchanged digital tuple
is a digital-path refutation, not proof of an analog, mux, cable, connector, or
host-port fault. That result is evidence for reconsidering the parked P3.02
electrical discriminator, not a substitute for it.

The design does not:

- write EUD, UART, raw MMIO, clocks, resets, regulators, or power controls;
- unbind and rebind the UDC;
- change parent or child to host role;
- retry a role write, candidate, transfer, or uncertain action;
- add global clock probes, instruction probes, or another kernel hook; or
- infer success from a terminal register tuple alone.

## Frozen Source and Artifact Facts

The exact FYG8 source and fixed Image establish the following facts.

1. `mode_store()` calls `dwc3_msm_set_role()`. DEVICE sets
   `vbus_active=true`; NONE clears it; `dwc3_ext_event_notify()` derives
   `B_SESS_VLD` and queues `dwc3_otg_sm_work()`.
2. A PERIPHERAL-to-NONE transition calls
   `dwc3_otg_start_peripheral(..., false)`, clears `dwc->connected`, releases
   the child runtime-PM reference, and requests low-power entry.
3. In DEVICE role, child runtime suspend calls `dwc3_gadget_suspend()`. Once
   bound, that path executes `dwc3_gadget_run_stop(..., false)`, disconnects
   the gadget callbacks, and disables EP0, but it preserves `gadget_driver`
   and vendor `softconnect`.
4. Child runtime resume calls `dwc3_resume_common()`. In the fixed Image the
   relevant `dwc3_gadget_resume()` body is inlined there. Its live path calls
   `__dwc3_gadget_start()` and then `dwc3_gadget_run_stop(..., true)`.
5. `dwc3_runtime_resume()` remains an out-of-line outer witness and propagates
   core-init failures. The inlined gadget-resume return remains discarded by
   `dwc3_resume_common()`, so the inner gadget-start and RUN_STOP returns must
   be retained separately.
6. `dwc3_gadget_run_stop()` polls at most 2,000 times with a 1--2 ms sleep and
   returns either zero or `-ETIMEDOUT`. The applicable DWC31 resume soft-reset
   loop is bounded near 200 ms. The unrelated DRD mode-switch 100 ms sleep is
   not on this path.
7. The fixed Image already calls `s22_p294_dwc3_state_snapshot()` and
   `s22_p300_dwc3_event_config_snapshot()` after every successful
   `dwc3_gadget_run_stop(..., true)`. No kernel change is needed to compare
   direct and post-cycle state.
8. The runtime trace text buffer is 65,536 bytes, the parsed-record cap is 64,
   the per-line bound is 1,024 bytes, and a phase may register at most 30
   events.
9. The fixed checkpoint geometry provides ordinal 105 PROGRESS exact rules
   for all `0xD00..0xDAF` values and broad FAILURE bands in
   `(0x4000,0x4FFF]`, `(0x5000,0x5FFF]`, and `(0x6000,0x6FFF]`.
10. P3.12 retained only the clock domain, multi-path flag, reach mask, and
    QSCRATCH state. It did not retain the complete DWC3 state/event tuple.
    P3.13 therefore measures its direct baseline and post-cycle tuple in the
    same boot instead of claiming historical tuple equality.

The source anchors are:

```text
kernel_platform/msm-kernel/drivers/usb/dwc3/dwc3-msm-core.c
  dwc3_msm_set_role
  dwc3_ext_event_notify
  dwc3_otg_start_peripheral
  dwc3_otg_sm_work

kernel_platform/msm-kernel/drivers/usb/dwc3/core.c
  dwc3_runtime_suspend
  dwc3_runtime_resume
  dwc3_suspend_common
  dwc3_resume_common

kernel_platform/msm-kernel/drivers/usb/dwc3/gadget.c
  dwc3_gadget_suspend
  dwc3_gadget_resume
  __dwc3_gadget_start
  dwc3_gadget_run_stop

P3.12 materialized runtime and descriptor
  s22plus_fyg8_p290_e3_runtime.inc.c
  s22plus_fyg8_p286_trace_descriptor.h
```

The implementation contract must bind the exact fixed Image, linked symbols,
materialized sources, descriptor, position table, telemetry model, decoder,
evidence adapter, and all generated runtime bytes.

## Causal Fence Before the Cycle

The original direct bind remains a competing explanation until it has had the
same bounded opportunity to enumerate. P3.13 therefore uses this order:

1. Establish parent `peripheral`, exact UDC membership, and a same-run direct
   QSCRATCH witness with both session-valid bits set.
2. Arm the existing 15-event bind observer and bind the exact UDC once.
3. Retain the direct-path state and event-config snapshots.
4. Hold a 30-second direct fence while sampling canonical UDC state and speed
   every 100 ms and retaining the existing CONNECT_DONE observer.
5. If configured/high-speed or CONNECT_DONE appears, classify
   `DIRECT_LATE_SUCCESS`, publish the final pair, and do not cycle.
6. If any other non-baseline direct activity appears, classify direct-path
   activity and do not attribute a later result to the cycle.
7. Close, parse, validate, and clean the direct observer.
8. Arm the dedicated cycle observer and immediately re-read UDC state/speed.
   Any change in the cleanup/setup gap is direct-path drift and prevents cycle
   attribution.

The exact ACM banner is prepared before bind but must not be written yet. It
is released only after the final retained pair is durable.

## Controlled Cycle

### Stop half

The stop half has one independent 30-second absolute deadline.

1. Write exactly `none\n` once to the existing wrapper mode node.
2. Require exact `none` readback.
3. Require the configfs UDC binding string to remain exact; an unbind is path
   drift.
4. Require ordered `start_peripheral(on=0)`, child runtime suspend, and
   `run_stop(false)` entry/return evidence.
5. Require exact child `runtime_status=suspended`.
6. Require exact parent `runtime_status=suspended`.
7. Preserve the measured inner RUN_STOP result even though the caller discards
   it.

A measured inner `run_stop(false) == -ETIMEDOUT` is a controller stop result.
An outer cycle deadline, unreaped helper, malformed readback, unavailable
trace, or incomplete tuple is `NO_PROOF_OBSERVER`. Those outcomes are never
collapsed.

### Restart half

The restart half starts a fresh independent 30-second absolute deadline.

1. Write exactly `peripheral\n` once to the same mode node.
2. Require exact `peripheral` readback and unchanged UDC binding.
3. Require exact child and parent `runtime_status=active`.
4. Require an ordered `dwc3_runtime_resume` entry/return pair.
5. Within that outer pair require `__dwc3_gadget_start` and
   `dwc3_gadget_run_stop(true)` entry/return pairs.
6. Require exactly one post-restart QSCRATCH witness.
7. Require exactly one post-start state snapshot and event-config snapshot.
8. Reject any `dwc3_gadget_pullup` hit as direct/force-pullup path drift.

A negative outer runtime-resume return is a core-init/device result. A
negative nested gadget-start result or nested RUN_STOP `-ETIMEDOUT` is an
actual device-path result even if a higher caller returns zero. A positive
return where the source contract permits only zero or negative values is an
observer/source contradiction.

Outer resume without the required nested gadget-start/RUN_STOP shape does not
prove an analog fault. It means the DEVICE resume precondition or path was not
established.

### Final window

Keep the cycle observer armed for one final 30-second UDC state/speed window.
This catches late direct pullup re-entry and state-machine multiplicity. The
cycle set intentionally omits IRQ and device-event probes, so a successful
enumeration cannot create an unbounded event storm in this phase.

After the final window:

1. disable recording;
2. read trace, profile, and ring statistics;
3. parse and classify all required pairs;
4. verify `nmissed == 0`, clean ring statistics, complete ordering, and
   `profile_hits >= records` for every event;
5. clean every owned trace object;
6. publish the adjacent final A/B pair;
7. attempt exactly one bounded ACM banner write; and
8. park without publishing another retained failure.

Banner failure after the pair cannot erase the retained result. Banner
success before the pair is a qualification failure.

## Checkpoint Position Contract

The fixed ordinal/stage geometry is unchanged. Direct terminal branches use
explicit zero-detail bypass checkpoints so the final pair remains adjacent.

| Ordinal | Stage/item | P3.13 meaning |
|---:|---|---|
| 84 | `0x8c/0` | banner prepared and deferred |
| 85 | `0x8d/0` | role, UDC, and direct QSCRATCH baseline ready |
| 86 | `0x8e/0` | direct observer ready |
| 87 | `0x8f/0` | direct bind returned |
| 88 | `0x8f/1` | direct start classified |
| 89 | `0x8f/2` | direct fence started |
| 90 | `0x8f/3` | direct fence closed |
| 91 | `0x8f/4` | direct or cycle branch selected |
| 92 | `0x90/0` | cycle observer ready or direct branch bypassed |
| 93 | `0x90/1` | stop helper returned or bypassed |
| 94 | `0x90/2` | child suspended or bypassed |
| 95 | `0x90/3` | parent suspended or bypassed |
| 96 | `0x90/4` | stop result classified or bypassed |
| 97 | `0x90/5` | restart helper returned or bypassed |
| 98 | `0x90/6` | restart readbacks complete or bypassed |
| 99 | `0x90/7` | resume path classified or bypassed |
| 100 | `0x91/0` | post-cycle tuple captured or bypassed |
| 101 | `0x91/1` | final observation window complete |
| 102 | `0x91/2` | trace integrity complete |
| 103 | `0x91/3` | result classified |
| 104 | `0x92/0` | final pair ready |
| 105 | `0x92/1` | A detail published |
| 106 | `0x93/0` | B detail published |

An early failure uses the exact current position and parks. It does not invent
bypass progress, retry the step, or publish a misleading final pair.

## Trace Event Inventory

The existing cycle set has 29 events under a hard phase limit of 30. P3.13
does not append to it. It removes the 12 closed clock-callsite events and uses
this dedicated 25-event set:

| Index | Event |
|---:|---|
| 0--1 | `start_peripheral_in/out` |
| 2--3 | `child_suspend_in/out` |
| 4--5 | `child_resume_in/out` |
| 6--7 | `phy_suspend_in/out` |
| 8--9 | `phy_power_in/out` |
| 10--11 | `phy_init_in/out` |
| 12--13 | `notify_connect_in/out` |
| 14--15 | `outer_sm_work_in/out` |
| 16 | `p307_qscratch` |
| 17--18 | `pullup_in/out` |
| 19--20 | `run_stop_in/out` |
| 21--22 | `gadget_start_in/out` |
| 23 | `dwc3_state_snapshot` |
| 24 | `event_config` |

The role phase separately expands from four to five events by adding the same
QSCRATCH descriptor. The direct bind phase retains its existing 15-event set.
Each phase owns setup, readback, profile, ring, parse, and cleanup separately.

`__dwc3_gadget_ep_enable`, endpoint disable, and disconnect callbacks are not
in the P3.13 cycle set. They can execute on the source path, but execution does
not create a trace record without an enabled descriptor. They remain part of
the timing/state audit and consume zero entries in the record budget.

## Record and Text Budget

The budget is derived from the new post-bind source path and enabled
descriptors, not from P3.12 measurements.

| Source in a clean cycle | Records |
|---|---:|
| two start-peripheral calls | 4 |
| child suspend and resume | 4 |
| PHY suspend off/on | 4 |
| PHY power off/on | 4 |
| one PHY init | 2 |
| one notify-connect | 2 |
| four bounded state-machine work invocations | 8 |
| one QSCRATCH witness | 1 |
| pullup | 0 |
| RUN_STOP false and true | 4 |
| one gadget-start pair | 2 |
| state snapshot | 1 |
| event-config snapshot | 1 |
| **clean total** | **37** |

One bounded direct/force-pullup drift adds one pullup pair, one extra
gadget-start pair, one extra RUN_STOP pair, and two snapshots: eight records.
The accepted drift ceiling is therefore 45 records.

```text
clean: 37 / 64, headroom 27
single bounded drift: 45 / 64, headroom 19
text at drift ceiling: 45 * 1024 = 46,080 / 65,536
text headroom: 19,456 bytes
```

More multiplicity is a path/observer contradiction. A 65th parsed record is
`-P260_EOVERFLOW` and `NO_PROOF_OBSERVER`, never a USB conclusion.
Qualification must execute 37-, 45-, and 65-record fixtures and per-event
ceiling fixtures against the materialized parser.

## Time Budget

The two cycle deadlines are independent and include their nested kernel polls.
The bounded userspace waits are:

| Window | Bound |
|---|---:|
| initial TTY readiness | 5 s |
| initial role/readback | 30 s |
| direct-path fence | 30 s |
| stop half | 30 s |
| restart half | 30 s |
| final UDC state/speed window | 30 s |
| post-pair banner attempt | 5 s |
| **total bounded waits** | **160 s** |

The Process-v2 candidate endpoint window is 300 seconds, leaving 140 seconds
for boot, module load, trace setup/cleanup, and host transition overhead. No
deadline increase is justified by the current transitive audit.

Qualification must distinguish:

- outer deadline expiry or unreaped helper: `NO_PROOF_OBSERVER`; and
- measured inner `dwc3_gadget_run_stop() == -ETIMEDOUT`: controller result.

Any future timeout change must recompute the complete runtime, Process-v2
observer, and transient guard lifetimes together.

## Same-Boot Digital Tuple

P3.13 compares the direct bind baseline with the post-cycle start in the same
boot and fixed Image. The B normal family carries a 10-bit delta mask:

| Bit | Difference |
|---:|---|
| 0 | `USBLNKST` |
| 1 | `COREIDLE` |
| 2 | `SUSPHY` |
| 3 | `CONNECTSPD` |
| 4 | QSCRATCH `UTMI_OTG_VBUS_VALID` |
| 5 | QSCRATCH `SW_SESSVLD_SEL` |
| 6 | `RUN_STOP`, `DEVCTRLHLT`, or `PRTCAP` invariant |
| 7 | `DEVTEN` |
| 8 | static event-buffer config: `GEVNTSIZ` or event length |
| 9 | live event status: `GEVNTCOUNT`, event count, or flags |

`dwc` and event-buffer pointers must both be nonzero and identical across the
two snapshots. A missing or mismatched pointer is a hard contradiction, not a
delta bit. A zero mask means the measured digital state is identical across
the two paths; it does not mean the connector or host observed a pull-up.

## Retained Encoding

The A slot preserves canonical UDC state/speed and whether the cycle was
attempted:

```text
A = 0xD00 + cycle_attempted * 63 + state_index * 7 + speed_index
```

`cycle_attempted` is zero for a direct terminal branch and one after the cycle
starts. Nine canonical states and seven canonical speeds produce 126 values,
`0xD00..0xD7D`, entirely inside the fixed exact-rule band.

The B slot uses existing accepted runtime bands:

| Family | Range | Meaning |
|---|---|---|
| normal cycle | `0x4801..0x4C00` | `0x4801 + 10-bit delta_mask` |
| direct branch | `0x4C01..0x4C02` | late success or non-baseline direct activity |
| controller/device | `0x5001..0x5050` | 10 sources x 8 negative-errno buckets |
| path drift | `0x5061..0x507F` | nonzero 5-bit drift mask |
| observer contradiction | `0x6701..0x673F` | exact fail-closed reason |

The ten controller/device sources are frozen as stop mode-helper/sysfs write,
child runtime suspend, stop RUN_STOP, PHY power-off, restart
mode-helper/sysfs write, child runtime resume, PHY init, PHY power-on,
gadget-start, and start RUN_STOP. The eight errno buckets are `ETIMEDOUT`,
`EBUSY`, `EINVAL`, `EAGAIN`, `EIO`, `ENODEV`, `ENOMEM`, and `OTHER_NEG`.
Callbacks whose exact source body always returns zero use any nonzero value as
an observer/source contradiction rather than this family.

The five path-drift bits cover pullup, start/QSCRATCH multiplicity, outer-work
multiplicity, missing/extra resume-start-run nesting, and UDC/role/late-direct
drift. A positive return value where the source does not permit it is an
observer contradiction rather than an errno bucket.

The H0 design audit enumerated all 126 A outputs and 1,200 B outputs through
the existing runtime, checkpoint-client, and fixed-Image gates. The
implementation validator must repeat the enumeration against the actual
materialized P3.13 runtime, model, pair decoder, and evidence adapter.
Because these numeric bands overlap historical candidate meanings, the
P3.13-specific overlay identity and pair decoder are mandatory context; a
generic or inherited decoder must fail closed.

## Result Contract

| Observation | Result |
|---|---|
| direct configured/high or CONNECT_DONE before cycle | direct late success; no cycle attribution |
| other direct or cleanup-gap activity | direct/path result; no cycle attribution |
| post-cycle configured/high plus exact host evidence | cycle effect proved |
| post-cycle silence and delta mask zero | cycle refuted with digital tuple equality; analog remains open |
| post-cycle silence and nonzero delta | changed digital boundary; follow the mask |
| measured inner negative return | exact controller/device boundary |
| pullup, unbind, force path, multiplicity, or nesting drift | no cycle causal claim |
| unavailable/lost/malformed observer or capacity overflow | `NO_PROOF_OBSERVER` |

No terminal register tuple alone proves enumeration. Positive proof still
requires the target contract's exact host observation, rollback, and final
health.

## Hazard-Closure Qualification Artifact

P3.13 qualification must generate one machine-readable
`s22plus_fyg8_p313_hazard_closure_v1` artifact bound to exact source hashes and
test outputs. It is a qualification result, not a new policy gate or per-run
review ladder.

It must map each named prior or current hazard to an executable proof:

| Hazard | Required proof |
|---|---|
| P3.11 profile equality | surplus profile hits accepted; deficit, `nmissed`, and ring loss rejected |
| P3.10 Carrier-v2 JSON | real Process-v2 adapter round trip |
| P3.04 stale position table | all 107 positions match actual runtime calls |
| P3.08 tracefs ABI | every generated descriptor passes source-derived ABI audit |
| swallowed inner return | outer zero plus inner negative remains a device result |
| child/parent PM race | both suspended and both active fences exercised |
| record undercount | source-derived 37/45/65 fixtures and per-event ceilings |
| timeout collapse | independent stop/restart deadlines and internal/outer split |
| early banner | no exact banner call before final publication; exactly one bounded call after |
| tuple hand-join | same-boot direct/post-cycle tuple comparison and pointer contradiction |

This artifact closes the transmission failure that allowed a reviewed hazard
to be omitted from P3.11 implementation. A prose assertion is insufficient.

## Implementation and Qualification Gates

Before packaging, all of the following must pass against materialized P3.13
sources rather than an ancestor runtime:

1. freeze and print the complete `SOURCE_KEYS` closure;
2. generate the 5-event role, existing 15-event direct, and dedicated 25-event
   cycle descriptors;
3. validate descriptor group, event, probe-kind/`$retval`, register, type,
   symbol, and parser-table authority;
4. execute all role, direct, stop, restart, timeout, path-drift, record-budget,
   banner-order, and tuple-delta fixtures;
5. enumerate every actual A/B encoder output through runtime publication,
   checkpoint client, fixed Image gate, model, decoder, and Process-v2
   evidence adapter;
6. validate all 107 position calls and adjacent final-pair geometry;
7. prove trace/profile/ring cleanup on success and every error branch;
8. prove the 160-second bound remains below the exact 300-second observer;
9. emit and validate the hazard-closure artifact;
10. cross-compile touched C and run focused Python validation; and
11. receive one focused independent review of the changed runtime/schema.

If any fixed-Image hook, kernel source, module plan, checkpoint ABI, carrier
size, transfer machinery, rollback, or recovery closure changes, this design's
userspace-only conclusion is invalid. Recompute the source contract and apply
the review/Full-LTO requirements of the changed layer.

## Authority State

This is H0 design evidence for the exact S22+ FYG8 target only. It performed
no device command, D0, D1, F1, build, packaging, transfer, reboot, or flash.
It grants no approval, does not arm P3.13, and does not transfer authority or
evidence to A90.
