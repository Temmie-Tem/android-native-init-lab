# Native Init V3359 Self-dd F2 Boot Candidate Source Build

- Cycle: `V3359`
- Decision: `v3359-self-dd-f2-boot-candidate-source-build-pass-live-policy-blocked`
- Init: `A90 Linux init 0.11.122 (v3359-self-dd-f2-boot-candidate)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3359_self_dd_f2_boot_candidate.img`
- Boot SHA256: `4f51a7a325c014b80571fd1f8982f0510c48ea8b7c666721d4667a54626fd8c9`
- Helper SHA256: `fa395d3ecb6944a57487f3966948a634596157e4de3fdc39575a2fc502d1ceef`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3335_gpu_z3_primary_setcrtc.img`

## Change

- Adds `boot-flash-f2 BOOT-FLASH-F2-BOOT-CANDIDATE <candidate-path> <expected-sha256> <expected-version>` as the first rung that intentionally leaves the boot partition on the verified target image for a host-controlled reboot.
- F2 repeats the F0/F1 source checks, captures `before.full` to the approved SD staging root, writes the planned full 64 MiB target image, and verifies the target full SHA.
- On success, F2 returns a clean command END with `reboot_required=1` and retains the `before.full` snapshot. The host must immediately reboot, verify the self-written candidate, then roll back through `native_init_flash.py`.
- On target-write or target-readback failure after any target pwrite, F2 attempts an immediate before.full restore before returning failure. It never reboots itself.
- The command is `CMD_DANGEROUS` and token-gated. It is source-built only in this unit; live execution remains blocked by the F2 policy gate in `AGENTS.md` and design section 12.1.

## Validation Contract

- Static PASS requires the V3359 strings, command registration, and token-gated F2 contract to be present, while preserving the existing F0 and F1 commands.
- Live F2 PASS, when separately authorized, will require `target_full_match=1`, `result=ok target-written-ready-to-reboot`, reboot into the expected self-written candidate build marker, candidate `selftest fail=0`, pstore entries `0`, and clean v2321 rollback.
- No live F2 content-changing write or reboot into a self-written candidate is claimed by this source-build report.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: ``
- Candidate type: `self-dd-f2-boot-candidate`.
