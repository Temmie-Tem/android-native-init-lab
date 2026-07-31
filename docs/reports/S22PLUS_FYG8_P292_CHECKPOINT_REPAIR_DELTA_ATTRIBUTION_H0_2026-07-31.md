# S22+ FYG8 P2.92 checkpoint repair delta attribution H0

Date: 2026-07-31 KST

Tier: H0

Status: `PASS_CHECKPOINT_REPAIR_DELTA_ATTRIBUTION`

## Result

The phase-2 generator applied the exact-active-slot and publication-errno
repair on top of the byte-exact P2.90 zero-delta baseline. Its declared and
actual changed-artifact sets are identical:

```text
candidate_patch
checkpoint_client
p290_checkpoint_header
p290_e3_runtime_include
runtime_wrapper
```

The remaining eight materialized artifacts are byte-identical to the retained
P2.90 baseline. Independent phase-2 runs A and B are byte-identical. No
comparison was weakened and no undeclared delta exists.

The phase-2 SoT descriptor has SHA256:

```text
68ad5fcb719f65ec3fbf1f18279b72ddbf428fdbbcffe0327ef40e76b07b14aa
```

The private durable delta result has SHA256:

```text
80f618f36a5795b3c81c8506e82052d937bd96fce67f8ad2957e2e0b4441553e
```

## Exact active-slot repair

The kernel state no longer retains only a reconstructive subset of the active
slot. It retains the exact ten-byte committed slot, including outcome, detail,
and commit CRC.

The seed path copies slot zero into exact active state only after the initial
record is stored and revalidated. Every successful later commit copies the
fully built successor slot into exact active state only after target commit
and verification. All active-record comparisons use these exact bytes.

The old partial fields and reconstructed
`PROGRESS/detail=0` active-slot builder are absent. Successor generation is
derived from the exact active slot. The retained ABI remains one 45-byte record
with two ten-byte alternating slots.

## Publication errno preservation

The userspace client records the exact returned negative errno and operation
class for each checkpoint `openat`, `write`, or `close` failure. The ranges are:

```text
openat: 0x4000 + errno
write:  0x5000 + errno
close:  0x6000 + errno
```

Linux errno `1..4095` round-trips exactly. The client and kernel validators
both accept these values only as failure outcomes.

When a checkpoint publication returns an error, the runtime first attempts an
operation-aware failure record using that exact encoded cause. If it commits,
the ordinary retained channel contains the cause before confirmed parking. If
the retained channel itself also fails, a dedicated volatile evidence
structure records triggering rc, operation, exact publication errno, and
fallback rc before the single raw channel-failure park. This does not claim
that a failed persistent channel can durably report its own total failure.
The next fault harness must verify both branches separately.

## Validation

The focused suite passes six tests:

- phase-2 SoT and all errno range round trips;
- exact five-artifact delta and eight-artifact non-delta;
- deterministic phase-2 A/B generation;
- rejection of one undeclared changed artifact;
- rejection of one missing declared change; and
- rejection of a B-only mutation.

The generated userspace links with the repository AArch64 toolchain under
`-Wall -Wextra -Werror` as a static ARM64 ELF. Two materializations produce the
same ELF SHA256:

```text
8e90891458eaf21d7b8ae62d110c8d23205a4d844172c681a562b367698fa999
```

The repaired candidate patch clean-applies to the pinned kernel tree and has
SHA256:

```text
65f30fd2843510bc4437b8155b512dff4b806d68f0f32f891024cb166fb7e72b
```

## Boundary

This unit proves delta attribution, syntax, clean application, and AArch64
compilability. It does not yet prove accept-to-resume closure, cumulative
107-position walking, the inherited detail-zero prefix, the retained P2.90
seed initial condition, corruption rejection, or fault-injected errno
observability. Those are the next H0 unit.

No successor intent was derived, no kernel or image was built, no device was
contacted, and no live authority exists.
