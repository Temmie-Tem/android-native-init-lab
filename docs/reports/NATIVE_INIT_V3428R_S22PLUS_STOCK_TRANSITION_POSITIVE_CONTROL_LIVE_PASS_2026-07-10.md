# V3428R S22+ Stock Transition Positive Control Live Pass

## Verdict

`PASS_STAGE_A_AND_CROSS_SESSION_RETENTION`.

The stock/Magisk-origin positive control closed the collection-sensitivity and
cross-session retention prerequisite for the V3426 direct-PID1 phase observer.
An exact run-bound PRECHECK+FINAL pair was absent at baseline, armed and verified
in the current ring, preserved through attended manual RDX/Download plus a
boot-only Magisk identity rollback, and recovered unchanged from the first
rollback boot's `/proc/last_kmsg`.

This result validates the observer and transition. It does not claim that a
future direct-PID1 candidate reaches Stage A.

## Pins And Review

- Target: `SM-S906N/g0q/S906NKSS7FYG8`
- Helper SHA256: `b42c98c8bde0821b899015ab2524feec74b0e9cecb08a1bc72896353c5236c67`
- Pre-live helper commit: `a2c4e807`
- Observer contract: `cba82ce1bae23f56bcad57876f5d647e31a37a36d7bc9b477de57b1f85b3babf`
- Transition contract: `426aa2bb50f6e73e153f5f5dc9cde59ddf37ab315f46860c1dc0bd0b3e810734`
- Magisk boot-only AP: `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`
- Focused validation: 49 tests PASS
- Connected read-only dry-run: PASS
- Persistent Claude Opus session: `10a19d6c-d0ef-4659-af34-dfd6472c7eb6`
- Pre-live identity-delta review: GO
- Post-live evidence audit: `PASS is WARRANTED`

## Live Run

Private evidence:
`workspace/private/runs/s22plus_v3428r_stock_transition_20260710T102349Z/`.

- Run ID: `de3b50b0734fdd418b732bf76d5d788d`
- Schema: `s22plus_v3428r_stock_transition_positive_control_v1`
- Live start: `2026-07-10T10:23:49.209243Z`
- Quiet-transition start: `2026-07-10T10:23:50.566755Z`
- Manual transition elapsed: 125.229114 seconds
- Rollback flash start: `2026-07-10T10:26:01.427995Z`
- Rollback flash done: `2026-07-10T10:26:02.966719Z`
- First rooted boot ready: `2026-07-10T10:26:38.116192Z`
- Live end: `2026-07-10T10:26:39.010139Z`
- Candidate flash: none
- Magisk identity rollback: Odin rc=0
- Stock fallback: not entered
- Timeline: complete, all eight canonical phases plus three no-candidate semantics

## Marker Proof

Baseline `/proc/ap_klog` was 2,097,136 bytes and contained no current-run marker.
The PRECHECK snapshot contained exactly one valid PRECHECK. The FINAL snapshot
contained exactly one valid PRECHECK followed by exactly one valid FINAL. Both
used the expected run ID, module SHA, contract SHA, V3428R-derived context SHA,
embedded sequence, and CRC; all issue and foreign-marker counts were zero.

On the first rollback boot, both complete `/proc/last_kmsg` reads were 2,097,136
bytes and had identical SHA256:

```text
07ac07fbf25bbe642c4085da9a1b55662c0e79c03c9ce7d6a2940d106359497e
```

The retained snapshot contained the exact same PRECHECK and FINAL identities in
embedded sequence order. The PRECHECK-to-FINAL byte gap was 1223 bytes in both
the current-ring and retained snapshots. The classifier reported no malformed,
unframed, duplicate, foreign, identity, CRC, or ordering issue.

## Final Device State

The first rollback boot and a separate post-run check both found:

- model/device: `SM-S906N` / `g0q`
- bootloader/incremental: `S906NKSS7FYG8`
- `sys.boot_completed=1`
- `ro.boot.verifiedbootstate=orange`
- Magisk root: healthy
- boot SHA256: `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`
- Odin endpoint: absent after normal Android return

## Interpretation And Next Gate

The positive result is conclusive for this stock-origin run: the exact pair was
created after a clean baseline and survived into the next Linux session's
`last_kmsg`. It establishes that later absence from a direct-PID1 experiment is
not automatically evidence that this collection path is insensitive; absence
must still follow the V3427 `NO_PROOF` rule because Stage A reach and transition
loss remain hidden without a positive pair.

The next bounded unit is host build and review of the direct-PID1 observer
candidate using the validated V3426 contract. Any live candidate needs a new
SHA-pinned one-shot exception and explicit approval. V3428R is retired.
