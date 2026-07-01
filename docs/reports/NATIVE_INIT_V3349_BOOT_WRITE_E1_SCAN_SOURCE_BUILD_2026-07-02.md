# Native Init V3349 §0.2 Write-Probe E1 Tail-Slack Zero-Sector Scan Source Build

- Cycle: `V3349`
- Decision: `v3349-boot-write-e1-scan-source-build-pass`
- Init: `A90 Linux init 0.11.113 (v3349-boot-write-e1-scan)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3349_boot_write_e1_scan.img`
- Boot SHA256: `74929b7528ce262a194c65bd895ddb45b9547161a56a0900551cdd8025ef18d3`
- Helper SHA256: `fa395d3ecb6944a57487f3966948a634596157e4de3fdc39575a2fc502d1ceef`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3335_gpu_z3_primary_setcrtc.img`

## Change

- `boot-write-e1` now SCANS the tail-slack window `[roundup(used_len), size - 1 MiB)` for the FIRST all-zero 4096B sector and targets it, instead of a single fixed offset. V3348 live showed the fixed tail offset held stale non-zero data, so the all-zero gate correctly refused (no write). The scan keeps both safety layers (past parsed content AND confirmed-zero) while finding a genuine zero sector to probe the first pwrite.
- All other E1 safety properties are unchanged (CMD_DANGEROUS, token, fail-closed header, O_NOFOLLOW + identity on every fd, O_DIRECT region readback + full-partition SHA before/after, single pwrite of the confirmed-zero bytes it read).

## Validation Contract

- PASS requires post-flash `selftest fail=0`, `version` 0.11.113, and after a recovery drill + `hide`, `boot-write-e1 BOOT-WRITE-PROBE-E1-TAILSLACK` emitting `have_zero_sector=1`, `slack_zero=1`, `pwrite_rc=4096` (or a clean refusal), `region_match=1`, `full_match=1`, then rollback to `v2321` with `selftest fail=0`. If `have_zero_sector=0` the probe stops with `no-zero-slack` and no write occurs.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: ``
- Candidate type: `boot-write-e1-scan-candidate`.
