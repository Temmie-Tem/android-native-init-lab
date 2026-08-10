# S22+ FYG8 P3.14 live-profile snapshot incident

Date: 2026-08-10 KST

Target: Samsung Galaxy S22+ FYG8 (`SM-S906N` / `g0q`) only

Classification: `INTERMEDIATE_PROFILE_SNAPSHOT_ORDERING_FAILURE`

## Device and recovery result

The distinct P3.14 boot-only candidate and exact Magisk rollback each
transferred exactly once. The operator observed a normal candidate boot
without a loop. The candidate ACM observer received zero bytes and closed as
an endpoint timeout after its bounded 300-second window.

Exact rollback completed once. Rooted, boot-completed FYG8 Android, the exact
boot and supporting-partition identities, stopped boot animation, and absence
of Download mode passed. The 19-record Process-v2 journal is `CLOSED`, final
health is `HEALTHY`, and `recovery_required=false`. Candidate replay is
forbidden. A90 received no command from this work.

## Retained device result

Two 2,097,136-byte retained reads were byte-identical. Header and slot CRCs,
family count, foreign count, delimiter integrity, and snapshot-edge integrity
were clean. The committed adjacent slots are:

1. generation 96, stage `0x90`, item 3, progress zero at the completed
   parent-suspended boundary; and
2. generation 97, stage `0x90`, item 4, failure `0x6705`,
   `profile-record-deficit`, while classifying the live stop snapshot.

This preserves the same bounded stop-side facts as the preceding unit: the
direct fence selected the cycle, the stop helper returned, the UDC binding
survived, and child plus parent reached suspended state. The runtime stopped
before constructing the restart helper. P3.14 therefore proves no restart,
resume, post-cycle QSCRATCH, state delta, connector, or pull-up conclusion.

## Observer cause

The actual materialized runtime calls:

```c
rc = p282_trace_read_snapshot(&cycle_control, 0);
if (rc == 0)
    rc = p314_parse_live_snapshot(
        &cycle_control, &stop_result, P314_PHASE_STOP);
```

For the cycle phase, `p282_trace_read_snapshot(..., 0)` reads the trace text
but deliberately does not read `kprobe_profile`. The trace control was
zero-initialized, so every `profile_hits[]` entry remains zero. The live parser
then unconditionally calls `p313_cycle_profile_relations()`, which returns
`0x6705` whenever any parsed record count is nonzero.

A host-only TU compiled from the actual materialized P3.14 parser reproduces
the live result with the exact clean 14-record stop fixture:

```text
rc=0x6705 records=14 profile0=0 record0=1
```

This is deterministic observer self-failure, not evidence of a kernel kprobe
profile deficit and not a USB or PM result. The valid profile lower-bound
check requires a profile snapshot. The existing final and partial close paths
already disable tracing, call `p282_trace_read_snapshot(..., 1)`, and only
then compare profile hits to records.

## Why qualification missed it

The P3.14 runtime fixture extracted and executed `p313_parse_cycle()` directly.
It validated the 14/41/49 record geometry, all 1,023 pair masks, return-value
domains, and overflow, but it did not extract or execute
`p314_parse_live_snapshot()`. Its reference to
`p313_cycle_profile_relations()` was compile-only. The value-by-position and
Process-v2 matrices began after a runtime detail had already been produced, so
they could validate `0x6705` as an allowed contradiction without proving that
the live snapshot had first populated profile counts.

The hazard closure therefore proved parser values and carrier placement but
not the actual intermediate snapshot call sequence. This is the same broad
class as earlier authority-seam incidents: an internally consistent fixture
tested a lower-level component while the materialized wrapper that supplied
its inputs remained unexecuted.

## Successor boundary

P3.14 is consumed and never replayable. A minimal successor remains
userspace-only while the fixed Image, kernel hooks, 25-event inventory,
61-module plan, Carrier layout, rollback, transfer, recovery, and guard remain
unchanged. It needs no Full-LTO under those exact inputs.

Before another device action, qualification must:

1. make every live stop and restart profile comparison follow a successful
   profile read, or defer that comparison to a proved close path that reads
   the profile after disabling tracing;
2. execute the actual materialized `p314_parse_live_snapshot()` with nonzero
   stop and restart records, accepting equal/excess profile counts and
   rejecting a deliberate deficit;
3. prove the two intermediate callsites use the selected profile-snapshot
   contract before the live parser;
4. retain the existing final/partial disable, profile, ring, cleanup, pair,
   capacity, carrier, and Process-v2 matrix checks; and
5. bind this incident closure into the real validator-before-packaging path.

No device evidence from P3.14 may be relabelled as a clean digital refutation.
