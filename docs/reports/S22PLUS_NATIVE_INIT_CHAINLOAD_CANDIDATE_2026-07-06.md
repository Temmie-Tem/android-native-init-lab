# S22+ Native Init Chainload Candidate - 2026-07-06

## Scope

Host-side preparation only.  No S22+ partition write, reboot, Odin/Heimdall
flash, or live boot validation was performed in this unit.

The device has no `init_boot` partition in the observed by-name table, so the
direct native-init entry point is the `boot.img` first-stage ramdisk `/init`.
This unit builds the first conservative candidate by replacing `/init` with a
small wrapper and moving the stock Android init to `/init.stock`.

## Source

- Wrapper source:
  `workspace/public/src/native-init/s22plus_init_chainload.c`
- Stock boot image:
  `workspace/private/inputs/s22plus_firmware/S906NKSS7FYG8_SKC/extracted-images/raw/boot.img`
- Stock boot SHA256:
  `4150b962314e6136acba61b20f471d6ee1c418b83cf8c3ee4d9cf7c91a3640ae`

## Candidate Behavior

The wrapper runs as PID 1 from `/init`, emits proof markers, and immediately
execs the original Android init at `/init.stock` using the original argv/envp.

Proof attempts:

- Write `/s22_native_init_wrapper_ran`
- Write `/debug_ramdisk/s22_native_init_wrapper_ran`
- Create `/dev/kmsg` as char `1:11` if missing, then write a kmsg marker

The wrapper does not mount persistent partitions and does not touch hardware
state.  If `/init.stock` exec fails, it writes a failure marker to kmsg and
parks with `pause()`.

## Host Validation

No-change boot repack:

- `kernel` round-trip compare: pass
- `ramdisk` round-trip compare: pass
- Note: AOSP `mkbootimg.py` does not preserve the original GKI
  `boot_signature`; the repacked image reports `boot.img signature size: 0`.

Chainload candidate:

- Wrapper compile: pass
  - ELF: `ARM aarch64`, statically linked, stripped
  - SHA256:
    `b3f0276e491f304d518f824471fe986e0200194ee8ad88dcd53fac48a5ad9e70`
- Candidate unpack: pass
  - `boot magic: ANDROID!`
  - `boot image header version: 4`
  - `kernel_size: 41490944`
  - `ramdisk size: 1967140`
  - `os version: 12.0.0`
  - `os patch level: 2025-08`
  - `boot.img signature size: 0`
- Kernel compare against stock unpack: pass
- `/init` compare against compiled wrapper: pass
- `/init.stock` compare against stock `/init`: pass
- Marker strings present in wrapper: pass

## Private Outputs

- Unpadded candidate:
  `workspace/private/outputs/s22plus_native_init/chainload_v0/boot_chainload_unpadded.img`
  - size: `43466752`
  - SHA256:
    `6d9e27b5532d33e8d4c1976e5ba1b0f883ecd12d6c7aa244d8e4377f7bb0550d`
- 96 MiB padded candidate:
  `workspace/private/outputs/s22plus_native_init/chainload_v0/boot_chainload_padded_96m.img`
  - size: `100663296`
  - SHA256:
    `e1ea3c01edb7c9d9a16b58653ca878db399c6cbeb660370c1bd9b69722d93c74`
- Odin/Heimdall payload image:
  `workspace/private/outputs/s22plus_native_init/chainload_v0/boot.img.lz4`
  - size: `23762113`
  - SHA256:
    `a7d7880f48308f46ab86632674ec16e398ed5b23d33c50f65e6a1d88495ed14c`
- Boot-only AP tar:
  `workspace/private/outputs/s22plus_native_init/chainload_v0/S22PLUS_S906NKSS7FYG8_chainload_boot_only_AP.tar`
  - contents: `boot.img.lz4`
  - size: `23767040`
  - SHA256:
    `d8e342b2c1f961daacdbcbe5ee4c5282d96d79efb84243914cb3927587690ad7`
- Boot-only AP tar.md5:
  `workspace/private/outputs/s22plus_native_init/chainload_v0/S22PLUS_S906NKSS7FYG8_chainload_boot_only_AP.tar.md5`
  - size: `23767073`
  - SHA256:
    `998a2afe17c3628ba81996e2a411c28c1f5908d68acc4f61a368de8fe01a01c3`

## Flash Readiness Notes

This is not yet a live-proof.  The next gate is a bounded Samsung download-mode
flash plan for boot only, with recovery path confirmed first.  Because the
candidate is unsigned (`boot_signature size: 0`), acceptance relies on the
already observed unlocked/orange boot state.

## Live Follow-up - 2026-07-06

This follow-up did perform S22+ boot-only Odin4 flashes.  It did not prove
native-init entry yet.

### Odin4 Packaging Facts

The first generated `tar.md5` packages were rejected before device transfer.
The working Odin4 AP package profile for this device/tool is:

- tar member: `boot.img.lz4`
- lz4 format: modern LZ4 frame, not legacy kernel `-l`
- lz4 options: `--content-size -B6` so the frame includes original size and
  uses 1 MiB blocks like the Samsung stock AP payload
- `tar.md5` trailer: Odin4 accepts the short `AP.tar.md5` trailer shape used in
  `workspace/private/outputs/s22plus_native_init/chainload_v0_2/odin4/AP.tar.md5`

### v0.1

`chainload_v0` flashed successfully after repackaging into the Odin4-compatible
frame profile:

- Odin log:
  `workspace/private/outputs/s22plus_native_init/odin4_candidate_frame_size_b6/odin_candidate_flash_20260705T195656Z.log`
- Transfer: `boot.img.lz4` reached `100%`
- Boot result: Android eventually returned after a factory reset, but the
  original `/s22_native_init_wrapper_ran` and
  `/debug_ramdisk/s22_native_init_wrapper_ran` markers were absent from ADB
  shell view.
- Interpretation: not a native-init proof.  Root/debug ramdisk markers are not
  durable or visible enough through stock non-root Android.

### v0.2

`workspace/public/src/native-init/s22plus_init_chainload.c` was updated to
`version=0.2`, adding a delayed child that waits for
`/data/local/tmp/s22_native_init_wrapper_ran`.

- Candidate build:
  `workspace/private/outputs/s22plus_native_init/chainload_v0_2/`
- Wrapper SHA256:
  `6781bdd61f1293921d9336ee1f8421fb341af905e3b83026bcd123269faf05cb`
- Odin AP SHA256:
  `e1739591fee2c084a33be5e8e82ff3606a9ce1682c5ee41e953fb02306d205c4`
- Odin log:
  `workspace/private/outputs/s22plus_native_init/chainload_v0_2/odin4/odin_candidate_flash_20260705T200852Z.log`
- Transfer: `boot.img.lz4` reached `100%`
- Live verification:
  `workspace/private/outputs/s22plus_native_init/chainload_v0_2/live_verify_20260705T200909Z/verify.txt`
- Boot result: `sys.boot_completed=1`, unlocked/orange state preserved, build
  remained `S906NKSS7FYG8`.
- Marker result: `/data/local/tmp/s22_native_init_wrapper_ran`,
  `/s22_native_init_wrapper_ran`, and
  `/debug_ramdisk/s22_native_init_wrapper_ran` were all absent.
- Interpretation: Android booted from the candidate path, but no readable proof
  marker survived.  This is still not a native-init entry proof.

### v0.3

`chainload_v0_3_cmdline` kept the v0.2 ramdisk and added boot header cmdline:

`androidboot.s22_native_init=v0_3 s22_native_init=v0_3`

- Candidate build:
  `workspace/private/outputs/s22plus_native_init/chainload_v0_3_cmdline/`
- Odin AP SHA256:
  `627cca8fde82820d7c931d08e73a26d3080baada9c7a93356ee1b21b436f36a7`
- Odin log:
  `workspace/private/outputs/s22plus_native_init/chainload_v0_3_cmdline/odin4/odin_candidate_flash_20260705T201505Z.log`
- Transfer: `boot.img.lz4` reached `100%`
- Live verification:
  `workspace/private/outputs/s22plus_native_init/chainload_v0_3_cmdline/live_verify_20260705T201523Z/verify.txt`
- Boot result: no ADB device after 180 seconds; operator reported recovery.
- Interpretation: cmdline mutation on this stock boot image is not a safe proof
  channel without more boot-chain understanding.

### Rollback / Current State

Stock boot-only rollback was flashed:

- Stock rollback Odin log:
  `workspace/private/outputs/s22plus_native_init/odin4_stock_rollback_short/odin_stock_rollback_20260705T201859Z.log`
- Transfer: `boot.img.lz4` reached `100%`
- Current live state after rollback:
  - ADB: `RFCT519XWGK device`
  - `sys.boot_completed=1`
  - `ro.boot.flash.locked=0`
  - `ro.boot.verifiedbootstate=orange`
  - `ro.build.PDA=S906NKSS7FYG8`
  - `ro.bootloader=S906NKSS7FYG8`
  - `ro.boot.s22_native_init` is empty

### Direction Change

The next work should not keep iterating first-stage `/init` wrappers blindly.
The experiment environment needs recovery infrastructure first:

1. Keep the current stock boot rollback package available.
2. Prepare an exact S22+ Snapdragon `g0q` / `SM-S906N` TWRP gate as recovery
   infrastructure, not as part of the native-init proof itself.
3. Only after recovery is convenient and repeatable, resume native-init proof
   with a readable proof channel.

Relevant TWRP references checked during this follow-up:

- Unofficial S22+ Snapdragon `g0q` device tree and guide:
  `https://github.com/afaneh92/android_device_samsung_g0q`
- Official TWRP Samsung device list did not show S22+ as an official supported
  device:
  `https://twrp.me/Devices/Samsung/`
