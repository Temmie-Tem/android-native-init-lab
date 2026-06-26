# Native Init V3302 GPU Compute C2 Pattern Live Validation

## Summary

- Cycle: `V3302`
- Track: GPU compute demo C2 live 128x128 buffer-pattern proof.
- Result: PASS
- Flashed boot image: `workspace/private/inputs/boot_images/boot_linux_v3302_gpu_compute_c2_pattern_probe.img`
- Boot SHA256: `3f437360d9c428548fb1d89dfa90d56091313375c0b04578c45d95021d43af5a`
- Resident after flash: `A90 Linux init 0.11.76 (v3302-gpu-compute-c2-pattern-probe)`
- Device identifiers, serials, MAC/BSSID/IP values: redacted/omitted.

## Flash Gate

- Pre-flash bridge: running and connected.
- Pre-flash resident: `0.11.75 (v3301-gpu-compute-c1-invocationid-probe)`.
- Pre-flash selftest: `pass=12 warn=1 fail=0`.
- Rollback images verified before flash:
  - `boot_linux_v2321_usb_clean_identity_rodata.img`: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
  - `boot_linux_v2237_supplicant_terminate_poll.img`: `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`
  - `boot_linux_v48.img`: `1c87fa59712395027c5c2e489b15c4f6ddefabc3c50f78d3c235c4508a63e042`
  - TWRP recovery image: `b1ef377a52ec8ab43b49a5fcc7a0b27e8efff91bf2d8cccdc565ecadadcc646c`
- Flash helper: `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- Flash result: helper wrote only boot, readback SHA matched, and post-flash `version`/`status` verify passed.

## C2 Probe

- Command: `gpu c2-compute-pattern-probe --timeout-ms 5000 --materialize-devnode`
- Probe result: `gpu.c2.compute.result=pattern-readback-pass`
- Materialize devnode: `rc=0`
- Submit/wait/readback:
  - `submit_rc=0`
  - `wait_rc=0`
  - `readtimestamp_rc=0`
  - `readback_sync_rc=0`
  - `retired_timestamp=1`
- UAV proof:
  - `readback0=0`
  - `readback1=1`
  - `readback2=2`
  - `readback3=3`
  - `readback31=31`
  - `readback127=127`
  - `readback128=128`
  - `readback4096=4096`
  - `readback8192=8192`
  - `readback16383=16383`
  - `changed_count=16384`
  - `expected_match_count=16384`
  - `mismatch_count=0`
  - `pass=1`
- Timing: `total_elapsed_ms=15`, command duration `28ms`.
- Note: an earlier no-materialize probe failed with `open_errno=2` for `/dev/kgsl-3d0`; the materialized C2 probe above is the accepted live result.

## Post-Probe Health

- Post-probe selftest: `pass=12 warn=1 fail=0`.
- Bridge capture C2 markers confirmed:
  - `gpu.c2.compute.result=pattern-readback-pass`
  - `gpu.c2.compute.expected_match_count=16384`
  - `gpu.c2.compute.mismatch_count=0`
  - `gpu.c2.compute.pass=1`
- GPU fault filter over the bridge capture found no `kgsl` fault/snapshot/IOMMU/page-fault, GMU fault/hang/error, CP illegal/error/fault/hang, ringbuffer fault/hang/error, or GPU/page/IOMMU fault match.

## Safety

- No forbidden partition write was attempted.
- No PMIC/regulator/GDSC/GPIO/backlight/panel re-init write was attempted.
- No proprietary blob/EGL/OpenCL path was used; the probe stayed on freedreno/KGSL-direct userspace command submission.
- No rollback was required.

## Next

- C2 is closed.
- Next rung: C3 present the compute output through the proven H5 KMS path for visual confirmation.
