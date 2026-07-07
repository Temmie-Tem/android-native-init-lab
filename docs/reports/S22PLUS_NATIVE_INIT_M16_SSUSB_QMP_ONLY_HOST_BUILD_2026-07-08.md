# S22+ Native-Init M16 SSUSB-QMP-Only Host Build - 2026-07-08

## Verdict

PASS: host-only M16 SSUSB-QMP-only candidate built and statically validated.

No live flash was executed. M16 is not live-authorized until a fresh
SHA-pinned `AGENTS.md` exception and guarded live helper preflight exist.

## Purpose

M15 proved that the two-module PHY-side split still boot-loops:

```text
phy-msm-ssusb-qmp.ko
phy-msm-snps-eusb2.ko
```

M16 keeps the M13/M14/M15 mount, configfs, role-force, `a600000.dwc3` bind
policy, no-Android-handoff, and no-reboot park model, but loads only:

```text
phy-msm-ssusb-qmp.ko
```

M16 withholds the complementary M15 module:

```text
phy-msm-snps-eusb2.ko
```

This separates the first PHY module from the complementary single-module
candidate and from an open-only/no-finit control.

## Artifacts

```text
source       workspace/public/src/native-init/s22plus_init_usb_acm_m16_ssusb_qmp_only_park.c
builder      workspace/public/src/scripts/revalidation/build_s22plus_inplace_m16_ssusb_qmp_only_park.py
out_dir      workspace/private/outputs/s22plus_native_init/inplace_m16_ssusb_qmp_only_v0_1
AP.tar.md5   workspace/private/outputs/s22plus_native_init/inplace_m16_ssusb_qmp_only_v0_1/odin4/AP.tar.md5
manifest     workspace/private/outputs/s22plus_native_init/inplace_m16_ssusb_qmp_only_v0_1/manifest.json
```

Exact hashes:

```text
AP.tar.md5       266c3229298e9edd568239a5b09ae0a67325b3df600dd8fc1f9326d0f81de709
boot.img         69ff6738e62e4fe891c4c9e204caca19220cc1938b40037e6d992bc97bb1ff42
M16 /init        cabccce620de641fa777c00152588ef8cf5234098509b30afb4751d543dac993
M16 module list  fe59628f9d30996e80b47938675a3e133f2ae7ba7a934b31ef19aa2bf87bb4a1
source           b96c8a2c5a44eadbf03bd1f1aadadb5a74be76726d200d935e81276baf4c6c45
base boot        2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
kernel           bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff
```

The AP contains exactly one Odin member:

```text
boot.img.lz4
```

## Manifest Gates

```text
target=SM-S906N/g0q/S906NKSS7FYG8
boot_only=true
host_only_build=true
live_flash_authorized=false
requires_new_sha_pinned_agents_exception_before_flash=true
construction=magiskboot unpack/repack; replace ramdisk /init only
runtime=freestanding-raw-syscall
glibc_static_startup=false
mkbootimg_from_scratch=false
no_android_or_magisk_handoff=true
auto_reboot=false
reboot_syscall=false
host_commanded_reboot_download=false
persistent_partition_mount=false
block_device_writes=false
module_binary_injection=false
module_files_injected_into_boot_ramdisk=0
module_list_files_injected_into_boot_ramdisk=1
module_list_path=/s22plus_m16_ssusb_qmp_only.modules
module_subset=phy-msm-ssusb-qmp.ko
configfs_runtime_gadget=ss_acm.0 only
udc_binding=a600000.dwc3 only; never dummy_udc.0
usb_role_force=attempt /sys/class/usb_role/*/role=device
observation_model=park-vs-loop plus host ACM enumeration; no reboot beacon
```

Vendor metadata gates:

```text
vendor_ramdisk_sha256=41b2481b779ff48863c300250dabf1b3dcc45c7f58fab421fcf6df1245145193
ko_count=441
modules.load count=140
modules.load.recovery count=446
modules.dep count=441
modules.load.recovery all .ko=true
modules.load.recovery inline whitespace=false
modules.softdep has dwc3_msm=true
SSUSB-QMP-only count=1
SSUSB-QMP-only bytes=21
SSUSB-QMP-only position: phy-msm-ssusb-qmp.ko=259
```

## Static Validation

Commands run:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/build_s22plus_inplace_m16_ssusb_qmp_only_park.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/build_s22plus_inplace_m16_ssusb_qmp_only_park.py --force
```

Additional host checks:

```text
file(M16 /init) == ELF 64-bit LSB executable, ARM aarch64, statically linked, stripped
AP tar members == boot.img.lz4
module list == phy-msm-ssusb-qmp.ko
required strings present: S22_NATIVE_INIT_USB_ACM_M16, module_group=ssusb_qmp_only, module_count=1
forbidden strings absent: download, modules.load.recovery, /vendor_dlkm, ld-linux, libc.so
arm64 __NR_reboot=142 load absent
arm64 __NR_finit_module=273 load present
```

## Decision Tree

```text
M16 loops:
  phy-msm-ssusb-qmp.ko alone is enough to trigger the loop, or the runtime
  finit_module path is the trigger. Next add an open-only/no-finit control.

M16 parks/no ACM:
  phy-msm-ssusb-qmp.ko alone is tolerated. Next test phy-msm-snps-eusb2.ko
  alone before recombining.

M16 exposes ACM:
  Unexpected but positive; the ACM control-channel milestone is reached with a
  single module.
```

## Next

Next bounded unit is M16 live-gate preflight only:

1. Add a SHA-pinned `AGENTS.md` boot-only/Odin exception for the exact M16 AP.
2. Add a guarded M16 live helper using the exact hashes above.
3. Run `--offline-check` and default dry-run against Android/Magisk baseline.
4. Only then consider an attended live flash with an explicit ack.
