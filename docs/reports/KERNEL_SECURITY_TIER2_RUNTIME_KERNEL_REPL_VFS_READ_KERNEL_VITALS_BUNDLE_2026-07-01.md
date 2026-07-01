# Kernel REPL VFS-Read Kernel Vitals Bundle

Date: 2026-07-01

## Decision

`a90-repl-vfs-read-kernel-vitals-bundle-pass`.

The REPL VFS-read primitive now has a named `kernel-vitals` observation bundle for
standard `/proc` vital signs. This follows the KEYSTONE-FIRST + RETIRE-SUBSUMED
policy: read file-node equivalents through `filp_open` + `kernel_read` instead of
adding lone getter call-proofs for equivalent counters.

## Scope

- Added `a90_repl.py vfs-bundle kernel-vitals`.
- Paths: `/proc/uptime`, `/proc/loadavg`, `/proc/meminfo`, `/proc/stat`,
  `/proc/vmstat`, and `/proc/version`.
- Bounded read length: `512` bytes per path.
- Raw file bytes, runtime pointers, KASLR slide, serial capture, and command logs
  remain private-only.
- No call-safety tier was relaxed. The bundle reuses the existing VFS-read gate for
  `filp_open`, `kernel_read`, `filp_close`, `__kmalloc`, and `kfree`.

## Timeline Schema

The private run timeline was written in the canonical events-only schema:

```json
{"events":[{"name":"candidate_flash_start","timestamp_utc":"..."}]}
```

The top-level object contains only `events`, and each event contains only `name`
and `timestamp_utc`. The eight required events are present:
`candidate_flash_start`, `candidate_flash_done`, `candidate_boot_ready`,
`live_session_start`, `live_session_end`, `rollback_flash_start`,
`rollback_flash_done`, and `rollback_boot_ready`.

`workspace/public/src/scripts/analysis/analyze_repl_run_timing.py` now rejects
non-canonical `timeline.json` files instead of accepting nested `phases`,
`commands`, `steps`, or `timeline` objects. Nine private timelines with enough
UTC evidence were normalized to the events-only schema; older weak legacy
timelines without sufficient absolute timestamps were left unpromoted and are
skipped by the analyzer.

## Live Validation

Private run:
`workspace/private/runs/kernel/vfs-read-kernel-vitals-bundle-20260701T105200Z/`.

Preconditions:

- Candidate image SHA:
  `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`.
- Rollback image SHA:
  `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
- Deeper fallback images were present, including v2237 and v48.
- Flashing used only `workspace/public/src/scripts/revalidation/native_init_flash.py`.

Result:

- Baseline v2321 health passed before flash.
- Candidate flash matched the expected v1-repl SHA.
- Candidate health first attempt hit the known serial marker/input fragmentation;
  bridge restart plus retry passed.
- REPL selftest passed.
- `kernel-vitals` bundle passed all six paths in one REPL session.
- Post-proof candidate health passed.
- Rollback to v2321 matched the expected SHA.
- Final v2321 health passed: `selftest pass=11 warn=1 fail=0`.
- Final bridge status was `connected-no-immediate-error`.

The redacted evidence summary reports all six paths as text/proc-style readable
and keeps `read_data_redacted=true`.

## Timing

Canonical timeline:
`workspace/private/runs/kernel/vfs-read-kernel-vitals-bundle-20260701T105200Z/timeline.json`.

| Phase | Elapsed |
| --- | ---: |
| Candidate flash | `63.623s` |
| Candidate boot/health | `21.015s` |
| Live session | `449.778s` |
| Rollback flash | `64.713s` |
| Rollback boot/health | `20.895s` |
| Candidate-flash-start to rollback-boot-ready | `628.457s` |

The proof passed, but the live session is too slow for a routine bundle. The
next optimization should split heavy `/proc` reads into smaller named bundles
or add per-path timeout/continue behavior so one slow path cannot dominate the
whole session.

## Resident-Session Projection

The run-timing analyzer now implements the RESIDENT-SESSION MODE projection:
one v1-repl flash, repeated warm-rebooted bounded batches, and one v2321 rollback
at session end. It still rejects non-canonical timeline shapes.

Command:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/analysis/analyze_repl_run_timing.py --batch-size 10 --resident-batches 10 --warm-reboot-sec 15
```

Result over the current canonical private timelines:

- Canonical timelines parsed: `10/52`; non-canonical legacy timelines skipped:
  `42`.
- Mean candidate flash: `65.0s`; mean rollback flash: `64.7s`.
- Mean live session: `121.5s`, dragged upward by this `kernel-vitals` proof
  (`449.8s`).
- Resident projection: flashes `20 -> 2`, old in-boot batch `28.7s/target`,
  resident session `15.3s/target`, `18.8x` versus per-unit flash and `1.9x`
  versus per-unit in-boot batch.

This confirms the direction: the harness should move from unit마다 flash/rollback
to resident v1-repl sessions with mandatory warm reboots between bounded batches.
The practical speedup for smaller call-proof batches should be closer to the
expected `~8x+` regime once the heavy `/proc` bundle is not part of the mean.

## Host Validation

- `py_compile` passed for the touched Python files.
- `tests/test_analyze_repl_run_timing.py`: `6` tests passed.
- Focused `test_a90_repl.py` VFS bundle tests: `2` tests passed.
- Full `tests/test_a90_repl.py`: `205` tests passed.

## Outcome

`kernel-vitals` is now the preferred observation surface for standard `/proc`
kernel vital signs. Do not add individual state-getter call-proofs for the same
values unless a future target has no file-node equivalent or requires a genuinely
new ABI shape.
