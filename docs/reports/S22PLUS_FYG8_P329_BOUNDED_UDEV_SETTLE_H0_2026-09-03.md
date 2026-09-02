# S22+ FYG8 P3.29 bounded udev-settle H0

Date: 2026-09-03 KST

Target: `SM-S906N / g0q / S906NKSS7FYG8`

Tier: H0 only

Device contact: none

Independent review: `PASS_GO_P329_H0`

## Outcome

P3.29 is ready for one fresh Process-v2 connected preparation. It keeps the
P3.28 authenticated protocol, private key, BusyBox payload, exact CDC-ACM lane,
two-property ModemManager guard, boot-only transfer, rollback, and final-health
sequence. Its only live acquisition change is a bounded wait for udev to finish
publishing both guard properties on the already selected exact tty.

This result creates no connected preparation, approval, F1 authority, resident
service, interactive PTY, or standing shell. P3.28 remains consumed and cannot
be replayed.

Implementation commits are `956cd14c8b` and the receipt-reopen repair
`029db236cb`.

## Proportional repair

The retained P3.28 evidence showed that the first tty-property read happened
about 15.8 ms before udev published both required ignore flags. P3.29 therefore
adds only these bounds:

- settle for at most 500 ms;
- poll no faster than every 25 ms;
- require both `ID_MM_DEVICE_IGNORE=1` and `ID_MM_PORT_IGNORE=1` together;
- recheck the exact tty class node, character-device major/minor, USB identity,
  approved `usb:3-1.3` topology, and guard health on every poll;
- stop immediately on identity or guard drift;
- perform no parent/interface fallback, selector widening, tty-open retry, or
  protocol retry.

Stable absence becomes `guard-property-timeout`. The successful settle proceeds
to the unchanged P3.28 authenticated exchange exactly once.

## Candidate identities

Fresh binary run ID:
`c329f1e0a90b5e6d7c8a9b0c1d2e3f1b`.

Final host build:
`stock-candidate-build-v1-20260903-01`.

- builder result: 45,150 bytes, SHA-256
  `d8475c76d7fe31fa52fc78ed6f770eae73bd24520bf3ff4ab8b696a981503973`;
- candidate A/B AP: 28,631,081 bytes, SHA-256
  `7a83b7c32e52f13fb88ec3cc6d81671baf70f13c343f2e02b03a6d712ab494bf`;
- boot image: 100,663,296 bytes, SHA-256
  `ff5b61292f2a9c4cdefd6e1991eccef6c77cc60e9a6aec0b72fc60ff1321a61f`;
- Image: 41,490,944 bytes, SHA-256
  `6fc2e5c0b299c740b21c66ff0185b6e8ef4764e88e4821d0e3cd18ee37c5361a`;
- `/init`: 82,032 bytes, SHA-256
  `245a65095da1a615a727ee92edfd3906b7d20096c4a21cc25c73e683c6f7a1fd`;
- exact Magisk rollback: 23,367,721 bytes, SHA-256
  `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`.

The candidate AP has exactly one `boot.img.lz4` member. A and B are
byte-identical and differ from the consumed P3.28 AP. The P3.28 `S328` wire
magic, HMAC domains, `P328-NONCE` compatibility label, and 32-byte private key
are intentionally retained; every frame still carries the fresh P3.29 run
identity. Only the key size and SHA-256 are published.

## Process-v2 closure

Published H0 identities:

- candidate-static: 25,843 bytes, SHA-256
  `2a64e338bc5ba45d0dede1d04c68692a79847151cf66f88de70f0b12b44119f8`;
- run manifest: 1,043 bytes, SHA-256
  `9fd82d8bd242a37a5cf5fd3da4d7900d1b4afc8b98b73e3fd7cfaf8e29247c6e`;
- static check: 1,960 bytes, SHA-256
  `f4caa675bc27ca68db6d51e54adf765bcc1773867cc34f250d88c1241ee23d93`;
- ready manifest: 5,205 bytes, SHA-256
  `22431a21ab52c6cd004628a6803670499ec9a455a0a02dcf6e118472e5dc8d5d`.

Independent review found one real success-path defect before publication: the
retained P3.29 receipt was reopened through the P3.28 validator because the
family predicate intentionally includes both generations. Commit `029db236cb`
now dispatches P3.29 first, removes an unreachable duplicate branch, and adds a
focused regression test. No candidate or ready binding was consumed by that
host-only defect.

## Validation

- Common evidence/core/live, P3.28 regression, and P3.29 suites: 154/154 pass.
- P3.29 focused H0 and settle/reopen tests: 12/12 pass.
- Candidate builder, candidate-static, and fresh noncreating preparation
  audits: pass.
- Raw-first CLI audit: pass; private receipt 24,759 bytes, SHA-256
  `5e200cd5a9fcc5fce10f5c8056b1f235ef6856e9f44914c30a4703fe9a3effe8`.
- Focused raw-first current-tree and mutation checks: 2/2 pass.
- Python byte compilation and diff check: pass.

No exhaustive per-mutation full-tree census was added. The real raw-first CLI,
the focused ordering mutations, and the actual receipt-reopen regression cover
the changed path without slowing every experiment with a duplicate gate.

## Next bounded unit

Run one fresh connected D0 preparation into a campaign-visible P3.29 run
directory. If it prepares cleanly, obtain one fresh attended F1 approval and
run the ordinary candidate-observe-rollback-final-health sequence. The F1
closure row must be derived from the retained journal/result only after the run
reaches `CAMPAIGN_CLOSED`.
