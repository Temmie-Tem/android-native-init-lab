# S22+ FYG8 P2.58A UDC predicate repair design

Date: 2026-07-25 KST
Tier: H0
Status: `DESIGN_COMPLETE_P258A_UDC_PREDICATE_REPAIR_H0`
Live authority: none

## Objective

Repair the P2.57 UDC observation contract without changing the kernel, module
plan, stage sequence, detail namespace, device policy, or write authority.

The repaired contract must:

1. accept the known-good FYG8 topology where `dummy_udc.0` and
   `a600000.dwc3` coexist;
2. require exact identity of `a600000.dwc3`;
3. ignore unrelated valid UDC peers;
4. give the asynchronous DWC3-to-UDC boundary one fresh five-second dwell;
5. preserve fail-closed malformed/read/regression behavior; and
6. make the known-good topology executable validation input, not prose.

## Recurrence Prevention

Every new classifier predicate must carry a semantic oracle matrix before it
can pass source-contract validation:

```text
known-good target state                 -> PASS
target absent                           -> NOT_READY/FAIL
target plus unrelated valid peer        -> PASS unless exclusivity is proven
wrong type or wrong resolved identity   -> FAIL_CLOSED
malformed observation or read error     -> FAIL_CLOSED
```

The positive oracle must come from a canonical machine-readable stock
snapshot. A checker that verifies only function names, strings, compilation,
or internal descriptor consistency is insufficient.

For P2.58A the canonical stock snapshot is
`docs/module-map/s22plus-fyg8/stock-usb-runtime-topology.json`. Its
`sysfs.udc_entries` field must contain both observed UDC names. Source-contract
validation fails if the field is absent, malformed, or differs from the
descriptor's known-good fixture.

This is intentionally a focused guard, not a new repository-wide policy
engine. Future classifier families should reuse the same positive/negative/
peer principle with their own domain-specific evaluator.

## Runtime Predicate

Retire:

```c
entries == 1U && exact == 1U
```

Replace it with:

```text
enumerate /sys/class/udc
require exactly one name equal to a600000.dwc3
allow every unrelated valid name
newfstatat(target, AT_SYMLINK_NOFOLLOW) must report symlink
readlinkat(target) basename must equal a600000.dwc3
```

`ENOENT` and missing exact membership remain `-ENODEV` so the bounded poll may
continue. Malformed dirents, close/read failures, non-symlink targets, duplicate
exact membership, and wrong resolved identity fail closed.

## Dedicated Dwell

The P2.57 global deadline remains unchanged for all earlier gates.

Immediately after the DWC3 gate succeeds and `completed` advances to the UDC
gate index:

1. reset `deadline` from `CLOCK_MONOTONIC`;
2. add exactly five seconds with overflow checking; and
3. clear `post_grace_drain`.

The existing 100 ms maximum poll cadence and prior-gate regression checks stay
active. This grants a fresh dwell only once, at the one source-proven async
boundary. It does not create a generic per-gate timeout framework.

## Versioning And Build Boundary

P2.58A is a new source-contract ID and run-ID domain. It reuses the P2.57 E2
record profile and decoder because stages, items, generations, outcomes, and
details are unchanged.

The generator must prove:

```text
plan(P2.58A)       == plan(P2.57)
checkpoint(P2.58A) == checkpoint(P2.57)
kernel patch(P2.58A) == kernel patch(P2.57)
runtime(P2.58A)    != runtime(P2.57)
```

Consequently no Full-LTO kernel build is required for this unit. A later
candidate may reuse the already verified P2.57 Image only after the linked
audit proves exact Image identity and the newly built userspace is reproducible.
Boot repacking, manifest creation, D0, F1 approval, and live work remain
separate later units.

## Semantic Fixtures

Required cases:

| Case | Entries | Target metadata | Expected |
|---|---|---|---|
| target absent | `dummy_udc.0` | absent | fail |
| real only | `a600000.dwc3` | exact symlink | pass |
| known-good FYG8 | real + dummy | exact symlink | pass |
| unrelated peer | real + foreign | exact symlink | pass |
| wrong target | real + dummy | symlink basename differs | fail |
| wrong type | real + dummy | not a symlink | fail |
| duplicate model input | real twice | exact symlink | fail |

Mutation validation must show that removing the peer case, changing its
expected result, changing the target name, or restoring global singleton
cardinality is rejected.

## Safety Boundary

P2.58A performs only existing mounts, exact module loading, and bounded sysfs
reads. It adds no module, sysfs/configfs write, role force, gadget binding,
network transport, reboot, partition access, Odin invocation, or device
authority.

## Exit Criteria

H0 implementation is complete when:

- the canonical topology oracle is machine-readable and validated;
- every semantic fixture passes and required mutations fail;
- two source generations and two userspace builds are byte-identical;
- the linked static AArch64 runtime passes;
- plan, checkpoint, and kernel patch are byte-identical to P2.57;
- no candidate or device action occurred; and
- focused and historical regression tests pass.
