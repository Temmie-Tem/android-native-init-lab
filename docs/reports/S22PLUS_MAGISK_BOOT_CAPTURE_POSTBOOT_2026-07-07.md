# S22+ Magisk Boot-Capture Post-Boot Snapshot - 2026-07-07

## Scope

Read-only rooted Android capture for the S22+ native-init observability pivot.
This unit collects the real Android runtime state that future native PID1 work
must reproduce or deliberately replace:

- module inventory and `modules.load` / `modules.dep` metadata;
- current loaded module set;
- dmesg key lines for USB/display/module topics;
- USB gadget/configfs state, including ADB and NCM functions;
- display/DRM/KGSL surface state;
- boot and service properties.

No reboot, Odin transfer, partition write, Magisk module, service.d script,
filesystem mutation, or native-init candidate was used in this unit.

## Preconditions

The previous unit restored the measurement environment:

- `docs/reports/S22PLUS_TWRP_MAGISK_BOOT_CAPTURE_RESTORE_LIVE_2026-07-07.md`
- root proof: `uid=0(root) ... context=u:r:magisk:s0`

## Collector

Added:

```text
workspace/public/src/scripts/revalidation/s22plus_magisk_boot_capture_collect.py
```

Validation:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/s22plus_magisk_boot_capture_collect.py
```

Result: pass.

Live command:

```text
python3 workspace/public/src/scripts/revalidation/s22plus_magisk_boot_capture_collect.py
```

Private raw run:

```text
workspace/private/runs/s22plus_magisk_boot_capture_20260706T172546Z
```

Raw logs are private because they can contain serials, USB addresses, MACs,
kernel command-line details, service state, and other device identifiers.

## Device / Root Proof

Public redacted summary:

```text
model=SM-S906N
device=g0q
build=S906NKSS7FYG8
bootloader=S906NKSS7FYG8
verifiedbootstate=orange
boot_completed=1
root_uid0=true
magisk_su=true
```

## Module State

Captured:

```text
module_file_count=356
loaded_module_count=482
modules_load_count=712
```

`modules.load` first entries:

```text
1  msm_sysstats.ko
2  zsmalloc.ko
3  lzo.ko
4  lzo-rle.ko
5  ssg.ko
6  blk-sec-stats.ko
7  msm_show_resume_irq.ko
8  mhi_cntrl_qcom.ko
9  mhi_dev_uci.ko
10 mhi_dev_netdev.ko
11 mhi_dev_dtr.ko
12 mhi.ko
13 phy-qcom-ufs-qmp-v4-lahaina.ko
14 phy-qcom-ufs-qmp-v4-parrot.ko
15 phy-qcom-ufs-qmp-v4-anarok.ko
16 phy-qcom-ufs-qmp-v3.ko
17 phy-qcom-ufs-qmp-14nm.ko
18 pinctrl-spmi-mpp.ko
19 sec-pinmux.ko
20 pwm-qti-lpg.ko
21 pci-msm-drv.ko
22 lcd.ko
23 camcc-waipio.ko
24 camcc-diwali.ko
25 debugcc-diwali.ko
26 videocc-waipio.ko
27 gpucc-waipio.ko
```

Selected `modules.load` anchor positions:

```text
0012 mhi.ko
0022 lcd.ko
0027 gpucc-waipio.ko
0076 icnss2.ko
0096 msm_kgsl.ko
0108 dhd.ko
0109 cnss2.ko
0122 dwc3-msm.ko
0125 usb_f_diag.ko
0126 usb_f_qdss.ko
0129 usb_f_gsi.ko
0159 bcm4389.ko
0179 ipa_fmwk.ko
0311 adsp_loader_dlkm.ko
0339 ipam.ko
0352 msm_drm.ko
```

Runtime `/proc/modules` contains the corresponding loaded anchors, including:

```text
msm_drm
dwc3_msm
usb_f_gsi
usb_f_qdss
usb_f_diag
usb_f_ss_acm
msm_kgsl
gpucc_waipio
dispcc_waipio
dhd
bcm4389
mhi
ipa_fmwk
ipam
```

Interpretation:

- S22+ native PID1 cannot assume A90-style built-in USB/display availability.
- `modules.load` is a usable first ordering seed, but it is not by itself the
  complete Android boot recipe; Android's live loaded set is larger and includes
  runtime/config dependent modules.
- `/proc/modules` order is treated as runtime inventory, not authoritative load
  timestamp order.

## USB / Observation Channel

USB/configfs state is present and rich enough to guide native observability work:

```text
gadget=/config/usb_gadget/g1
adb_present=true
ncm_present=true
functions include:
  ffs.adb
  ncm.0
  rndis.rndis
  gsi.rmnet
  gsi.rndis
  ss_acm.0
  diag.diag
  qdss.qdss
  mass_storage.0
  uac2.0
  uvc.0
```

dmesg key-line counts from the captured ring:

```text
usb=222
display=16
module=4
pstore=0
```

Interpretation:

- ADB and NCM are not speculative; both exist in the Android configfs gadget.
- A future observable native init should prioritize the minimal module/configfs
  path for `dwc3-msm`, `usb_f_*`, FunctionFS ADB, and optionally NCM.
- The current dmesg ring is useful for state validation but did not preserve a
  full very-early boot timeline.

## Display / GPU State

Captured display nodes:

```text
/sys/class/drm/card0
/sys/class/drm/card0-DSI-1
/sys/class/drm/card0-DP-1
/sys/class/drm/card0-Virtual-1
/sys/class/drm/renderD128
/sys/class/backlight/panel
/sys/class/backlight/panel0-backlight
/dev/dri/card0
/dev/dri/renderD128
```

Android service state includes:

```text
SurfaceFlinger
SurfaceFlingerAIDL
display
gpu
graphicsstats
vendor.qti.hardware.display.config.IDisplayConfig/default
```

Interpretation:

- Display/KMS is up through the Qualcomm MDSS/DRM stack in Android.
- The minimum native first-light display path should not start by trying to
  own full Android HWC. Use DRM/KMS evidence as the lower-level anchor, then
  add panel/backlight handling only after USB observability exists.

## Limits

This unit is a post-boot rooted snapshot. It did not install a Magisk boot-time
measurement capsule, so it does not capture the full early boot timeline before
Android services and dmesg ring churn. The result is still enough to prove the
actual configured USB/display endpoints and to seed module ordering.

A stronger M1 capture can be done next with a temporary Magisk boot-time capsule
that writes private logs under `/data` during `post-fs-data` / `service.d`, then
auto-cleans. That requires a separate S22+ data-write/Magisk-capsule gate; it is
not covered by the TWRP+Magisk restore exception.

## Result

PASS: rooted Android boot-capture snapshot completed and produced concrete
native-init observability inputs. The next design step should build an
observable native-init plan around USB-first bring-up instead of another blind
first-light flash.
