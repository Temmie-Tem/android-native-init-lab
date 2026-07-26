# S22+ FYG8 P2.77 E3 post-bind timeout focused analysis

Date: 2026-07-26 KST
Tier: H0
Status: `FOCUSED_ANALYSIS_COMPLETE`
Device contact: none

## Question

P2.76 reached UDC-bind stage `0x8e`, then timed out at configured-state stage
`0x8f` with no host ACM endpoint. This unit tests three explanations before
designing another candidate:

1. the bare PID1 rootfs lacks firmware files required by a selected driver;
2. the retained buffer already contains candidate DWC3 or firmware errors; or
3. the candidate crosses a real asynchronous DWC3-MSM boundary without
   measuring its completion or the USB bus state.

The conclusion is:

```text
missing selected-driver firmware: RULED OUT
candidate kernel printk in retained read: UNAVAILABLE
post-bind DWC3-MSM / bus-state boundary: OPEN, highest priority
```

The analysis identifies a strong code-supported race window. It does not claim
that timing is the proven permanent root cause.

## Evidence Reconstruction

The exact live evidence is:

```text
stage 0x8e progress
stage 0x8f failure, detail 110 (ETIMEDOUT)
host endpoint observer timeout, zero bytes
candidate boot observed, no boot loop
exact rollback and final health passed
```

The P2.60 runtime performs these operations in order:

1. mount and validate configfs;
2. create the ACM gadget;
3. wait for and open `ttyGS0`;
4. queue the exact banner before binding;
5. write/read parent `ssusb/mode=peripheral` and verify the exact UDC member;
6. bind `g1` to `a600000.dwc3`; and
7. poll UDC `state` and `current_speed`.

The retained record therefore places the failure after all gadget-local work
and after successful configfs UDC binding.

## Retained Buffer Segmentation

The two retained reads are byte-identical combined Samsung circular buffers,
not a candidate-only kernel log.

Offset reconstruction separates:

- stale Android kernel messages from before the candidate transaction;
- XBL/ABL and Odin transfer messages;
- the candidate bootloader sequence;
- the P2.60 checkpoint record; and
- the later reset/rollback sequence.

Immediately before the candidate checkpoint, ABL reports:

```text
Failed to get KlogOffset, Not Found
SamsungLogFlush KlogOffset:0x0
```

There is no candidate kernel printk segment between the candidate bootloader
messages and the checkpoint record. Consequently, `dwc3`, `phy`, `typec`,
`max77705`, and `firmware` strings elsewhere in the retained read are stale
Android or bootloader data. They cannot be attributed to the candidate.

The candidate bootloader segment does independently show cable power before
the kernel:

```text
chg_get_charger_status ... vbus_status(1)
MuicGetVbusStatus: 1
Booting Into Mission Mode
```

This proves pre-kernel cable VBUS observation. It does not prove that the
candidate kernel asserted a data-line pull-up or that the host processed USB
traffic.

## Firmware Hypothesis

Missing `/vendor/firmware` is a real general bare-PID1 hazard. A module that
calls `request_firmware()` can bind or initialize differently when the vendor
filesystem is absent.

It is not a producer in the exact P2.76 closure:

- the exact candidate reuses 60 selected FYG8 vendor-ramdisk modules;
- all 60 binaries were extracted from that exact vendor ramdisk;
- `modinfo -F firmware` is empty for every selected binary;
- undefined-symbol inspection finds zero
  `request_firmware*`, `firmware_request*`, or `firmware_upload*` references;
- neither `mfd_max77705.ko` nor `pdic_max77705.ko` is selected; and
- the selected USB path includes the QMP, HS, eUSB2, repeater, redriver,
  notifier, Type-C-manager, DWC3-MSM, and UCSI components without an external
  firmware API reference.

The Max77705 family does have a firmware-update path in the wider stock
system. That fact cannot explain a missing firmware request from a module that
this candidate never loads. Whether unmodeled Max77705/PDIC side effects are
still useful is a separate architecture hypothesis, not a firmware-file
failure.

The old M34 S7A/S7A2 negative results do not settle that separate question.
Later M34 analysis proved that the old loader did not establish per-module
load success. P2.76, by contrast, has typed insertion and bind checkpoints.
Historical "no USB" outcomes cannot be promoted into present module-state
evidence.

## Exact FYG8 Source Path

### Parent role write is asynchronous

The exact FYG8 `dwc3-msm-core.c` path is:

```text
mode_store()
  -> dwc3_msm_set_role(USB_ROLE_DEVICE)
     -> vbus_active=true
     -> id_state=DWC3_ID_FLOAT
     -> dwc3_ext_event_notify()
        -> B_SESS_VLD set
        -> queue_delayed_work(sm_work, 0)
```

`mode_store()` returns after queuing `sm_work`. It does not wait for that new
work item to finish. `mode_show()` reports `peripheral` from
`vbus_active`/`id_state`; it is not a readback of `drd_state` or
`in_device_mode`.

The current runtime accepts:

```text
mode == peripheral
exact a600000.dwc3 class member exists
```

as the end of stage `0x8d`. Both can be true before the parent state machine
finishes its device transition.

### UDC publication can precede parent completion

The child DWC3 role-switch setup defaults to peripheral unless the DT requests
host default. It can therefore register `a600000.dwc3` before the parent
DWC3-MSM state machine consumes the newly queued B-session-valid event.

This explains why exact UDC membership is not a completion fence for:

```text
dwc3_otg_start_peripheral()
  -> PM/runtime resume
  -> VBUS override
  -> redriver and PHY connect notifications
  -> DWC3 child role switch
  -> in_device_mode=true
```

### Stage 0x8e includes a successful pull-up request

The generic UDC core initializes `udc->vbus = true`. Binding the configfs
composite driver executes:

```text
driver->bind()
usb_gadget_udc_start()
usb_udc_connect_control()
  -> usb_gadget_connect()
     -> dwc3_gadget_pullup(..., true)
```

The exact DWC3 pull-up function sets `softconnect`, resumes runtime PM, performs
the required core soft reset, installs event buffers, starts the gadget, and
sets run/stop. A returned error propagates through the configfs UDC write.

Because stage `0x8e` passed, these calls returned success. This rules out:

- UDC absence;
- an unbound configfs gadget;
- `udc->vbus` being false at bind time; and
- a synchronous DWC3 pull-up error returned to configfs.

It does not prove that the host saw the electrical connect, reset the bus, read
descriptors, assigned an address, or selected a configuration. Those are
later asynchronous events.

## Hypothesis Ledger

| Hypothesis | Status | Evidence |
| --- | --- | --- |
| selected module waits for a missing firmware file | `RULED_OUT` | exact 60-binary metadata and undefined-symbol scan |
| candidate DWC3 printk is already recoverable | `RULED_OUT` for this run | no candidate klog segment; ABL reports missing KlogOffset |
| cable VBUS was absent before candidate kernel | `RULED_OUT` | candidate bootloader repeatedly reports VBUS present |
| exact UDC did not exist | `RULED_OUT` | stage `0x8d` exact membership |
| configfs bind or synchronous pull-up returned an error | `RULED_OUT` | stage `0x8e` progress after exact write/readback |
| UDC core suppressed connect because `udc->vbus=false` | `RULED_OUT` | exact UDC core initializes it true and bind succeeded |
| parent DWC3-MSM transition had not settled when bind ran | `OPEN`, strongly prioritized | role write queues work; current readback is not a completion fence |
| host saw connect/reset/descriptor errors | `OPEN` | P2.74 sidecar was not running |
| host saw no electrical connect at all | `OPEN` | same missing host trace |
| PHY/redriver/runtime-PM failed asynchronously after bind | `OPEN` | no candidate klog or post-bind state detail |
| Max77705/PDIC side effects are still required despite forced role | `OPEN`, lower priority | no direct evidence; not a firmware-request result |

## Existing Diagnostic Surface

The exact kernel already exposes two useful read-only surfaces.

First, `/sys/class/udc/a600000.dwc3/state` reports the canonical USB device
state, and `current_speed` reports the negotiated speed. The current runtime
polls both but discards their last values when it emits generic
`ETIMEDOUT`.

Second, DWC3-MSM creates a Qualcomm IPC log context named from
`a600000.ssusb`, with dots converted to underscores. With debug enabled this
appears under:

```text
/sys/kernel/debug/ipc_logging/a600000_ssusb/log
```

At low Samsung debug level, contexts may share:

```text
/sys/kernel/debug/ipc_logging/dummy_log/log
```

The exact driver emits load-bearing markers including:

```text
mode_request
XCVR: BSV set
BIDLE gsync
StrtGdgt gsync
```

`CONFIG_DEBUG_FS=y` is present in the exact candidate kernel, and
`qcom_ipc_logging.ko` precedes DWC3-MSM in the proven module sequence. The
availability and retention of either exact log file in bare PID1 remain
unproved; they must be treated as optional evidence, not a success gate.

## Next Bounded Design

Do not add modules or another USB composition yet. The next candidate should
increase information at the same post-bind boundary:

1. On the `0x8f` deadline, encode the last exact UDC `state` as a structured
   detail rather than collapsing every non-configured state to 110.
2. Encode the last `current_speed` independently, including `unknown`.
3. Re-read parent `ssusb/mode` at the same terminal snapshot.
4. Optionally mount debugfs and classify a bounded set of exact DWC3 IPC
   markers. Absence or overflow must remain diagnostic, not fatal.
5. Actually start the P2.74 host USB sidecar before execution and keep it
   through rollback and final health.

The UDC-state classifier gives immediate branches:

| Final UDC state | Meaning |
| --- | --- |
| `not attached` | no host-visible attach/reset reached the UDC |
| `attached` or `powered` | electrical session began but reset/address did not complete |
| `default` | host reset reached the device |
| `addressed` | descriptor/address exchange progressed |
| `configured` with wrong speed | enumeration completed; speed contract is the only failure |

The state names must be parsed from the kernel's canonical
`usb_state_string()` vocabulary, not inferred from ordinal values.

No blind delay, `soft_connect`, Max77705 expansion, firmware copy, descriptor
expansion, or broad kernel instrumentation is justified before this
discriminator. The current evidence has reached a real asynchronous hardware
boundary; the next unit should identify which side of that boundary stopped.

## Proof Limit

Static source proves the control-flow possibilities and eliminates several
direct failure producers. It cannot reconstruct workqueue timing, PHY state,
or host bus events from a run that did not retain candidate klog and did not
start the host sidecar.

The strongest honest conclusion is therefore:

```text
P2.76 successfully requested and bound the real DWC3 gadget.
The exact USB bus progress after that request is unobserved.
Missing firmware files are not the cause in the selected module closure.
```
