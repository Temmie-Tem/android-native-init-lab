# S22+ Observable Native-Init M3 Host Build - 2026-07-07

## Scope

Built the first observable direct native `/init` candidate after the M1/M2
measurement pass. This was not a live boot flash. No Odin transfer, reboot,
partition write, Magisk module install, Android service change, sysfs/configfs
write on the running Android system, or native-init device boot was performed.

The only Android-side action in this unit was a rooted read of the 26 measured
USB-first vendor `.ko` files from `/vendor_dlkm/lib/modules` into a temporary
tar under `/data/local/tmp`, followed by host pull and remote deletion. The
resulting proprietary module bytes live only under `workspace/private/`.

## Clarification

"Module" here means Linux kernel `.ko` module. It does not mean a Magisk app
module. The Magisk app module list is expected to remain empty.

## Inputs

M2 recipe:

```text
workspace/private/outputs/s22plus_observable_init_recipe/s22plus_magisk_boot_time_capture_m1_20260706T173432Z/observable_init_recipe.json
```

Private module bundle:

```text
workspace/private/inputs/s22plus_module_bundles/FYG8_usb_first_m2/
```

Bundle summary:

```text
module_count=26
total_bytes=2854024
missing=[]
```

## Implementation

Added:

```text
workspace/public/src/native-init/s22plus_init_observable_m3.c
workspace/public/src/scripts/revalidation/build_s22plus_observable_m3_boot.py
```

The direct PID1 candidate:

- mounts minimal pseudo filesystems: proc, sysfs, devtmpfs/tmpfs, run tmpfs,
  configfs, and pstore;
- creates `/dev/kmsg` and dynamically discovers the `pmsg` char major from
  `/proc/devices` before creating `/dev/pmsg0`;
- emits `S22_NATIVE_INIT_OBSERVABLE_M3` to kmsg/pmsg and ramdisk marker files;
- inserts the M2 26-module USB-first vendor `.ko` list with per-module
  `finit_module` result logging;
- creates a minimal configfs `ncm.0` link-only gadget;
- deliberately does not assign committed MAC or IP addresses in public source;
- parks with heartbeat logs instead of auto-rebooting.

It deliberately does not mount persistent partitions, write block devices,
start Android, chainload Magisk, or auto-reboot.

## Validation

Commands:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/build_s22plus_observable_m3_boot.py

aarch64-linux-gnu-gcc -static -Os -Wall -Wextra -Werror \
  -o /tmp/s22plus_init_observable_m3_test \
  workspace/public/src/native-init/s22plus_init_observable_m3.c

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/build_s22plus_observable_m3_boot.py --force
```

Static build result:

```text
ELF 64-bit LSB executable, ARM aarch64, statically linked, stripped
```

Required strings were present in the built init:

```text
S22_NATIVE_INIT_OBSERVABLE_M3
ncm.0
finit_rc
pmsg
link_only=1
```

Generated AP package:

```text
workspace/private/outputs/s22plus_native_init/observable_m3_v0_1/odin4/AP.tar.md5
```

Package member gate:

```text
boot.img.lz4
```

Sizes:

```text
boot_unpadded=48168960
boot_img=100663296
boot_img_lz4=100663699
ap_tar_md5=100669481
ramdisk_cpio=6672384
observable_init=663456
module_bundle_total=2854024
```

Hashes:

```text
source=0a48f542a9a63aeabba5ea3d79a6a912477c09260ab79189306e439a2114d50b
stock_kernel=027d4ab6f39d4544f87d33b219bb7877ab9b662b40434bfb96464c1193aeb69d
module_bundle_manifest=1c22c93496e03a7df6dd74959511797b6d033b74361d3d3733d7be8269a5fa05
observable_init=8eabd5e3aac2ce3e6ea106e132f5c3a26997be3308b6e4d163bb1a6b4d9c6dcb
ramdisk_cpio=c90b310c2f33f85c6a77d8de32dbc95e4981e8915566b42ea8f4c8699cf82af5
boot_img=583a748f045c1053b808ca5b337c66336d3838f3fa240fa5de8e4dbf3f819734
boot_img_lz4=1d53d4404b10ee374fd7d51024c2b1e8edd53fa5ec20d58a6d33512cb78b4c5b
ap_tar_md5=d588b84c231a53ba8447716af2f0bee6128f738634c951b8728fed662c17807e
```

Odin invalid-device parse gate:

```text
Check file : .../observable_m3_v0_1/odin4/AP.tar.md5
/dev/bus/usb/999/999
No such file or directory
usb device Fail
```

This proves Odin parsed the single-member AP before failing at the intentionally
invalid USB device path.

## Result

PASS: M3 host-only observable native-init candidate is built and statically
validated.

LIVE FLASH IS NOT AUTHORIZED by the current contract. A live M3 boot attempt
requires a fresh SHA-pinned S22+ boot-only `AGENTS.md` exception for:

```text
AP.tar.md5 SHA256: d588b84c231a53ba8447716af2f0bee6128f738634c951b8728fed662c17807e
boot.img SHA256:   583a748f045c1053b808ca5b337c66336d3838f3fa240fa5de8e4dbf3f819734
```

Recommended next gate: add that SHA-pinned exception only if the operator wants
to live-test M3, then flash boot-only via the existing S22+ Odin path, watch for
USB NCM link enumeration, and collect kmsg/pstore evidence before any further
native-init candidate.
