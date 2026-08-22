# S22+ FYG8 P3.19 Global Consumed-Candidate Registry H0

Status: `PASS_GO_P319_GLOBAL_CONSUMED_CANDIDATE_REGISTRY_H0_CAPABILITY_V1`;
host-only, no device contact, no live authority.

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

The 41-line Global Consumed-Candidate Registry addition to the binding common
Process-v2 contract is an explicit restrictive contract-repin, not an
incidental expected-hash update. The predecessor is 33,498 bytes,
SHA-256 `72f1eb6115872683af6a374b37267193c9c730a51698e5adf30b328b75b68d9b`
at `53af56674a7d818086d6ca2297eb903c69ef8f66`; the reviewed successor is
36,163 bytes, SHA-256
`26d9c8110e19ca4dba09418d07350cd051167423387a684f8deebf76c0843af1` at
`10cf4c25e0c7d97422b683ef925f9e18b15ace6c`. The machine-bound delta is
`+41/-0` lines and `+2,665` bytes. Existing independent review commit
`eaff1d48d32550674d12d2fa6b456444a60d20ee` records the registry and common
contract addition as independently reviewed H0 evidence. The repin is
restrictive/additive only: it adds no ready, run, recovery, F1, or live
authority and preserves the Download-request-cut blocker.

The pre-repin broad `test_s22plus_fyg8_p319*.py` selection had 532 selected
methods, but only 519 started: the 13 methods in
`P319ExperimentExecutabilityClosureTest` were suppressed by its failing
`setUpClass`, yielding 517 passes, zero failures, and two errors. The
fail-closed selector guard now mechanically proves 532 selected methods and
exactly 13 members of that class without masking its setup errors. After the
repin, the exact class runs 13/13; the new integration receipt reports source
closure PASS and remains H0-blocked only on Download-request recovery, fresh
baseline, and requalification. Fresh post-repin full selection: Ran 532 tests in 166.955s: 531 pass, 0 fail, 1 error. The sole error was
`test_independent_tmp_regeneration_is_byte_identical`, whose materialization
input `/mnt/android-lab-logical/vendor_dlkm/lib/modules/spu_verify.ko` is
unavailable. This is a fresh post-repin result, not a relabelled pass; the
pre-repin 532-selected/519-started distinction above remains historical.

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
- experiment-executability closure `20260822-01`: 96,194 bytes, SHA-256
  `6d5e14b7ed8f786b6aa99ff9d1f95e6ed99c7408b91a80c636b475fdb16bd63d`,
  mode 0400, nlink 1;
- integration `20260822-06`: 59,678 bytes, SHA-256
  `7f8f2b20babd78cc0d2529567884afa7033b697413838edde776ad8695b8cac9`,
  mode 0400, nlink 1.
- prior integration `-05`: 58,553 bytes, SHA-256
  `9dd913e657e561f2ee309967a00d554880911b458d210f445c4388183d0118f4`,
  preserved as historical evidence.

The integration result remains `BLOCKED_P319_PROCESS_V2_INTEGRATION_H0`
with three explicit blockers: `BLOCKED_DOWNLOAD_REQUEST_CUT_RECOVERY`,
`FRESH_BASELINE_MISSING`, and `REQUALIFICATION_REQUIRED` (four changed
SOURCE_KEY entries). `source_closure_pass=true`; the global registry blocker
and `EXECUTABILITY_SOURCE_CLOSURE_BLOCKED` are absent. This does not make the
runner ready.

The raw-first default path now names `-09`; `-05` through `-08` remain
preserved historical or superseded receipts and were not overwritten.

## Independent review

Independent changed-closure review of implementation commit `10cf4c25e0`
returned PASS with no actionable findings. It rechecked the lock-open TOCTOU,
head-tail cut recovery, profile/firmware key drift, strict release ownership,
foreign-claim recovery, claim-intent-only handling, legacy containment,
fresh-process/concurrent qualification, exact private receipts, and the
mechanical no-authority axes. The review resolves only topic 30. It does not
close Download-request recovery, executability, baseline, or requalification
blockers and grants no runner-ready, D0, D1, F1, recovery, replay, or live
authority.

Fresh baseline, adapter SOURCE_KEYS requalification, and the Download-request
cut recovery design remain separate blockers. This H0 unit creates no D0, D1,
F1, recovery, replay, causal, candidate-success, or live authority.
