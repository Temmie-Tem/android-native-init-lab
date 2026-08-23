# S22+ FYG8 P3.19 Download-request cut recovery H0 implementation

Status: `PASS_GO_P319_DOWNLOAD_REQUEST_CUT_RECOVERY_H0_CAPABILITY_V1`.

This bounded unit contacts no device, ADB, USB, Odin endpoint, A90, or S20+.
It creates no ready/run/approval manifest and grants no D0, D1, F1,
recovery, replay, causal, candidate-success, or live authority.

## Implemented boundary

The real `device_action_f1_live_v2.py` recovery owner now consumes the durable
journal, `candidate-download-request-intent.json`, target-session lease,
endpoint lease, global registry evidence, and the preapproved rollback owner.
After request intent publication, recovery never calls `request_download`,
continues the candidate, creates a candidate claim, or synthesizes a candidate
attempt. It passively observes the current endpoint once per recovery
invocation. An exact endpoint permits only the existing rollback transfer and
final health path.

The adapter is `device-action-f1-live-v2-8`. The request intent is version 2
and binds the full eleven-field candidate identity rederived from the prepared
manifest, AP-member receipt, and approval binding. Execution publishes the
request intent, asks for Download, claims the global candidate identity, and
only then begins the local candidate attempt. A cut after the claim intent but
before its result therefore has no candidate attempt or candidate transfer.

Absent, ambiguous, foreign, stale, malformed, indirect, and partial request,
endpoint, registry-intent, and recovery-receipt evidence becomes a durable
`RECOVERY_DOWNLOAD` parked result. It is never relabeled
`FAIL_F1_V2_PRE_CANDIDATE_DOWNLOAD`. A claim-intent-only cut follows the same
recovery-only rule and leaves the global registry without a candidate claim.

The parked outcome is an append-only journal checkpoint. Once it exists, a
later recovery call does not observe the endpoint again. If an exact endpoint
was recorded but the host cut before rollback began, recovery performs one
fresh endpoint revalidation; a failed revalidation is also written once as an
append-only parked checkpoint and is not retried automatically.

The journal has a distinct rollback-only timeline:

`live_session_start -> rollback_flash_start -> rollback_flash_done -> rollback_boot_ready -> live_session_end`.

It is separate from the ordinary candidate timeline, so recovery cannot satisfy
the journal by inventing a candidate event. Request-cut ownership is rejected
once candidate-attempt evidence exists, leaving ordinary consumed-candidate
recovery unchanged. The exact endpoint fixture closes through rollback and
final health as
`NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`; the parked fixtures remain
`RECOVERY_REQUIRED_F1_V2_ROLLBACK_NOT_VERIFIED`.

## Host-only validation

Focused validation passes:

- journal core: `24/24`;
- live runner: `65/65`;
- integration qualification: `11/11`;
- combined: `100/100`.

The integration qualification binds the exact fixture, live-runner, and
journal-core source bytes before execution, executes seventeen named fake-backend
fixtures, then proves those three sources remained byte-identical. The fixture
set includes exact endpoint rollback plus final health, fresh-module-state
recovery, rollback and final-health cuts that resume without candidate-side
inputs, one-shot endpoint revalidation, durable request ordering and no
replay, a claim-intent-only cut with zero claim and zero candidate attempt,
an active global claim cut before local attempt, uncertainty parking that
survives later request-intent loss, malformed
endpoint/request/claim evidence, full claim-metadata drift, rejection of any
candidate-attempt artifact after a request-cut transition, and target-session
lease enforcement.

The repository-wide raw-first audit first rejected the newly committed dormant
S20+ health source. The repair adds that exact filename only to the
target-external pre-boundary membership set, increasing the membership count
from 51 to 52; S20+ bytes remain unfrozen and ordinary S20+ edits do not alter
the S22+ semantic projection. The changed S22 journal core and live runner are
rebound in the frozen S22 inventories and active source map.

New no-clobber private successors are:

- raw-first `20260823-02`: `11,012B`, SHA-256 `d84487138f45f8dadba2be1b8470d77e91331ff0fa810fbde2137089c6d67880`;
- registry `20260823-02`: `2,964B`, SHA-256 `2dfec77ad45bf318d1aee22bf21c2bba66d351ea4a43c1b22feff1cc6c323ff2`;
- prerequisite `20260823-02`: `12,528B`, SHA-256 `4785343654809f5f01c8c055e280102eb2dd834bd6ce2cc1378ce24dee3bec5c`;
- integration `20260823-02`: `61,592B`, SHA-256 `b376a2c5523335c203df042e30ad8b4eaf08b21e5c8036eecbc67f8ae2712258`.

All four are mode `0400` and link count 1. The integration component runs all
seventeen selected fixtures with zero failures/errors, sets
`runner_recovery_closed=true` and
`download_request_cut_recovery_blocked=false`, and remains authority-free.

## Review and integration state

An independent Luna MAX changed-closure review returned `PASS_GO` with no
load-bearing finding. It verified the real journal/live/integration closure,
the claim-before-attempt order, durable parked outcomes, rollback-only cut
resumption, target-session lease, seventeen bound fixtures, and all four exact
private successor identities. The append-only review row resolves only topic
32 and changes full-tail accounting from 50/35/15 to 50/36/14.

An Ox Alpha reviewer trial produced no verdict after repeated no-progress and
was stopped; it is not review authority for this unit.

The machine integration result removes only
`BLOCKED_DOWNLOAD_REQUEST_CUT_RECOVERY` and remains
`BLOCKED_P319_PROCESS_V2_INTEGRATION_H0` on exactly:

1. `FRESH_BASELINE_MISSING`;
2. `REQUALIFICATION_REQUIRED` for four candidate-qualification source keys.

The scoped review does not remove either remaining blocker or create a
ready/run/approval manifest.

Ready, run, approval, D0, D1, F1, live, replay, causal, and candidate-success
axes remain false. Runtime evaluability witnesses remain
`PENDING_FRESH_CANDIDATE_RUN`; that is a post-run causal-classification gate,
not a new pre-live authority.

No prior receipt or A90/S20+ file was overwritten or edited by this unit.
