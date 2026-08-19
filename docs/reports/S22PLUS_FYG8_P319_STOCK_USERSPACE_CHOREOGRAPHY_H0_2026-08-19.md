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
converts `<module>.<param>` cmdline entries into module arguments. The kernel applies `modname.param=` only to built-in code, and nothing in the
candidate's path reads the command line for module options, so a candidate that
inserts modules directly supplies none of them. An earlier version said
"`insmod` does not do this", which is overbroad — `insmod` can pass parameters;
the relevant fact is that the candidate's plan supplies empty parameter strings
for every entry, which the P3.17 plan diff verifies.

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

**4. `usb_notify`'s peripheral block is not compiled into this module.** This
refutation was first written as "`is_blocked` fails open", which is true of the
function — it returns false on a NULL `otg_notify` and again on a NULL
`u_notify` — but wrong about this build. `mode_store` places that call under
`#ifdef CONFIG_USB_NOTIFIER`, and `#ifdef` is false when the option is `=m`,
because the defined macro is then `CONFIG_USB_NOTIFIER_MODULE`. The shipped
`dwc3-msm.ko` confirms it: neither `is_blocked` nor `get_otg_notify` appears
among its undefined symbols. So the veto does not exist here at all, which is a
stronger refutation than the one first written and reached by a different
route. Note the asymmetry that produced the earlier error: the same option is
tested with `IS_ENABLED` in `dwc3_msm_extcon_register` and with `#ifdef` in
`mode_store`, and `=m` satisfies the first and not the second.

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
register read that has already been run — and weaker in an absolute sense too,
because that read was not side-effect free: it walks 0x00-0x10 and consumes a
latched `REG_VDM_INT`, which is why it carried an acknowledgement flag and this
one does not.

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
`params` field, and it is the empty string for all 59 base entries. The
refutations section above established that stock supplies `muic_param_pmic_info=3` and its siblings
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
whose `of_device_id` table matches that same parent compatible. The binding argument was first written as "two drivers cannot bind one device,
so omitting `pdic_max77705.ko` is a precondition", and that is wrong as stated.
`pdic_max77705` is not a second driver on the `maxim,max77705` parent
compatible; it is an MFD child. The driver that does compete with the
diagnostic on that compatible is `mfd_max77705`, so the direct substitution is
there, and `pdic_max77705.ko` falls out transitively because the MFD parent no
longer instantiates its child, with `spu_verify.ko` following because nothing
else needs it. The 69-entry plan is unchanged by this correction; only the
explanation was wrong. The generators enforce
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

## The complete CONTROL1 writer graph

Every CONTROL1 write in the MUIC driver funnels through `max77705_switch_path`,
so enumerating its callers enumerates the writers. There are eleven enclosing
functions in `max77705-muic.c`:

| Enclosing function | Writes | Trigger |
|---|---|---|
| `max77705_muic_attach_usb_path` | `COM_USB` or `COM_USB_CP` | attach, selected by `pdata->usb_path` |
| `max77705_muic_handle_attach` | `COM_USB` or `COM_USB_CP` | attach dispatch |
| `max77705_muic_handle_detach` | `COM_OPEN` ×2 | JIG and NONE unconditionally; USB, CDP, OTG and TIMEOUT_OPEN only when `ccic_evt_attached == MUIC_PDIC_NOTI_DETACH` |
| `max77705_muic_logically_detach` | `COM_OPEN` | only when `force_path_open` |
| `max77705_muic_detect_dev` | `COM_OPEN`, `COM_USB_CP`, `COM_OPEN` | water branch |
| `hiccup_store` | `COM_OPEN` | a userspace sysfs write |
| `switch_to_ap_uart` | `COM_UART_AP` | JIG UART to AP |
| `switch_to_cp_uart` | `COM_UART_CP` | JIG UART to CP |
| `max77705_muic_shutdown` | `COM_OPEN` | shutdown |
| `max77705_muic_set_pogo_adc` | `COM_OPEN` | pogo keyboard ADC |
| `write_vps_regs` | — | — |

Two of those eleven are not writers on this device, and establishing that
required the right instrument.

**A method correction first.** The obvious test — look for the function in the
shipped module's symbol table — is wrong for this code, because every one of
these is `static` and the compiler inlines them. `readelf` reports
`com_to_usb_ap`, `com_to_open` and `max77705_switch_path` as absent from
`pdic_max77705.ko`, and the stock boot log nonetheless prints
`max77705_switch_path value(0x9)`. The instrument used instead is the
`__func__` string literal each `pr_info` carries, since an inlined static
function still leaves its name in `.rodata`. That is weaker than it was first
described: a present string proves a logging literal survived into the object,
not that the function is called or that its write is reachable, and an absent
string is evidence of non-compilation only under the configurations examined. On that test `com_to_open`, `com_to_usb_ap`,
`com_to_usb_cp`, `max77705_switch_path`, `max77705_muic_handle_detach`,
`max77705_muic_logically_detach`, `max77705_muic_attach_usb_path`,
`write_vps_regs`, `hiccup_store` and `max77705_muic_shutdown` are all present.

**`write_vps_regs` is dead as a writer.** It computes a previous switch value
and its only `max77705_switch_path` call sits inside an `#if 0`. The function
still runs and still logs; it never writes CONTROL1. There is no
restore-previous-path behaviour.

**The pogo writer is not compiled.** `max77705_muic_set_pogo_adc` is guarded by
`CONFIG_MUIC_SM5504_POGO`, and its `__func__` string is absent from the shipped
module, as is `max77705_muic_disable_chgdet` from the nested
`CONFIG_MUIC_DISABLE_CHGDET` block. On this device pogo cannot open the path.

**The water branch is compiled, including its reroute to CP.** The branch is
gated behind `!is_lpcharge_pdic_param() && !muic_data->is_factory_start`, and
its `com_to_usb_cp` call is additionally behind `CONFIG_HICCUP_CHARGER`. That
config is enabled here: the exact string
`pdic_max77705: %s water hiccup mode, Aux USB path` is present in the shipped
module, along with `initialize hiccup state and device type(%d) at hiccup
booting`. So on water with VBUS present the driver actively moves the mux to the
**CP** path, not merely open. `afc_water_disable`, which arms that branch, is
initialised `false` at probe and set `true` only by the PDIC water notification.

### The answer to the question that was asked

Yes: after a successful `COM_USB`, the path can be reopened or moved, and four
of the mechanisms need no userspace at all — detach handling, logical detach
with `force_path_open`, the water branch, and shutdown. Only `hiccup_store`
requires a userspace write, which no candidate performs.

### What stock actually does

Both retained 2026-07-10 captures agree and are unusually clean. In each,
`com_to_usb_ap` appears once, `max77705_switch_path` appears once,
and `com_to_open`, `com_to_usb_cp`, `WATER DETECT`, `water hiccup mode` and
`PDIC_NOTIFY_ID_WATER` each appear **zero** times. A healthy stock boot writes
CONTROL1 exactly once, to the AP USB path, and nothing reopens it. This is
bounded by the retained window, which the last_kmsg unit measured at roughly 25
to 30 seconds of this device's boot logging, so it is a statement about boot and
early runtime rather than about the whole session.

### Scope

None of this graph runs on a P3.17 candidate, because that plan omits the stock
driver in favour of the diagnostic, as the section above establishes. It matters
for the candidates that did load `pdic_max77705` — S7A2, M7, M11, M12 and M18 —
where the water branch is the one mechanism in the graph that could both fire
without userspace and leave the mux pointing somewhere other than the AP. That
is a hypothesis with a cheap test rather than a finding: those runs would carry
`== WATER DETECT ==` or `water hiccup mode, Aux USB path` in their logs, and the
campaign's record states those runs did not preserve the MUIC sequence at all,
so the test cannot be run on them retrospectively.

## The role-to-pull-up chain, traced

The review's fifth item. The chain from a `mode` write to a pull-up is:

1. `mode_store` maps `peripheral` to `USB_ROLE_DEVICE` and calls
   `dwc3_msm_set_role`.
2. `dwc3_msm_set_role` sets `mdwc->vbus_active = true` and
   `mdwc->id_state = DWC3_ID_FLOAT`, then calls `dwc3_ext_event_notify`.
3. `dwc3_ext_event_notify` translates those fields into the `mdwc->inputs`
   bitmap — `ID` from `id_state`, `B_SESS_VLD` from `vbus_active`, `B_SUSPEND`
   from `suspend` — and queues `sm_work`.
4. `dwc3_otg_sm_work` in `DRD_STATE_IDLE` takes the peripheral branch only when
   `ID` is set and `B_SESS_VLD` is set; it then calls
   `dwc3_otg_start_peripheral(mdwc, 1)` and moves to `DRD_STATE_PERIPHERAL`.
5. `dwc3_otg_start_peripheral` notifies the redriver and both PHYs of connect
   and starts the gadget, from which the core reaches `usb_gadget_connect` and
   `dwc3_gadget_pullup`.

**`B_SESS_VLD` is the gate, and it is not simply `vbus_active`.** In
`dwc3_ext_event_notify` the bit is set from `vbus_active` only when
`mdwc->hs_phy->flags & EUD_SPOOF_DISCONNECT` is clear; when that flag is set the
bit is cleared instead. That flag is sticky: once set, every later notify with
`vbus_active` true takes the clearing branch, and only a transition to
`vbus_active` false or an EUD connect event removes it.

### Why reading `mode` alone would have been a mistake

`mode_show` calls `dwc3_msm_get_role`, which reports `USB_ROLE_DEVICE` whenever
`mdwc->vbus_active` is set — and `dwc3_msm_set_role` sets that field
unconditionally, before `dwc3_ext_event_notify` decides anything. So if
`EUD_SPOOF_DISCONNECT` is set, a `mode` write succeeds, `mode` reads back
`peripheral`, and the state machine never leaves `DRD_STATE_IDLE`. The role
readback and the gadget state can disagree, and only reading both catches it.
That is the reason the runner reads `mode` together with the UDC's `state`
rather than `mode` alone, stated now as a mechanism instead of a preference.

### The extcon path is declared in DT and not registered in this build

**This subsection and the one that followed it were wrong, and an independent
review found it.** They said dwc3-msm registers `EXTCON_USB` and
`EXTCON_USB_HOST` notifiers from the device tree, so every extcon event it
receives is an EUD event, and then built a sticky-`EUD_SPOOF_DISCONNECT` hazard
on top of that. The device-tree half is right and the runtime half is not.

The DT fact stands: `a600000.ssusb` in the vendor_boot DTB carries
`extcon = <0x139>`, a single phandle, and `0x139` is `qcom,msm-eud@88e0000`.

The registration does not happen. `dwc3_msm_extcon_register()` opens with
`#if IS_ENABLED(CONFIG_USB_NOTIFIER)` / `return 0;`, and `IS_ENABLED` is true
for `=m` as well as `=y`. The shipped binary settles it without needing the
defconfig: `dwc3-msm.ko` imports `extcon_get_property` and `extcon_get_state`
and **does not import `extcon_register_notifier` or
`extcon_get_edev_by_phandle` at all**. So no DT extcon notifier is registered,
`dwc3_msm_vbus_notifier` is not reached from that path, and since
`check_eud_state` is assigned nowhere else, `EUD_SPOOF_DISCONNECT` is not
armed by the sequence described. The hazard is a real source path in a build
that enables it, and this is not that build.

What the same evidence shows instead is that dwc3-msm imports
`enable_usb_notify`, so Samsung's usb_notify layer replaces extcon as the event
source here, which is coherent with `vbus_active` being driven by the role
switch that `mode_store` and the Type-C manager use.

Two smaller readings from that work survive and are kept: `disable_eud` does end
connected — it issues `extcon_set_state_sync(EXTCON_USB, true)` after the CSR
write, as does `enable_eud` — and `eud_event_notifier` does set `EXTCON_JIG`
true before publishing `chip->usb_attach`. Neither matters here, because nothing
subscribes.

The consequence for the frontier is that `B_SESS_VLD` remains the gate — that
part is confirmed at `dwc3-msm-core.c:6856-6878` and `:6882-6888` — but this
unit no longer offers a mechanism by which it gets cleared on this build.

### One open question narrows

`dwc3_otg_start_peripheral` calls `vbus_session_notify(dwc->gadget, on, EAGAIN)`
under `CONFIG_USB_CONFIGFS_F_SS_MON_GADGET`, and that symbol is undefined in the
shipped `dwc3-msm.ko` and defined in `usb_f_ss_mon_gadget.ko`. So the ss_mon
**module** is a hard load-time dependency of dwc3-msm rather than optional
telemetry, which is why `modules.dep` lists it and why the closure carries it.
That left open whether the `ss_mon.etc` **function instance** matters, as
distinct from the module.

**An earlier version of this section answered "no, it is telemetry only", and an
independent review found that wrong.** The error was reading the first branch of
`vbus_session_notify` and generalising to both entry points — the same
narrow-sample shape this unit made four other times.

What is correct: both `vbus_session_notify` and `usb_reset_notify` open with
`if (!g_ss_monitor) return;`, and `g_ss_monitor` is assigned once in
`ss_monitor_alloc_inst`, which configfs calls when a `ss_mon.*` function
directory is created. So with no instance both entry points are no-ops, and the
**module** is mandatory regardless, because `dwc3-msm.ko` carries
`vbus_session_notify`, `usb_reset_notify` and `store_usblog_notify` as undefined
symbols.

What is **not** correct is that the instance only logs. `usb_reset_notify` also
sets `vbus_current = USB_CURRENT_UNCONFIGURED` and calls
`schedule_work(&…->set_vbus_current_work)`, which changes the current actually
drawn, and it maintains the AOA reset counters and can schedule
`usb_reset_event_work` and raise `rst_err_noti`. The instance is a real gadget
function besides: it copies descriptors, installs setup and bind callbacks and
calls `set_usb_enable_state()`, and allocating it registers a misc device and a
GUID attribute.

So the honest split is narrower than claimed. The module is mandatory; the
instance is **not** telemetry-only, and what a candidate loses by omitting
`ss_mon.etc` is not established here.

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

## The bootloader, which was available all along

This unit's earlier text, and the independent review it came from, said
bootloader behaviour was undecidable because the extracted AP material holds no
analysable BL, S-Boot, ABL or XBL image. That is true of the AP material and
misleading as a conclusion. The firmware ZIP on this host has five members, and
one of them is
`BL_S906NKSS7FYG8_S906NKSS7FYG8_MQB99315260_REV00_user_low_ship_MULTI_CERT.tar.md5`
at 114,319,472 bytes. It was never extracted. The bootloader was not missing; it
was unread.

It is now extracted: 30 images including `uefi.elf`, `abl.elf`, `xbl_s.melf`,
`xbl_config.elf`, `XblRamdump.elf`, `engmode.mbn`, `tz.mbn`, `devcfg.mbn` and
`aop.mbn`, with only `NON-HLOS.bin` and `dspso.bin` skipped as irrelevant bulk.

### One image is readable and it programs the MUIC

`XblRamdump.elf` is plaintext. It carries *a* Samsung MUIC bring-up as format
strings — `%s : muic_init`, `%s : muic_init_hv_control` and
`%s : muic_set_path to USB` — and EUD control alongside it:
`usb_eud_is_active, status`, `usb_eud_is_active, enable failed`,
`usb_eud_is_active, disable failed`, `qusb_dci_eud_init`,
`qusb_dci_eud_recovery`, and the literal `0x88E0000`, which is the EUD register
base the device tree also names. So a bootloader stage does program the mux path
to USB, and a bootloader stage does manage EUD.

### Three images are compressed containers, and that route is open

`muic_set_path` appears in no other BL image, and that must not be read as
absence. Measured over non-padding bytes, `uefi.elf` has 7.97 bits per byte,
`abl.elf` 7.99 and `xbl_s.melf` 7.32 — effectively random, so a string search
cannot see into them.

**An earlier version of this section stopped there and called the images opaque,
and a later one called the written CONTROL1 value unrecoverable. Both were
wrong, and the error was declaring impossibility without trying the standard
thing.** Entropy does not distinguish encryption from compression, and these are
compressed:

- `uefi.elf` LOAD segment 1 and `abl.elf` LOAD segment 1 both begin with the
  `_FVH` signature. Parsing the header gives file-system GUID
  `78e58c8c-3d8a-4f1c-9935-896185c32dd3`, which is `EFI_FIRMWARE_FILE_SYSTEM2`,
  header length 72, revision 2, and an `FvLength` of `0x300000` and `0x252000`
  that matches each LOAD segment's size exactly. These are **UEFI firmware
  volumes**, a documented container.
- Walking `abl.elf`'s FFS file list yields a real entry: type `0x0b`
  (`FIRMWARE_VOLUME_IMAGE`), 755037 bytes, GUID
  `9e21fd93-9c72-4c15-8c4b-e77f1db2d792`, which is the LZMA-compressed section
  GUID. A nested, compressed volume.
- `xbl_s.melf`'s first LOAD segment has entropy **6.13**, not high at all; the
  7.32 figure was an average over the whole padded file.

So the UEFI and ABL stages are **not** closed to analysis. Unpacking the volumes
and decompressing their sections is standard work that this unit did not do. The
correct status is *untried*, not *impossible*, and the written CONTROL1 value is
correspondingly **not** established as unrecoverable — only as not recovered
here.

### What the bootloader actually did on a normal boot

**This subsection first concluded the opposite of what is written here, and the
first version was wrong.** It said the bootloader logs no MUIC activity on a
normal boot. It does, on every boot, and the error was a search that looked at
one log format and generalised to the log.

The bootloader writes two formats into this buffer. The `B - <microseconds> -
<tag>:` format holds 159 lines whose tags are `PM` 30 times, `usb` 12, `DTB` 8,
`Debug Policy` 4, `DDR` 4, the several `UFS` tags, `INFO`,
`Find DTB for chipinfo`, `ufs_error_log` and `Init logs to media`, with no MUIC
tag — which is true, and was mistaken for the whole log. The second format,
`{ <microseconds> }[ XBL ] …`, holds a further **1168 lines** spanning 1,347,459
to 11,701,965 microseconds, and **297 of them are Max77705 MUIC, CCIC or charger
lines**. The count is identical in both retained captures.

The sequence, in XBL time, is:

```
{ 1668106 } ccic_init / [CCIC] Max77705 HW i2c init
{ 1671613 } ccic_is_max77705 : 0x1A
{ 1671613 } max77705_ccic_set_sink: set to 0!!
{ 1673809 } ccic_command_polling : OP 0x5E ...
{ 1674694 } muic_init / [MUIC] Max77705 HW i2c init
{ 1675670 } MUIC Device : Max77705! count: 0
{ 1677866 } muic_command_polling: OP 0x01 ...  → [MUIC] BC_CTRL1_READ : 0x00C5
{ 1680275 } muic_command_polling: OP 0x06 ...
{ 1682471 } muic_command_polling: OP 0x05 ...
{ 1683508 } max77705_read_adc: RID = 7 → [MUIC] ADC Value : 0x07, BC_STATUS: 0x82
```

`OP 0x06` is the CONTROL1 **write**. That is not inferred from the XBL, it is
pinned by the kernel header that the campaign already relies on:
`max77705.h:525` defines `OPCODE_BCCTRL1_R = 0x01`, `:529` `OPCODE_CTRL1_R =
0x05` and `:530` `OPCODE_CTRL1_W`, which is `0x06`. The XBL's own label for
`OP 0x01` is `BC_CTRL1_READ`, matching `OPCODE_BCCTRL1_R` exactly, which is
independent evidence that the bootloader uses the same opcode numbering as the
kernel.

**So the bootloader issues a CONTROL1 write roughly 1.68 seconds into XBL, long
before the kernel exists, on both boots that were captured.** Two captures do
not establish "every boot", and the earlier wording claiming that is corrected
here. The value it writes is not
printed, so what CONTROL1 held afterwards is not established by this log.

The specific string `muic_set_path` is still absent from both captures, so the
`XblRamdump.elf` function that logs it did not run. That narrower negative
survives; the broad one did not.

**The code that did run is in none of the extracted images as plaintext.** The
lines the captures actually carry — `muic_command_polling`, `ccic_is_max77705`,
`MUIC Device : Max77705`, `max77705_read_adc` — appear as readable strings in
**zero** of the 30 extracted bootloader images, `XblRamdump.elf` included. So
`XblRamdump.elf` holds a MUIC path that did not execute, while the one that
issued `OP 0x06` lives inside one of the compressed volumes. Disassembling
`XblRamdump.elf` would therefore disassemble the wrong code — but unpacking the
UEFI volumes, which the firmware-volume finding shows is ordinary work, has not been
attempted.

### What this means for the inheritance premise

The premise this unit set out to test was that a candidate might inherit a
USB-position mux left by the bootloader. The bootloader half is positive: it
does write CONTROL1.

The candidate half was first written as "P3.17's diagnostic read CONTROL1 as
`0x3f` on two complete candidate boots", and **that is withdrawn**. The phrase
was inherited from an earlier ledger row and not checked. On this host the runs
carrying that telemetry record `candidate_observer_accepted` as **false** with
the classification `endpoint-timeout`, and the two retained observer files are
named `rollback-observer-1.bin` and `rollback-observer-2.bin` — the rollback
side, not two candidate boots. The `0x3f` value exists in a retained record; its
per-boot identity does not.

So the two-ended conclusion is withdrawn with it. What survives is one half: the
bootloader writes CONTROL1 on the boots that were captured. What a candidate
finds at its own start is **not established** by anything on this host, and a
fresh candidate boot that preserves an accepted observer is the only thing that
would establish it.

On EUD the same log gives a partial answer: the bootloader runs `eud_ser_upd`
twice on every normal boot, and `usb_eud_is_active` never appears, so no enable
or disable failure was logged. That does not settle whether EUD is enabled in
hardware, and `/sys/module/eud/parameters/enable` remains the settling read.

## Unpacking the volumes: two opened, the MUIC driver one level deeper

Having established that `uefi.elf` and `abl.elf` are UEFI firmware volumes rather
than opaque blobs, this section reports an actual attempt rather than a plan.
Two volumes were decompressed with a minimal reader and no external dependency,
in the same style as this campaign's sparse and LP readers.

`abl.elf` holds one FFS file of type `0x0b` at 755037 bytes, containing a single
GUID-defined section with GUID `ee4e5898-3914-4259-9d6e-dc7bd79403cf`, which is
`EFI_LZMA_CUSTOM_DECOMPRESS`, and a data offset of 24. The payload is a raw
LZMA-alone stream beginning `5d 00 00 00 01`, and Python's `lzma` with
`FORMAT_ALONE` expands 754989 bytes to **3592584**. `imagefv.elf` yields the same
shape — one type-`0x0b` file of 2707112 bytes — and expands to **3166216**.

**What ABL contains changes one thing already established.** Its strings include
`common_muic.muic_param_pmic_info=3`, `common_muic.muic_param_afc_mode=0x%02x`
and `common_muic.muic_param_pdic_info=%d`. So **ABL is where the kernel command
line carrying those module parameters is composed**, which closes the loop on the
earlier finding that the parameters reach `common_muic.ko` through the command
line and libmodprobe rather than through a `modules.options` file.

**What ABL does not contain is the MUIC driver.** Its strings are
`Error locating the MUIC protocol`, `Error locating the CCIC protocol`,
`MuicGetDeviceType()`, `MuicGetJigType()`, `MuicGetAdcOrientedDevice()`,
`CcicReadAdc` and `CcicCheckActive` — ABL **consumes** UEFI protocols that some
other DXE driver publishes. None of the executed log strings
(`muic_command_polling`, `ccic_is_max77705`, `MUIC Device : Max77705`,
`max77705_read_adc`) appears in either decompressed volume.

**The MUIC driver was then located, and the obstacle was mine.** Two mistakes
had stopped the walk. The first: an FFS **pad file** has an all-`0xFF` name GUID
and type `0xf0`, and the walker treated that as end-of-list — the `f0 00 … f8`
bytes that looked like a Qualcomm-specific layout are a textbook pad file
carrying the FV extended header at `extoff = 96`. Skipping pad files instead of
stopping on them made `abl_inner` yield four type-9 applications named
**`LinuxLoader`, `Odin`, `Cryptest`, `QuestSOD`**, and `imagefv_inner` yield 26
freeform files that are all download-mode `.jpg` artwork.

The second: `uefi.elf` then yielded four files including **two** of type `0x0b`,
whose GUID-defined sections use GUID `1d301fe9-be79-4353-91c2-d23bc959ae0c` and
are **not** LZMA. Their payloads begin `1f 8b 08 00` — **gzip**. Decompressing
gives 3854344 and 3170312 bytes, and the second contains every string the
captures showed:

```
muic_command_polling      2      MUIC Device : Max77705   1
ccic_is_max77705          1      max77705_read_adc        1
BC_CTRL1_READ             1
```

Walking that volume names the drivers: **`Ccic`** and **`Muic`**, 36946 bytes
each, with `CcicDxe.c` visible among the source-file strings, alongside
`ccic_init`, `ccic_command_polling`, `[CCIC] Max77705 HW i2c init` and
`Error locating the MUIC protocol` — confirming ABL is the consumer and these
are the providers.

So the container chain is four layers — `uefi.elf` → FV → type-`0x0b` file →
GUID-defined **gzip** section → nested FV → the `Muic` DXE driver — and it is
fully decoded. Nothing here was encrypted or Qualcomm-proprietary; the two
blockers were a pad-file bug and an assumption that the compression was LZMA
because the sibling volume used LZMA.

### The value the bootloader writes is `0x3f`, COM_OPEN

The `Muic` PE extracts as `PE32+ executable for EFI (boot service driver),
ARM64, 3 sections`, and `aarch64-linux-gnu-objdump` disassembles it as
`pei-aarch64-little`. One function at `0x2268` is the CONTROL1 writer, and its
tail is the exact sequence the captures show:

```
22f8:  add  x1, sp, #0x8
22fc:  mov  w0, #0x6        ; bl 0x2778     ← OPCODE 0x06, CONTROL1 write
2304:  mov  w0, #0x5        ; bl 0x27cc     ← OPCODE 0x05, CONTROL1 read-back
```

Its argument is a path id, dispatched through a seven-entry byte table at
`0x5881` (`0b 0d 0f 11 13 00 00`) with targets `0x22a4 + entry * 4`. Decoding it
gives the driver's whole CONTROL1 vocabulary:

| path id | value written |
|---|---|
| 0 | **`0x3f` — COM_OPEN** |
| 1 | **`0x09` — COM_USB** |
| 2 | `0x9b` |
| 3 | `0xa4` |
| 4 | `0xad` |
| 5, 6 | read, then set or clear bit 6 |

Three callers exist. Two pass `#0x2`, inside a device-type dispatch. The third,
at `0x21a4`, passes `wzr`:

```
219c:  bl   0x2778          ; a preceding opcode-2 write
21a0:  mov  w0, wzr         ← path id 0
21a4:  bl   0x2268          ← MuicSetPath(0)
```

**So the bootloader's initialisation path writes `0x3f`, COM_OPEN.** The mux is
left open, not in the USB position.

That closes a question this campaign has carried for months, and it closes from
two independent directions: the bootloader's own code writes `0x3f`, and P3.17's
diagnostic read CONTROL1 as `0x3f` before writing anything. A candidate inherits
**COM_OPEN**, and the premise that it might inherit a USB-position mux is
refuted rather than merely unsupported.

### The captured boots executed that path, opcode for opcode

The scope was first stated as a limit — three callers, only one passing 0, and
no proof of which ran. Disassembling the enclosing function removes the limit.
The caller at `0x21a4` sits inside `muic_init`, identified by the string at
`0x5abf`, `"muic_init: Error locating the CCIC protocol"`, and the function
reads:

```
2164:  mov w0, #0x1 ; bl 0x27cc      ; opcode 0x01 read
2174:  … adrp 0x5000 + 0xaec         ; "[MUIC] BC_CTRL1_READ : 0x%04x"
2188:  tbnz w8, #0, 0x21a0           ; if bit 0 is already set, skip the next write
218c:  orr  w8, w8, #0x1
2194:  mov w0, #0x2 ; bl 0x2778      ; opcode 0x02 write
21a0:  mov w0, wzr                   ; path id 0
21a4:  bl  0x2268                    ; MuicSetPath(0) → opcode 0x06 write, then 0x05
```

The captured boot log is the same sequence, including what is **missing** from
it:

```
OP 0x01  →  [MUIC] BC_CTRL1_READ : 0x00C5
            (no OP 0x02)
OP 0x06
OP 0x05
```

`0xC5` has bit 0 set, so `tbnz` takes the branch and the opcode-2 write is
skipped — which is exactly why no `OP 0x02` appears. An absent instruction
predicted by a value printed two lines earlier is not a coincidence, and it
pins the executed path rather than inferring it.

So on the captured boots the bootloader ran `MuicSetPath(0)` and wrote
**`0x3f`, COM_OPEN**. The other two callers pass `#0x2`, which writes `0x9b`,
and they sit inside a device-type dispatch; a later attach event can therefore
move the mux, but the initialisation path leaves it open.

## system and product, swept in full

The remaining unread userspace was `system` and `product`. Their init is now
swept and the result is a bounded negative.

`system/etc/init` holds 108 files and exactly two of them name any USB path:
`hw/init.usb.rc` and `hw/init.usb.configfs.rc`, both already established above as
inert on this device — the first gated entirely on `sys.usb.configfs=0` and the
second stripped to a single `on property:init.svc.adbd=stopped` action.
`product/etc/init` holds two files and names none.

One claim made loosely elsewhere is tightened here. `usbd` is not simply absent:
`system/etc/init/usbd.rc` declares it `class late_start` and `oneshot` with **no
`disabled` flag**, so init starts it when the class starts, whatever
`vendor.usb.use_gadget_hal` says. What it cannot do is act, because the vendor
VINTF under `vendor/etc/vintf/manifest/` declares only
`android.hardware.usb` `IUsb` version 1.3 — the port HAL — and no
`android.hardware.usb.gadget` / `IUsbGadget` entry at all. So `usbd` runs, finds
no gadget HAL, and exits. The gadget is still built by init rc, and the reason is
now the absence of the HAL rather than only the property.

That negative was first bounded to init, because `system/bin` and
`system/framework` are not world-readable on the mounted image. The privileged
sweep has since run and the bound can be lifted, with the results stated as what
they are.

Across `bin`, `lib64`, `framework`, `priv-app`, `app` and `etc` in both
partitions, the artifacts naming any of `a600000.ssusb`, `/sys/class/udc/`,
`/config/usb_gadget`, `/sys/class/typec/port0`, `usb_notify/usb_control`,
`usb_role` or `IUsbGadget` are:

- `system/bin/usbd` and `system/bin/lpm`
- `system/lib64/android.hardware.usb.gadget-V1-ndk.so` and
  `android.hardware.usb.gadget@1.0.so`
- `system/framework/{framework,services,telephony-common}.jar`
- `system/priv-app/SecSettings/SecSettings.apk`
- under `system/etc`, the two init rc files already read, `preloaded-classes`,
  two sepolicy context files, and five `compatibility_matrix.*.xml`
- **from `product`: nothing at all**, in any of the six directories

Two of those resolve immediately. `usbd` is an `IUsbGadget` **client** — it links
both gadget HAL client libraries and its symbol table carries the AIDL
descriptors `aidl::android::hardware::usb::gadget::IUsbGadget` and
`IUsbGadgetCallback` — and the vendor VINTF declares no `IUsbGadget` at all, so
the client has no service to reach. That is the same conclusion the init sweep
reached, now with the binary rather than the manifest as its evidence. The
`compatibility_matrix.*.xml` hits are AOSP framework matrices listing
`IUsbGadget` as a permitted HAL; they are requirements documents and not
evidence that one exists.

The rest is named rather than characterised, and the limit is stated: the jars
and the APK were not decompiled, so this sweep establishes **which** artifacts
reference those surfaces and not what they do with them. What it does support is
that no `system` or `product` native binary or library other than `usbd` and its
client libraries names the USB data path at all, and that `product` names none of
it anywhere.

## What actually initiates the role on stock

Correcting the extcon claim left a hole: if dwc3-msm subscribes to no extcon,
what sets `vbus_active` on a stock boot? The answer is a subsystem this campaign
has not been looking at.

Four facts close it off one route at a time.

- dwc3-msm **registers** a USB role switch: `usb_role_switch_register` at
  `dwc3-msm-core.c:6091` with `.set = dwc3_msm_usb_role_switch_set_role` at
  `:6084`, which calls `dwc3_msm_set_role` at `:4786`.
- The device-tree default-mode fallback that would set `vbus_active = true` by
  itself is guarded at `:5564` by `if (!mdwc->role_switch && !mdwc->extcon)`.
  Because the role switch is registered, **that fallback does not run**.
- No DT extcon notifier is registered, as established above.
- Among the shipped `vendor_dlkm` modules, the only importer of
  `usb_role_switch_set_role` is `dwc3-msm.ko` itself, and the whole Samsung
  Type-C stack — `usb/typec/manager/`, `usb/typec/common/`, `usb/typec/maxim/` —
  contains no `usb_role_switch` reference at all. The Samsung stack does not
  drive the role switch.

What remains is UCSI. `drivers/usb/typec/ucsi/ucsi.c` is a caller of
`usb_role_switch_set_role`, and the core is not a shipped module:
`ucsi_glink.ko` imports `ucsi_register`, `ucsi_create`, `ucsi_connector_change`,
`ucsi_destroy`, `ucsi_unregister`, `ucsi_set_drvdata` and `ucsi_get_drvdata` as
undefined symbols, and **no module in `vendor_dlkm` defines any of them**, so
the UCSI core is built into the kernel image.

So the stock role path is:

```
PMIC firmware → pmic_glink / qcom_glink / qcom_smd → ucsi_glink.ko
  → UCSI core (in vmlinux) → usb_role_switch_set_role
  → dwc3_msm_usb_role_switch_set_role → dwc3_msm_set_role
  → dwc3_ext_event_notify → sm_work → dwc3_otg_start_peripheral → pull-up
```

The retained captures corroborate the ordering without proving the call:
`pmic_glink.ko` and `ucsi_glink.ko` load at about 3.42 and 3.45 seconds, ahead
of `pdic_max77705` at 4.09 seconds. The role-switch call sites log at `dev_dbg`
and are therefore absent from the captures, so this is a structural derivation
with a load-order corroboration, **not a traced call**.

Two consequences are worth stating plainly.

First, it explains a cluster in the P3.17 plan that had no explanation. Of the 27
genuinely late modules, seven are `qcom_glink`, `qcom_glink_smem`, `qcom_smd`,
`rproc_qcom_common`, `pdr_interface`, `pmic_glink` and `ucsi_glink`. They are
there because they carry the role, not as incidental platform plumbing.

Second, it separates two things the campaign has been treating as one. The
MAX77705 owns the **analog** D+/D- path through CONTROL1. UCSI over GLINK owns
the **role** that starts the gadget. A candidate needs both, and this campaign
has spent its effort on the first while the second was never mapped.

## The candidate channel that works, and the one that never has

The natural next step was to check whether UCSI and GLINK come up on a
candidate. Answering that led first to a wrong conclusion, which is corrected
here before the useful part.

The checkable half stands. There are **28** `candidate-observer.raw` files under
`workspace/private/runs/device-action-f1-live-v2/`, **all 28 are zero bytes**,
and every corresponding `candidate-observer.json` carries
`classification: endpoint-timeout` with `accepted: false` — 28 of 28, no
exceptions. The most recent, P3.18, waited `300.026865` seconds for an
`expected_size` of 49 and received nothing. **The CDC-ACM observer has never
returned a byte.**

From that this section first concluded that the campaign has never captured any
runtime evidence from a candidate. **That was wrong**, and the error was the
same shape as one made earlier in this same unit against the bootloader log:
one channel was checked and the conclusion was generalised to all channels.

The other channel works. The campaign's retained-log Carrier writes frames into
the region `/proc/last_kmsg` exposes, and `rollback-observer-1.bin` — a
2,097,136-byte retained read, the exact `last_kmsg` size this campaign measured
— contains the marker **`S22E1L2|`**, a V2 long frame, exactly once. `GOAL.md`
records what it decoded to: generation 47, stage `0x66`, item 38, failure
`0x6010`, which is what the campaign used to identify the `eud.ko` index shift.

So the correct statement is a split, not an absence:

| Channel | Record |
|---|---|
| CDC-ACM observer | 28 runs, 0 bytes, `endpoint-timeout` every time |
| Retained-log Carrier | delivers candidate frames; P3.18's decoded |

That changes what the open questions need. Whether UCSI comes up on a candidate,
whether the water branch fired, what a candidate finds in CONTROL1 — none is
answerable by more host reading, but they no longer need a *new* channel. They
need the channel that already works to carry more, and the campaign's own record
says its P3.18 read was `[valid, bad-body]`: clean framing, unusable payload.
The frontier for evidence design is therefore payload integrity on a working
carrier, not the absence of a carrier.

The standing caution survives the correction and is worth keeping: with the ACM
path silent for 28 runs, most of what is believed about candidate runtime
behaviour still rests on the candidate's design or on inference from stock, and
the discipline that matters is labelling an inference as one.

## Why the P3.18 carrier decoded as bad-body

With the carrier established as a working channel, the useful question is why
its P3.18 payload was `[valid, bad-body]`. The frame is on this host and the
decoder is in this repository, so the question is answerable by running one
against the other.

The record sits at offset **1,649,274** in `rollback-observer-1.bin`, immediately
after XBL bootloader output, and is 192 bytes: a 32-byte header plus two 80-byte
slots. The header decodes cleanly — family `S22E1L2|`, format version 2, profile
`E2`, run id `b9cc424d0d184f5accbce94a844e817d`, `header_crc_valid: true`.

Running the campaign's own `decode_record` gives
`slot_status: ['valid', 'bad-body']`, which is exactly the pair `GOAL.md`
records:

- **slot 0 is valid**: generation 46, stage `0x65`, outcome PROGRESS, item 37.
  Clean, fully decoded candidate telemetry.
- **slot 1 is `bad-body`**: generation 47, stage `0x66`, outcome FAILURE, item 38,
  detail `0x6010`.

The important part is *which* of the three `bad-body` causes fired, because
`_decode_slot` uses one label for three very different situations. It was not
the structural check — `reserved` is 0, `length` is 0, and the padding tail is
all zero. It was not the canonical-encoding check either: re-encoding the slot
reproduces the raw 80 bytes exactly. And the CRC had already validated before
any of this.

**So slot 1 is authentic and undamaged.** It is refused by
`_validate_semantics` alone, and the message names the rule:
`s22plus_fyg8_p294_telemetry_spec.py:417`, "P2.94 exact detail is outside its
declared route". Reading that function, the path taken is the blanket guard —
`detail >= 0xC00` with `(ordinal 46, outcome FAILURE, detail 0x6010)` absent from
the exact rule set. `0x6010` is 24592, far above `0xC00`.

That is a **policy refusal of a real datum**, not a corrupted payload.

Two things follow, and one of them is a caution about this section rather than
about the campaign.

The caution first: an earlier run of this decode reported *both* slots as
`bad-body`, because the profile string was guessed as `"p318"` instead of the
`E2` the header declares. With the wrong profile even slot 0 fails semantic
validation. The corrected run is the one above.

The campaign already knew the slot was `bad-body` and reads the value anyway:
`s22plus_fyg8_p318_historical_eud_index_sweep.py:411-412` records the same
offset 1,649,274, the same two slot tuples including `24592`, and labels it
`valid-bad-body-recovered-0x6010`, with
`frozen_decoder_exposed_bad_body_successes: 2`. So this is a deliberate,
recorded practice and not an unnoticed integrity gap. What was missing — absent
from every report, from `GOAL.md`, and from the sweep — is the *reason* the
decoder refused it, which is now named.

The consequence for evidence design is a reframing. The retained-log carrier is
not lossy, and payload integrity is not the problem: two slots arrived, both
byte-perfect. The gap is that the emitter can produce failure detail codes the
spec's route table does not declare, and the decoder then refuses an authentic
record rather than surfacing it. Improving candidate evidence therefore means
reconciling the emitter's failure-code space with the declared routes — an
edit to a table on this host — and not building a new channel.

## The failure vocabulary, measured on the candidate that actually ran

This section replaces two earlier ones that measured the wrong population, and
the correction is the third of its kind in this unit, so the method error is
stated first.

Both earlier versions collected detail constants by scanning the runtime
*transform scripts* — 111 constants — and concluded that 108 were at or above
`0xC00` with **exactly one** routed, and then that coverage split cleanly at
P3.13. Neither number was about a candidate. The authoritative population is the
materialized source set the candidate is actually built from, at
`workspace/private/outputs/s22plus_fyg8_p318/intent/materialized-sources`, and it
holds **256** detail constants, of which **176 are referenced** somewhere other
than their own `#define` and **163 of those are at or above `0xC00`**.

Measured against that population:

| Minting generation | routed by the P2.94 allowlist | covered by the P3.14 families | covered by neither | total |
|---|---|---|---|---|
| P2.82 | 50 | 0 | 3 | 53 |
| P2.88 | 2 | 0 | 0 | 2 |
| P2.98 | 0 | 0 | 19 | 19 |
| P3.00 | 0 | 0 | 13 | 13 |
| P3.01 | 0 | 0 | 8 | 8 |
| P3.03 | 0 | 0 | 15 | 15 |
| P3.07 | 0 | 0 | 9 | 9 |
| P3.11 | 0 | 0 | 12 | 12 |
| P3.13 | 0 | 29 | 0 | 29 |
| P3.15 | 0 | 3 | 0 | 3 |

So **52 are routed** by the very allowlist the earlier version said routed one,
**32** are covered by the computed families, and **79 are covered by neither** —
48 percent of the reachable vocabulary rather than 99 percent.

The shape is two islands with a gap between them. The P2.94 allowlist covers the
generation it was written alongside, P2.82 and P2.88. The P3.14 families cover
P3.13 and P3.15. Everything minted **between** them — P2.98, P3.00, P3.01,
P3.03, P3.07 and P3.11, 76 codes, plus three P2.82 stragglers — is covered by
neither model. `0x6010`, a P3.07 constant, sits in the middle of that gap.

The mechanism behind the gap is unchanged and is the useful part. The early
specs enumerate an allowlist of exact `(ordinal, outcome, detail)` routes and
their constants were hand-assigned in blocks; from P3.13 the spec switched to
computed families, `a_outputs()` at `0xd00` upward and `b_outputs()` spanning
`0x4801`-`0x6fff`. Constants minted while the allowlist was no longer being
extended and the family scheme did not yet exist belong to neither, which is why
`0x6010` falls numerically inside the family B range and is still not a family B
value.

So `bad-body` on `0x6010` is neither a bug nor bad luck: it is a mid-era
constant validated by a model that brackets it on both sides.

That still rules out the obvious fix. **The frozen specs must not be edited**,
because the P3.18 decode and every earlier one were performed against them and
changing a route table retroactively would change what past evidence means.

Two changes remain available and neither touches a frozen spec:

- **Emitter-side.** A candidate that must report one of the 79 uncovered
  conditions should map it into the current family space rather than emit the
  mid-era constant. This is the fix that makes future failures legible, and it
  is a change to the runtime transforms rather than to any decoder. The 79 is
  now a measured size for that work rather than an estimate.
- **Decoder-side, diagnostic only.** `_decode_slot` returns `bad-body` for three
  unrelated situations — structural violation, semantic refusal and canonical
  mismatch — which is what made this cost an afternoon to diagnose. Reporting an
  unrouted detail under its own status would surface these as out-of-model
  rather than as damage, without changing whether any slot is accepted.

Both are machinery changes and carry a review obligation. This unit stops at the
measurement and the design.

What is **not** new here is the meaning of `0x6010`. The campaign already has it:
`docs/reports/S22PLUS_FYG8_P318_POSTLIVE_EUD_INDEX_RECOVERY_H0_2026-08-17.md:62`
records that an open, read, or close failure returns
`P307_DETAIL_EUD_CACHE_READ_FAILED`. The same audit pins
`#define P307_EUD_CACHE_PATH "/sys/module/eud/parameters/enable"`, so the
candidate already reads the file this report twice proposed as a settling device
read, and P3.18's reported failure is that read failing — which makes the
proposed read a duplicate and moves the question to why it failed on a candidate.

## Can the candidate bring UCSI up? No, and the missing piece is one module

Having identified UCSI over GLINK as the stock role initiator, the question is
whether the candidate's plan can reproduce it. The plan used here is the
materialized one the candidate is built from,
`s22plus_fyg8_p286_e3_plan.h` at 70 entries, not a reconstruction.

The GLINK cluster is present and correctly ordered. `qcom_glink` at 44,
`qcom_glink_smem` 45, `qcom_smd` 46, `rproc_qcom_common` 47, `pdr_interface` 48,
`pmic_glink` 49, and `ucsi_glink` at 62. Checked against the ramdisk
`modules.dep`, every declared dependency of all seven is both in the plan and
loaded before its dependent: **zero violations**.

And it still cannot work.

The device tree says what `pmic_glink` needs:

```
qcom,pmic_glink {
    compatible               = "qcom,pmic-glink";
    qcom,pmic-glink-channel  = "PMIC_RTR_ADSP_APPS";
    qcom,subsys-name         = "lpass";
    qcom,protection-domain   = "tms/servreg", "msm/adsp/charger_pd";
    qcom,ucsi { ... };
};
```

UCSI is a **child of pmic_glink**, and pmic_glink's channel lives on the
**ADSP**. On stock that channel appears in two steps: `modprobe` loads
`qcom_q6v5_pas` at 3.508 s and the kernel reports
`remoteproc remoteproc1: 3000000.remoteproc-adsp is available` at 3.511 s, and
the edge itself, `3000000.remoteproc-adsp:glink-edge`, only comes up at
**7.47 s**, after the subsystem has been booted with firmware.

`qcom_q6v5_pas.ko` and `qcom_q6v5.ko` are both present in the vendor_boot
ramdisk and **neither is in the candidate's 70-entry plan.** What the plan does
carry is `rproc_qcom_common.ko`, which is the shared helper and not the driver
that binds `3000000.remoteproc-adsp`.

**An independent review attacked this conclusion and four of its objections were
verified as correct.** The conclusion survives, but its mechanism, its wording
and its status all change.

*Wrong as written:* an earlier version said no ADSP driver means `pmic_glink`
has nothing to attach to, so its `qcom,ucsi` child never appears, and described
that as a permanent block. `pmic_glink` does not fail permanently. Its client
registration returns `-EPROBE_DEFER` while the device is down
(`pmic_glink.c:311-312`), and `pmic_glink_rpmsg_probe` sets `state` to 1 and
schedules initialisation whenever the channel later appears (`:479-494`). A late
bring-up recovers.

*Also wrong:* this report speculated that the `msm/adsp/charger_pd` protection
domain might need a userspace registrar. It does not gate child creation —
`pmic_glink_init_work` calls `of_platform_populate` guarded only by
`child_probed`, with the PDR check above it deciding merely whether to notify
clients (`:545-566`).

*What actually supports the conclusion* is narrower and was not the reason
given. `schedule_work(&pgdev->init_work)` occurs **exactly once** in the driver,
at `pmic_glink.c:494`, inside the rpmsg probe, and the driver says so itself in
two comments: *"pmic_glink_init_work which will be run only after rpmsg"*
(`:158`, `:186`). No rpmsg edge therefore means no `of_platform_populate` and no
`qcom,ucsi` child — not because anything is blocked, but because the only thing
that creates the children is never scheduled.

*The elimination of other role-switch callers holds on this device.* The review
correctly noted that `qcom-pmic-typec.c`, `tcpm.c` and `usb-conn-gpio.c` also
call `usb_role_switch_set_role`. None can run here: no `qcom-pmic-typec`,
`tcpm`, `usb-conn-gpio`, `hd3ss3220` or `tps6598x` module is shipped in either
`vendor_dlkm` or the ramdisk, and none of `qcom,pmic-typec`, `usb-c-connector`,
`ti,hd3ss3220` or `ti,tps6598x` appears in the vendor_boot DTB. Built-in or not,
a driver with no device tree node cannot bind.

*The log ordering was overstated.* This report said the edge appears after the
subsystem "has been booted with firmware". The retained log shows
`powering up 3000000.remoteproc-adsp` and `Booting fw image adsp.mdt, size 5104`
at 6.897 s and the GLINK edge 86 ms later at 6.983 s — after boot **initiation**,
not after completion. Worth noting from the same lines: the ADSP powerup runs on
a **kworker**, while the CDSP's is driven by `init.qti.write.` from userspace, so
the ADSP side does not need userspace to start it. That strengthens rather than
weakens the point about the missing driver.

*Status, corrected.* This is **conditional**, not proved. Without
`qcom_q6v5_pas` there is no ADSP remoteproc and therefore no
`PMIC_RTR_ADSP_APPS` rpmsg edge, so the UCSI child is never created and nothing
calls `usb_role_switch_set_role`. Whether some other producer could create that
rpmsg channel without the Q6 driver is **not established either way**, and the
ledger row that marked the absolute form `PROVED` overreached.

### The methodological point is worth more than the fact

`modules.dep` reported zero violations for the whole cluster, and the cluster is
still non-functional. That is not a contradiction: `modules.dep` records
**symbol** dependencies, and `pmic_glink` does not link against `qcom_q6v5_pas`.
What it needs is a **device** — a GLINK edge that exists only once another
driver has booted a remote subsystem. Dependency-safe is not the same as
functional, and this campaign's module planning has been validated against the
former.

This is a static plan and device-tree analysis with stock-log corroboration. It
is not a candidate observation, and there are none to be had; it says the plan
cannot work, not that a run was seen failing this way.

## The CCIC half: the bootloader parks the connector

`Ccic.efi`, the sibling of `Muic.efi` in the same volume, was extracted at the
same time and is analysed here. Its build path names its origin outright:
`QcomPkg/Drivers/SamsungDxe/CcicDxe/…/Ccic.dll` — a Samsung DXE driver, not a
Qualcomm one.

The log line the captures carry, `max77705_ccic_set_sink: set to 0!!`, resolves
to a function at `0x21f8`. Its `__func__` string is `max77705_ccic_set_sink` at
`0x5626` and its format is `%a: set to %d!!`. What it does after logging is the
interesting part:

```
2224:  mov w1, w19          ; the value, 0 on the captured boots
222c:  mov w0, #0x5e        ; CCIC opcode 0x5E
2230:  mov x2, xzr
2234:  mov w3, #0x1
```

and the captures show `ccic_command_polling : OP 0x5E Response OP 0x5E` on the
next line, so the command reaches the chip and is answered.

**Opcode `0x5E` does not exist in the kernel.** `max77705.h`'s opcode enum runs
`OPCODE_SAMSUNG_READ_MESSAGE = 0x5D` straight to `OPCODE_SAMSUNG_SHIPMODE_EN =
0x61`, and no `0x5e` appears anywhere in the Maxim driver or headers. It is a
bootloader-only command that Linux never issues and does not name.

Its caller runs inside CCIC init, gated on a check at `0x2538` immediately after
chip identification, which matches the captured order exactly: `ccic_init`, then
`[CCIC] Max77705 HW i2c init`, then `ccic_is_max77705 : 0x1A`, then
`max77705_ccic_set_sink: set to 0!!`, then `OP 0x5E`, then
`ccic is found!! count : 0`.

Put beside the MUIC result, this looked like the bootloader parking the
connector: sink cleared on the CCIC through a private opcode, `COM_OPEN` written
to the MUIC. **That reading was wrong, and it was wrong for the fourth time in
the same way — a log format I had not enumerated.**

The retained captures carry a third bootloader format beyond `B - <us> - <tag>:`
and `{ <us> }[ XBL ]`: **`{ <us> }[ ABL ]`, 1179 lines** in one capture and 1188
and 786 in the others. Enumerating it produces the rest of the sequence:

```
{ 2746677 }[ ABL ] MuicGetDeviceType: 2
{ 2793983 }[ ABL ]  MuicGetAdcOrientedDevice: 0
{ 2794166 }[ ABL ]  MuicGetVbusStatus: 1
{ 2825215 }[ ABL ]  MuicGetJigType: 0
{ 3256546 }[ ABL ]  SetPath: 1
{ 3266062 }[ ABL ] Samsung USB Driver enumeration start!
```

`SetPath: 1` is `MuicSetPath(1)`, and the jump table decoded above maps path id 1
to **`0x09`, COM_USB**. Ten milliseconds later ABL starts USB enumeration. All
three captures examined show it, at 3.2565, 3.2607 and 3.2606 seconds — this is
the ordinary boot path, not a special case.

So the corrected sequence, all before the kernel exists, is:

| stage | action | CONTROL1 |
|---|---|---|
| XBL `muic_init`, ~1.68 s | `MuicSetPath(0)` | `0x3f` COM_OPEN |
| ABL, ~3.26 s | `SetPath: 1` | `0x09` COM_USB |
| ABL, ~3.27 s | `Samsung USB Driver enumeration start!` | — |

**The bootloader does not park the connector. It opens the mux early and then
routes it to USB before handing off.** `COM_OPEN` is an intermediate state, not
the handoff state, and the CCIC `set_sink(0)` sits in that early phase rather
than describing the final one.

That leaves a real tension rather than a tidy answer. If the bootloader hands
off at COM_USB, a candidate should inherit COM_USB — yet P3.17's diagnostic read
CONTROL1 as `0x3f` before writing. Something between ABL's `SetPath: 1` and a
candidate's own first read either resets CONTROL1 or takes a different path.
Which of those is happening is **not** established here, and it is now the
sharpest open question the bootloader work produced.

One bound from the CCIC half survives unchanged: what `0x5E` means to the
chip is not established, only that Linux never sends it.

## What remains open

Four items this unit closed are not listed here; they have their own sections
and the ledger carries the order they were closed in. What is still open:

- What the bootloader's `OP 0x06` writes to CONTROL1. The outer volumes are now
  unpacked; the MUIC driver sits in an inner volume whose Qualcomm-specific file
  layout is not yet decoded.
- Whether adding the ADSP remoteproc driver to the plan is sufficient, or
  whether the protection domain `msm/adsp/charger_pd` also needs a userspace
  registrar that a candidate cannot provide.
- Why the candidate's own read of `/sys/module/eud/parameters/enable` failed,
  which is what `0x6010` reports and is a candidate-side question. A host D0 read
  of the same file would not answer it.
- Whether the water branch ever fired on the candidates that did load
  `pdic_max77705`. Those runs did not preserve the MUIC sequence, so the test
  cannot be run retrospectively and only a new run can answer it.

## Evidence

Staged surfaces are under `workspace/private/p319_stock_userspace/`, which is
gitignored and holds firmware-derived material that must not be committed.
Mount points are read-only loop mounts under `/mnt/android-lab-logical/`.
