# S22+ ML011: first deferred-probe phase and healthy original-A return

Status: **CONSUMED / ANDROID_CLOSED_HEALTHY**.

The exact separately approved attended operation transferred ML011 N once and
its original Android A once. First final health passed; no health-only
continuation was needed. The task is closed with no remaining F1 owner.
A90 and S20+ were not touched. No successor or replay authority is armed.

## Observed progress

The complete returned log contains **284 intact V9 records across 82 distinct
events**, with zero damaged or foreign candidates. Production projection and
an independent HMAC/domain/count/label decoder agree.

The records establish at-least-once execution inside `deferred_probe_initcall`,
return from its debugfs and first trigger calls, and entry into the phase-1
worker. Thus this candidate provides body/worker evidence beyond ML010's
pre-dispatch observation. No first-flush return, worker return, phase-2 point,
deferred-initcall return or later fixed milestone was accepted. Those absences
do not locate a stopped instruction, failed flush or reset cause.

The sparse initcall trace has entry/return records for its eight level-first
anchors and the two selected entries immediately preceding deferred probing.
It also has the pre-dispatch point for ordinal 1,793, without that dispatch's
return. This sparse selection does not reproduce ML010's full table coverage.

The device-related observations cover ten named OF-node associations and one
unlisted-OF bucket, all with entry-observed phase 1:

| Association | Accepted points |
| --- | --- |
| Eight interconnect associations | All five worker/preparation/callback points |
| Qualified SMEM association | All five points |
| Unlisted-OF bucket | All five points; identity remains unknown |
| Qualified TLMM pin-control association | Before PM-list move/bus probe, before `device_set_driver`, and before the selected callback |

For the TLMM association, each of those three pre-points has four intact
records. There is no accepted post-selected-callback or post-bus-probe record.
The exact qualified DTB identifies this catalog path as `qcom,sm8450-tlmm`.
That is a static association, not a recorded runtime driver name. The selected
callback may be the bus wrapper around the driver probe; the pre-point does
not prove entry into either callback body or the marker helper's subsequent
return. No callback success/return code is recorded.

This makes the TLMM-associated callback path a useful next source-inspection
scope. It does **not** establish TLMM as the failure cause. Static records can
come from different firmware attempts, an OF node can be shared, and later
retries within a phase are not fully observed. Duplicate counts are not boot
counts, and a complete returned log does not reveal the original write-window
capacity, latest attempt or a same-boot sequence. The operator reported physical
Download completion only; no ML011 reboot-period observation was supplied.

## USB, recovery and health

The original 120-second USB observation window expired. All **114** complete
raw snapshots show actual endpoint absence: ENOENT, empty USB fields and zero
related interfaces. This is distinct from a present endpoint without NCM.
No request was attempted. Physical RAM-userspace PID1 and authenticated USB
remain **NO_PROOF**.

The stopped owner retained its original recovery authority. After the operator
reported physical Download entry, that same owner transferred A once and
completed the first seven-read final rooted-Android health check. No candidate,
Download command, uncertain transfer or grant was repeated. The fixed retained
log read occurred only after healthy closure and between health brackets proving
the exact returned Android boot.

Preparation's earlier health snapshot had expired when the approval arrived.
One fresh invocation of the already authorized fixed preapproval D0 passed
before grant opening. The exact approval and attendance statement were saved;
refreshing that observation did not change the task or require new consent.

| Canonical event | Seconds from grant opening | Outcome |
| --- | ---: | --- |
| Live session start | 0.000 | Exact finite attended grant |
| Candidate transfer start | 15.256 | N intent, once |
| Candidate transfer complete | 16.791 | Raw transfer proof |
| Candidate boot ready | — | Not proved; USB window expired |
| Original-A transfer start | 213.362 | Existing stopped-owner recovery |
| Original-A transfer complete | 214.745 | Raw transfer proof, once |
| Rollback boot ready / session end | 261.279 | First final health and durable closure |

The return includes physical intervention and is not automatic recovery.

## Evidence and audit

The retained read acquired **2,097,136 raw bytes**, return code zero and empty
stderr. SHA-256:
`65e2fa38bbe97a0a9f7d20cfdd094767193ea8123d8dd214cbe518415d227c26`.
Offline rederivation confirms the owner, one N/A pair, terminal, raw health,
timeline and full marker projection. It verifies all **653** task capture
producers, **40** frozen execution-source records and **22** unchanged protected
proof/journal files, with acquisition, process and socket entry points blocked.
The independent decoder joins V9 event indices to the exact qualified catalog
and fresh final ELF selection. Original evidence was not edited or regenerated.

An initial offline USB inspection treated the producer's NDJSON as one JSON
object. Reading the actual producer/consumer corrected that host-only parser
assumption; the original raw snapshots were reused without another device read.

| Receipt | SHA-256 |
| --- | --- |
| Exact task | `1a1cc7e269d06eb2f9e1b0a5c682d2e16285771e7d9b7a68b75fad2102a148ec` |
| Healthy task closure | `b01fb5b32b5186c9540eb19df7e10c159fe8322569de06d8a4a549c39db1fa11` |
| Original terminal | `c5516c39037218d0c1e1d9c76d878692de81334318af7fb24e5b83b2fa3bfb11` |
| Retention result | `dec1215a432d70a5103a11063830f43e580f67f8fc015b370ceee252965b84fd` |
| Closed-run/raw audit | `8b0a49e9cd5f02897b56a4950913d2065cb90cde02e8baa6d3c0a764c750e479` |
| USB raw projection | `de586bfad9477de35ee4950cb52ed2f4aafaf449e585e43841e3122486d635bd` |

Private evidence: `workspace/private/outputs/s22plus-mainline-ml011-h0-20261030-1/`.
The [H0 report](S22PLUS_MAINLINE_ML011_DEFERRED_PROBE_H0_2026-10-30.md) retains
the artifact qualification, independent review and historical readiness
checkpoint. No execution-critical source changed during this physical run.
