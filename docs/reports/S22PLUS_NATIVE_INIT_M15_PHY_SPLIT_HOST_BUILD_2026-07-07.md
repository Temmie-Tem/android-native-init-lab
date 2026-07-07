# S22+ Native-Init M15 PHY-Split Host Build - 2026-07-07

## Verdict

PASS: host-only M15 PHY-split candidate built and statically validated.

No live flash was executed. M15 is not live-authorized until a fresh
SHA-pinned `AGENTS.md` exception and guarded live helper preflight exist.

## Purpose

M14 proved that the four-module core USB/ACM add-back loops before any ACM or
ADB transport appears. M15 keeps the M13/M14 mount, configfs, role-force,
`a600000.dwc3` bind policy, no-Android-handoff, and no-reboot park model, but
loads only the two PHY-side modules from the failed M14 group:

```text
phy-msm-ssusb-qmp.ko
phy-msm-snps-eusb2.ko
```

M15 withholds the remaining two M14 modules:

```text
dwc3-msm.ko
usb_f_ss_acm.ko
```

This separates "PHY-side module load causes the loop" from
"dwc3-msm/usb_f_ss_acm causes the loop".

## Artifacts

```text
source       workspace/public/src/native-init/s22plus_init_usb_acm_m15_phy_split_park.c
builder      workspace/public/src/scripts/revalidation/build_s22plus_inplace_m15_phy_split_park.py
out_dir      workspace/private/outputs/s22plus_native_init/inplace_m15_phy_split_v0_1
AP.tar.md5   workspace/private/outputs/s22plus_native_init/inplace_m15_phy_split_v0_1/odin4/AP.tar.md5
manifest     workspace/private/outputs/s22plus_native_init/inplace_m15_phy_split_v0_1/manifest.json
```

Exact hashes:

```text
AP.tar.md5       16a4d526bbc0cb09bc63d61f4743d17dddb26c34047127fe610b1f677bddced2
boot.img         adaee20d490748aa1be555cdc7aa6828b9bc553185355a60183bd722119b5812
M15 /init        5897fee141921dffc2848fb3eb3515a9b2d75d41e0c286448c4f0add06ab8558
M15 module list  f3afe268a05c47492107227b224185c65f7757c004806c4c24d23231bd19e217
source           ac57cb1ece2dcc65bf5a8cbfc3fa0a077b006c757a4615298ee00d115b1fdd13
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
module_list_path=/s22plus_m15_phy_split.modules
module_subset=phy-msm-ssusb-qmp.ko, phy-msm-snps-eusb2.ko
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
PHY split count=2
PHY split bytes=43
PHY split positions: phy-msm-ssusb-qmp.ko=259, phy-msm-snps-eusb2.ko=261
```

## Static Validation

Commands run:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/build_s22plus_inplace_m15_phy_split_park.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/build_s22plus_inplace_m15_phy_split_park.py --force
```

Additional host checks:

```text
file(M15 /init) == ELF 64-bit LSB executable, ARM aarch64, statically linked, stripped
AP tar members == boot.img.lz4
module list == phy-msm-ssusb-qmp.ko, phy-msm-snps-eusb2.ko
required strings present: S22_NATIVE_INIT_USB_ACM_M15, module_group=phy_split, module_count=2
forbidden strings absent: download, modules.load.recovery, /vendor_dlkm, ld-linux, libc.so
arm64 __NR_reboot=142 load absent
arm64 __NR_finit_module=273 load present
```

## Decision Tree

```text
M15 loops:
  The loop is at or below the PHY-side module load or the finit_module path.
  Next split should be one PHY module at a time, plus an open-only/no-finit
  control if needed.

M15 parks/no ACM:
  The two PHY modules are tolerated under native-init. Next add dwc3-msm.ko
  alone before adding usb_f_ss_acm.ko.

M15 exposes ACM:
  Unexpected but positive; the ACM control-channel milestone is reached with a
  smaller-than-M14 module set.
```

## Next

Next bounded unit is M15 live-gate preflight only:

1. Add a SHA-pinned `AGENTS.md` boot-only/Odin exception for the exact M15 AP.
2. Add a guarded M15 live helper using the exact hashes above.
3. Run `--offline-check` and default dry-run against Android/Magisk baseline.
4. Only then consider an attended live flash with an explicit ack.
