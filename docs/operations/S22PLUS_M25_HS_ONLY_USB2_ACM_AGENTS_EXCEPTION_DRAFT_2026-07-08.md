# S22+ M25 HS-Only USB2 ACM AGENTS Exception Draft (2026-07-08)

This document is inert until copied into `AGENTS.md`.

Scope: one bounded attended S22+ M25 HS-only USB2 ACM native-init boot+DTBO
run on `SM-S906N/g0q/S906NKSS7FYG8`, followed by rollback to the pinned
Magisk boot baseline and stock DTBO.

Helper:

```text
workspace/public/src/scripts/revalidation/s22plus_m25_hs_only_usb2_acm_live_gate.py
```

Ack tokens:

```text
S22PLUS-M25-HS-ONLY-USB2-ACM-LIVE-GATE
S22PLUS-M25-HS-ONLY-ROLLBACK-FROM-DOWNLOAD
S22PLUS-M25-RESTORE-STOCK-DTBO
```

Pinned candidate and rollback artifacts:

```text
M25 boot AP.tar.md5 SHA256       7f89cfb8ff188190d1d161aee97e3edec2730bfc46efca9df37f2035f7206805
M25 boot.img SHA256             0ace02ff82be1cb7473879ff52f1c9e8d1491edaa3d9a88b829f901b2c86559f
M25 /init SHA256                cc03d95f06b851717d3ccb4fc32fbecac3adfe7109c1a68454f846e3014ecf75
M25 module list SHA256          00607484b7b777ee5cb54d7657f0cb554b9b66c42fec0e414d0544c0735d6496
M25 generated source SHA256     22350e7de748cf3a2f47236ef984bb224df58ffa7664ced811151c9db189562f
M25 vendor DTB SHA256           2cd64d43a4f6b89a7c5523f3ef73fbb84dcad92c6d857e649cd1f0baa7c0080e
M25 DTBO AP.tar.md5 SHA256      35afd774444066fd8e2ffe831da11dd73ee47dce3bdd5b1e37675f82344e56b6
M25 patched DTBO raw SHA256     8962cbbded722c85dbdebfbdc2eba5476b9a64e2a2933888b81f947159eddc17
M25 stock DTBO rollback AP SHA256 6f397421bee84f4ea0c80a8519be0f6f6af84119794970e8a1faaa05f261caaa
known Magisk boot SHA256        2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
stock DTBO raw SHA256           97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c
```

The boot AP must contain exactly one `boot.img.lz4` member. The DTBO candidate
AP and stock DTBO rollback AP must each contain exactly one `dtbo.img.lz4`
member.

Runtime:

- M25 first applies a DTBO high-speed cap by replacing each equal-length
  `super-speed` maximum-speed value with `high-speed` across all 11 DTBO
  overlay blobs.
- M25 then flashes a boot-only `/init` replacement based on the known booting
  Magisk boot.
- It uses `module_group=hs_only_usb2`, `module_count=40`, and
  `s22plus_m25_hs_only_usb2.modules`.
- It creates only the USB2 HighSpeed ACM path, attempts `ss_acm.0` on
  `a600000.dwc3 only`, and forces `bcdUSB=0x0200`.
- `phy-msm-ssusb-qmp.ko intentionally excluded`.
- It has no reboot beacon and no arm64 reboot syscall path.

Exact module list:

```text
clk-rpmh.ko
gcc-waipio.ko
icc-rpmh.ko
qcom_ipc_logging.ko
rpmh-regulator.ko
clk-dummy.ko
clk-qcom.ko
cmd-db.ko
debug-regulator.ko
gdsc-regulator.ko
icc-bcm-voter.ko
icc-debug.ko
iommu-logger.ko
qnoc-waipio.ko
phy-generic.ko
proxy-consumer.ko
qcom_iommu_util.ko
qcom_rpmh.ko
qcom-scm.ko
qnoc-qos.ko
sec_class.ko
secure_buffer.ko
smem.ko
socinfo.ko
arm_smmu.ko
phy-msm-snps-hs.ko
phy-msm-snps-eusb2.ko
dwc3-msm.ko
usb_f_ss_mon_gadget.ko
usb_f_ss_acm.ko
repeater.ko
redriver.ko
usb_notify_layer.ko
switch_class.ko
common_muic.ko
vbus_notifier.ko
usb_typec_manager.ko
if_cb_manager.ko
pdic_notifier_module.ko
qc_usb_audio.ko
```

Allowed:

- flash exactly the pinned M25 DTBO high-speed AP through Odin4;
- after Android/root returns and the patched DTBO hash is verified, flash
  exactly the pinned M25 boot-only AP through Odin4;
- observe for M25 ACM, ADB return, or Download/Odin return for a bounded window;
- rollback through the pinned Magisk boot rollback AP;
- restore the stock DTBO rollback AP after boot rollback;
- if Magisk rollback fails and Download mode remains available, use the pinned
  stock boot-only fallback AP;
- manual download-mode rollback through `--rollback-from-download` may be used
  after operator manual Download entry;
- if Android does not return after the DTBO-only step, use
  `--restore-dtbo-from-download` to restore stock DTBO only.

Forbidden:

- no vendor_boot, vbmeta, recovery, BL, CP, CSC, super, userdata, EFS, RPMB,
  keymaster, modem, or bootloader action;
- no raw host partition writes;
- no fastboot;
- no EUD sysfs write;
- no EUD enable/open;
- no QMP/USB3 module loading;
- no module binary injection;
- no broad module permutation;
- no reboot retry loop after a no-transport bootloop result.

If no ACM/ADB/Download rollback transport appears, stop and require manual
download-mode rollback. Treat operator-observed bootloop plus manual Download
as no-proof until rollback restores Magisk boot and stock DTBO and post-rollback
surfaces are collected.
