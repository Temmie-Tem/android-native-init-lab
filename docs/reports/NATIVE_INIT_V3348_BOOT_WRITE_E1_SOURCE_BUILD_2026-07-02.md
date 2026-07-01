# Native Init V3348 §0.2 Write-Probe Rung E1 (first boot-block pwrite) Source Build

- Cycle: `V3348`
- Decision: `v3348-boot-write-e1-source-build-pass`
- Init: `A90 Linux init 0.11.112 (v3348-boot-write-e1)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3348_boot_write_e1.img`
- Boot SHA256: `b0165848bce010dc46a8a99c16b7688dfaa3f0cb68b4a2880d90d7ddc519c8cf`
- Helper SHA256: `fa395d3ecb6944a57487f3966948a634596157e4de3fdc39575a2fc502d1ceef`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3335_gpu_z3_primary_setcrtc.img`

## Change

- Adds the CMD_DANGEROUS, token-gated `boot-write-e1 <token>` command (`a90_boot_write_e1.c`) — the §0.2 E1 rung and the only self-dd file with a `pwrite`.
- Read-then-write-IDENTICAL to a CONFIRMED-ZERO 4096B sector in the boot tail slack (past the parsed boot-image content, 1 MiB before the partition end). Fail-closed boot-header parse; every boot-node fd is O_NOFOLLOW and identity-confirmed; write is verified by an O_DIRECT region readback and an O_DIRECT full-partition SHA before/after.
- Marked CMD_DANGEROUS and removed from the menu allow-list, so it cannot run during the auto-menu without an explicit hide/menu-settle.

## Validation Contract

- PASS requires post-flash `selftest fail=0`, `version` 0.11.112, and after a recovery drill + `hide`, `boot-write-e1 BOOT-WRITE-PROBE-E1-TAILSLACK` emitting `slack_zero=1`, a recorded `pwrite_rc`, `region_match=1` (if written), `full_match=1`, then rollback to `v2321` with `selftest fail=0`.
- On UFS the interrupted-write residual is externally-recoverable (boot-only); the operator must confirm Odin/TWRP recovery before dispatch.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: ``
- Candidate type: `boot-write-e1-candidate`.
