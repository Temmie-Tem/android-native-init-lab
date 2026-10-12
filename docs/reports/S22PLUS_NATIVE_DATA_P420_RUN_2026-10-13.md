# S22+ P420 native_data recovery and clean-root proof

Status: **PROVED_CLEAN_ROOT; ANDROID_CLOSED_HEALTHY**.

The operator returned the exact P420 attended 1800-second/one-operation grant
on 2026-10-13 KST. Only `SM-S906N/g0q/S906NKSS7FYG8` was selected. One fresh
P420 boot-only N and one original-A transfer completed. A90 and S20+ were
untouched. P421 file logging and P422 retrieval were not executed.

## Filesystem result

Authenticated native health preceded the unique fixed EXEC intent. Protected
entry-41/GPT binding observed `state=1`, `recover=1`, `orphan=0`. The pinned
strict writer completed at stage 5 with zero logical or I/O error, two writes
and 5120 bytes. These are exactly its journal and primary-superblock
finalization writes; no additional replayed home-block write was reported.

After conclusive child settlement and restored partition RO, the fresh
superblock was `clean=1/state=1/recover=0/orphan=0`. The separate pinned
read-only checker completed successfully. Protected root comparison matched
all **8969** expected entries, including all **8175** boot inputs, with zero
missing, content, metadata or other findings. The exact root result had no
extra mutable paths. Installation markers and witness matched; protected
unmount and final partition-RO/GPT checks passed.

The authenticated result is `PASS_JOURNAL_RECOVERY_OBSERVED`, verdict
`PROVED_CLEAN_ROOT`. This is a physical native_data consistency and exact-root
observation under the existing predicate. It proves neither installed Debian
execution nor the prospective P421 file's creation, survival or retrieval.
No general fsck repair, orphan cleanup, formatter, reinstall or root-admission
exception was introduced. The filesystem proof remains distinct from Android
health and from P421's mandatory fresh admission.

## Return and preserved read failure

The second same-boot native session completed its fixed authenticated Download
return. Original A was transferred once. During the first final-health
bracket, its fourth fixed ADB command returned exit 1 because the selected
device was temporarily absent. That raw capture and `RawCaptureError` stop
remain preserved.

The existing recovery path rederived the already completed A transfer and
performed only a new health observation. No candidate, EXEC, control or A
transfer was repeated. The health continuation proved numeric root, original
boot/supporting digests, a changed Android boot, exact retained GPT and
34357624832-byte Android userdata capacity with native_data still present.
Terminal: **ANDROID_CLOSED_HEALTHY**, `recovered=true`, `research_closed=true`.
Here the recovery flag records the health continuation; physical Download
assistance and an additional recovery transfer were unnecessary.

## Canonical timeline

Times are seconds from the original grant opening, measured by host BOOTTIME.

| Event | Seconds |
| --- | ---: |
| Live session start | 0.000 |
| Fresh Android preflight complete | 3.637 |
| Candidate flash start | 18.523 |
| Candidate flash done | 20.080 |
| Native authenticated health complete, before original EXEC | 45.876 |
| Complete clean-root result and DETACH | 51.193 |
| Authenticated Download return complete | 53.665 |
| Original-A flash start | 61.681 |
| Original-A flash done | 63.398 |
| First Android-final health read stopped | 105.343 |
| Health-only continuation complete | 112.615 |
| H0 audit and grant closure | 256.387 |

## Durable closure

The H0 closure rederived the native authenticated transcripts, all completed
transitions, initial/final Android health and the original image/operation-bound
global claim. It reopened **578 raw captures** and preserved **263 frozen source
paths**. All connected command acquisition was blocked; only host `file` and
`readelf` checks of the exact pinned replayer were allowed. The 20-row journal
and original terminal remained unchanged. The one candidate and grant are
consumed/closed, and no F1 owner remains.

Private evidence is under
`workspace/private/outputs/s22plus-debian-file-evidence-h0-20261012-1/connected-p420-1/task/`,
with its source snapshot in the parent evidence directory. The execution
source version is `83ea0a535ee0d9ad3df8773e839625db4472cc84` plus the already
reviewed frozen working-tree closure documented in the
[H0 report](S22PLUS_DEBIAN_FILE_ROUTE_P420_P422_H0_2026-10-13.md).

| Receipt | SHA-256 |
| --- | --- |
| Operation terminal | `bf5df530edd68bf00f5286592ff6bd41c8817abc3adf40febce1c6e95de9594b` |
| Closure audit | `ca6c33f1c20bce002d9e551a0e28e14dff6e220fc805bcb549cde7757aee0b30` |
| Closed task | `1f55b38e6e2ffb684c89f7957cb5656d4fc1e2dab446c59b58934a55bcc73f10` |

P421's prerequisite now has physical evidence. Its file pilot and P422's later
sealed reader still require separate returned attended grants, fresh binding
and their own original-A closures. No grant transfers between these stages.
