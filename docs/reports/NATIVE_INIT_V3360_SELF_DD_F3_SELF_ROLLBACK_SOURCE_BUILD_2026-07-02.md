# Native Init V3360 Self-dd F3 Self-Rollback Source Build

- Cycle: `V3360`
- Decision: `v3360-self-dd-f3-self-rollback-source-build-pass-live-policy-blocked`
- Init: `A90 Linux init 0.11.123 (v3360-self-dd-f3-self-rollback)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3360_self_dd_f3_self_rollback.img`
- Boot SHA256: `2989c292d1a7ae7cd5f9eb78906b2451d717e4221b9c9b76114ddc9054b52a29`
- Helper SHA256: `fa395d3ecb6944a57487f3966948a634596157e4de3fdc39575a2fc502d1ceef`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3335_gpu_z3_primary_setcrtc.img`

## Change

- Adds `boot-flash-f3 BOOT-FLASH-F3-SELF-ROLLBACK <candidate-path> <expected-sha256> <expected-version>` for the self-rollback rung.
- F3 uses the same guarded leave-target primitive as F2, but it is intended to run from a candidate that was itself booted through F2. Its staged target is the v2321 rollback image.
- On success, F3 returns a clean command END with `reboot_required=1` and retains the `before.full` snapshot. The host must immediately reboot and verify v2321.
- On target-write or target-readback failure after any target pwrite, F3 attempts an immediate before.full restore before returning failure. It never reboots itself.
- The command is `CMD_DANGEROUS` and token-gated. It is source-built only in this unit; live execution remains blocked by the F3 policy gate in `AGENTS.md` and design section 12.1.

## Validation Contract

- Static PASS requires the V3360 strings, command registration, and token-gated F3 contract to be present, while preserving the existing F0/F1/F2 commands.
- Live F3 PASS, when separately authorized, will require F2 boot into V3360, F3 `target_full_match=1`, `result=ok rollback-written-ready-to-reboot`, reboot into v2321, v2321 `selftest fail=0`, pstore entries `0`, and retained-snapshot cleanup.
- No live F3 self-rollback write or reboot into v2321 is claimed by this source-build report.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: ``
- Candidate type: `self-dd-f3-self-rollback`.
