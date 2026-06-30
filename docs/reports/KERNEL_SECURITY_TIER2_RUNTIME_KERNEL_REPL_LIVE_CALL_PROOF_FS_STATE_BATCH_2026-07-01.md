# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: FS State Batch

Date: 2026-07-01

## Scope

- Targets: `get_max_files`, `get_nr_dirty_inodes`.
- Device action: yes, boot partition only through `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`.
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`.
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`.
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
- Private evidence:
  `workspace/private/runs/kernel/live-call-proof-fs-state-batch-20260701/` and
  `workspace/private/runs/kernel/live-call-proof-fs-state-batch-20260701-attempt2/`.

## Static Gate

Host validation passed before live call:

- `py_compile` for `workspace/public/src/scripts/revalidation/a90_repl.py` and `tests/test_a90_repl.py`.
- Focused tests for classifier coverage, fake batch proof, batch CLI scheduler regression, and seed inventory.
- Full `tests/test_a90_repl.py`: `Ran 169 tests`, `OK`.
- Classifier CLI over the selected targets: both `get_max_files` and `get_nr_dirty_inodes` are `SAFE-SCALAR`.

Static identities:

| Target | Link VA | Method | Xrefs | Boundary | Source Contract |
| --- | ---: | --- | ---: | --- | --- |
| `get_max_files` | `0xffffff800829005c` | `export-recovery` | `1` | `proc_nr_files +0x18` | `extern unsigned long get_max_files(void)` |
| `get_nr_dirty_inodes` | `0xffffff80082b1234` | `disasm-signature+xref+map` | `4` | `proc_nr_inodes +0xf8` | `extern long get_nr_dirty_inodes(void)` |

Both targets have no pointer arguments, no pre-call argument pointer dereferences, no context calls,
and no returned pointer is dereferenced or freed. `get_max_files` has an exact 6-word body gate.
`get_nr_dirty_inodes` has an exact 62-word body gate and implementation fragments pinned to
`fs/inode.c`.

## Live Proof

Passing command:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof-batch \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --timeout 180 \
  --dmesg-tail 80 \
  --safe-op-retries 5 \
  --retry-delay-sec 0.75 \
  --evidence-dir workspace/private/runs/kernel/live-call-proof-fs-state-batch-20260701-attempt2/proof/batch \
  get_max_files get_nr_dirty_inodes
```

Public batch result:

```json
{
  "decision": "a90-repl-live-call-proof-batch-pass",
  "ok": true,
  "target_count": 2,
  "completed_targets": ["get_max_files", "get_nr_dirty_inodes"],
  "host_batch_single_repl_session": true,
  "raw_runtime_values_redacted": true
}
```

Case table:

| Target | Case | Expected | Observed | Result |
| --- | --- | --- | ---: | --- |
| `get_max_files` | read 1 | positive VFS open-file limit | `0x71c6a` | PASS |
| `get_max_files` | read 2 | same value across short repeat | `0x71c6a` | PASS |
| `get_nr_dirty_inodes` | read 1 | nonnegative dirty-inode approximation | `0x6c2a` | PASS |
| `get_nr_dirty_inodes` | read 2 | sane short-repeat value; drift allowed | `0x6c29` | PASS |

The private evidence includes per-boot slide and runtime target addresses. These raw runtime values are
intentionally absent from this public report.

## Timing

Timeline sources:

- Attempt 1: `workspace/private/runs/kernel/live-call-proof-fs-state-batch-20260701/timeline.json`.
- Attempt 2: `workspace/private/runs/kernel/live-call-proof-fs-state-batch-20260701-attempt2/result.json`.

Attempt 1 stopped before any target call because a redundant candidate `a90ctl selftest` hit serial
`AT` echo and missed the `A90P1 END` marker. The candidate flash helper had already verified native
selftest, and rollback completed cleanly. No function-map entry was promoted from attempt 1.

| Attempt 1 Phase | Elapsed |
| --- | ---: |
| candidate flash helper | `64.297s` |
| candidate explicit health before serial parse failure | `11.002s` |
| live proof session | not reached |
| rollback flash helper | `80.313s` |
| rollback explicit health | `1.125s` |

Attempt 2 passed. Because attempt 2 was continued manually after the first host-side serial issue, its
timeline is reconstructed from `native_init_flash` timestamps and Codex command wall time rather than a
single wrapper-owned monotonic timeline.

| Attempt 2 Phase | Elapsed |
| --- | ---: |
| candidate flash helper | `67.083s` |
| candidate flash start to boot ready | `67.083s` |
| candidate status check | `0.336s` |
| REPL selftest | `171.114s` |
| live batch proof | `8.819s` |
| live-session command total | `180.269s` |
| rollback flash helper | `63.646s` |
| rollback flash start to boot ready | `63.646s` |
| final bridge resync and explicit health | `2.918s` |

Operational note: the first final-health check in attempt 2 was mistakenly launched in parallel and hit
the serial bridge transaction lock plus `AT` echo. A host-side `a90_bridge.py restart` resynchronized
the stream; final sequential `version/status/selftest` then passed.

## Rollback And End State

Rollback to v2321 was performed through `native_init_flash.py` with pinned SHA and matching readback
SHA. Final explicit bridge checks passed after bridge resync:

- `a90ctl.py version`: `v2321-usb-clean-identity-rodata`.
- `a90ctl.py status`: completed with `selftest pass=11 warn=1 fail=0`.
- `a90ctl.py selftest`: `pass=11 warn=1 fail=0`.

## Function Map Entries

```json
[
  {
    "symbol": "get_max_files",
    "status": "live-proven",
    "trusted_input_contract": "no arguments; VFS files_stat.max_files is read-only and no returned pointer is dereferenced or freed",
    "return_contract": "unsigned long open-file limit is positive, below the conservative sane count bound, and stable across short-repeat proof calls",
    "observed_return_value": "short-repeat no-argument calls started at 0x71c6a",
    "cleanup": "n/a-fs-vfs-read-only",
    "auto_call_policy": "same-session-batch-proof-only-not-mass-call"
  },
  {
    "symbol": "get_nr_dirty_inodes",
    "status": "live-proven",
    "trusted_input_contract": "no arguments; VFS inode counters are read-only per-CPU aggregates and no returned pointer is dereferenced or freed",
    "return_contract": "long dirty-inode approximation is clamped nonnegative and below the conservative sane count bound; short-repeat drift is allowed",
    "observed_return_value": "short-repeat no-argument calls started at 0x6c2a",
    "cleanup": "n/a-fs-vfs-read-only",
    "auto_call_policy": "same-session-batch-proof-only-not-mass-call"
  }
]
```
