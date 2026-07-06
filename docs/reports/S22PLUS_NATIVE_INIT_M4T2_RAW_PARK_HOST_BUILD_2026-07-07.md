# S22+ Native-Init M4T2 Raw Park Host Build - 2026-07-07

## Scope

Host-only build and validation for the next S22+ native-init discriminator
after M4T1 failed. No reboot, Odin live transfer, partition write, recovery
action, Magisk action, or connected-device mutation was performed.

M4T2 intentionally does less than M4T1:

- no libc startup;
- no syscalls;
- no reboot request;
- no marker write;
- no modules, configfs, watchdog, persistent mount, Android handoff, or Magisk
  handoff;
- raw `_start` enters an infinite `wfe`/branch park.

The intended future live discriminator is behavioral: if M4T2 still fast-loops,
the failure is before or during exec of `/init`; if it stops fast-looping and
parks, the kernel reached and ran the custom PID1.

## Builder

Added:

```text
workspace/public/src/native-init/s22plus_init_park_m4t2.S
workspace/public/src/scripts/revalidation/build_s22plus_inplace_m4t2_park.py
```

Private output:

```text
workspace/private/outputs/s22plus_native_init/inplace_m4t2_park_v0_1
```

Command:

```bash
python3 workspace/public/src/scripts/revalidation/build_s22plus_inplace_m4t2_park.py --force
```

## Raw Init

Raw `/init` hash and size:

```text
sha256=b8371e3ac671ff71e9be752b8ff1087a4f20811c871a43ca8e698eee47783d12
size=544
```

Static marker string retained for host verification:

```text
S22_NATIVE_INIT_PARK_M4T2 raw-pid1 no-libc no-syscall no-reboot infinite-park
```

ELF shape:

```text
ELF 64-bit LSB executable, ARM aarch64, statically linked, stripped
Type: EXEC
Machine: AArch64
Entry point: 0x4000b0
Program headers: LOAD, GNU_STACK
PT_INTERP: absent
```

The builder rejects dynamic-loader strings such as `/lib` and `ld-linux`.

## Candidate Hashes

```text
source        d5ec47527dae3d94e88ca8555e7efd96048de3ea87a3a136b50ad5a8be301551
base boot     2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
kernel        bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff
boot.img      8103bce76fb3e41d71b64735a64d2f2f29431a44ea1c9a85dc0bc151d71afd15
boot.img.lz4  8db75e0cce8a8bea69c05e7747f4690fed19e51ddbc0f81dc06e1f4621be6265
AP.tar.md5    66d7f24b348702f58efbe1945b0d2751052ed27f6ce1f6fc4e5da63f3a585b24
```

The AP contains exactly:

```text
boot.img.lz4
```

## Validation

No-change MagiskBoot repack:

```text
base boot sha             2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
no-change repack boot sha 2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
result                    byte-identical
```

Ramdisk listing diff:

```diff
-rwxr-x---  0  0  200 KB  0:0  init
+rwxr-x---  0  0  544 B   0:0  init
```

Patched boot unpack:

```text
HEADER_VER      [4]
KERNEL_SZ       [41490944]
RAMDISK_SZ      [1295217]
OS_VERSION      [12.0.0]
OS_PATCH_LEVEL  [2025-08]
PAGESIZE        [4096]
CMDLINE         []
KERNEL_FMT      [raw]
RAMDISK_FMT     [lz4_legacy]
SAMSUNG_SEANDROID
VBMETA
```

Odin parse dry-run against an intentionally invalid USB path reached package
checking and failed only at the invalid USB device:

```text
Check file : .../inplace_m4t2_park_v0_1/odin4/AP.tar.md5
/dev/bus/usb/999/999
No such file or directory
usb device Fail
```

## Live Status

M4T2 is built but not live-authorized. Before any live flash, it requires:

- a fresh SHA-pinned `AGENTS.md` S22+ boot-only exception for
  `AP.tar.md5` SHA256
  `66d7f24b348702f58efbe1945b0d2751052ed27f6ce1f6fc4e5da63f3a585b24`;
- a guarded helper/dry-run;
- attended rollback plan using the pinned Magisk boot-only AP first.

Do not run M4T2 as a normal unattended live gate. Its expected success signal
is not ADB or self-download; it is the absence of the fast reboot loop, which
needs explicit operator observation or another early-boot observation channel.
