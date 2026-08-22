# A90 public-MPGen RTIC canary hazard review handoff — H0

Date: 2026-08-23
Target: Samsung Galaxy A90 5G only
Tier: H0 independent hazard-decision handoff
Device contact: none
Authority: none — this handoff allocates no candidate, version, manifest,
approval, ordinal, journal, D0, D1, F1, transfer, reboot, rollback, or replay

## Decision requested

Decide whether the exact rebuilt kernel bytes below may become the kernel input
to **one future attended boot-only Native-health canary**, after every ordinary
candidate, recovery, qualification, D0, and approval prerequisite is separately
satisfied.

The narrow canary question is:

> Does the operator-owned A90 accept one fresh boot-only candidate containing
> this exact structurally self-consistent, stock-policy-shaped public-MPGen
> kernel and reach exact bounded Native health before any Debian handoff?

The accepted result, if any, must be `PASS_GO_H0_CANARY_HAZARD`. It means only
that one future canary is a proportionate discriminator for the named unknowns.
It is not `PASS`, production equivalence, a candidate qualification, a run
approval, or live authority. `NO_GO` must name a concrete blocker and objective
retirement evidence; an unbounded demand for unavailable proprietary source is
not by itself a falsifiable gate.

## Exact bytes under hazard review

| Surface | Bound value |
|---|---|
| raw Image | 48,830,480 / `1ddae56f8df97030794a590192e4a4162876736029b1a54fd26173c9287002b7` |
| expected comparison carrier | 49,827,613 / `15b49a71aeb2342a5b5a7e24de27f78a4124bf877f6d8d8f28aaab928fa6bd71` |
| generated RTIC DTB | 173 / `68e6ab5bb2ccdde5e3d87086110257176c0fe55726d1d4f5db6eba3a4b6aca04` |
| MP bytes | 1,624 / `d95fd9710dd019c5f2e0a273669bcb9b96f81dfdf994afd940b9abb4ff04ec69` |
| MP VA / raw offset / interface | `0xffffff8009f00000` / `0x01e80000` / `30.3` |
| task offsets | `88/1704/1728/2144` |
| catalog | ordered RO/WK/WU/AW `3/1/2/0` |
| source report | `A90_RTIC_LOCATOR_REPAIRED_DETERMINISTIC_REBUILD_H0_2026-08-23.md` / `fcd1a282ad072cbc22a93b0596c2858797db5599e2d3fae3cd9d71de1ac32e2f` |
| source commit | `1639f7c6a3` |

The comparison carrier is a host-only construction of the exact raw Image,
the same first two stock hardware DTBs, and the generated RTIC DTB. A later
candidate builder must reproduce that exact kernel-wrapper hash; the handoff
does not create or name a boot image.

## Static facts already closed

The reviewer may rely on these public-scope conclusions only to the extent
their cited report supports them:

- the selected OSRC/config/toolchain and historical MPGen identities are exact;
- the MPGen subtree is byte-clean and the stock clock is injected outside it;
- the public catalog is the exact ordered stock `3/1/2/0` shape;
- all three mapped objects are exact and the unchanged decoder returns the
  stock task offsets;
- every MPGen pass emits those offsets with no sentinel;
- two fresh sequential output trees produce byte-identical complete selected
  outputs, including `vmlinux` and Image;
- the RTIC validator passes the exact wrapper/FDT/`MP_DATA`/range/marker/hash/
  interface binding in both builds; and
- relative to the preceding stock-shaped control, only two build-ID ranges and
  the 16-byte task-offset field change. No CFP or configuration byte changes.

The earlier independent decision is `PASS_H0_BUILD_GATE`. It did not accept
the canary hazard and grants no authority.

## Complete residual hazard bundle

The review must decide the bundle as a whole. It may not silently delete or
reinterpret one member after a successful boot.

### H1 — non-stock MPGen content version

The MP reports public content version `2.7.e26468.30`, not stock
`2.7.ef86a6.30`. Both use structure interface `30.3`; available source does
not prove whether the proprietary consumer checks only the interface, accepts
this producer, or rejects it. The canary may distinguish boot acceptance but
cannot prove production-tool equivalence.

### H2 — candidate-derived measured extent

The rebuilt MP describes extent `0x039d3000`, not stock `0x03973000`. The value
is derived from the final candidate link and bound by its generated DTB; forcing
the stock extent would describe different bytes. Proprietary acceptance of a
different valid extent remains unproved.

### H3 — public catalog and producer provenance

The selected historical public tree is a Qualcomm-derived 2.7 implementation
whose catalog comments do not assert Samsung production provenance. Exact
producer identity and output determinism are proved; production equivalence is
not. A successful canary must not relabel this source as the stock producer.

### H4 — proprietary RTIC/QHEE response

Available Qualcomm source proves that `MP_DATA` is sent to QHEE, but exact A90
ABL/TZ/HYP code and failure semantics are unavailable. Rejection may appear as
an early reset or boot loop. A successful Native boot establishes only that the
exact canary traversed the enforced path far enough to reach its bounded health
predicate.

### H5 — possible proprietary whole-Image measurement

The rebuilt Image necessarily differs broadly from stock even when its config
and layout controls match. The retained locally generated module-signing X.509,
compiler output, and normalized build IDs could be covered by an unavailable
proprietary measurement. Linux's in-kernel module verifier is not an early
Image-acceptance path, but that does not disprove an external whole-Image check.

### H6 — standalone-product secondary input gaps

The standalone build lacks Samsung's `secgetspf` product query. Existing source
analysis limits its visible effects to SEP-version flags, one fingerprint
conditional, and one WLAN MIMO define. This canary claims only early Native
boot health and performs no Wi-Fi, external-module, Debian, or production-
stability test. Success cannot close those later gaps; failure without bounded
evidence cannot be attributed specifically to RTIC.

## Why a canary may be proportionate

All known producer and binding defects are now statically closed. The remaining
questions are properties of unavailable proprietary consumers and therefore
cannot be retired by another comparison of the same public bytes. The proposed
experiment changes only `boot`, has one exact V2321 rollback, forbids candidate
replay, and already has a reviewed first-opportunity TWRP `/proc/last_kmsg`
evidence path before rollback. It does not write UFS rootfs content or another
partition.

This paragraph is an argument for review, not authority. The reviewer must
reject the bundle if the record identifies a known destructive consequence,
an unresolved static inconsistency, an unbounded effect, or a confounding
candidate change that prevents the narrow question from being answered.

## Mandatory future prerequisites outside this review

Even a hazard `PASS_GO` leaves all of these requirements fresh and separate:

1. allocate a new successor identity only after the review is final;
2. construct the kernel carrier from the exact reviewed Image, the exact two
   hardware DTBs, and the exact generated RTIC DTB, reproducing the expected
   carrier hash;
3. keep the native ramdisk execution semantics equal to the already reviewed
   minimal owner input except for the fresh identity/state-path substitutions
   required by that owner, and review any additional semantic change;
4. produce a candidate-specific boot image, qualification, manifest, hashes,
   and exact hazard binding;
5. revalidate the unchanged owner, candidate-return continuation, failed-boot
   observer, rollback, and postrollback closures and current review artifacts;
6. establish exact healthy current V2321 and physical recovery through fresh
   connected D0; current tracked V2321 health is unproved;
7. obtain one fresh attended approval for that exact candidate/rollback pair;
8. execute the candidate at most once, capture first-opportunity evidence on
   failure, and follow only the journal-bound one-shot rollback/recovery path.

H34 and every earlier candidate remain consumed and non-replayable. A hazard
review cannot waive, merge, or pre-satisfy any item above.

## Required reviewer output

Return one exact verdict plus findings:

- `PASS_GO_H0_CANARY_HAZARD` only if all H1–H6 are explicitly accepted as the
  bounded risk of one future attended canary;
- otherwise `NO_GO_H0_CANARY_HAZARD` with HIGH/MEDIUM/LOW findings, exact
  evidence, and an objective retirement condition for each blocker.

The reviewer must state that contacts with device, `/dev`, USB, ADB, network,
other targets, and `workspace/private` were all zero, and that the verdict
grants no candidate or live authority.
