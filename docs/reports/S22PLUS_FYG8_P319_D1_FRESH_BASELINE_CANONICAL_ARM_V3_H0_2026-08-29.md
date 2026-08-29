# S22+ FYG8 P3.19 D1 fresh-baseline canonical-arm V3 H0 report

Date: 2026-08-29

Status: **INDEPENDENTLY REVIEWED / PASS_GO / NOT ACTIVE**

## Cause

The consumed D1 V2 invocation stopped before every device command because its
production P3.18 arm writer emitted indented JSON while the V2 validator
required compact canonical JSON. The exact approval and ordinal remain
consumed without replay. Its 773-byte arm and 1,989-byte stop prove no start,
raw acquisition, reboot dispatch, result, Download transition, or payload.

The pre-F1 autonomous runner cannot bind that known-failing V2 source. A fresh
normal-reboot descriptor therefore requires a new ordinal whose production arm
writer and production validator agree before any acquisition can begin.

## Change

`s22plus_fyg8_p319_d1_fresh_baseline_v3.py` preserves the reviewed V2 execution
and raw-first path but uses the pinned V1 canonical writer
`_durable_create()` for its new arm. A host-only seam fixture executes that
writer into V3's real `_arm_complete()` validator and requires byte-canonical
success before the acquisition boundary.

V3 uses only the new fixed ordinal `d1-fresh-baseline-3` and new private
namespace. Its binding pins the exact reviewed V1 and V2 sources/bindings plus
both consumed arm/stop pairs. The consumed V2 stop is semantically checked for
`NAMESPACE_PUBLICATION`, `during-arm-publication`, absent start/result/raw,
false reboot-dispatch possibility, false result reuse, and false replay. A
generic exception containing “already exists” is not accepted as duplicate-arm
proof; only the exact V1 journal error for V3's fixed arm becomes
`CanonicalArmAlreadyExists`.

## Boundary

The tracked binding records the exact independent `PASS_GO`, but that capability
review is not a current operator approval. The default CLI is the host-only
self-test. No token was issued, no approval exists, and no device, USB
transport, reboot, Download, payload, D0, D1, F1, recovery, or replay authority
is created.

V3 is a prerequisite candidate for the future autonomous normal-reboot
descriptor, not that descriptor's activation. The pre-F1 catalog and
coordinator remain `DEFINED_NOT_ACTIVE`; Process-v2 and F1 are unchanged.
Machine integration remains blocked on `FRESH_BASELINE_MISSING`.

## Validation

The reviewed source is 73,125 bytes with SHA-256
`cb13236e1fb10bf25ac47f7706df050abe15b2ab5a7e423bbdc7b5b31c2c491d`.
The 6,650-byte `1f5f5ffc` review-pending binding remains in Git history. The
canonical reviewed binding is 6,705 bytes with SHA-256
`dcb869aeeebf877d669da0a1f45b8c1d56a65777c13c9d518c0ad2dace93fc10`.
The raw-first auditor registers V3 as its nineteenth active source and emits a
13,518-byte mode-0400 receipt with SHA-256
`5562f3e56f7ac92f8da89b1932ad60f6b4313c429ef09ddacf3feb11ae8b9bbf`;
the 12,916-byte `66658f67` predecessor remains unmodified.
The exact 70,669-byte auditor is `626ae50d`. V3 hostile tests pass 31/31,
raw-first hostile tests pass 24/24, raw-first documentation tests pass 19/19,
taxonomy passes 39/39, and the common Process-v2 selection passes 142/142.
The default self-test returns
`PASS_P319_D1_FRESH_BASELINE_V3_CANONICAL_ARM_FIXTURE_H0`, reports the consumed
V2 binding, and makes no process or device call. The V3 suite inherits the 28
reviewed V2 hostile cases and replaces only version/binding/report assertions;
three additional cases cover V2 provenance, the canonical writer-to-validator
seam, and exact duplicate classification. Independent read-only review of
implementation commit `3c062fb386` found no remaining load-bearing blocker and
approved only this H0 capability.
