# S22+ M34 S7 USB Session Producer Chain Stock Check

Date: 2026-07-09 KST / 2026-07-08 UTC

Status: HOST/READ-ONLY COMPLETE. No live flash is authorized by this report.

## Boundary

This report follows the consumed M34 S6 live gate and the post-S6 stock USB
diff. It narrows the next S7 host-build direction by checking what stock Android
uses to produce the USB-C peripheral session before the gadget can enumerate.

This was read-only against rooted stock Android except for a temporary script
under `/data/local/tmp`, created only to read root-owned sysfs paths and removed
immediately after capture. No partition, sysfs, configfs, module, reboot, or
flash write was performed.

Raw capture:

```text
workspace/private/runs/s22plus_stock_typec_session_post_s6_20260708T220931Z/typec_session.txt
```

The raw capture redacts the adb serial in its header.

## What S6 Actually Already Had

S6 did not completely omit the TypeC/PD support layer. Its module list includes:

```text
common_muic.ko
vbus_notifier.ko
pdic_notifier_module.ko
usb_typec_manager.ko
redriver.ko
if_cb_manager.ko
pmic_glink.ko
ucsi_glink.ko
```

So the next unit must not repeat the stale claim that all of those are missing.
The real stock-vs-S6 gap is narrower and more specific.

## Stock TypeC Session State

Stock Android exposes TypeC state through the max77705 USB-C device:

```text
/sys/class/typec/port0 ->
  ../../devices/platform/soc/994000.i2c/i2c-57/57-0066/max77705-usbc/typec/port0

/sys/class/typec/port0-partner ->
  ../../devices/platform/soc/994000.i2c/i2c-57/57-0066/max77705-usbc/typec/port0/port0-partner
```

The active role values with the host cable connected are:

```text
data_role  = host [device]
power_role = source [sink]
port_type  = [dual] source sink
```

This is the stock peripheral session: the phone is selected as USB data device
and power sink before the `04e8:6860` gadget is useful to the host.

The controller nodes confirm that the old Qualcomm-style manual session knobs
are not present:

```text
/sys/devices/platform/soc/a600000.ssusb/mode  = peripheral
/sys/devices/platform/soc/a600000.ssusb/speed = super-speed
/sys/devices/platform/soc/a600000.ssusb/b_sess           missing
/sys/devices/platform/soc/a600000.ssusb/id               missing
/sys/devices/platform/soc/a600000.ssusb/usb_data_enabled missing
```

So `ssusb/mode=peripheral` is necessary but not the whole story. The connected
cable/session comes from the max77705 TypeC/PD/MUIC path.

## Stock Modules Present

The rooted stock `/proc/modules` snapshot shows the additional producer chain
around the pieces S6 already had:

```text
max77705_charger
max77705_fuelgauge
mfd_max77705
pdic_max77705
qcom_i2c_pmic
altmode_glink
charger_ulog_glink
pmic_glink
ucsi_glink
common_muic
pdic_notifier_module
usb_typec_manager
redriver
if_cb_manager
dwc3_msm
usb_f_conn_gadget
usb_f_ss_acm
usb_f_ss_mon_gadget
```

S6 already had the lower/common notifier pieces but missed the stock
max77705/altmode producers and `usb_f_conn_gadget`.

Missing from S6, using module filenames from the firmware:

```text
qcom-i2c-pmic.ko
mfd_max77705.ko
max77705_charger.ko
max77705-fuelgauge.ko
pdic_max77705.ko
charger-ulog-glink.ko
altmode-glink.ko
usb_f_conn_gadget.ko
```

The firmware module database confirms these are stock modules. Examples:

```text
modules.load.recovery: altmode-glink.ko
modules.load.recovery: max77705_charger.ko
modules.load.recovery: max77705-fuelgauge.ko
modules.load.recovery: mfd_max77705.ko
modules.load.recovery: pdic_max77705.ko
modules.dep: /lib/modules/altmode-glink.ko: pmic_glink ...
modules.dep: /lib/modules/mfd_max77705.ko: abc usb_notify_layer sec_class
modules.dep: /lib/modules/pdic_max77705.ko: mfd_max77705 dwc3-msm ...
```

## Interpretation

S6 proved that these alone are not enough:

- `ssusb/mode=peripheral`
- no high-speed forcing
- QMP/EUD/UCSI softdep parity
- common MUIC/notifier/typec manager dependencies
- UDC bind to `a600000.dwc3`

The remaining session gap is that stock has a real `max77705-usbc` TypeC device
with an attached partner and selected `data_role=device`, while S6 has not yet
proven that the max77705 PDIC/charger/altmode producers are loaded and probed in
native init before UDC bind.

That gap can explain the S4/S6 symptom:

- the gadget can be constructed and the init can survive;
- but no valid connected-device session is produced for the host cable;
- therefore no `04e8:6860` endpoint appears.

It also fits S5:

- `soft_connect=connect` tried to force the pullup in an invalid or incomplete
  session state;
- the device then fell to Samsung `04e8:685d` upload/download.

This does not retire the stock-composite/FunctionFS gap. It means S7 should
avoid mixing too many untested deltas. Prove the session producer chain first,
then compose closer to stock.

## S7 Direction

Recommended split:

1. **S7A host-build/design:** restore the missing stock session-producer modules
   from `modules.load.recovery`/`modules.dep` order and add readback markers for:
   `/sys/class/typec/port0`, `port0-partner`, `data_role`, `power_role`,
   `ssusb/mode`, `ssusb/speed`, and UDC state before and after bind. Keep
   `soft_connect` disabled.
2. **S7B host-build/design:** after S7A statically validates, add
   `usb_f_conn_gadget.ko` plus stock descriptor/composite parity from the
   post-S6 stock USB diff. Keep FunctionFS links (`ffs.mtp`/`ffs.adb`) separate
   unless direct native init also mounts/populates FunctionFS or starts the
   needed stock userspace.

Candidate safety notes for S7A:

- Loading `max77705_*`, `pdic_*`, `qcom-i2c-pmic.ko` (stock module name
  `qcom_i2c_pmic`), and `altmode-glink` touches the external USB-C PD/charger
  path. That is stock module loading, but it is PMIC-adjacent and needs an
  explicit host-only design review before a live gate.
- The candidate must not write charge current, OTG/VBUS boost, regulator,
  GDSC, GPIO, display, or raw PMIC knobs.
- The only intended role action is to let stock drivers detect the attached
  host cable as data-device/power-sink. Do not use `soft_connect`.

Any live S7 attempt needs a fresh SHA-pinned active `AGENTS.md` exception and
explicit operator approval. This report authorizes no boot flash, DTBO,
vendor_boot, vbmeta, recovery, non-boot partition write, raw host `dd`,
fastboot, Magisk module, sysrq panic, EUD write, or A90 action.
