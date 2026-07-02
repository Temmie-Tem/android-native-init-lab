# Native Init V3354 §0.2 Write-Probe E4 Header Source Build

- Cycle: `V3354`
- Decision: `v3354-boot-write-e4-header-source-build-pass`
- Init: `A90 Linux init 0.11.118 (v3354-boot-write-e4-header)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3354_boot_write_e4_header.img`
- Boot SHA256: `627b0192d53d9744805c21f151159c177a17827fdd78883a2990faedaa034a43`
- Helper SHA256: `fa395d3ecb6944a57487f3966948a634596157e4de3fdc39575a2fc502d1ceef`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3335_gpu_z3_primary_setcrtc.img`

## Change

- Adds `boot-write-e4 <token>` after the V3353 E3b live pass. E4 writes one 4096B identity block at boot partition offset 0, the Android boot-header sector.
- The command reads the sector first, requires `ANDROID!` magic and a valid boot-header parse, writes exactly the bytes it just read, fsyncs, checks an O_DIRECT sector readback and sector SHA, then compares O_DIRECT full-partition SHA before/after.
- This is the first non-slack write rung. The residual tear risk is boot-header corruption, still boot-only and externally recoverable through the existing v2321 rollback path.

## Validation Contract

- PASS requires post-flash `selftest fail=0`, `version` 0.11.118, and after `hide`, `boot-write-e4 BOOT-WRITE-PROBE-E4-HEADER-SECTOR` emitting `target_off=0`, `len=4096`, `header_magic=ANDROID`, `pwrite_count=1`, `sector_sha_match=1`, `region_match_all=1`, `full_match=1`, then rollback to `v2321` with `selftest fail=0`.
- This is a source-build preparation only; no live V3354 write is claimed here.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: ``
- Candidate type: `boot-write-e4-header-candidate`.
