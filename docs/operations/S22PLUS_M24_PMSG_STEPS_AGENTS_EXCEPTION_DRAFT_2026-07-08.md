# S22+ M24 PMSG-Steps AGENTS Exception Draft (2026-07-08)

This document is inert until copied into `AGENTS.md`.

Scope: one bounded attended S22+ M24 pmsg-step DTS-exact QMP/DWC3
native-init boot-only run, followed by rollback to the pinned Magisk boot
baseline and post-rollback retained-surface collection.

Helper:

```text
workspace/public/src/scripts/revalidation/s22plus_m24_pmsg_steps_live_gate.py
```

Ack tokens:

```text
S22PLUS-M24-PMSG-STEPS-LIVE-GATE
S22PLUS-M24-PMSG-STEPS-ROLLBACK-FROM-DOWNLOAD
```

Pinned candidate:

```text
AP.tar.md5 SHA256       e09538024abe89585486d54856a5c86bef666da456f314084d4d4d8bb6553fe8
boot.img SHA256         0cccc003687227c4265081fa59d440f4be3e7f40fbb64aca2a3930ca7d5ca3df
base boot SHA256        2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
kernel SHA256           bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff
/init SHA256            4086d18f453980893fa1b8022f93991775b0ee28a6088f1216de82b74cbaf341
module list SHA256      a542b86aee8d2b09d0ca233e0a81d7deb8919a77657122d91f3b46e0a7933349
generated source SHA256 f9a060f7804571c036631c954b3e88c064aa33176d7d8ec6abe9da8b8bf84bdd
vendor DTB SHA256       2cd64d43a4f6b89a7c5523f3ef73fbb84dcad92c6d857e649cd1f0baa7c0080e
```

Runtime:

- M24 is a boot-only `/init` replacement based on the known booting Magisk boot.
- It loads the same 43-module DTS-derived QMP/DWC3/HS-PHY/provider closure as M23.
- It uses `module_group=dts_exact_qmp`, `module_count=43`, and
  `s22plus_m24_pmsg_steps.modules`.
- It writes pmsg step markers to `/dev/pmsg0` with prefix `A90_STEP:M24:`.
- It creates fallback pmsg char node metadata `fallback_pmsg_major=507`.
- It emits `module_prepare` and `module_finit` markers around each module
  insertion attempt.
- It attempts `ss_acm.0` on `a600000.dwc3`, with `a600000.dwc3 only; never
  dummy_udc.0`.
- It has no reboot beacon and no arm64 reboot syscall path.
- EUD extcon excluded; no EUD sysfs write; no EUD enable/open.

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
pinctrl-waipio.ko
qnoc-waipio.ko
phy-generic.ko
pinctrl-msm.ko
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
phy-msm-ssusb-qmp.ko
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

- flash exactly the pinned M24 boot-only AP through Odin4;
- observe for ACM, ADB return, or Download/Odin return for a bounded window;
- rollback through the pinned Magisk boot-only AP;
- if Magisk rollback fails and Download mode remains available, use the pinned
  stock boot-only fallback AP;
- manual download-mode rollback through `--rollback-from-download` may be used
  after operator manual Download entry;
- after rollback, run pmsg/pstore/last_kmsg/reset-context post-rollback capture
  including `/proc/reset_summary`, `/proc/reset_klog`, `/proc/reset_history`,
  `/proc/reset_tzlog`, and `/proc/enhanced_boot_stat`.

Forbidden:

- no vendor_boot, DTBO, vbmeta, recovery, BL, CP, CSC, super, userdata, EFS,
  RPMB, keymaster, modem, or bootloader action;
- no raw host partition writes;
- no fastboot;
- no EUD sysfs write;
- no EUD enable/open;
- no module binary injection;
- no broad module permutation;
- no reboot retry loop after a no-transport bootloop result.

If no ACM/ADB/Download rollback transport appears, stop and require manual
download-mode rollback. Treat operator-observed bootloop plus manual Download
as no-proof until the post-rollback pmsg/pstore/last_kmsg/reset-context surfaces
are collected.
