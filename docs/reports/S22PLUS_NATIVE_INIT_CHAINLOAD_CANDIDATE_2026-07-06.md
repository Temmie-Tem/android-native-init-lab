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
