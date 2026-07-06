# S22+ Native-Init M4A Fast-Dwell Host Build - 2026-07-07

## Scope

Host-only build of the M4A fast-dwell direct-PID1 candidate. No live flash,
reboot, Odin transfer, partition write, Magisk module install, module load, or
device state change was performed.

M4A implements the post-M3.2 watchdog-hypothesis steer: write the earliest
native-init marker, wait only two seconds, then request Samsung download mode.
If a live run self-returns to download mode quickly, that is behavioral proof
that `/init` executed and the previous long dwell likely crossed a watchdog
window. If it still bootloops, proceed to minimal-delta boot and then UART.

## Source

```text
workspace/public/src/native-init/s22plus_init_marker_m4a.c
```

Behavior:

- runs as direct `/init`;
- creates `/dev/kmsg` and fallback `/dev/pmsg0` only;
- emits `S22_NATIVE_INIT_FAST_DWELL_M4A`;
- attempts to open and ping only an existing `/dev/watchdog` or
  `/dev/watchdog0`; it does not create watchdog device nodes;
- sleeps for two seconds;
- calls `reboot(..., "download")`;
- parks only if the reboot syscall returns.

No USB modules, configfs gadget setup, persistent partition mount, Android
handoff, Magisk handoff, or non-boot partition behavior is included.

## Build Helper

```text
workspace/public/src/scripts/revalidation/build_s22plus_marker_m4a_boot.py
```

The helper reuses the M3.2 stock-format packaging:

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
  workspace/public/src/scripts/revalidation/build_s22plus_marker_m4a_boot.py \
  workspace/public/src/scripts/revalidation/build_s22plus_marker_m32_boot.py \
  workspace/public/src/scripts/revalidation/build_s22plus_marker_m31_boot.py \
  workspace/public/src/scripts/revalidation/build_s22plus_direct_p3_boot.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/build_s22plus_marker_m4a_boot.py \
  --force
```

Private output:

```text
workspace/private/outputs/s22plus_native_init/marker_m4a_fastdwell_v0_1/
```

## Artifact Hashes

```text
source:
4e5360d6098a0c0333be1cab01620abc286b18839cde29d8269c7efd7add0144

marker init:
adbc4e53f2c77cc9bec556654a64aa9b14ba2f9ce65ca9dab4481e1590bb27b6

padded boot.img:
38901566af3b5449a245515f10bedc34090c320d871f1f055a2f84ae669d3dbb

AP.tar.md5:
fe20dee1dc28910a75e7b732049b0fdda434e3cc6a81755006ba2a6236cad2dc
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
S22_NATIVE_INIT_FAST_DWELL_M4A
proof=watchdog-hypothesis-fast-self-download
ramdisk_format=legacy-lz4
fallback_pmsg_major=507
no_usb_modules=1
no_configfs=1
download_reboot_after_sec=2
watchdog_open_if_present=1
```

Odin parse gate:

```text
Check file : workspace/private/outputs/s22plus_native_init/marker_m4a_fastdwell_v0_1/odin4/AP.tar.md5
/dev/bus/usb/999/999
No such file or directory
usb device Fail
```

Interpretation: Odin parsed the package shape and reached the intentionally
invalid transport path; no live transfer occurred.

## Live Boundary

No M4A live flash is authorized by this host build.

After this artifact was built, the operator refined the bootloop interpretation:
the loop is fast, so the first live floor probe should be M4 TEST 0
instant-download, not M4A fast-dwell. Keep M4A as the next layer only if M4T0
proves custom `/init` executes and reaches download mode.

A live test requires a fresh SHA-pinned S22+ boot-only `AGENTS.md` exception for
exactly:

```text
candidate AP.tar.md5 SHA256:
fe20dee1dc28910a75e7b732049b0fdda434e3cc6a81755006ba2a6236cad2dc

candidate padded boot.img SHA256:
38901566af3b5449a245515f10bedc34090c320d871f1f055a2f84ae669d3dbb
```

Expected live interpretation:

- fast self-return to download mode: `/init` executed; watchdog/long-dwell
  hypothesis is likely correct;
- bootloop or no self-download: do not retry M4A; proceed to minimal-delta boot
  or UART as directed;
- empty `/sys/fs/pstore` remains ambiguous and must not be the sole negative
  proof.
