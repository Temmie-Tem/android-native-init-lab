# S22+ Native-Init M4T1 In-Place MagiskBoot Host Build - 2026-07-07

## Scope

Host-only build and validation for the next S22+ native-init acceptance probe.
No reboot, Odin live transfer, partition write, recovery action, Magisk action,
or connected-device mutation was performed.

This unit implements the current `GOAL.md` steer: stop rebuilding `boot.img`
from scratch with `mkbootimg`; instead start from the known-booting Magisk
boot image and replace only the ramdisk `/init` entry with the M4T0
instant-download native init.

## Builder

Added:

```text
workspace/public/src/scripts/revalidation/build_s22plus_inplace_m4t1_magiskboot.py
```

Private output:

```text
workspace/private/outputs/s22plus_native_init/inplace_m4t1_magiskboot_v0_1
```

Command:

```bash
python3 workspace/public/src/scripts/revalidation/build_s22plus_inplace_m4t1_magiskboot.py --force
```

The builder extracts/uses the x86_64 `magiskboot` from the staged Magisk v30.7
APK when needed, validates the known-booting Magisk boot SHA, proves a
no-change `magiskboot unpack -h` + `magiskboot repack` is byte-identical, then
replaces only ramdisk entry `init`.

## Candidate Behavior

The installed `/init` is the same first-action floor behavior as M4T0:

- first candidate action is `reboot(..., "download")`;
- no marker is written before that reboot syscall;
- no watchdog device is touched;
- no module insertion, configfs gadget, persistent mount, Android handoff, or
  Magisk handoff is attempted.

Required string gate in the compiled `/init`:

```text
S22_NATIVE_INIT_INSTANT_DOWNLOAD_M4T0
proof=first-action-download-reboot
no_marker_before_reboot=1
no_usb_modules=1
no_configfs=1
no_android_handoff=1
```

## Inputs

Known-booting Magisk boot baseline:

```text
workspace/private/outputs/s22plus_magisk_root_boot_only/boot.img
sha256=2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
size=100663296
```

Original Magisk ramdisk `/init`:

```text
sha256=383670a7ba3a6a4b79e5f3467e1da4b66a5df66a9b356ab9f70916854dd6b468
size=199960
```

Compiled instant-download `/init`:

```text
sha256=61d9839fc424d6699ce2abf288b99483c978d0ef12937693e552d5bdf8ad4d17
size=597920
```

## Output Hashes

```text
boot.img       9ce597e4ba920f1331937dbe4736f923728ff5502b02c02dea8357b3a9d5b9d1
boot.img.lz4   6964ebaf61ae3fc9f3eddb660b2523e9cccf70fe49a07e1bbbd9561de4945964
AP.tar.md5     9f5b4c48b95b710f742d5ea8c7f16ef4802cf27e78469381073d460361d0451c
```

The Odin AP contains exactly one tar member:

```text
boot.img.lz4
```

Odin parse dry-run against an invalid USB path reached package checking and
failed only at the intentionally invalid USB device:

```text
Check file : .../inplace_m4t1_magiskboot_v0_1/odin4/AP.tar.md5
/dev/bus/usb/999/999
No such file or directory
usb device Fail
```

## Validation

No-change MagiskBoot repack:

```text
base boot sha             2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
no-change repack boot sha 2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
result                    byte-identical
```

Ramdisk listing diff before/after replacement:

```diff
-rwxr-x---  0  0  200 KB  0:0  init
+rwxr-x---  0  0  598 KB  0:0  init
```

All other listed ramdisk entries remained present. `magiskboot cpio test`
remained rc=1 after the edit because `.backup` and `overlay.d` Magisk structure
is deliberately preserved; the actual replacement gate is the extracted
`init` SHA matching the compiled native init.

Patched boot unpack:

```text
HEADER_VER      [4]
KERNEL_SZ       [41490944]
RAMDISK_SZ      [1609227]
OS_VERSION      [12.0.0]
OS_PATCH_LEVEL  [2025-08]
PAGESIZE        [4096]
CMDLINE         []
KERNEL_FMT      [raw]
RAMDISK_FMT     [lz4_legacy]
SAMSUNG_SEANDROID
VBMETA
```

Kernel SHA is preserved from the known-booting Magisk boot:

```text
bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff
```

Boot-level diff versus the known-booting Magisk boot:

```text
same_size=true
total_size=100663296
changed_byte_count=539596
first_changed_offset=12
last_changed_offset=100663258
unchanged_prefix_bytes=12
unchanged_suffix_bytes=37
```

This is expected for a ramdisk replacement: header ramdisk-size bytes and
AVB/VBMETA-related tail bytes update. The important validation is that
MagiskBoot can no-change repack byte-identically and that the patched image
keeps the Samsung/VBMETA trailer shape.

## M4T0 Comparison

The failed M4T0 `mkbootimg` candidate unpacked as:

```text
HEADER_VER      [4]
KERNEL_SZ       [41490944]
RAMDISK_SZ      [1973195]
OS_VERSION      [12.0.0]
OS_PATCH_LEVEL  [2025-08]
PAGESIZE        [4096]
CMDLINE         []
KERNEL_FMT      [raw]
RAMDISK_FMT     [lz4_legacy]
```

Unlike the known-booting Magisk boot and M4T1, M4T0 did not show:

```text
SAMSUNG_SEANDROID
VBMETA
```

This is the strongest host-side explanation so far for the live symptom:
the previous direct native-init candidates were probably rejected before
`/init` because they were reconstructed boot images, not because the
instant-download init logic was too late or wrong.

## Live Status

M4T1 is built but not live-authorized. A live gate requires a fresh
SHA-pinned `AGENTS.md` S22+ boot-only exception and guarded helper for exactly:

```text
AP.tar.md5 sha256=9f5b4c48b95b710f742d5ea8c7f16ef4802cf27e78469381073d460361d0451c
boot.img sha256=9ce597e4ba920f1331937dbe4736f923728ff5502b02c02dea8357b3a9d5b9d1
```

Expected discriminator:

- self-enters download mode quickly: boot is accepted and native `/init` ran;
- repeats the same bootloader/software-rejection loop: the acceptance issue is
  not just the missing Samsung/VBMETA trailer from the `mkbootimg` path, so the
  next evidence channel should be UART or deeper boot-chain inspection.
