# Native Init V3195 GPU G3 Noop Submit Probe Live

## Summary

- Cycle: `V3195`
- Flashed artifact: `workspace/private/inputs/boot_images/boot_linux_v3194_gpu_g3_noop_submit_probe.img`
- Artifact SHA256: `a3067ee439e7b779fbbbb36a2f2d6a09208e1a2c58f434c31be3e51d3286e14f`
- Resident after flash: `A90 Linux init 0.11.25 (v3194-gpu-g3-noop-submit-probe)`
- Result: PASS

## Flash Gate

- Checked flash path: `workspace/public/src/scripts/revalidation/native_init_flash.py --from-native`
- Local image marker and SHA256 verified before flash.
- Recovery ADB gate passed through the checked helper.
- Boot partition write readback SHA256 matched the local artifact.
- Post-reboot `version` and `status` verification passed.
- Rollback precondition confirmed before flash:
  - v2321 rollback image SHA256 matched `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
  - v2237 fallback image SHA256 matched `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`.
  - final v48 fallback image was present.
  - TWRP/recovery image was present and the checked helper exercised the recovery path.
- Rollback needed: no.

## Health

- Pre-flash resident: `A90 Linux init 0.11.24 (v3192-gpu-g2-mmap-probe)`.
- Pre-flash selftest: `pass=12 warn=1 fail=0`.
- Post-flash selftest before GPU ladder: `pass=12 warn=1 fail=0`.
- Post-G3 selftest: `pass=12 warn=1 fail=0`.
- One post-flash `selftest verbose` attempt hit serial command framing garble; a short `version` command immediately passed, and the retried selftest passed. This was treated as transport noise, not a resident or GPU failure.

## GPU Ladder

- `gpu g0-fwclass-prepare`: `result=ok`; firmware cache files verified; no power write/ioctl/mmap in G0 prepare.
- `gpu g1-context-probe --timeout-ms 5000 --materialize-devnode`: `result=created-destroyed`, `timed_out=0`, `open_elapsed_ms=125`, `total_elapsed_ms=126`.
- `gpu g2-mmap-probe --timeout-ms 5000 --materialize-devnode`: `result=mapped-unmapped`, `timed_out=0`, `mmap_rc=0`, `munmap_rc=0`, `free_rc=0`, `destroy_rc=0`, `total_elapsed_ms=9`.
- `gpu g3-noop-submit-probe --timeout-ms 5000 --materialize-devnode`: `result=submitted-fenced-retired`, `timed_out=0`, `child_killed=0`, `child_reaped=1`, `child_status=0x0`, `total_elapsed_ms=9`.

## G3 Detail

- G3 scope: `kgsl-noop-submit-fence-probe`.
- Parent KGSL access: `parent_enters_open=0`, `parent_enters_ioctl=0`.
- KGSL allowlist: draw context create, GPU object alloc/info/sync, GPU command, timestamp event, waittimestamp, readtimestamp, GPU object free, draw context destroy.
- PM4 source: `mesa-freedreno-pkt7-cp-nop`.
- PM4 constants: `CP_TYPE7_PKT=0x70000000`, `CP_NOP=0x10`.
- Noop IB: `noop_dwords=2`, `noop_bytes=8`, `noop_header=0x70100001`, `noop_payload=0x0`.
- Cache sync: `sync_rc=0`, `sync_length=8`.
- Submit: `submit_rc=0`, `submit_timestamp=1`.
- Fence: `timestamp_event_rc=0`, `fence_poll_rc=1`, `fence_poll_revents=0x1`, `fence_close_rc=0`.
- Retirement: `wait_rc=0`, `readtimestamp_rc=0`, `retired_timestamp=1`.
- Cleanup: `munmap_rc=0`, `free_deferred=0`, `free_rc=0`, `destroy_rc=0`, `close_rc=0`.
- Boundary: `render_attempted=0`, `power_write_attempted=0`.

## Kernel Log Check

- Filter checked KGSL/Adreno/GMU/GPU fault, hang, snapshot, error, timeout, and related IOMMU lines after the live probe.
- No GPU fault, hang, snapshot, timeout, or KGSL submit error was observed.
- Matching non-error entries were boot-time KGSL IOMMU registration and `a640_zap` load/reset messages.
- The `run /bin/busybox sh -c ...` wrapper emitted Android linker-configuration warnings; these were from the userland command wrapper and not GPU faults.

## Decision

V3195 validates the G3 rung: userspace can submit a minimal KGSL command stream, obtain a timestamp fence, observe immediate retirement, and clean up without render, KMS, proprietary blob, power-rail, or security-recon paths. The next clean rung is G4: bounded solid/triangle render setup, still staying within freedreno/KGSL-direct source-derived command construction.
