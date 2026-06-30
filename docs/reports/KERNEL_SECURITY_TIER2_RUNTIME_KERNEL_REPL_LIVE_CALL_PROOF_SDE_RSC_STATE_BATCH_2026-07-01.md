# KERNEL SECURITY Tier-2 Runtime Kernel REPL - SDE RSC State Batch Live Call Proof

Date: 2026-07-01

## Result

PASS. Three adjacent SDE RSC read-only scalar getters were proven in one
`v1-repl` boot session, then the device was rolled back to the clean v2321
baseline.

This unit continues the corrected `BATCH + SATURATION-STOP + PIVOT` cadence:
same-shape state-observation getters are batched in one live session, while
adjacent client-pointer helpers stay parked until they have a separate valid
`struct sde_rsc_client *` contract.

## Batch Targets

| target | contract | C1 identity | source contract | live result |
| --- | --- | --- | --- | --- |
| `get_sde_rsc_current_state` | scalar `rsc_index=0`; return enum state `0..3`, stable across repeat calls | `export-recovery`, `0xffffff8008861bec`, direct-BL xrefs `4` | `enum sde_rsc_state get_sde_rsc_current_state(int rsc_index)` from `include/linux/sde_rsc.h:291` | two calls returned stable `0x1` |
| `get_sde_rsc_primary_crtc` | scalar `rsc_index=0`; return stable u32/int CRTC id, `0` means unavailable | `export-recovery`, `0xffffff8008861b7c`, direct-BL xrefs `1` | `int get_sde_rsc_primary_crtc(int rsc_index)` from `include/linux/sde_rsc.h:299` | two calls returned stable `0x85` |
| `get_sde_rsc_version` | scalar `rsc_index=0`; return revision `0..3`, stable across repeat calls | `export-recovery`, `0xffffff8008861c64`, direct-BL xrefs `1` | `u32 get_sde_rsc_version(int rsc_index)` from `include/linux/sde_rsc.h:319` | two calls returned stable `0x2` |

All three bodies were statically gated with exact current-image word checks,
next-symbol boundaries, scalar-only source signatures, C1 verified
`export-recovery`, and no early argument-pointer dereference.

Parked adjacent candidates stayed denied:

- `sde_rsc_client_get_vsync_refcount`: `DENY`, no seeded valid client-pointer
  contract.
- `sde_rsc_client_reset_vsync_refcount`: `DENY`, no seeded valid client-pointer
  contract.
- `sde_rsc_client_is_state_update_complete`: `DENY`, dereferences `x0` before a
  safe scalar return path and needs a valid client-pointer contract.
- `sde_rsc_client_trigger_vote`: `DENY`, dereferences `x0`, takes locks, and
  can trigger vote/state side effects.

## Static / Host Validation

Host validation passed before live flash:

- `py_compile`: `a90_repl.py` and `tests/test_a90_repl.py`.
- Focused unittest targets:
  - `CallSafetyClassificationTests.test_safe_with_valid_pointer_seed_records_required_args`.
  - `CallSafetyClassificationTests.test_seed_inventory_summary_counts_tiers`.
  - `CallSafetyClassificationTests.test_source_signature_oracle_distinguishes_scalar_and_pointer_args`.
  - `SelftestIntegrationTests.test_call_proof_sde_rsc_state_batch_passes_with_index0_contract`.
- Full unittest suite: `tests.test_a90_repl` ran `163` tests, `OK`.
- CLI `call-safety-classify` over the SDE RSC scalar/client cluster:
  - `SAFE-SCALAR`: `is_sde_rsc_available`, `get_sde_rsc_current_state`,
    `get_sde_rsc_primary_crtc`, `get_sde_rsc_version`.
  - `DENY`: the four adjacent `sde_rsc_client_*` helpers listed above.

The fake integration test runs all three new getters through one `ReplSession`
and asserts the fixed `SDE_RSC_INDEX 0` argument, bounded return ranges, repeat
stability, redaction of raw runtime values, and per-target private evidence.

## Live Validation

Flash gates were followed:

- Rollback/fallback/TWRP artifacts were confirmed before flashing.
- Candidate `boot_linux_tier2_repl_v1_repl.img` SHA256:
  `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`.
- Rollback `boot_linux_v2321_usb_clean_identity_rodata.img` SHA256:
  `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
- Deeper fallback `boot_linux_v2237_supplicant_terminate_poll.img` SHA256:
  `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`.
- Final fallback `boot_linux_v48.img` SHA256:
  `1c87fa59712395027c5c2e489b15c4f6ddefabc3c50f78d3c235c4508a63e042`.

Baseline v2321 health passed before candidate flash:

- `version`: `A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)`.
- `selftest`: `pass=11 warn=1 fail=0`.
- `status`: `selftest pass=11 warn=1 fail=0`.

Candidate flash:

- `native_init_flash.py` wrote boot only through `--from-native`.
- Recovery/TWRP ADB was reached before the boot write.
- Remote pushed image SHA matched the candidate SHA.
- Boot readback SHA matched the candidate SHA.
- Helper `version/status` passed after boot.
- Explicit candidate `version`, `selftest`, and `status` passed after restarting
  the serial bridge and waiting for the bridge to settle.

Same-session proof order:

1. `get_sde_rsc_current_state`
   - Decision: `a90-repl-live-call-proof-get_sde_rsc_current_state-pass`.
   - Two calls with `rsc_index=0` returned stable `0x1`.
   - Return stayed within enum contract `0..3`.
2. `get_sde_rsc_primary_crtc`
   - Decision: `a90-repl-live-call-proof-get_sde_rsc_primary_crtc-pass`.
   - Two calls with `rsc_index=0` returned stable `0x85`.
   - Return stayed within u32/int contract.
3. `get_sde_rsc_version`
   - Decision: `a90-repl-live-call-proof-get_sde_rsc_version-pass`.
   - Two calls with `rsc_index=0` returned stable `0x2`.
   - Return stayed within revision contract `0..3`.

Raw runtime addresses, slide values, and private command logs are kept out of
git under
`workspace/private/runs/kernel/live-call-proof-sde-rsc-state-batch-20260701-attempt2/`.

## Timing

Timeline object was written to private evidence as required by `GOAL.md`:

| marker | UTC timestamp |
| --- | --- |
| `candidate_flash_start` | `2026-06-30T20:18:18.928942+00:00` |
| `candidate_flash_done` | `2026-06-30T20:19:27.247728+00:00` |
| `candidate_boot_ready` | `2026-06-30T20:19:51.734108+00:00` |
| `live_session_start` | `2026-06-30T20:19:54.141968+00:00` |
| `live_session_end` | `2026-06-30T20:20:05.029406+00:00` |
| `rollback_flash_start` | `2026-06-30T20:20:05.029416+00:00` |
| `rollback_flash_done` | `2026-06-30T20:21:09.233760+00:00` |
| `rollback_boot_ready` | `2026-06-30T20:21:33.715346+00:00` |

Per-phase elapsed:

| phase | elapsed |
| --- | ---: |
| candidate flash helper total | `68.319s` |
| candidate post-flash bridge/health to ready | `24.486s` |
| live proof session | `10.887s` |
| rollback flash helper total | `64.204s` |
| rollback post-flash bridge/health to ready | `24.482s` |
| candidate start to rollback ready | `194.786s` |

Candidate helper phase timings:

| phase | elapsed |
| --- | ---: |
| `inspect_local_image` | `0.035s` |
| `native_to_recovery` | `3.956s` |
| `wait_recovery_adb` | `28.135s` |
| `adb_push` | `0.840s` |
| `remote_sha256` | `0.098s` |
| `boot_dd_write` | `0.443s` |
| `boot_readback_sha256` | `0.189s` |
| `flash_boot_image` | `1.571s` |
| `reboot_twrp_to_system` | `2.465s` |
| `verify_native_init` | `32.048s` |
| `total` | `68.270s` |

Rollback helper phase timings:

| phase | elapsed |
| --- | ---: |
| `inspect_local_image` | `0.033s` |
| `native_to_recovery` | `0.553s` |
| `wait_recovery_adb` | `27.135s` |
| `adb_push` | `0.855s` |
| `remote_sha256` | `0.108s` |
| `boot_dd_write` | `0.440s` |
| `boot_readback_sha256` | `0.354s` |
| `flash_boot_image` | `1.758s` |
| `reboot_twrp_to_system` | `2.568s` |
| `verify_native_init` | `32.051s` |
| `total` | `64.157s` |

## Rollback

Rollback to v2321 was performed through `native_init_flash.py`.

- Remote pushed image SHA matched the rollback SHA.
- Boot write completed.
- Boot readback SHA matched
  `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
- Helper `version/status` passed after reboot.
- Explicit final `version`, `selftest`, and `status` passed after bridge restart
  and settle.

Final resident state is clean v2321 with `selftest pass=11 warn=1 fail=0`.

## Operational Note

The first wrapper attempt stopped before any live call because its private
`SOURCE_ROOT` pointed at a missing source tree, causing the source-signature gate
to reject `get_sde_rsc_current_state`. That attempt still rolled back cleanly to
v2321 with final `selftest fail=0`. The passing attempt used the same public code
and the correct kernel source root, then completed the proof and rollback.

## Function Map Update

Promoted contracts:

- `get_sde_rsc_current_state`: read-only scalar SDE RSC state query. Trusted only
  as `get_sde_rsc_current_state(0)`, with enum return `0..3` and repeat stability.
- `get_sde_rsc_primary_crtc`: read-only scalar primary CRTC id query. Trusted
  only as `get_sde_rsc_primary_crtc(0)`, with stable u32/int return.
- `get_sde_rsc_version`: read-only scalar SDE RSC revision query. Trusted only as
  `get_sde_rsc_version(0)`, with revision return `0..3` and repeat stability.

These entries are same-session batch proof targets, not mass-call permissions.
The `sde_rsc_client_*` helpers remain out until a separate valid client-pointer
and side-effect contract exists.
