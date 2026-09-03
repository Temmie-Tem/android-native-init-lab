# S20+ G986N corrected-order TWRP-fastbootd preparation Q1 H0

Status: `CONSUMED_PASS_RETURNED_HEALTHY`

## Bounded correction

The consumed first staged preparation probe returned healthy `NO_PROOF` after
its mount command emitted only a 70-byte `ENOENT` diagnostic. Exact retained-T2
ramdisk inspection shows the recovery's own init creates
`functions/ffs.fastboot` before mounting the named FunctionFS instance. Q1
changes only the order from mount-then-create to create-then-mount.

It remains a preparation-only question while ADB stays attached. It sends no
fastboot request, links no fastboot function into the active gadget, performs
no USB role switch, opens no block path, and writes no persistent state.

## Exact closure

- active runner: 42,079 bytes, SHA-256
  `0f7d3c5ed460ce70ceb37aca0bc369f5ec7cb65d14695067f33c5f039a3fdc3f`;
- activation-normalized runner SHA-256:
  `53d297e007b2a7246a7a1c8cbecb743ec51d53ce5d64eb66789678a25e7a4bdd`;
- terminal-owner focused test: 12,985 bytes, SHA-256
  `f0fe7f0e921e3238acf7793bf0ffb50c8b926a47f8c6881cdc92c236df82eccd`;
- corrected preparation script: 1,978 bytes, SHA-256
  `02cea7562ec7f8b28beeec3086729322c91daff549cc7befc5320c8c86a24ffa`;
- unchanged post-state script: 987 bytes, SHA-256
  `34e74bf7cbfb5185d60d28b265397873a81b41407ab44ddec49d64c5dc8e9481`;
- consumed predecessor terminal: 1,275 bytes, SHA-256
  `ea9a201bf1bd9a093c70a3791ebf4fb1b1b4f489788bfe2660ee2c1d5372221d`;
- consumed predecessor marker: 657 bytes, SHA-256
  `b0349cb99202bb5997f196fc74db7656bf25342f068e5b955339807c0847a4c0`;
- predecessor command result: 688 bytes, SHA-256
  `50042ef670fd700d907773eee4f046039cdb693f1127d9878049a2909d97903e`;
- predecessor raw stdout: 70 bytes, SHA-256
  `6dd9ce2743aaca177c1194e88b0ec4e88493c72f0d59ab1496163855b926ae3a`.

The runner rederives the complete predecessor with zero device contact and
requires its no-replay terminal plus an absent shared guard. Its new intent is
durable before the corrected fixed root-ADB script. That script creates and
verifies only the absent configfs function, mounts and verifies only the fixed
FunctionFS instance, starts only the existing service, and waits at most ten
seconds each for service and endpoints. Ordered stage output and a second fixed
post-read are raw-captured before parsing. Every post-intent outcome requires
physical TWRP System return and fresh exact healthy Android.

Thirteen focused tests cover dormancy and normalized binding, exact predecessor
rederivation, create-before-mount order, forbidden surfaces, stage-prefix
classification, intent-before-effect, failure stop, cut recovery, effect-free
abort, raw-bound success, final strictness, and run-root containment.

Independent review first found and blocked one tracked raw-device-log literal.
The repaired runner validates only the private raw return code, size, SHA-256,
and empty stderr plus the pinned structured result; no raw bytes remain in the
tracked source. Re-review returned `PASS_GO` with CRITICAL/MAJOR/MINOR `0/0/0`.
Mechanical activation set `LIVE_ACTIVE=true` and rotated only the full
runner/test identities and declared status. It creates no standing invocation:
retained-T2 entry and Q1 each require a fresh direct attended request.
Activation-only independent review returned `PASS_GO` with
CRITICAL/MAJOR/MINOR `0/0/0`, exact dormant-hash reconstruction, unchanged
normalized/script/command closure, and reviewer device contacts/writes `0/0`.

## Live result

The sole Q1 invocation emitted all four exact stage lines through
`endpoints-ready`. The fixed post-read proved the FunctionFS mount, configfs
function, running fastbootd service, `ep0/ep1/ep2`, unchanged ADB link and UDC,
absent fastboot link, `mtp,adb`, and running adbd. Its 1,552-byte probe result
SHA-256 is
`89b1bc15c3705e5f0f8c59184b1d50afbb347cfc49f8299f9f1b87510fad8462`.

Attended TWRP System return reached fresh exact healthy Android. The 1,273-byte
final result SHA-256 is
`afdabd50be11120dafb73793c08bbb8b78e69a108a029c13134f6825ba53cc53`
with verdict `PASS_S20PLUS_G986N_TWRP_FASTBOOTD_PREP_Q1_RETURNED_HEALTHY`.
Replay is false, and USB switches, fastboot commands, persistent writes, and
partition operations are zero. The Q1 intent is consumed.
