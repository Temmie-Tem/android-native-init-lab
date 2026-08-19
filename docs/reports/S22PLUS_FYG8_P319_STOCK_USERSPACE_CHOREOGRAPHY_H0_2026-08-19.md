# S22+ FYG8 P3.19 — the stock USB choreography, read from the firmware

Status: `IMPLEMENTED_REVIEW_PENDING`

**NO DEVICE OR LIVE AUTHORITY.** This unit is host-only. It reads files that
were already on this host and creates no D0, D1, F1, recovery, replay, device,
or live authority. No device, ADB, USB, Odin, transfer, recovery, replay, live
authority, A90 or S20+ action occurred.

## Why this unit exists

The independent review ranked this first and stated the reason plainly: a prior
report's claim that `system` and `vendor` were unavailable had gone stale,
because `super.img` was extracted to the SD card in the Gate 0 unit and has been
sitting there unread. The question it was meant to answer is what Android's
userspace does for USB that a native-init PID 1 omits.

That question is now answered from the firmware rather than from inference.

## What was read

`super.img` is Android-sparse and 10352130812 bytes. Five logical partitions
were extracted with the campaign's own sparse-aware LP reader — the same reader
`fsck.f2fs` already validated in the Gate 0 unit — and mounted read-only:

| Partition | Bytes | SHA-256 |
|---|---|---|
| vendor | 2175606784 | `a885cb219d3d21aea87aacb514650857d46f9e2d3b2bfa2fb7a7f1754c5dacf2` |
| odm | 21389312 | `937e692aff25c4a88d27b2b93e4b23abe39ebe034a95c6b18416b2667c263e76` |
| system_ext | 183328768 | `d6aa196410579173d0ea42fe7070fdc1bb2ed9da83d3086c87de0adff4cf29b9` |
| system | 6669402112 | not digested |
| product | 1314770944 | not digested |

All five are F2FS with `compress_algorithm=lz4`, mounted `ro` so the host kernel
decompresses transparently; no image was modified. `vendor` carries 4118 paths
and 160 init rc files, `system_ext` 1077 paths, and `odm` 13 paths which are
nothing but sepolicy — odm contributes nothing to this question.

## The stock chain, resolved to this unit's actual values

Three properties decide which of several possible paths this device takes, and
all three are pinned rather than assumed:

- `vendor.usb.use_gadget_hal=0` (`vendor/build.prop:326`), so the gadget is
  built by init rc and **not** by `usbd`.
- `vendor.usb.controller=a600000.dwc3` (`vendor/etc/init/hw/init.target.rc:130`).
- `androidboot.usbcontroller=a600000.dwc3` in the vendor_boot bootconfig.

`system/etc/init/hw/init.usb.rc` is entirely gated on `sys.usb.configfs=0`, the
legacy `android_usb` interface, and is therefore inert here. AOSP's
`init.usb.configfs.rc` has been stripped on this build to a single action,
`on property:init.svc.adbd=stopped` setting `sys.usb.ffs.ready 0`. The whole
configfs choreography is Samsung's `vendor/etc/init/hw/init.qcom.usb.rc`, 2684
lines and 165 action blocks, of which 153 are per-composition permutations.

The chain that actually runs:

1. `init.target.rc:130` sets `vendor.usb.controller a600000.dwc3`.
2. `init.qcom.usb.rc:188`, on that property with `use_gadget_hal=0`, sets
   `sys.usb.controller` and `sys.usb.configfs 1`.
3. `on post-fs` mounts configfs, builds the `g1` and `g2` gadget trees, creates
   every function directory, mounts functionfs for adb, diag, mtp and ptp, sets
   `bcdUSB 0x0200`, `bcdDevice 0x504`, `os_desc/use 1`, `os_desc/b_vendor_code
   0x1`, `os_desc/qw_sign "MSFT100"`, `MaxPower 900`, and execs
   `/vendor/bin/init.qcom.usb.sh`.
4. `init.qcom.usb.sh` sets `vendor.usb.configfs 1` and the product string. Its
   only write to `a600000.ssusb/mode` is inside a `soc_machine == "SA"`
   (Automotive) branch and does **not** run on this device.
5. `sys.usb.config` is set, `adbd` starts, opens the functionfs endpoints, and
   the kernel side of that raises `sys.usb.ffs.ready 1`.
6. `on property:sys.usb.ffs.ready=1 && sys.usb.config=adb &&
   property:sys.usb.configfs=1` links the functions, writes `idVendor 0x04E8`
   and `idProduct 0x6860`, and only then writes
   `/config/usb_gadget/g1/UDC ${sys.usb.controller}`.

Step 6 is the pull-up, and its ordering is the load-bearing part: **the UDC bind
is gated on a userspace daemon having already opened the function's endpoints.**
For `ffs.adb` that daemon is adbd. A CDC-ACM function has no userspace side, so
a candidate is not blocked by this gate — but any candidate that ever tries to
reproduce the stock adb composition is.

## Stock gadget versus the candidate's

The P2.60/E3 runtime, which is what P3.17 carries, builds `acm.usb0` directly.
Compared against the stock `adb` composition:

| Attribute | Stock | Candidate |
|---|---|---|
| `idVendor` | `0x04E8` | `0x04e8` |
| `idProduct` | `0x6860` | `0x6861` |
| `bcdUSB` | `0x0200` | `0x0200` |
| `bcdDevice` | `0x504` | `0x0003` |
| `max_speed` | not written | `high-speed` |
| `os_desc` use / vendor code / sign | written | not written |
| config functions | `f1=ffs.adb`, `f2=ss_mon.etc` | `acm.usb0` only |

The one difference worth a second look is `ss_mon.etc`. It is a Samsung
`usb_f_ss_mon_gadget` function and it appears as `f2` in **every** stock
composition without exception. Whether it is required for the pull-up is not
established here; it is recorded because a function present in every stock
configuration and absent from every candidate configuration is the shape of
thing this campaign has been looking for.

## Four candidate causes this unit refutes

Each of these looked like a live explanation while being read, and each is
refuted against the shipped binaries rather than against the source alone.

**1. Missing module parameters do not reroute the mux.** Stock boot loads
`common_muic.ko` with `muic_param_pdic_info=1 muic_param_pmic_info=3
muic_param_afc_mode=0x30`, visible in both retained 2026-07-10 captures. There
is no `modules.options` anywhere in `vendor_dlkm`, `vendor`, or the vendor_boot
ramdisk; the source is the kernel command line, which carries
`common_muic.muic_param_pmic_info=3` and its siblings, and Android's libmodprobe
converts `<module>.<param>` cmdline entries into module arguments. `insmod` does
not do this, and the kernel applies `modname.param=` only to built-in code, so a
candidate that inserts modules directly supplies none of them.

That looked decisive, because `get_switch_sel()` returns
`pmic_info & 0xfff` and bit 0 selects `MUIC_PATH_USB_AP` against
`MUIC_PATH_USB_CP`, and routing D+/D- to the modem is exactly the shape of "the
kernel looks healthy and nothing is on the wire". It is wrong. `muic_param.c`
falls back to `pmic_info`, which is `extern` only under
`(IS_MODULE(CONFIG_SEC_PARAM) || CONFIG_SEC_MPARAM) && !CONFIG_MUIC_USE_MODULE_PARAM`
and otherwise `static int pmic_info = -1`. The shipped
`vendor_dlkm/lib/modules/common_muic.ko` has no `pmic_info`, `charging_mode`, or
`ccic_info` symbol of any kind, undefined or otherwise, so the static branch is
what was compiled. With no argument the fallback is `-1 & 0xfff = 0xfff`, bit 0
is set, and the path is `MUIC_PATH_USB_AP` — the same result as the stock value
of 3. The same reasoning disposes of `pdic_param_lpcharge`: `pdic_param.c` has
the identical guard, `pdic_notifier_module.ko` carries no bare `lpcharge` or
`factory_mode` symbol, so the fallback is `static unsigned int lpcharge` at 0,
which is what the stock command line sets it to anyway.

**2. There is no GPIO mux.** `muic-core.c` calls `pdata->set_gpio_usb_sel(...)`
in two places, which would be a second physical switching element outside the
MAX77705. `set_gpio_usb_sel` is never assigned anywhere in the tree, so the
pointer is always NULL and both calls are skipped.

**3. `usb_notify`'s data gate defaults open.** `usb_notify_sysfs.c:1260` sets
`udev->usb_data_enabled = 1` when the device is created, so
`/sys/class/usb_notify/usb_control/usb_data_enabled` does not need userspace to
turn it on.

**4. `usb_notify`'s peripheral block fails open.** `mode_store` refuses
`peripheral` when `is_blocked(get_otg_notify(), NOTIFY_BLOCK_TYPE_CLIENT)` is
true, which would be a silent, userspace-shaped veto on the role request.
`is_blocked` returns false on a NULL `otg_notify` and again on a NULL
`u_notify`, so a candidate that has not brought up the notifier is not blocked
by it.

## A stale path in the stock HAL, and the real role knob

`vendor/etc/init/android.hardware.usb@1.3-service.coral.rc` chowns and chmods
three nodes under `/sys/devices/platform/soc/a600000.ssusb/`: `b_sess`, `id`,
and `usb_data_enabled`. **None of the three exists in this kernel.** `b_sess`
does not appear anywhere under `drivers/`, and `usb_data_enabled` appears only
in `drivers/usb/notify/`. The HAL is named for `coral`, a Pixel, and these are
carried-over paths; the `chown`/`chmod` lines are no-ops on this device. Any
plan that reaches for them — including a reading of the review's ranked item
that treats them as available — is chasing nodes that are not there.

The nodes that do exist come from `ATTRIBUTE_GROUPS(dwc3_msm)` wired through
`.dev_groups = dwc3_msm_groups` on the platform driver, and they are exactly
four: `orientation`, `mode`, `speed`, `bus_vote`. The review's `a600000.ssusb/mode`
is real; the other two paths it inherited from the HAL rc are not.

`mode` is `DEVICE_ATTR_RW`. `mode_store` maps `peripheral` to `USB_ROLE_DEVICE`
and calls `dwc3_msm_set_role`, which is a driver-mediated role request that
touches the MAX77705 not at all. `mode_show` calls `dwc3_msm_get_role` and
returns `peripheral`, `host`, or `none`.

## The second MUIC interface

`init.qcom.rc:247-262` chowns a Samsung MUIC surface this campaign has not used:
`/dev/ccic_misc` and `/sys/class/sec/switch/{otg_test,uart_sel,usb_sel,
afc_disable,apo_factory,afc_set_voltage,vbus_value,vbus_value_pd,vbus_rawdata,
show_reg,hiccup}`.

`usb_sel` is mode 0664 and writable, which is worth stating precisely so it is
not mistaken for a switch: `max77705_muic_set_usb_sel` sets `pdata->usb_path`
and returns. **It issues no I²C.** It changes which path a subsequent attach
will select; it does not move the mux. Reading it is a pure read of driver
state, with none of the VDM_INT-clearing hazard that `mxim/debug0/reg` carries.

## What this changes about the frontier

The review demoted the mux hypothesis and named the stronger frontier as
`role request → UDC bind → DWC3 pull-up/connect → physical host attach`. This
unit supplies the first cheap measurement on that frontier, and it is a read:

    cat /sys/bus/platform/devices/a600000.ssusb/mode

`mode_show` has no side effect, issues no I²C, and consumes no latched
interrupt. It returns the role the driver has been told to take, not the
controller's negotiated state: `dwc3_msm_get_role` reads `mdwc->vbus_active` and
`mdwc->id_state`, which are the same two fields `dwc3_msm_set_role` assigns.
This sentence first said it returns the controller's actual current role, which
was wrong. On a candidate it separates
"the role never became peripheral" from "the role is peripheral and nothing
reaches the host", which are the two halves the frontier is currently one
undivided question about. It is a strictly weaker action than the Stage B
register read that has already been run.

## What remains open

- Whether `ss_mon.etc` participates in the pull-up, or is only telemetry.
- ~~The ramdisk versus `vendor_dlkm` `pdic_max77705.ko` identity.~~ Closed
  below.
- ~~The 69-entry P3.17 plan against the 140-entry first-stage list.~~ Closed
  below.
- The static CONTROL1 writer graph, of which `max77705-muic.c:1825` is now
  located: water handling can issue `com_to_open` and, under
  `CONFIG_HICCUP_CHARGER`, `com_to_usb_cp`, both gated behind
  `!is_lpcharge_pdic_param() && !muic_data->is_factory_start`.
- Bootloader behaviour remains undecidable from the extracted AP set.

## Evidence

Staged surfaces are under `workspace/private/p319_stock_userspace/`, which is
gitignored and holds firmware-derived material that must not be committed.
Mount points are read-only loop mounts under `/mnt/android-lab-logical/`.

## The measurement was taken, and two claims above need correcting

The runner was built and collected once against the running stock unit. Every
declared attribute was present, every read returned zero, and the classification
is `configured`:

| Attribute | Value |
|---|---|
| `a600000.ssusb/mode` | `peripheral` |
| `udc/state` | `configured` |
| `udc/function` | `g1` |
| `udc/current_speed` | `super-speed` |
| `udc/maximum_speed` | `super-speed` |
| `udc/is_a_peripheral` | `0` |
| `udc/is_selfpowered` | `0` |
| `configfs g1/UDC` | `a600000.dwc3` |
| `/sys/class/udc` entries | `a600000.dwc3`, `dummy_udc.0` |

**First correction: this is not a new control.** The section above presented the
read as the first cheap measurement on the frontier. The campaign already had
five of these nine values: `S22PLUS_FYG8_P278_..._2026-07-26` records the exact
stock recipe as `vendor.usb.use_gadget_hal=0`, `UDC=a600000.dwc3`, `parent
mode=peripheral`, `UDC state=configured`, `UDC speed=super-speed`. What this
unit adds is that the tuple is unchanged three and a half weeks and several
boots later, that it now comes from a contract-bound raw-first runner rather
than an ad-hoc capture, and four values the older recipe did not carry:
`function`, `maximum_speed`, `is_a_peripheral` and `is_selfpowered`.

**Second correction: the runner is not a new instrument for the candidate.**
The section above said the read separates "the role never became peripheral"
from "the role is peripheral and nothing reaches the host". The P2.60/E3
runtime already does both halves itself: `p260_wait_role_and_udc` writes
`peripheral` to `/sys/devices/platform/soc/a600000.ssusb/mode` and then polls
until it reads back, and `p260_wait_configured` polls
`/sys/class/udc/a600000.dwc3/state` and `current_speed`. So a candidate that
reaches the UDC bind has already proven `mode` was `peripheral`. The runner's
real contribution is narrower and should be stated as such: a reproducible stock
control tuple, and a post-hoc reader usable on any boot rather than only at the
candidate's own stages.

`dummy_udc.0` is worth one line. It is not shipped as a module — there is no
`dummy_hcd.ko` in `vendor_dlkm`, in `vendor`, or in the vendor_boot ramdisk — so
it is built into the kernel and is present even on a candidate that loads no
modules at all. A gadget setup that picked a UDC by globbing `/sys/class/udc`
could bind to it and look healthy with nothing on the wire, particularly before
`dwc3-msm` has probed, when it would be the only entry. That trap is already
closed: `p260_udc_name` is the literal `"a600000.dwc3"`.

One further thing was looked at and found already known. `p260_wait_configured`
returns `-P260_EPROTO` when the state is `configured` but `current_speed` is not
exactly `high-speed`, and this unit measured the stock link at `super-speed`,
which looks like a predicate that could turn a successful enumeration into a
failure. It is not a defect and not a discovery:
`S22PLUS_FYG8_P274_..._2026-07-26` already tabulates `stage 0x8f, EPROTO` as
"configured but `current_speed` was not exact `high-speed`" with its own
diagnostic path, so the strictness is deliberate. The candidate also writes
`max_speed high-speed` to the gadget and verifies the readback, so it does not
rely on the controller's default. Searching the campaign's records finds no run
in which stage `0x8f` produced `EPROTO`; the recorded `0x8f` outcome is
`ETIMEDOUT` before `configured`. The high-speed pin has therefore never been the
observed failure, which bounds it rather than clearing it.

## The module identity question is closed, and it closes wider than asked

The module-closure-plan unit left one thing unresolved and said why: the
ramdisk's 423456-byte `pdic_max77705.ko` did not appear verbatim inside
`vendor_dlkm.img`, and because that image has F2FS compression enabled a byte
search proved nothing either way. Mounting the filesystem removes the obstacle
entirely, since the host kernel decompresses on read. The two files are not
merely the same build:

    27e988788242888dc0c3acaf835a66585c024b034b07741e619b674ee77db3db  ramdisk
    27e988788242888dc0c3acaf835a66585c024b034b07741e619b674ee77db3db  vendor_dlkm

Identical bytes, identical 423456-byte size. The earlier caution that "same name
is not same module" was the right caution and the answer to it is that here they
are the same file.

Comparing every module rather than the one that was asked about turns this from
a fact into a structural property. The vendor_boot ramdisk holds 441 `.ko` files
and `vendor_dlkm` holds 356; 306 names appear in both, and **all 306 are byte
identical, with zero differences**. The two disjoint sets are not arbitrary:

- 135 modules are ramdisk-only, and every one of the 135 is in the ramdisk's
  own 140-entry first-stage `modules.load`. The first stage's exclusive modules
  are exactly the ones `vendor_dlkm` does not re-ship.
- 50 modules are `vendor_dlkm`-only, and they are entirely late-boot media and
  data: the `lpass_cdc`, `wcd`, `swr` and `q6` audio stack, `msm_video`,
  `msm-eva`, `camera`, `hdmi`, and the `rmnet_*` and `ipa*` networking modules.
  Not one of them matches `usb`, `typec`, `muic`, `pdic`, `dwc`, `phy`, or
  `redriver`.

All fourteen members of the `pdic_max77705` closure — `usb_notify_layer`,
`mfd_max77705`, `switch_class`, `common_muic`, `pdic_notifier_module`,
`vbus_notifier`, `usb_typec_manager`, `usb_f_ss_mon_gadget`, `redriver`,
`if_cb_manager`, `qc_usb_audio`, `dwc3-msm`, `spu_verify` and `pdic_max77705` —
are present in both trees and byte identical in both.

The consequence is stronger than the question. A candidate that loads the mux
and USB stack from the ramdisk is loading the same bytes stock loads from
`vendor_dlkm`, so no difference between the two copies can explain any candidate
failure, and no candidate needs to mount a logical partition to reach the USB
path. Byte identity is also a strictly stronger statement than the matching
vermagic the closure-plan unit recorded.

## The P3.17 plan against the first stage, and what it omits on purpose

The review's second ranked item was this diff, and the review supplied its own
numbers. They were checked rather than repeated. The plan is not a file: it is
the 59-entry `s22plus_fyg8_p241_e2_plan.h` table grown by a chain of pinned
transforms, 59 to 60 by `dispcc-waipio.ko`, 60 to 61 by `usb_notifier_qcom.ko`,
61 to 64 by `msm-geni-se.ko`, `gpi.ko` and `i2c-msm-geni.ko`, and 64 to 69 by
`spmi-pmic-arb.ko`, `pinctrl-spmi-gpio.ko`, `qti-regmap-debugfs.ko`,
`regmap-spmi.ko` and `qcom-spmi-pmic.ko`. Reconstructing it from the header and
those insertions lands on 69 entries with 69 unique names, which is the
self-check, and matches `EXPECTED_MODULE_PLAN_COUNT = 69` in both the P3.17
static checker and its qualification closure.

Against the ramdisk's 140-entry first-stage `modules.load`, the split is **42
overlapping and 27 genuinely late**, exactly the review's figures, and all 69
are present in the vendor_boot ramdisk. The 27 are, in plan order:
`qmi_helpers`, `eud`, `phy-msm-ssusb-qmp`, `repeater`, `redriver`,
`usb_notify_layer`, `qcom_glink`, `qcom_glink_smem`, `qcom_smd`,
`rproc_qcom_common`, `pdr_interface`, `pmic_glink`, `switch_class`,
`common_muic`, `vbus_notifier`, `if_cb_manager`, `pdic_notifier_module`,
`usb_typec_manager`, `usb_f_ss_mon_gadget`, `phy-msm-snps-hs`,
`phy-msm-snps-eusb2`, `qc_usb_audio`, `dwc3-msm`, `ucsi_glink`, `gpi`,
`i2c-msm-geni` and `usb_notifier_qcom`.

Two things fall out of the diff that the counts alone do not show.

**The candidate passes no module parameters at all.** Every plan entry carries a
`params` field, and it is the empty string for all 59 base entries. The section
above established that stock supplies `muic_param_pmic_info=3` and its siblings
through the kernel command line and libmodprobe, and that `insmod` does not read
those. This is the other half of that statement, verified in the plan rather
than inferred: there is nowhere in the plan for a parameter to be passed, and
none is.

**The plan omits the stock mux driver, and the omission is a substitution.**
Three of the fourteen `pdic_max77705` closure members are absent from the 69:
`mfd_max77705.ko`, `spu_verify.ko` and `pdic_max77705.ko`. None of the three is
in the first-stage list either, so nothing else loads them. That reads like a
gap until the custom module is accounted for:
`workspace/public/src/kernel-modules/s22plus_max77705_mux_diag/` builds
`s22plus_max77705_mux_diag.ko`, which the P3.17 executability fixed point names
as `CUSTOM_LATE_MODULE` against `CUSTOM_LATE_COMPAT = "maxim,max77705"`, and
whose `of_device_id` table matches that same parent compatible. Two drivers
cannot bind one device, so omitting `pdic_max77705.ko` is not an oversight but a
precondition for the diagnostic to bind at all; `mfd_max77705.ko` and
`spu_verify.ko` follow because nothing else needs them. The generators enforce
the separation in the other direction too, asserting the plan header contains
zero occurrences of the diagnostic's name.

The consequence is specific to P3.17 and must not be generalised. On a P3.17
candidate the stock MUIC driver is not loaded, so
`max77705_muic_attach_usb_path` — the function that turns an attach event into
`com_to_usb_ap` — cannot run, and CONTROL1 is instead written by the
diagnostic's direct SMBus opcode sequence, reading with opcode `0x05` and
writing with `0x06`. That is the structural ground under the review's demotion
of the mux hypothesis: P3.17's `0x3f` then `0x09` then `0x09` shows the command
protocol reached and CONTROL1 retaining COM_USB, and it says nothing about the
stock attach path because that path was not present. This says nothing about
other candidates. S7A2, M7, M11, M12 and M18 did load `pdic_max77705` and failed
anyway, which the campaign has already recorded and which this diff does not
revisit.

Finally, the plan omits 96 of the 140 stock first-stage modules. That number is
recorded as a fact about scope, not as a defect: the candidate is a different
first stage with different goals, and nothing here establishes that any of the
96 is needed for USB.
