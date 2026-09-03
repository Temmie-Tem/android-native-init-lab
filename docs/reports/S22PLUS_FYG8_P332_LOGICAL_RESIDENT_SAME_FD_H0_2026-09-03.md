# S22+ FYG8 P3.32 same-FD logical-session H0 readiness

Date: 2026-09-03 KST

Target: `SM-S906N / g0q / S906NKSS7FYG8`

Tier: H0, host only

Status: `PASS_GO_P332_H0`

## Outcome

P3.32 tests one narrow explanation for the P3.31 first-session failure: the
new outer resident/reconnect lifecycle may have disturbed the already-proved
P3.30 exchange before its first `OPEN_PARSED` diagnostic. P3.32 therefore
returns to the exact P3.30 authenticated runtime and changes only its publisher
entry. One already-open tty descriptor runs two sequential complete P3.30
sessions; session two begins only after session one returns success.

Each session retains the P3.30 banner, `OPEN_PARSED`/`RNG` diagnostics,
fresh challenge, HMAC-SHA256 exchange, three fixed BusyBox commands, bounded
child cleanup, and clean `DONE`. The host opens and closes the candidate tty
once. Physical reopen count and transport reconnect count are both zero.

This is not a persistent resident install. It adds no Android service, Magisk
module, interactive PTY, caller-selected command, arbitrary file transfer,
fallback, broad retry, or selector change. A future live PASS would prove only
two authenticated logical sessions over one candidate observation window.

## Exact host closure

- fresh run ID: `c332f1e0a90b5e6d7c8a9b0c1d2e3f8b`;
- final builder result: 49,309 bytes, SHA-256
  `34b5c70bafc6eef854a95c88fb3ac6e3d1c2212de7604c76389c60f8ee0b2888`;
- candidate A/B AP: byte-identical, boot-only, 28,631,081 bytes, SHA-256
  `e1309080879700445b88cef08eb3becb4e57e524f5467979857fc79ee36a9a9d`;
- Image: 41,490,944 bytes, SHA-256
  `051338de2d7410def8be356b797b9e2310a6c0030c46fa3765b84fbff0417ded`;
- `boot.img.lz4`: 28,623,051 bytes, SHA-256
  `e68b7981e5a8dab9ba59c3ff3fbeb4aa4e0fb8ff167207a66d14009297587c87`;
- exact Magisk rollback AP: 23,367,721 bytes, SHA-256
  `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`.

The final candidate source closure contains the exact P3.30 runtime input and
does not contain the P3.31 resident runtime. P3.30 and P3.31 run identities
and APs are rejected as consumed predecessors.

## Process-v2 readiness

- candidate-static: 31,856 bytes, SHA-256
  `85313bb97fcc8bb3c925ec52b3c557c5280537b42c1741b27b9f6454e3f85634`;
- run manifest: 1,043 bytes, SHA-256
  `a2d29de712fcbb32cc4b09acb013b93e8ba7535bcbc16263be7ccb94208ee884`;
- static check: 1,960 bytes, SHA-256
  `8938a53937e2c36d7e0996d6083649d6a74c02122a621897fb69c0e34798d202`;
- tracked ready manifest: 6,827 bytes, SHA-256
  `a95641eb82a10aaa8b0371b0dccf8d6d6adf182627e1eb00588173a2851cdfc0`.

The shared host preflight reopens the exact AP, rollback, private promotion
files, P3.32 runtime/observer sources, and public key identity and returns
`PASS_DEVICE_ACTION_F1_V2_HOST_PREFLIGHT`. It reports `device_contact=false`,
`odin_invoked=false`, and `live_authorized=false`.

P3.32 D0 may accept only the exact retained P3.31 post-run baseline at
2,097,136 bytes/SHA-256
`f33384fbedd604deca988bfb8ac9522e492aa930f5e81a816348730a5d0e3238`,
whose P3.31 decoder finds one integrity-clean `NO_PROOF_OBSERVER` record at
offset 1,767,463. This proves only that the fresh P3.32 run is absent.

## Validation and review

The focused artifact, adapter, runtime, observer, and builder suite passes
21/21. Candidate-static and prepare tests pass 9/9, the runtime subset passes
6/6, and P3.32 common integration plus P3.30/P3.31 regressions pass 17/17.
Builder audit, static audit, preparation audit, Python compilation, diff check,
and actual common host preflight pass without device contact.

The current-tree raw-first CLI audit and focused P3.32 mutation test pass, and
independent review returned `PASS_GO_RAW_FIRST_P332`. The legacy full 30-case
auditor suite exceeded its 240-second bound because it repeats full-tree scans;
it was not rerun or promoted into a P3.32 readiness gate.

Independent review found one real success-classification type bug:
`physical_reopen_count=false` compared equal to integer zero. The final live
validator now requires an exact integer zero at both proof and receipt seams;
the hostile regression passes, and the reviewer confirmed the blocker is
resolved. The final read-only review reproduced the builder, static and prepare
audits, the ready-bundle verification, current source closure, boot-only AP,
focused tests and P3.30/P3.31 regressions and returned `PASS_GO_P332_H0`.

## Next boundary

This H0 package creates no D0 preparation, approval, F1 action, transfer,
recovery, replay, resident service, standing shell, or causal USB claim. After
this independent H0 review, the next step is one fresh exact-target D0
preparation. Any F1 execution still requires a new attended approval and the
mandatory exact rollback.
