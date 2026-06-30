# Runtime Kernel REPL live call proof - get_diplayport_status

Date: 2026-07-01

## Summary

- Target: `get_diplayport_status` (symbol spelling in the image/source is `diplayport`).
- Device action: yes, boot partition only through `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`.
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`.
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`.
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
- Result: PASS. `get_diplayport_status()` returned stable `0x0` twice under the no-argument read-only status contract.
- End state: rolled back to v2321; final `version`, `selftest`, and `status` passed with `selftest fail=0`.

## Candidate Selection

`get_diplayport_status` was selected as a new one-target proof outside the stopped scheduler-counter sub-goal. It is a no-argument CCIC/DisplayPort status getter and the current image body either returns `0` when the CCIC data pointer is NULL or reads the status field and emits its built-in `printk` status line before returning the same field.

Adjacent candidates checked during host triage were not selected:

| Candidate | Disposition |
| --- | --- |
| `get_ddr_revision_id_2` | Parked; same DDR revision family as the earlier failed/parked revision target and calls `qcom_smem_get` plus `printk`. |
| `get_debug_reset_header` | Parked; allocates, reads a debug partition, logs, and frees. |
| `get_empty_filp` | Parked; allocates a `struct file`, calls capability/security/RCU paths. |
| `get_dump_page` | Parked; reaches `__get_user_pages`. |

Classifier CLI after seeding showed exactly one selected target as `SAFE-SCALAR` and the four parked neighbors as `DENY`.

## Static Gate

Host validation:

- `py_compile`: PASS for `workspace/public/src/scripts/revalidation/a90_repl.py` and `tests/test_a90_repl.py`.
- Focused tests: PASS, `Ran 14 tests`.
- Classifier CLI: PASS, counts `SAFE-SCALAR=1`, `DENY=4` for the selected/parked candidate set.

Static proof constraints added for the selected target:

- Source signature: `extern int get_diplayport_status(void)` from `include/linux/ccic/s2mm005_ext.h:98`.
- Pointer arguments: none.
- C1 identity: verified by `disasm-signature+xref+map`.
- Link address: `0xffffff80095a5f14`.
- Direct BL xref count: `1`.
- First BL target: `printk` at the verified link address.
- No argument pointer dereferences before the first BL or return.
- Context-call count: `0`.
- Next symbol boundary: `process_check_accessory` at `+0x58`.
- Current-image word pinning: all 22 expected instruction words matched, including the JOPP entry, global CCIC pointer load, NULL branch, status load, `printk` call, return reload, RET, and next-entry guard.

## Contract

Input contract:

`get_diplayport_status()` is called with no arguments. The CCIC/DisplayPort state is treated as read-only. The function may emit its built-in `printk` status line. No returned pointer is dereferenced or freed.

Return contract:

The returned `int` status value must be stable across the short proof run and must be in `0..0xff`.

## Live Proof

Command:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --timeout 90 \
  --dmesg-tail 80 \
  --safe-op-retries 5 \
  --retry-delay-sec 0.75 \
  --evidence-dir workspace/private/runs/kernel/live-call-proof-get-diplayport-status-20260701/proof \
  get_diplayport_status
```

Public result:

```json
{
  "decision": "a90-repl-live-call-proof-get_diplayport_status-pass",
  "ok": true,
  "proof_status": "trusted-under-ccic-displayport-status-read-only-contract",
  "observed_return_value": "0x0",
  "repeat_count": 2,
  "all_returns_in_range": true,
  "all_returns_stable": true,
  "raw_runtime_values_redacted": true
}
```

Case table:

| Case | Expected | Observed | Result |
| --- | --- | --- | --- |
| `get_diplayport_status-read-1` | status in `0x0..0xff` | `0x0` | PASS |
| `get_diplayport_status-read-2` | same value as first call | `0x0` | PASS |

The private evidence includes the per-boot slide and runtime target address. These raw runtime values are intentionally absent from this public report.

## Timing

Timeline source: `workspace/private/runs/kernel/live-call-proof-get-diplayport-status-20260701/result.json`.

| Phase | Elapsed |
| --- | ---: |
| candidate flash helper | `64.665s` |
| candidate flash start to boot ready | `85.473s` |
| candidate boot/health to ready | `20.808s` |
| live proof session | `5.280s` |
| rollback flash helper | `64.272s` |
| rollback flash start to boot ready | `84.964s` |
| rollback boot/health to ready | `20.692s` |
| total candidate-start to rollback-ready | `176.173s` |

## Rollback And End State

Rollback to v2321 was performed through `native_init_flash.py` with pinned SHA and matching readback SHA. Final explicit bridge checks passed:

- `a90ctl.py --timeout 30 version`: v2321 clean identity baseline.
- `a90ctl.py --timeout 30 selftest`: `pass=11 warn=1 fail=0`.
- `a90ctl.py --timeout 30 status`: completed with `selftest fail=0`.

## Function Map Entry

```json
{
  "symbol": "get_diplayport_status",
  "status": "live-proven",
  "trusted_input_contract": "no arguments; CCIC/DisplayPort status state is read-only; function may emit its built-in printk status line; no returned pointer is dereferenced or freed",
  "return_contract": "int status value is stable across repeated proof calls and in 0..0xff",
  "observed_return_value": "repeated no-argument calls returned stable CCIC DisplayPort status 0x0",
  "cleanup": "n/a-scalar-read-only",
  "auto_call_policy": "one-target-proof-only-not-mass-call"
}
```
