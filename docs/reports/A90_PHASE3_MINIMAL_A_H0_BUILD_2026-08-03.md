# A90 phase3 minimal-A H0 build

Date: 2026-08-03

Status: `H0_BUILD_PASS_CAPABILITY_PASS_GO`

## Capability

The A90 flat builder can now select the separate Doom engine as an optional
component. An enabled profile must package exactly its active engine. A
disabled profile builds no engine artifact and must package no member under
`bin/a90_doomgeneric_private_engine_*`.

The first disabled-engine profile is
`phase3-minimal-a-no-doom-engine`. It retains the 60-source native init and the
existing helper, removes 47 Doom-only init flags, removes the 80-source engine
build, and grants no candidate authority.

## Host findings and disposition

1. The first build omitted `a90_doomgeneric_bridge.c` and failed during the
   init link. This established a direct remaining dependency from
   `init_v724.c`; the bridge source was restored and the partial output was not
   reused.
2. The next deterministic build exposed three stale engine binaries inherited
   from the base ramdisk. The obsolete set and packed-selection validation were
   extended to remove and reject every observed stale variant. That output was
   not reused.
3. The first independent capability review refused `PASS_GO`: the initial
   check validated the staging directory after packing, not the emitted CPIO.
   The builder now parses the emitted `newc` bytes itself, validates required
   entries and the exact engine family from that archive, and rejects malformed
   structure. Its receipts bind both builder source files and revalidate source,
   manifest, and input pins around execution.
4. The next independent review found canonical-path aliases and permissive
   numeric parsing. The parser now requires each member name to equal its
   canonical POSIX form, every numeric field to contain exactly eight ASCII
   hexadecimal digits, and all member alignment padding to be zero.
5. A fresh A/B output from that exact closure then passed byte identity,
   source-key binding, accepted-input immutability,
   required-entry inspection, exact engine-family absence, static AArch64 ELF
   inspection, and Android boot-image inspection.

## Result and boundary

The final boot is 4,874,240 bytes smaller than the v3404 reference, and its
ramdisk is 4,872,192 bytes smaller. The init is 65,536 bytes smaller; the helper
is unchanged; there is no separate engine artifact.

All work in this report was H0. No USB or device action occurred, no accepted
or rollback artifact was changed, and the profile remains
`candidate_authority=false`. Independent review returned reusable `PASS_GO`
with no unresolved Critical, High, Medium, or Low finding. The receipt retires
when its bound execution-critical closure changes or a new hazard or incident
occurs. It grants no F1 authority; any later F1 remains attended and requires
fresh qualification. S22+ was untouched.

Canonical receipt:
`docs/reports/A90_PHASE3_MINIMAL_A_BUILDER_INDEPENDENT_REVIEW_2026-08-03.json`.
