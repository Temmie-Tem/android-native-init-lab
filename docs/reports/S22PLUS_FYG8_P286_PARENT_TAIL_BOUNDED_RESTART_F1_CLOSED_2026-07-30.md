# S22+ FYG8 P2.86 parent-tail bounded-restart F1

Date: 2026-07-30 KST

Status:
`NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK; TRANSACTION_CLOSED`

Correction notice: the later focused H0 source/slot audit proves that P2.86
withheld this run's `0x8f/detail=0xc18` publication until exact parent
`runtime_status=suspended` readback succeeded. The same audit rules out a torn
generation-89 write and in-run retained-log `idx` drift, and identifies the
unmarked pre-dispatch tracefs snapshot as the first unbounded restart
boundary. See
`S22PLUS_FYG8_P286_POST_0X8F_SILENCE_ATTRIBUTION_H0_2026-07-30.md`.

## Scope

This report records one authorized P2.86 Process v2 candidate attempt, its
bounded observation, one rollback-only recovery resumption, the mandatory exact
Magisk rollback, and final health. It does not authorize a replay or a
successor F1.

Raw device and host evidence remains under `workspace/private/`. This report
contains no device serial, USB identity, PARTUUID, address, or raw log.

## Exact transaction

- source contract:
  `s22plus-fyg8-p286-parent-tail-bounded-restart-v1`;
- candidate run ID: `c6cde593033d6f1be93f82c8ff5a81e8`;
- manifest: `s22plus-fyg8-p286-process-v2-ready-1`;
- candidate boot-only AP SHA256:
  `db06aa4e9365d9620cba523a91b13968810093ad7a2f42e3aba0c989ac75fe26`;
- exact Magisk rollback AP SHA256:
  `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`;
- ready-manifest SHA256:
  `673167bdffc8e0714528dd118dfa0ef4d3432c7aba3646a5c37525cafa2bd1aa`;
- approval binding SHA256:
  `7d2609855afd41c174c02792ee1aaed7e773a12c46b81612e5c1d600a363b2af`;
- validated bundle SHA256:
  `6aea0254047fe9b88b2bbf1efb3537ddbf71aa8479486878c3ace967f180e91b`;
- execution-closure SHA256:
  `74bf82006ed6f869c24062a7c3626682d2c115c255d38e8ba10f43e62dd45460`.

The downstream runner registration had an explicit independent safety-review
PASS before connected D0. The standalone D0 and the preparation D0 each
observed one exact healthy target, a clean retained baseline, and zero Download
endpoints. Strict reopening of the prepared binding passed.

The candidate and rollback each completed exactly one boot-only Odin transfer.
The candidate was not replayed. The operator reported a normal candidate boot
with no boot loop. That observation is not an ACM or retained-checkpoint
acceptance result.

## Candidate observation

The candidate observer ran for the full 300-second bound. It received no
matching CDC ACM endpoint or banner and classified `endpoint-timeout`.
The candidate-observer guard was released cleanly. The Download endpoint was
absent at the observation boundary.

This is a bounded negative host observation, not evidence that the candidate
failed to boot. It proves no exact ACM receipt.

## Retained result

Two post-rollback reads are byte-identical. Each is 2,097,136 bytes with
SHA256:

`91d83c3e3fad1cc6bfe02b52d151095ae649484e66ca37a3e06833a010ad0585`

The decoder found one exact P2.86 record, zero historical-family records, zero
foreign records, and no integrity issue:

```text
generation 88: stage 0x8f, outcome progress, detail 0xc18
```

The active detail is `suspended-power-helper-off-zero`. The structured
classification is `E2_PROGRESS_OBSERVED`. It is neither terminal nor
terminal-success.

The exact run ID and policy ID match the P2.86 manifest. No P2.86 failure,
success, or later progress record survived.

## What the result proves

The retained detail preserves the P2.84 child/power-helper semantics, but
P2.86 moved its publication after a new parent-status gate. In the exact
source-bound runtime it establishes:

1. initial parent `peripheral` mode and exact real-UDC membership were reached;
2. the bounded NONE helper completed its exact write and normalized readback;
3. the traced `dwc3_otg_start_peripheral(..., 0)` pair returned zero;
4. the child suspend callback returned nonnegative;
5. child runtime status read back exactly `suspended`;
6. the traced power-off helper entered, returned, and reported zero; and
7. parent runtime status read back exactly `suspended`.

As before, the power-helper return is software progress, not electrical proof.
It does not prove a regulator vote changed or a physical rail lost voltage.

## What the result does not prove

No later P2.86 checkpoint survived. In particular, there is no `0x90`
restart-trace-cleanup-pending marker, no new exact detail `0xc50..0xc5c`, and
no terminal `0x93`.

Therefore the retained evidence does not prove:

- completion or quiescence of the stop-side outer `dwc3_otg_sm_work`;
- entry to or return from the first restart tracefs snapshot;
- bounded PERIPHERAL helper dispatch or completion;
- DEVICE restart write or `peripheral` readback;
- child resume or femto-HS PHY reinitialization;
- configfs UDC bind;
- final UDC state or speed; or
- host ACM receipt.

The P2.86 bounded failure machinery was intended to make those later outcomes
classifiable. The focused H0 audit shows that unbounded tracefs and sysfs
operations still precede those publications. Both slots remain valid, and the
raw ring bytes prove no indexed retained-log write occurred before the next
boot, so a torn newer slot or header-drift rejection is not the explanation.
The exact live blocking primitive remains unproved.

## Rollback recovery deviation

After candidate observation closed, the first physical-Download endpoint
capture failed closed at
`enumeration-evidence-before-snapshot`. The persisted diagnostic classified
`inventory-membership-changed`: one USB member disappeared between enumeration
and the snapshot. The durable journal remained at `OBSERVED`; no rollback
attempt start or rollback transfer had occurred.

A subsequent read-only USB inventory found one stable exact S22 Download
endpoint. Process v2 `--recover` then reopened the same approval binding and
resumed rollback only. Recovery accepted no approval argument, could not
transfer the candidate, and completed the exact rollback on attempt one.

This was a recovery-path resumption, not a candidate retry. The original
approval already preauthorized the mandatory rollback.

## Rollback and health

Final checks passed for:

- Android boot completion and stopped boot animation;
- FYG8 stock kernel identity;
- Magisk root access;
- exact boot rollback identity;
- recovery, vendor_boot, and DTBO supporting-partition identities; and
- absence of an Odin endpoint.

The strict result validator reopened the candidate and rollback transfer
receipts, both final retained reads, final health, journal, approval binding,
and complete execution closure. It passed with:

- candidate transfer starts/results: `1/1`;
- rollback transfer starts/results: `1/1`;
- durable journal records: `19`;
- final state: `CLOSED`;
- recovery required: `false`.

The canonical timeline is:

```json
{
  "events": [
    {"name": "live_session_start", "timestamp_utc": "2026-07-30T05:13:13.709973Z"},
    {"name": "candidate_flash_start", "timestamp_utc": "2026-07-30T05:13:29.006222Z"},
    {"name": "candidate_flash_done", "timestamp_utc": "2026-07-30T05:13:30.616893Z"},
    {"name": "candidate_boot_ready", "timestamp_utc": "2026-07-30T05:18:31.134238Z"},
    {"name": "rollback_flash_start", "timestamp_utc": "2026-07-30T05:22:52.644413Z"},
    {"name": "rollback_flash_done", "timestamp_utc": "2026-07-30T05:22:54.168702Z"},
    {"name": "rollback_boot_ready", "timestamp_utc": "2026-07-30T05:27:47.316794Z"},
    {"name": "live_session_end", "timestamp_utc": "2026-07-30T05:27:47.343156Z"}
  ]
}
```

The live-result artifact is 8,025 bytes with SHA256:

`48f4043ff839b0a0640db5e06ea026cfab244bea072a295c671ac15031860aa4`

The live-state artifact is 5,792 bytes with SHA256:

`9b1851ed01803a458df605a1c531dc03324edccabf4061ee65a7f11825aba3a7`

The journal-head artifact is 276 bytes with SHA256:

`162dfa2484bbe11c38ca5a74c06e24db23eb91ebb96dc7f4eb597cddb2a7838e`

The final verdict is `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`, with outcome
`candidate_not_proven_rollback_verified`.

## Disposition

The approval is consumed. Do not replay or rebuild P2.86. The focused H0 gap
analysis is complete in
`S22PLUS_FYG8_P286_POST_0X8F_SILENCE_ATTRIBUTION_H0_2026-07-30.md`.
Do not implement P2.88 until a host-only successor design places attributable
evidence before every unbounded restart snapshot/read and solves the
single-publication stage constraint.

Any later live candidate requires a new versioned source contract, fresh
identity, ordinary Full-LTO/package/static gates, a new ready manifest,
connected D0, and fresh exact F1 approval.
