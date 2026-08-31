# S20+ G986N boot recovery-canary B0 F1 H0 review

Date: 2026-08-31

Status: **PASS_GO_H0 - DORMANT, NOT ACTIVE**

## Scope

This review qualifies one attended, mandatory-rollback F1 owner for the exact
operator-owned `SM-G986N` / `y2q` / `y2qksx` /
`G986NKSS8IYC2` target. It does not activate the owner, prepare a run, consume
an approval, contact a device, enter Download mode, invoke Odin, or transfer a
partition payload.

The candidate and rollback are the already-qualified B0 carrier artifacts:

- candidate AP: `36,198,441` bytes, SHA-256
  `a8ed52d314e3b0cf5820e99ecd55e97cacdbc8a943d2181886d52d42a1c177fa`;
- resident rollback AP: `25,835,561` bytes, SHA-256
  `1b33d098ea34b0396330cedf2e40c508704f1ba035b1f81e80a8526a637f1be2`.

Each archive contains only canonical `boot.img.lz4`. Recovery-partition read,
write, and transfer counts are fixed at zero.

## Qualified owner

- runner:
  `workspace/public/src/scripts/revalidation/s20plus_g986n_boot_recovery_canary_b0_f1.py`;
- size: `218,089` bytes;
- SHA-256:
  `4457bb0179586fcb8edaa88e895aae17ca951ae44ed8ddb0d0c0a592de86a6b7`;
- activation-normalized SHA-256:
  `7d4299e8a4fc503eee8d41ae0cf051b4f922b72c5550443e2d8cdba3cf2622b5`;
- dormant constant: `B0_F1_ACTIVE = False`;
- host closure SHA-256:
  `3623bdb9b4c3d907355808e4653d46dbd6012821ca023ea2240dd0ee4c29501e`.

The focused test is `47,856` bytes at SHA-256
`202511efb0ae3459e8b604ea7d59b71aa19f93f26cb47453a801cb200f7d0d5b`.
`py_compile`, 48/48 focused tests, and `--validate-host` passed. Connected
modes stop before any command while dormant.

## Safety result

The reviewed owner fixes the following boundaries:

- fresh prepare begins from exact rooted resident Android, records an empty
  Download baseline, performs one no-replay transition, and emits one exact
  expiring approval only after binding the resulting Download endpoint;
- candidate and rollback setup revalidate the endpoint, exact boot-only AP,
  Odin, cage shell, and cgroup capability before intent; each intent is the
  last durable boundary before its one backend attempt;
- every Odin path uses a fixed environment. Transfers and payload-free return
  run inside an intent-bound cgroup; recovery first kills any survivor, proves
  the cage empty, removes it, and publishes quiescence. Read-only Odin listing
  uses a stable transient cage plus a pinned ten-second BusyBox watchdog;
- all journal, guard, and global-claim final names use file-fsynced
  `O_TMPFILE` plus no-replace `linkat(AT_EMPTY_PATH)` and directory fsync;
- root-health raw output includes the boot ID in the same fixed root command.
  Completed failures and stale-boot captures rotate to bounded ordinals, while
  every accepted receipt re-derives the raw boot digest and capture family;
- candidate observation distinguishes claim proof from transport, requires a
  different boot, and does not treat an unchanged Download endpoint after an
  uncertain transfer as quiescent;
- resident rollback is mandatory after candidate intent. Candidate and
  rollback effects never replay, and recovery closure no longer reopens the
  candidate, builder, manifest, or prose reports;
- physical fallback has one expiring attended confirmation, one bounded
  observation, at most one post-cut current read, and a durable consumed miss;
- terminal `PROVED` requires completed candidate transfer, the intended B0
  claim, completed rollback transfer, and fresh rooted resident health.
  `REFUTED` also requires completed candidate attribution; otherwise the
  result remains `NO_PROOF`.

Independent hostile review returned `PASS_GO_H0` with HIGH/MEDIUM/LOW
`0/0/0`. It re-derived the exact source and test identities, 48/48 result, and
host closure. The review issued no ADB, Odin, or other device command.

## Authority boundary and next gate

This result qualifies a dormant capability only. The current target contract
still says arbitrary F1 is undefined. Before any connected command, a separate
target-contract amendment and mechanical activation must receive independent
review. After activation, the owner must perform a fresh connected `--prepare`
and stop for the exact approval token it emits. Earlier general consent is not
that prepared binding. S22+, A90, and all other targets remain untouched.
