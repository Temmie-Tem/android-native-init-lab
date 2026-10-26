# S22+ P463 host profile failure and original-A recovery

State: **CONSUMED / NO_PROOF / ANDROID_CLOSED_HEALTHY**.
The requested USB APT installation and reboot-retention goal was not achieved.
One N transfer and one physical original-A recovery completed. P463 and its
one-operation grant are closed; no native, package or control action may replay.

## Observed execution

The operator explicitly approved one attended operation within 3600 seconds,
with physical Download recovery available. Initial original-A health and
Download entry passed, then the reviewed P463 boot-only image transferred.
The host observed the selected NCM endpoint. No authenticated Debian health,
PID1, package, ordinary-reboot or automatic-return proof was acquired.

During the first host network inventory, a complete successful nmcli response
contained a valid UTF-8 Korean connection.id. The consumer decoded the entire
four-field reply as ASCII and raised UnicodeDecodeError. This was a basic host
input-handling defect missed by the preparation tests. The failure preceded
P463's sharing intent/create/activation, SSH health and host clock dispatch.
Absence of those host actions does not prove that native_data stayed unchanged:
transfer-owned native preparation could already have entered writable lifetimes.

The failing profile explicitly names a different interface from the saved NCM
endpoint. The pre-sharing snapshot places a default route on that other
interface, outside the intended USB subnet; the configured MAC and address
fields in the profile reply are empty. The label alone does not establish that
NetworkManager created or applied the profile for NCM. Six further Ethernet
profiles were listed but not inspected, and the selected-device active UUID
was never captured. No foreign profile was removed, changed or deactivated.

After the stop, the operator entered Download. The bound-port observer and
original recovery transport independently confirmed the exact endpoint. The
same owner transferred original A once and completed changed-boot Android32
health, partition checks and capacity checks. No package or native attempt was
repeated. The original terminal is ANDROID_CLOSED_HEALTHY with recovered=true;
its scientific result remains NO_PROOF.

## Actual Android health reobservation

The original-A recovery encountered the same exact target-disappeared root-read
error seen in P462. The reviewed P463 health correction retained the abandoned
four captures and selected one entirely fresh seven-capture bracket under
its original absolute deadline. The original health consumer rederives that
replacement successfully. GPT/statfs and strict after-health then completed.
Only one A transfer occurred; no separate health continuation was dispatched.
This is actual device evidence for the bounded health correction, not evidence
for the failed APT workload.

## Post-closure filesystem observation

Before changing any execution source, the existing fixed baseline D0 profile
read the native_data superblock and checked same-boot Android health before and
after. The strict reader rejected the result because the journal needs-recovery
feature bit is set: M=40, incompat=0x2c6 rather than clean 0x2c2. CRC32C and the
other fixed superblock checks pass. Android health and its reported Android32
capacity remain valid.

This is not a clean or complete filesystem admission. Current package files,
databases and historical run-file contents remain unobserved. No journal replay,
filesystem repair, cleanup or additional N transfer was performed. A successor
needs separately reviewed recovery/current-root evidence and its own finite
attended authority before another writable Debian experiment.

## Prospective host correction

The [foreign-profile consumer](../../workspace/public/src/scripts/revalidation/s22plus_debian_apt_access_v1.py)
now splits the bounded response into byte lines, retains the exact four-field
check, decodes only connection.id as strict UTF-8 and keeps interface, MAC and
address fields strictly ASCII. Existing name/interface/MAC ownership checks,
subnet rejection and selected-device active-owner checks remain mandatory.
Changing LC_ALL would not rewrite a stored connection label.

The [regression tests](../../tests/test_s22plus_debian_apt_v1.py) exercise the
real configure_network path with Korean/accented/colon/Unicode-separator labels,
invalid encodings and field counts, each ownership conflict, overlapping or
malformed addresses, and an already owned selected device. Python compilation
and the 15-test APT suite pass. Independent review passes six focused network
fixture tests and 15 actual-capture/negative probes, including the preserved
failing response. That response advances only to the next uncaptured read;
it does not establish that every host profile or a future NCM owner is valid.

This correction is H0 only. Consumed images, reviews, task, grant, source
snapshots and raw evidence retain their original pins. The old capability
correctly rejects the changed source; it is not silently repinned or reused.
No new physical artifact, recovery capability or grant is activated here.

## Timeline and evidence

Seconds below are relative to the original grant opening. The last event is
task-close publication after the device recovery had completed.

| Canonical event | Seconds | Evidence |
| --- | ---: | --- |
| live_session_start | 0.000 | Original finite grant |
| candidate_flash_start | 192.659 | N transfer intent |
| candidate_flash_done | 194.259 | Raw-complete N transfer |
| candidate_boot_ready | — | Not proved |
| rollback_flash_start | 612.864 | Original-A recovery intent |
| rollback_flash_done | 614.257 | Raw-complete A transfer |
| rollback_boot_ready | 661.974 | Android recovery health complete |
| live_session_end | 889.486 | Audited task closure |

The 14 journal records and 519 bounded raw captures remain unchanged. Private
run, source and diagnosis evidence is under
`workspace/private/outputs/s22plus-debian-apt-p463-h0-20261027-1/`.

- Prepared task: `835ad250d473dab358e73c6ae94414429a8daa27896d45accafaaf800749db24`.
- Closed task: `52282e4bbb8954c51ed9936a4df7c61a3276b21e4c2de349bd624abfa95d96dd`.
- Actual health reobservation proof: `9be92856ce99b877739ef440cc6a82c1ddd6c17a7ede32416e146db38cdf2fe3`.
- Post-return superblock analysis: `085859f432e76a9cef79baebcbbea853562924c823303753652de58b6153ab74`.
- Independent H0 correction review: `87128c263627dd0bde79eb4397c7ef7e9bf8df8db7a6c99f872e92cd95246259`.

[Preparation](S22PLUS_DEBIAN_APT_P463_PREPARE_2026-10-27.md) remains its original
pre-execution record. A90 and S20+ received no command in this operation.
