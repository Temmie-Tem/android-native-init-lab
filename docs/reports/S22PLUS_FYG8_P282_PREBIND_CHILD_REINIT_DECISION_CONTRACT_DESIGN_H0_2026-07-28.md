# S22+ FYG8 P2.82 Pre-Bind Child-Reinit Decision Contract Design H0

Date: 2026-07-28 KST

## Verdict

`DESIGN_COMPLETE_P282_PREBIND_CHILD_REINIT_DECISION_CONTRACT_HOST_ONLY`

Implementation gates are amended by
`S22PLUS_FYG8_P282_CLASSIFIER_COVERAGE_RETAINED_GEOMETRY_REVIEW_H0_2026-07-28.md`.
The mechanism, stages, and detail meanings remain frozen.

The mechanism analysis is frozen. The exact FYG8 source supports one bounded
pre-bind parent-role cycle:

```text
peripheral
  -> none
  -> exact child runtime_status=suspended
  -> peripheral
  -> exact child runtime_status=active
  -> one configfs UDC bind
```

P2.82 turns that cycle into a complete decision contract. Every reachable
boundary has one retained classification, and the final UDC state preserves
the controlled-reinit class, bind branch, exact canonical UDC state, and exact
canonical current speed. No outcome is interpreted from absence of a trace
whose collection was unavailable or degraded.

P2.81 remains the already-recorded host qualification/substrate cleanup unit.
The versioned runtime successor is therefore P2.82.

This unit performed no implementation, build, image generation, D0, approval,
device contact, transfer, reboot, or flash. No S22+ F1 live run is authorized.

## Frozen Evidence

The design depends on these exact-source facts:

1. `mode_store()` calls `dwc3_msm_set_role()`.
2. DEVICE sets `vbus_active=true`; NONE sets it false unless a DP session
   causes the write to return without changing the role.
3. `dwc3_msm_set_role()` calls `dwc3_ext_event_notify()`.
4. `dwc3_ext_event_notify()` derives `B_SESS_VLD` from `vbus_active` and queues
   `dwc3_otg_sm_work()`.
5. `dwc3_otg_sm_work()` consumes `B_SESS_VLD` and calls
   `dwc3_otg_start_peripheral(..., true|false)`.
6. peripheral start holds one child runtime-PM reference; peripheral stop
   releases it and explicitly attempts child suspend if needed.
7. a DEVICE child runtime resume calls `dwc3_core_init_for_resume()`, which
   reaches `dwc3_core_init()` and `usb_phy_init()`.
8. the active femto USB2 PHY's `msm_hsphy_init()` requests power, clocks,
   reset, and PHY programming.
9. `dwc3_core_init()` ignores the return values from legacy
   `usb_phy_init()`. A negative `msm_hsphy_init()` can therefore coexist with
   a later non-negative child-resume return and must be observed directly.
10. `dwc3_gadget_pullup()` supports two valid shapes: direct run-stop when the
    child is already active, or resume-nested run-stop when
    `pm_runtime_get_sync()` resumes it.
11. P2.80 parsed both shapes but collapsed them into retained detail `0xb22`.

Exact local source anchors:

```text
/tmp/p280-postlive-phy-20260728/kernel_platform/msm-kernel/
  drivers/usb/dwc3/dwc3-msm-core.c:
    474-480, 3939-4009, 4721-4779, 4834-4865, 6633-6766, 6828-6896
  drivers/usb/dwc3/core.c:
    1006-1020, 1745-1768, 1771-1842, 1909-1953
  drivers/usb/dwc3/gadget.c:
    2606-2669, 4605-4627
  drivers/usb/phy/phy-msm-snps-hs.c:
    379-557, 610-650, 764-840
```

Exact module identities remain:

```text
dwc3-msm.ko:
  8913b050419e88699033e957d927beef86742ed035f531dc5c4729f50cea60f1
phy-msm-snps-hs.ko:
  22a866320ba0de46619484efafaf0cf7ea3f7ba387cee7c3dd085f3a82492e94
```

The successor source contract must bind those modules, the selected vmlinux,
the candidate config, the exact source bodies, and every derived post-call
offset.

## Upstream Cross-Check and Corrections

Qualcomm engineer Krishna Kurapati's upstream commit
[`c0aabed9cabe`](https://kernel.googlesource.com/pub/scm/linux/kernel/git/torvalds/linux/+/c0aabed9cabe)
states that pull-up can intentionally rely on runtime resume to run core init,
followed by gadget resume and run-stop. The exact FYG8 source contains that
error-propagating pull-up shape. The controlled child resume is therefore a
supported driver path, not a private register workaround.

The same upstream change also documents the relevant evidence trap: UDC
control can report success while a failed core-init path never reaches
run-stop. P2.82 consequently treats UDC visibility, runtime resume, PHY init,
run-stop, bus state, and host receipt as separate boundaries.

Two contextual Qualcomm DT precedents are valid but do not prove FYG8
behavior:

- SDM845 MTP was temporarily fixed to peripheral mode until charger/OTG
  support was available in
  [`9000a55bedb4`](https://kernel.googlesource.com/pub/scm/linux/kernel/git/torvalds/linux/+/9000a55bedb4).
- SM8450 QRD later moved from fixed peripheral operation to PMIC-GLINK-linked
  role switching in
  [`f578e5f0b8b5`](https://kernel.googlesource.com/pub/scm/linux/kernel/git/torvalds/linux/+/f578e5f0b8b5f81e19e5f97a95e9cadf4e9c699d).

One proposed upstream analogy is rejected. Commit
[`db638c6500ab`](https://kernel.googlesource.com/pub/scm/linux/kernel/git/torvalds/linux/+/db638c6500abaffb8f7770b2a69c40d003d54ae1)
gates D+ pull-up on B-Session for **DWC2**, not DWC3. It cannot establish a
DWC3 requirement.

The exact FYG8 candidate also does not bypass the vendor OTG state machine.
Its path is:

```text
mode_store
  -> dwc3_msm_set_role
  -> vbus_active / ID update
  -> dwc3_ext_event_notify
  -> B_SESS_VLD update
  -> queue dwc3_otg_sm_work
  -> dwc3_otg_start_peripheral
```

The design therefore does not add a second B-Session mechanism and does not
force child or parent host role.

## Scope Freeze

P2.82 answers one question:

> After an exact child suspend fence, does the standard DEVICE runtime-resume
> path perform a clean software PHY reinitialization, and does one subsequent
> UDC bind reach exact host-visible ACM?

It does not attempt to prove the original natural boot-time LDO-drop
hypothesis. The earlier proposed pre-module "Window I" is omitted because it
cannot change the intervention decision and would add another trace lifetime,
another parser surface, and another pre-module failure mode. A successful
P2.82 proves repair sufficiency, not the historical cause.

P2.82 must not add or perform:

- parent or child `host` role;
- direct regulator, clock, reset, MMIO, PMIC, GPIO, or power-domain writes;
- `power/control`, `runtime_usage`, debugfs, or struct-offset PM writes;
- a second gadget bind or unbind/rebind retry;
- physical cable replug as part of the accepted proof;
- a new tracing framework or global tracer reset;
- an extra module, firmware file, gadget function, or Android service; or
- any partition action beyond the unchanged later boot-only Process v2 path.

## Stage Contract

The P2.80 prefix through initial role/UDC stage `0x8d` remains
source-contract- and behavior-equivalent: the external paths, writes, banner
queue, stage order, and bounded checks before `0x8d` do not change. Linked code
addresses and bytes are not assumed stable after adding the successor logic.
P2.82 inserts three local stages before UDC bind and shifts the last three
stages:

| Generation | Stage | Meaning |
|---:|---:|---|
| 86 | `0x8d` | existing initial parent peripheral plus exact real UDC |
| 87 | `0x8e` | parent NONE write accepted and stop worker classified |
| 88 | `0x8f` | exact child `runtime_status=suspended` fence |
| 89 | `0x90` | parent DEVICE restart plus child resume/reinit classified |
| 90 | `0x91` | one UDC bind plus direct/resume bind branch classified |
| 91 | `0x92` | exact UDC state and current-speed tuple |
| 92 | `0x93` | zero-detail terminal success |

Every stage is written. No generation is skipped, so the existing two-slot
adjacency rule remains valid. A `0x92` configured/high-speed progress record
is followed by `0x93`; a `0x92` failure remains adjacent to the `0x91` bind
record.

The carrier remains exactly 45 bytes: one 25-byte run-bound header and two
10-byte A/B slots. Checkpoints replace the inactive slot in place and do not
advance the Samsung ring index or append another record. Generation 92 fits
the `u8` field. Implementation must prove this geometry and stale-run
rejection for every P2.82 success and failure stage before Full LTO.

All inserted steps are local item index zero. Module/gate item indices and
their existing regression/read-error bands remain unchanged.

## Controlled Sequence

The exact runtime order is:

1. Require the existing `0x8d` role and exact UDC result.
2. Preserve the already-open `ttyGS0` and exact 49-byte banner queued by the
   unchanged P2.80 prefix before `0x8d`; do not perform a second banner write.
3. Set up one isolated cycle trace instance and clear its bounded buffer.
4. Write exactly `none\n` to the existing parent mode node.
5. Require exact parent mode readback `none`.
6. Observe or time-bound the stop worker.
7. Require exact child `power/runtime_status` readback `suspended`.
8. Write exactly `peripheral\n` to the same parent node.
9. Require the start worker and exact child `runtime_status=active`.
10. Require exact parent mode `peripheral` and exact
   `/sys/class/udc/a600000.dwc3` membership.
11. Finish and verify cycle-trace cleanup.
12. Set up the existing versioned bind trace.
13. Perform exactly one configfs UDC bind.
14. Preserve direct versus resume-nested run-stop.
15. Read exact `(UDC state, current speed)` pairs until two consecutive reads
    are byte-identical and configured/high-speed, or until the bounded
    deadline. At the deadline, a byte-identical final pair becomes its exact
    tuple; a changing canonical pair becomes `0xc4b`.
16. Publish the generated tuple and, on configured/high-speed, terminal
    `0x93`. The host observer independently receives the banner queued at
    step 2.

The cycle trace remains armed continuously from before `none` through the
final peripheral/active fence. There is no unobserved gap in which an external
producer can resume the child and be mistaken for the controlled restart.

The stop half has one 30-second absolute deadline covering the NONE write,
readback, stop worker, and suspended fence. The restart half has one separate
30-second absolute deadline covering the DEVICE write, readback, start worker,
active fence, and exact UDC membership. Polling remains 100 ms. The final
configured wait retains its existing 30-second bound. Implementation must
recompute the manifest observation bound from the complete worst-case runtime
and guard lifetime before packaging; it must not reuse the previous value by
convention.

The derived execution bounds are `observation.timeout_sec=300` and a
360-second transient udev guard lifetime. The extra 60 seconds keeps guard
arming and host-side transition overhead outside the negative-observation
window; exact banner receipt remains valid if guard health later degrades.

## Trace Contract

Reuse P2.80's isolated tracefs instance, 64-KiB per-CPU buffer, counter clock,
module-qualified symbol resolution, event readback, `nmissed` validation, and
owned cleanup.

### Cycle window

The cycle descriptor contains ordered entry/return pairs for:

```text
dwc3-msm:dwc3_otg_start_peripheral(on=0|1)
dwc3_runtime_suspend()
dwc3_runtime_resume()
phy-msm-snps-hs:msm_hsphy_set_suspend(suspend=1)
phy-msm-snps-hs:msm_hsphy_enable_power(on=0|1)
phy-msm-snps-hs:msm_hsphy_init()
phy-msm-snps-hs:msm_hsphy_notify_connect()
```

The parser selects ordered subsequences within the bounded, freshly cleared
phase. It must not require global singleton event counts. It rejects
contradictory relevant events, foreign ordering inside a selected call tree,
missing return fields, nonzero `nmissed`, and source-incompatible nesting.
Each selected entry/return pair and its nested callbacks must share the exact
`common_pid` of the enclosing parent call and fall between that call's entry
and return timestamps. Events from other tasks remain permitted background
data and cannot satisfy or invalidate the selected subtree.

The stop subtree is selected from `start_peripheral(on=0)`. The restart
subtree is selected from `start_peripheral(on=1)`. Child suspend/resume and
femto callbacks must be nested within their corresponding parent calls when
the trace is authoritative.

### Bind window

Retain P2.80's pull-up, optional child runtime-resume, and run-stop pairs.
Unlike P2.80, preserve one of:

```text
direct run-stop
resume-nested run-stop
bind diagnostic degraded
```

The upstream-supported resume-nested shape is not a contradiction.

### Diagnostic precedence

- Trace setup, registration, or read loss is fail-soft only after complete
  ownership cleanup. Exact sysfs fences and primary ACM proof may continue,
  but the repair/bind class becomes `diagnostic-degraded`.
- Any unverified event, instance, or mount cleanup is fail-closed before UDC
  bind.
- An exact run-bound banner remains primary positive evidence even if a
  fail-soft diagnostic warning exists.
- Banner absence with degraded host guard or degraded device trace is not
  attributed to a specific device boundary.

## Detail Namespace

P2.82 inherits the existing bands and reserves:

```text
0xc00..0xcff  cycle, reinit, and bind control classifications
0xd00..0xf36  generated final repair/bind/state/speed tuples
```

Band dispatch occurs before any low-byte gate interpretation. No handwritten
range upper bound or duplicated decoder table is permitted.

### Instrumentation details

| Detail | Name | Outcome |
|---:|---|---|
| `0xc01` | cycle-trace-control-unavailable | progress warning |
| `0xc02` | cycle-trace-registration-unavailable | progress warning |
| `0xc03` | cycle-trace-incomplete | progress warning |
| `0xc04` | cycle-trace-cleanup-unverified | failure |
| `0xc05` | cycle-trace-source-contradiction | failure |
| `0xc06` | cycle-helper-source-contradiction | failure |

The generated stage allowlist is exact:

```text
0xc01..0xc03  progress only at 0x8e, 0x8f, or 0x90
0xc04         failure only at 0x90
0xc05         failure only at 0x8e, 0x8f, or 0x90
0xc06         failure only at 0x8e or 0x90
```

`0xc01..0xc03` remain sticky through the cycle. The first successful cycle
stage publishes the exact warning; later successful stages publish that same
warning until the generated final tuple preserves repair class
`diagnostic-degraded`. A failed sysfs fence publishes its concrete failure
instead. No warning is written before the stage's primary action succeeds, so
the runtime never publishes progress and failure for the same generation.

### Stop and suspend details

| Detail | Name | Outcome |
|---:|---|---|
| `0xc10` | none-readback-not-reached | failure at `0x8e` |
| `0xc11` | stop-worker-not-entered | failure at `0x8e` |
| `0xc12` | stop-worker-no-return | failure at `0x8e` |
| `0xc13` | stop-worker-unexpected-return | failure at `0x8e` |
| `0xc14` | child-suspend-not-entered | failure at `0x8f` |
| `0xc15` | child-suspend-no-return | failure at `0x8f` |
| `0xc16` | child-suspend-negative | failure at `0x8f` |
| `0xc17` | child-status-not-suspended | failure at `0x8f` |
| `0xc18` | suspended-power-helper-off-zero | progress at `0x8f` |
| `0xc19` | suspended-no-power-helper-off | progress at `0x8f` |
| `0xc1a` | suspended-power-helper-off-negative | progress at `0x8f` |

`msm_hsphy_enable_power(..., false)` is not itself a hard gate. Its caller
ignores the return and policy such as DPDM/EUD may intentionally retain a
vote. A zero return can also be an idempotent no-op when `power_enabled` was
already false. These details classify only the helper call and return, never
an analog rail transition.

### Restart and reinit details

| Detail | Name | Outcome |
|---:|---|---|
| `0xc20` | peripheral-readback-not-reached | failure at `0x90` |
| `0xc21` | start-worker-not-entered | failure at `0x90` |
| `0xc22` | start-worker-no-return | failure at `0x90` |
| `0xc23` | start-worker-unexpected-return | failure at `0x90` |
| `0xc24` | child-resume-not-entered-after-suspend | failure at `0x90` |
| `0xc25` | child-resume-no-return | failure at `0x90` |
| `0xc26` | femto-init-not-entered-in-resume | failure at `0x90` |
| `0xc27` | femto-power-on-not-entered-in-init | failure at `0x90` |
| `0xc28` | femto-power-on-negative | failure at `0x90` |
| `0xc29` | femto-init-negative | failure at `0x90` |
| `0xc2a` | child-resume-negative-after-init | failure at `0x90` |
| `0xc2b` | hsphy-notify-connect-missing | failure at `0x90` |
| `0xc2c` | child-status-not-active | failure at `0x90` |
| `0xc2d` | parent-mode-not-peripheral | failure at `0x90` |
| `0xc2e` | exact-udc-regression-after-restart | failure at `0x90` |
| `0xc2f` | reinit-power-helper-off-on-zero | progress at `0x90` |
| `0xc30` | reinit-software-only | progress at `0x90` |

Classification precedence follows execution order. A clean negative
power-helper return wins over the derived init return (`0xc28` before
`0xc29`). A clean negative init return wins over the later child-resume return
because legacy `usb_phy_init()` discards it. A non-negative child resume can
therefore never erase `0xc28` or `0xc29`.

### Bind details

| Detail | Name | Outcome |
|---:|---|---|
| `0xc40` | helper-off-on-zero-direct-run-stop | progress at `0x91` |
| `0xc41` | helper-off-on-zero-resume-run-stop | progress at `0x91` |
| `0xc42` | software-direct-run-stop | progress at `0x91` |
| `0xc43` | software-resume-run-stop | progress at `0x91` |
| `0xc44` | degraded-direct-run-stop | progress at `0x91` |
| `0xc45` | degraded-resume-run-stop | progress at `0x91` |
| `0xc46` | bind-diagnostic-branch-unknown | progress warning at `0x91` |
| `0xc47` | bind-pullup-zero-without-run-stop | failure at `0x91` |
| `0xc48` | nested-run-stop-negative | failure at `0x91` |
| `0xc49` | bind-trace-source-contradiction | failure at `0x91` |
| `0xc4a` | bind-trace-cleanup-unverified | failure at `0x91` |
| `0xc4b` | final-state-speed-unstable | failure at `0x92` |

Direct UDC-write or read failures retain their bounded errno/read-validation
classification rather than being flattened into this table.

### Deterministic precedence

For each stage, exactly one retained result is selected:

1. unverified trace ownership cleanup;
2. exact helper/source or clean-trace/source contradiction;
3. synchronous syscall or exact-read failure;
4. the earliest clean-trace call boundary that failed, in descriptor order;
5. the exact sysfs postcondition failure;
6. clean progress classification; or
7. diagnostic-degraded progress when trace collection was fail-soft.

At `0x90`, the restart call order is parent start, child resume, femto init,
power-on helper, init return, child-resume return, connect notify, then the
active/peripheral/UDC fence. The first failing boundary wins. A negative
power-on helper therefore wins over the derived init return, and a negative
init return wins over a later non-negative child-resume return.

At `0x91`, unverified cleanup outranks the UDC-write result. An exact
UDC-write errno comes next; only a successful bind is eligible for
trace/source contradiction or direct/resume/degraded branch classification.
At `0x92`, malformed or unreadable values use the existing exact read-error
path, canonical-but-changing pairs use `0xc4b`, and only a stable pair enters
the generated tuple. No earlier warning or progress detail can replace it.

Fail-soft trace loss can never produce `worker-not-entered`,
`resume-not-entered`, `init-not-entered`, or another clean negative claim.
Those details require an authoritative trace. With degraded tracing, only the
exact sysfs fences and final state/speed tuple remain primary.

## Generated Final Tuple

One authoritative descriptor defines three repair classes, three bind
branches, nine canonical UDC states, and seven canonical speeds:

```text
repair:
  0 power-helper-off-on-zero
  1 software-reinit-no-confirmed-helper-zero-pair
  2 diagnostic-degraded

bind:
  0 direct-run-stop
  1 resume-nested-run-stop
  2 diagnostic-degraded

state:
  0 not attached
  1 attached
  2 powered
  3 default
  4 addressed
  5 configured
  6 reconnecting
  7 unauthenticated
  8 suspended

speed:
  0 UNKNOWN
  1 low-speed
  2 full-speed
  3 high-speed
  4 wireless
  5 super-speed
  6 super-speed-plus
```

The nine states are the kernel `usb_state_string()` domain documented by the
[UDC sysfs ABI](https://kernel.googlesource.com/pub/scm/linux/kernel/git/stable/linux-stable/+/v4.1.6/Documentation/ABI/stable/sysfs-class-udc).
The runtime uses the exact source-emitted `not attached` spelling with a space,
not the older ABI prose's `not-attached` spelling. The seven speeds are pinned
to the exact FYG8 `usb_speed_string()` table.

Repair class zero requires an authoritative trace with zero-return
`enable_power(false)` and `enable_power(true)` calls in the selected
suspend/reinit subtrees. It does not assert that either call changed
`power_enabled`. Class one covers a clean full init/reset/connect sequence
without that exact zero-return pair, including a negative or absent off
helper. Class two is used whenever cycle tracing is fail-soft degraded.

Bind class zero or one requires an authoritative direct or resume-nested
run-stop parse respectively. Bind class two is used when bind tracing is
fail-soft degraded. A clean negative or source contradiction never enters the
tuple.

The exact detail is:

```text
0xd00 + ((((repair * 3) + bind) * 9 + state) * 7 + speed)
```

This generates exactly 567 allowlisted values from `0xd00` through `0xf36`.
Malformed, unknown, or unreadable strings do not enter this tuple; they use
the existing read/validation failure path. A tuple is generated only after
two consecutive pair reads are byte-identical. If individually canonical
values keep changing through the deadline, `0xc4b` is retained instead of a
mixed-time tuple.

Examples:

```text
0xd00  helper-off-on-zero + direct + not-attached + UNKNOWN
0xd3f  helper-off-on-zero + resume + not-attached + UNKNOWN
0xdbd  software + direct + not-attached + UNKNOWN
0xef8  degraded + degraded + not-attached + UNKNOWN
0xd26  helper-off-on-zero + direct + configured + high-speed
0xde3  software + direct + configured + high-speed
0xf1e  degraded + degraded + configured + high-speed
```

At stage `0x92`:

- `configured + high-speed` is a progress tuple followed by terminal `0x93`;
- every other canonical tuple is a failure;
- the tuple is self-contained, so a success still preserves repair and bind
  class in the slot adjacent to terminal;
- no result depends on a progress record older than the retained A/B pair.

## Exhaustive Decision Table

| Observed boundary | Retained result | What it establishes | What it does not establish | Next unit |
|---|---|---|---|---|
| trace setup/read unavailable, cleanup verified | `0xc01..0xc03` warning; continue degraded | primary cycle may still run | causal trace branch | continue once |
| trace cleanup unverified | `0xc04` failure | probe ownership is unsafe | any USB conclusion | host audit only |
| role helper contradicts its receipt | `0xc06` failure | helper/parent contract drift | role transition | fix contract |
| NONE write returns bounded errno | errno at `0x8e` | write failed synchronously | worker behavior | source/sysfs audit |
| NONE never reads back | `0xc10` | requested stop state not established | DP, external reassert, or worker cause | focused role audit |
| NONE reads back, stop worker absent | `0xc11` | role value changed without observed stop | child suspend | worker queue audit |
| stop worker enters but does not return | `0xc12` | stop path stalled | later PM/USB state | exact call-site audit |
| stop worker returns source-incompatible value/order | `0xc13` or `0xc05` | trace/source contradiction | device root cause | fix classifier/source pin |
| child suspend never enters | `0xc14` | controlled suspend was not invoked | PHY or bus failure | child-PM audit |
| child suspend enters but does not return | `0xc15` | suspend callback stalled | restart feasibility | callback audit |
| child suspend returns negative | `0xc16` | suspend failed explicitly | reinit result | error-path audit |
| no exact suspended status by deadline | `0xc17` | hard suspend fence absent | whether a brief transition occurred | no bind; PM audit |
| suspended plus zero-return power-off helper | `0xc18` progress | controlled suspend plus helper call/return | helper body changed state or analog rail voltage | restart |
| suspended without power-off helper | `0xc19` progress | controlled suspend only | LDO off/on cycle | restart as software reinit |
| suspended plus negative power-off helper | `0xc1a` progress | caller ignored an exact helper error | LDO state | restart as software reinit |
| suspended with trace loss | `0xc01..0xc03` progress | sysfs suspend fence only | callback order | restart degraded |
| DEVICE write returns bounded errno | errno at `0x90` | restart write failed | child resume | source/sysfs audit |
| DEVICE never reads back | `0xc20` | restart role not established | child resume | focused role audit |
| start worker absent | `0xc21` | parent start not invoked | child resume | worker queue audit |
| start worker does not return | `0xc22` | parent start stalled | later connect state | exact call-site audit |
| start worker contradicts source | `0xc23` or `0xc05` | trace/source mismatch | device root cause | fix contract |
| confirmed suspended child has no resume entry | `0xc24` | controlled restart did not own a child resume | whether another producer resumed it outside a valid trace | child-PM producer audit |
| child resume enters but does not return | `0xc25` | resume stalled | PHY completion | resume audit |
| resume lacks femto init | `0xc26` | full DEVICE reinit path was not observed | why dispatch differed | role/source audit |
| init lacks power-on helper | `0xc27` | exact femto source path diverged | power state | source/CFI audit |
| power-on helper returns negative | `0xc28` | software power request failed | analog state | regulator dependency audit |
| femto init returns negative | `0xc29` | PHY init failed even if child resume later returns zero | downstream link | init error audit |
| init is non-negative, child resume negative | `0xc2a` | a later core-resume boundary failed | bus attach | core-resume audit |
| resume/init succeed, connect notify absent | `0xc2b` | parent connect sequence incomplete | electrical attach | parent worker audit |
| child does not reach exact active status | `0xc2c` | child restart postcondition absent | parent role or UDC | child runtime-PM audit |
| parent does not read exact peripheral | `0xc2d` | parent role postcondition absent | child or UDC status | role producer audit |
| exact real UDC membership regresses | `0xc2e` | expected controller disappeared after restart | bind behavior | UDC lifecycle audit |
| zero-return power-helper pair plus reinit | `0xc2f` progress | both helper calls returned zero and init/reset/connect completed | either helper changed state, analog voltage, or host attach | bind once |
| full software reinit without a confirmed zero-return helper pair | `0xc30` progress | init/reset/connect sequence completed | LDO-cycle causality | bind once |
| status fences pass with diagnostic loss | `0xc01..0xc03` progress | bounded state transition only | callback causality | bind once degraded |
| configfs UDC bind returns errno | errno at `0x91` | bind failed synchronously | pull-up or bus | configfs/UDC audit |
| pull-up zero with no run-stop | `0xc47` | UDC-visible success lacks controller start | physical link | pull-up branch audit |
| resume-nested run-stop is negative | `0xc48` | controller start failed in resume branch | bus attach | exact run-stop error audit |
| clean bind trace contradicts source | `0xc49` | classifier/source mismatch | device root cause | fix contract |
| bind cleanup unverified | `0xc4a` | instrumentation ownership unsafe | bus result | host audit only |
| canonical state/speed pair never stabilizes | `0xc4b` at `0x92` | final observation raced through the deadline | any single coherent final tuple | timing/state audit |
| clean/degraded run-stop plus any canonical state/speed | generated `0xd00..0xf36` at `0x92` | exact repair, bind, state, speed tuple | analog cause when not configured | tuple-selected next unit |
| configured/high-speed tuple | tuple progress then `0x93` | device-side E3 terminal | host receipt or rollback | require observer + rollback |
| terminal + exact 49-byte banner + healthy rollback | Process v2 PASS | exact device-to-host ACM and recovery | E4 request/response | begin E4 design |
| terminal + exact banner + guard warning | PASS with guard warning | exact run-bound bytes cannot be synthesized by guard loss | clean negative observation | begin E4 design |
| terminal + no banner, guard healthy | no E3 host proof | device reached terminal | why host missed bytes | observer/host transport audit |
| terminal + no banner, guard lost | indeterminate host observation | device reached terminal only | banner absence attribution | repair observer before retry |
| no terminal + no banner | retained boundary result only | exact last device boundary if record valid | later path | table-selected H0 unit |

The five headline outcomes are therefore closed:

```text
child never suspends:
  NONE/write/worker boundary or 0xc10..0xc17

child suspends but does not resume:
  DEVICE/write/worker boundary or 0xc20..0xc25

child resumes but PHY init fails:
  0xc26 / 0xc27 / 0xc28 / 0xc29 / 0xc2a

PHY init succeeds but UDC remains not attached:
  0xc2b / 0xc2c / 0xc2d / 0xc2e before bind, or
  generated tuple with state=not-attached after bind

success:
  generated configured/high-speed tuple + terminal 0x93
  + exact observer banner + verified rollback
```

There is no unclassified headline result.

## Single Source of Truth

One P2.82 descriptor owns:

- stages and item indices;
- cycle and bind event descriptors;
- detail values, categories, outcomes, and stage allowlists;
- repair, bind, UDC-state, and speed enums;
- the generated tuple formula and legal range;
- canonical sysfs strings;
- exact role writes and forbidden host role; and
- safety-authority declarations.

It generates:

1. C headers/tables for the runtime;
2. parser event tables;
3. host decoder names and categories;
4. slot validation allowlists;
5. source-contract expectations;
6. safety dictionary entries; and
7. exhaustive and mutation tests.

Independent handwritten bounds, duplicate path maps, duplicate speed/state
tables, global cardinality predicates, and exact incidental ELF-string sets
are prohibited.

## Static Validation Before Full LTO

Full LTO is forbidden until one immutable pre-LTO receipt proves:

1. exact intent, source-contract, runtime, descriptor, module, vmlinux, and
   config identities, plus an unchanged pre-`0x8d` external-action sequence
   and exactly one pre-bind banner write;
2. two same-path userspace links with byte-identical `/init` and derived
   entrypoint rather than a literal address;
3. all 567 generated tuples round-trip through C and Python decoders;
4. one pinned AArch64 fixture executes the same production C classifier used
   by the runtime and emits all 46 C-band details, each only at its declared
   stage/outcome; this is reported separately from `0/46` FYG8 end-to-end
   device coverage;
5. every decision-table headline path reaches exactly one classification;
6. direct and resume-nested run-stop mutations decode differently;
7. child-no-suspend, no-resume, power-off-negative, power-on-negative,
   init-negative, resume-negative, successful-reinit/no-attach, and exact
   success fixtures;
8. a trace-loss mutation cannot become a clean negative claim;
9. a cleanup-loss mutation always fails closed;
10. an extra unrelated event does not fail via singleton counting;
11. a contradictory relevant event fails;
12. exact canonical state/speed parsing, stable-pair enforcement, and every
    invalid-string or pair-race mutation;
13. required paths versus incidental ELF strings remain separate;
14. updated safety dictionary includes exactly two additional bounded parent
    writes (`none`, `peripheral`) and no new power authority;
15. generic tracefs/QEMU lifecycle tests with pinned substrate;
16. static AArch64 compile/link and exact module-qualified symbol resolution;
17. a fixed 45-byte A/B geometry receipt covers every success/failure stage,
   generation through 92, stale-run rejection, and unsaturated boundaries;
18. observation/guard timing receipt covers the complete worst case; and
19. focused plus historical Process v2 tests.

The known-good P2.80 linked artifact and synthetic fixtures are meta-test
inputs. A new checker that rejects an applicable known-good shape, or accepts
its intended mutation, blocks Full LTO before any kernel build.

QEMU can validate tracefs mechanics, parser behavior, configfs/gadget ordering,
exact host receipt, and all shared production C classifier outputs under
synthetic observations. It cannot prove Qualcomm DWC3-MSM, femto PHY,
electrical attach, the controlled hardware cycle, or any FYG8 end-to-end
C-band path.

## Safety and Timing

The additional candidate authority is exactly two writes to the existing
parent mode node, before UDC bind:

```text
none
peripheral
```

The first write invokes the standard vendor stop path and child runtime
suspend. The second invokes the standard vendor start path and child DEVICE
runtime resume. No direct low-level power write is added.

The implementation safety dictionary must say this explicitly. It must not
retain a stale claim of no userspace sysfs writes.

The execution remains bounded and recoverable:

- one child cycle;
- one UDC bind;
- no retry loop;
- no host role;
- no physical-edge acceptance path;
- quiet park after terminal/failure;
- exact boot-only candidate and preverified Magisk rollback later under
  Process v2.

Implementation must add the two 30-second cycle budgets to the candidate
runtime calculation, measure QEMU/host overhead, and derive a fresh observer
and udev-guard lifetime. Guard expiry remains asymmetric: exact banner receipt
survives as positive evidence, while banner absence under guard loss is
indeterminate.

## Implementation Units

The next work is bounded and ordered:

1. **P2.82 contract/spec only:** descriptor, generated detail tables, decoder,
   exhaustive decision-table tests, and source/safety contract.
2. **P2.82 runtime only:** one continuous cycle trace, the two parent writes,
   exact child fences, inherited bind trace, and tuple publication.
3. **Pre-LTO qualification:** all 19 gates above plus one changed-closure
   adversarial review.
4. **Only then Full-LTO A/B:** no exploratory build and no checker repair
   after the pair.
5. **Offline package/promotion/ready manifest:** fresh timing and observer
   binding.
6. **D0 and F1 remain separate:** neither is authorized by this design.

If implementation discovers an outcome not represented by the table, the
design reopens and Full LTO remains blocked. Otherwise this contract is frozen;
do not add another mechanism hypothesis or diagnostic target before the next
bounded result.
