# S22+ P423: no authenticated early stage; Android healthy

Status: **NO_AUTHENTICATED_STAGE; ANDROID_CLOSED_HEALTHY**.

The operator returned P423's exact attended 1800-second/one-operation grant on
2026-10-13 KST. Only `SM-S906N/g0q/S906NKSS7FYG8` was selected. One P423
boot-only candidate and one original-A transfer completed. The candidate and
grant are consumed/closed, with no F1 owner. A90 and S20+ were untouched.

## Scientific result and limits

The selected `debian-stage-probe-v1` workload contains Debian shell `/init`,
minimal RAM setup and one stock `sec_log_buf` module. It selects zero platform
or UFS modules, no USB gadget, storage admission, block-backed filesystem work,
installed init or ordinary reboot. Its
[H0 qualification](S22PLUS_DEBIAN_EARLY_STAGE_P423_H0_2026-10-13.md) and
[reviewed policy](../operations/S22PLUS_DEBIAN_STAGE_PROBE_V1.md) remained bound
to the unchanged execution closure.

After healthy closure, the fixed D0 reader acquired **2097136 bytes** from
`last_kmsg` on the same returned Android boot. Before/after rooted health and
shell-v2 transport checks passed. The exact production decoder returned:

| Observation | Result |
| --- | --- |
| Authenticated P423 stage records | 0 |
| Damaged candidate envelopes | 0 |
| Foreign frames | 0 |
| `S22STG1` prefix occurrences | 0 |
| Early Debian PID1 / logger binding | Unproved |
| Last authenticated stage | None |

The result is **NO_AUTHENTICATED_STAGE**. A readable returned log does not
establish that it contains P423's candidate boot. Missing records cannot
distinguish failure before the first marker from failure to retain later
evidence. They do not prove non-execution or locate a stopping point. P421's
behavior and storage state remain unresolved by this probe. No PID1, logger
insertion, terminal stage, helper return, parking, installed Debian or SSH
success is claimed. No record was reconstructed or synthesized.

## Execution, physical return and health continuation

Fresh original-A health, exact target/source/artifact/recovery bindings and
global exclusion passed before the candidate transfer. That one N intent
consumed the automatic probe. The fixed host window ended 90 seconds after
the original transfer completion without a device query. Its immutable result
is **AWAITING_RETAINED_STAGE_RECORDS**, with device activity unknown and no
live execution proof. The later D0 result does not rewrite that window record.

After the window, the operator reported physical Download entry. The machine
observer independently verified the bound endpoint and transferred original A
once. The first final-health bracket stopped with `RawCaptureError`: a fixed
ADB read returned exit 1 and `error: closed`, without timeout, overflow or
producer failure. The raw capture is preserved.

The existing recovery path rederived the completed A transfer and continued
only health observation. It performed no additional N/A transfer or control.
Final numeric root, original boot/supporting digests, changed Android boot,
exact GPT and 34357624832-byte Android userdata capacity passed, with the native
partition still present. Terminal: **ANDROID_CLOSED_HEALTHY**,
`recovered=true`, `research_closed=true`. This is Android health, not candidate
execution proof or a native_data filesystem check.

## Canonical timeline

Seconds are host BOOTTIME elapsed from the original grant opening.

| Event | Seconds |
| --- | ---: |
| Live session start | 0.000 |
| Fresh Android preflight complete | 2.365 |
| Candidate flash start | 15.318 |
| Candidate flash done | 16.811 |
| Candidate boot readiness | Not observed; no live execution channel selected |
| Original 90-second host window complete | 106.905 |
| Original-A flash start after physical Download | 135.944 |
| Original-A flash done | 137.440 |
| First final-health ADB read stopped | 178.503 |
| Health-only continuation complete | 195.897 |
| H0 audit and grant closure | 207.188 |

## Evidence preservation and closure

H0 closure blocked all process/device acquisition while rederiving the consumed
image/operation-bound global claim, both transfers, host window, initial/final
health and terminal. It checked **755 raw captures**, the one classified health
failure, **242 frozen source paths** and the unchanged **16-row journal**.
The post-closure D0 has 16 additional successful captures. Its result was
independently rederived with process/device acquisition blocked, and the prior
journal, terminal and closed-task bytes remained unchanged.

Private evidence root:
`workspace/private/outputs/s22plus-debian-stage-p423-h0-20261013-1/`.
`offline-1/task/` is the original preparation directory and now holds its
consumed physical operation, terminal and closure. `physical-p423-source-snapshot/`,
the physical/return/health-continuation driver outputs, `retention-p423-1/`
and the retention audits retain source, raw and interpretation provenance.
Execution base commit: `d6818a508b4aedce69435e3d0ab28b92f05da1b9`, with the
qualified frozen working-tree closure described in the preparation report.

| Receipt | SHA-256 |
| --- | --- |
| Operation terminal | `3b0184a3dc858d066ccd54c97a17955a8965ed46e0edc1e0817412ccd04213c3` |
| Closure audit | `6b43fd7cc1247b9bf72aa62b713545528b912a4795966d0a973a8bee7aecf4ff` |
| Closed task | `82e0f8fdcbd726379f017c54276b3d1f5639457d42a69b4b39a6ff4b8a2f0d90` |
| Retained-log acquisition receipt | `7a0e529fb0a7703c8fd3a218e5fb73a4cb1828dc1135bf6353851ad51bb27e2a` |
| Stage result | `d61c2a3e511806e939ca19ff197ad9d1d4d786744ba6ba64f3dff9d0f0263a4f` |
| H0 retention audit | `0270a4d63b07cc4472b7efb2d3c2bdc9e252839d426182568f333d5786865cf8` |

No successor candidate, replay or further device action is selected. The
bounded experiment and required recovery/retrieval are complete; the full
Debian/SSH objective remains unachieved.
