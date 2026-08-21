# A90 H29 minimal F1 qualification handoff — 2026-08-21

Target: operator-owned Samsung Galaxy A90 5G only
Tier: H0 public-scope qualification input and review handoff
Authority: none; no D0, approval, ordinal, F1, transfer, reboot, physical action, or live effect

## Review subject

Review the H29 candidate-neutral minimal owner against the public input at
`docs/reports/A90_H29_MINIMAL_F1_QUALIFICATION_INPUT_2026-08-21.json`.
The review must bind the current owner execution closure
`c2da655e18e54d06be9a054ee4fad8de19a4e6901fd60e4104be8b2c817ec68d`. The
current public single-Samsung candidate-return review is direct-regular and
`PASS_GO` at
`5fc90b7491a26acd9b37ca9f997f8a1e7edc62606196434e6f84ece6cecc12a0`, and
binds continuation closure
`9b17904db2374664d91af10e98b8c8f9d4e1cdee5e8ac9514018838d4dfafeb5`. Review
bytes remain outside the owner execution closure.

This is a fresh H29 qualification input. The consumed H28 review and its
`0dca4f3ddc98eb4625411c93ad7c1748f3c016aab0075a570652ca946fc4eb1f`
execution closure are historical only and must not be promoted or copied into
the H29 review. H27 and H28 candidate hashes are explicitly distinct from H29.

## Exact H29 claim

H29 is version `0.11.196`, build
`phase3-minimal-h29-stock-rebuild-1007-cfp`, size `58,372,096`, SHA-256
`c3d1b84eab65f387ce807cf9c355dc04dcc966cef15bf64e4fda901242907324`.
The public build report and flat-builder manifest are bound by their declared
SHA-256 values in the input. The H29 materialization is identity-only relative
to the H28 functional configuration; whether it boots A90 is unproved.

The exact rollback remains V2321 `0.9.285 /
v2321-usb-clean-identity-rodata`, size `60,882,944`, SHA-256
`ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
The H29 fresh-state generation is separate:

* `/cache/a90-auto-handoff-phase3-minimal-h29.enable`
* `/cache/a90-auto-handoff-phase3-minimal-h29.done`

The hazard is `A90_SELF_BUILT_KERNEL_BOOT_ACCEPTANCE_WITH_NEW_BUILD_CERT`.
Its exact UTF-8/no-trailing-newline statement and digest are in the input. The
qualification is limited to one attended boot-only Native health experiment
with exact V2321 rollback. Android/vendor external-module compatibility, stock
byte equivalence, full build reproducibility, and the H29 boot result remain
unproved.

## Recovery binding and privacy boundary

The demonstrated recovery profile and method are fixed to
`A90_ATTENDED_PHYSICAL_RECOVERY_V1` and
`NATIVE_TO_STABLE_ADB_BASELINE_SINGLE_NEW_RECOVERY_ARRIVAL_BOOT_READBACK_V1`.
The public input intentionally does **not** invent or expose a recovery ADB
serial. `recoveryIdentity.status` is
`UNBOUND_PRIVATE_MANIFEST_REQUIRED`, with `adbSerialSha256: null` and
`rawSerialTracked: false`. The exact 64-hex serial digest must be supplied by
the operator-side private manifest from the attended recovery qualification
before any owner manifest or review can be accepted. This H0 handoff neither
opens private bytes nor treats a placeholder as a target identity.

The continuation review binds the reusable fixed backend's current
single-Samsung operational precondition: exactly one Samsung USB endpoint,
Native `04e8:6861` with zero ADB rows, or Recovery `04e8:6860` with exactly one
bound recovery ADB row. Extra Samsung/ADB endpoints or ambiguity park before
per-device contact. This is an A90 operational speed/safety precondition, not
a permanent common boundary; multi-device support is out of scope.

## Required review checks

1. Read `AGENTS.md`, `docs/operations/targets/A90_TARGET_CONTRACT.md`, and
   `GOAL_A90.md` in order.
2. Recompute `owner.execution_closure_sha256()` and require the declared
   `c2da655e…` value exactly. Do not include this input, this handoff, the
   continuation review, or any private manifest in that closure.
3. Confirm the named continuation review is the exact public direct-regular
   JSON with `PASS_GO`, current closure `9b17904d…`, zero findings/contacts,
   and `liveAuthority=false`.
4. Confirm exact H29 candidate/rollback identities, H29 fresh-state paths,
   H29 build-report/flat-manifest digests, and distinct H27/H28 candidate
   identities. Do not open `workspace/private` in this review.
5. Confirm the recovery profile/method and the explicit unbound-private serial
   declaration. A review must not replace `null` with a guessed or derived
   serial hash; the eventual private manifest must bind the exact digest.
6. Confirm the hazard statement digest, accepted flag, one candidate attempt,
   one V2321 rollback, boot-only partition scope, intent-before-effect,
   no-replay, single-Samsung precondition, and bounded final Native health.
7. Attack candidate substitution, H27/H28 review reuse, changed H29 state
   paths, stale owner/continuation closures, report/manifest hash drift,
   hazard statement mutation, nonzero/boolean substitution, and accidental
   authority flags.

## Expected review artifact

On `PASS_GO`, publish one canonical JSON at
`docs/reports/A90_BOOT_ONLY_F1_MINIMAL_H29_INDEPENDENT_REVIEW_2026-08-21.json`
using `a90-boot-only-f1-minimal-independent-review-v1`. It must bind the exact
H29 candidate and V2321 rollback, current owner closure, recovery and hazard
objects, H29 fresh-state paths, zero findings/contacts, and
`liveAuthority=false`. It must not create a private manifest, D0, attended
approval, token, or device authority. The private serial digest remains a
separate operator-side binding; its absence here is deliberate and fail-closed.

After a valid independent H29 review exists, the operator-side owner may build
one private manifest that supplies the exact private candidate/rollback paths,
review path/size/SHA, and the exact recovery serial digest. That later step is
still H0 and does not grant D0 or F1; current target preflight, attended
approval, and the contract's live activation remain separate.
