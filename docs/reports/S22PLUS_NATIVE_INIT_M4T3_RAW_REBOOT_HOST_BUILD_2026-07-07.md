# S22+ Native-Init M4T3 Raw Reboot Host Build - 2026-07-07

## Scope

Host-only build and validation for the next S22+ native-init discriminator after
M4T2 proved raw PID1 execution. No reboot, Odin live transfer, partition write,
recovery action, Magisk action, or connected-device mutation was performed.

M4T3 adds exactly one primitive on top of the proven M4T2 floor:

- raw AArch64 `_start`;
- no libc startup;
- no stack use;
- no marker write;
- no module insertion, configfs gadget setup, watchdog action, persistent mount,
  Android handoff, or Magisk handoff;
- first action is a direct arm64 `reboot(2)` syscall requesting `"download"`;
- if that syscall returns, the process enters an infinite `wfe`/branch park.

The future live discriminator is therefore sharper than M4T2:

- download mode returns: raw reboot syscall path works from custom PID1;
- no transport but stable park: custom PID1 survived and the syscall returned or
  was rejected;
- fast bootloop: raw reboot syscall path or immediate PID1 action is unstable.

## Builder

Added:

```text
workspace/public/src/native-init/s22plus_init_raw_reboot_m4t3.S
workspace/public/src/scripts/revalidation/build_s22plus_inplace_m4t3_raw_reboot.py
```

Private output:

```text
workspace/private/outputs/s22plus_native_init/inplace_m4t3_raw_reboot_v0_1
```

Command:

```bash
python3 workspace/public/src/scripts/revalidation/build_s22plus_inplace_m4t3_raw_reboot.py --force
```

## Raw Init

Raw `/init` hash and size:

```text
sha256=e975a973395fd1bfe2fee0dccb9d47400e6746d62b508cd139b49c551b9aa67c
size=616
```

Static strings retained for host verification:

```text
S22_NATIVE_INIT_RAW_REBOOT_M4T3 raw-pid1 no-libc one-raw-syscall reboot-download then-park
download
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

Disassembly of the first action:

```text
4000b0: mov  x0, #0xdead
4000b4: movk x0, #0xfee1, lsl #16
4000b8: mov  x1, #0x1969
4000bc: movk x1, #0x2812, lsl #16
4000c0: mov  x2, #0xc3d4
4000c4: movk x2, #0xa1b2, lsl #16
4000c8: adrp x3, 0x400000
4000cc: add  x3, x3, #0x140
4000d0: mov  x8, #0x8e
4000d4: svc  #0x0
4000d8: wfe
4000dc: b    0x4000d8
```

This encodes:

```text
reboot(0xfee1dead, 0x28121969, 0xa1b2c3d4, "download")
```

The builder rejects `PT_INTERP`, dynamic-loader strings, missing marker strings,
and a missing `svc #0` instruction.

## Candidate Hashes

```text
source        f4e0477805bc5787484cdd7fbf4f452bf9756e56182a10359ade1ac140f72e2b
base boot     2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
kernel        bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff
boot.img      d5e0371c6cb68af8990ce3ac4701ad4e0e487dbe54f4702dae29e21d86f4b92a
boot.img.lz4  c7e41988589f0aff0435f4ad657653e18b1be8c0891ea83be2b83d9f9d632595
AP.tar.md5    f0a26bb95a091070713f8d736419cbe60974195bb59509cb1fd7cc28a0b1a907
```

The AP contains exactly:

```text
boot.img.lz4
```

## Validation

Python syntax:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/build_s22plus_inplace_m4t3_raw_reboot.py
```

No-change MagiskBoot repack:

```text
base boot sha             2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
no-change repack boot sha 2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
result                    byte-identical
```

Patched boot unpack:

```text
HEADER_VER      [4]
KERNEL_SZ       [41490944]
RAMDISK_SZ      [1295281]
OS_VERSION      [12.0.0]
OS_PATCH_LEVEL  [2025-08]
PAGESIZE        [4096]
CMDLINE         []
KERNEL_FMT      [raw]
RAMDISK_FMT     [lz4_legacy]
SAMSUNG_SEANDROID
VBMETA
```

Ramdisk replacement gates:

```text
original Magisk /init sha 383670a7ba3a6a4b79e5f3467e1da4b66a5df66a9b356ab9f70916854dd6b468
replaced /init sha        e975a973395fd1bfe2fee0dccb9d47400e6746d62b508cd139b49c551b9aa67c
replaced entry            init
mode                      750
```

Odin parse dry-run against an intentionally invalid USB path reached package
checking and failed only at the invalid USB device:

```text
Check file : .../inplace_m4t3_raw_reboot_v0_1/odin4/AP.tar.md5
/dev/bus/usb/999/999
No such file or directory
usb device Fail
```

## Live Status

M4T3 is built but not live-authorized. Before any live flash, it requires:

- a fresh SHA-pinned `AGENTS.md` S22+ boot-only exception for
  `AP.tar.md5` SHA256
  `f0a26bb95a091070713f8d736419cbe60974195bb59509cb1fd7cc28a0b1a907`;
- a guarded helper and dry-run that checks the exact AP, contained boot image,
  raw `/init`, rollback AP, and current Android/root baseline;
- attended rollback plan using the pinned Magisk boot-only AP first.

Do not run M4T3 as a normal unattended live gate. It changes the first action
from M4T2's no-syscall park to a real reboot syscall, so the result must be
interpreted against the three-way discriminator above.
