# S22+ FYG8 P3.19 — the stock USB choreography, read from the firmware

Status: `IMPLEMENTED_REVIEW_PENDING` for the whole report and the corpus-semantic
binding V3 successor;
`PASS_GO_P319_CANDIDATE_PDIC_PROBE_BOUNDARY_V2_H0_CAPABILITY` for the exact
candidate-PDIC probe-boundary V2 closure only.

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
other candidates. The S7A2, M7, M11, M12 and M18 plans included
`pdic_max77705`, but their retained evidence did not prove that their module
loops reached it or preserve its `finit_module` result. Treating plan inclusion
as a successful live load was an overstatement; the candidate-probe audit now
corrects it.

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
driver in favour of the diagnostic, as the section above establishes. It would
matter on S7A2, M7, M11, M12 and M18 only if their planned `pdic_max77705` load
actually succeeded, and that premise is not retained. The water branch is the
one mechanism in the graph that could both fire without userspace and leave the
mux pointing somewhere other than the AP. That remains a hypothesis with a
cheap future test rather than a retrospective finding: a run that reached it
would carry `== WATER DETECT ==` or `water hiccup mode, Aux USB path`, while
those five runs preserved neither a module result nor the MUIC sequence.

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
fully decoded. Nothing *on this chain* was encrypted or needed a
Qualcomm-proprietary decoder — which is a statement about the four container
layers actually opened, not about the images left unopened or about the code
inside, which includes vendor Samsung DXE drivers. The two
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
`0x5881` (`0b 0d 0f 11 13 00 00`) with targets `0x22a4 + table_byte * 4`,
where `table_byte` is the byte the path id indexes rather than the path id
itself: path id 1 selects `0x0d` and lands at `0x22d8`, not at `0x22a8`. Decoding it
gives the driver's whole CONTROL1 vocabulary, and every value is named by the
kernel's own bitfields — `NOBCCOMP[7] | RCPS[6] | COMP2SW[5:3] | COMN1SW[2:0]`
with `MAX77705_MUIC_RCPS_VAL = 0`, from `max77705-muic.h:294-301` and `:376-381`:

| path id | value written | kernel constant | check |
|---|---|---|---|
| 0 | `0x3f` | **`COM_OPEN`** | `(7<<3)｜7` |
| 1 | `0x09` | **`COM_USB`** | `(1<<3)｜1` |
| 2 | `0x9b` | **`COM_UART`** | `0x80｜(3<<3)｜3` |
| 3 | `0xa4` | **`COM_USB_CP`** | `0x80｜(4<<3)｜4` |
| 4 | `0xad` | **`COM_UART_CP`** | `0x80｜(5<<3)｜5` |
| 5, 6 | — | read, then set or clear bit 6 | — |

All five arithmetic checks match exactly, so the bootloader and the kernel share
one CONTROL1 encoding. That also settles what the other two callers do: they
pass `#0x2`, which is **`COM_UART`**, consistent with their position inside a
device-type dispatch that queries `MuicGetJigType`.

Three callers exist. Two pass `#0x2`, inside a device-type dispatch. The third,
at `0x21a4`, passes `wzr`:

```
219c:  bl   0x2778          ; a preceding opcode-2 write
21a0:  mov  w0, wzr         ← path id 0
21a4:  bl   0x2268          ← MuicSetPath(0)
```

**So the bootloader's initialisation path writes `0x3f`, COM_OPEN.** The mux is
left open, not in the USB position.

**That closes one half of a question this campaign has carried for months, and
only one half.** An earlier draft of this paragraph said it closed "from two
independent directions", the second being that P3.17's diagnostic read CONTROL1
as `0x3f` before writing anything, and concluded that a candidate inherits
**COM_OPEN**. That second direction was withdrawn earlier in this same report
(see the paragraph beginning "The candidate half was first written as"), and the
reassertion here was a stale survival of the pre-withdrawal text. **It is
withdrawn again, and this time the reason is mechanical rather than
evidentiary.**

The sixth review caught the contradiction; the opcode census then supplied the
reason it can never be repaired from these captures. Across all 103 ABL captures
the MUIC opcode order inside `muic_init` is `0x01` → `0x06` → `0x05`, in that
order, **268 times out of 268, with no exception**. `0x01` is `OPCODE_BCCTRL1_R`;
the first `CONTROL1` access of every boot is `0x06`, a **write**. The bootloader
therefore never reads `CONTROL1` before overwriting it, so **no retained log on
this host can show what the mux held at the moment the boot began** — not for a
stock boot and not for a candidate. What a candidate inherits is not merely
unproven here; it is outside what this evidence class can express, and only a
fresh boot carrying an accepted observer that reads `CONTROL1` before anything
writes it would establish it.

What survives is the bootloader half, and it survives intact: the code writes
`0x3f`, and the captures show it executing.

### The captured boots executed that path, opcode for opcode

The scope was first stated as a limit — three callers, only one passing 0, and
no proof of which ran. Disassembling the enclosing function removes the limit.
The caller at `0x21a4` sits inside `muic_init`, identified by the string at
`0x5abf`, `"muic_init: Error locating the CCIC protocol"`, and the function
reads:

```
2168:  mov w0, #0x1 ; 216c: bl 0x27cc ; opcode 0x01 read
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
command the kernel does not name.

**An earlier version of this sentence said Linux never issues it. That is
withdrawn as a capability claim.** The shipped tree carries a generic opcode
writer: `max77705_debug.c` defines `mxim_debug_opcode_store`, and its
`MXIM_DEBUG_OPCODE_WRITE` ioctl copies a user buffer and sends
`opcode_wdata[0]` as the opcode through `mxim_debug_i2c_write`, with the
character device registered by `mxim_debug_init`. Any opcode, `0x5E` included,
can therefore be issued from Linux through that path. The defensible statement
is the narrower one: **no Samsung enum entry, constant, or named helper for
`0x5E` exists**, and no normal boot path reaches it. That interface is also
F1-class for this campaign and no write through it has been made.

Its caller runs inside CCIC init, gated on a check at `0x2538` immediately after
chip identification, which matches the captured order exactly: `ccic_init`, then
`[CCIC] Max77705 HW i2c init`, then `ccic_is_max77705 : 0x1A`, then
`max77705_ccic_set_sink: set to 0!!`, then `OP 0x5E`, then
`ccic is found!! count : 0`.

Put beside the MUIC result, this looked like the bootloader parking the
connector: sink cleared on the CCIC, `COM_OPEN` written to the MUIC. Enumerating
a third bootloader log format then looked like it reversed that. **Reading the
third format properly resolves both, and the answer is the one the campaign has
been missing.**

### The third format, and whose lines they are

Beyond `B - <us> - <tag>:` and `{ <us> }[ XBL ]` the captures carry
**`{ <us> }[ ABL ]`** — 1179, 1188 and 786 lines in the three examined. It holds
the rest of the connector sequence:

```
{ 3256058 }[ ABL ] init cc mode flag 0x0
{ 3256058 }[ ABL ] Launching odin -927639495
{ 3260724 }[ ABL ]  SetPath: 1
{ 3260724 }[ ABL ] SetDdiBootMode: Saving bootloader mode: [1] in DDI.
{ 3261975 }[ ABL ] LaunchAppFromGuidedFv odin, (Success)
{ 3270118 }[ ABL ] Samsung USB Driver enumeration start!
{ 3281373 }[ ABL ] Odin: CmdsInit start
{ 3351157 }[ ABL ] [EnumeratePartitions] lun: 0
```

`SetPath: 1` is `MuicSetPath(1)`, which the decoded jump table maps to **`0x09`,
COM_USB**. **This report first attributed the line to Odin; that attribution is
superseded below and is wrong.** Disassembling `LinuxLoader.efi` shows the
`SetPath` wrapper and all of its callers live there, so the line is issued by
LinuxLoader's download-mode branch *before* Odin is launched. What survives from
the original reading is only that it is emitted after `Launching odin` is
logged, which is what made Odin the obvious but incorrect owner. All three captures show `Launching odin` once,
`SetPath: 1`, and `Saving bootloader mode: [1]`, so the bootloader tail in every
retained capture is a **download-mode session**, not a normal boot. That is what
this campaign's own flow produces: capture, then reboot to Download to flash.

### Which resolves the tension, and answers an older question

The two stages do different things and always have:

| path | stage | CONTROL1 |
|---|---|---|
| both | XBL `muic_init` | `MuicSetPath(0)` → `0x3f` COM_OPEN |
| **Download** | ABL → Odin | `MuicSetPath(1)` → `0x09` **COM_USB**, then enumeration |
| **Normal** | ABL → LinuxLoader | no `SetPath` evidenced |

An earlier version of this paragraph continued: "So a candidate reads `0x3f`
because its boot is a normal boot … P3.17's pre-read of `0x3f` and the
bootloader's own code agree after all." **That is withdrawn**, for the third and
last time in this report. It is the same claim the candidate-half paragraph
above already withdrew, restated as if the withdrawal had not happened, and the
sixth review found one of the three survivals while a sweep of this report for
the same shape found the other two. What the captures license is a statement
about *stock normal boots*: in all 41 of them XBL writes `COM_OPEN` and nothing
in the corpus writes `CONTROL1` again before the kernel starts.

What it does bear on is a question this campaign has carried from the beginning
— **why Download mode enumerates to a host while a candidate never has.** On the
stock side that now has an answer: download mode does not merely happen to work,
Odin explicitly routes the analog path to USB before bringing up its USB stack,
and the normal boot path never does. Carrying that across to the candidate is a
separate step this report does not take.

### Checked against every capture, not three

The paragraph above was first written as a limit: three captures, all Odin, so
no normal-boot ABL stage to compare against. That limit was an artifact of the
sample, and the sample was three because three were to hand — the same shape as
five other errors in this unit. Enumerating **every** retained capture with an
ABL stage settles it:

**The numbers below replace an earlier `80 / 77 / 3` table.** That table was
challenged by an independent review for having no bounded population — no
inclusion criterion, no paths, no hashes — and the challenge was correct. It was
also, separately, wrong in both directions: it undercounted the corpus and it
counted files rather than captures.

The population is now closed by
`scripts/analysis/s22plus_fyg8_p319_abl_log_census.py`, which states one mechanical
criterion — every regular file under `workspace/private` of exactly 2097136
bytes, the `last_kmsg` region size this campaign measured — and selects nothing
by name or by run. It finds **306 matching files**, and then does the step the
earlier census omitted: it deduplicates by SHA-256 before counting. **185 of
those files are byte-identical copies of another**, because the retained tree
copies the same `baseline-observer.bin` into many run directories. Counting
files would have inflated the corpus by more than a factor of two.

**Those two numbers drift and the conclusions do not.** They were 293 and 172
when this section was written. Every unit that materializes a capture copy into
its own run directory adds files that satisfy the criterion — the witness-parser
predecessor added thirteen — so the raw file count only grows. Rebuilding after
that growth leaves `distinct_captures` at **121**, ABL stages at **103**, boot
segments at **268**, `SetPath` occurrences at **110** and the opcode census at
`0x01` 268 / `0x05` 378 / `0x06` 378, all unchanged. The drifting pair is the
population size; the invariant set is everything the report reasons from. Read
the two file counts as a dated snapshot and the rest as results.

| ABL path | distinct files | boot segments | `SetPath` |
|---|---|---|---|
| → Odin (download mode) | **62** | **227** | `SetPath: 1` in **62 of 62** files, **110** occurrences |
| → normal handoff to Linux | **41** | **41** | **none at all, in all 41** |
| any | 103 | 268 | `SetPath: 0` never appears; the only value ever observed is `1` |

Eighteen further distinct files carry no ABL stage and are excluded from the
table but not from the manifest.

**The "boot segments" column was added after the sixth review**, which pointed
out that SHA-256 identity is file identity and not boot identity. A retained
buffer can hold several boot rings, and the download files hold up to seven. The
per-file counts in the middle column are still correct as file counts; they were
wrong wherever the earlier text called them boots. The section
"The register accounting closes, and it closes on a bit the census hid" derives
the segment count and states what it changes.

All **41** normal-handoff captures carry `Booting Into Mission Mode`. That
matters because the earlier reading rested on three captures, two of them
`post_recovery`, where the review fairly objected that a recovery flush is not
an ordinary handoff. Mission Mode is the ordinary handoff, and it is now the
whole of the normal population rather than an inference from one example.

So the claim strengthens from *not evidenced* to **evidenced absent**, on a
sample thirteen times larger than the one that first supported it: across 41
distinct normal boots the ABL stage issues no `SetPath`, across 62 distinct
download boots it always issues `SetPath: 1`, and across all 103 the value `0`
never occurs. `LinuxLoader.efi` still contains
`Error MuicSetPath()` and so retains the capability; what is now established is
that it did not exercise it on any captured normal boot.

Disassembling `LinuxLoader.efi` refines the attribution and **corrects a claim
this report briefly carried**. That claim was that the string ` SetPath: %d` is
linked in but never referenced, so LinuxLoader contains dead library code. It
was produced by searching for the immediate `#0x195` after converting the
string's decimal offset 987509 to hex **incorrectly** — 987509 is `0xf1175`, not
`0xf1195`. Searching the right immediate finds **three** call sites, and the one
at `0x402d0` is a textbook wrapper:

```
40208:  … locate the MUIC protocol via the protocol table
4020c:  mov  w20, w0                  ; the wrapper's own path argument
40258:  adrp x1, 0xf0000 + 0xde4      ; "Error locating the MUIC protocol"
40270:  mov  w0, w20                  ; pass the argument through
402a8:  adrp x1, 0xf1000 + 0x160      ; "Error MuicSetPath()"   — failure branch
402d0:  adrp x1, 0xf1000 + 0x175      ; " SetPath: %d"          — success branch
402d4:  mov  w2, w20                  ; log the value
```

So `LinuxLoader` is the ABL core — it also carries `Launching odin` and
`SetDdiBootMode`, which `Odin.efi` does not — and it owns the `SetPath` wrapper.
The `SetPath: 1` line therefore belongs to **LinuxLoader's download-mode
branch**, issued before Odin is launched, rather than to Odin itself as this
report first said.

What is withdrawn is only the code-side "dead library" corroboration, which was
an artifact of a hex conversion error — the sixth instance in this unit of
concluding absence from an incomplete search. Enumerating the wrapper's callers
properly replaces it with a real one. The wrapper begins at `0x401f8` and has
**three** callers, each with its argument in view. This is a scan for direct
`BL` encodings only: an indirect call through a function pointer or a vtable
would not appear in it, and this unit has since found that the bootloader's own
MUIC and CCIC access is vtable-dispatched, so the possibility is a live one
rather than a formality. Read the count as *three direct callers*, not as a
proof that no other call site exists:

| site | guard | argument | effect |
|---|---|---|---|
| `0x1464` | immediately after logging `Launching odin` | `#0x1` | `COM_USB` |
| `0x45a24` | `and w9, w11, #~1` then `cmp w9, #0x6` | `#0x1` | `COM_USB` |
| `0x45a98` | `ldr w8, [x8, #1888]` then `cmp w8, #0x1` | `#0x6` | clears BCCTRL1 bit 6 |

The third is not a path switch: path id 6 lands in the `Muic` driver's
read-modify branch at `0x2314`, which does `and w8, w19, #0xffffffbf`.

**This row previously said it clears `RCPS` and leaves `COMN1SW`/`COMP2SW`
untouched. That was wrong and is withdrawn.** Those are `CONTROL1` fields, and
this branch never touches `CONTROL1`. Reading the surrounding instructions
rather than the mask alone shows the register: the value is fetched at `0x22a8`
with `mov w0,#0x1 ; bl 0x27cc` and stored back at `0x2320` with `mov w0,#0x2` —
`OPCODE_BCCTRL1_R` and `OPCODE_BCCTRL1_W`. The `CONTROL1` pair `0x05`/`0x06` is
used only by the constant-writing branches. So path id 6 is a read-modify-write
of **`BCCTRL1` bit 6**, and `CONTROL1` is left exactly as it was.

**The bit has a name, and an earlier version of this paragraph wrongly said it
had none.** That version read: "no `BCCTRL1` bitfield appears in the header or
the Maxim driver, so nothing on this host licenses a name for it." That is
**withdrawn**. It was an absence claim made after searching one header
(`max77705.h`, the PDIC header) and not the MUIC header. The lab's A90 source
tree, present on this host, defines the field set:

```
include/linux/muic/max77705-muic.h:233   /* MAX77705 BC_CTRL1 */
:234  BC_CTRL1_DCDCpl_SHIFT      7
:235  BC_CTRL1_UIDEN_SHIFT       6
:236  BC_CTRL1_NoAutoIBUS_SHIFT  5
:237  BC_CTRL1_3ADCPDet_SHIFT    4
:238  BC_CTRL1_CHGDetMan_SHIFT   1
:239  BC_CTRL1_CHGDetEn_SHIFT    0
```

The MAX77705 is the same part on both units, so the field names transfer even
though the tree is the A90's. The bit that path id 5 sets with
`orr w8, w19, #0x40` and path id 6 clears with `and w8, w19, #0xffffffbf` is
therefore **`BC_CTRL1_UIDEN`**, bit 6 — the MUIC's UID (accessory-ID) detection
enable, not a switch field at all.

Withdrawing `RCPS` was still correct, and for the reason given: `RCPS` is a
`CONTROL1` field and this branch never touches `CONTROL1`. The error was
carrying the name across on a matching bit index. The correction is not that the
bit is unnameable but that it had to be named from the register's own header.

So **no call site in LinuxLoader passes 0**; it never writes `COM_OPEN`, which
leaves XBL's `muic_init` as the only writer of that value. Both real path
switches pass `1`, and both sit behind conditions — one explicitly the
download-mode branch, the other a mode test.

That matches the log evidence exactly rather than merely being consistent with
it: across 103 distinct ABL stages, all 62 download-mode boots log `SetPath: 1`
and all 41 normal-boot stages log none, which is what a code path taken only
under those two guards produces.

One bound from the CCIC half survives, now with the search behind it. Opcode
`0x5E` is not named anywhere reachable: the S22+ kernel's enum skips `0x5D` to
`0x61`, and the same gap is present in the Note 10 and Tab S6 Samsung trees,
so it is absent from Samsung's Linux drivers generally rather than trimmed for
this device. The public sibling chip does not help either — the MAX77958 opcode
guide uses a different map, with SNK PDO commands at `0x3E` and `0x3F`, so its
numbering cannot be carried across. `0x5E` is therefore a bootloader-only
opcode with no public documentation, and its effect is inferred from the calling
function's name, `max77705_ccic_set_sink`, and its argument of 0 — not from any
specification.

## The bootloader enumerates without any of the kernel's role machinery

The UEFI volume that holds `Muic` and `Ccic` holds 84 files in all, and among
them is a complete USB stack: `UsbfnDwc3Dxe`, `UsbInitDxe`, `UsbConfigDxe`,
`UsbPwrCtrlDxe`, `UsbDeviceDxe`, `UsbBusDxe`, `UsbMsdDxe`, `UsbMassStorageDxe`
and `UsbKbDxe`. `UsbfnDwc3Dxe` at 102400 bytes is a full DWC3 **function**
driver — TRB rings, physical endpoints, `StartXfer`/`EndXfer`/`UpdateXfer`, a
control state machine handling reset and disconnect, and charger-port detection
through `PmicSmbchgProtocol->ChargerPort()`.

The structurally important part is how the mode is chosen. `UsbConfigDxe`
exposes a core interface whose members its asserts name outright:

```
UsbCoreIfc->InitCommon      UsbCoreIfc->Reset
UsbCoreIfc->InitDevice      UsbCoreIfc->EnableVbus
UsbCoreIfc->InitHost        UsbCoreIfc->GetVbusStatus
UsbCoreIfc->PollSSPhyTraining
UsbCoreIfc->AdvanceSSCmplPattern
```

with errors including `Cannot Get Connection Mode for Core %d` and
`Cannot simulate host and device at the same time`. **The bootloader selects
peripheral mode by calling `InitDevice` on the core directly.** There is no role
switch, no UCSI, no extcon and no PDIC anywhere in that path.

**The host end of that sentence needs a separate warrant, and a review was right
to ask for one.** An earlier version ended "— and Odin enumerates to a host on
this exact hardware every time the campaign flashes", offered as if the captures
showed it. They do not. Every enumeration string in these logs, including
`Samsung USB Driver enumeration start!`, is written by the bootloader about its
own progress; no capture carries a host endpoint, a udev event, a descriptor, or
an Odin receipt, and **no per-capture receipt binds any of the 62 download
hashes to a particular host session**. What does warrant the claim is
operational rather than log-borne: this campaign's own Odin transfers to this
unit have completed, and a completed transfer requires the host to have
enumerated the device. That is recorded in the campaign ledger, not in these
captures, and it is a statement about the campaign's flashes in aggregate rather
than about any one of the 62.

That changes the weight of this unit's UCSI finding rather than contradicting it.
UCSI over GLINK is how the **stock kernel** chooses to initiate the role; it is
**not a precondition for device-mode enumeration on this SoC**, and the
bootloader is the existence proof. A candidate that writes `peripheral` to
`a600000.ssusb/mode` is doing the kernel-side equivalent of `InitDevice` — it
sets `vbus_active` and drives the DRD state machine directly, bypassing UCSI
exactly as the bootloader bypasses it.

So "the candidate cannot reach UCSI" is true and much less consequential than it
first appeared: **the candidate does not need to reach it.** What the bootloader
does that a candidate on a normal boot does not is narrower and already
identified — Odin routes the analog path with `MuicSetPath(1)` before bringing
the controller up, and a normal boot leaves `COM_OPEN`.

That was first read from strings and the interface's own assert messages, which
an independent review correctly called an inference from names. It is now read
from the registers.

`UsbfnDwc3Dxe.efi` is AArch64 PE32+ with `.text` at RVA `0x1000`. Its
`MmioRead32` and `MmioWrite32` helpers are identifiable at `0xc018` and `0xc050`
— both open with `tst x0, #0x3` and branch to an assert on a misaligned address
— and the DWC3 register offsets appear as immediates throughout: `0xc100`,
`0xc110`, `0xc200`, `0xc2c0`, `0xc700`, `0xc704`, `0xc708`.

The role is decided at `0x3ba0`:

```
bl 0xc018                ; MmioRead32(base + 0xC110)   GCTL
and w8, w0, #0xffffcfff  ; clear PRTCAPDIR, bits [13:12]
orr w1, w8, #0x2000      ; PRTCAPDIR = 0b10 = device
bl 0xc050                ; MmioWrite32(base + 0xC110)
```

**Two claims made here were too strong, and the sixth review was right to say
so.** They are restated below in a form the disassembly actually supports — and
completing the search makes the conclusion stronger, not weaker.

*The write is one of three, not one.* An earlier version showed the four
instructions above as the GCTL access. In fact `0x3b80` loads the GCTL address
once and performs **three** consecutive read-modify-writes through it:

```
3b90:  and   w1, w0, #0xfffeffff            ; clear bit 16, GCTL_U2RSTECN
3ba4:  and   w8, w0, #0xffffcfff            ; clear PRTCAPDIR [13:12]
3bac:  orr   w1, w8, #0x2000                ;   → PRTCAPDIR = 0b10 = device
3bbc:  mov   w1, #0x100000                  ; PWRDNSCALE field
3bc0:  bfxil w1, w0, #0, #19                ;   preserving bits [18:0] verbatim
```

The third matters for the conclusion: `bfxil w1, w0, #0, #19` copies the live
bits `[18:0]` — which **contain PRTCAPDIR at [13:12]** — into the new value, so
the last write of the sequence *preserves* the device selection rather than
disturbing it. The earlier text described the middle write alone and said "the
instruction immediately before clears GCTL bit 16", which was true but presented
a three-write sequence as one.

*The absence claim rested on an immediate-operand search.* It read: "the image
contains no `orr` of `#0x1000` or `#0x3000` at all". That search cannot see a
register-operand `orr`, a `bfi`/`bfxil`, or a value loaded from a table, so on
its own it does not license "no site anywhere selects host or OTG". **That
wording is withdrawn and replaced by an enumeration**, which is the check that
should have been run: `mov wN, #0xc110` occurs at exactly **two** sites in
`UsbfnDwc3Dxe.efi`, `0x3b80` above and `0x5184`. The second is

```
5184:  mov  w10, #0xc110
5194:  bl   0xc018                          ; MmioRead32(base + 0xC110)
5198:  and  w1, w0, #0xffffff3f             ; clear bits [7:6], GCTL_RAMCLKSEL
51a0:  bl   0xc050                          ; MmioWrite32
```

Its mask `0xffffff3f` clears only bits 7 and 6 and **preserves [13:12]**. So
every writer of GCTL in this image is now accounted for, and exactly one of them
touches `PRTCAPDIR`: the one that selects device. That is a closed enumeration
over the register rather than an absence of one instruction encoding.

*The branch claim was false as written.* It said "the only branches before it
are `tbnz w0, #31` tests". The function entered at `0x37b4` contains earlier
`b.ne`, `cbz`, and loop branches, including at `0x3a20`, `0x3a6c`, `0x3ac8`, and
`0x3b50`. **Withdrawn.** What survives is the narrower and still useful fact
that none of them writes `GCTL`, which the two-site enumeration above
establishes directly; the reachability of `0x3b80` from the driver entry point
(`0x114c` through `0x1454`) and from `UsbfnExitBootService` at `0x1be0` is
unaffected, but it is reachability, not a proof of unconditional execution.

So the bootloader does not negotiate a role, read an ID pin, or consult a
connector state to become a peripheral. It writes `PRTCAPDIR = device` into
`GCTL` and proceeds. What remains unproven is the narrower naming question:
this was traced from the register write upward to the driver entry, not
downward from a slot literally named `InitDevice`, so the register evidence is
attached to the Usbfn DWC3 driver's init path rather than to that name.

## Three bootloader modes, and only one leaves the mux open

`XblRamdump.elf` carried `%s : muic_set_path to USB` from the start, and this
unit twice noted that the string never appears in any capture without
establishing what would make it run. Disassembling it settles that and completes
the picture.

The image has no section headers, so its first LOAD segment was extracted at
file offset `0x1000` for `0xbf000` bytes and disassembled as raw AArch64 with
`--adjust-vma=0xa7d00000`. The string block maps exactly: file offset 1073840 is
`0x1062b0`, which lies in the second LOAD segment and resolves to VA
`0xa7e262b0`, page `0xa7e26000` plus `0x2b0`. Reading the code at `0xa7d14ac4`:

```
adrp x19, 0xa7e26000 ; add x19, x19, #0x281   ; x19 = "init_device_for_rdx"
adrp x1,  … + #0x271 ; bl log                 ; "%s : muic_init"
bl 0xa7d308e0                                  ; muic_init()
adrp x1,  … + #0x295 ; bl log                 ; "%s : muic_init_hv_control"
bl 0xa7d30998                                  ; muic_init_hv_control()
adrp x1,  … + #0x2b0 ; bl log                 ; "%s : muic_set_path to USB"
mov  w0, #0x1                                  ; path id 1
bl 0xa7d30974                                  ; muic_set_path(1) → COM_USB
adrp x1,  … + #0x2cb ; bl log                 ; "%s : ccic_init"
```

`x19` is the `%s` passed to every log call, so the enclosing function names
itself: **`init_device_for_rdx`** — device initialisation for RAM dump. It
routes the mux to USB, which is what a ramdump upload needs.

That gives all three bootloader modes, each established from its own code:

| mode | who routes the mux | CONTROL1 left |
|---|---|---|
| **normal boot** | nobody after XBL's `muic_init` | **`0x3f` COM_OPEN** |
| **download (Odin)** | `LinuxLoader` download branch, `MuicSetPath(1)` | `0x09` COM_USB |
| **ramdump (RDX)** | `XblRamdump`'s `init_device_for_rdx`, `muic_set_path(1)` | `0x09` COM_USB |

**Every bootloader mode that needs USB routes the mux explicitly, and the normal
boot is the only one that does not.** Nothing here is incidental: the two modes
that talk to a host both contain an unconditional, logged call, and the mode that
hands off to Linux contains none on any captured path.

For a candidate that is the whole instruction. It boots through the one mode
that leaves `COM_OPEN`, so it must route the analog path itself.

Two bounds on that sentence, both from later sections of this report. First,
everything above is **static**: the download and RDX sequences are code that
exists and is unconditional where it sits, not code observed executing on a
particular boot. Second, both sequences run through thunks that no-op when the
chip never probed, and the log line is emitted *before* the thunk, so even a
capture containing the string does not establish that the write landed. What is
established is the shape of the code, and it is one-sided enough to act on: no
normal-boot path in any image read here writes anything but `COM_OPEN`. The
instruction to a candidate follows from that, not from a proven execution —
and the stock kernel's own `pdic_max77705` reaching `com_to_usb_ap` at 4.19 s is
the independent evidence that something must do this after the bootloader.

## The RDX bring-up is five calls, and only half of them can fail loudly

`init_device_for_rdx` was read for its `muic_set_path` call. Reading the whole
function instead of the one call shows it is a straight line with no branch in
it, and that the mux switch is one of five steps:

```
"pdic init.. "
"%s : muic_init"             bl 0xa7d308e0
"%s : muic_init_hv_control"  bl 0xa7d30998
"%s : muic_set_path to USB"  mov w0,#1 ; bl 0xa7d30974
"%s : ccic_init"             bl 0xa7d96edc
"%s : ccic_set_sink"         mov w0,#1 ; bl 0xa7d96f90  → w20
"Done for RDX"
"%s : ccic_set_sink finish: %d"   (w3 = w20)
```

Two drivers, not one: the MUIC entries live around `0xa7d30…` and the CCIC
entries around `0xa7d96…`. The first log line is `pdic init..`, which is the
Samsung rename of CCIC, so the CCIC half of this sequence is the same block the
kernel drives as `pdic_max77705`.

### They are protocol thunks, so this is a calling convention, not register writes

None of the five is an implementation. Each is a UEFI protocol thunk over a
ready flag and an interface pointer:

| | ready flag | interface pointer | vtable slots used |
|---|---|---|---|
| MUIC | `0xa7f34000` + 476 | `0xa7fd9000` + 3488 | `+0` probe, `+8` init, `+16` set_path, `+24` init_hv_control |
| CCIC | `0xa7f7e000` + 1976 | `0xa7fad000` + 1896 | `+0` poll, `+24` set_sink |

`muic_init` publishes the interface, calls `[iface+0]`, and treats the probe as
successful only when the returned byte is `0x1a` or `0x10`
(`cmp w8,#0x1a ; ccmp w8,#0x10,#0x4,ne ; b.eq`). Otherwise it retries, capped at
ten attempts (`cmp w8,#0xa`). Only on success does it store `1` into the ready
flag and tail-call `[iface+8]`. `ccic_init` has the same shape with its own
budget of ten and a readiness test of "the returned byte is not `0xff`".

The function called between retries, `0xa7d94c0c`, contains exactly one
instruction — `ret` — and sits in a run of stubs (`mov w0,wzr ; ret`). Whatever
it is named, in this image the retry loop waits for nothing.

### The asymmetry, and the trap in it

The two halves report failure completely differently:

- `muic_set_path` and `muic_init_hv_control` check the ready flag and, when it is
  clear, **execute a bare `ret`**. They return nothing. A MUIC that never probed
  makes both calls silent no-ops.
- `ccic_set_sink` checks its flag and returns **`-2`** when clear, then loads
  `[iface+24]` and returns **`-3`** if that slot is null. The caller captures
  that value in `w20` and prints it as `ccic_set_sink finish: %d`.

So `ccic_set_sink finish: -2` in a capture would be diagnostic. Nothing
equivalent exists on the MUIC side.

**And the log line is emitted before the call, unconditionally.** `%s :
muic_set_path to USB` is printed by the caller and then the thunk decides whether
to do anything. The string's presence in a log is therefore evidence that the
sequence was *entered*, not that the mux was *switched*. This unit has already
mistaken a narrow sample for a whole medium six times; recording the distinction
here is what keeps that string from being read later as proof of a routed mux.

### What this does not give

The register writes are still one level down. The thunks name vtable slots; the
implementations behind them are in `Muic.efi` and `Ccic.efi`. `Muic.efi`'s
`+16` is the already-disassembled `MuicSetPath` with its `0x3f/0x09/0x9b/0xa4/
0xad` jump table, so that slot is resolved. `+24` (`init_hv_control`) is not,
and `Ccic.efi` has not been opened at all. Until those are read, what
`ccic_set_sink(1)` actually programs is unknown.

## Resolving the vtable slots to register writes

The thunks named slots. This resolves them, and the resolution has to start by
correcting an assumption: **on this path**, `XblRamdump` does not call the
`Muic`/`Ccic` DXE drivers. An earlier version dropped the qualifier and said it
flatly; what the disassembly shows is one path using its own callbacks, which
does not establish that no path in the image ever reaches the DXE drivers.
`muic_init` publishes an interface it carries itself, at
`0xa7e9cf60`, and `ccic_init` publishes one at `0xa7ea3fe0`. Both are four
pointers followed by a null, and every pointer lands back inside `XblRamdump`'s
own code segment:

| slot | MUIC `0xa7e9cf60` | CCIC `0xa7ea3fe0` |
|---|---|---|
| `+0` | `0xa7d309bc` | `0xa7d96fc4` |
| `+8` | `0xa7d30a00` | `0xa7d97014` |
| `+16` | `0xa7d30a8c` | `0xa7d97044` |
| `+24` | `0xa7d30b58` | `0xa7d970b8` |

A ramdump image cannot depend on DXE drivers that may not be loaded, so it ships
its own copy. That makes the DXE drivers an *independent* witness rather than
the implementation: `Muic.efi`'s `.data` holds a vtable at `0x7110` of
`{0x20c8, 0x210c, 0x2268, 0x2350}` and `Ccic.efi`'s at `0x70d0` of
`{0x2070, 0x20c0, 0x2144, 0x21f8}`. Slot `+16` of the first is `0x2268`, the
`MuicSetPath` already disassembled here, and slot `+24` of the second is
`0x21f8`, the `max77705_ccic_set_sink` already disassembled here. Both were
originally found by chasing log strings; finding them again at the slot offsets
the thunks use, in a separately built image, is what ties them to the call path.

### `init_hv_control` is a single opcode

`Muic.efi`'s `+24` at `0x2350` is four instructions of work:

```
235c:  mov w0, #0x12          ; OPCODE_HVCTRL_W
2360:  sub x1, x29, #0x4
2364:  sturb wzr, [x29, #-4]  ; payload = 0x00
2368:  bl 0x2778              ; the opcode-write helper
```

`max77705.h` names it: `OPCODE_HVCTRL_R = 0x11`, `OPCODE_HVCTRL_W` next. The
step between `muic_init` and `muic_set_path` clears high-voltage control.

### The path-id map is wider than five constants

The executed `set_path` at `0xa7d30a8c` indexes a byte table at `0xa7e3fbbb`
holding `0b 0d 0f 11 13 00 00`, which resolves to:

| id | effect | opcodes |
|---|---|---|
| 0 | `CONTROL1` = `0x3f` `COM_OPEN` | `0x06` write, `0x05` read-back |
| 1 | `CONTROL1` = `0x09` `COM_USB` | `0x06`, `0x05` |
| 2 | `CONTROL1` = `0x9b` `COM_UART` | `0x06`, `0x05` |
| 3 | `CONTROL1` = `0xa4` `COM_USB_CP` | `0x06`, `0x05` |
| 4 | `CONTROL1` = `0xad` `COM_UART_CP` | `0x06`, `0x05` |
| 5 | `BCCTRL1` bit 6 **set** | `0x01` read, `0x02` write |
| 6 | `BCCTRL1` bit 6 **clear** | `0x01`, `0x02` |
| >6 | `CONTROL1` = `0x00` | `0x06`, `0x05` |

Ids 5 and 6 reach `CONTROL1` not at all, which is what makes the withdrawn
`RCPS` reading above a mistake rather than a wording problem.

### Where the opcodes come from

Laying the five calls beside `max77705.h` splits them cleanly:

- `muic_set_path` uses `OPCODE_CTRL1_W` `0x06` and `OPCODE_CTRL1_R` `0x05`, or
  `OPCODE_BCCTRL1_R/W` `0x01`/`0x02`. All four are kernel-named.
- `muic_init_hv_control` uses `OPCODE_HVCTRL_W` `0x12`. Kernel-named.
- `ccic_set_sink` uses `0x5E`, which the kernel enum skips entirely, jumping
  `OPCODE_SAMSUNG_READ_MESSAGE = 0x5D` to `OPCODE_SAMSUNG_SHIPMODE_EN = 0x61`.

So the MUIC half of the bring-up is expressible in commands Linux already has
names and helpers for, and the CCIC half is not. A candidate that wants to
reproduce the sequence can reach the mux through the kernel's own vocabulary;
the sink step has no such route, and whatever the stock kernel does to reach the
same state, it is not this command.

## The download branch does not repeat the RDX sequence; it adds one call

Reading `init_device_for_rdx` produced a five-call bring-up and this unit then
asked whether LinuxLoader's download branch runs the same five. The closed
capture manifest answers it empirically rather than statically, by counting
which MUIC and CCIC lines appear in each class of boot. The answer is that the
question was framed wrongly.

Every bring-up line appears in **all 103** ABL-bearing captures — 62 download and
41 normal alike — and every one of them is tagged `[ XBL ]`:

```
[ XBL ] muic_init            [ XBL ] ccic_init
[ XBL ] [MUIC] Max77705 HW i2c init   [ XBL ] [CCIC] Max77705 HW i2c init
[ XBL ] [MUIC] BC_CTRL1_READ : 0x..   [ XBL ] ccic_is_max77705 : 0x..
[ XBL ] muic_command_polling: OP 0x.. [ XBL ] ccic_command_polling : OP 0x..
[ XBL ] max77705_ccic_set_sink: set to 0!!
```

`ccic_set_sink` is logged with the value **0 in all 103 captures** and with `1`
in none of them. No `muic_` or `ccic_` bring-up line is tagged `[ ABL ]` on any
capture.

The ABL stage does touch the chip on both classes, but only to read it:
`MuicGetDeviceType`, `MuicGetJigType`, `MuicGetVbusStatus`,
`MuicGetAdcOrientedDevice` and `CcicReadAdc` each appear in 62 of 62 download
captures and 41 of 41 normal ones. **Across the entire MUIC and CCIC surface,
exactly one line separates a download boot from a normal boot:**

| | download | normal |
|---|---|---|
| XBL bring-up, including `ccic_set_sink: set to 0` | 62 / 62 | 41 / 41 |
| ABL read-only queries | 62 / 62 | 41 / 41 |
| `[ ABL ] SetPath` | **62 / 62** | **0 / 41** |

### What this corrects

The five-call sequence is real, but it is **RDX's**, not the general bring-up.
XBL performs four of those five on every boot that has ever been captured here.
What `init_device_for_rdx` adds is `muic_set_path(1)` *and* `ccic_set_sink(1)`;
what the download branch adds is `muic_set_path(1)` **alone**.

That difference resolves the campaign's open question about opcode `0x5E` in a
direction this unit did not expect. Download mode is the one path known to
enumerate to a host, and it does so with the sink value left at `0` — the value
XBL wrote. **Setting the sink is therefore not a precondition for enumeration**,
and `0x5E`'s unknown payload semantics sit off the critical path rather than on
it. The earlier framing, which called `0x5E` the one remaining gap in the
sequence a candidate must reproduce, is withdrawn.

It also narrows the earlier reading of the bootloader "parking the connector".
The sink clear is not a decision the bootloader takes about a particular boot;
it is unconditional, and it happens identically on the boots that go on to
enumerate.

**On the bootloader side, the difference between a boot that enumerates and one
that does not reduces to one action: write `COM_USB` to `CONTROL1`.** Everything
else in the five-call sequence has already been done by XBL before Linux starts,
on every boot, in both classes.

**That is a statement about the bootloader, and it must not be read as an
instruction that would make a candidate work.** Two facts on this host bound it,
and both point the same way.

First, nothing here establishes the candidate side. The opcode accounting in
this report shows that the bootloader never reads `CONTROL1` before writing it,
so no capture in this corpus — stock or candidate — can show what a candidate starts
from or what it would need to change.

Second, the campaign does not have the counter-evidence this report previously
claimed. Five candidate *plans* — `S7A2`, `M7`, `M11`, `M12`, `M18` — included
`pdic_max77705`, the driver that owns this write, and all five failed to expose
the intended endpoint. Their retained evidence did not prove that the module
loop reached that entry, that `finit_module` succeeded, or that the platform
child bound. The honest form of the sentence is therefore narrower: this unit
has closed the bootloader half and identified the register action that
distinguishes the two stock classes; it has **not** shown that a candidate ever
reached the stock writer, much less that performing the write is sufficient.

## The register accounting closes, and it closes on a bit the census hid

The sixth review made two objections to the capture census that are correct and
that this section acts on: SHA-256 identity is not boot identity, and
normalising the log lines before comparing them hid a register-value difference.
Following both produced the strongest single result in this unit.

### One file is not one boot

The census called its 121 deduplicated files "distinct boots". **That is
withdrawn.** A file is a retained buffer, and a retained buffer can hold several
boot rings. Counting the bootloader's own per-boot MUIC banner
(`MUIC Device : Max77705! count: 0`) inside each file gives the real population:

| | files | boot segments |
|---|---|---|
| normal handoff | 41 | **41** (1 per file, no exception) |
| download | 62 | **227** (2 in 15 files, 4 in 42, 5 in 3, 7 in 2) |
| **total ABL** | **103** | **268** |

So the corpus is **268 boot segments in 103 files**, not 103 boots. Every number
in this report that was stated per-file is now also available per-segment, and
where the two differ the per-segment number is the one that means anything about
boots. The normal-handoff side is unaffected — 41 files hold exactly 41
segments — which is why the earlier conclusions about normal boots survive the
correction, and the download side is where the count was wrong by a factor
approaching four.

### The hidden bit is `NoAutoIBUS`, and it survives a reboot

Normalising digits collapsed `BC_CTRL1_READ : 0x00C5` and
`BC_CTRL1_READ : 0x00E5` into the same apparent line. They are not the same
line. Across the 268 segments the split is exact:

| | `0x00C5` | `0x00E5` |
|---|---|---|
| normal segments (41) | **41** | 0 |
| download segments (227) | **62** | **165** |

and in every one of the 62 download files the single `0x00C5` is the **first**
segment in file order, with every later segment reading `0x00E5`. There are four
distinct sequences across 62 files and all four have that shape:
`C5,E5` ×15, `C5,E5,E5,E5` ×42, `C5,E5,E5,E5,E5` ×3, `C5,E5,E5,E5,E5,E5,E5` ×2.

`0xC5` is `1100_0101` and `0xE5` is `1110_0101`. The difference is **bit 5**,
which the MUIC header names `BC_CTRL1_NoAutoIBUS`. Both values carry
`BC_CTRL1_UIDEN` (bit 6) set — the same bit the path-id 5 and 6 branches would
have toggled.

The read is `OPCODE_BCCTRL1_R`, and it is the **first** MUIC access of the boot.
So the value is not something the boot produced; it is what the MUIC was already
holding when the boot began. **`NoAutoIBUS` is chip state that survives a
reboot**, set during a download session and still set on the next start, and the
retained log records it because the bootloader happens to read that register
before writing anything.

### No boot in the corpus writes `BCCTRL1` at all

The opcode census over all 103 captures returns exactly three opcodes:

```
OP 0x01  (OPCODE_BCCTRL1_R)   268     one per boot segment
OP 0x06  (OPCODE_CTRL1_W)     378
OP 0x05  (OPCODE_CTRL1_R)     378
OP 0x02  (OPCODE_BCCTRL1_W)     0     in 0 of 103 captures
```

`0x02` never occurs. Path ids 5 and 6 are the only branches that issue it, so
**neither was executed in any of the 268 segments** — and the earlier argument
that pinned the executed path by predicting a missing `0x02` from a bit of the
`0x00C5` value can be discarded in favour of counting the opcode directly. It
also settles the previous section's question about `0xE5`: the boot that reads
it did not write it.

### Every `CONTROL1` access in the corpus is attributed

378 `CONTROL1` write/read-back pairs, 268 boot segments, and `SetPath: 1`
appears **110** times. 268 + 110 = **378**, exactly. Two sites — XBL's
`muic_init` once per segment, and ABL's `SetPath: 1` — account for every logged
`CONTROL1` access in the corpus with **zero residual**. The 110 are all in
download files; normal segments contribute none.

That is the load-bearing chain stated as an accounting identity rather than as
an inference from one disassembled branch: 41 normal boot segments perform 41
`CONTROL1` writes, all of them `muic_init`'s, and `muic_init` writes `0x3f`,
`COM_OPEN`. **No normal boot in the corpus writes `COM_USB`.**

The limit of the method is worth stating precisely, because the review pressed
on it correctly: this closes the accounting over *logged* accesses. Every
`muic_command_polling` line is attributed and none is left over, but an I²C write
issued without going through that helper would produce no line to count and is
not excluded by it.

### Why the inheritance question cannot be answered from any of these captures

The ordering inside `muic_init` is `0x01` → `0x06` → `0x05`, **268 times out of
268**. The first `CONTROL1` access of every boot is a write. The bootloader
therefore never reads `CONTROL1` before overwriting it, and **no retained log on
this host can show what the mux held at the moment a boot began.** That is a
property of the code, not of this sample, so collecting more captures of this
kind cannot answer it. Only a boot carrying an accepted observer that reads
`CONTROL1` before anything writes it would.

### A kernel-side signal the census walked past

The same scan shows `[MUIC]` tags that XBL does not emit:
`muic_notifier_register` 25, `muic_notifier_notify` 50,
`muic_notifier_attach_attached_dev` 16, `muic_notifier_detach_attached_dev` 9,
`muic_notifier_init` 3. Those are Linux MUIC notifier lines, present in a
minority of the retained buffers. This unit did not analyse them; they are
recorded here because they are the only kernel-side MUIC evidence found so far
in this corpus, and the open question this campaign now carries is a kernel-side
one.

## The corpus holds kernel-side MUIC evidence, and all of it is stock

The register-accounting scan turned up `[MUIC]` tags that XBL does not emit —
`muic_notifier_register`, `muic_notifier_notify`, `muic_notifier_attach_attached_dev`
and its detach counterpart. Those are Linux MUIC notifier lines, so the retained
buffers carry kernel-side MUIC evidence, which this campaign had not previously
found anywhere. This section reads them, and the result is a negative that
matters more than the positive it was hoped to be.

### What the stock attach path looks like

Ten of the 121 distinct captures carry notifier lines. Two shapes appear.

In `postrollback_o3r1_last_kmsg.bin` the events run from `t = 577 s` to
`t = 681 s` in six attach/detach pairs, and every one of them is emitted by

```
[  581.897103] [3:irq/367-max7770:  869] [MUIC] muic_notifier_attach_attached_dev: (2)
[  581.897121] [3:irq/367-max7770:  869] [MUIC] muic_notifier_notify: CMD=1, DATA=2
[  581.897470] [3:irq/367-max7770:  869] [MUIC] muic_notifier_notify: notify done(0x0)
```

— **the MAX77705's own kernel IRQ thread**, `irq/367-max7770`, PID 869. That is
a cable being plugged and unplugged during a live session, and the interrupt is
what drives it.

The other shape is at boot. In `candidate-last_kmsg.bin` the same attach appears
at `t = 4.14 s`, but the emitting context is `modprobe`, PID 660, immediately
after four `muic_notifier_register` calls from PIDs 482, 553 and 660:

```
[    4.121229] [5:       modprobe:  660] [MUIC] muic_notifier_register: listener=9 register
[    4.141570] [2:       modprobe:  660] [MUIC] muic_notifier_attach_attached_dev: (2)
```

So the boot-time attach is the probe reading the part's current state as the
listeners register, not an interrupt arriving. `(2)` resolves against
`include/linux/muic/muic.h:141-145` — `ATTACHED_DEV_NONE_MUIC = 0`, then
`ATTACHED_DEV_USB_MUIC`, then `ATTACHED_DEV_CDP_MUIC` — so the attached device
is **`ATTACHED_DEV_CDP_MUIC`**, a charging downstream port.

The IRQ thread itself is not rare: **111 of the 121 captures contain a
`irq/<n>-max7770x` thread**. The 10 that do not are all `baseline-observer.bin`
and `rollback-observer-1.bin` files, and those carry no kernel MUIC line of any
kind — zero registers, zero attaches.

### The negative: no candidate boot is in this corpus

The reason this cannot answer the question it was opened for is that **none of
the 121 captures contains a candidate boot.** Two independent checks agree, and
the second was run precisely because concluding an absence from one check is the
error this report has made repeatedly.

The first looked for candidate-side markers — the checkpoint device
`/proc/s22_checkpoint`, a native-init string, a campaign run ID. **Zero captures
carry any of them.**

The second looked at who is running. Extracting the process field from every
`sec_log_buf` line gives 587 distinct process names, and the ones present in
**121 of 121** captures are `vaultkeeperd`, `qseecomd`, `UsbHostNotifica`,
`android.hardwar`, `wifi@1.0-servic`, `cass`, `iod`, `kauditd` and `init`. That
is a complete stock Samsung Android userspace, in every capture without
exception. A candidate boots the campaign's own PID 1 and runs none of it.

The file named `candidate-last_kmsg.bin` is not a counterexample; it is an
illustration. A retained buffer holds what ran *before* the capture, and this
one holds stock Android, `modprobe` and all, together with a download-mode
segment. Naming a capture for the run that collected it does not make its
contents a candidate boot.

### What this closes and what it hands forward

**Closed:** the hope that the retained corpus could show whether a candidate
ever received a MUIC attach. It cannot, because it contains no candidate boot,
and no amount of further reading of these files will change that. This is the
same shape as the `CONTROL1` inheritance result: a property of the evidence
class, not of the sample size.

**Handed forward**, and it is worth having: the stock attach path is now pinned
concretely rather than read from source. A working MUIC attach on this hardware
is `irq/<n>-max7770x` driving `muic_notifier_attach_attached_dev`, with the
boot-time initial state instead delivered in the `modprobe` probe context, and
`ATTACHED_DEV_CDP_MUIC` as the value a host port produces. That is the baseline
any candidate-side reading of `pdic_max77705.ko` or of the interrupt wiring has
to be compared against, and it did not exist before this unit.

## The shipped MUIC attach guards do not block the AP path

The next candidate-side question was deliberately narrower than "does the
driver exist": whether the exact shipped `pdic_max77705.ko` contains a guard
that prevents the stock CDP attach from reaching `com_to_usb_ap`.  It does not.
This section is direct-ELF analysis of the 423456-byte module, SHA-256
`27e988788242888dc0c3acaf835a66585c024b034b07741e619b674ee77db3db`,
BuildID `a59ccb842e0d521ec636b01ed54a65b6c0121d07`.  The ramdisk and
`vendor_dlkm` copies were already proved byte-identical; the latter was used.

This needed machine code rather than symbol-name inference.  The relevant
static helpers are inlined into the 4024-byte `max77705_muic_detect_dev`
function at `.text+0x177c4`, so their absence from the function symbol table
means nothing.  The audit reads ELF sections, symbols, relocations,
instructions and the dispatch table directly; `objdump` was used for human
inspection, not as the authority parser.  Its exact source counterparts are
also snapshotted and hashed so that field and enum names are not guessed from
offsets.

### CDP reaches the USB-path block

The attach switch uses `new_dev - 1` to index the halfword table at
`.rodata+0x5de`.  Values `1`, `2`, `23` and `24` — USB, CDP, JIG USB off and
JIG USB on — all resolve to `.text+0x18198`.  In particular, **CDP value `2`
enters the USB-path block**.  That is the same value the retained stock
notifier emitted, so this is a binary-to-observation comparison rather than a
new interpretation of the log.

A fresh probe stores `ATTACHED_DEV_NONE_MUIC` at `0x16650`, then calls the
initial detector with IRQ `-1` at `0x16c94`.  A first CDP result is therefore
not rejected by the duplicated-device branch.  The stock `modprobe` attach at
4.14 seconds is the observed positive control for exactly this probe-time
path.

### `usb_path` selects AP in both parameter cases

The inlined block loads `pdata->usb_path` from offset 12 at `0x181b8`.  The
three-way branch is exact: **`usb_path == 0` branches to AP** at `0x17c64`,
`usb_path == 1` branches to CP at `0x18428`, and every other value logs
`invalid usb_path` and performs no CONTROL1 write.

The producer closes the candidate-specific half.  In `common_muic.ko`,
`muic_param_pmic_info` is the four-byte value `-1` when no argument is passed,
`get_switch_sel` masks it with `0xfff`, and `muic_init_gpio_cb` writes
`usb_path = (switch_sel & 1) ^ 1`.  Therefore:

| load shape | `switch_sel` | `usb_path` |
|---|---:|---:|
| candidate-style, no module argument | `0xfff` | `0` = AP |
| stock `muic_param_pmic_info=3` | `3` | `0` = AP |

The missing stock parameter changes neither route.  This independently
confirms and machine-binds the source reading earlier in this report.

### `com_to_usb_ap` has one later suppression, and it starts clear

The AP block begins at `0x17c64`.  There is no conditional branch between its
`com_to_usb_ap` log and construction of `COM_USB=0x09`; the POGO return is not
compiled in this binary.  It places opcode `0x06`, data byte `0x09` and read
length zero in the command and calls `max77705_usbc_opcode_write` at
`0x17d18`.

**`fac_water_enable` is the only surviving post-AP suppression.**  At
`0x17cb8` the module loads the word at `usbc_data+1108`; the `CBNZ` at
`0x17cbc` skips the opcode call when it is nonzero.  That does not create a
candidate-only default:

- `usbc_data` is allocated with `kzalloc`, so the field starts at zero;
- the entire `.text` contains exactly two stores to offset 1108, at `0x9d70`
  and `0x9da0`, setting it to one for control-option command 3 and clearing it
  for command 4;
- `max77705_control_option_command` has exactly one call site, `0xebec`, inside
  `max77705_sysfs_set_prop`, and it is not a kernel export.

Thus a no-parameter load with no PDIC control-option sysfs write takes the AP
branch and enqueues `06 09`.  The exact stock log — `usb_path=0`,
`com_to_usb_ap`, `switch_path value(0x9)`, wire dump `06 09` — agrees at every
step.

### Consequence

These guards **do not explain the earlier candidate silence**.  That is useful
negative evidence: adding or changing another attach-path bypass would target
a mechanism the shipped binary does not contain.  It does not prove that an
earlier candidate reached this block.  The remaining boundary is now smaller:
did the module probe and bind, did initial status classify the attached host as
USB/CDP, did the exact IRQ/DT wiring exist, and did the queued opcode reach the
I2C worker?  Those are the next candidate-side checks.  No device action is
needed to answer their structural half.

## The stock DT and nested IRQ chain close through the nonnegative I2C write path

The structural half is now answered, and the answer is another useful
negative: the shipped DT, MFD demultiplexer and PDIC nested-IRQ wiring are
internally consistent and the same path is visible end to end in a retained
stock positive control. This does **not** say that a candidate loaded or bound
the modules. It says that a defect in the stock DT or shipped IRQ demultiplexer
is not an explanation for the candidate silence.

The audit reads the 8388608-byte stock `dtbo.img`, SHA-256 `97a4864f...`, with a
bounded FDT parser rather than `strings`. It contains 11 FDT blobs. The sole
`Samsung G0Q PROJECT (board-id,12)` overlay is blob 10 at `0x6bdce4`, size
708337, and targets `qupv3_se5_i2c`. Its enabled `max77705@66` node has:

- compatible `maxim,max77705`, address `0x66`;
- enabled child `max77705_pdic`;
- interrupt tuple `<0x11 5 1>`, whose phandle node in the FDT itself resolves
  as **pm8350c GPIO5**, active low; and
- pinctrl state `if_pmic_irq`, also on GPIO5.

The direct-ELF half uses the exact shipped 125840-byte `mfd_max77705.ko`,
SHA-256 `26f23873...`, and the same 423456-byte `pdic_max77705.ko` used in the
guard audit. The MFD module consumes `max77705,irq-gpio`, allocates 42 nested
descriptors, converts the GPIO to the parent Linux IRQ, and registers a
low-triggered one-shot threaded handler named `max77705-irq`. It publishes
three MFD children, including `max77705-usbc`; that is exactly the PDIC platform
driver name. Its parent handler reads the USBC interrupt group and calls
`handle_nested_irq(irq_base + i)`.

The PDIC probe registers five MUIC children at offsets 22, 23, 24, 26 and 27.
CHGT is offset 26. Probe completion sets `cc_booting_complete = 1` and then
clears parent INTSRC mask bit 3. Both order and polarity are bound in source
and in the shipped machine code. Before that completion the handler may exist
but the USBC group is not an enabled diagnostic path; after it, the parent can
dispatch the nested MUIC sources.

### One retained stock exemplar agrees at every boundary

The first positive-control exemplar is the exact 2097136-byte
`postrollback_o3r1_last_kmsg.bin`, SHA-256 `8069cece...`. Its parent line
occurs 174 times and always reports the same tuple: Linux IRQ `367`, nested IRQ
base `324`, Linux GPIO `282`, IRQ source `0x08`, PMIC revision `0x05`. The
kernel thread name `irq/367-max7770` is not a different action name: the kernel
constructs `irq/367-max77705-irq` and `TASK_COMM_LEN=16` truncates it to the 15
visible characters.

Within this capture the nested inventory is exact: VBUS is IRQ 346, VBADC is
347, and CHGT is 350. For CHGT, **`324 + 26 = 350`**, directly joining the
logged base to the PDIC offset. A second capture uses base 330 and absolute
IRQs 352, 353 and 356 while preserving the same offsets. Six CDP attach
sequences in the first exemplar each preserve the same order:

```text
max77705_muic_irq irq:350 (muic-chgtyp)
CDP classification
max77705_muic_attach_usb_path usb_path=0
com_to_usb_ap
opcode_write: 00000000: 06 09
muic_notifier_attach_attached_dev: (2)
```

That closes more than static compatibility. In the retained stock corpus, the
enabled DT route produces dynamically allocated parent and nested IRQ numbers
whose relative offsets match the shipped PDIC demultiplexer, and the handler
reaches the AP attach path.

One wording needs an exact boundary. `opcode_write: 06 09` is emitted just
*before* `max77705_bulk_write()`, so it is a pre-write buffer dump, not a
physical-wire capture. The exact source calls the bulk write immediately after
the dump; its caller logs `i2c write fail. dequeue opcode` on every negative
return, and that failure line occurs zero times in this raw. The stock control
therefore proves a **`06 09` I2C bulk-write attempt with a nonnegative return**,
not an electrical acknowledgement independently observed on the bus.

### Consequence and retained boundary

The hypothesis that a stock DT, GPIO, MFD child-name, nested-offset or shipped
demultiplexer defect explains the candidate silence is refuted. The result
does not upgrade any rejected candidate observation and does not infer a
candidate event from this stock log. The remaining direct boundary is
**candidate-side module load, platform bind, `cc_booting_complete` publication,
parent-USBC unmask, and initial status classification**. A successor should
observe those gates rather than change another connector-side attach guard.
The work is H0 only; it contacted no device and grants no D0, D1, F1, recovery,
replay or live authority.

## The IRQ numbers are not stock properties; the offsets are

The MAX77705 IRQ and device-tree audit landed in `281b8e0f17` and established
the stock attach chain from one retained capture. Its device-tree result stands
and is the useful half. Its three absolute interrupt numbers do not, and this
section separates them, because the audit freezes those numbers as identity
constants and will fail closed against any other capture in the corpus.

### What generalises: the offsets

Both captures in the corpus that log nested interrupt numbers agree on the
offsets, and they are the same offsets the shipped PDIC binary and source give:

| line | capture A | capture B | offset |
|---|---|---|---|
| `muic-vbusdet` | 346 | 352 | **22** |
| `muic-vbadc` | 347 | 353 | **23** |
| `muic-chgtyp` | **350** | **356** | **26** |
| implied nested base | 324 | 330 | — |

The base is not inferred from one nested IRQ. It is the `irq_base` field printed
directly by `max77705_irq_thread`. Against that independent field,
346 − 324 = 352 − 330 = 22, and likewise for 23 and 26. The base-free checks
also agree: 347 − 346 = 353 − 352 = 1 and 350 − 346 = 356 − 352 = 4.
**The offsets are the invariant.** The DTBO closes the parent GPIO route; the
PDIC binary/source and these two retained captures close the nested offsets.

### What does not: the absolute numbers

The audit states "parent IRQ 367 → nested base 324 → CHGT offset 26 → IRQ 350"
as one chain, which reads as four properties of the stock system. Only the third
is. Scanning the parent thread name across the corpus returns **at least 24
distinct parent IRQ numbers**:

```
344 348 350 355 356 358 362 363 364 366 367 368 369 370 371 372
373 374 375 376 377 378 379 380
```

`367` occurs in 6 of the 111 captures that carry the thread. The nested base is
**324 in one capture and 330 in another** — the only two that print it. These
are dynamically allocated Linux IRQ numbers and they shift from boot to boot;
freezing them as identity constants binds the audit to a single blob.

The audit's own thread-name derivation is correct and worth keeping:
`irq/367-max77705-irq` truncated to `TASK_COMM_LEN` gives `irq/367-max7770`,
which is exactly the comm this report found earlier. The derivation generalises;
the `367` in it does not.

### The chain is broader than claimed in one respect and narrower in another

The audit checks its six-token chain in a 45-line window before each of six
attaches, in one capture. Checking the same tokens across all ten
notifier-bearing captures gives a sharper result.

**Broader:** `com_to_usb_ap` is followed by exactly one
`opcode_write: 00000000: 06 09` in **10 of 10** captures, 17 occurrences in
total, with the two counts equal in every capture. That is a much stronger
statement than six occurrences in one blob, and it does not depend on the
interrupt.

**Narrower:** the chain's *first* token, `max77705_muic_irq irq:<n>
(muic-chgtyp)`, appears in **two of ten** captures. Across the 17 AP events,
eight run in an IRQ-thread context and nine in `modprobe` or `kworker` context.
The other **eight captures** have no logged chgtyp interrupt at all. So an
interrupt is one route to the mux write, not the route.

### The ordering is not invariant

The audit asserts the `06 09` dump precedes the notifier attach. That holds
**16 times out of 17**. The one exception is in the capture the audit did not
read:

```
37267.635277  com_to_usb_ap
37267.635343  muic_notifier_attach_attached_dev: (2)
37267.659355  opcode_write: 00000000: 06 09      ← 24 ms later
```

The notifier fires before the write is dumped. That is consistent with the
opcode being queued rather than issued inline — the failure log the audit counts
is `i2c write fail. dequeue opcode`, and a dequeue implies a work queue — but it
means the order is a tendency, not a guarantee, and an ordered-token assertion
over it is too strong.

### Two smaller corrections

The apparent three-to-two asymmetry was produced by counting CDP `(2)` rather
than all attach values. The capture has three `com_to_usb_ap`, three `06 09`
dumps and three notifier attaches: two `(2)` and one `(64)`. The `(64)` event is
the same capture's DCD Timeout `i(8)` path. There is no retained-window
truncation to invoke and no attach-less AP write in these 17 events.

The original audit hardcodes `CDP` as the matched device. The corpus also contains
`vps table match found at i(7), USB`, `at i(8), DCD Timeout`, and notifier values
`(1)` and `(64)` besides `(2)`. The CDP path is one of several the same code
serves.

### Why this is worth stating plainly

This is the seventh instance of the shape this report keeps returning to: a
result read off one sample and stated about the medium. It is worth noting that
the correction did not weaken the finding. The device-tree derivation survives
intact, the `com_to_usb_ap` → `06 09` coupling came out stronger than claimed,
and what was lost was three constants that were never going to hold.

The repaired audit does not replace those constants with new corpus-size
constants. It independently re-enumerates the current private tree, hashes and
deduplicates every size-matching file, requires that live population to equal
the exact manifest, and then requires per-capture `com_to_usb_ap`, `06 09` and
attach multiplicities to agree. It derives the current 17 and 16/1 ordering
split as result data; neither is an acceptance literal. Likewise, it reports
the current 24 parent values without accepting only that set. The only nested
arithmetic gate uses the directly logged base plus all three offsets and the
two base-free pairwise differences.

## Initial classification precedes unmask; the historical live-load claim did not survive

The candidate-side boundary was split into five observables rather than being
treated as one `pdic_max77705` event: module insertion, `max77705-usbc` platform
bind, the final VBUSDET registration result, initial MUIC classification, and
parent-USBC unmask. That split changes the priority of the next witness.

### The stock initial attach is an IRQ-free probe action

The complete 121-capture corpus contains ten captures with an AP mux path. Two
contain a logged `muic-chgtyp` interrupt. The other **eight** are exactly the
eight captures containing one boot-time `modprobe` sequence, and every one has
the same ordered chain:

```text
max77705_muic_probe
max77705_muic_init_detect
USBC1 0x27 / USBC2 0x05 / BC 0x82
ATTACHED
com_to_usb_ap
opcode 06 09
notifier CDP (2)
max77705_usbc_probe: probing Complete
```

This is set equality, not two independent counts that happen to be eight. The
audit derives the set from the re-enumerated manifest corpus and requires
`initial-probe captures == AP-path captures - chgtyp-IRQ captures`. All eight
tokens occur once per capture in `modprobe` context, in order, with no initial
status-read failure and no unmask-read failure.

The source explains why. `max77705_muic_probe()` calls
`max77705_muic_init_detect()`, which sets `is_muic_ready`, bulk-reads the five
status bytes and classifies them with the synthetic `MUIC_IRQ_INIT_DETECT`.
Only after that function returns does `max77705_usbc_probe()` publish
`cc_booting_complete = 1` and call `max77705_usbc_umask_irq()`. The initial
attach therefore does not wait for a physical CHGT interrupt and does not
depend on parent bit 3 already being unmasked. If the cable state is present
when the driver probes, classification can open the AP mux first.

### Probe completion and unmask are not success receipts

There are two independent fail-open status joins in the shipped driver. The
source calls `max77705_muic_probe(usbc_data);` as a bare statement. The exact
module agrees: the `bl max77705_muic_probe` at `.text+0xd4f0` is followed by
`mov x0,x19`, discarding the return before CC initialization. A failed MUIC
initialization therefore does not prevent the outer platform probe from
continuing.

The unmask helper is `void`. It reads parent register `0x23`, returns without
clearing bit 3 if that read fails, and ignores the return from the following
write. The caller still prints `probing Complete..` and returns zero. Thus none
of these alone proves the preceding boundary:

- `finit_module(pdic_max77705.ko) == 0` does not prove that a matching child
  finished a successful MUIC initialization;
- `probing Complete..` or `cc_booting_complete == 1` does not prove the initial
  five-byte classification succeeded; and
- either one does not prove register `0x23` was written with bit 3 clear.

The layers need distinct witnesses. In particular, the final VBUSDET result is
the hidden gate between bind and initial classification, while unmask is
important for later interrupts but is downstream of the boot-time attach that
matters here.

### The surviving S7A2 artifact proves a plan, not a live load

The exact 100669481-byte S7A2 AP was unpacked again rather than trusting its
old manifest. It yields the exact 100663296-byte boot, 8904-byte PID 1 and
1378-byte, 86-entry module list. The relevant one-based positions are
`msm-geni-se` 30, `gpi` 31, `i2c-msm-geni` 62, `mfd_max77705` 82,
`spu_verify` 83 and `pdic_max77705` 84. So the candidate artifact really does
contain the transport, parent and child in the intended order.

The exact historical loader source gives that fact its limit. It calls
`finit_module`, emits `phase=module name=<name> rc=<value>`, increments
`loaded` for every *attempt*, and proceeds regardless of a negative return.
Its only evidence sink is `/dev/kmsg`; it does not fsync a durable receipt. The
S7A2 live result retained zero S7A2 markers. M7, M11, M12 and M18 likewise state
that their retained marker absence does not prove their module loop was
reached. Consequently, the earlier sentence that all five candidates “did
load `pdic_max77705`” confused planned inclusion with observed success. Their
plans included it; their live `finit_module` results, platform binds, initial
classifications and unmask write results are unknown.

### The next witness is now exact

A successor does not need another connector-side guard and should not put ACM
on its proof-critical path. Its retained ring witness should close, in order:

1. durable per-module `finit_module` results for `i2c-msm-geni`,
   `mfd_max77705` and `pdic_max77705`;
2. the exact `max77705-usbc` platform bind and probe-entry identity;
3. the final VBUSDET `request_threaded_irq` result that controls whether
   `max77705_muic_irq_init()` returns success;
4. the initial five-byte MUIC status and the classified device/path; and
5. a readback of parent INTSRC mask register `0x23` with bit 3 clear.

The bind, VBUSDET and initial-status witnesses must be retained together: if
the five-byte classification is absent, they distinguish no bind from the
silent final-IRQ gate. The first four decide whether the IRQ-free probe path
opened the mux. The fifth separately decides whether later interrupts were
enabled. This unit is H0 only and performs no device action.

The retained auditor is
`workspace/public/src/scripts/analysis/s22plus_fyg8_p319_candidate_pdic_probe_boundary.py`.
Its reviewed V1 private receipt is 12719 bytes/SHA-256 `d4d40565...`, mode
`0400`, link count one. It re-extracts the AP using exact tool snapshots, binds five
historical live reports, exact source functions and exact PDIC machine-code
instructions, and re-enumerates the complete current corpus before deriving
the eight/two split. Fifteen focused real-input and mutation tests pass. The
first 12719-byte `d2101f69...` receipt is preserved under `20260820-01`; it was
generated before the focused mutation suite and is not current authority. V1
is superseded by the narrower V2 registration split recorded next.

## The platform probe has two silent failure points, not one

Reviewing the probe-boundary audit against the materialized driver source
confirms its ordering result and its two negatives, and adds one the audit did
not record. All line numbers below are in the audit's own materialized
`max77705_usbc.c`.

### Confirmed at source

The ordering holds exactly as stated:

```
3835:   max77705_init_irq_handler(usbc_data);
3836:   max77705_muic_probe(usbc_data);        ← init_regs, then init_detect
3897:   max77705_usbc_umask_irq(usbc_data);
```

with `max77705_muic_probe` reaching `max77705_muic_init_detect`, which sets
`is_muic_ready = true` and calls `max77705_muic_detect_dev(muic_data,
MUIC_IRQ_INIT_DETECT)`, and the classification path continuing
`max77705_muic_handle_attach` → `max77705_muic_attach_usb_path` (`:1419`,
`:1432`) → `com_to_usb_ap` (`:1155`). So **the AP mux switch is reached 61 lines
before the parent unmask**, and the log evidence agrees: eight of the ten
notifier-bearing captures perform the whole sequence with no logged chgtyp
interrupt.

`max77705_usbc_umask_irq` is confirmed `static void`. It reads `0x23`, returns
silently on a read failure, and does not check the write result, so
`msg_maxim("probing Complete..")` at `:250` of the function body prints whether
or not the unmask succeeded.

### The addition is real, but it is the USBC IRQ family

The report already records that `max77705_muic_probe`'s return is discarded, so
a failed MUIC probe does not fail the platform probe. The same is true one line
earlier and was not recorded: `max77705_init_irq_handler` is declared
`int max77705_init_irq_handler(...)` at `:3319`, and the call at `:3835` is
bare — no assignment, no test. The exact module agrees: the branch at
`.text+0xd4e8` is followed by `mov x0,x19` at `.text+0xd4ec`, before the
separate MUIC-probe branch at `.text+0xd4f0`.

The function name alone is too broad a description of what failed. This first
handler registers the APC, SYSMSG, VDM0 through VDM6, and VIR0 interrupt
families. Its result is discarded, so failure in that **pre-MUIC USBC IRQ
family** does not block the subsequent initial-detect call. This does not prove
that every nested MUIC IRQ-registration failure is non-blocking.

### The nested MUIC registrations have a last-result gate

`max77705_muic_irq_init()` separately requests UIADC, CHGT, DCD, VBADC and
VBUSDET in that order. `REQUEST_IRQ` assigns each request result to the same
`ret`; on a negative result it clears that IRQ field but does not return. A
later success therefore overwrites an earlier failure. In particular, a CHGT
registration failure can be hidden by a later successful request and does not
by itself prevent the IRQ-free initial classification.

The final request is different only because it is last. A negative VBUSDET
result is the value returned to `max77705_muic_init_regs()`, which frees the
MUIC IRQs and returns the error. `max77705_muic_probe()` then takes
`fail_init_irq` before `max77705_muic_init_detect()`. The outer USBC probe still
discards that MUIC-probe return and may print `probing Complete`, but the
five-byte initial classification and AP mux write did not run.

The useful elimination is therefore precise: absence of a delivered CHGT
interrupt does not explain an absent **initial** mux transition, and neither
does a pre-MUIC APC/SYSMSG/VDM/VIR registration error. A final nested IRQ
failure can still stop initial detect while remaining invisible in the outer
probe result. The broad statement in the append-only
`h0-probe-has-two-silent-failure-points-1` row that any MUIC interrupt-handler
failure remains non-blocking is superseded by this split. Its separate claim
that five historical candidates loaded `pdic_max77705` is also superseded by
the already established plan-inclusion/live-result distinction.

### A scope note on the unmask evidence

The V2 audit counts all three source call sites but semantically reads only the
probe-path `max77705_usbc_umask_irq` call. The same source has two further call
sites, at `:2888` and `:2921`, both in reset or RAM-test
recovery paths preceded by `usbc_data->is_first_booting = 1;` and
`max77705_init_opcode(usbc_data, 1);`. They were not examined. Nothing here
suggests a candidate reaches them, but "the unmask helper is called once" is not
what was checked and should not be read into the result.

### One wording correction

A summary of this work stated that classification runs "before IRQ/unmask".
Registration is **before** classification, at `:3835`; only the unmask is after.
The report's own section title says "precedes unmask" and is correct. The two
facts have different mechanisms — ordering puts classification ahead of the
unmask, while a *discarded return* is what makes the pre-MUIC USBC registration
failure non-blocking — and collapsing them would hide the second.

### V2 retained evidence

The current V2 receipt is 14440 bytes/SHA-256 `cd3969eb...`, mode `0400`, link
count one under `candidate-pdic-probe-boundary-20260820-04`. The bound auditor
is 53129 bytes/SHA-256 `937301a7...`; the 10927-byte focused test source is
`e73bb60b...`, and its fifteen tests cover both discarded call results, both
discard instructions, the shared-ret/final-VBUSDET distinction and the 3/1/2
unmask call-site scope. The 14091-byte `3a4765ad...` intermediate is preserved
under `20260820-03`; it bound the new source seams but preceded the explicit
conclusion fields. The two 12719-byte V1 receipts under `20260820-01` and `-02`
remain historical evidence. Only V2 is the successor under the original
`candidate-pdic-probe-boundary` review obligation.

Independent source review reproduced the exact 14440-byte `cd3969eb...`
receipt and confirmed both corrections: `max77705_init_irq_handler` owns the
USBC APC/SYSMSG/VDM/VIR family rather than the nested MUIC family, and only the
last shared-`ret` MUIC request controls the return from
`max77705_muic_irq_init()`. The scoped verdict is
`PASS_GO_P319_CANDIDATE_PDIC_PROBE_BOUNDARY_V2_H0_CAPABILITY`; it resolves that
one review obligation and grants no device or live authority. The implementation
snapshot literally ran all 298 P3.19 tests successfully. The reviewer later
measured 297/298, with only the known unrelated raw-first 1726/1729 identity
drift caused by concurrent S20+ files. A later bookkeeping run again measured
297/298 but regenerated 1724 against the same preserved 1726, confirming that
the count itself moves with that concurrent inventory rather than with this
S22+ closure. Common Process-v2 passes 122/122. These time-stamped shared-tree
aggregates do not alter the exact 15/15 V2 closure.

## Successor H0 design: four of the five witnesses need no new code

The witness order is fixed. This section is the H0 design input for a successor
that preserves it, and it starts from a measurement rather than from a plan:
**which of the five are already emitted, and do they already survive the ring.**

### What the stock driver already emits

| # | witness | existing emitter | captures carrying it |
|---|---|---|---|
| 1 | per-module `finit_module` rc | S7A2 `emit_module_result(name, rc)` → `/dev/kmsg` | — (no candidate boot in corpus) |
| 2 | bind / probe entry | `msg_maxim("probing Complete..")` | 8 |
| 3 | VBUSDET registration result | `max77705_muic_irq_init uiadc(..), …, vbusdet(N)` | 8 |
| 4a | initial status bytes | `USBC1:0x.., USBC2:0x.., BC:0x..` | **121 of 121**, 1163 lines |
| 4b | classification result | `vps table match found at i(N), <name>` | 17 |
| 5 | parent `0x23` bit 3 readback | **none** | 0 |

Witness 3 is the one worth dwelling on, because it converts an inference into a
reading. `REQUEST_IRQ` sets `_irq = 0` when a request fails, and the `pr_info`
that prints all five IRQ numbers runs **unconditionally** after the last request
and before `return ret`. So `vbusdet(0)` is a *positive* witness that
registration failed, and a nonzero value is a positive witness that it
succeeded. Nothing has to be added to the driver, and the "absence of an error
line" reasoning this report has had to bound repeatedly is not needed here.

The same line is a better source than the one the IRQ audit currently uses. The
audit reads nested numbers from `max77705_muic_irq irq:<n> (muic-<name>)`
dispatch lines, which exist in only 2 captures. The `irq_init` five-tuple exists
in 8, and it additionally carries `uiadc` and `dcdtmo`, which no dispatch line
in the corpus ever showed. A sample reads
`uiadc(355), chgtyp(354), dcdtmo(352), vbadc(351), vbusdet(350)` — base 328,
and the base-free differences hold: `354 − 350 = 4`, `351 − 350 = 1`.

### The two real gaps

**Witness 5 has no emitter at all.** A readback of parent `0x23` with bit 3
clear is not printed anywhere in the driver, and nothing in the corpus carries
it. This is the only witness that requires new capability, and it is the one the
fixed order puts last — correctly, since it does not gate the mux write.

**Witness 4 is three bytes, not five.** `max77705_muic_detect_dev` reads
`u8 status[5]` and prints only `status[0..2]` as `USBC1`, `USBC2`, `BC`.
`status[3]` and `status[4]` are read into the buffer and never logged. Calling
this witness "the initial five-byte classification" overstates what the existing
emitter provides by two bytes.

### The constraint that actually decides the design

All five witnesses occur before roughly `t = 5 s`. The retained ring is FIFO and
2,097,136 bytes. Measuring every capture in the corpus:

| | value |
|---|---|
| ring span, seconds | min 24, **median 540**, max 984 |
| earliest timestamp still in the ring | min 1, **median 9029**, max 236195 |
| captures whose ring still reaches `t < 10 s` | **14 of 121** |

So on a stock boot the ring holds roughly nine minutes of kernel log, and **the
boot window has already been overwritten in 107 of 121 retained captures.** The
witnesses are not lost because nothing wrote them; they are lost because
everything written afterwards pushed them out.

That reframes the requirement. It is not a time budget and should not be written
as one. It is a **byte budget**: the total kernel log emitted between the
witness lines and the moment the ring is captured must stay below 2,097,136
bytes. On stock that budget is consumed in about nine minutes because stock
Android userspace is loud — `vaultkeeperd` alone accounts for 606,320 lines
across the corpus. A candidate runs none of that userspace, so its budget should
last far longer, but **that rate is unmeasured**, because no candidate boot
exists in this corpus to measure it from. The successor should therefore treat
the byte budget as the design constraint and instrument its own consumption
rather than assume the stock figure transfers.

### What this means for the successor

It does not need to add instrumentation for witnesses 2, 3 and 4b, and it needs
only two bytes more for 4a. Its real work is threefold: guarantee the candidate
*reaches* those lines, keep the post-witness log volume inside the byte budget
until the ring is captured, and add the single missing emitter for witness 5.
Witness 1 is already emitted by the S7A2 loader but has never been observed to
survive, because no candidate boot has ever been retained — so it must be
treated as unvalidated retention rather than as a working channel.

## Successor transport correction: stock retention is not candidate retention

The corpus measurement above is correct about stock boots and wrong as a
candidate transport argument. The distinction is not subtle once the exact
candidate closure is read: **an emitter existing in the stock driver does not
connect it to the candidate's retained Carrier.**

### The current candidate has two different rings, not one path

The exact P3.18 static closure says `sec_log_buf_absent=true`. Its 70-entry
effective early plan contains the custom DWC3 latch and ends at
`i2c-msm-geni.ko`; it contains neither `sec_log_buf.ko` nor the stock
`mfd_max77705.ko` and `pdic_max77705.ko`. Consequently the current candidate
cannot reach the stock PDIC emitters, and ordinary `pr_info` or PID 1 writes to
`/dev/kmsg` have no Samsung retained-log writer behind them.

The Carrier is a separate direct writer. The fixed kernel patch maps the
2,097,152-byte reserved region, seeds from its 16-byte header's `idx`, places
the 192-byte Carrier record directly in the 2,097,136-byte payload, and requires
`head->idx == seed_idx` before every later update. It deliberately does not
advance `idx`.

Loading `sec_log_buf` after that seed is not a harmless way to acquire the
missing stock lines. Its probe first copies the current printk early buffer by
calling `__log_buf_write`, and every positive write increments `idx` by the
exact byte count. Its live console writer does the same for every accepted
message. Any such write violates the Carrier's fixed-`idx` gate and makes later
Carrier publication fail closed. Adding that module therefore requires a
Carrier redesign and is forbidden for this successor.

This corrects the design implication in append-only row
`h0-successor-witness-design-1`: witnesses 2, 3, 4a and 4b already have **stock
emitters**, but none is yet a candidate-retained witness. The stock 2 MiB FIFO
byte budget describes the stock logger, not the current direct Carrier.

### The usable transport already exists elsewhere in the runtime

P3.18 inherited the P3.03 live `/dev/kmsg` observer. Before the module loop it
creates and opens `/dev/kmsg` read-only/nonblocking and seeks to the live tail.
It drains after the complete module loop and again during the later execution
window. `EPIPE` is an explicit ring-loss terminal, and a non-consecutive kmsg
sequence is a separate fail-closed contradiction. This is the path that can
observe the stock emitters without changing the reserved-ring `idx`.

It still needs a bounded successor delta. Today it drains only after the full
module loop, retains no raw lines, and does not count cumulative record bytes.
The successor must:

1. drain after each relevant module rather than waiting for the whole loop;
2. count the exact bytes returned by `/dev/kmsg`, reject counter overflow, and
   preserve first/last sequence plus the existing `EPIPE`/gap result;
3. parse only the exact bind/probe, IRQ five-tuple, status and classification
   grammars against an external positive corpus; and
4. publish their structured summary through the direct Carrier, never claim
   the transient raw printk text as retained authority.

Witness 1 should be published from the known `finit_module` return directly,
not recovered from PID 1's own log line. The exact bind symlink is stronger
than `probing Complete` and should remain the bind identity. The live-kmsg
parser supplies VBUSDET, the existing three printed status bytes and the
classification. A separately qualified producer still supplies status bytes
3/4 and the final register-`0x23` readback.

### Retained audit

The host-only auditor is
`workspace/public/src/scripts/analysis/s22plus_fyg8_p319_candidate_witness_transport.py`.
It binds the exact P3.18 static closure, plan, runtime wrapper/include and
candidate patch plus the Samsung retained logger source/header. Its current
private receipt is 4111 bytes/SHA-256 `ef917cd3...`, mode `0400`, link count
one; eight preserved inputs are also mode `0400`, link count one under mode
`0700` directories. The auditor is 24025 bytes/SHA-256 `13f22634...`; the
7386-byte focused test source is `0b3edc5e...`, and 13 real-input and mutation
tests pass. The `20260820-01-failed-before-result` directory is preserved: its
inputs were complete, but an incorrect expected direct-store multiplicity
stopped before result publication. `20260820-02` is the only current receipt.

This result is `IMPLEMENTED_REVIEW_PENDING`. It changes no candidate byte and
creates no device or live authority. The next H0 unit is an external-corpus
qualification of the bounded P3.19 live-kmsg parser, not a candidate build and
not an F1 execution.

## Review of the transport binding: the emitters are not in the plan

The witness-transport unit is `IMPLEMENTED_REVIEW_PENDING`. This is that review.
Its two load-bearing claims hold, its receipt reproduces, and it leaves one gap
that has to be stated before the next unit starts.

### Confirmed

The `sec_log_buf` prohibition is sound and is the kind of claim that deserved
checking, because it removes an option. The Carrier maps the 2,097,152-byte
reserved region, seeds from the header's `idx`, and gates every later update on
`head->idx == seed_idx` without advancing it. `sec_log_buf`'s probe copies the
early printk buffer through `__log_buf_write`, which advances `idx` by the byte
count, and its console writer does the same per message. So loading it after the
seed does break the gate, and the module is correctly excluded.

The correction to the design row `h0-successor-witness-design-1` is accepted.
That row measured the **stock** 2 MiB FIFO and derived a byte budget from it.
The candidate does not use that FIFO; it uses a fixed-`idx` direct Carrier
record. The byte-budget framing describes the stock logger and does not transfer,
and the row's design implication was wrong on that point.

The receipt reproduces here at 4111 bytes / `ef917cd32f743386...`, and the
auditor's plan check is a real mechanical parse of the bound header rather than
an assertion: 70 rows, last row `i2c-msm-geni.ko`, `mfd_max77705.ko` and
`pdic_max77705.ko` both absent.

### The gap: the parser targets lines this plan cannot produce

The successor delta specifies a `/dev/kmsg` parser for the bind/probe identity,
the IRQ five-tuple, the printed status bytes and the classification. **Every one
of those lines is emitted by `pdic_max77705` or `mfd_max77705`**, and the same
unit proves those two modules are not in the bound 70-entry plan. So on the
current plan the parser has nothing to parse — not because the transport is
weak, but because the emitters never run.

Nothing in the delivered design states that the successor's plan must carry
them. That requirement is load-bearing and unstated, and it is not an inference
the next unit should have to make: witnesses 2, 3, 4a and 4b are unreachable
without it, no matter how good the drain is.

The campaign has carried such a plan before. This report records that the
`S7A2`, `M7`, `M11`, `M12` and `M18` **plans** included `pdic_max77705` — a
planned load, not a proven one, as an earlier correction established. So
restoring the modules is a return to a shape the campaign has already built,
not new ground.

### A forward-compatibility note on the auditor

`audit_effective_plan()` raises `AuditError("P3.18 unexpectedly carries stock
MAX77705 modules")` when either module name appears. As an identity assertion on
the bound P3.18 artifact that is correct and should stay. But it fails closed on
exactly the plan shape the successor needs, so if a successor plan is ever passed
through this path the check has to move from "these modules are absent" to
"these modules match the plan under audit". Recording it now is cheaper than
rediscovering it when the successor plan first runs.

### What this does not change

The transport choice itself is right. Draining per module rather than after the
loop, counting returned bytes with overflow rejection, preserving first/last
sequence alongside the existing `EPIPE` and gap terminals, and publishing only a
structured summary through the Carrier while never treating transient printk
text as retained authority — all of that stands, and the ordering of witness 1
from the `finit_module` return rather than from PID 1's own log line is a
genuine improvement over what this report proposed.

## V2 plan input: the load order, and the DWC3 tie is one symbol on the DP path

The successor plan is now in scope as a separate H0 predecessor unit, and V2 has
to close the exact load order and the custom MUX diagnostic module replacement
alongside the existing closure. This section is input to that existing closure
obligation and opens no new one.

A note on how it is recorded: the ledger row for this input first quoted the
existing closure row's identifier inline, which collided with a uniqueness check
that matches that identifier surrounded by spaces and made two rows look like
closure-plan rows. The row was reworded rather than the check relaxed — the
check guards a real invariant, and the defect was in the new row. Both are decidable on this host, and this
section decides them.

### The closure and its exact load order

`modules.dep` on the mounted `vendor_dlkm` gives `pdic_max77705.ko` **13 direct
dependencies** and `mfd_max77705.ko` one. The transitive closure is **14
modules**, which independently reproduces the count the existing
`h0-module-closure-plan-1` already carries. Ordering them by dependency depth
gives the load order, with any order permissible inside a level:

| depth | modules |
|---|---|
| 0 | `if_cb_manager`, `redriver`, `spu_verify`, `switch_class`, `usb_notify_layer`, `vbus_notifier` |
| 1 | `common_muic`, `mfd_max77705`, `pdic_notifier_module`, `qc_usb_audio` |
| 2 | `usb_typec_manager` |
| 3 | `usb_f_ss_mon_gadget` |
| 4 | `dwc3-msm` |
| 5 | `pdic_max77705` |

`mfd_max77705` at depth 1 requires only `usb_notify_layer`, so the MFD half is
cheap. Everything expensive is below `pdic_max77705`.

### The DWC3 entry is one symbol, and it is on the DisplayPort path

`dwc3-msm` at depth 4 looked like the hard part, because the current candidate
carries a **custom DWC3 latch** and the user's V2 list names the custom MUX
diagnostic module replacement as an open item. It is smaller than it looks.

Intersecting `pdic_max77705.ko`'s undefined symbols with `dwc3-msm.ko`'s
`__ksymtab` exports returns exactly **one** name:

```
dwc3_restart_usb_host_mode
```

The module has exactly one relocation against it, `R_AARCH64_CALL26` at
`.text+0x12318`, and the enclosing defined symbol is
**`max77705_vdm_dp_select_pin`** — DisplayPort VDM pin assignment. The A90 tree
on this host shows the same family symbol called only from
`max77705_alternate.c` and `ccic_alternate.c`, both alternate-mode handlers,
which agrees, though the binding evidence here is the S22+ module itself rather
than the A90 source.

So the tie between `pdic_max77705` and the DWC3 module is a **link-time
requirement for one function on the DisplayPort alternate-mode path**. The
device-mode enumeration path this campaign cares about never reaches
`max77705_vdm_dp_select_pin`.

### What that decides, and what it does not

It collapses "replace the custom DWC3 latch with the stock module" into "satisfy
one symbol". That is a materially different and much smaller problem, and V2
should not carry the larger framing by default.

It does not decide **how** to satisfy it. Providing the symbol some other way
changes module identity and integrity, which this campaign's contract governs
and which needs its own review; nothing here authorises a stub. What is settled
is the size and location of the dependency: one symbol, one call site, on a path
the goal does not use.

### The two V2 items this does not touch

**Stage capacity.** The bound plan is 70 rows. Adding a 14-module closure takes
it to at most 84 minus whatever is already present, and whether the plan array
and its staging tolerate that is not answered here.

**EUD identity trigger.** Untouched by this analysis.

## V2 plan capacity and EUD identity: 73 rows fit, and 37 is stale

The remaining two V2 questions are also decidable without a candidate build.
The host-only auditor is
`workspace/public/src/scripts/analysis/s22plus_fyg8_p319_successor_module_plan_v2.py`.
It reopens the exact P3.18 plan and both runtime sources, the retained FYG8
`modules.dep`, and the preceding transport auditor rather than weakening that
auditor's P3.18-specific absence assertion.

### The fourteen-module closure adds only three rows

The closure has fourteen members, but eleven are already in the exact 70-row
P3.18 plan. The missing set is exactly:

1. `spu_verify.ko` / `spu_verify`;
2. `mfd_max77705.ko` / `mfd_max77705`; and
3. `pdic_max77705.ko` / `pdic_max77705`.

Appending those three in that order produces a dependency-safe 73-row plan:
indices 70, 71 and 72. Every dependency of all fourteen members precedes its
consumer.

This also removes an unnecessary choice from the prior framing. The exact base
plan already carries **both** `s22plus_dwc3_event_latch.ko` at index 0 and the
stock `dwc3-msm.ko` at index 59. The latch does not replace `dwc3-msm`; the
stock provider has no new plan row to add. The one-symbol/one-DP-call-site
result in the preceding section remains true, but this plan arithmetic does not
freeze the successor's exact provider binary or qualify its export. No stub is
authorised, and provider identity remains a materialization input.

### The folded stage representation fits 73 rows

The apparent 60-stage interval is not a 60-module array limit. The exact
runtime defines module stages `0x40..0x7b` before gate stage `0x7c`. It gives
indices 0 through 58 unique stages and folds every later load into index 59 /
stage `0x7b`, while preserving the actual failing index as
`0x700 + index`. The arrays themselves are sized from
`S22PLUS_O2_MODULE_PLAN_COUNT`, and two static assertions cap the byte-sized
index at 256 entries.

For the exact 73-row successor the arithmetic is:

| field | value |
|---|---:|
| direct entries | 59 |
| folded entries | 14 |
| last module index/item | 72 / `0x48` |
| last folded failure detail | `0x748` |
| folded stage / next gate | `0x7b` / `0x7c` |

At the representation boundary, 256 entries end at item `0xff` and detail
`0x7ff`; 257 is rejected. Seventy-three therefore fits without moving the gate
or widening a retained field.

### The EUD trigger must come from the same plan

The exact EUD identity is the full tuple `("eud.ko", "eud", "")`, present once
at zero-based index **38**. The inherited runtime independently defines
`P307_EUD_MODULE_INDEX 37U`; that is the P3.18 off-by-one which the latch
insertion exposed. Appending the three successor rows leaves the derived index
at 38, but merely changing the literal to 38 would preserve the original
hazard.

The V2 contract is stronger: derive the EUD index from that sole exact tuple in
the same plan materialization, permit no independent runtime literal, and call
one shared post-load trigger after successful loads in both the direct and
folded loops. A synthetic insertion before EUD moves the derived value from 38
to 39; a duplicate or a filename/runtime/params mismatch is rejected. The
current runtime has not yet implemented that consumer, so this result does not
claim a successor binary exists.

### Retained result and boundary

The current `-02` private receipt is 14833 bytes/SHA-256 `d8c12396...`, mode `0400`,
link count one. Five inputs are preserved mode `0400`, link count one under
mode `0700` directories. The 24387-byte auditor is `d2d61d6e...`; the
10907-byte focused test source is `0330f28a...`, and 15 real-input, boundary and
mutation tests pass. The `-01` receipt remains preserved at 14682 bytes /
`2ab6146d...`; it preceded the explicit source-bound `0x7ff` detail ceiling,
direct-loop placement mutation, and provider-identity qualification boundary,
so it is superseded and is not current authority.

This is a V2 implementation under the existing `module-closure-plan` review
obligation, not a second obligation. It is `IMPLEMENTED_REVIEW_PENDING` and
does not materialize the 73-row header, implement the shared runtime hook,
freeze the three added module binaries, qualify a build, or grant device/live
authority. Those materialization steps precede the live-kmsg parser
qualification; an external-corpus parser alone still cannot make an unreachable
emitter into candidate evidence.

## Review of the V2 plan unit, and a correction to this report's DWC3 framing

The successor-plan V2 unit answers the capacity item this report left open, and
in answering it refutes the framing of the section above. Verified here against
the bound plan.

### Confirmed: the increment is three, not fourteen

Intersecting the fourteen-module closure with the bound 70-row plan gives
**eleven already present** — `if_cb_manager`, `redriver`, `switch_class`,
`usb_notify_layer`, `vbus_notifier`, `common_muic`, `pdic_notifier_module`,
`qc_usb_audio`, `usb_typec_manager`, `usb_f_ss_mon_gadget` and `dwc3-msm` — and
**three missing**: `spu_verify.ko`, `mfd_max77705.ko`, `pdic_max77705.ko`.
70 + 3 = **73**. The receipt reproduces here at 14833 bytes /
`d8c12396e241e387...`.

This closes the stage-capacity question this report raised and could not answer.
The estimate offered there — "at most 84 minus whatever is already present" —
was a bound rather than a number, and the number is 73.

### The correction: there was never a DWC3 conflict to collapse

The section above analysed the `dwc3-msm` tie because the candidate "carries a
custom DWC3 latch", and framed the result as collapsing a custom-module
replacement into a single symbol. **That framing is withdrawn.** The plan
contains both:

```
row  0: s22plus_dwc3_event_latch.ko    (the campaign's custom module)
row 59: dwc3-msm.ko                    (the stock module)
```

They are not alternatives. The custom module is an *event latch* that coexists
with the stock DWC3 module, which the plan has been loading all along. So
`dwc3_restart_usb_host_mode` is already provided, the dependency was already
satisfied before this analysis started, and no replacement was ever pending.

The underlying facts in that section survive unchanged and were independently
correct: exactly one symbol ties `pdic_max77705` to `dwc3-msm`, it has exactly
one relocation at `.text+0x12318`, and the enclosing function is
`max77705_vdm_dp_select_pin` on the DisplayPort alternate-mode path. What was
wrong was the problem those facts were said to solve. Their actual bearing is
narrower: they say what would break if `dwc3-msm` were ever *removed* from the
plan, not what must be added to it.

This is the second time in this report a conclusion was drawn about a plan
without reading the plan — the first being the transport parser specified for
emitters the plan does not carry. Reading the 70 rows costs one command.

### The residual is provider identity, and it is correctly stated

The V2 unit's remaining caveat is the right one. Row 59 names `dwc3-msm.ko`, but
which **bytes** that row resolves to — the stock `vendor_dlkm` module or a
campaign-built variant — is not qualified, and that is what actually determines
whether the symbol is exported at load time. A named row is not a provider
identity. The same applies to the three new rows: naming them is not the same as
binding their bytes, which the unit lists as its next step.

The EUD index correction is likewise a real one: an index derived from the tuple
is 38, and the literal 37 that sat beside it was stale.

## Review of the 73-row materialization: the closure is inflated by unused paths

The materialization unit is `IMPLEMENTED_REVIEW_PENDING` and reports separately.
This is the review of its changed closure, verified here.

### Confirmed, including the cross-check this report asked for

The receipt reproduces at 10658 bytes / `8b8c1f5afd8c0269...`. The three added
entries are appended at indices 70, 71, 72 as `spu_verify.ko`,
`mfd_max77705.ko`, `pdic_max77705.ko`, which respects the dependency topology:
`spu_verify` has no dependencies, `mfd_max77705` needs only `usb_notify_layer`,
`pdic_max77705` needs all thirteen, and every one of them now precedes it.
`i2c-msm-geni` at row 69 still precedes the MFD, which it must.

The provider-identity residual raised in the previous review is **closed for
these four modules**. The receipt binds `spu_verify.ko`, `mfd_max77705.ko`,
`pdic_max77705.ko` and `dwc3-msm.ko` to the exact `vendor_dlkm` bytes —
`d670a944…`, `26f23873…`, `27e98878…`, `8913b050…` — which are the same bytes
this report's symbol analysis was performed on. That analysis therefore
transfers to the bound artifacts rather than to a same-named file.

### What the closure actually consists of

Both modules that entered this closure for non-obvious reasons turn out to be
link-only ties to paths the goal never takes, and the symmetry is worth naming.

`dwc3-msm` is tied by one symbol, `dwc3_restart_usb_host_mode`, whose single
relocation sits in `max77705_vdm_dp_select_pin` — DisplayPort alternate mode.

`spu_verify` is the same shape and had not been examined. Intersecting
`pdic_max77705.ko`'s undefined symbols with `spu_verify.ko`'s exports returns
exactly one name, `spu_firmware_signature_verify`, with exactly one relocation,
at `.text+0x102e8`. Its enclosing defined symbol is
**`max77705_firmware_update_sysfs`**.

So `spu_verify` enters the candidate solely to satisfy a symbol whose only
consumer is the MAX77705 **firmware-update sysfs handler** — a path this
campaign's contract places out of bounds and has never taken.

### Why that is worth recording rather than waving through

It changes nothing about whether the module should be added: the loader needs
the symbol resolved, and omitting `spu_verify` would fail the `pdic_max77705`
load outright. Loading it initiates nothing by itself.

What it changes is the description of the candidate. After this materialization
the candidate carries the link closure for a firmware-update path that is
contractually forbidden, and that fact should be visible to whoever reviews the
candidate's surface before a build — not discovered from the module list later.
Two of the fourteen closure members are present only for paths the goal does not
use, which also means the closure is not evidence that those subsystems are
needed at runtime.

### What remains unqualified here

The receipt binds four modules. The other ten closure members were already in
the plan and their bytes are not re-bound by this unit, so "the plan names them"
is still not the same as "these bytes will load" for those ten. Nothing observed
suggests a mismatch; it is simply outside what this receipt covers.

## An accounting correction: a review row is not a resolution

The two review rows this reviewer appended for the module-closure work —
`h0-v2-plan-review-dwc3-framing-withdrawn-1` and
`h0-materialization-review-spu-verify-tie-1` — read as independent reviews but
discharged nothing, and one of them opened an obligation instead of closing one.

The taxonomy's rule is mechanical and neither row met it. A resolving row's
ordinal must match `^h0-<topic>-review-<N>$` and its action must begin
`PASS_GO_`. Both of those rows carried plain `P319_…` actions, and their
ordinals put `review` inside the topic segment rather than in the fixed
position. So they parsed as ordinary rows.

The obligation they were meant to discharge is a single one:
`h0-module-closure-plan-1`, action
`P319_CANDIDATE_MODULE_LOAD_PLAN_IMPLEMENTED_REVIEW_PENDING`. The V2 row
`h0-module-closure-plan-v2-8` is explicitly recorded as sitting *under* that
obligation rather than opening a second, so the plan, its V2 stage and EUD
derivation, and the 73-row materialization are one topic with one review.

It is now discharged by `h0-module-closure-plan-review-1` with action
`PASS_GO_P319_MODULE_CLOSURE_PLAN_INDEPENDENT_REVIEW_V1`. The two earlier rows
stand unmodified as evidence; the ledger is append-only and their content was
never the problem.

The collision guard bit twice. Both the first review row and this resolution row
quoted the base ordinal inline, and a uniqueness check that matches that
identifier surrounded by spaces counted them as extra closure-plan rows. The
first occurrence was recorded a section earlier with the note that the check
guards a real invariant; the same mistake was then repeated in the very row
written to correct the accounting. Both times the row was reworded and the check
left alone.

The lesson generalises past this instance. Writing a thorough review and
recording it in prose is not the same as satisfying the accounting the campaign
runs on, and the accounting is the part that decides whether the next stage may
start. The check costs one command and should be run whenever a review row is
appended.

## Parser grammar input: the witness lines have four format strings, not two

Input for the parser/witness implementation that sits under the existing
candidate-witness-transport obligation. This resolves nothing and approves no
capability; it is the grammar the parser should be built from, taken from the
driver's own format strings rather than from examples in the corpus.

### The exact strings

```
probe entry        max77705_usbc.c:3912
                   msg_maxim("probing Complete..")

IRQ five-tuple     max77705-muic.c:2267   in max77705_muic_irq_init
                   "%s uiadc(%d), chgtyp(%d), dcdtmo(%d), vbadc(%d), vbusdet(%d)\n"

initial status     max77705-muic.c:1739   in max77705_muic_detect_dev
                   "%s USBC1:0x%02x, USBC2:0x%02x, BC:0x%02x\n"

classification     max77705-muic.c:1699   in max77705_muic_check_new_dev
                   "%s vps table match found at i(%lu), %s\n"
```

### Two traps a hand-written grammar would fall into

**The classification line has a second form.** `muic_lookup_vps_table` at
`max77705-muic.c:302` prints
`"%s (%d) vps table match found at i(%d), %s\n"` — an extra parenthesised
argument before the phrase, and `%d` where the other site uses `%lu`. Both forms
occur in the corpus:

```
muic_lookup_vps_table (1) vps table match found at i(7), USB
max77705_muic_check_new_dev vps table match found at i(9), CDP
```

A parser anchored on either one alone silently drops the other, and the two are
not interchangeable — they come from different call contexts, so the function
prefix has to be part of the grammar rather than skipped as noise.

**There is a richer status line, and it is not the initial-detect witness.**
`max77705-muic.c:2202` prints seven registers plus the classified device:

```
"%s USBC1:0x%02x, USBC2:0x%02x, BC:0x%02x, CC0:0x%x, CC1:0x%x, PD0:0x%x, PD1:0x%x attached_dev:%d\n"
```

That covers everything the five-byte witness wants and more. But its enclosing
function is `max77705_muic_print_reg_log(struct work_struct *work)` — a
**deferred work item**, not the initial-detect path. It is a valuable secondary
source if it lands inside the retained window, and it must not be accepted as
the witness for initial classification, because it does not run synchronously
with it and carries no guarantee of ordering against the mux write.

This also bounds the earlier note that "witness 4 is three bytes, not five".
That remains true of the initial-detect emitter at `:1739`. The two missing
bytes are printed elsewhere, asynchronously, by a different function.

## Review of the witness parser, and a coupling that will keep breaking audits

The parser predecessor carries a scoped `PASS_GO` and reports separately. This
is the review of it against this report's own grammar input.

### Confirmed

The receipt reproduces at 15478 bytes / `14ca869c411a5940...`, and the parser's
own suite is 25/25.

Both traps this report raised are handled, and handled properly rather than
labelled. Both classification grammars are bound with the function prefix as
part of the match, and the corpus qualification refuses to pass unless **both
forms** are present — a stricter gate than merely accepting either. The deferred
seven-register line is bound as `deferred_status`, marked
`deferred_status_is_auxiliary_only`, and is genuinely excluded from the ordered
witness staging: the stage map is `{irq: 1, initial_status: 2, classification:
3, probe: 4}` and `deferred_status` does not appear in it. The stored initial
status is `uint32_t initial_status[3]`, matching the three-byte emitter rather
than the seven-value one.

### Two places where a name claims more than the code computes

Neither is a correctness defect. Both are the kind of line that later gets
quoted as if it were a proof.

`required = {"probe", "irq", "initial_status", "classification",
"deferred_status"}` is **dead**. The gate on the next line tests a four-element
literal that omits `classification`, and `required` is never read again.
Classification is in fact required, and more strictly, by the following check
that both form counts are non-zero — so the coverage is right and the variable
stating it is not the thing enforcing it.

`deferred_is_not_initial` is computed as `initial_status_count > 0`. That is a
presence count, not the structural exclusion the name asserts. The exclusion is
real and lives in the stage map; this field does not test it. It does fail
closed in the case that matters — a log carrying only the deferred line yields
`False` — so the behaviour is sound and only the naming overstates.

### The coupling: two audits pin a drifting artifact by its bytes

This is the finding that matters, and it is not the parser unit's fault.

The parser unit materialized thirteen copies of a corpus capture into its own
run directories. Each is exactly 2,097,136 bytes, so each satisfies this
report's census criterion, which is deliberately mechanical and selects nothing
by name. The population went from 293 files to 306.

Rebuilding shows every conclusion is untouched: `distinct_captures` 121, ABL
stages 103, boot segments 268, `SetPath` 110, opcodes `0x01` 268 / `0x05` 378 /
`0x06` 378. The thirteen are pure duplicates. Only the raw file count and the
duplicate count moved, and this report now labels those two a dated snapshot and
pins the invariants instead.

But the MAX77705 IRQ/DT audit and the candidate PDIC probe-boundary audit both
bind `abl-capture-manifest.json` **by exact SHA-256**. The IRQ audit expects
`aa2d19ea09d3317d...`; the current manifest is `f234dd23547d4a31...`. Both
audits therefore fail in `setUpClass` with "source/snapshot bytes differ", and
they failed before this reviewer regenerated anything — regenerating changed
which mismatch, not whether there was one.

The manifest is a *generated, regenerable* artifact whose byte content moves
whenever any unit materializes a capture copy. Pinning it by bytes makes those
audits break as a side effect of unrelated normal work, and it will keep
happening: every future unit that stages a capture does the same thing again.

The fix is a design choice and is not made here, since both audits belong to
another unit. The direction the evidence supports is to bind the manifest's
**invariants** — distinct captures, ABL stages, boot segments, `SetPath` count,
opcode census — rather than its serialized bytes, because those are exactly the
quantities that survived the drift while the bytes did not.

## Semantic manifest binding: duplicate paths no longer rewrite authority

The bounded V3 successor implements that choice without weakening the corpus
gate. Both audits still stable-read the current generated manifest, require its
strict schema, and re-enumerate every 2,097,136-byte file under
`workspace/private`. The live file count, duplicate count, complete path lists
and the set of distinct capture hashes must agree with that current manifest.
A stale manifest or a new distinct capture therefore still fails closed.

What is no longer made permanent authority is the manifest's particular JSON
serialization. The two raw population fields `matching_files` and
`duplicate_files_collapsed`, plus each `captures[].paths` list, are removed from
a canonical semantic projection. Nothing else is removed. The projection still
contains all 121 distinct capture SHA-256 identities, every per-capture
classification, the ABL and boot-segment census, `SetPath`, BC/CONTROL1 and
opcode counts, and the kernel-side marker/daemon/IRQ/notifier census. Its exact
identity is 47,799 bytes/SHA-256
`c1c75743fcdb06a3b3180e6a1d091a620969922ac2209d9169d21922a6d7b6a3`.
Both the old 293-file manifest and the current 306-file manifest produce those
same bytes.

The positive regression adds a coherent duplicate path and increments both
volatile counts; both V3 receipts remain byte-identical. The negative
regressions change `abl_stages` or opcode `0x06`; each changes the projection
and is rejected. Thus the repair permits exactly the drift that already proved
semantically inert, rather than accepting arbitrary corpus growth.

The IRQ/DT V3 successor is `20260820-06`, 16,818 bytes/SHA-256
`48c389e4e9afe369238359c48baba3057680bd1d06bebe76fdd7f254591ef3c6`.
Its source is 61,791 bytes/SHA-256 `34aa1778...`, and its focused suite is now
16 tests. The PDIC probe-boundary V3 successor is `20260820-05`, 15,563
bytes/SHA-256
`7744d9e7c5d76148ad4038f59531dd686d6e8b3a1327e78206ae5c6ad4390025`.
Its bound source is 55,113 bytes/SHA-256 `74b7ce5d...`, and its focused suite is
now 17 tests. Both receipts are mode `0400`, link count one. The reviewed V2
receipts `5c84bfc5...` and `cd3969eb...` remain preserved rather than
overwritten.

The two auditor suites plus this report and taxonomy pass 181/181. The complete
P3.19 discovery passes 387/388: both manifest-coupling failures are gone, and
the sole remaining failure is the pre-existing raw-first whole-tree inventory
receipt at 1726 sources against the current 1724. Common Process-v2 passes
122/122. That unrelated dynamic inventory failure is reported, not waived.

This repair is `IMPLEMENTED_REVIEW_PENDING`. It changes only the H0 auditor
authority projection, performs no device action, and grants no D0, D1, F1,
recovery, replay or live authority. The Envelope-v5/Carrier unit remains next;
this repair only removes an unrelated generated-manifest tripwire from its
test path.

## The manifest coupling is fixed, and the fix is invariant in the right direction

The semantic-binding unit replaces the byte pin this report objected to. Verified
here, including the property that matters most: that the fix did not over-correct
into insensitivity.

### The projection drops exactly the drifting parts

`corpus_semantic_projection()` rebuilds the manifest without
`matching_files`, `duplicate_files_collapsed` and per-capture `paths`, sorts the
captures by `sha256`, and serializes with sorted keys. Everything the report
reasons from survives — the per-capture `bc_ctrl1_reads`, `boot_segments`,
`muic_opcodes`, `setpath_occurrences`, the opcode census and the counts block.
At 47,799 bytes across 121 captures it is around 395 bytes per capture, which is
consistent with keeping the whole per-capture record minus its paths.

### Tested against the failure mode, and against over-correction

Driving the projection directly with mutated manifests:

| mutation | projection |
|---|---|
| +40 pure duplicate paths, counts bumped | **unchanged** |
| +1 genuinely new distinct capture | **changed** |
| per-capture path order reversed | unchanged |
| capture list order reversed | unchanged |

The first row is the failure that broke both audits and it is closed. **The
second row is the one that makes the fix worth having**: a binding that stopped
noticing everything would have been worse than the byte pin. It still detects a
real corpus change.

The identity reproduces at 47,799 bytes / `c1c75743fcdb06a3...`, and both audits
reproduce: IRQ at 16,818 bytes / `48c389e4e9afe369...` and PDIC at 15,563 bytes
/ `7744d9e7c5d76148...`. P3.19 is back to a single failure, the known raw-first
receipt population identity from parallel uncommitted S20+ files.

The projection also fails closed on schema drift rather than silently projecting
a subset: `set(manifest) != MANIFEST_KEYS` and `set(capture) != CAPTURE_KEYS`
both raise, so adding or removing a census field aborts instead of quietly
changing what is bound.

### One thing to anticipate rather than a defect

The projection is still a pinned identity, and by design it changes when a
genuinely new distinct capture enters the corpus. The next legitimate growth of
this corpus is **a candidate boot capture** — which is the campaign's goal. When
that lands, the projection will change and both audit identities will need
re-pinning.

That is the intended semantics working, not a regression, and it is worth
writing down now so that whoever sees those two audits go red on the day a
candidate finally retains evidence recognises it as the success signal rather
than as breakage.

## The Carrier's two new emitters convert a load into a rebuild

The Envelope-v5 Carrier is implemented and its receipt reproduces at 11,647
bytes / `05ee3385c8c80010...`. This section reviews the one consequence its own
limits statement points at but does not cost.

### What the unit did, and it is not what this report expected

This report concluded that W5, the parent `0x23` bit-3 readback, had no read
path: no log emitter, no sysfs, no debugfs, no regmap surface. That was correct
about the **stock** driver and it stopped there. The unit's answer is to patch
the driver source, which is a route this report did not consider:

- `max77705_muic_detect_dev` is patched to print all five status bytes it
  already holds, closing the "three bytes, not five" gap at **zero extra I2C
  transactions**. That part is elegant.
- `max77705_usbc_umask_irq` is patched to check the existing `0x23` write, add
  one readback, and emit `P319_INTSRC_MASK:0x%02x`.

The unit is explicit that this is source only: "No new `pdic_max77705.ko`, boot
image, AP archive, manifest, or candidate build exists", and "a future candidate
build must compile and bind the materialized driver source before any
qualification can claim that the new emitters execute." That statement is
correct and was made before this review.

### What it costs, which the statement does not say

Compiling that source produces a **rebuilt vendor module**, and the campaign has
never shipped one. Today it *loads Samsung's own* `pdic_max77705.ko`, bound to
the exact `vendor_dlkm` bytes. Replacing it changes the problem class.

The shipped module declares

```
vermagic=5.10.226-android12-9-gki-30958166-abS906NKSS7FYG8
         SMP preempt mod_unload modversions aarch64
```

and the loader used by the candidate is `sys_finit_module(fd, "", 0)` — **flags
zero**, so vermagic and `modversions` CRCs are both enforced. A rebuilt module
must reproduce that vermagic exactly and satisfy the CRCs for every symbol it
imports; the campaign's own map records **22,131 consumer-side symbol/CRC rows
across 4,060 unique symbols** for the 441 shipped modules.

The campaign's kernel-rebuild audit already records the gate this sits behind:
"These CRCs prove only what shipped modules **require**. Provider compatibility
is unproved until the completed Full-LTO `vmlinux.symvers` and rebuilt module
set are compared against them" — alongside `stock_equivalent_claim=false`.

And there is direct evidence the current build environment does not yet
reproduce the vendor vermagic. The campaign's own module,
`s22plus_dwc3_event_latch.ko`, carries

```
vermagic=5.10.226-android12-9-30958166-abS906NKSS7FYG8 ...
```

— the same release **without `-gki-`** — built from a tree whose
`CONFIG_LOCALVERSION` is empty. Two different vermagic strings are in play, the
loader compares them exactly, and nothing on this host shows the campaign
producing the `-gki-` form.

### What that means for sequencing

The two new emitters are not a two-line patch in cost. They move
`pdic_max77705` from *the vendor's byte, loaded* to *our byte, rebuilt*, which
pulls in the Full-LTO provider-compatibility gate the campaign has explicitly
not passed and which its own posture excludes ("no kernel rebuild").

This does not argue against the patches. It argues about **when**. W4's missing
two bytes and W5 both ride on that rebuild; W1 through W4a-as-three-bytes and
W4b do not — they parse lines the shipped module already emits.

So the split this report recommended earlier survives the Carrier unit and gets
sharper. A first candidate carrying only the emitters that already exist needs
no rebuilt vendor module at all. The patched-source witnesses belong to a second
candidate, behind the provider-compatibility gate, and costing them as "compile
the source" understates them by that entire gate.

### One thing this makes newly urgent

If a rebuilt vendor module is ever required, the vermagic question stops being
academic. It is also worth noting that **whether any shipped vendor module has
ever loaded on a candidate is still unproven** — that is precisely what W1, the
per-module `finit_module` return, exists to answer, and it is the cheapest
witness in the set.

## A withdrawn vermagic claim, and a config that belongs to a different build

### First, the withdrawal

The preceding section argued that a rebuilt `pdic_max77705.ko` "must reproduce
that vermagic exactly", and rested part of that on the campaign's own
`s22plus_dwc3_event_latch.ko` carrying the release **without `-gki-`**.

**That argument is withdrawn.** The loader this campaign runs does not compare
the release token when the module carries CRCs:

```c
/* First part is kernel version, which we ignore if module has crcs. */
static inline int same_magic(const char *amagic, const char *bmagic,
			     bool has_crcs)
{
	if (has_crcs) {
		amagic += strcspn(amagic, " ");
		bmagic += strcspn(bmagic, " ");
	}
	return strcmp(amagic, bmagic) == 0;
}
```

`common/kernel/module.c:1395-1404`, in this campaign's own materialized tree.
`has_crcs` is `info->index.vers`, the module's `__versions` section, which every
`modversions` module has. `-gki-` versus no `-gki-` lives entirely inside the
skipped token. The observation was real; the conclusion drawn from it was not.

What survives the withdrawal is the half that was always the expensive half: the
suffix must still match exactly, and **CRC provider closure remains mandatory**.
A rebuild still owes the provider-compatibility gate. The sequencing
recommendation is unchanged, and this unit acted on it — it reached the same
witnesses through stock emitters and rebuilt nothing.

### Second, what the audit certifies is not what it audits

The auditor pins the flashed Image
`71f573eb...` and takes its section authority, symbol CRCs and module
configuration from `s22plus_fyg8_p310/immutable-a-v6/`. Those are two different
kernel binaries.

That directory also contains an `Image`,
`9c2115bb8cd396d0396490c737b39713abdeac311d2ba49679a1bacd9a41e609`. Against the
flashed Image it differs in **565 of 633 64 KiB blocks, 8,153,294 bytes, 19.65%
of the file**. Measured against the audited `vmlinux`, the export value fields
resolve the question outright:

| Image | `__ksymtab` value diffs | `__ksymtab_gpl` value diffs |
| --- | --- | --- |
| `immutable-a-v6/Image` | **0** | **0** |
| `fixed-p310-ready-1/Image` (flashed) | 31 | 28 |

The audited `vmlinux` is the sibling Image's, exactly. The report's "only the
expected 31/28 value-field differences" is not a vmlinux-versus-Image format
quirk. It is the signature of a different link, and the 59 symbols are all data
objects displaced by exactly 128 or 160 bytes — `param_ops_*`, `_ctype`,
`kmalloc_caches`, `clk_divider_ops`, `crypto_ft_tab`. `System.map` agrees with
`vmlinux`, not with the flashed Image.

The cause is recoverable, because the flashed Image carries its own
configuration: it has one `IKCFG_ST` block. Decompressed it is 185,508 bytes,
the same length as the pinned `.config`, and differs from it in **exactly two
non-comment lines**:

```
flashed Image  CONFIG_S22PLUS_FYG8_E1_RUN_ID_HEX="b9cc424d0d184f5accbce94a844e817d"
pinned .config CONFIG_S22PLUS_FYG8_E1_RUN_ID_HEX="a06fa64d1ce9442ab427e01999f08c0c"
```

plus the matching `E1_UNSAT_TAG_HEX`. Two compiled-in string constants of
different content, and the address churn follows from them.

This is an identity error, not a physics error. The auditor's own
`RUN_ID = b9cc424d0d184f5accbce94a844e817d` is the **flashed** Image's run
identity, while `CONFIG_IDENTITY` pins a config file whose own recorded run
identity is `a06fa64d...` — a different candidate run. A campaign with a
no-replay rule and per-run identity should not certify one run's module lane
from another run's config, however similar the two builds are.

### Third, every conclusion survives, by a route the auditor did not take

Re-derived from the flashed Image alone:

- its vermagic is
  `5.10.226-android12-9-30958166-abS906NKSS7FYG8 SMP preempt mod_unload modversions aarch64`,
  so the suffix equals `STOCK_SUFFIX` exactly;
- its embedded config carries `CONFIG_MODVERSIONS=y`, `CONFIG_MODULE_SIG` unset,
  `CONFIG_MODULE_FORCE_LOAD` unset, `CONFIG_MODULE_REL_CRCS` absent;
- it contains no module-signature diagnostic string at all;
- `__kcrctab`, `__kcrctab_gpl` and `__ksymtab_strings` are byte-identical to the
  audited vmlinux, so the CRC values the closure consumes are untouched by the
  address churn. The `3,566 = 3,238 + 328` closure stands.

So the unit's headline result is correct. It is correct because CRCs are
type-derived and layout-independent, not because the audit established the
Image's provenance — and the audit's one address-sensitive check is the one it
absorbed into a pass constant.

### The fix is one function, and it points the right way

`STOCK_SUFFIX` and the module lane can both be **derived from the pinned Image**
instead of asserted beside it: read `IKCFG_ST`, decompress, read the config;
read the `vermagic` string. The Image is already hash-pinned, so nothing is
weakened. Two things change: `31/28` becomes `0/0` once the correct vmlinux is
bound, and the auditor stops holding a constant that only happens to be true.

That is the same direction as the manifest-coupling repair reviewed earlier in
this report — replace a coincidence with a derivation — and the same failure
shape as the `irq:350` constant this report has already had to withdraw once.

### Two objections raised and dropped

Recorded because they were checked, not because they bit.

- **GPL export split.** `_image_provider_map` merges `__ksymtab` and
  `__ksymtab_gpl` into one namespace, so a non-GPL module importing a GPL-only
  symbol would pass the audit and fail `resolve_symbol` with `-ENOENT`. All 73
  modules in the snapshot declare `license=GPL`. Inert today.
- **Symbol namespaces.** `verify_namespace_is_imported` is unmodelled. The whole
  export set carries only two non-empty namespaces,
  `VFS_internal_I_am_really_a_filesystem_and_am_NOT_a_driver` (116 symbols) and
  `CRYPTO_INTERNAL` (3). No vendor module in this plan is a filesystem or a
  crypto internal consumer. Inert today, cheap to add.

## The provenance repair holds, and its strongest fact is the one it does not claim

The repair removes the different-run `vmlinux`, `vmlinux.symvers` and `.config`
from ABI authority, derives the module lane from the flashed Image's own
`IKCFG_ST` block, binds the `b9cc424d...` run identity the auditor already
asserted, and replaces the `STOCK_SUFFIX` constant with a suffix read out of the
Image. `external_build_provenance` is recorded as `not_bound`, with no exact
vmlinux for this Image available. That is the correct answer to the finding: the
`0/0` this reviewer named as the repaired end state was **not** claimable, and it
was not claimed.

### Reproduced without the auditor

The Image was decoded again from scratch — locating the string blob from a known
export name and growing it, then walking PREL32 triples — with none of the
auditor's constants in the loop:

| quantity | this reviewer, from the raw Image | auditor |
| --- | --- | --- |
| exported providers | 2,851 + 4,371 = **7,222** | 7,222 |
| module `__versions` entries over 73 modules | **3,566** | 3,566 |
| entries with no Image provider | **328** | 328 |
| entries whose CRC equals the Image provider's | **3,238** | 3,238 |

The five section SHA-256 values agree with independent computation.

### The removed cross-check was replaced by a stronger one, and the report is silent about it

Before the repair, `image_provider_map == symvers_map` was the only thing that
validated the decode. Removing `symvers` removes that, and nothing in the unit
argues what took its place. Tested directly: rebuild the provider map with the
CRC table rotated by **one entry** and re-run the closure.

```
CRC agreement, correct decode : 3238
CRC agreement, 1-entry shift  :    0
```

The closure is self-validating. No misalignment of the name table against the
parallel CRC table survives it, because names and CRCs are joined by index and
3,238 independent CRC agreements have to hold simultaneously. It is also a
*better* check than the one it replaced: `symvers` came from the same build as
the map it certified, whereas these 3,238 agreements are between **Samsung's
shipped modules and this campaign's own kernel** — two unrelated producers.

The report gives `3,566` as a result. It is also the proof that the raw decode is
correct, and saying so retires the "authority removed, nothing put back"
objection permanently rather than leaving it open for the next reviewer.

### The one thing still inherited from the removed authority

`IMAGE_SECTION_LAYOUT` is five bare offset literals. They are the removed
vmlinux's section offsets minus the `0x10000` file displacement — `35,693,760`
is `0x221A4C0 - 0x10000`. The repair removed the authority and kept its output.
The per-section SHA-256 adds nothing here, because the Image is already
hash-pinned, so any section byte change fails earlier.

They are correct, and they are also derivable, which is the point. Measured:

- the five sections are **exactly contiguous** — all four inter-section gaps are
  zero, spanning `35,693,760` to `35,979,344`;
- both export tables have exactly as many entries as their CRC tables,
  2,851 and 4,371;
- the left edge is sharp: the 12 bytes before `__ksymtab` do not decode as an
  entry, and every one of the 2,851 entries inside does;
- the right edge is sharp: the 12 bytes after `__ksymtab_gpl` do not decode.

Asserting contiguity is one line and turns five independent literals into one
start offset plus four sizes, each of which the closure then checks. That is the
same direction as this repair itself: replace an asserted constant with a
derived one.

Neither point blocks the unit. The provenance defect recorded earlier is closed.

## What remains open

Four items this unit closed are not listed here; they have their own sections
and the ledger carries the order they were closed in. What is still open:

One further entry has been removed since: *the kernel-side MUIC notifier lines
in the corpus*. It was closed by the section immediately above rather than
struck through, because a closed entry left in this list understates the result
and the list is meant to be read as live.

This list was rewritten after the bootloader work landed. Its first entry used
to be *what the bootloader's `OP 0x06` writes to CONTROL1*, on the ground that
the MUIC driver sat in an inner volume whose layout was not yet decoded. That
entry is **closed**: the volume was decoded, `Muic.efi` disassembled, its whole
CONTROL1 vocabulary read off the jump table, and the normal boot shown to leave
`0x3f` COM_OPEN. Leaving it listed would have understated the unit's own result,
which is the reason this section is restated rather than appended to.

- What `ccic_set_sink`'s opcode `0x5E` actually programs. The command is
  identified, reaches the chip, and is answered, but it is named nowhere the
  kernel can see. This is no longer on the critical path: download mode
  enumerates with the sink left at the value XBL wrote, so the gap is a gap in
  understanding rather than a blocker.
- Whether what the bootloader programs into the DWC3 core differs elsewhere from
  what the kernel programs. The role selection itself is now read from the
  registers, but the rest of the init sequence — the `0xc100`, `0xc200` and
  `0xc700` block writes around it — has not been compared against the kernel's.
- Images never opened: `xbl_s.melf` (three LZMA candidates inside),
  `devcfg.mbn`, `tz.mbn`, `hypvm.mbn`, and the CP (68 MB) and CSC (24 MB)
  volumes. Nothing here suggests they carry MUIC code; they are listed so that
  "the bootloader was enumerated" is not read as "every image was opened".
- Whether adding the ADSP remoteproc driver to the plan is sufficient, or
  whether the protection domain `msm/adsp/charger_pd` also needs a userspace
  registrar that a candidate cannot provide.
- Why the candidate's own read of `/sys/module/eud/parameters/enable` failed,
  which is what `0x6010` reports and is a candidate-side question. A host D0 read
  of the same file would not answer it.
- Whether the water branch ever fired on candidates whose plans included
  `pdic_max77705`. Those runs preserved neither a successful module result nor
  the MUIC sequence, so the test cannot be run retrospectively and only a new
  run with the five witnesses above can answer it.
- **What sets `BC_CTRL1_NoAutoIBUS` and what it does.** The bit is retained
  across a reboot and no boot in the corpus writes `BCCTRL1`, so it is set by
  something outside these 268 segments — a download session or the kernel — and
  this unit did not identify which. Its effect on the analog path is also
  unread; the name is from the MUIC header, the semantics are not.
- **The remaining candidate-side execution boundary.** The shipped DT, parent
  GPIO, MFD child publication, PDIC nested offsets and stock queue-to-I2C path
  are closed above. What remains unproved is whether a candidate obtained
  successful controller/MFD/PDIC insertion results, bound `max77705-usbc`,
  completed the initial five-byte classification and separately read back the
  parent USBC source unmasked. The stock positive control defines those four
  witnesses but cannot supply candidate-side facts.

## Evidence

Staged surfaces are under `workspace/private/p319_stock_userspace/`, which is
gitignored and holds firmware-derived material that must not be committed.
Mount points are read-only loop mounts under `/mnt/android-lab-logical/`.

The direct-ELF guard audit is
`workspace/public/src/scripts/analysis/s22plus_fyg8_p319_pdic_muic_guard_audit.py`.
Its nine exact module/source inputs are preserved mode `0400`, link count one
under the `20260820-02/inputs/` private output.  The canonical result is 5160
bytes, SHA-256
`1ae6edcd80a919cb513c230d3d1a0bc9a7131880e5e5461e42d0e55f6e6d9d3c`,
mode `0400`, link count one; both the output root and input directory are mode
`0700`, and a fresh `--audit-only` encoding is byte-identical.

The initial `20260820-01` result, 5160 bytes/SHA-256
`fc8b107ad974f2006cef5c1171f5183de9415001fa4c8fcfedb84129bd245dbc`,
is preserved mode `0400`, link count one rather than overwritten.  Its file
evidence was sound, but the intermediate output directory inherited ambient
umask and was created mode `0775`; the successor makes exact `0700` directory
publication part of the producer and tests it.  Twelve focused tests execute
the real private inputs, preserve that predecessor and reject CDP dispatch,
AP/CP polarity, COM_USB value, water-guard polarity, additional water writer,
common-MUIC default/formula and source-writer mutations.  This evidence is H0
only and creates no device or live authority.

The reviewed V2 DT/nested-IRQ predecessor is
`workspace/public/src/scripts/analysis/s22plus_fyg8_p319_max77705_irq_dt_audit.py`,
formerly 59974 bytes/SHA-256 `25ed0fa7...`. Twelve exact source/module/manifest inputs
are snapshotted mode `0400`, link count one under the private mode-`0700` input
directory; the 8 MiB stock DTBO and all current size-matching files under
`workspace/private` are stable-read, deduplicated, and compared to the complete
manifest path/hash inventory. Its canonical `20260820-05`
result is 15697 bytes/SHA-256
`5c84bfc5fe9307a856f4bf74dba2751be3f3bf575936bb33b6b3a242cbb12a3a`,
mode `0400`, link count one, under a mode-`0700` output root. Fourteen focused
tests execute the exact population, accept a synthetic coherent change of
absolute base, and reject relative-offset, selected-DT GPIO, parent action,
nested-dispatch, unmask, CHGT, AP/`06 09` multiplicity, injected I2C-failure
and source bulk-write/unmask mutations. A fresh `--audit-only` encoding is
byte-identical. This result is H0 only and creates no device or live authority.

Independent review regenerated the current receipt byte-for-byte and matched
every derived count and per-capture distribution. It also verified the direct
base source, both base-free differences, live manifest re-enumeration, and the
absence of the old absolute-number acceptance literals. Its scoped verdict is
`PASS_GO_P319_MAX77705_IRQ_DT_CORPUS_AUDIT_V2_H0_CAPABILITY`; this qualifies
only the H0 audit and creates no device or live authority.

Four predecessors remain preserved rather than overwritten. `20260820-01` is
8187 bytes/SHA-256 `25be452a...`; `20260820-02` is 8370 bytes/SHA-256
`6c3d25a7...`; `20260820-03` is 8545 bytes/SHA-256 `bc193d7e...`; all are mode
`0400`, link count one, and `20260820-04` is 15697 bytes/SHA-256 `fef955a4...`
with the same metadata. The second added direct FDT phandle resolution. The
third corrected the pre-write dump boundary. The fourth removed absolute IRQ,
single-capture and ordered-token assumptions. The fifth additionally proved
the then-current manifest equalled the live private corpus. It remains reviewed
historical evidence; the V3 semantic successor above is the current
deterministic regeneration and awaits its own independent review.
