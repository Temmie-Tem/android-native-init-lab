# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: sec_debug state batch

Date: 2026-07-01

- Decision: `a90-repl-live-call-proof-sec-debug-state-batch-pass`
- Scope: bounded same-shape live-call proof using `call-proof-batch`; boot partition only; rollback to `v2321`
- Targets: `sec_debug_is_enabled(void)`, `sec_debug_level(void)`
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private evidence: `workspace/private/runs/kernel/live-call-proof-sec-debug-state-batch-20260701T093249Z/proof/a90_repl_evidence.json`
- Private result: `workspace/private/runs/kernel/live-call-proof-sec-debug-state-batch-20260701T093249Z/result.json`
- Private timeline: `workspace/private/runs/kernel/live-call-proof-sec-debug-state-batch-20260701T093249Z/timeline.json`

## Target Selection

This run follows the 2026-07-01 batch cadence: same-shape read-only state
getters were grouped into one `v1-repl` boot session and one rollback. The
Samsung `sec_debug` header exposes adjacent no-argument getters:
`sec_debug_is_enabled()` and `sec_debug_level()`. Both are state-observation
queries and add platform debug-policy visibility to the REPL function map.

`sec_debug_is_enabled_for_ssr()` was deliberately parked. Its source type is
`int`, it has only one direct xref in the current image, and it was not needed
to prove the same-shape `sec_debug` state batch. The batch therefore stayed
limited to the two no-argument getters with clear return contracts.

Trusted contracts:

- `sec_debug_is_enabled`: no arguments; pinned Samsung `sec_debug` enabled
  state leaf; return must be exactly `0` or `1`; repeated values must stay
  stable in the short proof window.
- `sec_debug_level`: no arguments; pinned Samsung `sec_debug` level leaf;
  return is a `uint32_t`; repeated values must stay stable in the short proof
  window.
- Neither return is treated as a pointer; nothing returned is dereferenced or
  freed.

## Static Gate

`sec_debug_is_enabled`:

- Address: `sec_debug_is_enabled=0xffffff80086e37cc`.
- Resolution: `exact-leaf-map+xref+word-boundary`, verified true.
- Export candidate count: `0`.
- Direct BL xrefs: `26`.
- JOPP entry: yes.
- Source declaration: `extern bool sec_debug_is_enabled(void)` at
  `include/linux/samsung/debug/sec_debug.h:305`.
- C1 safety tier after target-limited seeding: `SAFE-SCALAR`.
- Required valid pointer args: none.
- Next-symbol boundary: `sec_modem_loading_fail_to_bootloader` at `+0x38`.

Static word checks pinned the full body and guard:

`0xb0014e48 0xb0014e49 0x90012f2a 0x5289e98b 0x91075129 0x9116414a 0xb941d108 0x6b0b011f 0x9a8a0128 0xb9400108 0x7100011f 0x1a9f07e0 0xd65f03c0 0x00be7bad`

`sec_debug_level`:

- Address: `sec_debug_level=0xffffff80086e3bb4`.
- Resolution: `exact-leaf-map+xref+word-boundary`, verified true.
- Export candidate count: `0`.
- Direct BL xrefs: `1`.
- JOPP entry: yes.
- Source declaration: `extern unsigned int sec_debug_level(void)` at
  `include/linux/samsung/debug/sec_debug.h:306`.
- C1 safety tier after target-limited seeding: `SAFE-SCALAR`.
- Required valid pointer args: none.
- Next-symbol boundary: `sec_debug_is_enabled_for_ssr` at `+0x10`.

Static word checks pinned the full body and guard:

`0xb0014e48 0xb941d100 0xd65f03c0 0x00be7bad`

For both targets, the generic 64-byte classifier scan can include following
`sec_debug` code after the exact next-symbol boundary. This proof treats the
explicit next-symbol body and guard as the function-body authority.

## Live Run

Flash gate:

- Rollback image `v2321`, deeper fallback `v2237`, final fallback `v48`, and
  TWRP recovery artifacts were present before candidate flash.
- Baseline v2321 `version/status/selftest` passed before candidate flash.
- Candidate flash used `native_init_flash.py`; pushed-image SHA and boot
  readback SHA matched the candidate SHA.
- Candidate helper `version/status` verification passed after reboot.
- The first explicit candidate `selftest` attempt hit serial `AT` echo / END
  marker loss. After bridge restart, candidate `selftest` passed with
  `pass=11 warn=1 fail=0`.
- REPL selftest returned `a90-repl-v2a1-selftest-pass`.

Observed public values:

| Target | Read 1 | Read 2 | Result |
| --- | ---: | ---: | --- |
| `sec_debug_is_enabled` | `0x0` | `0x0` | PASS |
| `sec_debug_level` | `0x4f4c` | `0x4f4c` | PASS |

`sec_debug_is_enabled` returned bool values and stayed stable.
`sec_debug_level` returned a `uint32_t` value and stayed stable. Raw runtime
values and the KASLR slide are private-only and not committed.

Health and rollback:

- Post-proof candidate `version/status/selftest` passed with
  `pass=11 warn=1 fail=0`.
- Rollback to `v2321` used `native_init_flash.py`; pushed-image SHA and boot
  readback SHA matched the v2321 SHA.
- Rollback helper `version/status` verification passed.
- The first standalone final `selftest` attempt hit serial END marker loss.
  After bridge restart, final v2321 standalone `selftest` passed with
  `pass=11 warn=1 fail=0`.
- Final bridge status was `connected-no-immediate-error`.

## Timing

Timing was recorded in:

- `workspace/private/runs/kernel/live-call-proof-sec-debug-state-batch-20260701T093249Z/timeline.json`.

The live proof started at `2026-07-01T09:32:49Z`.

| Phase | Elapsed |
| --- | ---: |
| baseline bridge/version/status/selftest preflight | `2.144s` host-observed |
| candidate flash helper total | `65.703s` |
| candidate selftest first attempt | marker loss at `10.129s` |
| candidate bridge restart + selftest retry + REPL selftest | `8.038s` host-observed |
| live proof batch | `8.128s` host-observed |
| post-proof candidate version/status/selftest | `1.233s` host-observed |
| rollback flash helper total | `64.381s` |
| final selftest first attempt | marker loss at `10.200s` |
| final bridge status after marker loss | `0.330s` host-observed |
| final bridge restart | `2.130s` host-observed |
| final selftest retry | `0.440s` host-observed |
| final bridge status retry | `0.330s` host-observed |

The helper total rows are retained for compatibility with prior reports and
are not additive. All serial bridge operations in the accepted live path were
run sequentially.

## Validation

Host validation:

- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/revalidation/a90_repl.py tests/test_a90_repl.py`
- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 tests/test_a90_repl.py CallSafetyClassificationTests SelftestIntegrationTests.test_call_proof_sec_debug_state_batch_passes_with_no_arg_contracts`
- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/a90_repl.py call-safety-classify --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img --no-objdump sec_debug_is_enabled sec_debug_level`
- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 tests/test_a90_repl.py`

Live validation:

- Candidate flash passed with matching candidate readback SHA.
- Candidate `selftest` retry and REPL selftest passed.
- `call-proof-batch sec_debug_is_enabled sec_debug_level` passed in one REPL
  session.
- Post-proof health passed.
- Rollback to v2321 passed with matching rollback readback SHA.
- Final v2321 standalone `selftest` retry and bridge status passed.

## Function Map Entries

`sec_debug_is_enabled` is live-proven only under this contract:

- Input: no arguments.
- Static body: pinned Samsung `sec_debug` enabled-state leaf; ret before
  `sec_modem_loading_fail_to_bootloader`.
- Return: bool value, exactly `0` or `1`, stable across the short repeated
  proof.
- Observed live result: `0x0`, `0x0`.
- Auto-call policy: same-session batch proof only, not a mass-call permission.

`sec_debug_level` is live-proven only under this contract:

- Input: no arguments.
- Static body: pinned Samsung `sec_debug` level read leaf; ret before
  `sec_debug_is_enabled_for_ssr`.
- Return: `uint32_t`, stable across the short repeated proof.
- Observed live result: `0x4f4c`, `0x4f4c`.
- Auto-call policy: same-session batch proof only, not a mass-call permission.
