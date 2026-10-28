# S22+ mainline RAM/USB experiment ML002 — 2026-10-29

Status: **CONSUMED — NO_PROOF / ANDROID_CLOSED_HEALTHY**.

The operator returned the exact finite approval and confirmed attendance and
usable physical Download recovery after the candidate and fixed preapproval
D0 health were qualified. One candidate N and one original Android A were
transferred. Final rooted Android identity and boot/supporting-partition
hashes passed. Authenticated mainline PID1/USB was not proved.

## Physical result and recovery

The original owner completed fresh preflight, Android Download entry and one
N transfer. Its 117 bounded USB2 sysfs captures all succeeded but showed the
selected device absent, with no related interface. The original 120-second
window expired. No endpoint, host network profile or authenticated socket
request was established. These are sampled observations, not a continuous
record of every bus event.

During the attempt the operator reported **repeated reboots approximately
every 8–9 seconds**, describing a boot loop. The interval is a human estimate;
the host did not measure reset edges or the boot stage. This differs from
ML001's reported unchanged screen, but does not establish ABL acceptance,
uniLoader entry, kernel/PID1 execution or a particular reset mechanism.
No further candidate action was attempted.

The operator confirmed physical Download entry while retaining attendance
and the same cable/port. The original owner validated the Download endpoint
and completed one original-A transfer. Its first health attempt failed at
`03-health` with empty stdout and an ADB target-not-found error. That incomplete
raw prefix was retained. The separately reviewed health-only continuation
obtained a fresh complete bracket and closed `ANDROID_CLOSED_HEALTHY` without
another transfer or mixing the failed prefix into the successful proof.

Offline `repair_close` rederived the original transfer/health proof with
command, socket and subprocess acquisition forbidden. The consumed records,
terminal and 15 journal rows were unchanged; the F1 owner is absent. The
connector now reports `CLOSED_BY_ORIGINAL_OWNER`. The single-operation grant
is consumed and neither N nor A may replay. Automatic recovery remains
unproved because physical assistance was used.

## Candidate and retained scope

ML002 uses the [reviewed staging correction](S22PLUS_MAINLINE_ABL_PLACEMENT_SUCCESSOR_H0_2026-10-28.md)
with a fresh RAM-canary key, identity and derived USB/network identity.
Its seven init input pins equal the retained physical init's inputs. The
prepare-4 kernel and g0q DTB are reused; no production source changed.
`ML002` is the reporting ordinal. The existing
`ml001/mainline-ram-1/mainline-ram-v1` wire capability identifiers stay fixed;
the actual run ID, payload and AP are fresh. The consumed ML001 is preserved.

The selected scope remains one boot-only N transfer, at most 120 seconds of
authenticated RAM PID1/USB observation, physical Download and one original-A
return with rooted Android health. The finite grant is one operation within
1800 seconds. Linux storage access and installed-root execution are excluded;
automatic recovery remains unproved. Native_data consistency is unobserved.

## Preparation and validation

- Built and inspected the new static ARM64 init and loader.
- The actual new loader passed 20 cases and 1,051 linked copy cases.
- All 64 normal source placements passed the entry guard; three representative
  full copies matched exactly. Maximum-selector execution also passed from
  relocation through the kernel branch, including BSS, stack, register,
  kernel/initrd-byte and FDT checks.
- Actual-EL QEMU entered at EL1/EL2 and rejected EL3 without rewriting entry
  registers. Physical entry and cache behavior remain unproved.
- Two independently repacked boot-v4/AP outputs are byte-identical and contain
  only `boot.img.lz4`, preserving the checked original-A outer envelope.
- The narrow independent candidate addendum found no issues, reused the
  unchanged 15-source staging review and current 34-source execution review,
  and bound 64 fresh/retained evidence receipts. Old review records were not
  repinned. The current admission consumer and connector bundle accepted the
  exact new artifacts and predecessor's healthy Android closure.
- The reviewed ordinary-terminal bridge is connected. Named fixed preapproval
  D0 passed identity/root/partition-digest and host checks; its raw evidence
  rederived successfully, with no unresolved F1 owner, control or transfer.
  Current health must still meet the original freshness checks at grant/effect.

Relevant past-failure rows are ABI (actual ARM64 entry/copy), ARTIFACT (exact
new identity and package joins), ROUTE/HOST (actual consumer and ordinary worker),
SEMANTIC (H0 and physical proof separation), and RETURN (original-A physical
recovery and final health). Display changes are not selected. A90, S20+ and
unrelated paused boot-journal/ABL-report work were untouched.

Prepared task SHA-256:
`640ce3911aa8cf18c86f3b40fc2ca41dc3b5c40bee80f802a7da87cb2538ca76`.
Candidate AP SHA-256:
`997c6844b68e01a529f6d0b0364a7a62313c2a700921796d3a544c588051744b`.
Candidate addendum SHA-256:
`08fa8c53be34acdb517c1a8f72f5a913f44034d2c105429baab0cbd19ef92d83`.

## Canonical timeline and retained evidence

Seconds are relative to the original grant opening. Transfer completion and
health times are the journal's raw-proved step completions; the final event
is later H0 closure publication, not the time Android first became healthy.

| Canonical event | Seconds | Evidence |
| --- | ---: | --- |
| live_session_start | 0.000 | Original finite grant |
| candidate_flash_start | 15.433 | N transfer intent |
| candidate_flash_done | 16.971 | Raw-complete N step |
| candidate_boot_ready | — | Not proved |
| rollback_flash_start | 159.794 | Original-A recovery intent |
| rollback_flash_done | 161.184 | Raw-complete A step |
| rollback_boot_ready | 281.419 | Fresh complete recovery-health bracket |
| live_session_end | 412.314 | Audited task closure |

The 682 bounded raw-capture receipts, operator observation, canonical timeline,
task close, source snapshots, test results and exact candidate/review are under
`workspace/private/outputs/s22plus-mainline-ml002-h0-20261029-1/`.
Closed task SHA-256:
`9d0dbc6b234d749ec63f4b0d9f940f271d200fc839cbf4cc299ad86dba34c738`.

The next useful unit is H0 diagnosis of this repeated-reset observation against
the exact loader/kernel/configuration and existing evidence. The staging
compatibility correction remains statically qualified, but physical progress
and reset cause are unproved. No follow-on candidate or grant is armed. Any
future proposal must account for the new observation within the existing
review/qualification rules; this report creates no new authority or gate.
