# S22+ FYG8 P2.84 controlled-suspend boundary F1

Date: 2026-07-29 KST

Status:
`NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK; TRANSACTION_CLOSED`

## Scope

This report records one authorized P2.84 Process v2 candidate attempt, its
bounded observation, the mandatory exact Magisk rollback, and final health.
It does not authorize a replay or a successor F1.

Raw device and host evidence remains under `workspace/private/`. This report
contains no device serial, USB identity, PARTUUID, address, or raw log.

## Exact transaction

- source contract:
  `s22plus-fyg8-p284-sysfs-ingestion-correction-v1`;
- candidate run ID: `023060c8dd0ab036f8547a816624356f`;
- manifest: `s22plus-fyg8-p284-process-v2-ready-1`;
- candidate boot-only AP SHA256:
  `f0362df50d105ec2cd198572ff87c4f7c194e92ab8cea9279bd802ed04541682`;
- exact Magisk rollback AP SHA256:
  `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`;
- approval binding SHA256:
  `454bcb68449ec863b0bbb106a27858fd94872cc0e3ec6130d4b233e1833528d6`;
- validated bundle SHA256:
  `c3a670ba0477723380e2b685525a19db92880bc52d53ccae36dd342c2f598eaf`;
- execution-closure SHA256:
  `2513f750247ace7d83484980cfec2dbcd486e6afbf816148189f409621dcc3c2`.

The candidate and rollback each completed exactly one boot-only Odin transfer.
The candidate was not replayed. The operator reported a normal candidate boot
with no boot loop. That observation is not an ACM acceptance result.

The candidate observer ran for the full 300-second bound, accepted no matching
ACM endpoint, and released its guard cleanly. The Download endpoint departed
and was absent at the observer boundary.

## Retained result

Two post-rollback reads are byte-identical. Each is 2,097,136 bytes with
SHA256:

`aa3b3a7fa7a524e3f06d7c5e9c9a9508ec2691dd572e44369d613218abad9c44`

The decoder found one exact P2.84 record (family count one) and zero foreign
records:

```text
generation 87: stage 0x8e, outcome progress, detail 0
generation 88: stage 0x8f, outcome progress, detail 0xc18
```

The active detail is `suspended-power-helper-off-zero`. The structured
classification is `E2_PROGRESS_OBSERVED`; the record is neither terminal nor
terminal-success.

## What the result proves

Stage `0x8e/detail=0` closes the P2.82 comparator false negative under the
versioned P2.84 correction. In the exact source-bound runtime it establishes:

1. the inherited prefix reached initial parent `peripheral` mode and exact
   real-UDC membership;
2. the bounded helper completed the exact `none` write;
3. the normalized parent-mode readback matched exact `none`; and
4. the authoritative stop worker entered, returned, and reported zero.

Stage `0x8f/detail=0xc18` then establishes:

1. the child suspend callback entered and returned a nonnegative result;
2. the child runtime status read back exactly `suspended`; and
3. the traced power-off helper entered, returned, and reported zero.

This is the first live P2.84 proof through the corrected NONE readback and the
controlled child-suspend boundary.

## What the result does not prove

The exact contract deliberately treats the power-off helper result as software
progress, not electrical proof. A zero return does not prove that the helper
body changed state, that a regulator vote changed, or that an analog rail lost
voltage; it may include an idempotent path.

No `0x90`, `0x91`, `0x92`, or terminal `0x93` checkpoint survived. Therefore
the retained evidence does not prove:

- exact DEVICE restart write or `peripheral` readback;
- child resume or femto-HS PHY reinitialization;
- configfs UDC bind;
- final UDC state or speed; or
- host ACM receipt.

The runtime calls the restart phase immediately after publishing `0x8f`, but
absence of a later retained checkpoint does not identify whether execution
stalled, reset, lost retainable state, or failed before a checkpoint could
survive. No precise restart cause is inferred.

## Rollback and health

The preauthorized rollback completed without candidate replay. Final checks
passed for:

- Android boot completion and stopped boot animation;
- FYG8 stock kernel identity;
- root access;
- exact boot rollback identity;
- recovery, vendor_boot, and DTBO supporting-partition identities; and
- absence of an Odin endpoint.

All eight canonical timeline events are present in order:

1. `live_session_start`
2. `candidate_flash_start`
3. `candidate_flash_done`
4. `candidate_boot_ready`
5. `rollback_flash_start`
6. `rollback_flash_done`
7. `rollback_boot_ready`
8. `live_session_end`

The durable journal has 19 records and state `CLOSED`. Recovery is not
required. The live-result artifact is 8,117 bytes with SHA256:

`c825c662e459913c6cfafdd541660a7cf36500d70cef4c41008f67d8e2526e16`

The live-state artifact is 5,838 bytes with SHA256:

`5e5c372d8f9eed1b12150f4712f9f517202c18c993a4c88f1894947aea8b69aa`

The journal-head artifact is 276 bytes with SHA256:

`5295ab174ae85cfb01d20a77a97c5e6728c29ea04dc1ca24ce4ae5de5c746df7`

The final verdict is `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`, with outcome
`candidate_not_proven_rollback_verified`.

## Disposition

The approval is consumed. Do not repeat P2.82, replay P2.84, or rebuild the
P2.84 candidate. The next bounded unit is H0 analysis of the exact interval
after the `0x8f` publication and before any `0x90` restart checkpoint.

Any successor live candidate must use a new versioned source contract and
fresh immutable candidate identity, then repeat the ordinary static/package
gates, ready manifest, connected D0, and fresh F1 approval.
