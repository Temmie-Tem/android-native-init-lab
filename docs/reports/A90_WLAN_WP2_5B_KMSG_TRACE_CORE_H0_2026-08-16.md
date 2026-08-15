# A90 WP2-5b.1 kernel-log trace core H0

Date: 2026-08-16
Target: operator-owned Samsung Galaxy A90 5G only
Tier: H0 source, framing, parser, and state-machine implementation
Device, `/dev`, USB, network, live command, or other-target evidence: none
Excluded contact: one accidental S22+ public-source excerpt read; not used
Disposition: trace core complete H0; runtime observer and execution remain absent

## Result

WP2-5b.1 now has one generated binary framing contract, one C encoder core, one
raw Python consumer, one exact WP2-4 result binder, and one no-replay journal
prefix validator. This closes neither the full
`WP2_5B_STREAMING_KMSG_OBSERVER_ABSENT` gate nor any dependency gate. The C
core cannot open `/dev/kmsg`, poll, create a journal, or dispatch an effect.
The Python consumer cannot contact a target and always emits
`generationPromotionEligible=false` with H0 authority fields.
The permanent `WP2_5B_KMSG_STREAM_COMPLETENESS` invariant remains unchanged.

The implemented artifacts are:

- `workspace/public/src/scripts/revalidation/a90_wp2_5b_kmsg_trace_v1.py`;
- generated
  `docs/security/hardening/a90-wlan-vendor-property-ablation-2026-08-15/schema/a90-wp2-5b-kmsg-trace-v1.json`;
- generated
  `workspace/public/src/native-init/helpers/a90_wp2_5b_kmsg_contract.h`;
- `workspace/public/src/native-init/helpers/a90_wp2_5b_kmsg_stream.c`;
- `tests/test_a90_wp2_5b_kmsg_trace_v1.py`.

## Exact raw trace

The stream begins with one fixed magic/version header. It then contains
exactly one `ARM` frame, zero or more `RECORD` frames, an optional terminal
`FAULT`, and exactly one final `END` frame. Every frame uses one big-endian
fixed header. `ARM` binds the run, qualification, observer binary, generated
contract digest, and separately qualified record/byte caps. `END` binds the
driver-init epoch, parent-selected close binding, actual record/count totals,
and first/last sequence.

Each `RECORD` payload is exactly one successful `/dev/kmsg` read of 1 through
8192 bytes. Both C and Python reject noncanonical decimal fields, malformed
priority/sequence/timestamp/continuation headers, incomplete bodies, invalid
dictionary-line framing, oversized records, sequence gaps, duplicates,
regressions, wraparound, and cap exhaustion. Priority is source-bounded to
`0..2047` by the `u8` facility and three-bit level. Message and dictionary text
must use the selected kernel's exact lowercase `\xHH` escaping for a raw
backslash, nonprintable byte, or byte at least `0x7f`; raw backslashes,
unnecessary escapes, and an empty first dictionary line are invalid. The
Python consumer additionally rejects bad magic/version/reserved values,
truncation, unknown/duplicate/order-violating frames, trailing bytes, ARM/END
drift, or any `FAULT` as `NO_PROOF_OBSERVER`.

The C core reports format, sequence, count-cap, and byte-cap failures through
a typed `FAULT` frame. It does not claim that these are the only possible
runtime faults: the future owner must translate every `EPIPE`, `POLLERR`,
`EINVAL`, read/poll error, boundary failure, or final-drain failure into the
same fail-closed channel. A callback write failure leaves a truncated stream,
which the consumer also rejects.

## MAC signatures

The FALSE proof remains the exact kernel-facility error record with body
`WLAN MAC address is not set, type 0`, continuation `-`, no dictionary, exact
count one, type-1 exact count zero, and the bound exact-driver `wlan0` result.

The TRUE signature is deliberately not whole-body equality. The selected
`hdd_err` expands through `QDF_TRACE_ERROR`, `FL()`, and
`qdf_trace_msg_cmn()`, which prepend dynamic WLAN/PID/module/function/source-
line text before the source-unique literal. The consumer therefore requires a
kernel-facility error record, continuation `-`, no dictionary, and an exact
final suffix `getting MAC address from platform driver failed`, counted once.
This fixes an overstrict whole-body interpretation without weakening the
source-unique literal or accepting a userspace `/dev/kmsg` injection, whose
facility is forced away from kernel facility zero.

## Bound consumer and no-replay state

The consumer first invokes the pinned WP2-4 terminal validator. It then binds
the WP2-4 qualification projection to the raw-trace `ARM`, binds the driver
epoch and close receipt to `END`, and re-derives the MAC classification from
the exact raw records. The separate post-effect canonical driver-outcome
receipt binds the same run, boot, driver-init epoch, WLAN outcome,
driver-identity receipt hash, and interface-outcome receipt hash; its digest is
computed only after the outcome exists and is the exact journal payload.
Those two subordinate receipt producers remain runtime work and are not
implemented by this H0 core. A caller-supplied combined result is accepted
only when it is byte-for-byte equivalent under strict JSON types to the
consumer's re-derived result. Python `True` is never accepted for integer `1`.

The H0 journal vocabulary is the sole ordered prefix:

```text
OBSERVER_ARMED
EFFECT_INTENT
EFFECT_DISPATCHED
DRIVER_OUTCOME_BOUND
CAPTURE_CLOSED
TERMINAL
```

Every record binds the exact run and previous canonical-record digest. The
payloads bind, in order, the ARM receipt, proof subject, exact effect command,
driver-outcome receipt, complete raw-trace digest, and canonical WP2-4 result
digest. At and after `EFFECT_INTENT`, every incomplete prefix is
`OBSERVE_CLEANUP_RECOVERY_ONLY`; `effectReplayAllowed` is always false. This
validator intentionally returns no dispatch permission even before intent.
The durable atomic no-replace writer is not implemented by this unit.

Experiment proof, device safety, and workflow remain separate axes. A valid
MAC observation does not turn recovery uncertainty into health. A complete,
valid WP2-4 health result may remain `RESIDENT_HEALTHY` when only the kmsg
signature is missing, but a missing terminal journal or invalid driver-outcome
binding closes safety as `RECOVERY_REQUIRED` and workflow as
`RECOVERY_PARKED`. This H0 consumer never makes a generation promotable.

## Validation

The focused corpus covers canonical generation, pinned-source drift, raw
record grammar, every frame boundary, loss/fault handling, sequence
gap/duplicate/regression/wrap, record and total-trace caps, exact bindings, all
journal prefixes, chain/order/payload/type forgery, driver-outcome receipt
laundering, FALSE and TRUE signatures, missing evidence, forged safety and
combined results, arbitrary binary parser inputs, a native host C fixture,
explicit C fault fixtures, and AArch64 cross-compilation. The exact final
focused result was 156/156 PASS. Independent review returned
`PASS_H0_DOCUMENTATION_BOUNDARY`, with HIGH 0, MEDIUM 0, and LOW 0, against
the start/end-identical pre-receipt implementation closure `cf9150fe6692de53a191f150177865ebae10437c2103cb1abcfce1cc550357f9 /33`
(1,740,146 bytes). That review also completed 6,858 Python/C parser
differential inputs with zero mismatch and 1,126 malformed-container/type
validator inputs with zero exception. Generator checks, Python compilation,
host and AArch64 `-Wall -Wextra -Werror` builds, AArch64 file inspection, and
scoped diff checking passed. This paragraph is a receipt-only delta and is
separately rehashed before commit. No PASS from this report grants live
authority.

## What remains before any live unit

The next unit must integrate, without relaxing this contract:

1. exact no-symlink `/dev/kmsg` char-device identity and
   `O_RDONLY|O_NONBLOCK|O_CLOEXEC` plus `SEEK_END`;
2. a dedicated continuously draining owner armed before durable effect intent
   and before the selected driver-init epoch;
3. complete translation of `EPIPE`, `POLLERR`, `EINVAL`, read/poll errors,
   end-boundary failures, and final-drain uncertainty into durable evidence;
4. an exact private atomic no-replace trace/journal writer, strict raw
   canonical parser rejecting duplicate keys or noncanonical bytes, fsync,
   and crash-prefix reconciliation;
5. measured scheduling, record/byte, session, and ordinal budgets from a
   corrected healthy baseline and operator acceptance;
6. exact runtime integration hashes, hostile execution tests, independent
   execution review, recovery binding, and separate fresh authority.

Until those exist, the temporary gate remains open and WP2-5b cannot consume a
device ordinal.

## Authority

This work is H0 only. It grants no candidate identity, D0, D1, F1, live
execution, observer installation, property provisioning, handoff, UFS
mutation, recovery action, generation promotion, or device authority. No A90,
S22+, or S20+ device was contacted. The one accidental S22+ public-source
excerpt read disclosed above was excluded from every design claim, source pin,
test, and closure; no other-target evidence was used.
