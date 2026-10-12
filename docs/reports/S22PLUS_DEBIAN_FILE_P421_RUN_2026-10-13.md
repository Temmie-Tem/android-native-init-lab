# S22+ P421 file pilot consumed; original Android healthy

Status: **AWAITING_OFFLINE_FILE_RECORD; ANDROID_CLOSED_HEALTHY**.

The operator returned the exact P421 attended 1800-second/one-operation grant
on 2026-10-13 KST, after P420's
[clean-root proof and healthy closure](S22PLUS_NATIVE_DATA_P420_RUN_2026-10-13.md).
Only `SM-S906N/g0q/S906NKSS7FYG8` was selected. One P421 boot-only candidate
and one original-A transfer completed. The candidate and grant are consumed
and closed; no F1 owner remains. A90 and S20+ were untouched.

## What this operation establishes

Fresh original-A health and all source/artifact/target/recovery bindings
passed before the one candidate transfer. That transfer consumed the complete
automatic file pilot, including possible partial writes or no retained file.
The original 360-second host window completed without USB acquisition,
challenge, device query or control. Its immutable open/close records rederive
against the original N transfer completion and grant deadline.

The window is only an elapsed-time fact. It establishes no Debian PID1,
module progress, root admission, file-write, unmount or clean-filesystem proof.
Device activity during it remains unknown. P420's earlier clean root does not
establish the filesystem state after this potentially writing boot. An absent
or malformed later file cannot prove non-execution or authorize P421 replay.

After the window, the operator reported physical Download entry. The existing
machine observer independently bound the exact endpoint before one original-A
transfer. This operation did not start P422 or directly read native_data from
Android.

## Return and bounded health continuation

Original A transferred successfully. The first final-health bracket's second
fixed ADB command returned exit 1 because the selected device was temporarily
absent. The raw capture and `RawCaptureError` stop remain preserved.

The existing recovery path rederived the completed A transfer and performed
only health continuation. No N, A, writer or control was repeated. Final
numeric root, original boot/supporting digests, changed Android boot, exact
retained GPT and 34357624832-byte Android userdata capacity passed, with
native_data still present. The terminal is **ANDROID_CLOSED_HEALTHY**,
`recovered=true`, `research_closed=true`. Android health is separate from the
unobserved file and native_data filesystem state.

## Canonical timeline

Seconds are measured by host BOOTTIME from the original grant opening.

| Event | Seconds |
| --- | ---: |
| Live session start | 0.000 |
| Fresh Android preflight complete | 4.992 |
| Candidate flash start | 22.421 |
| Candidate flash done | 24.248 |
| Candidate boot readiness | Not observed; no live execution channel selected |
| Original 360-second host window complete | 384.481 |
| Original-A flash start after physical Download | 453.401 |
| Original-A flash done | 454.945 |
| First final-health ADB read stopped | 496.274 |
| Health-only continuation complete | 522.889 |
| H0 audit and grant closure | 577.869 |

## Durable evidence and next owner

H0 closure rederived the consumed image/operation-bound global claim, candidate
and A transfers, fixed window, initial/final Android health and final terminal.
All connected command and process acquisition was blocked. **820 raw captures**
and **244 frozen source paths** were checked. The original 16-row journal and
terminal were unchanged. There was exactly one preserved health-read failure,
one N transfer and one A transfer.

Private run evidence is under
`workspace/private/outputs/s22plus-debian-file-evidence-h0-20261012-1/offline-p421/task/`;
the directory name records where the offline task was prepared, not an H0-only
execution claim. Its physical execution used the returned grant and fresh
preflight. The parent evidence directory contains the source snapshot and
operator physical-action statement. Execution source version:
`7343beec960c49bb495686195381dfbc3390bd98`, with the already qualified
frozen working-tree closure from the
[preparation report](S22PLUS_DEBIAN_FILE_ROUTE_P420_P422_H0_2026-10-13.md).

| Receipt | SHA-256 |
| --- | --- |
| Operation terminal | `86d96860946643cb6e5e370ce018d88d65cb8d8d70e92057a9f01d5bfb0984fd` |
| Closure audit | `95e086c8a632830aaf89e378cfdc4e6932546c3cb396ab344ef1d8e77842a8e9` |
| Closed task | `221bf796c8d396b83198285b90ad9da98cd749ce31d498973a41f60401b518fd` |

The next owner is P422's already qualified mountless reader, sealed to P421's
exact run. It needs its own returned attended grant, fresh binding and
original-A closure. The H0 collector will then preserve captured raw bytes and
join both closed operations before authentication. A complete authenticated
file proves only its pre-unmount milestone; prefixes, unmount success, later
cleanliness and Android health keep their separate meanings. No read or
journal replay is silently added to P421's closed grant.
