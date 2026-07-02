# Native Init V3358 Self-dd F1 Roundtrip Source Build

- Cycle: `V3358`
- Decision: `v3358-self-dd-f1-roundtrip-source-build-pass-live-policy-blocked`
- Init: `A90 Linux init 0.11.121 (v3358-self-dd-f1-roundtrip)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3358_self_dd_f1_roundtrip.img`
- Boot SHA256: `106f797df52bc1c1ca887069dee0d01d3b0a20e00439711f6854520efce7723e`
- Helper SHA256: `fa395d3ecb6944a57487f3966948a634596157e4de3fdc39575a2fc502d1ceef`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3335_gpu_z3_primary_setcrtc.img`

## Change

- Adds `boot-flash-f1 BOOT-FLASH-F1-PAIRED-ROUNDTRIP <candidate-path> <expected-sha256> <expected-version>` as the first content-changing self-dd rung.
- F1 repeats the F0 source-plan checks, captures `before.full` to the approved SD staging root, writes the planned full 64 MiB target image, verifies the target full SHA, then immediately restores `before.full` and verifies the restored full SHA before any reboot.
- If a retained `before.full` snapshot already exists from a failed run, F1 refuses to overwrite it and stops before any target pwrite.
- The command is `CMD_DANGEROUS` and token-gated. It is source-built only in this unit; live execution remains blocked by the policy gate in `AGENTS.md` and design section 12.1.

## Validation Contract

- Static PASS requires the V3358 strings, command registration, and token-gated F1 contract to be present, while preserving the existing F0 read-only source-plan command.
- Live F1 PASS, when separately authorized, will require `target_full_match=1`, `restore_full_match=1`, `result=ok paired-roundtrip-restored`, pstore entries `0`, post-probe `selftest fail=0`, and clean v2321 rollback.
- No live F1 content-changing write is claimed by this source-build report.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: ``
- Candidate type: `self-dd-f1-roundtrip-candidate`.
