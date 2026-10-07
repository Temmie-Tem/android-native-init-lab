# P417 first run: no early proof; original Android recovered healthy

Date: 2026-10-08 KST. Target: only `SM-S906N/g0q/S906NKSS7FYG8`.
Candidate: P417 `v0.5.0-rc.1`, the separately reviewed
[Debian-owned early boot](../operations/S22PLUS_DEBIAN_EARLY_BOOT_V1.md).

## Result

P417 consumed one attended candidate transfer. The exact candidate USB evidence
endpoint was not detected within the fixed 90-second host wait. The owner stopped
with `TimeoutError` before opening the early evidence channel or transmitting
its challenge. Scientific result: **NO_PROOF** for Debian early PID1, module
preparation and protected metadata observation.

The operator entered physical Download. One original-A transfer completed,
followed by final **ANDROID_CLOSED_HEALTHY**, `recovered=true`. Candidate and
rollback transfer totals are exactly **N=1, A=1**. The candidate and finite
grant are consumed and closed, with no pending F1 owner.

The fixed host observer did not detect the selected endpoint before its
90-second deadline. It does not locate a failure in Debian `/init`, module loading, UFS,
parent measurement or gadget setup, nor prove non-execution, reboot, panic,
power state or thermal health. No authenticated RAM record was acquired.
The RAM-only record is not recoverable by an authorized post-return reader in
this profile. Hardware insertion, protected metadata and early Debian PID1
remain unproved despite the separate successful H0 VM tests.

No native_data mount, repair, journal replay, RO clear, filesystem-data write
or installed Debian execution was selected. This trial supplies no new
native_data superblock observation; P415 remains the last authenticated dirty
superblock evidence. Original Android recovery is a separate positive result.

## Execution and recovery evidence

The exact returned 1800-second/one-operation attended grant bound the qualified
boot-only AP, current reviewed sources, operator target and original A. Fresh
Android preflight passed before Download control and candidate transfer.
The candidate transfer intent owned all automatic preparation, and no later
preparation or observer request was replayed after the endpoint timeout.

The physical return used the existing measured Download identity and original
boot-only recovery artifact. The first post-A health attempt lost ADB during
its fixed health reads: one command returned `adb: device ... not found` with
status 1. Its raw evidence remains intact. The original A transfer was already
proved, so continuation reconstructed that transfer and performed only a fresh
fixed health observation. There was no second A transfer or additional control.

Final health proves exact original boot and supporting-partition digests,
root, a changed Android boot identity, complete Android32 GPT, native_data
partition presence and **34,357,624,832-byte** userdata capacity. All required
before/after health and storage checks passed on that final observation.
A90 and S20+ received no commands or transfers.

## Canonical timeline

Seconds are host BOOTTIME elapsed from the original grant, not a measurement
of target execution duration. `candidate_boot_ready` is explicitly unproved.

| Seconds | Canonical event / evidence |
| ---: | --- |
| 0.000 | `live_session_start`: exact attended grant opened |
| 36.774 | Fresh original-A preflight complete |
| 36.932 / 38.716 | Android Download intent / completion |
| 50.818 | `candidate_flash_start`: sole N transfer intent |
| 52.326 | `candidate_flash_done` |
| 52.373 | Fixed early endpoint observation starts |
| 142.437 | Observation timeout; `candidate_boot_ready` remains unproved |
| 216.049 | `rollback_flash_start`: sole original-A transfer intent after physical Download |
| 217.436 | `rollback_flash_done` |
| 217.447 | First post-A health observation begins; later ADB read fails |
| 333.582 | Health-only continuation begins; transfer intents unchanged |
| 337.333 | `rollback_boot_ready`: full rooted Android32 health complete |
| 543.397 | `live_session_end`: H0 audit and finite-grant closure |

## Provenance and closure

The [preparation report](S22PLUS_DEBIAN_EARLY_P417_H0_2026-10-07.md) records
actual A/B artifacts, ARM64 producer/consumer tests and independent `PASS_GO`.
The run used the reviewed working-tree source snapshots over base commit
`10eeb2cee2cfb42da74026d800b3ad3ad2114a7e`; that base commit alone is not the
execution-source identity. The frozen host/build manifests and generated seals
retain the actual source and artifact provenance without repinning old runs.

Private evidence root:
`workspace/private/outputs/s22plus-debian-early-p417-h0-20261007-1/`.
The approved task remains at `connected-2/task/`, and the consumed run remains
at `connected-2/task/operation-0001/`. Driver results, the original recovery
read failure, raw captures and source snapshots were preserved in place.

H0 closure revalidated both streams of **564 operation captures**, all
**219 unique frozen source paths**, initial/final Android proofs, both transfer
proofs and the permanent consumed claim. It classified the single failed raw
health command separately. With command acquisition blocked,
`Session.repair_close` reproduced the terminal without changing any of the
**15 journal rows** or terminal bytes.

| Record | SHA-256 |
| --- | --- |
| Terminal | `7b0f1bdcfb8816729d5407d39f9989deada416a4cd9377f0b54c84e89d37ef19` |
| Closure audit | `1b12fb6ff7225f841e1c833e4895a002e6a1bc6e041c391a9096ae1e92a82779` |
| Closed finite task | `e34c890be2f3ee2dbd7f0355aeb66e43961deabb3b7e30a25caaa5fb6a75877f` |

The next functional uncertainty is establishment of a real early observation
channel under Debian-owned initial userspace. A successor must address that
observability gap with fresh H0 evidence and its own current scope. This
consumed candidate, missing RAM evidence and healthy rollback authorize no
repeat, persistent receipt writer, journal recovery or installed-root handoff.
