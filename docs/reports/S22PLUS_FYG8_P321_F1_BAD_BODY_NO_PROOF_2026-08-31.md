# S22+ FYG8 P3.21 F1 bad-body no-proof closure

Date: 2026-08-31

Target: `SM-S906N` / `g0q` / `S906NKSS7FYG8`

Terminal verdict: `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`

Outcome: `p321_observer_no_proof_rollback_verified`

## Summary

P3.21 was transferred once and booted without an operator-observed boot loop. The
exact Magisk rollback was then transferred once, final rooted FYG8 health passed,
and the 19-record Process-v2 journal closed with `recovery_required=false`.
Neither candidate nor rollback was replayed.

The experiment did not produce an accepted P3.21 result. Two full-length final
`/proc/last_kmsg` reads were byte-identical and contained one exact P3.21 Carrier
family. Both slot CRCs were valid, but the newer slot was semantically invalid.
The strict result is therefore `NO_PROOF_OBSERVER`, not candidate success or
experiment failure.

## Preparation

The first connected prepare saw no exact ADB target and stopped before a complete
D0 result. A later fresh prepare retained one P3.19 family and published the
non-reusable typed baseline-rejection result. One separately approved normal
reboot then completed with a changed boot identity, unchanged target/topology,
healthy rooted FYG8 return, and zero Download/Odin/partition activity.

The final Process-v2 prepare used
`workspace/private/runs/device-action-f1-live-v2/p321-ready1-prepared-20260831-3`.
Its D0 result was 3,261 bytes with SHA-256
`854b78f65ce798a76be4fd8b63794a4becf82d7d019f9a15cdbd36c7e7b9fffe`.
It read 2,097,136 bytes to EOF with zero exact markers, zero family markers,
empty stderr, stable no-Download USB inventory, and no write or reboot.

The fresh approval binding was
`ec9f0081199372f8cedf6123f988d09e74cad1a28930b6ea7a453f6578b08a87`.
It bound the boot-only P3.21 AP
`770694d16123ea9a0ce28aded393fbf44e280794e5a94107c47952e904586514`
and exact rollback
`d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`.

## Live chronology

1. The exact P3.21 candidate transfer started and completed once.
2. Its Download usbfs node disappeared during enumeration-membership validation.
   This occurred outside the narrower birth-time-read departure repair and stopped
   the first invocation after the durable candidate result.
3. Journal recovery closed candidate observation without candidate replay. The
   operator confirmed normal candidate boot and no boot loop.
4. Recovery waited for attended physical Download entry. One wait ended without a
   rollback attempt; the later same-journal recovery bound the endpoint.
5. The exact rollback transfer started and completed once.
6. Android boot completion, stopped boot animation, root, boot/supporting-partition
   identities, and absence of Download mode passed. The journal closed.

## Retained P3.21 record

The two final reads were each 2,097,136 bytes and had identical SHA-256
`4dd963ccde3dd61e091e9e3601e5ae1865deba0c103fea09d1bf17af6a5dab8c`.
Their typed classification retained:

- exact P3.21 run ID and one Carrier family;
- valid Carrier header CRC;
- slot 0 valid at generation 92, stage `0x8f`, item index 4, outcome 0;
- slot 1 has a valid CRC and canonical padding at generation 93, stage `0x90`,
  item index 0, outcome 2, detail `0x6720`, but decodes as `bad-body` because
  that failure detail is outside the declared route for this position;
- fallback/progress only, no terminal success;
- `p320-stock-envelope-shape` integrity issue and contradiction count 1;
- zero accepted P3.21 stock results.

## Exact writer cause

The retained generation-92 position is `restart_deadline_ready`. The generated
P3.21 runtime then enters `p319_stock_publish()`, whose
`p319_stock_bypass_to_pair()` requires `g_checkpoint.generation == 105U` and
immediately calls `p290_fail_next(0x6720)` otherwise. It contains no progression
from 92 to 105. The failure writer therefore correctly commits the next A/B slot
with a valid CRC at generation 93, but writes the position-contradiction detail
into `restart_helper_dispatch`, where that detail is not legal. The decoder's
`bad-body` classification is consequently a semantic rejection, not torn media,
CRC damage, USB corruption, or a boot failure.

The earlier P3.13 implementation already contains the proportional repair shape:
reject terminal or generation greater than 105, then advance the bounded missing
positions until generation 105 before publishing positions 105 and 106. A future
successor may reuse that state transition, but P3.21 remains consumed and is never
replayed.

`COMPLETE` was not observed. The partial record proves only that a P3.21-bound
writer reached the retained progress structure. It does not prove the intended
terminal chain, USB attachment, MUX state, connector behavior, or candidate success.
The supplemental host USB sidecar remained `UNKNOWN` after the endpoint exception.

## Final evidence

- Candidate transfer result: 2,079 bytes,
  `308e9c3f65b8cc1d7dc9e51e73f10d133c318186ecb472af0ede9d3006d8a776`.
- Rollback transfer result: 2,030 bytes,
  `1416c0158ff9f9278394eb5a5aa7b84b1c39197f65e23f3b8b963c67db47ede3`.
- Final live result: 10,019 bytes,
  `d71d333513fe9fe48b2ee68e6418ea52b79161ad343b2b0554c1c0776af6d345`.
- Journal: 19 records, `CLOSED`.
- Candidate transfers: 1; rollback transfers: 1; replay: 0.
- Final health verified; `recovery_required=false`.

## Next bounded work

P3.21 is consumed and cannot be retried. H0 has isolated its publisher state
transition and repaired the separate post-transfer enumeration seam so that an
empty Odin list may accept only the exact single Download node retained by the
immediately preceding live receipt. Default enumeration, additions, replacements,
multiple removals, and an unbound removal remain fail-closed. Neither result grants
device authority; the next candidate requires new bytes and fresh preparation.
