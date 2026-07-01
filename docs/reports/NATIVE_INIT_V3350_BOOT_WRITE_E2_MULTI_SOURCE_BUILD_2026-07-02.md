# Native Init V3350 §0.2 Write-Probe E2 Multi-Offset Source Build

- Cycle: `V3350`
- Decision: `v3350-boot-write-e2-multi-source-build-pass`
- Init: `A90 Linux init 0.11.114 (v3350-boot-write-e2-multi)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3350_boot_write_e2_multi.img`
- Boot SHA256: `1238a1e4b701e5d9038aefa85dd0dac3968d0d5291af39b80db9540167c4427c`
- Helper SHA256: `fa395d3ecb6944a57487f3966948a634596157e4de3fdc39575a2fc502d1ceef`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3335_gpu_z3_primary_setcrtc.img`

## Change

- Adds the token-gated `boot-write-e2 <token>` command for the E2 rung. It reuses the E1 guarded write path but selects four spread 4096B targets in confirmed-zero tail slack, one from each quarter of `[roundup(used_len), size - 1 MiB)`.
- Every selected sector is read first and must be all-zero. The command writes only those same bytes back to the same offsets, fsyncs once, verifies each target with O_DIRECT readback, and compares O_DIRECT full-partition SHA before/after.
- `boot-write-e2` is `CMD_DANGEROUS`, not menu-allowed, and requires explicit hide/menu-settle before dispatch. This is a source-build preparation only; no live write is claimed here.

## Validation Contract

- PASS requires post-flash `selftest fail=0`, `version` 0.11.114, and after a recovery drill + `hide`, `boot-write-e2 BOOT-WRITE-PROBE-E2-MULTI-TAILSLACK` emitting `target_count=4`, four `targetN_off` lines with `slack_zero=1`, `pwrite_count=4` (or a clean refusal), `region_match_all=1`, `full_match=1`, then rollback to `v2321` with `selftest fail=0`.
- The AGENTS checked-helper flash path remains the only path used to install this candidate; the E2 live command itself remains separately operator-gated because it performs boot-block identity writes under the self-dd experiment.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: ``
- Candidate type: `boot-write-e2-multi-candidate`.
