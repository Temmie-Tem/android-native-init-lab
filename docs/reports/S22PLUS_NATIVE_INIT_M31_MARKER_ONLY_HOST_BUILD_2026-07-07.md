# S22+ Native-Init M3.1 Marker-Only Host Build - 2026-07-07

## Scope

Built the M3.1 marker-only direct native-init candidate host-side. This unit did
not flash, reboot, call Odin live, write partitions, load modules, or change the
running Android system.

## Reason

M3 v0.2 returned to download/Odin visibility before any collectable
`S22_NATIVE_INIT_OBSERVABLE_M3` marker, and before the programmed 90 second
download reboot. The postmortem scoped the failure above USB module/configfs
bring-up. M3.1 therefore removes USB entirely and proves only the earliest
direct `/init` marker path.

## Implementation

Added:

```text
workspace/public/src/native-init/s22plus_init_marker_m31.c
workspace/public/src/scripts/revalidation/build_s22plus_marker_m31_boot.py
```

M3.1 behavior:

- create `/dev` if needed;
- create `/dev/kmsg` as char `1:11`;
- create fallback `/dev/pmsg0` as char `507:0`;
- write `S22_NATIVE_INIT_MARKER_ONLY_M31` to kmsg and pmsg;
- emit ten 1-second heartbeat markers;
- call `reboot(..., "download")`;
- park if the reboot syscall returns.

M3.1 deliberately does not:

- insert USB or display kernel modules;
- mount or write configfs;
- create a USB gadget;
- mount persistent partitions;
- write block devices;
- start Android or Magisk.

## Built Candidate

Generated AP package:

```text
workspace/private/outputs/s22plus_native_init/marker_m31_v0_1/odin4/AP.tar.md5
```

Tar member gate:

```text
boot.img.lz4
```

Sizes:

```text
marker_init=597920
ramdisk_cpio=3741696
boot_unpadded=45240320
boot_img=100663296
boot_img_lz4=100663699
ap_tar=100669440
ap_tar_md5=100669481
```

Hashes:

```text
source=1335f855628d0a407eee815fab3e2cdabedf8ceebd25bd550290c97a6f0a709e
stock_kernel=027d4ab6f39d4544f87d33b219bb7877ab9b662b40434bfb96464c1193aeb69d
marker_init=4ad9c013ef101528a9f6181723c8448972ea2939d78fc93107313f3b9be2e8f6
ramdisk_cpio=499dd9c338938c2e1ea8e67bd80dd520daa23e1b8d0a80483d52ff3b9d621ef7
boot_unpadded=08a75c5556bc87884dcdce34172b192830439462f253720ffe5ce99654ea9813
boot_img=f3dea68c02be295141265820f4acdd425a12460e05957edf75c83a62c4a617c5
boot_img_lz4=dde4f2c2c8f5eed38b306c0b0272a5eee8ec6f1a1cc25a123dc4682674aa870a
ap_tar=6518937d3b42e87b67092bba1da36b58df305043cd18411390f86060ec1c8f23
ap_tar_md5=999beeb67f73c39eaa0b637bc3c62fe2d8474fa707110640ae51adca0fbd2cfb
```

## Validation

Commands:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/build_s22plus_marker_m31_boot.py

aarch64-linux-gnu-gcc -static -Os -Wall -Wextra -Werror \
  -o /tmp/s22plus_init_marker_m31_test \
  workspace/public/src/native-init/s22plus_init_marker_m31.c

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/build_s22plus_marker_m31_boot.py --force
```

Results:

```text
py_compile: pass
AArch64 static compile: pass
ELF: 64-bit LSB executable, ARM aarch64, statically linked, stripped
AP tar members: ['boot.img.lz4']
Odin invalid-device parse gate: reached intentionally invalid transport path
```

Required strings present in installed `/init`:

```text
S22_NATIVE_INIT_MARKER_ONLY_M31
fallback_pmsg_major=507
no_usb_modules=1
no_configfs=1
download_reboot_after_sec=10
```

Negative string/content checks:

```text
lib/modules/s22plus-m3: absent
*.ko under M3.1 ramdisk: absent
ncm.0: absent from M3.1 /init strings
finit_rc: absent from M3.1 /init strings
S22_NATIVE_INIT_OBSERVABLE_M3: absent from M3.1 /init strings
```

## Live Boundary

No live flash is authorized by this host build.

Before any live M3.1 attempt, add a fresh SHA-pinned `AGENTS.md` boot-only
exception for this exact AP and boot image, then add or update a guarded live
helper that verifies:

- exact M3.1 AP SHA256;
- exact M3.1 boot image SHA256;
- single `boot.img.lz4` AP member;
- pinned Magisk boot-only rollback AP;
- rooted Android preflight;
- post-rollback pstore marker collection.
