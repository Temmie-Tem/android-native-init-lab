# S22+ FYG8 R4W1-C2 no-AP recovery NO-GO repair

Date: 2026-07-21 KST

## Verdict before repair

Independent host-only read-only review session
`019f807c-c88c-7073-824b-7a1f4ecfec27` used `gpt-5.6-sol` at xhigh effort
against commit `1480370f`. It returned:

`NO_GO_TO_POLICY_ACTIVATION`

The review independently confirmed that all three R4W1-C2 Odin attempts stopped
at the exact extensionless `/proc/self/fd/7` AP parse error before `Setup
Connection`; no device session or partition transfer began. It found seven
activation blockers in the proposed no-AP recovery helper.

## Closed findings

1. Runtime dependencies and policy text were under-bound.
   The helper now pins the measured and connected helpers, Odin transition core,
   boot-only live core, USBFS identity observer, transport helper, its transitive
   M3 observable helper, birth-time `stat`, and Odin executable before contact
   and again before consumption. It recursively parses all local imports and
   requires exact equality with the pin set, so another undeclared transitive
   import fails closed. The
   installed policy must equal the reviewed draft byte-for-byte. A hard-coded
   canonical template SHA256 additionally binds every policy byte except the
   four self-referential helper/test identity fields, which are checked against
   their actual current values.
2. Odin inherited caller stdin.
   The child now receives `stdin=DEVNULL`, captured stdout/stderr, standard fd
   closure, and only the sealed Odin descriptor through `pass_fds`.
3. Pre-consumption failures allowed retry.
   The separate recovery state is now exclusively and durably created after the
   final host-only recheck but before any USB endpoint is opened or observed.
   Endpoint discovery failure therefore still consumes the one-shot.
4. Transaction semantic validation reopened different bytes.
   The `rollback_transfer_finished` decision now uses the exact descriptor-bound
   transaction payload already size/SHA verified in the incident loop.
5. Same-handset continuity was implicit.
   The fresh live acknowledgement is explicitly the load-bearing operator
   attestation for the original handset, cable, hub, host port, and normal
   Download screen. The consumed state preserves the exact acknowledgement and
   residual physical-continuity basis.
6. The 1 MiB output bound could overshoot by one read or through an injected
   timeout exception.
   The bounded reader truncates the triggering chunk to remaining capacity,
   kills/reaps the process, and persists at most exactly 1 MiB combined. An
   injected runner returning or raising oversized data is independently clamped
   through the same helper before persistence.
7. Failure evidence could claim `reboot=false` after launch.
   Durable attempt and process-outcome receipts now distinguish no attempt,
   attempted/no return, timeout, overflow, nonzero return, and success. PASS and
   failure both emit the canonical eight-event timeline with explicit no-flash
   phase semantics; unresolved failures use `reboot=null`, not false.

## Second independent review and repair

Independent host-only read-only review session
`019f8090-9c52-71a1-b3c3-918c56c432f3` reviewed committed repair
`f1e22994` with `gpt-5.6-sol` at xhigh effort and again returned
`NO_GO_TO_POLICY_ACTIVATION`. It independently reconfirmed zero prior partition
transfers and closed four of the original seven findings, then found three
remaining implementation blockers and one activation condition:

1. `s22plus_fyg8_r3c0_live_gate.py` imports the unpinned M3 observable helper.
   The exact M3 source is now pinned and the recursive graph-completeness check
   plus an unpinned-transitive-import regression test prevent recurrence.
2. `TimeoutExpired`/`BoundedOdinError` payloads bypassed the combined cap.
   Every return and exception branch now passes through one exact-cap function;
   an oversized timeout regression persists exactly 1 MiB and marks overflow.
3. Run/state ancestry and run-directory durability were under-bound.
   Every repository-relative component through both private roots must now be a
   direct directory. The run is one new direct child, its parent is fsynced, the
   run is revalidated immediately before state publication, and the state is an
   exclusive direct regular file with file and parent durability.
4. The consumed original measured policy must be retired atomically with new
   activation. The new helper rejects activation unless the exact old block has
   one `RETIRED` state and no `ACTIVE` state. The draft requires both changes in
   one later policy-only commit.

The draft also now states the truthful evidence boundary: all invocations that
publish consumed state must emit a result and canonical timeline; host-only
policy, acknowledgement, evidence, or run-directory setup failures before
consumption authorize no contact and need not synthesize a live result.

## Third independent review and repair

Independent host-only read-only review session
`019f80a0-0381-73c0-98ed-87a87d7585b6` reviewed commit `19906092` with
`gpt-5.6-sol` at xhigh effort. It reran all 209 related tests and independently
reconfirmed the complete runtime graph, exact incident evidence, zero prior
partition transfers, inactive new policy, absent recovery state, and no device
contact. Injected failure probes nevertheless returned
`NO_GO_TO_POLICY_ACTIVATION` for three evidence-integrity defects:

1. A transient `result.json` publication failure after `timeline.json` existed
   retried exclusive timeline creation and escaped with consumed state but no
   result. Final records now use exact-byte idempotent create: an existing direct
   regular record is accepted only when it is byte-for-byte identical to the
   attempted JSON. The failure handler reuses only the exact timeline attempted
   by this invocation and then durably records the failure result.
2. Exact Android/Magisk return was discarded if the later no-Odin observer
   failed. Android readiness, serial, final health object, and `reboot=true` are
   now committed to the in-memory result immediately after the exact Android
   gate. The independent Odin-absence fact remains `null` until proven and
   cannot turn an otherwise non-PASS result into PASS.
3. An `OSError` after Odin child creation discarded already collected bytes and
   falsely claimed the process could not start. The bounded runner now converts
   post-spawn I/O failures into a bounded `runner_error`, kills and reaps the
   direct child, and preserves all bytes observed before the error. A raw runner
   `OSError` is also labeled neutrally as failure before return, never as a
   claimed spawn failure.

Four focused regressions cover post-spawn output preservation, neutral raw
runner-error labeling, Android evidence preservation across a no-Odin observer
failure, and idempotent result finalization after an injected first-publication
failure.

## Fourth independent review and repair

Independent host-only read-only review session
`019f80b0-5bf6-75d0-bba4-7bcdfccedd03` reviewed commit `7ffb2857` with
`gpt-5.6-sol` at explicitly verified xhigh effort. It reran the related suite,
reopened the exact incident and policy inputs, and returned
`NO_GO_TO_POLICY_ACTIVATION` for five remaining host-integrity defects:

1. State publication could race a state-parent replacement. The helper now
   opens and holds direct run/state directory descriptors before consumption,
   publishes relative to those descriptors, and revalidates canonical parent,
   state, run, and launch-attempt inode identity before USB observation or Odin
   launch. An injected post-publication parent replacement stops before the
   launch receipt or endpoint observation.
2. A transient publication failure inside an already-failing invocation could
   still suppress timeline or result evidence. Exact-byte idempotent
   publication now makes two bounded attempts independently for each canonical
   record. An injected first failure for both records leaves both exact records
   and the truthful FAIL verdict.
3. Path-based final evidence could accept hardlinks or follow a replaced parent.
   All state, action, process-output, timeline, and result records now use
   descriptor-relative no-follow creation and reopening. Every accepted file
   must be regular with `st_nlink == 1`; hardlink aliases are rejected.
4. Odin inherited the complete caller environment. Its environment is now
   exactly `PATH=/usr/bin:/bin`, `LANG=C`, and `LC_ALL=C`; loader, library,
   Python, locale, and all other caller variables are absent.
5. Timeout/error cleanup used an unbounded child wait. The single 60-second
   budget now reserves a bounded cleanup interval, sends kill if needed, waits
   only for the remaining deadline, and records kill, reap, and cleanup-error
   status. A stuck-child regression proves no unbounded wait is issued.

The focused regressions additionally preserve bytes observed before a
post-spawn error, reject hardlink evidence, and verify the sanitized runner
contract. No device or USB command was executed.

## Fifth independent review and repair

Independent host-only read-only review session
`019f80c7-3ffe-7df1-96cc-69ddf64f6cd5` reviewed commit `2414e911` with
`gpt-5.6-sol` at explicitly verified xhigh effort. It reopened the exact
incident, ran the isolated 217-test suite, and used temporary-directory and mock
fault injection only. It returned `NO_GO_TO_POLICY_ACTIVATION` for six defects:

1. A state-parent replacement immediately after the last pre-launch check could
   still reach action and PASS while the canonical consumed state disappeared.
   The helper now publishes identical one-shot bytes first to an independent
   guard under `workspace/private`, then to the state directory. Either path
   permanently consumes the exception. The held guard, state, run, and action
   identities are checked again before PASS.
2. A run-parent replacement after final Android/Odin observation could return
   PASS with timeline/result only under the renamed inode. PASS publication now
   occurs only after canonical run identity is reopened following observation
   and context teardown. The injected replacement produces a truthful non-PASS.
3. Prerequisite and revalidation `odin4 -l` inherited caller environment and
   stdin through the pinned shared core. The no-AP helper now injects a sealed
   enumeration runner that rewrites to `/proc/self/fd/<odin-fd>`, inherits only
   that fd, uses `/dev/null`, and passes exactly `PATH`, `LANG`, and `LC_ALL`.
4. The shared default enumeration runner had an unbounded error-path wait. The
   no-AP path no longer invokes that default: all three enumeration phases use
   the same total-deadline bounded runner as the final reboot command.
5. A generic post-spawn selector fault could kill the child but lose stdout,
   stderr, and outcome evidence. Every post-spawn exception class is now
   converted to a bounded Odin error carrying captured bytes and kill/reap/
   cleanup status; close and poll anomalies cannot override the evidence.
6. PASS was published before stdout reporting and context teardown, allowing a
   later host error to leave a PASS file while the invocation raised failure.
   Both Odin and transaction contexts now exit before PASS publication. The
   result is the final load-bearing write; summary and descriptor close are
   explicitly non-throwing and non-load-bearing.

Seven added focused regressions reproduce these boundaries, including the
independent reviewer probes. No device, ADB, USB enumeration, Odin binary, or
network command was executed.

## Sixth independent review and repair

Independent host-only read-only review session
`019f80db-b155-7683-85b4-dce120a714d7` reviewed commit `92f99063` with
`gpt-5.6-sol` at explicitly verified xhigh effort. It independently rehashed
the incident, reran the isolated 224-test suite and offline checker, and used
only temporary-directory mock fault injection. It returned
`NO_GO_TO_POLICY_ACTIVATION` for three remaining enforcement defects:

1. The duplicate guard still lived below the swappable common
   `workspace/private` parent. Replacing that parent after the final prelaunch
   check reached action and left both canonical consumption records absent,
   restoring retry authority. The guard now lives directly at the repository
   root, outside `workspace/private`, and its root descriptor remains held.
   The exact common-parent replacement probe now reaches only a truthful FAIL
   while the root guard remains and `recovery_consumed=true`.
2. A bounded prerequisite/revalidation enumeration failure carried captured
   streams and kill/reap status only in its exception object. The shared core
   let that exception escape and the final result retained only its string.
   Every sealed `odin4 -l` invocation now durably publishes its own bounded
   stdout, stderr, and outcome record before return or re-raise. The final
   result binds the complete enumeration-outcome list. Injected partial output,
   `kill_sent=true`, and `reaped=true` survive in both durable files and the
   canonical FAIL result.
3. Old-policy retirement was enforced only inside the extracted old block, so
   a stray exact old `ACTIVE` sentinel elsewhere in `AGENTS.md` was accepted.
   Activation now requires exactly zero old `ACTIVE` sentinels and exactly one
   old `RETIRED` sentinel in the complete file, in addition to exact block
   shape.

Three reviewer-derived regressions plus the expanded enumeration contract bring
the focused suite to 42 tests. No device, ADB, real USB/Odin enumeration, Odin
binary, connected mode, network command, or policy activation occurred.

## Exact repaired identities

- helper: size `74463`, SHA256
  `e924aacf9b3f94c703e756fda30754a4f419557b378cecf524dc8fa69730ee09`
- focused test: size `55511`, SHA256
  `7af7a2706ac690034731fbd8544257724e815b3597f08d146ecbdeab933af928`
- policy draft: size `12242`, SHA256
  `6e7719efc7712d25a4253134e00a14514e46f9b5df369d2489c4d5001c98a957`
- normalized policy template SHA256:
  `bf90b0c5ceeb7178491319cf4dae1e958e30a90c17e0c8badf30189cb13aecdf`

## Host-only validation

- focused no-AP recovery suite: `42/42` PASS
- isolated related helper/core/USBFS/connected/live-core/transport suite:
  `227/227` PASS
- offline verdict:
  `PASS_R4W1C2_NOAP_REBOOT_RECOVERY_SOURCE_HOST_ONLY`
- policy active: `false`
- recovery consumed: `false`
- device contact/write/reboot/Odin transfer/flash: all `false`

No device or USB command was executed during any review or repair. Exact policy
activation remains blocked until a seventh independent adversarial review
returns `GO_TO_EXACT_POLICY_ACTIVATION` on these repaired bytes.
