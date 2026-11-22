# S20+ G986N UniLoader physical preparation

Target `SM-G986N / y2q / y2qksx / G986NKSS8IYC2`. The host-verified
candidate and exact original Magisk rollback pair are ready for review.
Live preparation stopped before target selection or mode transition.
The first physical proof remains Magisk Android through UniLoader,
with the fresh FDT marker and a proved original-boot return.
[UniLoader H0 build and QEMU handoff](S20PLUS_G986N_UNILOADER_ANDROID_H0_2026-11-22.md)

## Artifacts and observer

The [H0 preparer](../../workspace/public/src/mainline/s20plus_y2q_h0/prepare_uniloader_android.py)
revalidated the loader build and VM receipt, checked the marker inside
the candidate Image, and used the repository's pinned boot AP tooling.
The deterministic repackage produced the same candidate bytes twice.
Each AP has valid TAR/MD5 structure and one regular `boot.img.lz4` member.
Each member was decompressed and compared to its exact expected 64 MiB
boot digest. The host Odin4 binary also matched its existing pin.

| Role | AP bytes | AP SHA-256 | Decoded boot SHA-256 |
| --- | ---: | --- | --- |
| UniLoader candidate | 25,845,801 | `a7a0b09633043bbdac869b3c416fa4f4f01574499602e7848eeb977ec3e59003` | `36f95c3a8cbd07b6f928e2521a52923580dee91a86fe0cb25f1086b2846a9b09` |
| Original resident Magisk rollback | 25,835,561 | `1b33d098ea34b0396330cedf2e40c508704f1ba035b1f81e80a8526a637f1be2` | `d67d0af219d40d29f9e4d34da873e7aa33577d56fab68e2beccfe707418f7efc` |

The pair receipt is `artifact-pair.json` under
`workspace/private/outputs/s20plus-y2q-uniloader-h0-20261122.sgJEum/physical-prep-2/`.
It references the retained original Magisk AP and records the candidate
marker and read-script digests.

The [observation leaf](../../workspace/public/src/mainline/s20plus_y2q_h0/uniloader_android_observation.py)
defines one non-PTY read of the fixed FDT property, with a boot ID in
the same capture. The candidate's property is exactly 64 lowercase
hex bytes and one NUL. The host parser distinguishes a matching property,
an absent property, a different property and an unavailable read. It
joins the capture to validated Magisk Android health on both sides
using exact serial, topology and fresh boot identity. The future owner
must bind the capture to its journal and validate producer status,
including timeout and truncation, before interpretation.

Six focused tests passed, including raw NUL preservation, absent versus
unavailable, and rejection of changed or stale boot identity. The
actual property from the retained QEMU FDT also passed through the
bounded shell fixture and parser. These are host-only observer results.

## Current connected state

- The requested fresh Root-Health D0 made one ADB inventory. It saw
  one plausible row that did not satisfy the normal Android selector.
  It sent zero selected-target or root commands. The private failure
  receipt SHA-256 is
  `d475bdfad42ebbf1e78280bbbf1ec7fa11d7b7dd0b68c6dfc292792971d0e066`.
  The operator then identified the device as booted into TWRP.
- The retained-T2 baseline observer stopped in host validation
  with `raw_capture identity differs`, before its guard allocation
  and ADB inventory. T2 expects the original 25,006-byte capture helper
  at SHA-256 `410e260129c0c50dca29b008dc7cf1051ee007816ab18bea76aeae62505ca0e4`.
  Current bytes are 26,759 at
  `5a177d6bbe08cdd2c66f867c67a2a4093589b303d4b5b07f1e33d484f17498dc`.
  The expected bytes were rederived from Git commit `c41fd1ddf7`.
  Commits `c22f6138d8` and `0e3958b19f` changed that shared source.
  The dormant shared TWRP F1 runtime also rejects the same capture pin.
  The historical Android-first B0 owner has both capture and transport
  pin drift, in addition to its different candidate and proof contract.
- Device mode changes, partition operations, transfers and commands
  selected to S20+, S22+, A90 or any other device were zero.

## Proposed live sequence

1. Independently review target-local dependency binding and the exact
   UniLoader owner. Keep historical T2 evidence and S22+ runtime source
   identities intact. With the reviewed binding, qualify the currently
   running retained T2, prove physical Download fallback, and bind an
   attended finite approval to the candidate and original Magisk AP.
2. Transfer the candidate once. Prove a fresh, exact healthy Magisk
   Android boot and the matching FDT property from that same boot.
   Marker failure leaves the experiment unproved while the owner
   continues its independently authorized original-boot recovery path.
3. Restore the exact resident Magisk AP once, including after a
   successful experiment. Use the journaled Download route with
   physical fallback if the candidate cannot provide a qualified
   transport. Close with a proved boot transfer and fresh rooted
   Android health, checking the candidate marker's absence on that
   returned boot. Uncertain control or transfer retains its original
   owner and never replays.

The existing TWRP owner stops at recovery health, while this Android
compatibility trial requires Android health after rollback. The
candidate and marker helper are ready for the new owner's review.
The H0 pair carries no connected preparation or transfer authority.
