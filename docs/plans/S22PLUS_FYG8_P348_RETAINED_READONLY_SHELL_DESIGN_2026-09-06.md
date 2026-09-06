# P348: attended retained read-only shell session

Status: **H0 DESIGN ONLY — NOT IMPLEMENTED OR ACTIVATED** (2026-09-06).
Selected target: S22+ `SM-S906N/g0q/S906NKSS7FYG8` only.
P348 is a proposed successor name, not an artifact, ready declaration or grant.

## Objective and completion boundary

Boot once into native PID1, execute caller-selected read-only shell commands
across bounded later sessions, then complete exact Magisk Android rollback and
final health verification. This planning unit ends with this design, a scoped
implementation sequence, validation criteria and an updated goal. No device
read, preparation, candidate build, contract activation or transfer is part of
this unit.

The first usable interface is a host command runner. Each invocation starts a
fresh isolated `ash -o pipefail -c` child; shell variables, working directory and
background jobs do not persist between invocations. Output and command status
return to the caller. This is not an interactive PTY or an installed shell.
The native PID1 listener persists only in the current attended boot.

## Evidence and constraints

- [Current goal](../../GOAL.md): P347's five shell qualification sessions passed;
  its candidate was rolled back and its run is consumed. No live shell lease exists.
- [Target contract](../operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md):
  P344 proved later named read-only actions and exact healthy rollback. Its
  one-hour/16-action lease is a reusable design precedent, not P348 authority.
- P347 proved numeric identity, checked snapshot reads, nonzero exit, a
  15,156-ms timeout, authenticated cancel, and all 120,017 final output bytes.
  It did not prove arbitrary BusyBox applets or a shell session after tty reopen.
- Preserve the P347 child view, syscall filter and output-pipe fix. Available
  proc/sys files are the finite reviewed snapshots, not a general live Android
  filesystem. `uptime`, `free` and `ulimit` are not established as trustworthy
  applets under this filter; exit zero alone is not semantic evidence.
- Existing physical Download recovery remains required. An idle listener,
  timeout, host stop or closed tty does not prove autonomous Android recovery.

## Proposed session limits and interface

| Item | Proposed first capability |
| --- | --- |
| Attendance | Operator present for the candidate boot through physical recovery |
| Lifetime | At most 3,600 seconds from durable lease publication; no renewal |
| Later actions | At most 16 started actions; each owns one authenticated session |
| Shell input | Existing UTF-8/control-byte rules, 1–1,023 bytes; no caller environment or executable parameter |
| Child | Existing 15-second bound, fixed read-only view, UID/GID/capability drop |
| Output | Existing 128-KiB cap; retain flags and exact forwarded byte count |
| Logical session | At most 30 seconds, bounded by remaining lease time |
| Concurrency | One action or recovery owner under existing target/transaction locks |
| Transport | One exact tty open per later action; no retry/reopen inside that action |
| Controls | Host status, execute, cancel-current-command, end-session/recover |

Interface names are design vocabulary, not executable instructions. Execute
accepts a private command file to avoid shell interpolation and argv history.
Read it once with a size bound, validate it and durably retain those exact bytes
before dispatch; the same bytes enter the intent and frame. All command text,
output, nonces, keys and raw framing remain under `workspace/private/`.
Status reads host evidence only and creates no device session.

Cancel is handled by the process already owning the descriptor, using the
existing callback and authenticated sequence-4 CANCEL. An interactive interrupt
requests cancellation once and continues reading EXIT/ACK and the fixed final
nonce witness. It must not terminate the owner before evidence retention. A
second process must not open the tty to cancel. End-session stops new work,
settles an in-flight command if possible, then invokes the bound recovery owner.
Forced owner death is uncertainty, not successful cancellation.

## State and ownership

1. **Prepared / candidate qualification:** fresh candidate identity, reviewed
   closure and ordinary attended F1 approval are required in the later execution
   unit. P347's consumed approval and ready manifest are never reused.
2. **Initial observation:** run the five P347 shell qualification cases on the
   new candidate. Add one deliberate clean tty close/open followed by a fixed
   shell witness after 120 seconds of idle time, using host-first OPEN and the
   same authenticated boot ID. Keep the whole initial observer within 300 seconds.
   This is six initial sessions / 18 commands, separate from the 16 later actions;
   it is a new proposed scope requiring review, not an extension of P347 authority.
3. **Publish retained state:** require durable accepted observation, `OBSERVED`
   and `candidate_boot_ready`, then no-clobber lease/guard publication and fsync.
   Return ACTIVE only after verified observer-guard release. Failed publication
   or release permits rollback only. ACTIVE remains nonterminal F1 state.
4. **Execute:** revalidate source, target, topology, candidate, key, boot identity,
   recovery binding, lease and previous receipts. Under the same locks, durably
   publish command bytes and an intent, then select/recheck the exact endpoint,
   open once, authenticate fresh challenge/unchanged boot ID, execute fixed
   parent identity / selected shell / fixed nonce, retain raw evidence, publish
   result, and complete the action receipt. Commands never bypass this owner.
5. **Continue or stop:** only a fully validated completed action permits another
   action. Budget exhaustion, expiry, operator stop, attendance loss, binding
   drift or uncertainty makes the session rollback-required. No renewal or replay.
6. **Recover / close:** stop new actions before taking the recovery path. Use
   the existing journal-based exact rollback after attended physical Download
   entry, verify rooted FYG8 Android and original hashes, then close F1.
   Malformed lease/action evidence must not block already authorized rollback;
   it prevents functional PASS and is retained as unproved evidence.

Use a successor lease schema that binds the shell capability and exact command
identity (size/hash) to each intent; P335's fixed `catalog` and action-name-only
intent cannot express this unchanged. The host boot/time epoch must be bound
so a host restart or clock reset cannot extend the lease. Treat host reboot,
owner crash or suspend during the session as stop-and-recover; do not resume
command dispatch. A normal later CLI invocation on the unchanged host/boot may
reopen a settled lease. Use a suspend-aware elapsed clock or explicit suspend
detection; settle the concrete mechanism in implementation before qualification.

Admit a new action only with a full 30-second session window remaining. Recheck
immediately before OPEN and clamp its absolute deadline to expiry. If expiry
still occurs during receipt publication, retain terminal raw/result evidence
outside the expired action journal and proceed to rollback. Do not rewrite an
intent, create a new ordinal for the same command or rerun it to obtain a receipt.
No unattended scheduler or new daemon is needed: expiry revokes dispatch even
if no host process is running, and physical recovery still requires attendance.

## Command outcome versus session integrity

A new receipt separates `session_complete`, `command_outcome` and
`continuation_allowed`. The existing P343/P344 close validator requires all
three commands to have `ok=true` and exit zero; it cannot be applied unchanged.

| Observed result | Next action policy |
| --- | --- |
| Exit zero, complete frames and cleanup | Continue; applet meaning remains separately qualified |
| Nonzero exit other than 126/127, including shell syntax error | Continue only with complete cleanup, framing and final witness; preserve code |
| Timeout or bounded truncation | Continue only with verified cleanup and complete terminal/witness; never label command successful |
| Authenticated cancel ACK0 | Continue only with consistent cancelled EXIT, cleanup and final witness |
| Cancel ACK1 (already completed) | Preserve actual completed outcome; never claim active cancellation or repeat it |
| Exit 126/127, setup/exec failure or missing cleanup | Stop; retain failure, rollback only |
| Partial RX/TX, invalid ACK/HMAC, changed identity, missing result | Uncertain; stop and rollback only |

The inherited protocol flags every exit 126/127 as exec failure, including an
explicit caller `exit 126`/`exit 127` or command-not-found. Reserve these codes
as stop-and-recover outcomes; do not claim they identify the cause uniquely or
add a new setup-status protocol for this first capability.

The successor journal uses a completed-protocol status distinct from command
success. Its close reader validates the exact bytes, framing, outcome and intent
binding again; it cannot count receipts just because their JSON says completed.
A successful later command does not erase an earlier uncertain action.

## Implementation map

Paths below are relative to `workspace/public/src/scripts/revalidation/`.
Preserve consumed source pins and namespaces; avoid global text replacement
that silently changes historical consumers.

| Existing component | Smallest planned change |
| --- | --- |
| `s22plus_fyg8_p344_exploration_session.py` / P343 / P335 lease core | Successor shell lease using existing locks, durable ordering and rollback ownership; explicit shell intent/outcome/clock fields |
| `s22plus_fyg8_p344_exploration_action.py` / P343 action | Successor caller-command action with exact input binding and raw-first failure capture |
| `s22plus_fyg8_research_shell_exchange.py` | Reuse one-descriptor exchange and cancel callback; qualify same behavior for later actions |
| `s22plus_fyg8_p347_research_shell_observer.py` | Reuse five qualification semantics; successor observer adds the one idle/reopen proof |
| `s22plus_fyg8_p347_research_shell_runtime.py` and `s22plus_fyg8_readonly_child_v2.py` | Preserve child restrictions and pipe behavior; fresh identity, no new applets/syscalls |
| `device_action_f1_live_v2.py` and typed shell evidence registration | Explicit retained-shell branch, lease hooks, action entry and terminal proof; old shell branches still roll back immediately |
| P347 builder/static/adapter/preparer and raw-first audit | Fresh artifact/closure qualification binding actual later-action and recovery consumers |

Prefer a small successor module with explicit parameters around reusable code.
If a hash-pinned predecessor cannot be reused without modifying consumed inputs,
introduce a versioned core and keep the old consumer frozen. Do not implement a
parallel transport, second recovery owner, generic shell service or new D0/D1 lane.

## Ordered delivery and verification

1. **H0 implementation:** implement lease/intent/receipt and action flow, then
   initial proof, live integration and close consumer. Add the exact target
   capability clause only as part of reviewed implementation. This document
   changes no binding contract and supplies no ready/activation declaration.
2. **Focused H0 checks:** compile touched Python; exercise real exchange and
   retained receipt consumers with fixed fixtures. Test command-file mutation,
   command/intent mismatch, all outcome rows, cancel race, stale nonce, partial
   frames, output below/at/above cap, descendant cleanup, action/recovery lock
   contention, duplicate dispatch, pending intent, 16-action exhaustion, expiry
   before OPEN/during output/at publication, host epoch/suspend, and guard failure.
   Reuse prior unchanged child tests; cross-compile touched C and inspect `file`.
3. **Independent changed-closure review:** cover caller-command authority,
   finite lease, clean reopen, result semantics, raw-first paths, host clock and
   common/target recovery interactions. One reusable capability review is required;
   this design review cannot substitute for review of actual execution bytes.
4. **Candidate qualification:** fresh deterministic build/static checks, artifact
   closure, actual producer/consumer reopen and ordinary fresh preparation. No
   replay or repinning of P344/P347 evidence; request returned attended F1 approval
   only when that concrete qualified candidate is ready.
5. **Later live acceptance:** pass initial proof, then complete a caller-selected
   checked snapshot pipeline, a known nonzero command, timeout and active cancel,
   and a successful post-cancel command across separate later actions on the
   same boot. Require exact expected outcomes and no unresolved action. Finally
   transfer exact rollback once and prove Android health. Record actual duration
   and count; a short run does not prove a full hour of operation.

Keep `initial_qualification`, `later_shell_use`, and `rollback_health` separate
in the final structured result. Overall capability PASS requires all three;
no later use or an uncertain action gives NO_PROOF even after healthy rollback.
Output truncation remains a reported limitation, not full-output proof.

## Design decision status

The implementation mechanism for suspend-aware timing and the exact successor
schema/module names are bounded implementation decisions. Qualification must
resolve them before any ready declaration. No open product preference blocks
this design: retain the established one-hour/16-action limits and command-based
interface for the first capability. PTY, writable state, network and persistent
installation remain separate future scope.

## Planning verification

Independent read-only design review on 2026-09-06 found one actionable
clarification: reserve exit 126/127 as stop-and-recover outcomes under the
inherited EXEC_FAILURE encoding. That correction is incorporated above; the
review found no remaining material design contradiction. This is design review
only, not execution-closure PASS_GO. Host clock/suspend handling and the
successor retained-receipt parser remain implementation obligations.
Local document links, referenced source paths and whitespace checks passed.
No device commands, builds, runtime changes or contract activation were performed.
