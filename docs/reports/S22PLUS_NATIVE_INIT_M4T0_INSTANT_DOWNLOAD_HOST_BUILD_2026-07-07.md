# S22+ Native-Init M4 TEST 0 Instant-Download Host Build - 2026-07-07

## Scope

Host-only build of the M4 TEST 0 direct-PID1 floor candidate. No live flash,
reboot, Odin transfer, partition write, Magisk module install, module load, or
device state change was performed.

This implements the post-M3.2 refinement: because the observed bootloop is fast,
test the lowest behavioral floor before adding marker writes, dwell, watchdog
handling, modules, USB, or retained-log assumptions.

## Source

```text
workspace/public/src/native-init/s22plus_init_instant_download_m4t0.c
```

Behavior:

- runs as direct `/init`;
- in `main()`, the first candidate action is `reboot(..., "download")`;
- does not write a marker before the reboot syscall;
- does not touch watchdog, modules, configfs, USB, Android, Magisk, or
  persistent partitions;
- only if the reboot syscall returns, creates late `/dev/kmsg` and
  `/dev/pmsg0`, emits `S22_NATIVE_INIT_INSTANT_DOWNLOAD_M4T0`, and parks.

Pass/fail is behavioral:

- fast self-entry to Samsung download mode proves the kernel executed custom
  `/init` and the download reboot path works;
- another fast loop means the floor is still below marker/dwell logic: likely
  image/exec-format/early-panic territory, so move to minimal-delta boot or
  UART rather than adding more marker code.

## Build Helper

```text
workspace/public/src/scripts/revalidation/build_s22plus_instant_download_m4t0_boot.py
```

The helper uses the same boot-only package shape as M3.2/M4A:

- stock kernel SHA gate;
- stock ramdisk root copied from the known booting repack root;
- direct `/init` replacement only;
- reproducible `newc` ramdisk;
- stock-style legacy-LZ4 ramdisk passed to `mkbootimg`;
- padded `boot.img` size `100663296`;
- Odin AP tar with exactly one member, `boot.img.lz4`;
- dry Odin invalid-device parse gate.

## Build Command

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/build_s22plus_instant_download_m4t0_boot.py \
  workspace/public/src/scripts/revalidation/build_s22plus_marker_m4a_boot.py \
  workspace/public/src/scripts/revalidation/build_s22plus_marker_m32_boot.py \
  workspace/public/src/scripts/revalidation/build_s22plus_direct_p3_boot.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/build_s22plus_instant_download_m4t0_boot.py \
  --force
```

Private output:

```text
workspace/private/outputs/s22plus_native_init/instant_download_m4t0_v0_1/
```

## Artifact Hashes

```text
source:
e708cbce75f1177bfc0055980fb16ad935acd1ffce4e1a12d0113dca4455b680

instant init:
61d9839fc424d6699ce2abf288b99483c978d0ef12937693e552d5bdf8ad4d17

padded boot.img:
4617a8804b93435cd0b6a5307862b4d5f55ca7e25befa0c19b2e7619284979e9

AP.tar.md5:
ba445b131fddd79887a4ace357a77a42b1f49367eaeea156a3cfebfd883b1904
```

Rollback artifacts reconfirmed:

```text
Magisk boot-only rollback AP:
d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56

stock boot-only fallback AP:
1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e
```

## Static Validation

Binary:

```text
ELF 64-bit LSB executable, ARM aarch64, statically linked, stripped
```

Boot package:

```text
tar members: ["boot.img.lz4"]
boot.img size: 100663296
ramdisk format: legacy-lz4
ramdisk magic: 02214c18
ramdisk roundtrip SHA: matches ramdisk cpio
```

Required strings found in installed `/init`:

```text
S22_NATIVE_INIT_INSTANT_DOWNLOAD_M4T0
proof=first-action-download-reboot
ramdisk_format=legacy-lz4
no_marker_before_reboot=1
no_usb_modules=1
no_configfs=1
no_android_handoff=1
```

Odin parse gate:

```text
Check file : workspace/private/outputs/s22plus_native_init/instant_download_m4t0_v0_1/odin4/AP.tar.md5
/dev/bus/usb/999/999
No such file or directory
usb device Fail
```

Interpretation: Odin parsed the package shape and reached the intentionally
invalid transport path; no live transfer occurred.

## Live Boundary

No M4T0 live flash is authorized by this host build.

A live test requires a fresh SHA-pinned S22+ boot-only `AGENTS.md` exception for
exactly:

```text
candidate AP.tar.md5 SHA256:
ba445b131fddd79887a4ace357a77a42b1f49367eaeea156a3cfebfd883b1904

candidate padded boot.img SHA256:
4617a8804b93435cd0b6a5307862b4d5f55ca7e25befa0c19b2e7619284979e9
```

Expected live interpretation:

- fast self-entry to download mode: custom `/init` executed; build upward from
  this floor one layer at a time;
- fast loop/no download: stop this branch and move to minimal-delta boot or
  UART;
- screen behavior and loop period should be recorded by the operator because
  they are part of the proof surface.
