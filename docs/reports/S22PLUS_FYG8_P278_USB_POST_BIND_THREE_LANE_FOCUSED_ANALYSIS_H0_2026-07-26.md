# S22+ FYG8 P2.78 USB post-bind three-lane focused analysis

Date: 2026-07-26 KST
Tier: H0
Status: `FOCUSED_ANALYSIS_COMPLETE`
Device contact: none

## Question

P2.76 proved the exact real UDC bind at stage `0x8e`, then timed out while
waiting for exact `configured` plus `high-speed` at stage `0x8f`. The host ACM
observer received nothing, and the planned host USB trace sidecar was not
running. This unit asks what can be established before another candidate:

1. Does stock Android perform a missing vendor-specific userspace or firmware
   step before enabling the gadget?
2. Does the exact FYG8 DWC3 path support a RUN_STOP or `soft_connect` recovery
   hypothesis?
3. Which host evidence is needed to distinguish no attach from failed USB
   enumeration?

The combined answer is:

```text
stock hidden USB-enable write: strongly ruled down for the minimal ACM path
selected-module firmware dependency: ruled out
explicit peripheral mode write in P2.76: not proved to have executed
DWC3 parent transition completion: unobserved
old RUN_STOP erratum: unverified and low priority
blind soft_connect retry: not justified before state capture
host attach/reset/descriptor progress: unobserved because sidecar was absent
```

The strongest new finding is not a new module or an Android daemon. It is a
semantic gap in the current role step: stage `0x8d` can pass without executing
the active `mode_store("peripheral")` transition.

## Boundary and Method

This is a host-only, read-only analysis unit. It performs no build, image
generation, candidate mutation, D0, approval, Odin session, reboot, flash, or
device write. The frozen P2.76 execution closure is unchanged.

The method is evidence-first:

1. reopen exact FYG8 stock USB reports and live stock captures;
2. reopen the exact P2.60 runtime and source/QEMU contracts used by P2.76;
3. trace exact FYG8 DWC3-MSM, DWC3 gadget, and UDC-core source;
4. inspect the P2.74 sidecar and exact P2.76 private run shape without
   publishing raw identifiers;
5. compare narrow upstream documentation and the historical RUN_STOP patch
   discussion; and
6. assign every hypothesis a disposition and proof limit.

## Live Evidence Baseline

P2.76 established:

```text
0x88  configfs mounted and validated
0x89  gadget and descriptors created
0x8a  ACM function linked
0x8b  ttyGS0 opened
0x8c  exact banner queued
0x8d  parent mode read as peripheral and exact UDC member existed
0x8e  configfs UDC bind write/readback succeeded
0x8f  ETIMEDOUT before configured/high-speed
host ACM bytes = 0
```

The candidate booted without a boot loop. One exact rollback and final health
completed. The transaction is closed. This unit does not reinterpret the
durable verdict as PASS.

Stage `0x8e` rules out gadget-local construction failure, exact UDC absence,
and a synchronous error returned by the initial configfs bind. It does not
prove host attach, reset, descriptor exchange, address assignment, or
configuration.

## Lane 1: Stock Android Userspace and Firmware

### Exact stock recipe

The exact rooted FYG8 stock capture records:

```text
vendor.usb.use_gadget_hal=0
UDC=a600000.dwc3
parent mode=peripheral
UDC state=configured
UDC speed=super-speed
```

The active gadget composition is driven by
`/vendor/etc/init/hw/init.qcom.usb.rc`, not the Gadget HAL. Its relevant order
is the normal configfs order:

1. mount configfs;
2. create gadget, strings, functions, and configuration;
3. unbind the old UDC;
4. link selected functions; and
5. write `a600000.dwc3` to `UDC` last.

The exact stock rc contains no write to `dr_mode`, `usb_role`, or the
DWC3-MSM parent `mode` attribute. Stock obtains peripheral role from its
automatic Type-C/PD/notifier path, then activates the composed gadget with the
final UDC write.

Stock uses FunctionFS readiness properties before binding its MTP/ADB
composition. Those gates are requirements of that stock composite, not a
generic prerequisite for a standalone ACM function. The exact P2.70
generic-arm64 QEMU execution completed the same minimal configfs/ACM sequence
through configured state and exact host receipt. It does not model Qualcomm
role or PHY hardware, but it strongly rules down a missing generic Android
userspace ceremony before a minimal ACM UDC bind.

### Automatic stock role chain

Exact DT, module, and callback analysis already reconstructed the stock chain:

```text
max77705/PDIC
  -> usb_typec_manager
  -> usb_notifier_qcom
  -> usb_notify_layer
  -> DWC3-MSM external event/state machine
```

The child is `dr_mode=otg`, and the board carries role-switch links. This chain
explains how stock reaches peripheral mode without an rc write.

The earlier M34 report concluded that missing Max77705/PDIC state was the best
then-current explanation. Later V3425 source analysis proved that the parent
`mode` sysfs callback is an active bypass: if `mode_store("peripheral")`
executes after DWC3-MSM bind, it can directly set the parent role inputs and
queue the same state machine without waiting for the automatic notifier
producer. P2.76 did not prove that this callback actually executed, so the
V3425 bypass remains valid but was not necessarily consumed by the live run.

### Firmware subaudit

Missing `/vendor/firmware` remains a general bare-PID1 hazard, but it is not a
direct producer in the exact selected closure:

- the candidate contains exactly 60 selected vendor-ramdisk modules;
- their qualification result records
  `request_firmware_string_hits=0`;
- `modinfo -F firmware` is empty for every selected module;
- undefined-symbol inspection found no selected
  `request_firmware*`, `firmware_request*`, or `firmware_upload*` reference;
- `mfd_max77705.ko` and `pdic_max77705.ko`, which belong to the wider stock
  automatic role chain and may carry firmware-update behavior, are not
  selected.

Disposition:

```text
external firmware file missing from a selected driver: RULED_OUT
unmodeled automatic Max77705 notifier side effects: OPEN but not a firmware-file result
```

Copying firmware or broadening the module set is not justified by P2.76.

## Lane 2: Exact DWC3 Role, RUN_STOP, and Soft Connect

### New correction: stage 0x8d does not prove a role write

The exact runtime first reads the parent role:

```c
if (!peripheral) {
    rc = p260_write_value(p260_role_path, "peripheral");
}
```

If the first read already returns `peripheral`, the runtime skips the write.
It then accepts:

```text
parent mode reads peripheral
exact a600000.dwc3 UDC member exists
```

as stage `0x8d`.

Exact FYG8 `mode_show()` derives its value only from:

```text
vbus_active
id_state
```

It does not read `drd_state`, `in_device_mode`, or completion of
`sm_work`. Therefore `peripheral` can be visible without proving that the
parent device transition has reached `dwc3_otg_start_peripheral()`.

If `mode_store("peripheral")` does execute, the exact source:

1. validates the requested role;
2. sets `vbus_active=true` and `id_state=float`;
3. calls `dwc3_ext_event_notify()`; and
4. returns after queueing new `sm_work`.

The new work performs PM resume, child DRD synchronization, VBUS override,
redriver and PHY connect notifications, DBM reset, `in_device_mode=true`, and
the child device-role transition. The sysfs write itself is not a completion
fence.

There are two distinct open cases:

```text
A. the write was skipped because mode already read peripheral;
B. the write ran, but the newly queued parent work had not completed.
```

P2.76 cannot distinguish them.

### Why existing host contracts missed the gap

The P2.60 source contract requires the write token to exist in source, but does
not prove which branch executes at runtime. The P2.70 QEMU harness deliberately
rejects and replaces both:

```text
p260_wait_role_and_udc()
p260_bind_udc()
```

because generic QEMU cannot reproduce the Qualcomm role/UDC boundary. It
validates generic configfs and ACM behavior, not the FYG8 parent-role
semantics. This is an explicit coverage boundary, not a QEMU failure.

### What the first UDC bind already did

The exact UDC and DWC3 source show that a successful initial configfs bind
reaches:

```text
usb_gadget_connect()
  -> dwc3_gadget_pullup(true)
     -> runtime PM resume
     -> core soft reset
     -> event-buffer setup
     -> gadget start
     -> DCTL.RUN_STOP=1
```

The exact write at stage `0x8e` returned success and read back the bound UDC.
The candidate therefore did not omit the ordinary initial DWC3 soft reset or
RUN_STOP request.

### Soft-connect proof limit

The exact UDC sysfs accepts:

```text
connect
disconnect
```

not `1` and `0`. More importantly, `soft_connect_store()` ignores the return
values from `usb_gadget_udc_start()` and `usb_gadget_connect()` and returns the
input length. A successful sysfs write is therefore not evidence that the
controller reconnected.

A bounded `disconnect -> delay -> connect` sequence would repeat the DWC3
disconnect/reconnect path and its core reset. It remains a plausible
race-recovery experiment, but only after the run records UDC state, link state,
parent transition evidence, and host events. Adding it to the next diagnostic
candidate would combine two behavioral variables and obscure whether the
parent role transition was the real gap.

### Historical RUN_STOP patch

The cited 2016 RUN_STOP workaround discussion concerns a specific USB2-only
integration and an old DWC3 revision range around `<2.20a`. The review thread
also records unresolved questions about whether the proposed soft reset
actually detects or fixes the erratum.

Current evidence does not establish:

- the exact runtime DWC3 IP revision in this FYG8 run;
- the erratum's detection condition; or
- that P2.76 stopped in the affected LTSSM state.

The exact FYG8 driver already performs a core soft reset on reconnect. The old
erratum is therefore `OPEN_LOW_PRIORITY`, not a reason to install a blind
retry.

### Available device-side diagnostics

The exact candidate kernel has `CONFIG_DEBUG_FS=y`. Exact DWC3 source creates:

```text
/sys/kernel/debug/usb/a600000.dwc3/link_state
```

in dual-role/gadget configurations. A read verifies current device mode and
reports the canonical DWC3 link state. It also runtime-resumes the controller,
and debugfs is not a stable userspace ABI. Use it once at the terminal
deadline as optional diagnostic evidence, never as an acceptance gate or a
high-frequency poll.

The FYG8 delta archive does not replace `drivers/usb/dwc3/debugfs.c`; the
effective file is inherited from the matching base kernel archive. The
candidate config independently confirms `CONFIG_USB_DWC3=y`,
`CONFIG_USB_DWC3_DUAL_ROLE=y`, and `CONFIG_DEBUG_FS=y`.

DWC3-MSM also creates Qualcomm IPC log contexts derived from
`a600000.ssusb`. Load-bearing markers include:

```text
mode_request
XCVR: BSV set
BIDLE gsync
StrtGdgt gsync
```

Exact path availability at the active Samsung debug level remains unproved.
Marker absence must therefore be `unavailable/unknown`, not failure.

## Lane 3: Host Evidence

### P2.76 sidecar absence

The exact P2.76 private run has the Process v2 observer artifacts but no
`host-usb-trace` directory. Consequently:

```text
no host connect event: UNPROVED
host reset/descriptor failure: UNPROVED
host saw no URB traffic: UNPROVED
```

The zero-byte ACM observer means no accepted ACM endpoint/banner appeared. It
does not classify the earlier bus states.

### Existing sidecar coverage and startup gap

The P2.74 sidecar captures:

- `journalctl --dmesg --follow`;
- kernel and udev USB/TTY events; and
- one `lsusb` snapshot at each end.

It is non-authoritative and does not open ACM. This is the right separation
from the candidate-bound observer.

However, its current `status=starting` line is printed before `capture()`
starts either long-running source. `start.json` and the initial `lsusb`
snapshot are also written before the source subprocesses start. There is no
durable receipt that both kernel and udev captures are alive.

Before the next F1, the sidecar should emit an explicit, durable `armed`
receipt only after both source processes have started and survived an initial
bounded liveness check. That receipt is a research-evidence precondition, not
a Process v2 safety verdict and not recovery authority.

### usbmon

The host kernel has `CONFIG_USB_MON=m`, the module is installed, and debugfs is
mounted. The module was not loaded during this H0 check. Capturing usbmon
requires attended root privilege.

usbmon records URB submissions, completions, and submission errors between
USB drivers and host-controller drivers. It can distinguish:

```text
host submitted reset/descriptor traffic and received errors
host submitted no URBs for a candidate device
```

It cannot by itself prove that no electrical pull-up occurred: if the host
never creates a device or submits a URB, its trace can remain empty. Kernel and
udev events remain the primary attach discriminator.

Add bounded usbmon only as optional enrichment when it can be armed before the
transaction. Do not delay or block F1 merely because optional usbmon privilege
is unavailable.

### Odin as positive control

P2.76 completed candidate and rollback Odin transfers over the same attended
physical setup. This strongly rules down gross cable, port, and host-stack
failure during those transfer windows.

Download mode uses bootloader USB firmware and a different controller state
from the candidate kernel. Odin success therefore does not prove the
candidate's DWC3/PHY/pull-up path. It is a physical-path positive control, not
a candidate-path observation.

## Reasoning Ledger

| Observation | Hypothesis tested | Check | Result | Disposition |
|---|---|---|---|---|
| stock enumerates ACM in a larger composite | Android-only gadget ceremony is mandatory | exact rc, live stock tree, QEMU minimal ACM | final UDC bind is the activation; minimal generic path executes | `STRONGLY_RULED_DOWN` |
| bare PID1 lacks `/vendor/firmware` | selected USB module waits for firmware | exact 60-module metadata and symbols | zero direct firmware dependency | `RULED_OUT` |
| stage `0x8d` passed | active role write completed | exact candidate branch and `mode_show()` | write may be skipped; readback is not completion | `UNPROVED` |
| stage `0x8e` passed | initial pull-up call failed synchronously | configfs, UDC core, DWC3 call chain | bind and synchronous connect returned success | `RULED_OUT` |
| stage `0x8f` timed out | host saw no attach | P2.76 host artifacts | sidecar absent | `OPEN` |
| zero ACM bytes | descriptor exchange never started | observer scope | observer begins at ACM endpoint, not electrical attach | `OPEN` |
| RUN_STOP workaround exists online | same silicon erratum caused P2.76 | patch scope plus exact source | old/specific/disputed; exact revision and LTSSM absent | `OPEN_LOW_PRIORITY` |
| `soft_connect` can retrigger pull-up | successful write would prove recovery | exact UDC sysfs source | underlying reconnect rc is discarded | `NON_PROOF`, later experiment only |
| Odin worked twice | physical path is healthy | transaction evidence | gross path works in bootloader windows | `POSITIVE_CONTROL_ONLY` |

## Consolidated Hypothesis Ledger

| ID | Hypothesis | Current status | Decisive next evidence |
|---|---|---|---|
| H1 | P2.76 skipped the explicit mode write because mode already read peripheral | `OPEN`, newly elevated | initial mode plus write-attempt marker |
| H2 | mode write ran but parent `sm_work` did not reach peripheral start | `OPEN` | `mode_request`, BSV, BIDLE, and `StrtGdgt` markers |
| H3 | parent reached peripheral start, but UDC remained not attached | `OPEN` | final UDC state, link state, and zero host connect events |
| H4 | host began reset/descriptors but enumeration failed | `OPEN` | host kernel/udev and optional usbmon |
| H5 | one reconnect recovers a first-start race | `OPEN_LOW_PRIORITY` | separate bounded retry only after H1-H4 classification |
| H6 | a selected module needs an absent external firmware file | `RULED_OUT` | none |
| H7 | Android performs a hidden mandatory enable write for minimal ACM | `STRONGLY_RULED_DOWN` | revisit only if a stock-only sysfs producer is newly found |
| H8 | full Max77705 automatic role chain is mandatory | `CONDITIONAL` | not required if an explicit mode write is proved to execute and settle |
| H9 | old USB2-only RUN_STOP erratum applies | `OPEN_LOW_PRIORITY` | exact IP revision plus matching LTSSM evidence |
| H10 | generic minimal ACM composition is invalid | `STRONGLY_RULED_DOWN` | revisit only after host descriptor/EP0 evidence |

## Next Bounded Discriminator

The next source-bound candidate should change one role variable and retain the
evidence needed to interpret it:

1. capture initial parent `mode`;
2. record whether the explicit peripheral write is attempted and its return;
3. after the write, require/read final parent `mode`;
4. preserve final UDC `state` and `current_speed` at the `0x8f` deadline;
5. optionally capture one bounded DWC3 `link_state` read;
6. optionally classify exact DWC3-MSM IPC markers, with unavailable distinct
   from absent;
7. require a durable host-side `armed` receipt before F1 execution; and
8. keep kernel/udev capture through candidate, rollback, recovery, and final
   health, with optional bounded usbmon.

The preferred single behavior is:

```text
record initial mode
then explicitly write peripheral once
then wait for/read final mode before UDC bind
```

Exact source makes the write a no-op if the parent is already settled in the
same role, while it re-queues the transition when `drd_state` is still
undefined. This recommendation still requires an ordinary source-bound safety
review and static validation before implementation. It is not device
authority.

Do not add a `soft_connect` retry to the same candidate. If the next evidence
shows `StrtGdgt`, `not attached`, and no host event, a later isolated
`disconnect -> bounded delay -> connect` experiment becomes justified.

## Result Interpretation

| Candidate evidence | Host evidence | Supported coordinate |
|---|---|---|
| no write attempt | any | candidate branch skipped the active bypass |
| write attempt, no `mode_request` | any | sysfs path/callback or optional IPC visibility issue |
| `mode_request` and BSV, no BIDLE/StrtGdgt | any | parent state-machine/workqueue boundary |
| `StrtGdgt`, UDC `not attached` | no host connect | PHY/pull-up/role sequencing after parent start |
| UDC `default` | reset/EP0 traffic | host reset reached device; inspect descriptors |
| UDC `addressed` | control traffic | descriptor/address exchange progressed |
| UDC `configured`, wrong speed | host endpoint exists | speed contract only |
| UDC `configured`, exact speed, exact banner | matching host receipt | E3 live proof, then mandatory rollback/health |

## Validation

This unit revalidated:

- exact P2.76 runtime branch and configured-state poll;
- exact FYG8 DWC3-MSM role getter/setter, state-machine queue, and peripheral
  start path;
- exact DWC3 initial pull-up/reset/RUN_STOP implementation;
- exact UDC `soft_connect` command vocabulary and discarded reconnect return;
- P2.60 source-contract token coverage and P2.70 QEMU role-boundary exclusion;
- exact P2.76 sidecar absence without publishing private logs;
- host usbmon kernel configuration, installed module, debugfs mount, and
  current unloaded state; and
- exact 60-module closure count and zero recorded firmware string hits.

Focused regression validation also passes:

```text
P2.60 source-contract tests: 15/15
P2.60 QEMU-boundary tests:     3/3
P2.74 sidecar tests:           5/5
```

No candidate defect was modified and no new live result was inferred.

## References

Repository evidence:

- `docs/reports/S22PLUS_FYG8_P276_E3_F1_LIVE_POST_BIND_TIMEOUT_2026-07-26.md`
- `docs/reports/S22PLUS_FYG8_P277_E3_POST_BIND_TIMEOUT_FOCUSED_ANALYSIS_H0_2026-07-26.md`
- `docs/reports/S22PLUS_STOCK_USB_GADGET_ACM_RECIPE_2026-07-09.md`
- `docs/reports/S22PLUS_NATIVE_INIT_M34_S6_POST_STOCK_USB_DIFF_2026-07-09.md`
- `docs/reports/NATIVE_INIT_V3424_S22PLUS_FYG8_USB_ROLE_DEEP_RE_2026-07-10.md`
- `docs/reports/NATIVE_INIT_V3425_S22PLUS_FYG8_FORCED_PERIPHERAL_BYPASS_HOST_AUDIT_2026-07-10.md`
- `docs/reports/S22PLUS_FYG8_P274_F1_HOST_USB_TRACE_SIDECAR_H0_2026-07-26.md`
- `workspace/public/src/native-init/s22plus_fyg8_p260_e3_runtime.inc.c`
- `workspace/public/src/scripts/revalidation/s22plus_fyg8_p260_source_contract.py`
- `workspace/public/src/scripts/revalidation/s22plus_fyg8_p260_qemu_harness.py`
- exact FYG8 `drivers/usb/dwc3/dwc3-msm-core.c`
- exact FYG8 `drivers/usb/dwc3/gadget.c`
- exact FYG8 `drivers/usb/gadget/udc/core.c`

Primary external references:

- <https://docs.kernel.org/usb/gadget_configfs.html>
- <https://docs.kernel.org/usb/usbmon.html>
- <https://docs.kernel.org/filesystems/debugfs.html>
- <https://lkml.iu.edu/1604.0/01979.html>

Verdict:

```text
PASS_P278_USB_POST_BIND_THREE_LANE_FOCUSED_ANALYSIS_H0
NEXT = role-write evidence + terminal bus state + armed host trace
```
