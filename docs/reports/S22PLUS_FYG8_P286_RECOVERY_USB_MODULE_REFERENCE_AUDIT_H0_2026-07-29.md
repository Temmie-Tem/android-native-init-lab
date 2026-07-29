# S22+ FYG8 P2.86 recovery USB-module reference audit H0

Date: 2026-07-29 KST

Scope: host-only comparison of the exact FYG8 recovery module list, dependency
metadata, matching vendor/common kernel sources, the frozen P2.86 60-module
plan, and P2.42-P2.58 design history. No device, payload, build input, intent,
candidate, package, or authority change occurred.

## Verdict

`NO_PROOF_P286_RECOVERY_MODULE_DELTA_CAUSES_USB_FAILURE_HOST_ONLY`

The recovery list is a useful independent vendor reference, but its textual
order and superset membership do not establish that P2.86 is missing a
load-bearing ACM or attach-event module.

The focused dispositions are:

| Claim | Disposition |
|---|---|
| `usb_f_ss_acm.ko` is required for P2.86 `acm.usb0` | `REJECTED` |
| recovery list order proves the notifier modules register after DWC3 | `REJECTED` |
| absence of `usb_notifier_qcom.ko` alone explains failure after a manual `mode=peripheral` request | `REJECTED_AS_SUFFICIENT_CAUSE`; broader causal contribution remains `NO_PROOF` |
| an unidentified side effect from the other recovery modules is necessary | `NO_PROOF` |
| P2.84 failed because the ACM function module was absent | `REJECTED`; P2.84 never reached E3/ACM |

No module-plan change is selected. P2.86 Full-LTO and its planned F1 closure
continue unchanged. P2.88 remains paper-only and is not started.

## Exact list comparison

The exact stock file is:

`workspace/private/inputs/s22plus_firmware/S906NKSS7FYG8_SKC/extracted-images/ramdisk-list/vendor/extract/lib/modules/modules.load.recovery`

It has:

- SHA256
  `616bdb71f2b68d76eca23f72883aea25d5202d4e14f5c99dd934720df863ac10`;
- 446 lines;
- 441 unique module names; and
- five duplicated names:
  `cpu_hotplug.ko`, `gh_virt_wdt.ko`, `qcom_tsens.ko`,
  `qcom_wdt_core.ko`, and `thermal_pause.ko`.

The relevant one-based text positions are:

```text
262 dwc3-msm.ko
273 usb_f_ss_acm.ko
279 usb_notify_layer.ko
280 usb_notifier_qcom.ko
379 usb_typec_manager.ko
```

The frozen P2.86 planner result is exactly 60 modules, all unique and all
members of the recovery set. Its relevant zero-based positions are:

```text
41 usb_notify_layer.ko
53 usb_typec_manager.ko
58 dwc3-msm.ko
```

`usb_notifier_qcom.ko` and `usb_f_ss_acm.ko` are absent. The base 59-module
closure is produced by `s22plus_o2_module_plan.py`; P2.57 adds only
`dispcc-waipio.ko`; and the P2.86 source contract requires that inherited
60-module result to remain exact.

This proves a real list difference. It does not prove an initialization-order
difference.

## Why the text order is not the registration order

The exact stock `modules.dep` records:

- `dwc3-msm.ko` hard dependencies on `usb_notify_layer.ko`,
  `usb_typec_manager.ko`, and their supporting notifier modules; and
- `usb_notifier_qcom.ko` hard dependencies on `dwc3-msm.ko`,
  `usb_notify_layer.ko`, `usb_typec_manager.ko`, and their supporting
  modules.

Dependency-aware module loading therefore does not execute the five textual
rows as independent `insmod` operations in list order. Module initialization
also does not serialize asynchronous platform-driver probe completion across
unrelated modules.

Consequently:

```text
modules.load.recovery line order
  != dependency load order
  != platform probe completion order
  != notifier registration order
```

The original positional comparison is a valid clue, not an ordering proof.

## Notifier path and delayed-state replay

The matching base source is
`SM-S906N_15_base_osrc/Kernel.tar.gz`. The FYG8 delta does not replace the
sources cited below.

The stock automatic UFP path is:

```text
PDIC / Max77705 state
  -> usb_typec_manager state aggregation and cached usb.dr
  -> usb_notifier_qcom manager listener
  -> usb_notify_layer OTG event dispatch
  -> dwc_msm_vbus_event()
```

Three mechanisms make a simple "listener registered too late, event lost"
model unsupported:

1. `usb_typec_manager_notifier.c:1201-1238,1309-1333` registers a new USB
   listener and immediately invokes it with cached `typec_manager.usb.dr`
   state when that state is already known.
2. `usb_notifier_qcom.c:501-542` records whether DWC3-MSM probe is complete
   and registers the manager listener. UFP is translated to
   `NOTIFY_EVENT_VBUS` at lines 106-158; the final peripheral callback calls
   `dwc_msm_vbus_event()` at lines 389-393.
3. `usb_notify.c:2456-2471` retains an early delayed event in
   `reserve_state`. `enable_usb_notify()` at lines 3784-3810 releases that
   delayed path after DWC3 becomes ready.

Thus both relative directions have a replay path:

```text
manager state first, qcom listener later -> manager cached-state replay
qcom/notify event first, DWC3 later       -> notify reserve-state replay
```

The absence of `usb_notifier_qcom.ko` still means the exact P2.86 closure lacks
the stock automatic Samsung-to-QCOM Type-C bridge. That fact was already
known. It is not sufficient to explain failure after the candidate's explicit
role request.

## The manual role request bypass

The P2.86 userspace inherits the exact write of `peripheral` to the DWC3-MSM
`mode` sysfs attribute.

In matching `dwc3-msm-core.c`:

- `mode_store()` at lines 4834-4865 maps `peripheral` to
  `USB_ROLE_DEVICE`;
- `dwc3_msm_set_role()` at lines 4721-4779 sets
  `mdwc->vbus_active = true`;
- it sets `mdwc->id_state = DWC3_ID_FLOAT`; and
- it invokes `dwc3_ext_event_notify()` to queue the same role state machine.

P2.79A independently filtered all exact-candidate producers of
`vbus_active=true` and identified this manual role path as available while
the Samsung notifier caller was absent.

The refined boundary is therefore:

- `usb_notifier_qcom.ko` is needed for the stock automatic Type-C role path;
- it is not needed merely to make `vbus_active=true` and dispatch a device
  role through the candidate's explicit sysfs path; and
- orientation, PDIC/Max77705 state, redriver setup, or another stock side
  effect could still matter, but this audit does not prove one.

## Why `usb_f_ss_acm.ko` is not the E3 function

The exact P2.84 Full-LTO `.config`, inherited by the unchanged P2.86 kernel
base, contains:

```text
CONFIG_USB_F_ACM=y
CONFIG_USB_U_SERIAL=y
CONFIG_USB_CONFIGFS_ACM=y
```

The common kernel source establishes:

- `drivers/usb/gadget/Kconfig:256-264`:
  `USB_CONFIGFS_ACM` selects `USB_U_SERIAL` and `USB_F_ACM`; and
- `drivers/usb/gadget/function/f_acm.c:842-860`:
  `DECLARE_USB_FUNCTION_INIT(acm, ...)` registers the configfs function name
  `acm`.

The separate vendor implementation establishes:

- `drivers/usb/gadget/function/f_ss_acm.c:766-882`:
  the distinct function name is `ss_acm`; and
- its Makefile lines 75-76 build only that function as
  `usb_f_ss_acm.ko`.

The P2.86 runtime creates:

`/config/usb_gadget/g1/functions/acm.usb0`

It does not create `ss_acm.0`. The required generic ACM function is already
built into the kernel, so adding `usb_f_ss_acm.ko` would answer a different
configfs function contract. The same distinction was recorded in the P2.59
ACM analysis.

## Recovery-ramdisk USB choreography

The previously unexamined host artifact was:

`workspace/private/inputs/s22plus_firmware/S906NKSS7FYG8_SKC/extracted-images/raw/recovery.img`

It is a 104,857,600-byte Android recovery image with SHA256
`93fac06ca79bf4b365b25a8d49902bc41aba112ea253c30880c90e314d7895d4`.
Independent `magiskboot` unpacking produced ramdisk SHA256
`5707b8613a29f6b114cbd241c38146c4eb2c9183c46446d042c55892b9cb973f`.
The relevant extracted files and hashes are:

| File | SHA256 |
|---|---|
| `init.recovery.qcom.rc` | `68adefa661f26396003c530bb1269d461a9807d8752dce66fd270e00de0f78d4` |
| `init.recovery.samsung.rc` | `c27011d5f129f35cd6786aa5dfbed10bb3915bb716275e44a4b782a013de3f73` |
| `system/etc/init/hw/init.rc` | `2aa7ab7d635fb03cbdf79ea12f75bfeb52cabdbb30cf6bba354cc3015bbd872a` |

The ramdisk's `init` is a symlink to `/system/bin/init`; the executable
orchestration is in the recovery rc files.

### Exact recovery sequence

`init.recovery.qcom.rc:28-37` performs:

```text
setprop sys.usb.controller a600000.dwc3
setprop sys.usb.configfs 1
wait  /sys/bus/platform/devices/${ro.boot.usb.dwc3_msm:-a600000.ssusb}/mode
write /sys/bus/platform/devices/${ro.boot.usb.dwc3_msm:-a600000.ssusb}/mode peripheral
wait  /sys/class/udc/${ro.boot.usbcontroller} 1
```

`system/etc/init/hw/init.rc:95-106` then mounts configfs and creates:

```text
/config/usb_gadget/g1
idVendor = 0x18D1
strings/0x409/{serialnumber,manufacturer,product}
functions/ffs.adb
functions/ffs.fastboot
configs/b.1
configs/b.1/strings/0x409
```

For the ADB branch, lines 168-173 wait for
`sys.usb.ffs.ready=1`, then perform:

```text
idProduct = 0xD001
configs/b.1/strings/0x409/configuration = "adb"
symlink functions/ffs.adb -> configs/b.1/f1
write UDC a600000.dwc3
```

The one-second `wait` in the QCOM rc waits only for the UDC class node. The
later FunctionFS readiness property gates the ADB-function bind.

### Candidate comparison

P2.86 uses the same controller and role-control topology:

```text
/sys/devices/platform/soc/a600000.ssusb/mode = peripheral
/config/usb_gadget/g1
strings/0x409
configs/b.1
configs/b.1/strings/0x409
UDC = a600000.dwc3
```

Its configfs construction is an operation-shape superset, not a byte-for-byte
value superset. It additionally writes and verifies:

```text
bcdUSB
bcdDevice
max_speed = high-speed
configs/b.1/bmAttributes
configs/b.1/MaxPower
```

The identifier and string values are candidate-specific rather than recovery
values. The function difference is deliberate:

```text
recovery  functions/ffs.adb  -> requires sys.usb.ffs.ready
P2.86     functions/acm.usb0 -> built-in f_acm; no FunctionFS daemon gate
```

`max_speed=high-speed` is consistent with the E3 HS-only objective and the
P2.83 HS stock control. No setup operation required by the simpler generic ACM
graph is absent from the candidate.

The exact Linux host observer is also consistent with those candidate-specific
values. `device_action_cdc_acm_observer_v1.py:437-441` requires exact vendor,
product, driver, and interface values. The selected P2.60 contract defines:

```text
USB_VENDOR_ID        = 04e8
USB_PRODUCT_ID       = 6861
USB_DRIVER           = cdc_acm
USB_INTERFACE_NUMBER = 00
USB_SERIAL_PREFIX    = S22E3
BANNER_PREFIX        = S22PLUS-FYG8-E3:
```

`candidate_observer()` derives the observer dictionary from those same
contract constants that generate the candidate runtime values. The
candidate-observer VID/PID/serial/banner mismatch class is therefore closed by
construction, not by a manually duplicated manifest value. Generic `f_acm`
uses communication interface 0 and data interface 1; Linux `cdc_acm` binds the
communication interface, matching observer interface `00`.

One known portability deviation remains. P2.86 writes `bcdUSB` and
`bcdDevice`, but does not write `bDeviceClass`, `bDeviceSubClass`, or
`bDeviceProtocol`; their configfs defaults remain zero. A common IAD-style ACM
device-level triple is `0xEF/0x02/0x01`. This is not a defect for the selected
Linux host because `cdc_acm` binds the ACM interface descriptor
`0x02/0x02/0x01`, not the device-level class. Record the zero device-class
default as a known difference if a future validation target is a non-Linux
host.

P2.58A already live-proved the inherited module/runtime prefix through exact
membership of real UDC `a600000.dwc3`. Recovery and candidate therefore use
the same controller discovery and `mode=peripheral` boundary through UDC
availability. P2.76 separately proved exact configfs UDC bind and synchronous
pull-up request for the later E3 construction.

This closes the host-side hypothesis that the candidate fails because it
omitted a recovery configfs step or used the wrong controller/mode path. It
does not prove that recovery and bare PID1 enter that sequence with identical
kernel runtime-PM, PHY, Type-C, or electrical state.

The remaining difference relevant to the current `0x90/0x91` question is
therefore below the userspace choreography: the kernel/hardware state in which
the same role request executes. That supports, without independently proving,
the P2.80-P2.86 runtime-PM and PHY strategy.

## Remaining host-material inventory

The locally available host evidence for this question is now exhausted:

| Material | Disposition |
|---|---|
| ordinary boot ramdisk | generic first-stage init; no USB choreography |
| FYG8 DTBO set | USB controller and repeater nodes already audited |
| recovery ramdisk | exact controller, configfs, FunctionFS, and UDC sequence audited above |
| recovery kernel | same source family/GKI inputs already available for source comparison |
| system/vendor partitions | not present in the extracted set; ordinary Android USB policy is more complex and less direct than recovery for this question |

This is not a claim that no future host hypothesis can exist. It means the
known unexamined firmware artifact that could directly answer the
userspace-sequence question has been consumed, and it produced a clean
negative for choreography mismatch.

## P2.42-P2.58 history

The 60-module closure is deliberate:

- `usb_notify_layer.ko` and `usb_typec_manager.ko` were not removed; they are
  present in the plan.
- P2.51 explicitly deferred another USB module and the Samsung Type-C policy
  chain until a narrower SSUSB dependency discriminator was exhausted.
- P2.57 changed the 59-module plan by exactly one insertion,
  `dispcc-waipio.ko`.
- P2.58A retained that 60-module plan byte-for-byte and changed only its UDC
  predicate/runtime boundary.
- The earlier O3 design deliberately selected generic `acm.usb0`, not Samsung
  `ss_acm`.

The historical exclusion was therefore intentional at plan level. The
file-specific proof that `usb_notifier_qcom.ko` was not required merely to
produce a manual device role was completed later in P2.79A, not in the
P2.42-P2.58 module-selection record itself.

## Relation to P2.84 and P2.86

P2.84 retained `0x8f/detail=0xc18` and then stopped before the bounded DEVICE
restart completed. It did not reach child reinitialization, configfs gadget
construction, UDC binding, host ACM enumeration, or ACM bytes.

That live result therefore cannot support either:

```text
the recovery-only modules were required
the recovery-only modules were irrelevant
```

P2.86 addresses the earlier restart boundary. Changing its module plan now
would combine two hypotheses and invalidate the frozen source identity without
evidence that the second change is needed.

## Decision

Keep P2.86 unchanged through its already-selected Full-LTO, static closure,
ready-manifest, D0, and separately approved F1 sequence.

Do not copy the 446-module recovery list and do not add
`usb_f_ss_acm.ko` or `usb_notifier_qcom.ko` on this evidence.

If a later run reaches the manual role, reinitialization, and configfs
boundaries but still fails at connection, the next H0 unit should isolate one
exact missing stock side effect or physical-connect boundary. It should not
infer necessity from recovery superset membership alone.
