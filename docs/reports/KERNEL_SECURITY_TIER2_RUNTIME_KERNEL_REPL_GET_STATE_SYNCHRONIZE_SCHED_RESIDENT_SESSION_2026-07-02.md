# Kernel Security Tier-2 Runtime Kernel REPL - get_state_synchronize_sched resident-session proof

- Date: 2026-07-02 KST / 2026-07-01 UTC
- Scope: add and live-prove `get_state_synchronize_sched()` as a no-argument RCU-sched state reader.
- Device action: v1-repl candidate flash once, mandatory resident warm reboot, one bounded batch, v2321 rollback once.
- Public result: PASS, rolled back to `v2321-usb-clean-identity-rodata`, final standalone `selftest fail=0`.

## Target

`get_state_synchronize_sched()` was selected after the existing `CALL_PROOF_TARGETS` set was saturated and after skipping redundant `/proc` or `/sys`-equivalent getters. It is a file-node-free RCU-sched state primitive adjacent to the already-proven `get_state_synchronize_rcu()`.

This is intentionally a narrow scalar read contract:

- Input: no arguments.
- Return: `unsigned long` RCU-sched grace-period state.
- Expected behavior: repeated immediate calls are nondecreasing, with a conservatively bounded short-run delta.
- Cleanup: none; no pointer is returned or dereferenced.

## Static Gate

The generic direct-xref export gate would reject this symbol because it has no in-image BL callsites. The live-call proof therefore uses a target-specific exact leaf gate, not a global relaxation:

- Symbol: `get_state_synchronize_sched`
- Link address: `0xffffff8008150bfc`
- Resolution method: `exact-leaf-export+word-boundary`
- Export candidates: `1`
- Map agrees with export: yes
- Direct BL xrefs: `0`
- JOPP entry: yes
- Leaf body: yes
- In-body BL count: `0`
- Pre-call pointer deref: none
- Next symbol: `cond_synchronize_sched` at `+0x20`
- Source declaration: `unsigned long get_state_synchronize_sched(void)` at `include/linux/rcutree.h:79`

Pinned body words:

```text
f0015788 d5033bbf 91040108 910c2108
c8dffd00 d65f03c0 d503201f 00be7bad
```

The Samsung source drop exposes the declaration but not the implementation source. The implementation identity is therefore pinned by relocated export row, map agreement, exact words, JOPP entry, leaf/no-BL shape, and next-symbol boundary.

## Live Run

Run directory:

```text
workspace/private/runs/kernel/repl-resident-session-get-state-synchronize-sched-20260701T161101Z/
```

Harness summary:

- Decision: `a90-repl-resident-session-pass`
- Candidate flashed once: yes
- Warm reboot between batches: yes
- Completed targets: `1/1`
- Flash count: `2`
- Rollback flashed once: yes
- Timeline errors: none

Target result:

- Decision: `a90-repl-live-call-proof-get_state_synchronize_sched-pass`
- Proof status: `trusted-under-rcu-sched-state-read-only-contract`
- Observed returns:
  - read 1: `0xffffffffffffff36`
  - read 2: `0xffffffffffffff3d`
  - read 3: `0xffffffffffffff44`
- Max delta from first: `0xe`
- Nondecreasing: yes
- Bound check: pass

Raw runtime pointers and KASLR slide remain private-only in the run directory.

## Health And Rollback

Preflight confirmed the rollback/fallback boot images:

- v1-repl candidate SHA: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`
- v2321 rollback SHA: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- v2237 fallback SHA: `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`
- v48 fallback present: yes

Baseline v2321 `version/status/selftest` passed before the live run. The candidate booted and health checks passed. The REPL selftest hit known serial marker loss once before batch execution, then bridge restart plus retry health passed. Post-batch candidate health passed with `selftest fail=0`.

Rollback to v2321 completed through `native_init_flash.py` with matching v2321 readback SHA. Final rollback `version/status/selftest` passed, and an independent post-run `version` plus `selftest` confirmed:

- Resident build: `v2321-usb-clean-identity-rodata`
- Final selftest: `pass=11 warn=1 fail=0`

## Timing

Canonical `timeline.json` uses the single top-level `events` schema and includes the required phase events.

| Phase | Seconds |
| --- | ---: |
| candidate flash | 63.240 |
| candidate boot/health | 43.831 |
| resident warm reboot | 33.233 |
| post-reboot REPL ready | 32.036 |
| live target batch | 3.632 |
| post-batch health | 1.278 |
| rollback flash | 64.805 |
| rollback boot/health | 1.025 |
| candidate start to rollback ready | 243.131 |

The timing aggregator now parses `24/72` canonical timelines. With `batch_size=10`, `resident_batches=10`, and `warm_reboot=15s`, it projects:

- Flash count: `20 -> 2`
- Old in-boot batch: `30.4s/target`
- Resident session: `14.5s/target`
- Speedup: `20.9x` versus per-unit flash, `2.1x` versus per-unit in-boot batch

## Outcome

`get_state_synchronize_sched()` is promoted as live-proven only under the no-argument RCU-sched state-read contract. This does not make nearby `cond_synchronize_sched()` callable: that function can call `synchronize_sched()` and remains outside this proof.
