# P342 idle/reuse preparation

P342 is now CLOSED and healthy with
`PASS_F1_V2_P342_AUTHENTICATED_IDLE_REUSE_AND_ROLLED_BACK`.
Candidate and exact rollback completed once each. P342 and P341 are consumed,
never replayable. The preparation sections below preserve their original scope.

## Experiment

Keep P341 host-first OPEN and device behavior, changing only fresh identity.
Run two authenticated sessions, retain the same FD for 120 seconds of silent
idle, run a third session, then one planned close/reopen and a fourth session.
There are twelve fixed commands total. The existing 300-second observation
deadline also bounds the idle and each exchange. Unexpected idle bytes, EOF,
authentication or reopen failure stop without replay. No arbitrary shell,
PTY, later-action lease, persistence or autonomous mode control is enabled.
Exact boot-only Magisk rollback and healthy rooted FYG8 return remain required.

## Artifacts and host qualification

- Final build: `workspace/private/outputs/s22plus_fyg8_p342/stock-candidate-build-v1-20260905-02`.
- Result: 82774 bytes, SHA256 `9868c30c966ecd308f680f51f79d7715aa8151e319efada475efc4f7f1185a7b`.
- A/B AP: 28631081 bytes, SHA256 `76e23db43ce8e73711fc5a7b28c35ceebab8a5081687c2d4c6a19ce3bed5f83b`.
- Rollback: 23367721 bytes, SHA256 `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`.
- Run ID: `c342f1e0a90b5e6d7c8a9b0c1d2e3f9b`.
- Public manifest: `workspace/public/src/device-action/manifests/s22plus_fyg8_p342_process_v2_ready_1.json`.
- Manifest: 13313 bytes, SHA256 `08e91eb8f01498b169cb9730db0ad73796951505e4e6de1eb4862c1f7b9ba2c9`.

Independent H0 review passed the artifact and common execution integration.
Focused idle tests 9/9, artifact tests 15/15, process tests 3/3 and live tests
7/7 pass. A real-clock host PTY rehearsal retained 120.032 seconds of idle;
this is host evidence, not proof of device idle stability. Live tests exercise
actual producer/parser, partial capture/publication/reopen, four-session proof,
deadline and final rollback projection paths. P341 historical CLOSED decoding
was separately preserved; its old binding was used only as a nonexecuting fixture.

Two host defects were caught before code issuance. The P342 raw classifier now
binds the fresh run ID before parsing instead of relabeling predecessor output;
CRC-valid predecessor evidence is rejected. Historical P341 semantics are not
rewritten. Real four-session proof plus supplemental Carrier projections can
make CLOSED state 33084 bytes, above the old 32768-byte writer bound. Only exact
P342 `live-state.json` now uses the existing 65536-byte atomic writer. Other
campaign states and journals retain their bounds; schemas and capture limits
are unchanged. Independent `PASS_GO_P342_STATE_BOUND_H0` covers live source
SHA256 `fab122a55ce299d203f8965af7fc91f862ad27bc9c4b6fc57a7367b3a59f0341`.

## Connected preparation

Initial bounded D0 found retained evidence-family markers. The preapproved
normal-reboot D1 ran exactly once and returned the same target with a changed
boot ID, rooted FYG8 health, expected partition digests and no Download endpoint.
Other attached targets received no command. Linked result:
`workspace/private/runs/device-action-d1-p342-baseline/p342-normal-reboot-20260905-1-result.json`,
2963 bytes, SHA256 `241302ac66acf04432718dc7cdc9377c814490e660037fdec4be3c33913e7b80`.

First ordinary D0 preparation `p342-ready1-prepared-20260905-1` passed clean
baseline but was superseded by the state-writer source correction before any
code was issued. Its immutable evidence remains, with zero candidate/rollback
transfers. Fresh preparation uses `p342-ready1-prepared-20260905-2`; it does not
repeat D1. The ledger records preparations, not a premature F1 closure.

Final prepare-2 reopened successfully: prepared 30968 bytes/SHA256
`16723242bc7a41d1c07409ea2a75f65845e7bbf701b793ddbb75e9936bc10378`,
preflight 3261 bytes/SHA256
`a049f3353af78bec052568e348d565fa8adc9b11b77379d7ec0f54890d6f6f71`.
The baseline has zero exact and family markers. Current boot, serial and
topology match D1's returned values. No transaction exists. Independent review
`PASS_GO_P342_PREPARATION_LEDGER_H0` verified the five appended H0/D0/D1 rows
against retained bytes and reparsed the ledger with its previous prefix intact.

Fresh returned approval is still required before F1. Physical Download handling
may be required for rollback; automatic recovery and indefinite residency are
not claimed by this preparation.

Final raw-first audit passed over 1909 Python files and 422 subprocess modules.
Receipt: `workspace/private/outputs/s22plus_fyg8_p342/raw-first-current-20260905-1.json`.
Auditor SHA256: `8d64aff30066e8e064fbb0b292116d0e703d763ed6105c52658084ce16638c63`.
Existing census metadata was updated for the reviewed P340-P342 sources,
the consumed P339 health helper and two explicitly separate S20 files; no
wildcard exclusions, operational changes or device authority were added.

## F1 outcome and reporting-cut repair

Run `p342-ready1-prepared-20260905-2` accepted four authenticated sessions and
twelve fixed command executions. Same-FD silent idle measured 120.000105308
seconds with zero received bytes, followed by a third same-FD session and one
planned reopen/fourth session. This proves this bounded idle/reuse experiment,
not indefinite stability, arbitrary shell or standing autonomous control.

Candidate receipt: 35488 bytes/SHA256
`ee91e9fa032f4eaa011578c942688a051621d92deb8f8caa64991d441c7a72be`.
RX: 2644 bytes/SHA256
`ce3ce11876dbfcea4077974b14ddd0399fddbf9e4fa5515ef4fd438e877fa678`.
Both boot-only transfers completed once. Rooted FYG8 health, exact expected
partition digests, current target continuity and two identical final logs were
captured before a host classification exception. A P319-only stock projection
assignment was incorrectly dedented, causing `UnboundLocalError: stock_rows`
in the common classifier for P342. This is a host reporting defect, not a USB
failure. Earlier tests covered adapter classification and final routing but
missed this real common-classifier connection; the new regression exercises it.

Independent `PASS_GO_P342_RETAINED_HEALTH_FINALIZER_H0` qualified the exact
private helper `workspace/private/outputs/s22plus_fyg8_p342/finish_retained_health.py`
(SHA256 `56142a8d7076d104aa4d5fac267f8a8f529414b6fb7d1641f6c9adf4f9144bef`).
It reopens raw health captures 19-22, final identity 25-26, EOF logs 23-24 and
Download-absence receipt 31; original health and final-observer validators pass.
One exact in-memory indentation repair permits retained classification.
The only backend method returns that retained result; no device operation is
available. The normal post-rollback state machine completed the journal and
result without repeating any device effect. The permanent fix is the same
one-line indentation change. Actual common-classifier regression failed with
the original exception before the fix; all eight focused live tests pass after.
Supplemental Carrier remains NO_PROOF_OBSERVER, separate from the accepted USB
primary proof. No supplemental scientific/causal result is promoted.

Final state: 31802 bytes/SHA256
`005635a19623edb9d06707be42ae2d530d58eb9af0eb3c4bf2d75d7fd7fe989b`.
Final result: 35666 bytes/SHA256
`0136a663965b29114221605c8da58b32b1f0a5a5f6c67c4229beabdb9581cf92`.
Journal CLOSED/19; outcome `p342_authenticated_idle_reuse_rollback_verified`;
`recovery_required=false`. No other target received commands.

Canonical journal timeline (UTC):

| Event | Time |
| --- | --- |
| Live start | 09:56:40.059230 |
| Candidate transfer start / complete | 09:56:55.900575 / 09:56:57.520676 |
| Candidate observation accepted | 09:59:11.654062 |
| Rollback transfer start / complete | 09:59:58.386321 / 09:59:59.918138 |
| Retained health finalized | 10:06:00.567213 |
| Closed | 10:06:00.593288 |

The last health event is reporting finalization time, not a newly issued read.
The original private captures retain the actual acquisition timings.
