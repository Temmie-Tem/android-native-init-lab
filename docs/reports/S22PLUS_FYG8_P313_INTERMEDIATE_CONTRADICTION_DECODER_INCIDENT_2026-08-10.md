# S22+ FYG8 P3.13 intermediate-contradiction decoder incident

Date: 2026-08-10 KST
Target: Samsung Galaxy S22+ FYG8 only
Classification: `HOST_CARRIER_SEMANTIC_AUTHORITY_FAILURE_AFTER_ROLLBACK`

## Device and recovery result

The distinct P3.13 boot-only candidate and exact rollback each transferred
exactly once. The candidate ACM observer timed out. The operator observed a
normal candidate boot without a loop and later confirmed the final Android
boot had no loop.

Rollback completed before a transient host endpoint-evidence failure. The
canonical recovery path resumed from durable rollback state without a second
candidate or rollback transfer. Rooted boot-completed FYG8 Android, the exact
boot and supporting-partition identities, absence of Download mode, and the
complete 19-record Process-v2 timeline passed. The journal is `CLOSED` and
`recovery_required=false`. Candidate replay is forbidden. A90 received no
command from this work.

## Retained device result

Two 2,097,136-byte retained reads were byte-identical and each contained one
Carrier-v2 family at the same offset. Header CRC, both slot CRCs, family count,
foreign count, and snapshot-edge integrity are clean.

The committed slots are:

1. generation 96, stage `0x90`, item 3, progress zero: completed
   `PARENT_SUSPENDED` at position ordinal 95;
2. generation 97, stage `0x90`, item 4, failure `0x6712`:
   `P313_DETAIL_CYCLE_EVENT_MULTIPLICITY` at position ordinal 96.

The runtime publishes position ordinal plus one as slot generation. Source
order places the failure after stop-helper return, child suspend, parent
suspend, UDC-binding revalidation, stop trace snapshot, and stop-side parsing,
but before creation or execution of the restart helper. In the non-final stop
parser, `0x6712` means at least one of the bounded functional event-pair counts
exceeded one. The detail does not identify which pair, so no narrower
controller or driver cause is claimed.

## Host decoder cause

The frozen P3.13 telemetry decoder imported the P3.12 Carrier model. P3.12
correctly knows the Carrier-v2 byte layout but its semantic validator predates
P3.13's `0x6701..0x673f` contradiction family. P3.13's own final-pair fixture
exercised only generations 106/107 and did not execute a terminal
contradiction at an intermediate generation.

Consequently the live evidence path verified the generation-97 slot CRC, then
rejected its semantic body and reported slot status `bad-body`. It fell back to
the valid generation-96 progress slot and persisted `E2_PROGRESS_OBSERVED`.
This was a semantic-authority failure, not a torn write or malformed device
record.

## Bounded post-live correction

The frozen P3.13 candidate, materialized sources, Image, ready manifest,
approval binding, journal, and live result remain unchanged. Three new H0-only
files provide a successor input without rewriting that history:

- `s22plus_fyg8_p313_postlive_carrier_model.py` preserves the Carrier-v2 byte
  ABI, inherits earlier progress semantics, and admits P3.13 contradictions at
  any valid position only with failure outcome;
- `s22plus_fyg8_p313_postlive_decoder.py` names and classifies an intermediate
  P3.13 contradiction without accepting it as telemetry success; and
- `test_s22plus_fyg8_p313_postlive_decoder.py` proves the frozen decoder's
  `[valid, bad-body]` failure and the corrected `[valid, valid]` result.

The focused regression passes strict JSON serialization and reports
`P313_OBSERVER_CONTRADICTION`, `cycle-event-multiplicity`, integrity clean,
foreign count zero, and no fallback for both retained reads. No device access,
transfer, reboot, or candidate replay is part of this correction.

Five focused regressions cover the historical fallback, corrected intermediate
failure, normal final pair, JSON-safe classification, and fail-closed rejection
of a contradiction detail paired with progress outcome. Python compilation,
the actual retained-byte reclassification, documentation tests, and scoped
diff checks pass. A changed-files-only independent re-review found no remaining
issue and confirmed that the frozen closure and all device/runner paths remain
unchanged.

## Successor boundary

Any successor must preserve the exact device result and may not treat P3.13 as
a clean digital refutation. Before another F1, host fixtures must round-trip a
P3.13 contradiction at an intermediate generation through the same Carrier
semantic authority used by the real evidence adapter. The next diagnostic
question is which stop-side event pair multiplied; restart/resume attribution
remains downstream and unmeasured.
