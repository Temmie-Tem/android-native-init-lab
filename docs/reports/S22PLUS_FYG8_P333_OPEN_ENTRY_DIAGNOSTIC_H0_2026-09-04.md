# S22+ FYG8 P3.33 OPEN-entry diagnostic H0 readiness

Date: 2026-09-04 KST

Target: `SM-S906N / g0q / S906NKSS7FYG8`

Tier: H0, host only

Status: `PASS_GO_P333_H0`

## Outcome

P3.31 and P3.32 both reached the native-PID1 banner and then stopped on the
first out-of-line console entry before `OPEN_PARSED`. P3.32 had already removed
P3.31's physical reopen/reconnect, so P3.33 changes only that remaining entry
boundary: the device emits the existing bounded diagnostic frame with stage
`0` and code `0` immediately before each console call.

The host requires stage `0` before the existing `OPEN_PARSED` and RNG stages.
Everything else remains P3.32: two complete logical sessions on one tty file
descriptor, no reconnect, the P3.30 HMAC exchange, three fixed BusyBox
commands, bounded child cleanup, and clean `DONE`. There is no new retry,
protocol, command, persistent state, interactive PTY, file transfer, or USB
causality claim.

## Exact host closure

- fresh run identity: `c333f1e0a90b5e6d7c8a9b0c1d2e3f7b`;
- builder result: 48,548 bytes, SHA-256
  `9c3697ab3e9bba7a9d8e0ed038d0bbe69cf0e2c3da333cd433e338149398d03c`;
- candidate A/B AP: byte-identical and boot-only, 28,631,081 bytes,
  SHA-256 `1a6036b688ae92c94f459aee66e06a817e767aa615c6a7a9cb2a22b7d13487b3`;
- Image: 41,490,944 bytes, SHA-256
  `f9b4465ba943bc4e1a473f0c133f5f3598e9e026f36791db140549b0edbd8e22`;
- `/init`: 82,264 bytes, SHA-256
  `e3d357a06de37578d6d013559fba0b724bfaf3a2dec467b600c80ece8bccffd4`;
- `boot.img.lz4`: 28,622,656 bytes, SHA-256
  `6b4b726f47d8e9e0fdd3c8c1b5b79d68b98d74b787a32d365e2830d8944677b1`;
- exact Magisk rollback AP: 23,367,721 bytes, SHA-256
  `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`.

Only one of the twelve inherited source-closure members changes: the runtime
include that adds stage `0` before each out-of-line console call. P3.30 through
P3.32 run identities and candidate APs remain rejected predecessors.

## Process-v2 readiness

- candidate-static: 31,201 bytes, SHA-256
  `f728aeea38ff6ec25e93c33627c1a398e716d8779a468f18aefaa1d2738d656a`;
- run manifest: 1,025 bytes, SHA-256
  `3aa0b16a796a1e8a10c0c1f016288675b9be743d6c6e7bc077540de0599deaa6`;
- static check: 1,942 bytes, SHA-256
  `90a0bcae40d44466a1ad4db21e419189f450a9485d36f6c7dea9b5418e1d6089`;
- tracked ready manifest: 7,090 bytes, SHA-256
  `6fb30bec1e9640ce1659b906f181dce9390f769ed24b80f3b35802418ed84f40`.

The private promotion records are mode `0400` with one link; the public ready
manifest is mode `0644` with one link. Non-creating rehearsal reopened the
published bundle and returned `verification=true`, `created=false`,
`device_contact=false`, `odin_invoked=false`, and `live_authorized=false`.

P3.33 D0 may recognize only the exact retained P3.32 rollback baseline:
2,097,136 bytes, SHA-256
`455eec000b3aa14e8fca155b857910b4ed4c16285e55e390e59dcfb2f3386ab4`.
The fixed P3.32 decoder finds one clean, foreign-free `NO_PROOF_OBSERVER`
record at offset 1,658,084. This proves only that fresh P3.33 is absent and
does not reuse P3.32 session evidence.

## Validation and review

Focused non-socket tests pass 29/29, Unix-socket observer tests pass 4/4,
raw-first tests pass 3/3 plus the current-tree CLI audit, and selected
P3.28/P3.30/P3.31/P3.32/P3.33 common regressions pass 23/23. Python compilation,
diff checks, static and preparation audits, and the repository boundary check
pass.

Independent review of the final changed closure returned `PASS_GO_P333_H0`.
It confirmed stage-order enforcement, the unchanged same-FD/no-reconnect/no-
retry semantics, canonical source-key round trips, exact offline verification,
and zero device/ADB/Odin contact. During implementation an unused execution of
the complete P3.32 static module was removed; P3.33 now retains only its exact
byte receipt, avoiding an unnecessary duplicate validation path.

## Next boundary

This H0 result creates no prepared run, approval, F1 action, transfer,
recovery, replay, resident install, standing shell, or causal USB claim. The
next step is one fresh exact-target D0 preparation. F1 still requires the new
prepared P3.33 approval and attended exact rollback.
