# Goal: S22+ repeatable native PID 1

Build a repeatable path from the FYG8 Android vendor boot chain and
source-matched kernel to a custom static `/init` running as PID 1, then grow
that entry point into a minimal observable and recoverable runtime.

This goal reports state, never device authority. The binding layers are
`AGENTS.md`, `docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md`, and
`docs/operations/DEVICE_ACTION_PROCESS_V2.md`. Select only
`SM-S906N/g0q/S906NKSS7FYG8`; A90 and S20+ remain isolated.

## Current bounded unit

P350 fixed native display H0 preparation is the selected unit. Deterministic
A/B boot packaging, three-session observer, real authenticated raw receipt
validation, 84 live regressions and full-tree raw-first audit passed. Independent
review returned PASS_GO for the bounded capability; final H0 ready publication
and reopening passed. No P350
device command or transfer occurred; actual display/probe behavior is UNPROVED.
The candidate AP is `30822441B/41b9272b`, with the existing exact Magisk rollback
`23367721B/d2373bf8`. It has no later-action lease. Fresh attended preparation
and approval remain required before any device effect.
Report: [P350 fixed display preparation](docs/reports/S22PLUS_FYG8_P350_NATIVE_DISPLAY_PREPARED_H0_2026-09-06.md).

## Paused P349 unit

P349 device work is paused pending operator attendance. Independent capability
review returned PASS_GO; A/B candidate, static promotion, 73 focused tests and
raw-first audit passed. Candidate AP is `28631081B/8ff75170`; exact Magisk
rollback is `23367721B/d2373bf8`. This is a UID/GID 65534 current-boot RAM
workspace, not a root shell: `/work` is 8 MiB/256 inodes, with fixed BusyBox
script execution and fresh children across actions.

The 65-minute/16-action lease requires initial six-session/120-second reopen
proof, eight ordered functional actions and 20/40/60-minute authenticated
same-boot workspace witnesses. Durable intent timing must satisfy each actual
elapsed threshold. Capacity tests remain host-only. Actual P349 hour/live RAM
behavior and rollback/final health are still UNPROVED; no F1 transfer occurred.

First D0 preserved a retained-family baseline stop. One preapproved ordinary
reboot D1 passed with changed boot ID and healthy rooted FYG8 return, then new
D0 and preparation initially passed in `p349-ready1-prepared-20260906-2`.
The returned approval then reached an observer-guard host authentication failure:
`pkexec` supplied no arm response within 30 seconds, and polkit logged failed
authentication. The run is ABORTED/4 before any Download request or candidate
attempt, with result `1351B/ca79a6d2`; actual result validation passed. No flash,
rollback or native session occurred, and the old approval cannot be replayed.

Fresh preparation `p349-ready1-prepared-20260906-3` also passed D0, but its
returned approval encountered the same host-authentication timeout. It too is
ABORTED/4 before Download or candidate transfer; result `1351B/c1cb7925`.
The operator then confirmed they were away and could not authenticate. Both
approval bindings are terminated; no replacement is currently prepared.

The latest execute-preflight recorded healthy rooted FYG8. No device transition
followed it, and no native shell is active. The candidate remains untransferred;
P348 remains closed/consumed. Resume only when the operator can complete host
authentication and physical Download recovery, with fresh exact preparation and
approval. P349 remains paused; separate H0 display build work is described below.
A90/S20+ receive no command.
Report: [P349 capability and preparation](docs/reports/S22PLUS_FYG8_P349_RAM_WORKSPACE_PREPARED_2026-09-06.md).

## Separate H0 display investigation

The operator requested a visible indication that native PID1 is running,
distinct from the retained boot logo. [Initial display research](docs/reports/S22PLUS_FYG8_NATIVE_DISPLAY_RESEARCH_H0_2026-09-06.md)
selects DRM/KMS as the preferred source-investigation path; current framebuffer
support is disabled and the USB plan omits the vendor display module. Actual
native display output remains unproved. This H0 work does not alter P349 or
activate a device lane. [Follow-up research](docs/reports/S22PLUS_FYG8_NATIVE_DISPLAY_FOLLOWUP_H0_2026-09-06.md)
found the retained panel-selection parameter, checked 50 modules/2,965 imports
against the exact Image within their declared graph, and identified a WC buffer
route. Stock display/debug providers also have persistent-write paths, including
probe and diagnostic-read triggers. [Minimal-build research](docs/reports/S22PLUS_FYG8_NATIVE_DISPLAY_MINIMAL_BUILD_RESEARCH_H0_2026-09-06.md)
identified paired diagnostic gates and forced make/header configuration; public
KMS/modetest examples support renderer design but do not qualify FYG8.
[Consolidated H0 result](docs/reports/S22PLUS_FYG8_NATIVE_DISPLAY_CONSOLIDATED_H0_2026-09-06.md):
isolated vendor-module Full-LTO/CFI build succeeded with known display persistence
paths and POC/SPI implementations excluded. Final combined graph: 82 modules,
4,391 versioned imports, zero unresolved/ambiguous/CRC-mismatched providers.
This qualifies a host build and symbol graph, not runtime ABI, safe probe,
transitive absence of persistence, screen output or recovery. The P350 unit above
adds a qualified host renderer/packager and fixed observation sequence. Runtime
probe and visible output remain unproved. P349 remains unchanged.

## Latest completed P348 unit

P348 is CLOSED/19 and consumed with
`PASS_F1_V2_P348_READONLY_RESEARCH_SHELL_AND_ROLLED_BACK`.
Candidate `28631081B/5dde2320` and exact Magisk rollback `23367721B/d2373bf8`
each transferred once. Six initial sessions / 18 commands, 120-second idle and
clean reopen passed, followed by all five retained-shell acceptance actions:
checked snapshot, exit 7, timeout, authenticated cancel and post-cancel success
with complete 120,017-byte output. Final rooted FYG8 Android, original
boot/supporting hashes and absent Download passed. No active native shell remains.

**One-hour stability is UNPROVED.** The last successful later action was
390.137 seconds after lease opening; the one-hour setting was only an upper
bound. Recovery was requested at 453.389 seconds. Future full-hour validation
needs a separately qualified successor with explicit timing and witness criteria;
this consumed candidate and lease must never be replayed or renewed.

Run `p348-ready1-prepared-20260906-2` has live result `42728B/97915e02`,
recovery_required=false. Actual prepared/result reopening passed. A host command
file mode rejection preceded any action intent; its corrected first execution
was ordinal 1. USB identity evidence failed while awaiting physical Download,
before rollback transfer. Same-journal recovery after operator Download entry
completed the exact rollback once. Original failure evidence is preserved and
its cause remains unproved. A90/S20+ received no command.
Report: [P348 result and timeline](docs/reports/S22PLUS_FYG8_P348_RETAINED_SHELL_PREPARED_2026-09-06.md).

## Latest completed bounded unit

P347 is CLOSED and consumed with
`PASS_F1_V2_P347_READONLY_RESEARCH_SHELL_AND_ROLLED_BACK`. Candidate
`28631081B/02c5d905` and exact Magisk rollback `23367721B/d2373bf8` each transferred
once. All five same-FD qualification sessions passed: numeric read-only canary,
exit 7, 15,156-ms timeout, authenticated cancel and all 120,017 final output bytes.
Final rooted FYG8 Android health, original boot/supporting hashes and absent
Download passed. No later shell lease or standing command authority exists.

Run `p347-ready1-prepared-20260906-3` is CLOSED/19, recovery_required=false;
live result `33570B/9e2db4b7`, observer raw `124676B/20f67548`. Actual prepared/
result reopening and append-only campaign-ledger closure passed. The first
execute-preflight host ADB startup-stderr stop is preserved separately; it
preceded target-specific commands and transaction creation. Candidate and
observation were never replayed, and no recover invocation was needed.

The approved bounded unit is complete. Any new candidate requires its own
qualification, current exact binding and fresh approval; P347 is never replayable.
A90 and S20+ received no command.
Report: `docs/reports/S22PLUS_FYG8_P347_OUTPUT_TIMING_PREPARED_2026-09-06.md`.

## Consumed P346 and diagnosis

P346 is CLOSED and consumed after the operator returned its exact F1 approval.
Candidate `28631081B/ad6a84ef` and exact Magisk rollback `23367721B/d2373bf8`
transferred once each. Final rooted FYG8 health, original boot/supporting hashes
and absent Download passed. Journal CLOSED/19; formal result
`NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`, `25665B/7d28bfa7`, with recovery not required.

The fixed read-only child canary and expected exit-7 session passed (2/5).
Session 3 failed expected timeout-outcome validation after a complete exchange;
authenticated cancel and post-cancel pipeline were not attempted. Raw evidence
is preserved. This is partial functional evidence, not complete qualification.

A host USB inventory failure after observation stopped the initial runner before
rollback transfer. One ordinary journal-based recovery completed exact rollback
without candidate or observation replay. Its precise cause remains unproved.
The earlier baseline D1 return timeout also remains preserved; late exact healthy
return and fresh ordinary D0 subsequently passed without repeating that reboot.

The approved bounded execution is complete. Any next work is H0 diagnosis of the
session-3 outcome and inventory failure using retained evidence. Do not replay
P346, widen its child filter, or start another candidate under its consumed approval.
Report: `docs/reports/S22PLUS_FYG8_P346_PREPARATION_AND_D1_RETURN_STOP_2026-09-06.md`.

H0 sleep diagnosis reproduced the failure: the exact candidate BusyBox calls
`clock_nanosleep(115)`, which the consumed filter denies with `EPERM`; BusyBox
then exits zero without waiting. The retained sequence-4 EXIT is zero/empty at
101 ms, consistent with the supervisor's 100-ms polling. Real-filter/C-supervisor
H0 reproduction agrees; no wait/reporting defect was found. Two new diagnosis
tests and nine child-boundary tests passed. Historical filter input is frozen
in `tests/fixtures/p346/readonly_child.inc.c`.

A private minimal relative-CLOCK_REALTIME-only correction passed H0 normal,
nonzero, cancel, 15-second timeout and next-pipeline tests, negative controls,
AArch64 compilation and independent review. That diagnostic proposal was not applied to P346:
the earlier no-widen question was subsequently resolved by the operator's
P347 preparation request. The historical P346 source stays unchanged; the new
version belongs only to P347. Full diagnosis evidence is in the report above.

## Adjacent H0 audit

The follow-up audit reproduced an additional output-integrity defect: a
120,000-byte BusyBox awk output (below the 128-KiB cap) yielded only 65,536 bytes
with exit 0, flags 0 and `ok`. Real-filter C/Python framing and exact candidate
BusyBox nonblocking-pipe tests cover the mechanism. Separately, denied
`prlimit64`/`sysinfo` queries let ulimit/uptime/free emit untrusted values with
exit 0; usleep shares the clock_nanosleep failure. Pipeline/substitution status
masking is a shell-semantics limitation, not a newly invented proof of failure
in the existing fixed canary. Independent review agrees.

These findings led to the separately qualified P347 successor above. The audit
itself applied no production fix or device action and remains the causal record.
Report: `docs/reports/S22PLUS_FYG8_P346_ADJACENT_FAILURE_AUDIT_2026-09-06.md`.

## Latest completed evidence

P345 is CLOSED/19 and consumed: candidate `28631081B/7ee59a13` and Magisk
rollback `23367721B/d2373bf8` each transferred once, with final rooted FYG8
health and original boot/supporting hashes verified. The qualification accepted
0/5 sessions; retained raw `670B/a8d28dc6` is partial evidence only. Terminal-only
metadata normalization published `15689B/039bcb3f`, verdict
`NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`, outcome
`p345_readonly_research_shell_unproved_rollback_verified`, recovery not required.
No journal, state, raw capture or prepared binding was rewritten.

H0 repair `4a8c6d8b0d` shares numeric parent-ID checks, separates child numeric
UID/GID queries, normalizes JSON metadata and excludes P345 from incompatible
P328 receipt fields. Independent review passed for code repair only. P345
43/46 host tests passed; three historical build reopenings reject changed source
identity. Shared exchange 8/8 and common F1 live 74/74 passed. Historical pins
remain unchanged; this does not qualify a fresh candidate.
Report: `docs/reports/S22PLUS_FYG8_P345_SHELL_QUALIFICATION_NO_PROOF_2026-09-06.md`.

P344 proved the bounded five-query named read-only exploration workflow:
initial four sessions/twelve commands and 120-second idle reuse, then successful
kernel/processes/mounts/memory/usb-state actions with published results and no
failed/pending action. Candidate/rollback 1/1, CLOSED/19 and final rooted FYG8
health passed. Verdict `PASS_F1_V2_P344_NAMED_EXPLORATION_AND_ROLLED_BACK`;
result `38199B/aba403cc`. The device returned to Android; all actions are consumed.
Report: `docs/reports/S22PLUS_FYG8_P344_NAMED_EXPLORATION_PREPARATION_2026-09-05.md`.

Earlier native-PID1 evidence includes P325 ACM arrival, P326 fixed bidirectional
USB/BusyBox shell, P327 framed fixed-command execution, and P335 authenticated
three-session command execution. None establishes unrestricted shell, interactive
PTY, indefinite residency, persistent installation, shell reboot/Download control,
autonomous recovery or Max77705 causal behavior. P343 and earlier NO_PROOF results
retain their original classifications and no-replay status.

## Archive and continuing boundaries

The complete previous 899-line goal was preserved byte-for-byte at
`docs/archive/roadmaps/GOAL_THROUGH_P345_H0_REPAIR_2026-09-06.md`.
Its completed history and earlier archive links are evidence only. The private
append-only campaign ledger and run journals remain authoritative for effects.

Never prepare a new experiment over unhealthy or uncertain state. Preserve exact
target, current boot, candidate/rollback, topology, source and journal bindings.
An unexplained device-session failure stops the experiment; retain raw evidence
and continue only allowed observation and preauthorized recovery. A consumed
candidate is never replayed, and a reporting failure never repeats a device effect.
