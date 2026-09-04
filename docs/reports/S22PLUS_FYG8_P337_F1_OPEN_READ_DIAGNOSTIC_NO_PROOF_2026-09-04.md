# S22+ FYG8 P3.37 F1 first-OPEN diagnostic result

Date: 2026-09-04 KST

Target: `SM-S906N / g0q / S906NKSS7FYG8`

Tier: attended F1, boot-only candidate with mandatory exact rollback

Formal result: `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`

Outcome:
`p337_authenticated_resident_open_read_diagnostic_unproved_rollback_verified`

## What succeeded

The exact P3.37 candidate and exact Magisk rollback each transferred once,
with no attempt 2. Candidate capture retained 97 bytes: the exact 49-byte
P3.37 native-PID1 banner, one CRC-valid stage-0/code-0 console-entry frame,
and one CRC-valid stage-3/code-`-71` first-OPEN-read diagnostic. The host
receipt also retained the exact 32-byte OPEN transmission and classified the
bounded session as `authenticated-session-error`.

The stage-3 value is the direct negative return from device-side
`p328_read_frame()`. Code `-71` is `EPROTO`, not the timeout path. Its source
can be an errno propagated while reading the header or body, the complete
header's magic/version/length rejection, or the body CRC rejection. It does
not identify which branch, nor prove which bytes the device actually consumed.

## What remains unproved

The candidate receipt is rejected (`accepted=false`). No `OPEN_PARSED`, RNG,
CHALLENGE, HMAC, READY, BusyBox command, clean DONE, resident listener, or
later-action lease was established. Session counts are 1 attempted, 0
successful, with 0 reconnects and 0 physical reopens. The result therefore
does not promote an authenticated session, command execution, resident shell,
interactive PTY, persistence, autonomous control, or a Max77705 causal claim.

Compared with P3.36, P3.37 closes the largest ambiguity: the first device
frame read did return, and it returned a protocol error. It does not yet
distinguish a propagated header/body read errno from header validation or
body CRC rejection.

## Rollback and closure

The first live command stopped after candidate observation while measuring
USB endpoint inventory. Recovery resumed the same durable journal, never
replayed the candidate, transferred the exact Magisk rollback once, and
retained healthy rooted FYG8 Android, expected boot/supporting-partition
identities, target topology continuity, and no Download endpoint.

The ordinary recovery then stopped host-side because P337 was omitted from
the final stock projection and its real rejected receipt carried one P337
proof-namespace key that the shared reopen allowlist omitted. Commit
`1f201ba1c4` repairs only those P337 projections; it does not loosen a success
criterion. Independently reviewed exact-run finalizer commit `d10be8e1fd`
rederived the consumed bundle, source closure and approval binding, reopened
only retained evidence, and appended the journal tail. It invoked no device,
ADB, USB revalidation, Odin, candidate, or rollback action.

Final identities:

- candidate AP: 28,631,081 bytes, SHA-256
  `0c1f6f231180f27376cf4b3e0ed8a84b7347cc2e5d066cf87db53d91cc239466`;
- rollback AP: 23,367,721 bytes, SHA-256
  `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`;
- candidate raw: 97 bytes, SHA-256
  `066a47804aa425c50497032549e8938dff413cf25969b10d55e15729293bc943`;
- candidate receipt: 7,406 bytes, SHA-256
  `8a938155c4d66067debfbf1895f9df78eefe03d624b8ac1694672aab94c7ca8c`;
- two byte-identical rollback reads: 2,097,136 bytes, SHA-256
  `64ac7a5b6666c4a21ce23effce2ec13015cdbdb985555300202ad46d8fe26a11`;
- final state: 18,129 bytes, SHA-256
  `72091518254d885091b94ddf8c95b7f6ef7327dc6f644ae15d6d530b108195e9`;
- final result: 21,075 bytes, SHA-256
  `391ea331e1dcef2812aa7c8bb471e6b127159b431a53a9575499001c32b0e07d`;
- journal: `CLOSED`, 19 records, terminal record SHA-256
  `fe48395218690171fc33747216069acf5ab7c8ff010c63e2e4e6c7c3a7fad060`;
- `recovery_required=false`.

P3.37 is consumed and never replayable.

## Proportional follow-up

Do not redesign the protocol or add a broad retry. First compare the exact
P3.35-success and P3.36/P3.37-failure paths from host OPEN construction through
the device's first `read_frame()`. If another candidate is needed, the minimal
new diagnostic is one bounded branch ordinal separating header read, header
validation, body read, and CRC rejection. H0 and captured-fixture tests should
qualify that single delta before another attended F1.
