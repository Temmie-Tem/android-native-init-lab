# P353 static first-frame preparation

P353 is a fresh successor for one observable transition from the boot logo to
a fixed static pattern: red/blue upper blocks and a green lower block with a
large black cross. The operator's visual observation establishes that narrow
output claim. Counter updates, completed display disable and post-display USB
are not its success criteria. Exact rollback and final rooted FYG8 health remain
separate mandatory outcomes. P352 stays consumed, NO_PROOF and rolled back.

The operator authorized implementation, H0 qualification and attended D0/D1
preparation through F1 approval-code issuance, and confirmed physical attendance.
That request does not authorize F1 execution. The ordinary fresh returned token
is still required after connected preparation.

## Implementation

The new renderer is generated from sealed P352/P351 sources. It retains twelve
exact display additions, fresh provider readiness, the source-bound `msm_drm`
name and exact 30HS timing. It snapshots all initial planes before any atomic
request and rejects nonzero inherited FBs, foreign active CRTCs, unexpected
connector attachments, duplicate/missing plane identities and unexpected primary
zpos/alpha/nonsecure-translation defaults.

One XRGB8888 WC buffer uses a 4352-byte pitch and 10183680-byte allocation. The
complete desired state contains CRTC mode/active first, selected connector,
selected primary FB/full rectangles, and explicit FB_ID=0/CRTC_ID=0 for every
other inherited plane on that CRTC. One blocking ALLOW_MODESET commit retains
kernel validation without a separate TEST_ONLY request. The successful child
keeps its fd/FB/GEM/mapping during the attended window, with no redraw or normal
cleanup. The vendor's CRTC/CTL replacement is the proposed old-composition
removal mechanism; actual hardware output remains unproved until observed.

A plain white fill is insufficiently distinctive because the vendor has a
white-on-error path. The fixed multicolor pattern is generated directly by the
actual C renderer; its H0 preview is retained privately.

The host completes an authenticated prefix: OPEN, READY, BOOT and the fixed
sequence-3 parent identity, then writes the exact authenticated sequence-4
`P353_DISPLAY_ONCE` request once. It reads no sequence-4 response and sends no
sequence 5, CLOSE, CANCEL or later action. The machine receipt proves only
**authenticated host dispatch**, not child receipt/execution, commit completion,
session closure or visible output. Raw replay reconstructs that same exact
prefix and rejects truncation, wrong HMAC, extra frames and proof promotion.

After the authenticated fixed request, the device supervisor retains its
existing one-shot-before-fork slot and 60-second child/group deadline. It drains
the local diagnostic pipe without tty forwarding or cancellation reads. Normal
exit, setup failure, error and timeout enter terminal park before the generic
error publisher or another listener. Host tty closure therefore does not control
the display child's lifetime. The child remains subject to its existing bound;
this is not an indefinite usable runtime or automatic recovery claim. Local
post-dispatch diagnostic text is ephemeral and is not claimed as captured output.

The observer retains exact pre-dispatch lane evidence and an actual immutable
candidate-end raw endpoint snapshot separately. The latter is a transport
diagnostic; capture failure is explicitly incomplete and never claims continuity.
It cannot undo a completed host write or an independent visual observation, and
does not permit another experimental effect. Ordinary exact Download/rollback
binding and no-replay rules remain unchanged. The implementation and reasoning
are scoped in the [P353 target clause](../operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md).

## H0 qualification

The Image changes only the established same-length run identity to
`c353f1e0a90b5e6d7c8a9b0c1d2e3f0b`; its identity is `41490944B`, SHA-256
`68f6aa66cb29cf94cd7c857545cffd54fc0a250f9bb0a98208a7a153a32e84d9`.
The kernel behavior, USB module plan and exact display module bytes are unchanged.

A/B userspace, renderer, boot and AP bytes match. The candidate AP is
`30965801B`, SHA-256
`a4515202203d667c4e9beef117fbc86b304c961e1c1e953a9865c3146d8f6c88`.
It contains only `boot.img.lz4`, `30959545B`, SHA-256
`fe273c5f0968f9f70367a260fb50e277a69b0664d755419522ec8a51bd16d9b9`.
The exact Magisk rollback remains `23367721B/d2373bf8`.

Twenty-one P353 tests pass: actual generated renderer against mocked DRM, actual
authenticated prefix/replay and immutable receipt reopening, post-write reporting
and fd-close failures, candidate-end snapshot integrity/failure, Carrier terminal
roundtrips, and generated-C supervisor joins over host sockets/fork/pipes. The C
join closes the host endpoint immediately after dispatch and covers normal exit,
error and the unchanged 60-second timeout using a scaled fixture clock. Tty
access traps and terminal-park interception check that the branch cannot return
to the old session/error-publisher path. Platform/child-isolation/DRM hardware
are not emulated by that join.

The real Carrier encoder/representation/adapter roundtrip covers COMPLETE,
INCOMPLETE and AMBIGUOUS plus wrong-run, corrupt Carrier and mismatched terminal
detail rejection. Carrier remains supplemental and cannot prove visible output.
An initial direct call to the private P320 parser's own audit hit its historical
default-run binding; the actual P353 adapter entry points were then used for
the qualification. No parser assertion or consumed result was changed.

Common live tests pass 74/74. The earlier focused run passes 35/35, including
unchanged P352 observer/live, P345 runtime and P347 regressions. Relevant Python
compilation and AArch64/static-ELF checks pass. One initial C build stopped on a
pointer-signedness warning in the new terminal comparison; a const-char cast
fixed it before the successful fresh A/B output. The failed H0 output is retained.

Independent review identified and resolved pre-dispatch parent-duration
validation, preservation of already-dispatched audit on reporting/close errors,
explicit dispatch-only final-result projection and actual closure-snapshot
bookkeeping and the nested preparation CLI entry ordering. Final independent
review is PASS_GO for the named unchanged capability closure; the receipt is
retained privately with SHA-256
`3e6e5d767294491b1c76aae2002c8425aa573b90dc38ec7a0077fc684ee9888e`.
Neither a machine dispatch PASS nor a healthy rollback upgrades visual output.

## Evidence and current preparation

Private artifacts and checks are under
`workspace/private/outputs/s22plus_fyg8_p353/`. The successful build directory is
`stock-candidate-build-v1-20260907-01/`. Earlier unapproved H0 static/promotion
records are preserved separately when the closure-snapshot binding was added;
they create no device authority.

Related source investigation:
[P352 initial plane and static first-frame follow-up](S22PLUS_FYG8_P352_INITIAL_PLANE_INVESTIGATION_H0_2026-09-07.md).

Final static qualification binds 100 source inputs. The real promotion CLI
publishes ready manifest `4686B/9f91cc6f` with bundle
`a7a1b491b9c867d39464135bc27cc8ffdc61246b2edaa2fd6aef43bb0ca3c363`.
The prior H0 entry-order failure is preserved; the fixed entry point runs once
after P353 overrides and has a direct CLI regression test.

Initial connected D0 preserved a typed baseline-classification stop:
`baseline-decoder-rejected`; host-only replay reports retained current/legacy/
partial evidence family. Initial exact rooted FYG8 health passed. The approved
one-normal-reboot D1 then passed `PASS_P353_D1_EXACT_NORMAL_REBOOT_RETURN_HEALTH`,
with one reboot, changed boot ID, matching boot/supporting hashes and absent
Download. Its private linked result is SHA-256
`a360e41d8415fdf793f23ac038461d1923924509074a75cca6f2acce78ef8f75`.
No candidate or partition transfer occurred and no other target was commanded.

Fresh connected D0 passes `PASS_DEVICE_ACTION_D0_V2_CONNECTED_READ_ONLY`,
with a clean baseline. The fresh prepared record is retained at private run
`p353-ready1-prepared-20260907-2`, SHA-256
`0063e16b798872d87abfcac1046ba100cdc0a42b6be88f08e895a4cac818864f`;
its D0 result SHA-256 is
`6f5564cccfb7219e45f233ce318ac938f68a3da9b39b8f0877a15e8d71b9f647`.
The exact approval code has been issued from that binding. F1 is not authorized
until the operator returns it; no candidate or rollback transfer occurred.
Visible output remains UNPROVED. A90 and S20+ received no device command.
