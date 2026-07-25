# S22+ FYG8 P2.63 E3 artifact-safety contract correction (H0)

Date: 2026-07-25 KST
Tier: H0
Status: `PASS_P263_E3_ARTIFACT_SAFETY_CONTRACT_HOST_ONLY`
Live authority: none

## Stop Before Packaging

The P2.60 v2 clean Full-LTO A/B builds completed and all six linked artifacts
were byte-identical. The linked audit also passed. Promotion stopped before
candidate packaging because the generic candidate builder would have emitted
this historical E2 claim:

`no_userspace_sysfs_or_configfs_write=true`

That claim is false for P2.60. The exact source-bound E3 runtime intentionally
writes the bounded SSUSB peripheral role and one exact CDC-ACM configfs gadget
before opening `ttyGS0` and writing the banner.

No v2 candidate AP was created or promoted. No device was contacted, and no
F1 binding or approval exists.

## Cause

The deterministic candidate builder and its static checker duplicated one
profile-level safety dictionary. All E2 contracts inherited P2.42's historical
read-only USB statement even after P2.60 introduced its exact bounded E3
write authority. The P2.60 source receipt already included the builder, so
repairing this statement invalidates the v2 intent and both linked builds for
promotion even though their bytes were reproducible.

## Correction

The candidate builder now owns the safety dictionary as one function selected
by exact source contract:

- non-E2 behavior is unchanged;
- historical E2 behavior keeps the read-only USB claim unchanged; and
- P2.60 replaces that false claim with exact source-contract-bound
  sysfs/configfs scope and bounded CDC-ACM/peripheral-role scope.

The candidate static checker consumes the same function instead of maintaining
a second dictionary. The P2.60 source contract requires the selector and both
E3 scope strings in its source-receipted registration closure.

## Validation

Focused validation proves:

1. historical E2 still emits the original read-only safety contract;
2. P2.60 does not claim absence of sysfs/configfs writes;
3. P2.60 emits both exact bounded scope strings;
4. adding the historical no-write claim to a P2.60 artifact is rejected;
5. every field of the complete P2.60 map fails independently when mutated;
6. complete E1, historical E2, and P2.60 maps are independently pinned;
7. an AST audit proves `build_candidate()` consumes the exact-contract helper;
8. the deterministic candidate checker consumes the builder's definition; and
9. the full P2.60 source-contract implementation audit still passes.

Python compilation, 31 focused tests, and `git diff --check` passed. The first
independent review returned `NO-GO` because generator, checker, and tests could
have drifted together. Complete independent expected maps, every-field
mutations, and an AST call-site mutation closed that finding. Read-only
re-review returned `GO` with no remaining finding. This unit
does not change kernel or userspace runtime behavior. It corrects only the
truthfulness and single-source ownership of deterministic artifact metadata.

## Consequence

The v2 intent, A/B bundles, and linked audit remain diagnostic build evidence
but are not promotable. P2.63 must derive one fresh intent from the corrected
source receipts, repeat clean Full-LTO A/B, package and statically verify both
deterministic candidates, and only then proceed to D0 and Process v2
preparation.
