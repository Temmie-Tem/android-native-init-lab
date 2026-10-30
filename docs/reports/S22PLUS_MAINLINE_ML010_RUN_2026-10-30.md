# S22+ ML010: regular-initcall trace and healthy original-A return

Status: **CONSUMED / ANDROID_CLOSED_HEALTHY**.

The separately approved attended operation transferred the exact ML010 N once
and its original Android A once. First final health passed without a health-only
continuation. The owner is closed; no successor or replay authority is armed.
A90 and S20+ were not touched.

## Observed progress

The complete returned log contains **12,208 intact V8 records across 3,590
distinct events**. Production projection and an independent raw decoder agree.
All three early milestones are present: before basic setup, after `driver_init`,
and before regular-initcall command-line allocation, with four records each.

The regular events form an exact contiguous prefix: entry and return records
for zero-based ordinals **0–1,792**, followed by the entry record for ordinal
**1,793**, the **1,794th regular table entry**. The fresh final Image/ELF table
resolves that last observed entry to **`deferred_probe_initcall`**, at level 7
(`late`). The preceding entries include:

| Zero-based ordinal | Function | Intact entry records | Intact return records |
| --- | --- | ---: | ---: |
| 1,791 | `boot_wait_for_devices` | 2 | 2 |
| 1,792 | `sync_state_resume_initcall` | 2 | 2 |
| 1,793 | `deferred_probe_initcall` | 2 | 0 |

There is no accepted return record for ordinal 1,793, no accepted regular
record for ordinals 1,794–1,824, and no post-basic/post-initramfs-wait/post-async
milestone. Six damaged or incomplete candidates are rejected; there are no
foreign-candidate records. No partial-body evidence class is used.

This establishes the named recording point before `deferred_probe_initcall`
dispatch during at least one ML010 attempt, and observed return points for the
preceding 1,793 dispatches. It does **not** prove entry into that callback body,
the last recording helper's subsequent cleanup/return, successful return codes,
driver matching, completed probes, userspace PID1 or USB. Records may come from
different attempts; their duplicate counts are not boot counts or a same-boot
sequence. The missing return cannot identify that function as the failure
location or cause. It also cannot explain an older candidate's missing record.

The exact source function enables and triggers deferred probing and contains
two `flush_work(&deferred_probe_work)` calls. This is useful source context for
a prospective H0 investigation of deferred work and dependency paths; neither
flush, a callback within that work, nor a timeout/reset cause was observed by
this trace. No ML010 reboot-period observation was supplied by the operator.

## USB, recovery and health

The original 120-second USB window expired. All **114** complete raw USB2
snapshots rederive actual endpoint absence: ENOENT, empty USB fields and zero
related interfaces. This is stronger than merely finding no NCM interface on
a present endpoint. No socket request was attempted. The separate mainline
RAM-userspace-PID1/USB result remains **NO_PROOF**.

The owner stopped after the timeout. The operator then reported physical
Download entry. The existing owner performed its original one-shot A recovery;
no new grant, candidate attempt or uncertain transfer was repeated. The first
seven-read final rooted-Android health passed. `ANDROID_CLOSED_HEALTHY` and
no remaining F1 owner were confirmed before the fixed retained-log read.

Preparation's earlier health snapshot had expired when the exact approval was
returned. One fresh invocation of the already authorized fixed preapproval D0
passed before grant opening. It changed no control or partition state and did
not require another human approval. The saved approval and physical Download
confirmation remain exact private human records.

| Canonical event | Seconds from grant opening | Outcome |
| --- | ---: | --- |
| Live session start | 0.000 | Exact finite attended grant |
| Candidate transfer start | 15.381 | N intent, once |
| Candidate transfer complete | 16.903 | Raw transfer proof |
| Candidate boot ready | — | Not proved; USB timeout at 135.302 |
| Original-A transfer start | 405.705 | Existing stopped-owner recovery |
| Original-A transfer complete | 407.100 | Raw transfer proof, once |
| Rollback boot ready | 454.642 | First final health passed |
| Live session end | 454.642 | Durable healthy closure |

Android Download intent occurred at 2.733 seconds. The interval before A
included the required physical intervention; it is not automatic recovery.

## Evidence and audit

The fixed post-closure D0 acquired **2,097,136 raw bytes**, producer return code
zero and empty stderr, between health brackets proving the exact returned
Android boot. The raw SHA-256 is
`22580e072483fb101f3fd376114c91fbd5aba1f088ebae7e5c9f3abace0fc1c7`.

Offline rederivation confirms the closed owner, exact N/A effects, terminal,
canonical timeline, raw health and complete retention projection. It verifies
all **622** task capture producers without failure, **39** frozen execution
source records and **22** unchanged protected proof/journal files. Acquisition,
subprocess and socket entry points were blocked during the audit. The independent
decoder checks the V8 domain, candidate, table count, reserved bytes and HMAC,
then joins ordinals to the final qualified Image table. Original raw evidence
and consumed records were not edited or regenerated.

| Receipt | SHA-256 |
| --- | --- |
| Exact task | `627522f1247ee96ec32cf700a22ff7407c0f53014b3baaf3b44868a6477477d8` |
| Healthy task closure | `524468c820dd1048a8353adf6befc8f4053c1ccf052c3d03916848c1db71d027` |
| Original terminal | `ffd69d65ac78da8d3769b3e1e718cca69d158e9163196fe42c13c06b4400639c` |
| Retention result | `5dd0e37de375fd2bb3cd3cd0cdf5b41d8e490d21df4c673e31c48d38025637bb` |
| Closed-run/raw audit | `cbecb6613878e861aaea893ca4c8402b7a2040709397372cd634b3bd863d178b` |
| USB raw projection | `53d13f5e7ff3bf910e7ac1d2120ce81b6a874eb644bd8795a12ded9290c7c758` |

Private execution/evidence:
`workspace/private/outputs/s22plus-mainline-ml010-h0-20261030-1/`.
The [H0 preparation report](S22PLUS_MAINLINE_ML010_CONSOLIDATED_TRACE_H0_2026-10-30.md)
retains the artifact qualification, independent review, timing limits and
historical readiness checkpoint. No execution-critical source changed during
this physical operation. This closure grants no further experiment.
