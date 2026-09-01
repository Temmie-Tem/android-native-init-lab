# S20+ G986N TWRP T2 connected-owner H0 record

Date: 2026-08-31
Live result: 2026-09-01
Target: `SM-G986N/y2q/y2qksx/G986NKSS8IYC2`
Status: **PROVED - T2 RECOVERY RETAINED, CANDIDATE CONSUMED**

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
`T2_F2_ACTIVE=true`. The retained-state assertion rotation makes the focused
hostile test 64,769 bytes at SHA-256
`8657920b486039ef37ff0dcf2ec14b2bdebd64980c7ee11c8c71d1eea39f3c5c`;
the execution model and owner identity are unchanged.

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
The candidate therefore remained globally unclaimed for a fresh run.

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

The reviewed repair was committed and re-emitted the first run as
`ABORTED_PRE_CANDIDATE_STOCK_RECOVERY_HEALTHY`, with zero candidate, rollback,
and partition-transfer attempts. It released only that run's guard and left the
T2 candidate unclaimed.

## T2 retained result

A second fresh preparation and exact returned approval consumed the sole T2
candidate. The 1,000-byte candidate result SHA-256
`4e3ccf32673c2f700fc97a09fc06691ffc2f65a088fda2e59f39e23b7047d764`
proves the caged recovery-only Odin transfer completed.

The same prepared serial and topology then appeared in ADB recovery state. The
fixed observer proved a fresh boot ID, root UID, TWRP
`3.7.1_12-AstroForge_v2`, donor incremental, `ro.secure=0`,
`ro.debuggable=1`, exact `mtp,adb`, running adbd, and the 398-byte T2 marker.
The 1,027-byte observation SHA-256 is
`636c5f68da26da44bade2230e50061b09ce0655cbf854ca894f0a4acf3685a4a`;
its 546-byte raw-capture receipt SHA-256 is
`d12d60e2c04e3e2b8734ef794105b98885c7dc818dcf80f5c9d0cd74ca3d5132`
and its 271-byte stdout SHA-256 is
`2a1fd5d711f35788449db6342e8d34b4e3fbacf2ce4356abd9646ca08b5401d8`.

The exact 1,911-byte terminal SHA-256 is
`da24acd3b33c78f4ed41565858e5314bb2c3a1acaf020ac06fb83fd99ab84d05`.
It reports `PROVED_T2_RECOVERY_RETAINED`, one candidate/proved recovery
transfer, zero rollback attempts, zero other partition transfers, and zero
S22+/A90/other-target commands. Terminal revalidation passed and the shared
guard is absent. TWRP is intentionally retained. The H0 manifest's historical
`UNKNOWN_REQUIRES_T2_FIRST_ATTEMPT` is now resolved by this separate live
terminal; the immutable build manifest is not rewritten.

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
Independent incident-repair review returned `PASS_GO` with HIGH/MEDIUM/LOW
`0/0/0`, and the zero-transfer run closed. The second fresh run produced the
retained terminal above. The global claim forbids another T2 prepare or
candidate transfer. Its closed rollback approval does not survive; any future
stock restore requires separate fresh reviewed authority. This result grants no
TWRP UI, mount, format, terminal, install, backup, restore, or arbitrary ADB
authority.

Independent review of the retained-result/status diff returned `PASS_GO` with
HIGH/MEDIUM/LOW `0/0/0` and rederived the terminal, global claim, guard absence,
raw observation, and no-authority-expansion conclusions.
