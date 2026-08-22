# S22+ FYG8 P3.19 Global Consumed-Candidate Registry H0

Status: `IMPLEMENTED_REVIEW_PENDING`; host-only, no device contact, no live
authority.

This bounded unit adds the fixed
`workspace/private/consumed-candidate-registry-v1/` authority and consumes it
from the real `device_action_f1_live_v2.py` runner. The registry is an
append-only, canonical-JSON, hash-chained claim log with immutable
no-clobber records, a validated replaceable head, directory/file fsync, a
fixed writer flock, and a fixed nonblocking target-session flock. The target
flock serializes physical Download sessions but is not a candidate record and
is held across execute/recover and final health. A candidate key is derived
from stable physical target identity plus AP size/SHA and the exact
`boot.img.lz4` member identity; the full profile and approval binding remain
claim metadata, so profile renaming cannot replay the same candidate.

The activation boundary binds 42 historical completed AP transfers from their
start/result/live-result/prepared receipts and exact AP/member bytes. The
activation is pinned to the current target lock inode identities. Legacy APs
are contained under `workspace/private`, direct regular files, and bounded
link-count evidence; one known retained AP has a second private hardlink and
is allowed as a bounded alias. Missing, foreign, malformed, replaced, or
incompletely rebound evidence fails closed.

The authority axes are intentionally separate:

- `registry_capability_authoritative=true` after independent review;
- `runner_registry_consumption_proved=true` in this changed closure;
- `runner_recovery_closed=false`;
- `runner_ready=false`, `f1_authorized=false`, and `live_authorized=false`.

The runner order is: approval check, target-session lease, run transaction,
verified candidate preflight, fresh Android recheck, Download request and
endpoint identification, local attempt checkpoint, global claim, candidate
backend transfer. A claim-intent-only cut is not treated as consumed; an
active or uncertain claim is rollback-only. The exact local
`odin_local_parse_failure` with revalidated raw output and no device session
is the only append-only release. A request cut before endpoint identification
remains `BLOCKED_DOWNLOAD_REQUEST_CUT_RECOVERY`; it is deliberately not
relabelled as a pre-candidate failure and keeps ready/live authority blocked.

Hostile qualification covers fresh-process reopen and duplicate rejection,
same- and different-candidate concurrent claims, candidate-key/profile-drift
rejection, activation 42-entry/omission checks, single head-temp recovery and
multiple-temp rejection, head/record mutation, symlink/hardlink and lock
replacement, nonblocking target-session busy, exact release restrictions, and
append-stable receipt projection. The focused registry and live-runner suites
pass 59 tests; the integration suite passes 10/10 and the prerequisite suite
passes 9/9. Raw-first hostile tests pass 20/20, raw-first docs pass 15/15,
taxonomy passes 39/39, and the four common Process-v2 modules pass 126/126.
No device or backend effect is used by the qualification.

The broad `test_s22plus_fyg8_p319*.py` selection is not quoted as green: it
ran 519 tests with 517 passes, zero failures, and two errors. One error is the
deliberate fail-closed Process-v2 binding-contract drift represented by
`EXECUTABILITY_SOURCE_CLOSURE_BLOCKED`; the other is the pre-existing absent
`/mnt/android-lab-logical/vendor_dlkm/lib/modules/spu_verify.ko` materialization
input. Neither is relabelled as a pass.

The final host-only identities for this review closure are:

- registry source: 53,811 bytes, SHA-256
  `0a112d7dd2633d3465137cdb67ed4539949a3c0c0ec90b178a3ec293735dbdc4`;
- legacy 42-entry authority: 21,021 bytes, SHA-256
  `db6bd3f0218e5e53b20bec18a6a747414477134ec5008af20c15ae098c88ca7a`;
- qualification helper: 12,821 bytes, SHA-256
  `581242e3daa77a52e91acc5ce797a2ab7746f793adbb507502a552a30c3c486a`;
- private qualification `-07`: 2,964 bytes, SHA-256
  `74d52bc5b0940df6249326c1a80ae1d77dbf4dc2985390951524f64254a907a3`,
  mode 0400, nlink 1;
- raw-first auditor/`-09` receipt: 62,591/11,012 bytes, SHA-256
  `d13be6fbeaa80915ce4b76fa45e810c9c8e982044b6f6b75814d5d65c694e799`/
  `1b98a4b10dbeb56487d47074095841c9a488b963a40a3be4769e17398d4eabb8`,
  receipt mode 0400, nlink 1;
- prerequisite `-05`: 12,535 bytes, SHA-256
  `407c726764e36de4144a451aa0c48b4d188176a7d54b721b76eb67f66ef712ce`,
  mode 0400, nlink 1;
- integration `-05`: 58,553 bytes, SHA-256
  `9dd913e657e561f2ee309967a00d554880911b458d210f445c4388183d0118f4`,
  mode 0400, nlink 1.

The integration result remains `BLOCKED_P319_PROCESS_V2_INTEGRATION_H0`
with four explicit blockers: `BLOCKED_DOWNLOAD_REQUEST_CUT_RECOVERY`,
`EXECUTABILITY_SOURCE_CLOSURE_BLOCKED`, `FRESH_BASELINE_MISSING`, and
`REQUALIFICATION_REQUIRED` (four changed SOURCE_KEY entries). The global
registry blocker is absent; that does not make the runner ready.

The raw-first default path now names `-09`; `-05` through `-08` remain
preserved historical or superseded receipts and were not overwritten.

Fresh baseline, adapter SOURCE_KEYS requalification, and the Download-request
cut recovery design remain separate blockers. This H0 unit creates no D0, D1,
F1, recovery, replay, causal, candidate-success, or live authority.
