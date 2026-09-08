# S22+ foreground-goal D0 / attended D1 improvement

The operator requested fewer repeated approval interruptions for goal-directed
D0/D1 research, including necessary root reads. This unit implements named
ordinary-Android reads and attended normal reboot under one explicit foreground
goal. It changes neither the permanent forbidden effects nor F1/unattended
authority. No connected command, reboot or live goal grant was issued here.

## Implemented scope

The [target capability](../operations/targets/S22PLUS_FYG8_GOAL_RESEARCH_V1.md)
defines `identity`, `processes`, `memory`, `mounts`, `usb-state`, `health` and
`normal-reboot`. The first six are D0; root is used only for their fixed status
commands. `normal-reboot` is attended D1, with one durable intent and one reboot
dispatch per invocation, exact changed-boot/root/hash health and a bounded
return observer. An explicit current goal selects the permitted subset; it
does not authorize arbitrary commands, paths or unrelated work. Completion,
cancellation, scope drift or unexplained failure ends the grant.

The common contract now permits a target to activate this narrowly reviewed
attended-goal consent rule. The root common-details digest follows that change.
Unattended D1 still requires its separately reviewed finite scope and stop or
recovery evidence; the old pre-F1 catalog remains dormant. No per-command
approval is added inside a valid goal, and CLI goal/attendance arguments cannot
create operator authority or physical presence.

The implementation reuses the existing ADB target parser, private raw capture,
rooted-health profile and shared target lease. Host-run fixtures exercise the
real ADB subprocess quoting/raw publication and identity/health consumers.
They are not connected device trials or unattended-recovery evidence.

## Independent findings and repairs

Review found a host-cut gap between local reboot intent and the shared pending
record. The shared pending record is now the authoritative intent and precedes
the local mirror and dispatch. Even BaseException/process cuts leave new D1 and
default F1 effects blocked. A missing local mirror never permits replay.
Read-only reconciliation requires the exact changed healthy boot, closes the
old goal and does not upgrade a failed bounded action.

Review also identified parked F1 ownership: a process lock disappears after the
process exits, even when its device session remains unresolved. Prospective F1
now records its exact run/binding before Download intent. Research D1 refuses
that owner before contacting the device, and active F1 recovery requires the
matching owner. Validated CLOSED publication retires it; a validated pre-effect
abort can retire it only without Download intent or transfer starts. Cuts retain
ownership. This is an interlock and grants no additional F1 effect.

Initial owner migration uses the retained P367 second run's CLOSED/19 and
verified health result, SHA-256
`80716d152eab83193c1aa14560ee3426806de851f3bee038708194be2681f05c`.
Existing consumed source bindings, prepared files, raw captures and journals
remain unchanged. The new closure cannot execute an old approval; future F1
candidates require their ordinary new binding and approval.

## Validation and activation

The tracked [independent review receipt](../../workspace/public/src/device-action/bindings/s22plus_goal_research_v1_review.json)
is the runtime activation input. The runner requires `PASS_GO`, the exact action
set and all nine current source identities; missing or changed inputs disable
connected entry. It grants capability availability, not a live goal/session.

Focused tests pass: 20 research tests, 76 F1 live regressions and nine registry
tests, plus nine P367 lifecycle regressions (**114 total**). The repository
boundary check also passes. Coverage includes real host fixture producer/consumer paths, exact target
selection, source drift, missing attendance, one dispatch, return deadlines,
unexpected transport failure, late read-only health, grant closure, authoritative
intent cuts, parked ownership and terminal-publication cuts. Touched Python
passes `py_compile`.

The 29-test historical process-document suite retains three pre-existing
failures: archived-policy dependency wording, the old P315 goal-text assertion
and retired-trial wording. Re-running with this task's changes removed produces
the same three failures; they were not weakened or reported as PASS.

Private review/test evidence is under
`workspace/private/outputs/s22plus_goal_research_autonomy_h0/`.
Other-target changes already present in the worktree are excluded; the only
root-file edit staged by this unit is its common-details hash. No A90/S20+
device command or target-specific source change belongs to this unit.

Independent review returned **PASS_GO** for all nine source identities. Receipt
SHA-256: `bd8ce7f21433d4b78ca98b1b63b7254c9dc6c7323f17343a846591e92944ef45`.
The actual runtime review gate reopened that receipt successfully. No live
grant was created; capability availability is separate from a goal invocation.
