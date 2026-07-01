# Native Init V3351 §0.2 Write-Probe E2 Zero-Population Source Build

- Cycle: `V3351`
- Decision: `v3351-boot-write-e2-zero-population-source-build-pass`
- Init: `A90 Linux init 0.11.115 (v3351-boot-write-e2-zero-population)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3351_boot_write_e2_zero_population.img`
- Boot SHA256: `84b035b494460c2d8976d0c09a1effb3a8f023858f3fa4b1e02120707ae7f89d`
- Helper SHA256: `fa395d3ecb6944a57487f3966948a634596157e4de3fdc39575a2fc502d1ceef`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3335_gpu_z3_primary_setcrtc.img`

## Change

- Revises `boot-write-e2 <token>` after the V3350 clean refusal. V3350 required one all-zero sector in each fixed quarter-band; live evidence showed band 0 had no zero sector, so the probe stopped before any write.
- V3351 scans the whole tail-slack window, records all all-zero 4096B sector offsets, then selects four spread indices from that zero population. Each selected sector is re-read and rechecked as all-zero before any write fd is opened.
- The rest of the safety envelope is unchanged: `CMD_DANGEROUS`, no auto-menu execution, O_NOFOLLOW + identity on every fd, one fsync after the four identity pwrite calls, O_DIRECT per-target readback, and O_DIRECT full-partition SHA before/after.

## Validation Contract

- PASS requires post-flash `selftest fail=0`, `version` 0.11.115, and after `hide`, `boot-write-e2 BOOT-WRITE-PROBE-E2-MULTI-TAILSLACK` emitting `zero_candidates>=4`, four `selectedN_off`/`targetN_off` lines, `pwrite_count=4` (or a clean refusal), `region_match_all=1`, `full_match=1`, then rollback to `v2321` with `selftest fail=0`.
- This is a source-build preparation only; no live V3351 write is claimed here.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: ``
- Candidate type: `boot-write-e2-zero-population-candidate`.
