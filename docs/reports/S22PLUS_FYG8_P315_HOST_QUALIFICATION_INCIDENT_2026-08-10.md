# S22+ FYG8 P3.15 host qualification incident

Date: 2026-08-10 KST

Target: Samsung Galaxy S22+ FYG8 (`SM-S906N` / `g0q`) only

Classification: `PREDEVICE_QUALIFICATION_AUTHORITY_SEAM_FAILURES`

## Safety result

Both failures occurred during H0 qualification before any connected device
command, Download handoff, Odin invocation, reboot, payload transfer, or F1
arm. No candidate was used on a device. A90 received no command. The failed
private output directories are preserved and are not reusable qualification
artifacts.

## Incident 1: direct-script module identity split

The actual candidate builder validates the hash-bound P3.15 prepackaging
closure before delegating to the inherited parent packager. On its first direct
script execution, root-bound validation imported the same builder by its
canonical module name while the entry process already held it as `__main__`.
That created two Python module objects with separate
`_PREPACKAGING_RECEIPT` and `_PREPACKAGING_VALIDATION` globals. Validation
passed in one object, but the late artifact-safety callback ran in the other
and failed closed with `P3.15 prepackaging gate was not established`.

The bounded repair aliases the direct-script module under its canonical name
before importing the parent or packaging audit. The actual packaging-wiring
audit now requires that alias exactly once and before the parent import. Its
negative fixtures still prove that missing or invalid proof produces zero
parent-packager calls and zero package output. A focused independent review of
this repair returned `PASS_GO`.

## Incident 2: inherited userspace identity omission

After the first repair, reproducible packaging succeeded, but the real static
checker rejected the P3.15 userspace result because it omitted inherited
top-level field `callsite_descriptor_a_b_identical: true`. The descriptor was
unchanged and independently fixed, but P3.15's newly serialized result did not
carry the exact identity witness required by its P3.11-derived static contract.

The bounded repair restores that exact field in the P3.15 userspace result and
adds a focused source regression requiring one occurrence. It does not change
the fixed Image, trace descriptor, callsite offsets, carrier, module plan, or
kernel. A focused independent review of this repair returned `PASS_GO`.

## Final closure

The corrected execution passed the root-bound prepackaging validator, actual
251,450-cell Process-v2 adapter/persistence matrix, two byte-identical
userspace builds, two byte-identical boot-only candidate packages, final
qualification, independent static closure, Process-v2 promotion, and real
ready-manifest verification. The canonical ready manifest has SHA-256
`a7f37b4fa9eb8783f90130e1a7eeb3ecc2053515527ed1f61046f111ba227c5f`.

These incidents establish two reusable host boundaries:

1. a validator and the callback consuming its process-local state must share
   one canonical module identity during direct execution; and
2. a successor result that preserves an inherited artifact contract must also
   preserve every identity field consumed by that contract's real checker.

Neither incident grants D0, D1, or F1 authority. A fresh connected D0 and
exact live binding remain mandatory before an F1 approval can be requested.
