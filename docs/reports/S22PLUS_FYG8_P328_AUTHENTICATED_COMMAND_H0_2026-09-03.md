# S22+ FYG8 P3.28 authenticated bounded-command H0

Date: 2026-09-03 KST

Target: `SM-S906N / g0q / S906NKSS7FYG8`

Tier: H0 only

Device contact: none

Independent review: `PASS_GO_P328_H0`

## Outcome

P3.28 is ready for one fresh Process-v2 preparation. It retains the P3.27
CDC-ACM lane and replaces unauthenticated fixed-command framing with an
authenticated, bounded, non-PTY command session. The live F1 proof still sends
only three fixed read-only BusyBox commands. This H0 result creates no standing
shell, resident service, connected preparation, approval, or F1 authority.

The source unit is commit `c13b6fb4f4`.

## Authentication and bounds

- Protocol: `S328` version 1.
- Authentication: HMAC-SHA256 over domain, exact run ID, fresh device nonce,
  sequence and exact command bytes.
- Nonce: exact 32-byte nonzero `getrandom` result; failure stops before child
  execution.
- Session: authenticated open/ready, at most 16 signed commands, signed close
  and done.
- Runtime command grammar: printable ASCII, no NUL/CR/LF, at most 1,023 bytes.
- F1 proof commands: exactly BusyBox `id`, BusyBox `uname -a`, and a run-bound
  BusyBox `echo`.
- Execution: no PTY, stdin `/dev/null`, 15-second command timeout, 128 KiB
  output bound, and bounded cleanup of the original child process group.

The symmetric 32-byte key is a fixed private input with mode `0400`, link count
one and SHA-256
`7eb6a32ca96daa9cd125b2798834f45515265a76d653ae719091d98f0a1f515b`.
Only its size and digest are published. The key is embedded in the private
candidate, so possession or extraction of that candidate implies possession of
the key. This is command-origin authentication for the experiment, not
hardware-backed secrecy.

## Candidate identities

Fresh binary run ID:
`c328f1e0a90b5e6d7c8a9b0c1d2e3f2b`.

Final host build:
`stock-candidate-build-v1-20260902-04`.

- builder result: 44,823 bytes, SHA-256
  `9901493f13e5a568f634710b353e9f557019c8ed43435b5130af68fe8c2fd286`;
- candidate A/B AP: 28,631,081 bytes, SHA-256
  `4ff89343a35a3bd0081ac8ed09ef0a872921b2ace5e9be266ce0c4d5a2bffbdb`;
- boot image: 100,663,296 bytes, SHA-256
  `49b8a1b15f0f5c758b4326e169e2596f72d9a712cf9e786561450f347a844ab3`;
- Image: 41,490,944 bytes, SHA-256
  `bc6ae05ea6ec36c1baf1807b6b52d434528b4eae2d25d1c95b7518db14f6af7a`;
- `/init`: 82,032 bytes, SHA-256
  `8cb723aa8171b9dafa60a6d0cf390d0e2e098761712c54cc20cb944a09a90086`;
- exact Magisk rollback: 23,367,721 bytes, SHA-256
  `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`.

The candidate AP has exactly one `boot.img.lz4` member. A and B are
byte-identical. The private key occurs exactly once in each materialized
`/init`; its bytes do not occur in the public tree.

## Process-v2 closure

P3.28 has distinct evidence, core and live dispatch. It reuses the proved P3.27
raw-first CDC lane, the exact P3.24 Type-C continuity checks, boot-only transfer,
mandatory rollback and final rooted-health choreography. A wrong or missing key
stops a fresh run before candidate intent. After a candidate effect, recovery
uses the retained key identity and never requires the secret to reach rollback.

The ordinary durable record bound remains 32 KiB. Only canonical
`live-result.json` publication has a dedicated 64 KiB cap. This removes the
repeated post-closure publisher failure seen in P3.23 through P3.27 without
loosening journals, state, receipts, or other records.

Published H0 identities:

- candidate-static: 25,741 bytes, SHA-256
  `73a8802a191b9ffe2ef6e790978eeb6fe5a8fd65953492affef27409f01d486a`;
- run manifest: 1,019 bytes, SHA-256
  `e8ab04c9840e5dcaceaad37bb16995ee6c2096161c61f85c7ab46819f4e3c957`;
- static result: 1,936 bytes, SHA-256
  `19a84c6be3091d0dc345ae150a40025691defd296a160ffd013a4bfd896c4647`;
- ready manifest: 4,959 bytes, SHA-256
  `8720216dae8b03c4c905250607225f9a845fb7c09d5407ac6f3667bca4e3636e`.

## Validation

- P3.28 focused tests: 42/42 pass.
- Common evidence/core/live plus P3.27 regression: 136/136 pass.
- Candidate builder, candidate-static and noncreating preparation audits: pass.
- Raw-first CLI audit: pass; private receipt 23,772 bytes, SHA-256
  `e8555a1f1900609ff00eb28cedeadbb65adddb6987021a698fccc40e08b92aea`.
- Raw-first P3.26/P3.28 mutation contracts: pass.
- Python byte compilation, diff check and repository boundary check: pass.

The full negative-census test module was not made a new readiness gate: it
repeats the same approximately 1,700-file census for every mutation. The real
CLI audit and the focused P3.26/P3.28 mutations are the bounded acceptance set.

## Next bounded unit

Run one fresh connected D0 preparation into a campaign-visible P3.28 run
directory. If it prepares cleanly, obtain one fresh attended F1 approval and
run the ordinary candidate-observe-rollback-final-health sequence. No new
protocol feature, resident design, or extra qualification ladder belongs
between H0 ready and that preparation. P3.29 remains a separate post-P3.28
resident-lane design and gains no authority from this result.
