# S22+ FYG8 P3.25 tty guard-property repair H0

Date: 2026-09-01

Target: `SM-S906N` / `g0q` / `S906NKSS7FYG8`

Status: `PASS_GO_P325_PROCESS_V2_H0`; no P3.25 device action

## Narrow experimental change

P3.24 proved that the exact candidate enumerated as `04e8:6861`, `cdc_acm`,
and `ttyACM0` on the bound candidate lane `usb:3-1.3`. Its observer retained
zero bytes because the pre-open ModemManager check queried the resolved USB
interface `3-1.3:1.0`; the two required ignore properties were present on the
tty add event instead. P3.24 remains formally `NO_PROOF`, closed, consumed,
healthy after exact rollback, and never replayable.

P3.25 keeps the P3.24 lane binding, single exact candidate selector, transient
udev rule, both required ModemManager flags, P300 passive trace, observation
receipt taxonomy, mandatory rollback, and final-health choreography. During
the delegated read only, both existing guard property probes are redirected to
the selected `Endpoint.tty_class`. There is no parent/interface fallback,
one-flag acceptance, selector widening, retry, or extra device action.

Host fixtures prove the exact tty-only two-flag case opens once and accepts the
expected banner. Missing either flag blocks before open with zero retained
bytes; wrong identity and character-device major/minor drift remain fail
closed. Both pre-open and post-read probes use the tty class node. The inherited
post-read property-loss behavior remains unchanged: an already captured exact
banner is still classified by the base observer rather than rewritten by the
adapter.

## Fresh artifact and ready binding

P3.25 uses fresh run identity
`c325f1e0a90b5e6d7c8a9b0c1d2e3f4b`; no P3.24 candidate byte or approval is
reused.

- Builder result `-02`: 40,980 bytes, SHA-256
  `49b408fbf3f3095e1c3f4887a29c8d47e6f209e471962ed5c5e823661bd95240`.
- Candidate AP A/B: 27,279,401 bytes, SHA-256
  `486fd1f2dcb8fbca9f31cb6bce438bb38945cf98e9bb9422f5d5301a7b0abdf4`.
- Image: 41,490,944 bytes, SHA-256
  `3b605c6bd60fb515c0015357e376dd7c1e33c4bbdb8c12905dff7d2749a26d92`.
- `/init`: 80,552 bytes, SHA-256
  `d3869368283730e8b92eb35e8af24c29d494b541595fb1de611172da1ffbde96`.
- Candidate-static `-02`: 23,312 bytes, SHA-256
  `bd3f14fae735f8254136e7d04174e1d92fd02c6aeed256ae19f2a9ee13c1addf`.
- Final ready manifest `ready_2`: 3,327 bytes, SHA-256
  `e98c3a14c11b69957333a15cae73cabfd6ec57fd2106fffddace467e3c044155`.
- Exact rollback remains 23,367,721 bytes, SHA-256
  `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`.

The A/B APs are byte-identical and contain only `boot.img.lz4`. Image
IKCONFIG/raw identity and `/init` join only the fresh P3.25 run; P3.19-P3.24
identities and the consumed P3.24 AP are rejected. Private promotion `-03`
contains exact mode-`0400`/single-link candidate-static, run-manifest, and
static-check records under a mode-`0700` directory. The earlier private `-02`
promotion is retained as a stale H0 predecessor; its untracked public
`ready_1` draft was moved to trash rather than overwritten.

## Preventing the P3.24 post-close publisher fault

P3.24 duplicated the complete retained Carrier projection inside
`candidate_arrival_proof`, growing the otherwise valid live state from 29,102
to 34,672 bytes and exceeding the shared 32 KiB record bound after `CLOSED`.
P3.25 retains the complete `p325_stock` evidence once in `final_evidence` and
sets only the duplicate `supplemental_carrier` field to `null`. It does not
raise the global record limit or discard primary arrival evidence.

A closed-state-shaped regression serializes within `core.MAX_RECORD`; restoring
the old duplicate shape exceeds that same bound. This removes a known host
reporting failure before live use without adding a device gate.

## Validation and authority

The host-only artifact/adapter/static set passes 23 focused tests. The final
ready suite passes 5 tests, including exact ready reopening and the compact
closed-state bound. Shared evidence/core/live regression passes 131 tests.
Python compilation, diff checks, builder/static audits, noncreating ready
rehearsal, published bundle verification, and exact promotion/publication modes
pass. No Full-LTO, new D1 rotation, separate baseline campaign, device contact,
ADB, USB action, `pkexec`, Odin, transfer, or flash was used to produce this
capability.

Independent hostile review rederived the fresh artifact identities, boot-only
A/B AP, exact rollback, P319-P324 rejection, actual P325 observer dispatch,
complete P324-lane/P325-guard execution closure, and unchanged safety scope.
Its verdict is `PASS_GO_P325_PROCESS_V2_H0`.

This H0 work and the ready manifest grant no approval or live authority. The
next step is one fresh connected Process-v2 prepare, one newly emitted exact
approval, one attended candidate transfer, bounded observation, mandatory
exact rollback, and final health verification.
