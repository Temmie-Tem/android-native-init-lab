# V3430 S22+ V3429 Phase Observer Live No-Proof Result

## Verdict

`NO_PROOF_STAGE_A_VS_TRANSITION_UNRESOLVED_STOP`.

The exact V3429 boot-only candidate transferred successfully, departed the
original Odin endpoint, remained without a host USB endpoint during the quiet
candidate window, and was recovered through attended manual RDX/Download and
the pinned Magisk boot-only rollback. The first rooted rollback boot was fully
healthy, but two identical complete `/proc/last_kmsg` reads contained no
current-run PRECHECK, FINAL, malformed frame, raw run token, or failure
diagnostic.

Under the V3427 contract this is NO_PROOF, not a retention failure and not proof
that direct PID1 did not execute.

## Pins And Preconditions

- Target: `SM-S906N/g0q/S906NKSS7FYG8`
- Pre-live commits: `4eebc790`, `ce728417`
- Helper SHA256: `587d81409ecfaea6002d63aaa931d01fdab1fb6a73a403bf6ed371427773769d`
- Candidate AP SHA256: `d6b2a430b2f5d21a7bdefe5b7db050c9e627d30ef5ecdee77ee44bd764579b4f`
- Candidate boot SHA256: `93eef3b07bfbeb2154ecc9bfddfdeed682d83d950ca5e6032b7cfd75e4c9a428`
- Run ID: `f1613e72912b63f030c25a6bd7fd072e`
- Observer contract: `cba82ce1bae23f56bcad57876f5d647e31a37a36d7bc9b477de57b1f85b3babf`
- Transition contract: `426aa2bb50f6e73e153f5f5dc9cde59ddf37ab315f46860c1dc0bd0b3e810734`
- Magisk rollback AP: `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`
- Recovered FYG8 AP size: 11,499,653,242 bytes
- Recovered FYG8 AP SHA256: `7934579fc2e7fc8097b58cb28e915578a972718b2cdc3f53d3f9b5e9bd5a0bb2`
- Connected read-only preflight: PASS
- V3426-V3430 validation before live: 64 tests PASS, then 9 focused tests PASS
- Active exception: consumed/retired after this run

Private evidence:
`workspace/private/runs/s22plus_v3430_phase_observer_20260710T121509Z/`.

## Live Timeline

- Live start: `2026-07-10T12:15:36.423697Z`
- Candidate flash start: `2026-07-10T12:15:48.152116Z`
- Candidate flash done: `2026-07-10T12:15:49.745482Z`, Odin rc=0
- Original Odin departure observed: `2026-07-10T12:15:50.015824Z`
- Host `MSM_UPLOAD` endpoint: `2026-07-10T21:17:54+09:00`
- Manual Download endpoint: `2026-07-10T21:18:01+09:00`
- Manual transition elapsed: 132.350596 seconds
- Rollback flash start: `2026-07-10T12:18:02.379213Z`
- Rollback flash done: `2026-07-10T12:18:03.767112Z`, Odin rc=0
- First rooted boot ready: `2026-07-10T12:18:47.752178Z`
- Live end: `2026-07-10T12:18:48.567642Z`
- Canonical eight-event timeline: complete

The operator observed no bootloop during the candidate window. The continuous
host observer saw no candidate-created USB endpoint between the original Odin
disconnect and the attended `MSM_UPLOAD`/Download sequence.

## Retained Evidence

Both first-boot reads were exactly 2,097,136 bytes and byte-identical:

```text
4081a8389310caed3b95effd7cd46586828a7f808dc2985f4c7b32a8c2b95db0
```

The classifier found zero current-run marker, zero malformed current-run issue,
and zero foreign marker. Direct searches also found zero occurrences of the raw
run ID, `S22_V3429_PHASE_OBSERVER_FAIL`, and `sec_log_buf`. This satisfies the
V3427 absence branch exactly and cannot be promoted to PASS or FAIL.

Evidence hashes:

- `result.json`: `ac3fb5da9815e8db67422b41caf9e403bf3b7cff1b5d1fdc57acd87f2d906186`
- `timeline.json`: `72d1859f44b588ba115deb4958c2c21a04f965c01470e76d472423db71f7f8a4`
- kernel-journal observer: `9d47ae70098acb07c81269b38e3ff60a96e6cbdf4a57f27e41ca28682f2a5666`
- udev observer: `fb200f1df6caad1a2b246922289d7daa59e8b513b8d3da9db89e29ef132fd143`

## Verified Host-Side Blocker

Post-run read-only comparison found an exact V3429 identity bug:

```text
V3429 generated header:
5.10.226-android12-9-gki-30958166-abS906NKSS7FYG8

live uname -r and /proc/sys/kernel/osrelease:
5.10.226-android12-9-30958166-abS906NKSS7FYG8
```

The builder incorrectly derived kernel osrelease from the module's vermagic
first token. V3429 checks this value before module identity and `finit_module`.
Therefore, if its direct PID1 ran, it deterministically took failure code 8 and
parked before `sec_log_buf` became the retained observer. Its `/dev/kmsg`
failure diagnostic could not be captured by a module that had not yet loaded.

This explains the exact no-marker shape and proves that V3429 could not reach
Stage A as built. It does not prove that `/init` itself executed. The connected
preflight also failed to compare the generated osrelease with the live value;
that missing gate must be added before any successor candidate.

## Final Device State And Next Gate

Separate post-run read-only checks found exact FYG8 identity,
`sys.boot_completed=1`, orange verified-boot state, healthy Magisk root, and
boot SHA256
`2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`.

Next is host-only V3431 correction: pin the exact live osrelease instead of
module vermagic, bind that value into the marker/build context, add a connected
preflight equality gate, use a fresh run ID, and rebuild deterministically. No
V3430 artifact, helper, token, or exception may be reused; any successor live
run requires a new SHA-pinned exception and explicit approval.
