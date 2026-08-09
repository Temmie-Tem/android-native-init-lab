# S22+ FYG8 P3.11 observer incident

Date: 2026-08-09

Target: Samsung Galaxy S22+ FYG8 (`SM-S906N` / `g0q`)

Result: `NO_PROOF_OBSERVER`, final health `HEALTHY`

## Device result

The distinct P3.11 candidate and exact rollback each transferred once. The
operator observed a normal candidate boot without a loop. Two byte-identical,
integrity-clean retained reads contained generations 68/69 at stages
`0x7B`/`0x7C`; the terminal record was `0x6805`
(`early-profile-record-mismatch`). No 24-callsite clock tuple was published,
so the run proves neither a clock success nor a clock failure. Candidate replay
is forbidden.

Exact rollback completed. Rooted, boot-completed FYG8 Android, the expected
boot identity, supporting-partition identities, and absence of Download mode
all passed. The durable journal is `CLOSED` and `recovery_required=false`.

## Observer cause

The materialized runtime compared each event's kprobe profile-hit count to its
trace-record count for exact equality. The trace-kprobe implementation
increments `nhit` before the trace-enabled and soft-disable/recording path, so
profile hits cover a wider lifetime than trace records. Exact equality is not
a valid losslessness contract. The valid relation is `profile_hits >= records`,
alongside `nmissed == 0`, clean ring statistics, and complete semantic
entry/return or post-callsite tuples. A profile count below its record count
remains a contradiction.

## Host decoder incident

After rollback and both retained reads, the generic Process-v2 evidence path
selected Carrier-v1 semantics for the P3.11 Carrier-v2 record and then rejected
nested `bytes` during JSON persistence. No device effect was repeated. A
recovery-only adapter with SHA-256
`3c1b429ff4b81609345f8945e5d41cf0062c24305ab183bab010f877e3107b63`
prohibited Download mode and all transfers, reused only the two durable reads,
encoded byte payloads as deterministic hex, revalidated exact final health,
and closed the original journal.

## Why prior review did not prevent recurrence

Both failures crossed an authority seam that the final qualification did not
exercise. Review had already established that kprobe `nhit` increments before
the trace-recording decision, but the materialized P3.11 runtime and its
fixtures still encoded exact profile/record equality. The reviewed source fact
was not converted into an executable lower-bound invariant.

Carrier-v2 JSON safety had also been repaired after P3.10, but that repair was
limited to the P3.10 decoder. The shared evidence selector did not require a
new overlay decoder's carrier family, record size, and format version to equal
the source contract's retained-record ABI. P3.11 therefore reintroduced a
Carrier-v1 decoder on a Carrier-v2 source while its own internal checks still
agreed.

P3.12 closes both seams mechanically: materialized fixtures execute profile
excess and deficit, while a shared decoder/carrier cross-authority check rejects
P3.11's historical mismatch and requires every supported overlay decoder to be
JSON-serializable for the source carrier before live persistence. Its canonical
bundle rehearsal also requires the Process-v2 runner to select the exact P3.12
overlay source set and to bind the inherited P3.10 decoder override; an unknown
overlay cannot silently fall through to P3.01 semantics.

## Successor boundary

P3.12 is a userspace-only observer repair. It keeps the fixed P3.10 Image,
module plan, 24 linked callsites, trace descriptors, and Carrier-v2 layout. Its
host fixtures must accept profile excess, reject profile deficit, round-trip
the Carrier-v2 record through the real Process-v2 evidence adapter, and verify
all emitted details through every applicable publication gate. P3.12 requires
fresh qualification and a fresh live binding; P3.11 is never replayed.
