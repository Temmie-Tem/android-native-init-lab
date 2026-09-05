# P339 initial diagnostic capture incident

Target: `SM-S906N / g0q / S906NKSS7FYG8`.

## Retained experiment

Run: `p339-ready2-prepared-20260905-2`, manifest `p339_process_v2_ready_2`.
The journal and transfer receipts prove one candidate and one exact Magisk
rollback completed, both with Odin return code zero. No second attempt exists.
The retained journal is now `CLOSED` with 19 records and `final_verified=true`.
State is `16464B/2b77ef8d`, result is `19305B/aa192e54`, and
`recovery_required=false`. Formal terminal is
`NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK` /
`p339_authenticated_resident_open_header_capture_unproved_rollback_verified`.
This run is consumed and cannot be replayed. It is not an F1 PASS.

Candidate AP: `28631081B/80830eed6818528577e3dd5d68af79743b55a014b1dd4e2c8a3c5f54711b47d3`.
Rollback AP: `23367721B/d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`.
Private evidence remains under
`workspace/private/runs/device-action-f1-live-v2/p339-ready2-prepared-20260905-2/`.

## Two host defects

The raw capture is 97 bytes, SHA-256
`4724b51f7d04cd2bcfa0efe03c8ee78a3304cc68def41fa44f32c56694739d8c`:
the exact 49-byte P339 banner, stage 0/code 0, and stage 3/code 1.
Host OPEN TX is 32 bytes, SHA-256
`e8fa40fb59801fe06eb22af4190a3c8c3f47d6e720d328a7848c85668a35bfa9`.

1. `_P339_INITIAL_OBSERVER` loads the retained P335 exchange implementation.
   After stage 0, its real `_exchange_one()` expects stage 1. Stage 3 is
   rejected and `exchange_retained()` closes the descriptor. The P339
   post-collection parser therefore cannot obtain stages 4 through 7, even
   if the device sends them. Their absence from the capture is not proof of
   absence from the device's output.
2. `_p339_validate_receipt()` assumes the reason is frame 0 and total frame
   count is `1 + word_count`. The actual initial stream includes stage 0,
   so its reason is frame 1 and count is `2 + word_count`. This rejects an
   existing `candidate-observer.json` and produces the misleading
   `interrupted-before-receipt` state. The raw and JSON files were retained.

The device's original header-grammar rejection remains unexplained. The
retained stage-3 code distinguishes it from the later OPEN semantic check,
but does not identify the bytes read by the device. No HMAC, command or
resident success is claimed for this run.

## Host-only repair qualification

`s22plus_fyg8_open_failure_capture.py` installs on a private initial codec.
At first-OPEN stage 3/code 1 or 4 it receives at most four existing 24-byte
diagnostic frames through the original raw writer and deadline. It checks
exact header/payload size, type, sequence, CRC and word order. It then returns
the original failure frame to the original rejecting parser. No transmission,
OPEN retry, connection reopen, timeout extension or successful proof is added.

Eight focused tests exercise the actual bound initial exchange over local
sockets: original 97-byte cut, complete 193-byte capture for codes 1/4,
partial/EOF and silent tails, malformed/order/CRC/size bounds, four-word cap,
unchanged three-session authenticated success, and publication/reopening of
partial bytes through the real durable raw writer. All pass. These are
host simulations, not new device results. Independent review confirmed the
collector's bounded scope; live integration and the receipt-index repair
remain to be completed and reviewed before the successor is ready.

## Recovery status

Final health originally timed out while S22+ ADB was unauthorized. One
exact-target host-side ADB reconnect restored the same device and topology;
the other connected Samsung device received no command. Ordinary recovery
then stopped before device collection on a prepared bundle hash mismatch.
The executable-source closure equals the retained closure. The mismatch was
the Process-v2 document digest carried through P300's Tier-3 materials after
policy commit `221201e8ae`. Supplying only the exact historical document bytes
from `965c5d5d75` in memory reproduces original bundle `313007c7`; current
policy, preparation, approval and prior journal records are not rewritten.

Existing raw-ADB sequence names collided during final health resumption. A
reviewed fixed `health-resume-1` child preserves the earlier captures and
retains new exact-target properties/root/partition health, two complete
byte-identical retained logs, and final serial/topology continuity. All those
reads completed. The subsequent finalizer incorrectly fell through to the
P328-only projection because its exclusion list omitted P339, raising
`P3.28 final stock projection is missing` before saving final state.

The fixed-run `s22plus_fyg8_p339_health_resume.py` rederives the completed
health from those raw handles using the original target/health/decoder
validators. Its one-condition finalizer correction excludes P339 from that
P328-only fallback. This reporting-cut path performs no device command,
endpoint enumeration or transfer; candidate and rollback remain exactly 1/1.
The rederivation audit passes with final-evidence SHA-256
`3822ec9111be3c87107eaefc705d62a7a8b5f449caaaefe0a2f192f6164bf3ce`.
Nine helper tests pass, including the actual recovery-entry path's single
final-capture rebind. Independent review returned
`PASS_GO_P339_RETAINED_HEALTH_FINALIZATION_H0` and the narrow follow-up
`PASS_GO_P339_HEALTH_RESUME_CONTEXT_H0`. Durable closure and result publication
completed at `2026-09-04T21:13:24Z`, with no further device command or transfer.
The health result does not promote the candidate's failed initial exchange.
The current F1 closure row was appended and reparsed in the canonical ledger;
the unrelated P320-P322 historical disposition was not changed.

Historical executable context is the unchanged common source at `5d71ad4337`:
live runner `663927B/5b7f782919035e444686c347d8a04ed2a1764281d5bf08dac63e4545d58e340c`.
The fixed-run helper intentionally requires that historical closure; later
common-source updates are not authorization to reinterpret this consumed run.

## P340 qualified successor

Independent review returned `PASS_GO_P340_H0` for the final reachable common
dispatch, initial collector, receipt, lease, recovery and terminal mappings.
The P339 device success/failure protocol is unchanged; the new identity is
`c340f1e0a90b5e6d7c8a9b0c1d2e3f0b`. Initial reader/proof/session/receipt logic
shares the existing implementation rather than another full session clone.
P340 counts stage 0 before stage 3; P339's consumed interpretation is preserved.
No retry, new command, timeout extension or global census gate was added.

Actual initial exchange/raw writer/publisher/parser plus normal/NO_PROOF final
routing tests pass 5/5; evidence/core 4/4, artifact/runtime/build 9/9 and
static/prepare 5/5 pass. No other-target or unrelated census identity enters
the P340 execution closure. The public ready manifest is `11144B/cebf38e5`;
static is `41150B/613e3c0b`; A/B AP is `28631081B/114523aa`, and exact rollback
remains `23367721B/d2373bf8`. Earlier private H0 static drafts and the private
ready copy were preserved; no consumed P339 artifact was changed.

One preapproved attended D1 reused the exact P296 state machine/P320 raw
transport with new private binding/run/raw names. It returned healthy with a
changed boot ID and no other-target command. Linked D1 result is
`2963B/6a87b9c8` under `workspace/private/runs/device-action-d1-p340-baseline/`;
the exact private invocation SHA is
`f44b5679ec73b0cf05987d282013385f892499cb00a215b403e97f5404992d20`.
No retained-baseline exception or public D0/D1 clone was introduced. Ordinary
fresh D0 must classify the new baseline and match this returned target/boot
before any F1 approval code is released. No P340 F1 transfer has occurred.

The first fresh P340 D0 passed (`3261B/9d4ed68d`, clean baseline, same D1
returned boot), but host preparation then found a missing Carrier export:
`_closure` selected the direct P340 import rather than the stable-loaded
adapter on `typed_evidence`. One line now selects that registered instance.
Independent `PASS_GO_P340_CLOSURE_IMPORT_REPAIR_H0` and the actual closure
regression pass; the focused initial/terminal/closure suite is now 6/6.
No AP, static or ready bytes changed, and no F1 transaction or approval was
created in `p340-ready1-prepared-20260905-1`. A new preparation directory is
required; no second D1 reboot is needed.

Fresh `p340-ready1-prepared-20260905-2` now passed common D0 with clean raw
baseline `2097136B/291672d7`, preflight `3261B/18616aeb` and prepared record
`26515B/c2e3dcf2`. The exact D1 result, binding and primitive result were
reopened; the D0 target, topology and boot match the returned D1 values.
`load_prepared` also passed against the current execution closure. Approval
digest `dfde76fb` is issued for attended operator response only. No P340
candidate/rollback transfer or F1 transaction has occurred. All current D1,
H0 and D0 ledger rows have been reparsed; P320–P322 history is unchanged.

## P340 attended F1: diagnostic captured, recovery pending

The operator returned exact approval digest `dfde76fb` and the ordinary live
runner executed `p340-ready1-prepared-20260905-2` once. Candidate AP
`28631081B/114523aa` completed its Odin transfer. The journal has 10 records,
through `candidate_boot_ready`, with state `OBSERVED`. Candidate/rollback
completed counts are 1/0; rollback has not been attempted. During the physical
Download wait the runner stopped with `measured USB endpoint inventory failed`.
This is a recovery-pending, consumed run, not a replayable candidate or a
healthy closed result. Only its preapproved exact rollback may resume from
the retained journal. No other-target command was sent.

The actual initial collector retained `candidate-observer.raw`, 193 bytes,
SHA-256 `f461d251c3e43b9e7a3398dba949f2973b04c6cb6db9cee4250a57bfb90cbda7`.
The published `candidate-observer.json` reports a complete four-word header
snapshot after stage 0/code 0 and stage 3/code 1 (`header-grammar`), with six
diagnostic frames total. Rejected header hex is
`533232504c55532d465947382d45333a` (16 bytes): the first 16 banner bytes,
`S22PLUS-FYG8-E3:` without a line terminator. The retained host TX is instead the valid
32-byte `S328` OPEN, SHA-256
`dc475d45f771cd21c0929b3b408f2e96ae0d793b897e7c48afe07d6c0998fbf8`.
This directly locates banner bytes at the device's OPEN parser; it does not
yet attribute how they returned there. Host TTY echo before raw-mode setup
is a hypothesis requiring execution-order inspection, not an established
root cause. The current device code sets and reads back zero local flags.

Diagnostic retention succeeded. Authentication and fixed-command sessions did
not: `accepted=false`, `successful_sessions=0`, proof is empty, and candidate
success/causal claims remain false. The original failed exchange was not
retried. Final health and formal F1 closure are pending. No premature F1
closure row was appended; the matching ledger row must land with durable
closure. Historical preparation statements above describe their earlier
zero-transfer stage, not the current run state.

## P340 recovery and closure

After the operator confirmed physical Download, the unchanged ordinary runner
resumed only `--recover` on the same prepared run. It freshly identified the
bound rollback endpoint, completed the exact Magisk rollback once and verified
rooted FYG8 final health. It returned normally with no host repair, candidate
replay, second transfer attempt or other-target command.

- Candidate/rollback completed: 1/1; journal CLOSED with 19 records.
- State: `19204B/826c89583365de3f8a0e1e830b0ef64fbbac28ea2c041159ae87c025bbc09224`.
- Result: `22241B/ed2d5d1d12f40114a4d2a1818167fc7ac9d915ae1b677e6ca65cdbf415bbd656`.
- Observer receipt: `8384B/26d21f2af898a8e637888f1ac6265786113ad730edcda9abcbafad14fe075cf0`.
- Formal verdict: `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`.
- Outcome: `p340_authenticated_resident_open_header_capture_unproved_rollback_verified`.
- `recovery_required=false`; diagnostic retention does not promote authentication.

Canonical UTC timeline, directly from the result:

| Event | Timestamp |
|---|---|
| live_session_start | 2026-09-05T06:29:36.057442Z |
| candidate_flash_start | 2026-09-05T06:29:57.097961Z |
| candidate_flash_done | 2026-09-05T06:29:58.865164Z |
| candidate_boot_ready | 2026-09-05T06:30:16.489685Z |
| rollback_flash_start | 2026-09-05T06:35:24.036017Z |
| rollback_flash_done | 2026-09-05T06:35:25.577534Z |
| rollback_boot_ready | 2026-09-05T06:35:59.600093Z |
| live_session_end | 2026-09-05T06:35:59.622345Z |

The earlier recovery-pending paragraph describes the interrupted stage only.
The matching F1 closure ledger row is appended from this retained journal and
result and reparsed after publication. P320–P322 retrospective disposition is
unchanged. P340 and its approval are consumed and never replayable; no standing
resident or device-control authority remains.
