# S22+ M34 S5 USB Version And Stock Gap Recon

Date: 2026-07-09 KST

Status: HOST/READ-ONLY COMPLETE. No live flash is authorized by this report.

## Scope

This report re-reads the M34 S5 live logs, the post-rollback stock Android USB
capture, and the stock FYG8 firmware files to answer two questions:

- whether USB version/speed differences matter for the current S22+ native-init
  USB wall
- which next changes are cheap enough to implement without guessing at a large
  Android USB stack

No device writes, flash, reboot, EUD sysfs writes, or Magisk module actions were
performed in this unit.

## Inputs

- S5 live run:
  `workspace/private/runs/s22plus_m34_s5_soft_connect_live_gate_20260708T210259Z/`
- Post-S5 stock Android USB capture:
  `workspace/private/runs/s22plus_stock_usb_state_after_s5_20260708T210916Z/`
- Stock vendor ramdisk extract:
  `workspace/private/inputs/s22plus_firmware/S906NKSS7FYG8_SKC/extracted-images/ramdisk-list/vendor/extract/`
- Stock AP archive:
  `workspace/private/inputs/firmware/SAMFW.COM_SM-S906N_SKC_S906NKSS7FYG8_fac/AP_S906NKSS7FYG8_S906NKSS7FYG8_MQB99315260_REV00_user_low_ship_MULTI_CERT_meta_OS15.tar.md5`

Device serials are intentionally not copied into this report.

## USB Version Evidence

Stock Android is SuperSpeed, not a USB2-only gadget:

- host `lsusb -v`: negotiated SuperSpeed 5Gbps, `bcdUSB 3.20`
- host `lsusb -t`: Samsung `04e8:6860` appears on the USB3 tree at 5000M
- host `usb-devices`: device version 3.20, speed 5000, class 0 composite,
  5 interfaces
- stock function set: MTP, CDC ACM control/data, `conn_gadget`, ADB

M34 S2/S3/S4/S5 intentionally forced high-speed:

- configfs `g1/max_speed = high-speed`
- S4/S5 `ssusb/speed = high-speed`
- S4/S5 `ssusb/mode = peripheral`
- S5 additionally wrote `soft_connect = connect`

S5 did not expose the intended stock-like `04e8:6860` gadget. A later endpoint
did appear, but it was Samsung `04e8:685d`, not the intended Android composite:

- observe 013, elapsed 62.987 s: `04e8:685d`, product `MSM_UPLOAD`, USB2/480M,
  CDC-class interfaces, no host `cdc_acm` driver
- observe 015, elapsed 73.950 s: `04e8:685d`, product `SAMSUNG USB`,
  USB3/5000M, CDC-class interfaces, no host `cdc_acm` driver; `odin4 -l`
  detected the endpoint and rollback used it

Interpretation: the current wall is not only "ACM descriptor mismatch". The
candidate failed to produce Android `6860` and later fell into Samsung
upload/download `685d`. USB speed still matters because stock Android uses
SuperSpeed, and the S5 fallback endpoint reached both USB2 and USB3 paths.

## Firmware And Module Evidence

Stock vendor ramdisk `modules.softdep` contains:

```text
softdep dwc3_msm pre: phy-generic phy-msm-snps-hs phy-msm-snps-eusb2 phy-msm-ssusb-qmp eud post: ucsi_glink
```

Stock Android has `phy_msm_ssusb_qmp` and `eud` loaded. M34 S5 explicitly
excluded both `phy-msm-ssusb-qmp.ko` and `eud.ko`, and also excluded
`ucsi_glink.ko`. That was reasonable for the prior HS-only reset-bisection, but
it is now a high-signal mismatch for stock-compatible SuperSpeed controller
bring-up.

The stock AP contains `super.img.lz4` as an Android sparse super image:

```text
super.img.lz4 8875694170 bytes
```

The local `lz4` and `simg2img` tooling exists, but `lpunpack`/`lpdump` was not
present in the workspace or host PATH during this unit. Boot/vendor_boot/
recovery ramdisks do not carry the full Android USB init rc recipe; that likely
lives inside logical partitions in `super.img` (`vendor`, `product`,
`system_ext`, `odm`, or related partitions). Extracting those rc files is a
separate host-only prep unit, not a live gate.

## Cheap Candidate Classes

Ordered by expected information per implementation cost:

1. Improve host observation for all Samsung products.

   This is the cheapest and should happen regardless of the next candidate.
   The live helper summary currently keys hard on `04e8:6860`; it must also
   summarize `04e8:685d`, product strings, speed, interface classes, and driver
   binding for every `04e8:*` device in each snapshot.

2. Stop forcing USB2 high-speed.

   Small code change: remove `g1/max_speed=high-speed` and
   `ssusb/speed=high-speed`, or switch to stock-like SuperSpeed policy. This
   aligns with stock Android's observed 5000M/USB 3.20 path. Alone it may still
   fail if QMP/EUD are missing.

3. Add the stock `dwc3_msm` softdep pieces.

   Moderate code/build change: include `phy-msm-ssusb-qmp.ko`, `eud.ko`, and
   `ucsi_glink.ko` in the module closure around `dwc3-msm.ko`. Do not write EUD
   sysfs knobs. Treat this as stock module dependency parity, not a debug
   transport experiment.

4. Descriptor/string parity.

   Easy code change but weaker explanation for S5: use stock-like
   `bDeviceClass=0`, `bDeviceSubClass=0`, `bDeviceProtocol=0`,
   `bcdUSB=0x0320`, `bcdDevice=0x0504`, `SAMSUNG` / `SAMSUNG_Android`, and
   config string `mtp_conn_adb`. This is useful after the device can reliably
   enumerate as `6860`; it is less likely to fix a fall-through to `685d` by
   itself.

5. Add stock companion functions selectively.

   `conn_gadget.0` and `ss_mon.mtp` are plausible after descriptor parity.
   `ffs.mtp` and `ffs.adb` are not cheap because FunctionFS usually requires
   userspace descriptors/daemons before UDC bind.

6. Extract `super.img` logical partitions and read USB init rc.

   Host-only and safe, but heavier than code toggles. Needed before cloning the
   Android USB service sequence more faithfully.

## Recommended Next Unit

The cheapest observation fix was implemented in
`workspace/public/src/scripts/revalidation/s22plus_m34_s5_soft_connect_live_gate.py`:
future snapshots now summarize every Samsung `04e8:*` device from
`usb-devices`, including product ID, product string, speed, interface classes,
drivers, and an explicit `samsung_upload_download_present` flag for `685d` /
`MSM_UPLOAD` / `SAMSUNG USB` endpoints.

Validation:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/revalidation/s22plus_m34_s5_soft_connect_live_gate.py
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest tests.test_s22plus_m34_s5_soft_connect_live_gate
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/s22plus_m34_s5_soft_connect_live_gate.py --offline-check
```

Do not flash another candidate yet. The next bounded unit should be host-only:

- prepare an S6 design that combines the smallest stock-controller deltas:
  remove HS forcing and add QMP/EUD/ucsi softdep parity
- separately prepare the super extraction path to recover `init.qcom.usb.rc` /
  Samsung USB rc logic before descriptor or companion-function cloning

The next live candidate needs a fresh SHA-pinned `AGENTS.md` exception. This
report authorizes no live flash.
