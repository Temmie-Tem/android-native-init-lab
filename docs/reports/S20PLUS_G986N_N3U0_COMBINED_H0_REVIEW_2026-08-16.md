# S20+ G986N N3-U0 combined H0 review

Date: 2026-08-16

Target: Samsung Galaxy S20+ 5G (`SM-G986N` / `device=y2q` /
`product=y2qksx` / `G986NKSS8IYC2`)

Verdict: **PASS_GO - EXACT HOST CLOSURE ONLY - OBSERVER DORMANT - NO LIVE AUTHORITY**

## Reviewed closure

| Public input | Size | SHA-256 |
|---|---:|---|
| `workspace/public/src/native-init/s20plus_n3u0_acm_witness.c` | 18,286 | `cb6b71b08575658edc22bb00472ee13eaa8198543ad393ef6e4ad6efb22ef2f1` |
| `workspace/public/src/android/s20plus_n3u0_acm.rc` | 368 | `bbaab9cc2829119d5a90775456eb0935b0890b1a3ce0e418afc847cc346385ad` |
| `workspace/public/src/scripts/revalidation/build_s20plus_n3u0_magisk_overlay.py` | 22,454 | `93af2c760acd7d4f33a992fe68cb0346485aa675490aed6c43b993f1f09dcce2` |
| `workspace/public/src/scripts/revalidation/s20plus_n3u0_usb_observer.py` | 16,713 | `f1c6af4123684be1122950442472de7803995345e125955322a8fd262b25e44f` |
| `tests/test_s20plus_n3u0_magisk_overlay.py` | 12,470 | `5e95b63ab9562a18069b8f241ec789e096f2d73be40d7379bdeecaa62538d57b` |
| `tests/test_s20plus_n3u0_usb_observer.py` | 15,132 | `e6f2c72e8b5ef267af49814db23f2f629592c51a1916135a8be6c739fe70a5a0` |

The reviewed component reports are SHA-256
`e4dfd0a6b25720c3488c69ae7c38928c07649db58b50f41dcec71e412640bcb6`
for the overlay build and
`d268e147b0e43aeec476620ded1d1cdc75205f50c13668dc4114a24378da2f95`
for the dormant observer.

The corresponding canonical private H0 outputs are:

| Output | Size | SHA-256 |
|---|---:|---|
| `s20plus_n3u0_acm` | 597,752 | `a0d90dbba2fe6f85af2421f888ecdfd76ecf22420b03846260ecab708de4810d` |
| `boot.img` | 67,108,864 | `7024d206453dbd82f04187b7a3ccb6042aef7e2e20ed9660a67b47ecf19206eb` |
| `boot.img.lz4` | 26,103,098 | `ee57ba63c557bca651fd633f77d6f006585ec0d5b22bb18418a6fade3590809d` |
| `AP.tar.md5` | 26,112,041 | `3aad497979cfa0f247aef68f50ea792f40127afa037c134eeb0d2e96798ca7af` |
| `manifest.json` | 11,916 | `594b83dfc52f37e1db21ab5f240b804ad10a8eb1d0642719aef0ecd5ddfc619f` |

## Review sequence and findings

The first independent pass returned `NO_GO` on two concrete issues:

1. a successful stock-UDC unbind write followed by readback/close failure could
   return before the state machine acquired restoration ownership; and
2. the dormant observer plan had reversed the exact target's Android
   `device` and `product` fields.

The remediated witness sets `stock_restore_required` before entering the
unbind boundary. Therefore every failure return from that boundary attempts
the one exact stock `g1` restore, while owned cleanup remains limited to paths
after the owned gadget was touched. Its host selftest explicitly models an
effect-before-failure unbind and requires one restore.

The observer now emits `device=y2q`, `product=y2qksx`, and the hostile test pins
the complete target map. The observer report also states the actual framing:
the host accepts the first complete exact record while the reviewed witness
may continue its bounded repeated emission.

A fresh independent review of the rotated closure returned `PASS_GO` with no
remaining blocker.

## Verification

- focused overlay plus observer tests: **25/25 PASS**;
- exact eleven-module S20+ aggregate: **315/315 PASS**;
- Python `py_compile` and scoped whitespace checks: PASS;
- two complete artifact builds and two witness builds: byte-identical;
- static AArch64 ELF, no interpreter or `DT_NEEDED`, no writable-executable
  load segment: PASS; and
- all six public identities and five private output identities above match.

The independent reviewer and primary workflow made no device, live USB, ADB,
`su`, Odin, network, reboot, or partition-transfer action during this review.

## Authority boundary and next unit

`PASS_GO` qualifies only these exact host bytes. `OBSERVER_ACTIVE` remains
false. The build-time artifact manifest retains its pre-review
`REVIEW_PENDING` label; this review report is the later qualification record
and does not mutate the artifact or activate it.

No connected run, approval, candidate intent, boot transfer, observation,
rollback, or final health exists. The next separately reviewed unit must be an
attended S20+-only boot owner that binds the exact target and current boot,
empty Download/USB baseline, the reviewed candidate AP, this observer, the
exact resident Magisk rollback boot, candidate no-replay, immediate recovery,
and final exact healthy rooted Android. Until that owner is implemented and
activated, N3-U0 remains H0-only.
