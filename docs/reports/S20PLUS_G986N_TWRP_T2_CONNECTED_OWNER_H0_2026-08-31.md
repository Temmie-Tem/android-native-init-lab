# S20+ G986N TWRP T2 connected-owner H0 record

Date: 2026-08-31
Target: `SM-G986N/y2q/y2qksx/G986NKSS8IYC2`
Status: **ACTIVE OWNER INCIDENT REPAIR - PASS_GO**

## T1-derived correction

T1 remains `NO_PROOF_T1_RETURNED_STOCK_RECOVERY_HEALTHY`. It proved one
candidate and one exact-stock recovery transfer, final healthy rooted Android,
and exact stock recovery. Its fixed recovery observer matched root UID, TWRP
`3.7.1_12-AstroForge_v2`, donor incremental, security properties, running adbd,
and the T1 marker. The sole mismatch was effective
`sys.usb.config=mtp,adb` versus T1's predeclared `adb`.

T2 does not reinterpret the T1 terminal. It mechanically revalidates the exact
active T1 source closure and journal, then pins and reparses the 2,144-byte T1
terminal SHA-256
`9475e2cd6f283c7390b0d4b86b5e5208f0e943b2b452439febbe1dc3ca82cd7f`,
336-byte observation SHA-256
`c2c1d123d1f26a2416252fc5da8c576efbb0bf2bd9527c2b2fcebd3529204e74`,
546-byte raw-capture receipt SHA-256
`bbd780281ffccf7991ad4a5b10c4ba063be9bc690422699b75a9b033159d024b`,
and 271-byte stdout SHA-256
`c2c8b4e7393153ff40e1ca3487b76d8c345e1c2816636a6f30913e9d27baf0cc`.
The recovery boot must differ from both T1 Android boots, and current serial
continuity is required without publishing the identifier.

## Exact T2 closure

The deterministic builder is 25,475 bytes at SHA-256
`505f4fabc5e9684464b3c266453734db9e5f089507576df5dac00785683e635d`.
Its 11,687-byte focused test is SHA-256
`ce29e8d8f74051dcb4502835c3ebe92dec26cbfeac74cd68788ed4722d1f987c`.
The 9,711-byte manifest is SHA-256
`80622cf532e0a846c1825a847449d5bdc7a9226bb1b61e068046ecb5851d1d48`
and preserves runtime acceptance as `UNKNOWN_REQUIRES_T2_FIRST_ATTEMPT`.
It preserves the reviewed T1 stock substrate and ramdisk safety changes while
using a distinct 398-byte T2 marker SHA-256
`19a1a617fd2e97feda6362a2435e3d2bcce600fb37f983dd131e21c5ecf9c246`.

The candidate identities are:

- recovery-only AP: 52,101,161 bytes, SHA-256
  `6d10b3154f2e899ee64305f3f3279d7d5243eb917f1fedb413b8f88d22ec88cb`;
- sole `recovery.img.lz4`: 52,096,466 bytes, SHA-256
  `6fed66d26ff7cc75899c4471ab60eefb49bccff052de37043bced65719b65936`;
- decoded recovery: 82,694,144 bytes, SHA-256
  `d46a1f72743a28acc4c820184d7318df9801ee43d425c22d092778e4b63d1f89`.

The sole rollback is the demonstrated 36,608,041-byte exact-stock
recovery-only AP SHA-256
`ac9745b642c7fbd950d988671f707e47d58f8e2092464b27a37bede2267d7157`.
Both archives contain one regular `recovery.img.lz4` and no other partition.

## Qualified implementation

The profile
`workspace/public/src/scripts/revalidation/s20plus_g986n_twrp_t2_profile_h0.py`
is 12,847 bytes at SHA-256
`c02b78f2a1215a1fc2104a4634264609d2060d610bc628a068b318cb1cf55fb7`.
It changes the retained observation to exact `mtp,adb` and the new T2 marker;
all other fixed TWRP properties and bounds remain.

The connected owner
`workspace/public/src/scripts/revalidation/s20plus_g986n_twrp_t2_f2.py` is
167,684 bytes at SHA-256
`7f5519ef76091f491165a0be5ce81733f0343318057d02f7577954db1d1a0d11`;
its activation-normalized SHA-256 is
`67f5f1708037afb6ba8c3f2879e70195453bc36df112bb37e0a37378bebd66a7`.
`T2_F2_ACTIVE=true`. The 64,691-byte focused hostile test is SHA-256
`1865c071546858035bffa667d17ee0f9f89de19b017df9e6c687c7be738a6929`.

The owner retains T1's exact-target binding, caged single Odin attempt per
branch, global candidate no-replay, no-clobber typed journal, raw evidence,
physical exact-stock rollback, final stock digest, and other-target isolation.
Only a new same-serial/topology T2 marker observation can produce
`PROVED_T2_RECOVERY_RETAINED`. That terminal has one candidate transfer, zero
rollback transfers, and grants no recovery UI, mount, format, install, backup,
restore, terminal, or other partition action.

## Expired-approval cleanup incident

The first fresh T2 preparation completed, but its exact approval was returned
after expiry. `--execute` rejected it inside `read_prepared()` before approval
consumption, candidate claim, Download intent, Odin, or any partition effect.
The candidate therefore remains globally unclaimed.

The first prepared-only abort revalidated the same healthy rooted Android boot
and exact stock recovery, publishing its bounded root/recovery receipts, then
stopped because the original check required a later boot. That ordering left
the run guard held even though candidate and rollback intents are absent. The
repair removes only the later-boot requirement for this already zero-transfer
terminal. The terminal validator still requires no candidate/rollback intent,
zero attempts, exact current health and stock recovery, matching global-claim
state, and the fixed pre-candidate recovery-read receipt before releasing the
run's guard. It sends no reboot or partition payload and grants no approval.
Before any new health read, terminal publication, or guard release, the repair
accepts only the exact pre-repair active closure SHA-256
`bdf8bd67962729c38152235b725ca8badca093fe1d08b229c84dd5fd2a669a57`
or the freshly rederived current reviewed closure. A stale/forged third closure
stops with the guard retained.

## Validation and authority

The T2 builder corpus passes 14/14 and the connected-owner corpus passes 55/55,
including exact T1 raw-evidence acceptance and negative USB/marker mutations;
the combined T2 corpus passes 69/69. `py_compile`, deterministic rebuild,
dormant and active render/host validation, predecessor revalidation, prior T1 51/51,
registry integration, and `git diff --check` pass. This report, revision-5
boundary, risk-tier/target sections, builder, profile, owner, and tests remain
exactly bound. The dormant closure and activation-only diff each received
independent `PASS_GO` with HIGH/MEDIUM/LOW `0/0/0` before their commits.
Activation created no standing approval. One T2 prepare and one bounded
prepared-only cleanup read occurred; the approval expired before consumption.
No T2 candidate claim, Download entry, Odin invocation, or recovery write has
occurred. Independent incident-repair review returned `PASS_GO` with
HIGH/MEDIUM/LOW `0/0/0`; the committed repair is required before the existing
zero-transfer run may close.
