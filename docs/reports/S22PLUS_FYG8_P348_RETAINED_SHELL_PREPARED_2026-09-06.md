# S22+ FYG8 P348 retained read-only shell preparation

P348 implements the [retained-shell design](../plans/S22PLUS_FYG8_P348_RETAINED_READONLY_SHELL_DESIGN_2026-09-06.md)
for `SM-S906N/g0q/S906NKSS7FYG8`. The operator authorized implementation and
D0/D1 preparation through F1 approval-code issuance. F1 execution requires the
separately returned exact code; preparation is not device feature proof.
P344/P347 remain consumed, with their original artifacts, journals and results.

## Capability

The fresh initial observer executes the five P347 shell cases, then one fixed
shell witness after a clean tty close, at least 120 seconds idle and one exact
reopen: six authenticated sessions / 18 commands within 300 seconds. An
accepted observation and candidate_boot_ready must be durable before lease
publication; only actual successful observer-guard release permits ACTIVE.

The attended same-boot lease permits at most 3,600 seconds and 16 later actions.
Each action reads one private 1–1,023-byte command file once, durably binds those
bytes to an intent and runs a fresh isolated child. The P347 child/filter,
blocking output writer, pipefail, 15-second timeout and 128-KiB output cap stay
unchanged. There is no PTY, persistent shell state, write/network expansion or
automatic Android recovery. Finite snapshots do not establish arbitrary applet
semantics; uptime/free/ulimit remain outside the proved applet set.

The action owner uses the existing target/transaction locks and exact endpoint.
Before each new dispatch it validates actual guard-release evidence, all prior
command/receipt/raw streams, and initial plus later nonce history. Cancellation
uses one SIGINT request in the descriptor owner and the existing authenticated
CANCEL/ACK protocol. Nonzero results, timeouts, truncation and cancel are distinct
from protocol failure; reserved exit 126/127 always stops, including combined
truncation/exec-failure flags. Known failures retain their outcome rather than
publishing a second uncertain result.

CLOCK_BOOTTIME bounds the lease; a host boot epoch or BOOTTIME-minus-MONOTONIC
increase above the 1-ms sampling tolerance stops reuse. Both the shared exchange
and its isolated codec check drift, lease expiry and the logical deadline at
actual I/O, including after select. No global OS/time module is modified. A
short observed session will not prove a full hour of operation.

Original raw-capture handles and selected output files are retained privately.
The close reader rederives command, output, exit/signal/flags, cancel and boot/
nonce semantics from the frames. Its summary is independent of current host
clock state. Corrupt/missing evidence produces NO_PROOF without blocking the
already bound exact rollback. Initial qualification, later shell use and final
Android health remain separate; capability PASS requires the ordered checked
snapshot / exit-7 / timeout / active-cancel / post-cancel pipeline cases plus
complete rollback and health. Subsequent ordinary commands do not erase that
proof, but an unresolved action prevents overall PASS.

## H0 qualification

- All 29 P348 tests passed, including actual PTY producer/retained-consumer,
  command-file bounds, previous-receipt loss, nonce history, guard publication,
  SIGINT, write-wait suspend/deadline, and combined flags/126 checks.
- Common F1 execution regression: 74/74 passed. The selected P344/P347,
  shared shell exchange and raw-first regressions passed 61/61 (including
  all 36 raw-first tests). Together with the P348 suite: 164 tests passed.
- The raw-first source audit passed on the actual changed closure. Legacy,
  closed and pre-boundary source census counts were unchanged (49/133/129);
  their only existing-file delta is the P348 typed-evidence registration.
  P348 endpoint owners are explicitly audited and source-frozen.
- Independent review returned `PASS_GO` for the exact frozen capability and
  independently reran all 29 P348 tests. It covers the new caller-command,
  retained-state, clock, receipt and higher-contract interactions. This is not
  a run approval or device proof. Receipt:
  `workspace/private/outputs/p348/independent-review.json`,
  `12553B/e093e3b96f40bada994f97b084dca947414bb670b66642c34bedadd3e80bed53`.
- Before A/B derivation, all 37 source keys and selected Git changes were
  recorded in `workspace/private/outputs/s22plus_fyg8_p348/h0-source-freeze.json`.
  The source keys were unchanged after build. Both generated init files are
  statically linked AArch64 ELF, and both APs are byte-identical.
- The real preparer invokes `candidate_static.build_result()` and rehearses
  `core.verify_bundle`; the standalone static script has no CLI dispatch and
  is not used as a qualification entry point.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| Candidate AP | 28631081 | `5dde23205b3c7bd0026aba0c2c6c2aded4645a808131ad323130976f4ca05263` |
| Image | 41490944 | `3d30a0de28abe2b77745426597f0bd10711c833d720270c37f89157bbdf704b0` |
| init | 149432 | `109e240313b8f5a068435ae87543acb308877e85a4de4078d4ccf0faabed8dd6` |
| Exact Magisk rollback AP | 23367721 | `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56` |

Candidate root:
`workspace/private/outputs/s22plus_fyg8_p348/stock-candidate-build-v1-20260906-01`.
The AP contains only regular `boot.img.lz4`; Image/init/AP join the fresh
`c348f1e0a90b5e6d7c8a9b0c1d2e3f0a` identity and reject consumed candidate identities.

Document links and the repository privacy boundary check passed. The staged
`git diff --check` reports only an extra final blank line in the frozen P348
runtime and preparer wrappers. These formatting-only notices are retained;
changing those already qualified bytes would invalidate the prepared binding.
No functional or safety assertion was relaxed.

## Preparation status

Preparation is complete; F1 remains unconsumed and no later shell lease exists.

1. Fresh D0 `p348-ready1-prepared-20260906-1` confirmed Android/root/original
   hashes, then stopped with `baseline-decoder-rejected`. The original bounded
   raw capture and no-replace stop result remain preserved. Host reopening of
   those exact bytes reproduced `baseline contains a current, legacy, or
   partial evidence family`; no evidence was relabeled clean.
2. The operator-preapproved ordinary-reboot D1 reused the unchanged P296/P320
   primitive through a fixed private metadata invocation. Its self-test passed;
   one actual reboot changed the boot ID and returned exact healthy rooted
   FYG8 Android with original hashes and no Download endpoint. Result:
   `workspace/private/runs/device-action-d1-p348-baseline/p348-normal-reboot-20260906-1-result.json`,
   `2963B/b6d354e9f2d876cc5a99a127c1b2f28536db7a8e82585a8c70c70526ae6cfd2b`.
   This is the existing ordinary D1 action, not a new lane or baseline exception.
3. Fresh D0 `p348-ready1-prepared-20260906-2` passed
   `PASS_DEVICE_ACTION_D0_V2_CONNECTED_READ_ONLY`. The resulting ordinary
   F1 preparation binds 67 execution sources, exact current target/boot,
   candidate, rollback, key and topology. Actual `load_prepared` reopening
   passed, and the F1 transaction directory is absent.

| Prepared input | Bytes | SHA-256 |
| --- | ---: | --- |
| Ready manifest | 9992 | `9a17515e44d525c4e2847835087ddad505f5fffb10cca3d426a180dae6ea19ba` |
| Successful D0 result | 3261 | `18d7118f5bcf04b77a3d0460b72819058b4f45ca5f50ca1aff5d38e20478d1db` |
| Prepared record | 38063 | `fabb00154e4802c3ec36864c90247bba8e80e0a2f161776bdc02c7d42e746fd2` |

Manifest:
`workspace/public/src/device-action/manifests/s22plus_fyg8_p348_process_v2_ready_1.json`.
Prepared run:
`workspace/private/runs/device-action-f1-live-v2/p348-ready1-prepared-20260906-2`.
Approval binding:
`b8bf1d9c4641f82d793b2870194ade9156a9708297e4c413c39ecf34290c7ddd`.

The exact approval code is issued to the operator separately. No P348 candidate
or rollback transfer, Download request or shell action occurred in this unit.
A90 and S20+ received no command. The existing unrelated S20+ edit and
untracked P345 ready manifest were excluded from this change.

After a separately returned F1 approval, the ordinary runner may open the
attended retained session. Its existing prepared run accepts
`--shell-command-file` for a bounded private command file and `--shell-status`
for host-only status. SIGINT requests authenticated cancellation in the action
owner; `--recover` ends the session through the already bound physical Download /
exact Magisk rollback path. These interfaces do not activate themselves.


## Consumed F1 result and recovery

The operator returned the exact prepared approval. P348 is now CLOSED/19 and
consumed, with `PASS_F1_V2_P348_READONLY_RESEARCH_SHELL_AND_ROLLED_BACK`, outcome
`p348_readonly_research_shell_rollback_verified`, recovery_required=false.
The preparation status above is historical. Candidate AP `28631081B/5dde2320`
and exact Magisk rollback `23367721B/d2373bf8` each transferred once; neither
candidate nor observation was replayed. Final rooted FYG8 Android, original
boot/supporting hashes and absent Download passed. Actual `load_prepared` and
`validate_live_result` reopening passed before these documentation updates.

Initial qualification completed all six sessions / 18 commands, including the
120-second idle and clean tty reopen. The retained lease then completed all five
reviewed acceptance roles with authenticated identity and final nonce evidence:

| Ordinal / role | Actual outcome | Exit / signal / flags | Duration ms | Selected bytes |
| --- | --- | --- | ---: | ---: |
| 1 / checked-snapshot | ok | 0 / 0 / 0 | 101 | 22 |
| 2 / known-nonzero | command-failed | 7 / 0 / 0 | 101 | 0 |
| 3 / timeout | timeout | -1 / 9 / 1 | 15159 | 0 |
| 4 / active-cancel | cancelled | -1 / 9 / 8 | 203 | 19 |
| 5 / post-cancel-success | ok | 0 / 0 / 0 | 810 | 120017 |

All five exchanges completed with continuation allowed and no pending intent.
The nonzero, timeout and cancel outcomes are preserved as such. Cancellation
used the existing action owner's callback, requested 0.2 seconds after its first
middle-command poll; ACK0 was observed. The private fixed invocation is
`workspace/private/outputs/p348/later-acceptance-20260906-1/active_cancel_invocation.py`.
This proves authenticated cancellation, not a live UI/SIGINT interaction.

**One-hour stability remains UNPROVED.** The configured hour was a maximum
lease duration, not an executed hour-long test. The last successful action
receipt was 390.137 seconds after lease opening (about 6 minutes 30 seconds).
The host recorded recovery-required at 453.389 seconds (about 7 minutes 33 seconds);
that later host timestamp is not another device-liveness witness. The operator
questioned the early return after recovery had started. The distinction was
clarified, without extending or reopening the consumed lease. A future full-hour
test needs a separately qualified successor and an explicit duration/witness
criterion compatible with expiry and its required full action window.

Two stops remain preserved. The first command-file invocation rejected mode
0644 at the host input check, before locks, intent or device contact. Correcting
the private input to 0600 allowed its first actual execution as ordinal 1.
During physical Download waiting, the first recovery invocation stopped with
`OdinMeasuredEvidenceFailure`, `usbfs-identity-failed` / `UsbfsIdentityError`;
its diagnostic says snapshot_persisted=false. No rollback transfer had started.
The precise cause is unproved. After the operator reported Download entry,
ordinary same-journal recovery revalidated the endpoint, transferred rollback
once and verified final health. The original diagnostic, raw captures and failed
invocation log remain intact; no source or safety check was changed.

Private evidence root:
`workspace/private/runs/device-action-f1-live-v2/p348-ready1-prepared-20260906-2`.
Live result `42728B/97915e02f444568ad97f2bca203d16241642e6adc72181285589117b5aef67cf`;
initial observer raw `125237B/10e1ba81fdd1f9cb78bb1e9b5f47b03988fd27c0c82279dfa75c775c1068a6a0`.
Execution-critical code remains the reviewed implementation commit `647392bc3e`.
Invocation logs are under `workspace/private/outputs/p348/`; action raw/result
receipts remain under the run's `p348-shell-actions` and append-only lease history
under `p348-shell-session`. No raw evidence or private identifiers are published.
A90/S20+ received no command. No active native shell lease remains.

### Canonical timeline (UTC)

| Event | Timestamp |
| --- | --- |
| live_session_start | 2026-09-06T06:06:17.191104Z |
| candidate_flash_start | 2026-09-06T06:06:35.160909Z |
| candidate_flash_done | 2026-09-06T06:06:36.759741Z |
| candidate_boot_ready | 2026-09-06T06:09:08.430248Z |
| rollback_flash_start | 2026-09-06T06:21:21.131529Z |
| rollback_flash_done | 2026-09-06T06:21:22.675112Z |
| rollback_boot_ready | 2026-09-06T06:21:57.103340Z |
| live_session_end | 2026-09-06T06:21:57.123927Z |
