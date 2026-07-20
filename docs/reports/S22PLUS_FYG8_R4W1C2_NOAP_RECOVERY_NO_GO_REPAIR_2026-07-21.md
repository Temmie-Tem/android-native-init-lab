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
   boot-only live core, USBFS identity observer, transport helper, birth-time
   `stat`, and Odin executable before contact and again before consumption. The
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
6. The 1 MiB output bound could overshoot by one read.
   The bounded reader truncates the triggering chunk to remaining capacity,
   kills/reaps the process, and persists at most exactly 1 MiB combined. An
   injected runner returning oversized data is independently clamped before
   persistence.
7. Failure evidence could claim `reboot=false` after launch.
   Durable attempt and process-outcome receipts now distinguish no attempt,
   attempted/no return, timeout, overflow, nonzero return, and success. PASS and
   failure both emit the canonical eight-event timeline with explicit no-flash
   phase semantics; unresolved failures use `reboot=null`, not false.

## Exact repaired identities

- helper: size `41971`, SHA256
  `98bd04ae429ad44d841b7794c61243aab9744204be1367b963b7db99e1147543`
- focused test: size `17301`, SHA256
  `233e0fefdef59ff87d81be575bb128e82d41ee04ec510df78b28d84345fa86d2`
- policy draft: size `7976`, SHA256
  `60854877d6cbde0b816b064d30e64a3f38d4581badb440bd3c4ee78f047d4d6f`
- normalized policy template SHA256:
  `9524e207e5949655af4c114afedc4d65aaef81e6513c5f7f7b34470b5b6bf72f`

## Host-only validation

- focused no-AP recovery suite: `18/18` PASS
- related helper/core/USBFS/connected/live-core suite: `185/185` PASS
- offline verdict:
  `PASS_R4W1C2_NOAP_REBOOT_RECOVERY_SOURCE_HOST_ONLY`
- policy active: `false`
- recovery consumed: `false`
- device contact/write/reboot/Odin transfer/flash: all `false`

No device or USB command was executed during the review or repair. Exact policy
activation remains blocked until a second independent adversarial review returns
`GO_TO_EXACT_POLICY_ACTIVATION` on these repaired bytes.
