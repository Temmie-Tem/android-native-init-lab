# S22+ FYG8 P3.20 F1 mixed-run observer no-proof

Date: 2026-08-30 KST

Target: Samsung Galaxy S22+ `SM-S906N` / `g0q` / `S906NKSS7FYG8`

Run: `workspace/private/runs/device-action-f1-live-v2/`
`p320-ready1-prepared-20260830-1`

Status: **closed, exact rollback verified, no proof**

Formal verdict: **`NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`**

Formal outcome: **`p320_observer_no_proof_rollback_verified`**

This report records one consumed P3.20 F1 run and its recovery. It grants no
candidate replay, new F1 authority, USB claim, or causal claim. Device serial,
raw device content, and endpoint-private identity remain under
`workspace/private/`. A90 and S20+ files, authority, and devices were not used.

## 1. Safe terminal state

The exact P3.20 candidate and exact Magisk rollback each transferred once with
classification `odin_transfer_completed`. The candidate boot reached normal
Android without a boot loop according to the operator. The Process-v2 journal
has 19 records and is `CLOSED`; exact rollback, final rooted FYG8 health, and
rollback boot-ready passed. `recovery_required=false`.

The immutable `live-result.json` is 8,696 bytes, mode `0400`, SHA-256
`5e4f4d7fa2d833a4dc1c4d91869eb6251e39a55d0c800abf737b425acf6a8cb1`.
The candidate and rollback transfer receipts are respectively SHA-256
`cffe94a449465b6c5c03505baf4653a2cd417011605d1452b5e71d415e0cf645`
and `6aaaf32c52e6840c783b7f9d53f645caa24ced6bbb04d1950f0cff15328ca1a7`.
The candidate is consumed and must never be replayed.

## 2. Host endpoint-observer incident

After the candidate transfer completed, candidate observation raised
`OdinTransitionError: measured USB endpoint inventory failed`. The immediate
cause was a failed birth-time read of one enumerated candidate-era usbfs node.

Raw usbfs evidence separates this from a device boot failure. Inventory
sequences 7 and 8 each read the same node's birth time successfully three
times with identical 35-byte stdout and empty stderr. Sequence 9 enumerated the
node but its first birth read returned 1, produced no stdout, and reported
`ENOENT`. The node therefore disappeared between enumeration and measurement.
This is a host snapshot TOCTOU race at endpoint departure, not evidence of a
boot loop or USB hardware failure.

The execute invocation stopped rather than guessing. Recovery resumed only
from the durable journal, recorded `interrupted_candidate_no_proof`, accepted
no candidate replay, obtained a fresh exact rollback Download endpoint, and
completed rollback and final health.

## 3. Final observer result

The two final `/proc/last_kmsg` reads are byte-identical: each is 2,097,136
bytes with SHA-256
`ec7f699a1ce79b5c69b88adc4f46b51a7147e9406505f28020051885fb5682a1`.
The frozen P3.20 adapter reports:

- `P320_STOCK_WITNESS_BASE_SHAPE_FAILURE`;
- `NO_PROOF_OBSERVER`;
- `long_record_count=0`, `exact_record_count=0`, `foreign_count=1`;
- `integrity_issue=true`, `candidate_success=false`;
- `causal_result_allowed=false`, `mux_result_claimable=false`.

There is one complete 192-byte `S22E1L2|` record at offset 1,658,341. It is a
CRC-valid E2 Carrier using the consumed P3.19 run ID, with generation 0 in
slot 0 and an uncommitted slot 1. Its SHA-256 is
`f526d0460b187be29292ebec6f723ff967ed3c1181ce6c27ca1d1c833022a52e`.
It is not a P3.20 result.

The fresh D0 baseline, Process-v2 prepare baseline, and execution-time baseline
all contain zero `S22E1L2|`, zero P3.19 run-ID bytes, and zero P3.20 run-ID
bytes. The P3.19 generation-0 record appears only in the two identical final
reads. This proves it was absent from all three immediate pre-candidate
baselines; it does not by itself identify the exact instruction or instant
that created it.

## 4. Mixed-run artifact finding

The candidate artifact contains a directly observable kernel/userspace
identity mismatch:

- `s22plus_fyg8_p320_stock_candidate_build.py` sets the inherited userspace
  packager `RUN_ID` to P3.20 at line 703;
- the same builder copies the P3.19 `fixed-Image` unchanged at lines 769-770
  and packages it at lines 795-799;
- the fixed Image contains the ASCII kernel configuration run ID P3.19 once
  and no P3.20 configuration string;
- the generated `/init` contains the raw P3.20 run ID once and no raw P3.19
  run ID;
- the packaged `boot.img` therefore contains both identities: ASCII P3.19 in
  the fixed Image and raw P3.20 in `/init`.

The kernel Carrier initialization parses
`CONFIG_S22PLUS_FYG8_E1_RUN_ID_HEX`. Its request-write guard compares the
userspace request run ID with the Carrier header and returns `-EKEYREJECTED` on
mismatch (`s22plus_fyg8_p310_carrier_transform.py` lines 298-301 and 463-465).
The live generation-0 P3.19 Carrier is consistent with initialization followed
by no accepted P3.20 request.

The exact rejected syscall return was not retained as an independent raw
receipt. Consequently, the causal interpretation “P3.20 requests were rejected
by this guard” is strongly `SUPPORTED`, not promoted to a rewritten formal
result. The byte identities, baseline absence, P3.19 generation-0 Carrier,
mixed artifact, and guard behavior are directly proved.

## 5. Conclusion and next bounded unit

P3.20 answered the boot-safety question positively at the operator-observation
level: the candidate reached normal Android without a boot loop, rollback
completed, and final health is good. It did not answer the USB experiment.

Two independent defects blocked attribution:

1. the usbfs endpoint-departure race interrupted the original candidate
   observation;
2. the candidate combined a P3.19-configured kernel Carrier with a P3.20
   userspace request and P3.20-only decoder.

Do not replay P3.20. A successor must use one run ID across the kernel Image,
userspace request, Carrier decoder, and Process-v2 manifest, and its static
audit must inspect both the kernel configuration string and raw userspace
bytes. The usbfs observer should separately treat a node that vanishes during
an allowed departure snapshot as a bounded resnapshot condition, not silently
as proof of absence. Both repairs require host-only qualification and review
before any new live candidate.
