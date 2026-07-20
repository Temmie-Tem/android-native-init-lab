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

## Exact repaired identities

- helper: size `47465`, SHA256
  `dd85eddca9d75376a248cfa77b143e52580b4d49a74dca9fb3ee93c48a77d263`
- focused test: size `22633`, SHA256
  `ca64906a889dca3cb3b4c5b958afb91c73ba204bab9cb284a1df200ce3847479`
- policy draft: size `9001`, SHA256
  `c72651e338576feddf43068479148db2e9b41da5d5e68a09a3a8c6aa030320a5`
- normalized policy template SHA256:
  `9eab648aec876d5e229e35926927dcf06cea8d1ab70c034df312b7e1a064d7f9`

## Host-only validation

- focused no-AP recovery suite: `24/24` PASS
- related helper/core/USBFS/connected/live-core/transport suite: `209/209` PASS
- offline verdict:
  `PASS_R4W1C2_NOAP_REBOOT_RECOVERY_SOURCE_HOST_ONLY`
- policy active: `false`
- recovery consumed: `false`
- device contact/write/reboot/Odin transfer/flash: all `false`

No device or USB command was executed during either review or repair. Exact
policy activation remains blocked until a fresh independent adversarial review
returns `GO_TO_EXACT_POLICY_ACTIVATION` on these repaired bytes.
