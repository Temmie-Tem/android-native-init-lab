# Goal: S22+ repeatable native PID 1

Build a repeatable path from the FYG8 Android vendor boot chain and
source-matched kernel to a custom static `/init` running as PID 1, then grow
that entry point into a minimal observable and recoverable runtime.

This goal reports state, never device authority. The binding layers are
`AGENTS.md`, `docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md`, and
`docs/operations/DEVICE_ACTION_PROCESS_V2.md`. Select only
`SM-S906N/g0q/S906NKSS7FYG8`; A90 and S20+ remain isolated.

## Current bounded unit

Prepare P346 through fresh F1 approval-code issuance. The operator authorized
necessary S22+ D0/D1 for this preparation on 2026-09-06. F1 execution awaits a
separate returned exact attended approval. Use ordinary D0 and, only if needed,
the existing attended one-normal-reboot baseline primitive. No candidate replay,
new D0/D1 framework, standing shell authority or autonomous recovery follows.

P346 reuses P345's fixed five-session qualification: numeric read/write-denial
canary, exit 7, timeout, authenticated cancel and subsequent pipeline/substitution.
The exact child view/filter, authentication, output/time limits, same-FD/no-reopen
geometry, boot-only AP and mandatory Magisk rollback remain unchanged. Fresh
run ID, source/artifact qualification and matching raw-first/ready/live bindings
are required. H0 implementation/source/artifact qualification now has independent
PASS_GO; A/B AP `28631081B/ad6a84ef` matches and ready1 is `7135B/54dfe8f1`.
Initial D0 stopped on retained baseline. One preapproved normal-reboot D1
exceeded its 240-second return bound; its consumed stop remains preserved.
After the operator reported Android, a later read-only observation proved fresh
boot ID, unchanged topology and exact rooted FYG8 health. No reboot was repeated.
Fresh preparation `p346-ready1-prepared-20260906-2` passed ordinary D0 with a
clean baseline and published a 30216-byte prepared binding. The actual prepared
consumer reopened it successfully and its F1 approval code was issued. F1
execution still requires the returned exact attended approval; no candidate
transfer occurred.
Late health does not turn the original D1 timeout into an in-bound PASS or prove
automatic recovery from an unresponsive experimental component.
Report: `docs/reports/S22PLUS_FYG8_P346_PREPARATION_AND_D1_RETURN_STOP_2026-09-06.md`.

Completion criterion: independently reviewed matching execution closure,
reproducible A/B boot-only artifacts, exact rollback identity, successful offline
promotion and ready revalidation, fresh healthy exact-target D0 with admissible
baseline, and normally reopened prepared binding plus its F1 approval code.

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
