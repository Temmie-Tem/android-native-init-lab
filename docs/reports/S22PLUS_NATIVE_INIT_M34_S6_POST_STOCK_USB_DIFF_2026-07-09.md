# S22+ M34 S6 Post-Live Stock USB Diff

Date: 2026-07-09 KST / 2026-07-08 UTC

Status: HOST/READ-ONLY COMPLETE. No live flash is authorized by this report.

## Boundary

This unit follows the consumed M34 S6 live gate. S6 survived the full 90 second
park window but did not enumerate any host USB endpoint. Operator observation
after the window: no sustained boot loop, then RDX/PMIC, then manual Download
mode for rollback. The rollback returned Android/Magisk baseline cleanly.

The goal here is not to authorize S7. It is to compare S6 against the stock
Android USB stack and retire the already-tested role/speed/softdep explanation.

## Evidence

Fresh rooted Android read-only capture:

```text
workspace/private/runs/s22plus_stock_usb_state_post_s6_20260708T215851Z/
```

The raw capture contains the device serial in private scratch data. This report
intentionally redacts it.

Relevant files:

- `device/getprop_usb.txt`
- `device/configfs_key_values.txt`
- `device/configfs_ls_key_dirs.txt`
- `device/init.qcom.usb.rc`
- `device/init.qcom.usb.sh`
- `device/proc_modules_usb_filtered.txt`
- `device/ps_usb_filtered.txt`
- `device/mount_usb_filtered.txt`
- `device/udc_attrs.txt`
- `device/ssusb_attrs.txt`
- `host/lsusb_04e8_6860_v.txt`
- `host/usb_devices.txt`

Stock firmware extract also confirms the relevant vendor modules and aliases:

- `usb_f_conn_gadget.ko`
- `usb_f_ss_acm.ko`
- `usb_f_ss_mon_gadget.ko`
- `modules.alias`: `usbfunc:conn_gadget`, `usbfunc:ss_acm`,
  `usbfunc:ss_mon`
- `modules.softdep`: `dwc3_msm pre: phy-generic phy-msm-snps-hs
  phy-msm-snps-eusb2 phy-msm-ssusb-qmp eud post: ucsi_glink`

The current extracted firmware set does not include the vendor partition rc
tree. The live rooted `/vendor/etc/init/hw/init.qcom.usb.rc` pull is therefore
the authoritative stock runtime choreography for this report.

## Stock Runtime USB State

Android is boot-complete on `SM-S906N/g0q/S906NKSS7FYG8` with orange verified
boot. Stock USB properties:

```text
sys.usb.config     = mtp,conn_gadget,adb
sys.usb.state      = mtp,conn_gadget,adb
sys.usb.configfs   = 1
sys.usb.configured = configured
sys.usb.controller = a600000.dwc3
sys.usb.ffs.ready  = 1
vendor.usb.configfs       = 1
vendor.usb.use_ffs_mtp    = 1
vendor.usb.use_gadget_hal = 0
```

Stock configfs values:

```text
UDC              = a600000.dwc3
max_speed        = super-speed-plus
idVendor         = 0x04e8
idProduct        = 0x6860
bcdUSB           = 0x0320
bcdDevice        = 0x0504
bDeviceClass     = 0x00
bDeviceSubClass  = 0x00
bDeviceProtocol  = 0x00
os_desc/use      = 1
os_desc/b_vendor_code = 0x01
os_desc/qw_sign       = MSFT100
manufacturer     = SAMSUNG
product          = SAMSUNG_Android
configuration    = mtp_conn_adb
```

Active stock config links five functions:

```text
configs/b.1/f1 -> functions/ffs.mtp
configs/b.1/f2 -> functions/ss_acm.0
configs/b.1/f3 -> functions/conn_gadget.0
configs/b.1/f4 -> functions/ffs.adb
configs/b.1/f5 -> functions/ss_mon.mtp
os_desc/b.1    -> configs/b.1
```

Host `lsusb -d 04e8:6860 -v` sees a SuperSpeed Samsung composite:

```text
bcdUSB       3.20
bDeviceClass 0
bcdDevice    5.04
bNumInterfaces 5
iConfiguration mtp_conn_adb
Interface 0: MTP
Interface 1/2: CDC ACM + CDC data, driver cdc_acm
Interface 3: conn_gadget, vendor-specific protocol 3
Interface 4: ADB
```

Stock userspace dependencies are active:

```text
android.hardware.usb@1.3-service.coral
connfwexe
adbd
ss_conn_daemon2

configfs mounted at /config
functionfs mounted at /dev/usb-ffs/adb
functionfs mounted at /dev/usb-ffs/mtp
functionfs mounted at /dev/usb-ffs/ptp
```

UDC/controller state:

```text
/sys/class/udc/a600000.dwc3/current_speed = super-speed
/sys/class/udc/a600000.dwc3/state         = configured
/sys/class/udc/a600000.dwc3/function      = g1
/sys/devices/platform/soc/a600000.ssusb/mode  = peripheral
/sys/devices/platform/soc/a600000.ssusb/speed = super-speed
```

## Stock Init Choreography

`init.qcom.usb.rc` first creates a broad function pool in post-fs, including:

```text
ffs.adb
ffs.mtp
ffs.ptp
ss_acm.0
conn_gadget.0
ss_mon.mtp
```

It also writes:

```text
g1/os_desc/use 1
g1/bcdDevice 0x504
g1/os_desc/b_vendor_code 0x1
g1/os_desc/qw_sign MSFT100
```

The active stock `mtp,conn_gadget,adb` binding is gated on FunctionFS readiness:

```text
on property:sys.usb.ffs.ready=1 &&
   property:sys.usb.config=mtp,conn_gadget,adb &&
   property:sys.usb.configfs=1
```

Only then does stock start `ss_conn_daemon2_service`, relink the five functions,
write `/sys/class/android_usb/f_conn_gadget/bInterfaceProtocol 3`, and finally
write `UDC=${sys.usb.controller}`.

## S6 Native-Init USB State

S6 intentionally tested a narrower runtime-gadget:

```text
functions/ss_acm.0 only
configs/b.1/f1 -> functions/ss_acm.0
bcdUSB          = 0x0200
bcdDevice       = 0x0034
bDeviceClass    = 0xef
bDeviceSubClass = 0x02
bDeviceProtocol = 0x01
manufacturer    = Codex
product         = S22 Native Init M34 Runtime Split
configuration   = acm
os_desc/use     = 1
UDC             = a600000.dwc3
ssusb/mode      = peripheral
```

S6 removed the previous high-speed forcing and restored QMP/EUD/UCSI softdep
parity:

```text
phy-msm-ssusb-qmp.ko
eud.ko
ucsi_glink.ko
```

But the S6 module list still did not include `usb_f_conn_gadget.ko`, and S6 did
not create or bind:

```text
ffs.mtp
conn_gadget.0
ffs.adb
ss_mon.mtp
os_desc/b.1
os_desc/b_vendor_code
os_desc/qw_sign
```

S6 also did not mount FunctionFS or start the stock USB userspace daemons.

Post-diff TypeC follow-up found a second stock gap. S6 already had
`common_muic.ko`, `pdic_notifier_module.ko`, `usb_typec_manager.ko`,
`redriver.ko`, `if_cb_manager.ko`, `pmic_glink.ko`, and `ucsi_glink.ko`, but it
did not include the stock max77705/altmode session-producer modules:

```text
qcom_i2c_pmic.ko
mfd_max77705.ko
max77705_charger.ko
max77705-fuelgauge.ko
pdic_max77705.ko
charger-ulog-glink.ko
altmode-glink.ko
```

The rooted stock TypeC read shows `/sys/class/typec/port0` backed by
`max77705-usbc`, a present `port0-partner`, and active roles:

```text
data_role  = host [device]
power_role = source [sink]
port_type  = [dual] source sink
```

That means `ssusb/mode=peripheral` is not sufficient by itself; stock also has a
USB-C peripheral session produced by the max77705/PDIC/altmode chain.

## Interpretation

S6 consumed the role/speed/softdep hypothesis:

1. It kept the real `ssusb/mode=peripheral` role lever.
2. It stopped forcing `g1/max_speed=high-speed` and `ssusb/speed=high-speed`.
3. It restored the stock `dwc3_msm` softdep path through QMP/EUD/UCSI.
4. It survived the observation window but still exposed no host USB device.

Therefore the best current explanation is not "missing peripheral mode" or
"wrong USB2/USB3 speed". The remaining high-signal gaps are:

- native init has not proven the stock max77705/PDIC/altmode session producer
  chain before UDC bind; and
- native init is not reproducing Samsung's actual bound composite or the
  FunctionFS/userspace readiness conditions that stock uses before UDC bind.

The important correction to the earlier M35 report is:

- S4/S5/S6 already tested the stock `ssusb` role lever path.
- S6 already removed high-speed forcing and restored QMP/EUD/UCSI softdep.
- Since S6 still produced no USB, descriptor/composition and FunctionFS/daemon
  parity are no longer a follow-up detail; they are now the frontier.

## S7 Direction

Do not rush to another live flash. The next unit should be host-only first:

1. First build/design S7A from the S6 base to restore the missing stock
   max77705/PDIC/altmode session producer modules and add readback markers for
   `/sys/class/typec/port0`, `port0-partner`, `data_role`, `power_role`,
   `ssusb/mode`, `ssusb/speed`, and UDC state before and after bind.
2. Keep `soft_connect` disabled. S5 already showed that forcing pullup without
   a valid session can fall into Samsung upload/download.
3. Then build/design the stock-composite delta: include `usb_f_conn_gadget.ko`
   in the module closure and create the non-FunctionFS stock companion
   functions `ss_acm.0`, `conn_gadget.0`, and `ss_mon.mtp`.
4. Match stock descriptors in that composite step:
   `bcdUSB=0x0320`, `bcdDevice=0x0504`, device class/subclass/protocol all
   zero, `SAMSUNG` / `SAMSUNG_Android`, `mtp_conn_adb`,
   `os_desc/b_vendor_code=0x01`, `os_desc/qw_sign=MSFT100`, and
   `os_desc/b.1 -> configs/b.1`.
5. Decide explicitly whether to include `ffs.mtp` and `ffs.adb`.

The FunctionFS point is the sharp edge:

- Linking `ffs.mtp` or `ffs.adb` without userspace descriptors can block or fail
  UDC binding.
- Omitting them means the interface numbering will not match stock and may not
  reproduce the exact ACM IAD placement.
- Starting stock `adbd`, MTP, or `ss_conn_daemon2` from direct native init is a
  larger step and should not be hidden inside a "descriptor polish" candidate.

Recommended split:

- S7A host-build/design: restore the missing stock session-producer modules and
  instrument TypeC/session readback; no `soft_connect`.
- S7B host-build/design: add `usb_f_conn_gadget.ko` plus stock descriptor and
  non-FunctionFS companion-function parity.
- S7C host-build/design: true stock composition with FunctionFS mounts and
  minimal userspace readiness, only after S7A/S7B are understood.

Any S7 live gate needs a fresh SHA-pinned active `AGENTS.md` exception and
explicit operator approval. This report authorizes no boot flash, no DTBO,
no vendor_boot, no vbmeta/recovery/non-boot partition write, no raw host `dd`,
no fastboot, no Magisk module, no EUD write, no sysrq panic, and no A90 action.
