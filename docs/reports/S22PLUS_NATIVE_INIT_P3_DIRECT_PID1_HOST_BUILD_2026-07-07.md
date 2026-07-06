# S22+ Native-Init P3 Direct PID1 Host Build

Date: 2026-07-07 KST

Target:
- Samsung Galaxy S22+ `SM-S906N` / `g0q`
- Build: `S906NKSS7FYG8`

Scope:
- Host-only construction of a direct native-init PID1 first-light candidate.
- No S22+ reboot, Odin live transfer, partition write, module load/unload, or
  device-state mutation was performed in this unit.
- This host-build unit also stages the new SHA-pinned `AGENTS.md` P3 boot-only
  exception for this exact artifact. No live flash was performed in this unit.

## Why P3 Changes Direction

P2 proved that the Magisk-preserving chainload candidate could be written to the
boot partition, but it did not hand off to rooted Android and did not produce the
expected marker. TWRP recovery later showed the failed P1 boot candidate was
still installed on `boot`, while recovery, vendor_boot, and vbmeta were unchanged.

P3 therefore stops trying to preserve Android/Magisk for first-light. It builds a
real direct `/init` proof image:

- `/init` is the native proof binary.
- It does not exec Android init or Magisk init.
- It emits recovery-collectable `kmsg` markers.
- It attempts `reboot(..., "recovery")` after a short dwell window so TWRP can
  collect `/proc/last_kmsg`.
- It parks as PID1 if the recovery reboot syscall returns.

This is a first-light proof and observation rung, not the final interactive
control plane. USB ACM/NCM direct bring-up remains the next rung after direct
PID1 execution is proven.

## Source

New source:

```text
workspace/public/src/native-init/s22plus_init_direct_p3.c
```

New host builder:

```text
workspace/public/src/scripts/revalidation/build_s22plus_direct_p3_boot.py
```

The direct init safety boundary is deliberately small:

- no persistent partition mount
- no block-device write
- no module load
- no GPIO, PMIC, backlight, or regulator write
- no attempt to start Android

Expected proof marker:

```text
S22_NATIVE_INIT_DIRECT_P3 version=0.1 pid1=direct proof=kmsg-last_kmsg auto_reboot=recovery no_android_handoff=1
```

## Build

Private output:

```text
workspace/private/outputs/s22plus_native_init/direct_p3_v0_1
```

Build command:

```text
python3 workspace/public/src/scripts/revalidation/build_s22plus_direct_p3_boot.py --force
```

The builder uses:

- stock FYG8 kernel SHA256
  `027d4ab6f39d4544f87d33b219bb7877ab9b662b40434bfb96464c1193aeb69d`
- stock-derived ramdisk root from the earlier stock chainload extraction
- deterministic uncompressed `newc` cpio ramdisk
- AOSP `mkbootimg.py` header-version 4 metadata from the stock no-change repack
- padded 100663296-byte boot image
- boot-only Odin AP containing exactly `boot.img.lz4`

Because the host currently lacks a system `lz4` binary or Python `lz4` module,
the builder writes a valid LZ4 frame with content-size metadata and raw stored
blocks. The AP is larger than compressed prior candidates, but Odin4's parser
accepted the package shape during the invalid-device parse gate.

## Candidate Hashes

```text
source:
211b04dbdee23b273e17ef39ee03b26eae0a116689324f5adf7e3ba738553658

direct init:
9eabf7b4765bdb2bf126d7929be590f4ac86e74aeb73b02c47bee43bac8cedd2

stock kernel:
027d4ab6f39d4544f87d33b219bb7877ab9b662b40434bfb96464c1193aeb69d

ramdisk cpio:
82b4d0c55d63e6c6759c7eedde2cab124efdfba06cecf0156df2798e58ad37cd

unpadded boot image:
2d14c9bd76c90b67a842f2ea31fa0500f4f8ed1f4580a2930b56f7bed0addd21

padded boot.img:
bb803901048a089b956d7657ed45496de7416a90c0a35872784b537d7167f2cb

boot.img.lz4:
25a2c899b41bd5967c72aede2bc31dfc5582c0a7762255ca7bbd3c8b3f76b737

AP.tar:
19e418d1c08cebcf5d4f39ec7c120294e6cd9bac67110cb0af5aba803b6e4e9b

AP.tar.md5:
21838b4e64656cead9804f9034ed554bf6737a9666d07001d30ec66c01364d8b
```

## Static Validation

Python validation:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/build_s22plus_direct_p3_boot.py \
  workspace/public/src/scripts/revalidation/s22plus_p2_stock_boot_rollback_guard.py \
  workspace/public/src/scripts/revalidation/s22plus_p0_recon_collect.py
```

C validation:

```text
aarch64-linux-gnu-gcc -static -Os -Wall -Wextra -Werror \
  -o /tmp/s22plus_init_direct_p3_check \
  workspace/public/src/native-init/s22plus_init_direct_p3.c
```

Result:

```text
ELF 64-bit LSB executable, ARM aarch64, statically linked
```

Candidate boot image unpack:

```text
boot magic: ANDROID!
kernel_size: 41490944
ramdisk size: 3741696
os version: 12.0.0
os patch level: 2025-08
boot image header version: 4
command line args:
boot.img signature size: 0
```

Ramdisk root check:

```text
/init       direct native-init proof binary
/init.stock stock Android init retained as inert, unused file
```

Required strings were present in `/init`:

```text
S22_NATIVE_INIT_DIRECT_P3
recovery
no_android_handoff=1
```

Odin AP check:

```text
tar member:
boot.img.lz4

file boot.img.lz4:
LZ4 compressed data (v1.4+)
```

Odin4 invalid-device parse gate:

```text
Check file : workspace/private/outputs/s22plus_native_init/direct_p3_v0_1/odin4/AP.tar.md5
/dev/bus/usb/999/999
No such file or directory
usb device Fail
```

Interpretation: Odin4 parsed the AP and reached the intentionally invalid USB
transport path. This is a package-shape proof, not a flash proof.

Reproducibility check:

```text
python3 workspace/public/src/scripts/revalidation/build_s22plus_direct_p3_boot.py --force
python3 workspace/public/src/scripts/revalidation/build_s22plus_direct_p3_boot.py \
  --out /tmp/s22plus_direct_p3_rebuild_check --force --no-odin-parse-gate

both outputs:
boot.img     bb803901048a089b956d7657ed45496de7416a90c0a35872784b537d7167f2cb
AP.tar.md5   21838b4e64656cead9804f9034ed554bf6737a9666d07001d30ec66c01364d8b
ramdisk cpio 82b4d0c55d63e6c6759c7eedde2cab124efdfba06cecf0156df2798e58ad37cd
```

## P3 Live Boundary

The new `AGENTS.md` P3 S22+ boot-only exception pins:

```text
target: SM-S906N / g0q / S906NKSS7FYG8
candidate AP.tar.md5 sha256:
21838b4e64656cead9804f9034ed554bf6737a9666d07001d30ec66c01364d8b

candidate padded boot.img sha256:
bb803901048a089b956d7657ed45496de7416a90c0a35872784b537d7167f2cb

candidate member:
boot.img.lz4 only
```

Expected live success condition:

1. Odin transfers this exact boot-only AP.
2. The direct native-init runs as PID1.
3. TWRP recovery becomes available automatically or manually.
4. Recovery-side `/proc/last_kmsg` contains `S22_NATIVE_INIT_DIRECT_P3`.
5. The pinned stock boot-only rollback AP restores Android boot.

## Result

PASS: P3 direct native-init PID1 first-light host candidate is built and
statically validated.

Not complete: direct S22+ native-init first-light is not live-proven yet, and no
interactive native-init USB ACM/NCM control plane exists yet.
