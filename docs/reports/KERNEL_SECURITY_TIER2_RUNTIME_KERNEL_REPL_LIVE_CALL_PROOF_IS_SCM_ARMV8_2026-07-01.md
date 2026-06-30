# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: is_scm_armv8

Date: 2026-07-01

## Scope

- Target: `is_scm_armv8`.
- Device action: yes, boot partition only through
  `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`.
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`.
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`.
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
- Private evidence:
  `workspace/private/runs/kernel/live-call-proof-is-scm-armv8-20260630T230729Z/`.

This unit revisits a previously rejected SCM candidate without weakening the safety gate. The risky
path in `is_scm_armv8()` is the first-call initialization path: when `scm_version == SCM_UNKNOWN`,
the function executes SMC probing and writes SCM convention state. The proof therefore pre-peeks the
cached `scm_version` word and refuses to call the function unless that cache is already nonzero and
one of the known enum values.

## Static Gate

Host validation passed before live call:

- `py_compile` for `workspace/public/src/scripts/revalidation/a90_repl.py` and
  `tests/test_a90_repl.py`.
- Focused classifier/source/fake-proof tests: `Ran 4 tests`, `OK`.
- Full fake `SelftestIntegrationTests`: `Ran 124 tests`, `OK`.
- Classifier CLI over `is_scm_armv8`: `SAFE-SCALAR=1`, seed count `131`.

Static identity:

| Target | Link VA | Method | Xrefs | Boundary | Source Contract |
| --- | ---: | --- | ---: | --- | --- |
| `is_scm_armv8` | `0xffffff800869493c` | `export-recovery` | `29` | `scm_call2 +0xe8` | `extern bool is_scm_armv8(void)` |

The source implementation is `drivers/soc/qcom/scm.c:566` and the exported declaration is
`include/soc/qcom/scm.h:112`. The proof gates the current-image cached return path words
(`scm_version` load, unknown-cache branch, cached bool compare/cset/ret) and also gates SMC-path
sentinel words so the runtime guard covers the exact hazardous branch it is avoiding.

## Live Proof

Passing command:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --timeout 180 \
  --dmesg-tail 80 \
  --safe-op-retries 5 \
  --retry-delay-sec 0.75 \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/live-call-proof-is-scm-armv8-20260630T230729Z/proof/call-proof \
  is_scm_armv8
```

Public result:

```json
{
  "decision": "a90-repl-live-call-proof-is_scm_armv8-pass",
  "ok": true,
  "proof_status": "trusted-under-cached-scm-version-bool-contract",
  "cached_scm_version_value": "0x3",
  "cached_scm_version_class": "SCM_ARMV8",
  "observed_return_value": "0x1",
  "expected_return_from_cached_scm_version": "0x1",
  "repeat_count": 2,
  "scm_version_unchanged": true
}
```

Case table:

| Case | Cached SCM version | Expected | Observed | Result |
| --- | ---: | ---: | ---: | --- |
| `is_scm_armv8-cached-read-1` | `0x3` | `0x1` | `0x1` | PASS |
| `is_scm_armv8-cached-read-2` | `0x3` | `0x1` | `0x1` | PASS |

The private evidence contains the slide and runtime addresses. Those raw runtime values are not
included in this public report.

## Timing

Timeline source:

- `workspace/private/runs/kernel/live-call-proof-is-scm-armv8-20260630T230729Z/timeline.json`.

Wrapper timeline:

| Phase | Elapsed |
| --- | ---: |
| candidate preflash marker-fail attempt | `0.097s` |
| candidate flash start to helper done | `63.752s` |
| candidate flash start to explicit boot ready | `73.642s` |
| candidate explicit health command total | `1.38s` |
| REPL selftest | `5.68s` |
| live proof | `6.54s` |
| live session total | `28.268s` |
| rollback flash start to helper done | `63.684s` |
| rollback flash start to helper boot ready | `71.936s` |
| final explicit health command total | `20.68s` |
| final standalone version retry | `0.46s` |
| candidate start to rollback helper ready | `195.440s` |
| candidate start to final health done | `249.686s` |

Candidate helper phase timings:

| Phase | Elapsed |
| --- | ---: |
| `inspect_local_image` | `0.062s` |
| `native_to_recovery` | `0.303s` |
| `wait_recovery_adb` | `27.128s` |
| `adb_push` | `0.847s` |
| `remote_sha256` | `0.107s` |
| `boot_dd_write` | `0.439s` |
| `boot_readback_sha256` | `0.353s` |
| `flash_boot_image` | `1.747s` |
| `reboot_twrp_to_system` | `2.392s` |
| `verify_native_init` | `31.986s` |
| `total` | `63.685s` |

Rollback helper phase timings:

| Phase | Elapsed |
| --- | ---: |
| `inspect_local_image` | `0.059s` |
| `native_to_recovery` | `0.303s` |
| `wait_recovery_adb` | `27.143s` |
| `adb_push` | `0.842s` |
| `remote_sha256` | `0.108s` |
| `boot_dd_write` | `0.442s` |
| `boot_readback_sha256` | `0.351s` |
| `flash_boot_image` | `1.742s` |
| `reboot_twrp_to_system` | `2.312s` |
| `verify_native_init` | `31.972s` |
| `total` | `63.600s` |

Notes:

- A first candidate flash command used `--expect-version v1-repl`; it stopped before reboot or boot
  write because the v1-repl image intentionally preserves the v2321 native-init identity string.
  The successful retry used the v2321 identity marker and proved v1-repl residency through REPL
  selftest.
- Final explicit `version` initially hit serial `AT` noise and was retried standalone. The retry
  passed, and final `selftest/status` had already passed with `selftest pass=11 warn=1 fail=0`.

## Rollback And End State

Rollback to v2321 was performed through `native_init_flash.py` with pinned SHA and matching readback
SHA. Final checks passed:

- `a90ctl.py version`: `v2321-usb-clean-identity-rodata`.
- `a90ctl.py selftest`: `pass=11 warn=1 fail=0`.
- `a90ctl.py status`: completed with `selftest pass=11 warn=1 fail=0`.

Final resident is v2321.

## Function Map Entry

```json
{
  "symbol": "is_scm_armv8",
  "status": "live-proven",
  "trusted_input_contract": "no arguments; proof first verifies scm_version is already cached nonzero so the function takes only the cached read-only return path and does not execute SMC initialization",
  "return_contract": "bool equals cached scm_version armv8 classification: SCM_LEGACY returns 0, SCM_ARMV8_32/64 returns 1, repeated calls stable and scm_version unchanged",
  "observed_return_value": "repeated cached-path calls returned stable bool 0x1 for cached scm_version 0x3",
  "cleanup": "n/a-scalar-cached-read-only",
  "auto_call_policy": "cached-path-proof-only-not-mass-call"
}
```
