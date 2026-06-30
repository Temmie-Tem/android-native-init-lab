# KERNEL SECURITY Tier-2 Runtime Kernel REPL — Current State Batch Live Call Proof

Date: 2026-07-01

## Result

PASS. Three same-shape current-task state query targets were proven in one
`v1-repl` boot session, then the device was rolled back to the clean v2321
baseline.

This unit follows the operator `BATCH + SATURATION-STOP + PIVOT` correction:
the live flash was amortized across adjacent, read-only current state queries
instead of spending one boot per target.

## Batch Targets

| target | contract | C1 identity | source contract | live result |
| --- | --- | --- | --- | --- |
| `current_umask` | no args; read current task fs umask | `export-recovery`, `0xffffff80082d3a24`, direct-BL xrefs `14` | `extern int current_umask(void)` from `include/linux/fs.h:2257` | two calls returned stable umask `0x12` |
| `in_group_p` | scalar `kgid_t`; read current credentials/group list | `export-recovery`, `0xffffff80080e211c`, direct-BL xrefs `30` | `extern int in_group_p(kgid_t)` from `include/linux/cred.h:67` | gid `0` returned `1` twice; gid `0x7fff` returned `0` twice |
| `in_egroup_p` | scalar `kgid_t`; read current effective credentials/group list | `export-recovery`, `0xffffff80080e218c`, direct-BL xrefs `8` | `extern int in_egroup_p(kgid_t)` from `include/linux/cred.h:68` | gid `0` returned `1` twice; gid `0x7fff` returned `0` twice |

All three targets are `SAFE-SCALAR`, leaf in the current image, have no early
argument-pointer dereference, and have exact current-image word gates.

Parked adjacent candidates stayed denied:

- `current_chrooted`: `DENY`, C1 unverified, zero direct-BL xrefs, path/spinlock helpers.
- `capable` / `ns_capable`: `DENY`; static disassembly shows a current task flag store after `security_capable`, so not read-only.
- `has_capability` / `has_capability_noaudit`: `DENY`, context-sensitive helper calls and no scalar-flow proof.
- `task_active_pid_ns`, `pid_nr_ns`, `pid_vnr`: `DENY`, pre-call pointer dereference without a new valid-pointer contract.

## Static / Host Validation

Host validation passed before live flash:

- `py_compile`: `a90_repl.py` and `tests/test_a90_repl.py`.
- Focused unittest targets:
  - `CallSafetyClassificationTests`.
  - `SelftestIntegrationTests.test_call_proof_current_state_batch_candidates_pass_in_one_fake_session`.
- Full unittest suite: `tests/test_a90_repl.py` ran `161` tests, `OK`.
- CLI `call-safety-classify` over the batch plus parked neighbors:
  - `SAFE-SCALAR=3`: `current_umask`, `in_group_p`, `in_egroup_p`.
  - `DENY=8`: parked candidates listed above.

The fake integration test runs all three targets through one `ReplSession`,
matching the live batch cadence.

## Live Validation

Flash gates were followed:

- Rollback/fallback/TWRP artifacts were present.
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
- `status`: `selftest pass=11 warn=1 fail=0`.
- `selftest`: `pass=11 warn=1 fail=0`.

Candidate flash:

- `native_init_flash.py` wrote boot only through `--from-native`.
- Recovery/TWRP ADB was reached before the boot write.
- Remote pushed image SHA matched the candidate SHA.
- Boot readback SHA matched the candidate SHA.
- Helper `version/status` passed after boot. The image reports the v2321 native-init
  version string because the v1-repl patch lives in the kernel/sysfs path, not the
  native-init version banner.
- First candidate `selftest` attempt hit serial `AT` desync; `version` resynced the
  bridge and retry returned `pass=11 warn=1 fail=0`.

Candidate phase timings:

| phase | elapsed |
| --- | ---: |
| `inspect_local_image` | `0.035s` |
| `native_to_recovery` | `0.303s` |
| `wait_recovery_adb` | `26.121s` |
| `adb_push` | `0.841s` |
| `remote_sha256` | `0.099s` |
| `boot_dd_write` | `0.454s` |
| `boot_readback_sha256` | `0.218s` |
| `flash_boot_image` | `1.612s` |
| `reboot_twrp_to_system` | `2.501s` |
| `verify_native_init` | `32.739s` |
| `total` | `63.377s` |

Same-session proof order:

1. `current_umask`
   - Decision: `a90-repl-live-call-proof-current_umask-pass`.
   - Two calls returned stable umask `0x12`.
2. `in_group_p`
   - Decision: `a90-repl-live-call-proof-in_group_p-pass`.
   - `in_group_p(0)` returned `1` twice.
   - `in_group_p(0x7fff)` returned `0` twice.
3. `in_egroup_p`
   - Decision: `a90-repl-live-call-proof-in_egroup_p-pass`.
   - `in_egroup_p(0)` returned `1` twice.
   - `in_egroup_p(0x7fff)` returned `0` twice.

Public summaries redact raw runtime addresses and slide values. Raw private
evidence is under
`workspace/private/runs/kernel/live-call-proof-current-state-batch-20260701/`.

## Rollback

Rollback to v2321 was performed through `native_init_flash.py`.

- Local v2321 marker and SHA were verified.
- Recovery/TWRP ADB was reached before the boot write.
- Remote pushed image SHA matched the rollback SHA.
- Boot write completed.
- Boot readback SHA matched
  `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
- Helper `version/status` passed after reboot.
- First manual final `selftest` attempt hit the same serial `AT` desync; `version`
  resynced the bridge and retry returned `pass=11 warn=1 fail=0`.

Rollback phase timings:

| phase | elapsed |
| --- | ---: |
| `inspect_local_image` | `0.050s` |
| `native_to_recovery` | `0.303s` |
| `wait_recovery_adb` | `27.129s` |
| `adb_push` | `0.852s` |
| `remote_sha256` | `0.111s` |
| `boot_dd_write` | `0.429s` |
| `boot_readback_sha256` | `0.344s` |
| `flash_boot_image` | `1.737s` |
| `reboot_twrp_to_system` | `2.548s` |
| `verify_native_init` | `32.482s` |
| `total` | `64.311s` |

Final resident state is clean v2321 with `selftest pass=11 warn=1 fail=0`.

## Function Map Update

Promoted contracts:

- `current_umask`: no-argument read-only current task umask query. Trusted only for
  the current REPL process context; do not generalize to arbitrary tasks.
- `in_group_p`: scalar `kgid_t` current credential membership query. Proven for
  gid `0` and a fixed unlikely gid `0x7fff` in the current REPL process context.
- `in_egroup_p`: scalar `kgid_t` current effective credential membership query.
  Proven for gid `0` and fixed unlikely gid `0x7fff` in the current REPL process
  context.

These entries are batch proof targets, not broad permission to call behavior-changing
capability helpers. `capable` and `ns_capable` remain parked because they set current
task state and are not read-only.
