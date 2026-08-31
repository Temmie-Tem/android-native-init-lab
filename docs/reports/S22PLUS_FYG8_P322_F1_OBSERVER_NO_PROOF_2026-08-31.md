# S22+ FYG8 P3.22 F1 observer no-proof closure

Date: 2026-08-31

Target: `SM-S906N` / `g0q` / `S906NKSS7FYG8`

Formal verdict: `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`

Outcome: `p322_observer_no_proof_rollback_verified`

## Scope

P3.22 tested the fresh run ID
`c322f1e0a90b5e6d7c8a9b0c1d2e3f4b` with the boot-only candidate AP
`27279401B/ff7f189d02ba7c124ba6bc805f9a8f385bc4995fb235b5c13b4e436ae69cd412`.
The exact Magisk rollback remained
`23367721B/d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`.
The execution-critical Process-v2 closure was committed at `21ae86c7cd` and
independently reviewed `PASS_GO_P322_H0` before connected preparation.

## Preparation and one-shot execution

The first connected preparation stopped read-only at baseline classification:
the prior P3.21 retained family was still present. No reboot, Download request,
Odin invocation, partition transfer, approval, or F1 authority was created by
that stopped D0.

One attended normal Android reboot then changed the boot identity while
preserving the exact target and USB topology. The following fresh connected D0
passed with a clean baseline and created one P3.22 prepared run. One exact
approval was consumed for that run.

The candidate AP transferred exactly once. The journal retained
`candidate_flashed`, the complete bounded observation, and
`candidate_boot_ready`. The initial physical-Download wait expired before an
endpoint arrived. This did not replay the candidate or attempt rollback. The
run remained parked at its durable journal and later resumed only through
`--recover` after the exact Download endpoint appeared. The rollback AP then
transferred exactly once.

The terminal journal contains 19 records and is `CLOSED`. Candidate and
rollback transfer counts are 1/1; recovery is no longer required. Final FYG8
Android boot completion, stopped boot animation, root, boot image, supporting
partition identities, and absence of Download mode all passed.

Private terminal receipts are under
`workspace/private/runs/device-action-f1-live-v2/f1-2026-08-30T205111789065Z-1788123071789099897`.
The 10,206-byte `live-result.json` has SHA-256
`788a01498d8413410388fd9b2d4a5a5c2ada2f4257169f68cc1f839b6dc86732`.
The journal head is 276 bytes with SHA-256
`07622959b1c3cb1823ec6ad78f25adfb1154331af7518d2eac51578ccf98fab0`.

## Retained observer result

Both post-rollback `/proc/last_kmsg` reads are 2,097,136 bytes and
byte-identical at SHA-256
`3d186a2a46cdca7eed219d6a915906322d3c2da001e7380b3a75e8b52ef7b4e2`.
They contain one P3.22-family record with one valid slot and one `bad-body`
slot. The valid active value is generation 92, stage `0x8f` (143), item index
4, progress outcome, detail zero, and no payload. The adapter therefore reports
`AMBIGUOUS_INTEGRITY_FAILURE`, integrity issue
`p320-stock-envelope-shape`, and proof class `NO_PROOF_OBSERVER`.

This proves that the fresh P3.22 candidate identity booted and left a retained
checkpoint record. It does not prove that the intended 92-through-104 bridge
completed, that either 105/106 payload position published, or that the stock
observer result was complete. `candidate_success`, causal-result authority,
host-silent, MUX, and USB claims all remain false.

## Next bounded unit

Do not replay P3.22. Before building another candidate, execute one small H0
re-derivation through the actual Carrier writer rules for the first generation
92 transition and its following slot. The existing C fixture proves only the
userspace generation loop; it does not yet discriminate a kernel writer
rejection, publication error, or persistence cut that leaves the observed
valid/`bad-body` pair.

If that re-derivation identifies one deterministic first-write or second-slot
failure, P3.23 should change only that mechanism and reuse the existing
Process-v2 machinery. If it does not, stop at the retained no-proof result and
add only the minimum error witness needed to distinguish those branches. No
new device action is authorized by this report.
