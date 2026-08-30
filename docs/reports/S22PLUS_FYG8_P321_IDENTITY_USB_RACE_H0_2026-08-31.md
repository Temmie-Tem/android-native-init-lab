# S22+ FYG8 P3.21 identity and USB-race H0 closure

Date: 2026-08-31

Target: `SM-S906N` / `g0q` / `S906NKSS7FYG8`

Verdict: `PASS_GO_P321_H0`

Authority: host-only; not an F1 approval or live result

## Scope

P3.21 fixes only the two blockers retained from the consumed P3.20 run:

1. replace the mixed P3.19-kernel/P3.20-userspace identity with one P3.21 run ID;
2. tolerate one observed usbfs node-departure race after transfer without replaying Odin.

It adds no new experiment, baseline ladder, recovery path, partition, target selector,
or causal claim.

## Artifact result

The fresh run ID is `c321f1e0a90b5e6d7c8a9b0c1d2e3f4b`.

- Image: 41,490,944 bytes,
  `f3b18031ffc6548d619f3c35e92b6f8b72a1fc1f7863c36a3b5b14cbe09c2810`.
- `/init`: 80,504 bytes,
  `2d260502fe55ed001532fc9fb8ca9bf2fed29f2722ce20d324df03aadd245bc5`.
- Candidate AP A/B: 27,279,401 bytes,
  `770694d16123ea9a0ce28aded393fbf44e280794e5a94107c47952e904586514`.
- Exact rollback: 23,367,721 bytes,
  `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`.

The Image transform changes only the same-length raw run-ID occurrence and the
same-length IKCONFIG gzip region. The gzip header remains
`1f8b0800000000000203`; unchanged input round-trips byte-identically. Kernel
layout, IKCONFIG markers, symbol/PREL32 provider sections, CRC sections, boot
container structure, and bytes outside the Image slice remain fixed. Independent
AP unpacking proves that the packaged Image and packaged `/init` both carry the
P3.21 identity and neither predecessor identity.

This is `PROVED` for the host artifacts. It does not prove a live kernel return,
USB attach, or candidate success.

## USB race result

The measured usbfs reader classifies departure only after a completed nonzero
birth-time command with empty stdout and a direct non-following `stat` that returns
`ENOENT`. Default and pre-transfer inventory remain fail-closed. Only the existing
post-transfer `allow_live_departure` path permits one resnapshot, and the resulting
path set must equal the initial set minus exactly the departed path.

Replacement at the same path, an unrelated arrival, another disappearance,
timeout, output overflow, producer failure, or non-`ENOENT` error still stops.
The Odin enumeration/transfer runner is not invoked again. This is a reviewed
race-handling mechanism, not evidence that P3.20 or P3.21 reached USB.

## Process-v2 closure

- Builder result: 33,947 bytes,
  `4bf4edcbe78456768e3494b47a497628ba9549f8767b5c214f3f50c79aad293e`.
- Candidate-static `-02`: 22,778 bytes,
  `7e4d4a54ccc74dd012ab5635bc472518aa7342e0f5e51cd1f3dbc5e2e98c3d45`.
- Ready manifest: 2,743 bytes,
  `d3c5a4885727bfe1b0ac5000ae38d6d523a3a4d0545a32f57a460f703839c7ef`.

Runtime prepare/execute must call the dedicated `validate_bound_result`; it cannot
fall back to the H0 builder audit. P319/P320 run IDs and the consumed P319 AP are
explicitly rejected. `COMPLETE` remains `NONCAUSAL_SUCCESS_PATH`, rollback and
final health remain mandatory, and candidate replay remains forbidden.

Focused results: P321 artifact/adapter/static 11 passed; P321 ready/runtime
projection 3 passed; USB identity/core 108 passed; P320 promotion/ready regression
5 passed; current-tree raw-first audit 1 passed. Python compilation and
`git diff --check` passed. Independent read-only review returned
`PASS_GO_P321_H0` with no material blocker.

## Next action

The ready manifest creates no run directory, approval, device command, or live
authority. The next invocation is ordinary attended Process-v2 preparation with
one fresh baseline. D1 is used only if that baseline is dirty. A fresh explicit F1
approval is still required before Download entry or candidate transfer.
