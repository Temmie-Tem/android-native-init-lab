# S22+ P368 display-child exit and bounded native return

P368 is consumed and CLOSED/19 with
`PASS_F1_V2_P368_NATIVE_RETURN_CONTROL_AND_ROLLED_BACK`, recovery_required=false.
The intended child exit and subsequent bounded Download return passed; exact
rollback and final rooted FYG8 health are complete. Preparation history follows.

P368 tests whether the existing native PID1 control path remains usable after
the display child exits. The fixed renderer calls `_exit(7)` immediately after
its third flushed swap-submission record. Module preparation, privilege drop,
PID1, the single Download CONTROL, return window and exact rollback stay in
place. P367 is consumed and its sources/artifacts/journals are unchanged.

## Evidence and limits

The existing parent reads child output and uses nonblocking wait4. A reaped
child emits authenticated stage-43 status and READY, then the same parent
continues the original CONTROL loop within its existing deadline. No supervisor
redesign is needed for this failure condition.

P368 qualification requires signed CHILD_EXIT/code 7, READY child-exited=true
and exactly three submissions, complete preparation/clone, and accepted CONTROL.
Both the live qualification and retained raw-capture consumers enforce that
witness. The complete run additionally requires exact bounded Download arrival,
one exact rollback and verified final health. CONTROL acceptance alone is not
reboot or recovery proof. Physical-intervention absence requires the operator's
separate observation; software causality and visible pixels remain unproved.

The read/reap race can freeze READY before all buffered submissions are read.
Fewer than three records remains NO_PROOF, with the existing rollback path and
no replay. A wrong/missing fault witness does not add a gate before CONTROL.
This experiment does not qualify PID1 failure, kernel/driver stalls, automatic
recovery from a blocked kernel call or unattended F1.

## Host validation

The generated renderer runs against the source-derived fake DRM fixture and
exits 7 after three submissions/four atomic calls (one initial commit and three
swaps). A prior commit failure remains exit 1 without injection or retry.
The generated native PID1, authentication/framing and observer are exercised
through the actual arrival and scoped final-health producer/consumer lifecycle.
USB, ADB, Odin and kernel behavior are explicit platform fixtures. The requested
child-exit path reaches fixture PASS/CLOSED; normal ten-swap behavior and a
preparation failure reach NO_PROOF/CLOSED with fixture rollback. Retained
qualification rejects altered counts, normal exit, signal and missing status.
These are H0 tests, not live recovery evidence.

Five new tests and 105 existing P367, common F1 and goal-research regressions
pass (110 total). Fifteen Python files compile. Independent source/artifact review returned PASS_GO. All 147 build inputs
and 192 static closure entries matched current bytes. The review receipt
SHA-256 is `e599dec6d8ff535d4a2a81c2737565fd7709f67491a7839ddcecf1749617d507`.

## Qualified artifacts

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| Image | 41490944 | `1f2342c170c73e5237863385f16f0bd020f36c57d13e1ec980fbeaa9f20b7e4b` |
| A/B identical AP | 31006761 | `379bd0d0ab343d9b07f194b397dbe2dfb19fc40ea7fd18fc6528a54b0c02397e` |
| Static ARM64 init | 150632 | `da678154729931d4e0ac03d8bc47e7f6feb8fbb7536241c3db220afe9f6288bf` |
| Static ARM64 renderer | 710064 | `2736e074bca103095170c567657839f5f09429054f412e5ec94bdf1680ffc0c2` |

The Image uses the same independently checked identity-only P344 transform.
The AP contains only the regular allowed `boot.img.lz4`. Builder source hashes
are checked before and after A/B; all recorded inputs remain unchanged. Native
runtime semantics retain their prior ARM64 qualification. The only renderer
behavior delta is the fixed third-submission exit; artifact identity is fresh.
Private evidence: `workspace/private/outputs/s22plus_fyg8_p368/`.

No D1 or F1 authority follows from this H0 capability. A live run still requires
fresh exact preparation and returned attended F1 approval under the target
contract, including the ability to enter physical Download if control fails.

## Prospective goal-research review refresh

The shared live owner changed only by P368 registration; its ownership logic
is unchanged. The S22 target gained the bounded P368 clause. An independent
review refreshed these two roles in the current nine-role goal-research receipt,
after verifying no pending D1, F1 owner or research grant. The old receipt bytes
are preserved privately, no historical grant is rewritten, and the actual
runtime review gate passes. This does not open a new goal or device action.

## Published preparation and fresh connected D0

The actual common bundle rehearsal and manifest publication passed. The ready
manifest is `workspace/public/src/device-action/manifests/s22plus_fyg8_p368_process_v2_ready_1.json` (5054 bytes,
SHA-256 `48387c46ce0af8b260ef746c82eb9ae7bd8e46399a0fb95428fa1f30ecd39ab7`). The published bundle SHA-256 is
`022956527cd28d1547b588761e0340ea056c34ad172c3cb40a054b949186f577`. Publication performed no device contact.

One connected `--prepare` completed the fixed read-only D0 profile in
`p368-ready1-prepared-20260908-1`. It returned
`PASS_DEVICE_ACTION_D0_V2_CONNECTED_READ_ONLY`: exact rooted FYG8, Android
completion, original boot/supporting hashes and absent Download all passed.
This fresh boot identity is bound in the private preparation, not inferred from
P367's historical health. No reboot, mode transition, Odin transfer or native
experiment occurred. A90 and S20+ received no command from this task.

The prepared candidate/rollback binding awaits its separately returned attended
F1 approval. There is no candidate consumption or live child-failure recovery
result yet. The operator must be able to enter physical Download if the bounded
software path does not return; unattended F1 remains inactive.

The actual prepared bundle reopened successfully against the current source,
artifact and private D0 evidence. Prepared record: 33105 bytes,
SHA-256 `eb64b08a1ab452f71d1461f7a1bce66457f824f750c71188f8fbd7e8aa94ba10`. Source review,
diff/link checks and the staged repository privacy boundary check passed.

## Completed attended execution

The operator returned the exact prepared approval. The ordinary execute ran
once, transferring one candidate and one exact Magisk rollback. It completed
without a recovery invocation or physical fallback prompt. Forty-seven signed
progress records establish complete preparation and child creation, then
CHILD_EXIT code 7. Signed READY reports three submissions and child-exited=true;
authenticated CONTROL acceptance follows. The exact Download endpoint arrived
within the existing 30-second window. Final Android completion, root, original
boot/supporting hashes and both target/global Download absence passed.

| Canonical event (UTC, 2026-09-08) | Time |
| --- | --- |
| `live_session_start` | 13:15:41.777530Z |
| `candidate_flash_start` | 13:15:59.446712Z |
| `candidate_flash_done` | 13:16:01.129580Z |
| `candidate_boot_ready` | 13:16:23.973984Z |
| `rollback_flash_start` | 13:16:31.098950Z |
| `rollback_flash_done` | 13:16:32.783837Z |
| `rollback_boot_ready` | 13:17:20.973340Z |
| `live_session_end` | 13:17:20.992653Z |

The operator separately confirmed seeing Download transition and rollback
without button or cable manipulation. This is retained as operator observation;
it does not rewrite the machine receipt's physical-intervention UNOBSERVED or
software-causal-attribution UNPROVED fields. The original observer projection
also retains NO_PROOF_OBSERVER, software_download_arrival=UNPROVED,
visible_panel_output=UNPROVED and display_execution_proved=false. Those narrower
fields are distinct from the complete run's validated CONTROL, bounded exact
arrival and rollback/final-health PASS. No pixel or kernel-stall claim follows.

The completed result supports return after this fixed display-child exit.
PID1 failure, blocked driver/kernel calls and unattended F1 remain unqualified.
The consumed candidate/CONTROL cannot replay; no native session remains active.
A90 and S20+ received no command from this invocation.

The actual prepared/result reopening and journal-chain validation passed.
The terminal result is 47,104 bytes, SHA-256
`dba169964a1aaefa0efa9860d3f1ad46bfb899a0d99d1bb9511aeeed8b43060c`.
One matching F1 campaign closure row was appended after validating its fields
and derivation from the current journal/result; all earlier ledger bytes were
verified unchanged. The old full-ledger taxonomy parser rejects an existing
row's evidence outcome (row 547 after blank-line removal); no historical parser
PASS is claimed and no old row or validation assertion was changed.
This reporting step changed no candidate, source binding, consumed journal or
raw capture and performed no device action.
