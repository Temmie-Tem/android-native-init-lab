# S22+ Native-Init M25 HS-Only USB2 ACM Host Build - 2026-07-08

PASS: host-only M25 candidate built and statically validated. No live flash,
reboot, rollback, partition write, sysfs write, or connected-device mutation was
performed by the builder.

M25 implements the new fault-avoidance direction: cap DWC3 to HighSpeed and
avoid the SS/QMP PHY module that repeatedly boot-looped. The build produces a
boot native-init AP plus a DTBO high-speed AP and stock DTBO rollback AP.

## Artifacts

Output:

`workspace/private/outputs/s22plus_native_init/m25_hs_only_usb2_acm_v0_1`

Hashes:

```text
boot AP.tar.md5       7f89cfb8ff188190d1d161aee97e3edec2730bfc46efca9df37f2035f7206805
boot.img              0ace02ff82be1cb7473879ff52f1c9e8d1491edaa3d9a88b829f901b2c86559f
M25 /init             cc03d95f06b851717d3ccb4fc32fbecac3adfe7109c1a68454f846e3014ecf75
generated source      22350e7de748cf3a2f47236ef984bb224df58ffa7664ced811151c9db189562f
module list           00607484b7b777ee5cb54d7657f0cb554b9b66c42fec0e414d0544c0735d6496
DTBO AP.tar.md5       35afd774444066fd8e2ffe831da11dd73ee47dce3bdd5b1e37675f82344e56b6
patched DTBO raw      8962cbbded722c85dbdebfbdc2eba5476b9a64e2a2933888b81f947159eddc17
stock DTBO rollback   6f397421bee84f4ea0c80a8519be0f6f6af84119794970e8a1faaa05f261caaa
```

Tar members:

```text
boot candidate AP:    boot.img.lz4
DTBO candidate AP:    dtbo.img.lz4
DTBO rollback AP:     dtbo.img.lz4
```

## Boot Candidate

The M25 boot candidate is built from the known-booting Magisk boot base
`2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e` using
`magiskboot unpack/repack`. A no-change repack remains byte-identical.

The ramdisk changes are limited to:

- replace `/init` with the freestanding raw-syscall M25 init;
- add `/s22plus_m25_hs_only_usb2.modules`;
- inject no module binaries.

Runtime guard strings include:

```text
S22_NATIVE_INIT_USB_ACM_M25_HS_ONLY
module_group=hs_only_usb2
module_count=40
hs_only=1
qmp_excluded=1
maximum_speed_dtbo=high-speed
dtbo_patch_required=1
udc=a600000.dwc3
gadget=ss_acm.0
tty=/dev/ttyGS0
```

The generated init has no program interpreter, is AArch64/static/freestanding,
contains `svc`, and contains no arm64 reboot syscall path.

## Module Closure

M25 derives the HS-only closure from the stock vendor DTB and
`modules.load.recovery` order. It keeps `/soc/hsphy@88e3000`
(`qcom,usb-hsphy-snps-femto`) and excludes `/soc/ssphy@88e8000`
(`qcom,usb-ssphy-qmp-dp-combo`).

Module count: `40`.

Excluded by design:

```text
phy-msm-ssusb-qmp.ko
eud.ko
ucsi_glink.ko
gh_virt_wdt.ko
qcom_wdt_core.ko
sec_debug.ko
sec_debug_region.ko
abc.ko
minidump.ko
```

## DTBO Candidate

The DTBO candidate changes only the DWC3 maximum-speed overlay values:

```text
old: super-speed\0
new: high-speed\0\0
```

Scope:

- stock DTBO blob count: `11`;
- patched maximum-speed properties: `11`;
- changed bytes: `110`;
- stock DTBO AVB descriptor digest matches;
- patched DTBO digest necessarily differs and still requires the already-proven
  disabled-vbmeta/orange baseline or equivalent signing before live use.

## Current Device Baseline

After the operator reported bootloop/manual Download-mode entry, a read-only
check found the phone currently back on clean Android/Magisk baseline:

```text
boot_completed=1
verifiedbootstate=orange
boot_recovery=0
su id=uid=0(root)
boot        2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
vendor_boot 096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7
dtbo        97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c
```

## Validation

Commands passed:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/build_s22plus_m25_hs_only_usb2_acm.py \
  tests/test_s22plus_m25_hs_only_usb2_acm_build.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_s22plus_m25_hs_only_usb2_acm_build

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/build_s22plus_m25_hs_only_usb2_acm.py --force
```

## Next

M25 is not live-authorized. The next live-capable step is a fresh, SHA-pinned
`AGENTS.md` exception plus a guarded helper that stages the DTBO high-speed AP,
then the M25 boot AP, and restores the stock DTBO plus Magisk boot baseline on
failure or after proof collection.
