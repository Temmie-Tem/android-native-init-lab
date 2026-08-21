# A90 candidate-return continuation — H0 implementation report

Date: 2026-08-21
Target: Samsung Galaxy A90 5G only
Tier: H0 host-only
Status: implemented, production backend disabled

## Result

The candidate-neutral continuation is implemented in
`workspace/public/src/scripts/server-distro/a90_f1_candidate_return_continuation_v1.py`.
It provides only fixed `prepare`, `resume`, and `finalize` modes. `prepare`
derives a fresh token without contact or journal writes. The core resume and
finalize state machine uses exact owner records, receipt joins, guards, strict
candidate/TWRP observations, intent-before-contact ordering, physical-action
confirmation only for the TWRP branch, and the existing one-shot rollback.

The production backend is intentionally not part of this H0 unit and
`LIVE_EXECUTION_ENABLED = False`; no CLI resume or finalize can contact a
device. A separately reviewed backend must bind the fixed inventory and TWRP
identity grammar before activation. No review JSON was added to the execution
closure.
On candidate PASS, the owner releases only the active-run guard; the
candidate-SHA guard remains present as the durable consumed no-replay marker.
Candidate and rollback health validation now requires the exact
manifest-bound qualification-review digest in `recoveryEvidenceSha256`; a
valid mismatched digest parks with no PASS or rollback-success terminal.
TWRP identity validation is exact-key/exact-type before equality and rejects
numeric bool/float/string substitutions without issuing a physical instruction.
Rollback now revalidates both guards after durable `31`; removing either guard
before flash results in zero backend effect calls and a no-replay park.
Continuation execution now leases both direct review identities/SHAs and the
continuation computed closure, revalidating around contacts, journal writes,
rollback, and the owner terminal release callback; same-byte swaps of either
review are rejected.
The qualification-review SHA is explicit in approval/intents without entering
the continuation execution closure, avoiding a self-reference cycle.
The owner terminal path now reopens and strictly validates durable `40` before
active-guard release; mutation, deletion, symlink, short/extra/duplicate, or
read failure retains guards and does not republish or retry.
The consumed H28 qualification review remains pinned at its original closure
`0dca4f3ddc98eb4625411c93ad7c1748f3c016aab0075a570652ca946fc4eb1f`; the current owner rejects it for a new run. H28
terminal-only readers validate the fixed historical review/manifest/journal
bytes (including review SHA-256
`51474c2d323971c07ca1425be613ea48cdd6c13f870606b166fba76835e6a9b2`)
without turning them into current qualification. A future H29 requires a
fresh qualification/review/manifest and current owner closure.

## Validation

- continuation/owner focused suite: `147/147` passed (the suite includes the
  shared owner regression corpus); standalone owner/adapter/receipt/recovery
  suite: `98/98` passed;
- `test_native_init_flash`: `40/40` passed;
- qualification plus H27/H28 recovery readers: `106/106` passed (7 H28
  qualification, 12 H27 pretransfer, 8 H27 postrollback, and 31/27/21 for
  the physical/slow/menu H28 readers);
- `py_compile` passed for the continuation and owner modules;
- `git diff --check` passed.

## Boundary

Device, `/dev`, USB, network, `workspace/private`, S22+, and S20+ access were
zero. No image, reboot, physical instruction, rollback, candidate transfer,
approval token, ordinal, or live authority was created. No commit was made.
