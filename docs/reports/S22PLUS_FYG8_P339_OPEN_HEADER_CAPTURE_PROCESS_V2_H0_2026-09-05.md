# S22+ FYG8 P3.39 rejected-OPEN header capture Process-v2 H0

Date: 2026-09-05
Target: `SM-S906N / g0q / S906NKSS7FYG8`
Tier: H0 only
Independent review: `PASS_GO_P339_H0`

## Result

P3.39 is the proportional successor to consumed P3.38. It keeps the successful
authenticated resident path, three fixed commands, session/reconnect bounds,
300-second observation, boot-only transfer, exact rollback and final-health
choreography unchanged.

Stage-3 diagnostic code `1` now means base header grammar rejection and new
code `4` means a grammar-valid OPEN was rejected by type, sequence, exact
length or run-ID validation. Only those two branches best-effort emit stages
4 through 7, carrying the rejected 16-byte header as four little-endian words
in the existing type-`0x86`/8-byte diagnostic frame. Partial capture remains
no-proof and the original error is returned. There is no retry, resync, drain,
wait, new handshake, frame type, payload width, command or D0/D1 wrapper.

## Exact host closure

- Run ID: `c339f1e0a90b5e6d7c8a9b0c1d2e3f1b`
- Builder result: `64362B/990f94cff5e28bc8360ede119eaa962a19dd1e75647489b9d1580dcf7f2bd338`
- Candidate AP A/B: `28631081B/80830eed6818528577e3dd5d68af79743b55a014b1dd4e2c8a3c5f54711b47d3`
- `/init`: `82624B/9818681f7c9da93be55bdd194ce32075662ef22b5e7ddf1a3f3d490c0686a8e6`
- Image: `41490944B/7c73b3803d67eec03968ebaa45c51d7f757853c4edefa21845c48a8455465a3e`
- Candidate-static: `40429B/5e27fdd7545890ddfe28f520728981a2f0b6bee5509bdbea66f660f7628b2080`
- Ready manifest (`ready_2`): `11056B/80d1a1a6da721108e0bd5d911f23cfd155cff9c1b6075d4dd952411b24c910bf`
- Exact rollback AP: `23367721B/d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`

Candidate A and B are byte-identical and contain only `boot.img.lz4`.
P3.38 and older run/AP identities are rejected. The AArch64 static `/init`
contains the fresh P3.39 identity.

## Proportional baseline path

Fresh P3.39 D0 may admit only the retained P3.38 rollback raw
`2097136B/321b03b24c488aa86f9cd2809dfdfdd2fa28fc8f5905183bbfe510cb1d58ab23`.
It must contain the P3.38 ID once at offset `1658754`, no P3.39 ID, and reopen
as the fixed P3.38 no-proof predecessor classification. Any drift stops; only
the existing attended D1 baseline fallback may precede a new D0. No new
baseline wrapper or permanent gate was added.

## Validation and boundary

- P3.39 focused tests: 23/23 passed after ready publication.
- Common evidence/core/live tests: 131/131 passed.
- P3.38 focused regressions: 21/21 passed.
- Builder, candidate-static and prepare audit-only checks passed.
- The raw-first boundary audit passed over 1,891 Python sources; private receipt
  is `54376B/015fda50204bc21d18fdef01268cecddf8c5acb8dad98ee0acde1a80ab350556`.
- Python compilation and `git diff --check` passed.

This result is host-only. It grants no D0/D1, F1, replay or recovery authority.
P3.38 remains consumed. A live P3.39 campaign still requires a fresh exact
connected preparation, attended one-use F1 approval, mandatory rollback and
healthy exact-target return.

`ready_1`/promotion `-01` are retained as an unused blocked predecessor: their
host-only ready-bundle verification exposed a P3.39 family-registration
omission before device contact. The three missing dispatch memberships were added and
independently reviewed as `PASS_GO_P339_LIVE_MAPPING_REPAIR_H0`; `ready_2` is
the only current preparation input.
