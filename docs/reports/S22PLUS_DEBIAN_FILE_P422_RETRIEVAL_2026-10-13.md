# S22+ P422 mountless retrieval: P421 file absent, Android healthy

Status: **PASS_ROOT_EVIDENCE_OBSERVED; NO_AUTHENTICATED_FILE;
ANDROID_CLOSED_HEALTHY**.

The operator returned the exact P422 attended 1800-second/one-operation grant
on 2026-10-13 KST. Only `SM-S906N/g0q/S906NKSS7FYG8` was selected. One P422
boot-only candidate transfer, one fixed mountless reader EXEC, the authenticated
native Download return, and one original-A transfer completed. The candidate
and grant are consumed and closed. No F1 owner remains. A90 and S20+ were untouched.

## File result and proof limits

The separate P422 reader was sealed to the exact run of the already
[closed P421 file pilot](S22PLUS_DEBIAN_FILE_P421_RUN_2026-10-13.md).
The actual selected path returned **ABSENT_IN_HOME_VIEW**. The reviewed H0
collector joined both closed operations, rederived their image-bound consumed
claims and raw original-A health, and returned **NO_AUTHENTICATED_FILE**.
There are no file bytes to authenticate; no empty substitute record was created.

P422 observed `state=1/recover=0/orphan=0`, hence **source_view_clean=true**.
The partition remained read-only, with no mount, journal replay, data write or
installed-code execution. Initial/final protected superblock and GPT identity
checks passed. The unprivileged reader exited successfully and was proved,
reaped and settled. It made 49 bounded reads totaling 291840 bytes. Its sealed
13-file table contained one readable zero-byte `wtmp` and 12 absent entries,
including the selected P421 record. Raw contents and run identities remain private.

This clean superblock observation is later than P421, but is not a complete
root-tree comparison or checker pass. It does not establish P421 unmount
success, its stopping point, or non-execution. P421's early Debian PID1,
module preparation, root admission and file-write claims remain unproved.
P420's earlier full clean-root proof remains historical. Neither missing
records nor the healthy Android return authorizes replay of any consumed run.

The retained reader observes checkpointed home blocks. Its unchanged contract
keeps the home-view limitation explicit even for this clean observation; the
collector reports absence rather than inventing a writer failure stage.

## Original Android return

Fresh original-A preflight and current target/source/artifact/recovery bindings
passed before the candidate transfer. After the reader, the same authenticated
native boot completed CONTROL Download, followed by the single original-A
transfer. No operator physical Download action was needed.

Final numeric root, original boot/supporting digests, changed Android boot,
retained GPT and 34357624832-byte Android userdata capacity all passed, with
native_data present. Terminal: **ANDROID_CLOSED_HEALTHY**,
`research_closed=true`, `recovered=false`. Here `recovered=false` means the
normal planned return completed; no fallback recovery or health retry was
needed. There were no failed raw acquisitions and no repeated effect.

## Canonical timeline

Seconds are measured by host BOOTTIME from the original grant opening.

| Event | Seconds |
| --- | ---: |
| Live session start | 0.000 |
| Fresh Android preflight complete | 4.008 |
| Candidate flash start | 16.722 |
| Candidate flash done | 18.237 |
| Authenticated native health before reader EXEC | 43.676 |
| Mountless evidence complete | 44.901 |
| Authenticated native Download complete | 47.273 |
| Original-A flash start | 53.524 |
| Original-A flash done | 55.079 |
| Full original Android health complete | 103.387 |
| H0 audit and grant closure | 138.905 |

## Durable evidence and validation

H0 closure rederived all completed steps, initial/final health, the consumed
image/operation claim and terminal with every subprocess and connected command
acquisition blocked. It checked **646 raw captures**, **261 frozen source
paths**, and the unchanged **18-row journal**. There were exactly five effect
intents: initial Android Download, N transfer, fixed reader EXEC, native
Download CONTROL and A transfer. N/A transfer counts are 1/1.

The H0 collector also blocked subprocesses and connected acquisition. It
preserved `acquisition.json` before interpreting the absent record, published
the result, and verified both operations' journals, terminals and close
records remained byte-identical. No new device command was needed for closure
or collection. The existing qualified execution code was unchanged; report
validation used content/link/diff and repository-boundary checks rather than
repeating prior image builds or VM tests.

Private evidence is under
`workspace/private/outputs/s22plus-debian-file-evidence-h0-20261012-1/`:
`offline-p422/task/` contains the consumed physical operation and close record;
`physical-p422-source-snapshot/` preserves its source bytes;
`p421-retrieved-by-p422-1/` contains the collector acquisition and result.
The offline preparation directory name does not describe physical execution.
Execution source version: `25de9baa10f295a41edd726b5867001249265743`, with the
qualified frozen working-tree closure from the
[preparation report](S22PLUS_DEBIAN_FILE_ROUTE_P420_P422_H0_2026-10-13.md).

| Receipt | SHA-256 |
| --- | --- |
| P422 operation terminal | `10c51701273c410bfbe29f46a7b1bb248b38c1dd7e5e4e8a2072202701ae029b` |
| P422 closure audit | `fe4ae45d39aa44a5f0c1d60e883048c57d5c1bf5d351554928026438adda6c1c` |
| P422 closed task | `e6097f47ef75b72e601302ecefddad773ceb6ae939666cc9802fe1208c54f0ac` |
| Same-run collector result | `ae3c8d191f922a3d7035612bf7baa2a3c64d835aba14ab759f5d19397eeabb8c` |
| Collector acquisition | `b1f69056b86a2b648a8f5d7eefbfba3aa438e5a334f800793c23db77000a83ce` |
| Collector audit | `d6febf441c12978ca5831bc58138643c638d73e607854735c007fcf1aab151aa` |

The P420–P422 route is closed. It proved P420's full clean root, P422's clean
mountless source view and both later Android returns, but did not obtain a
persisted P421 witness. Further work should first examine H0 evidence for a
bounded observation before the file writer's storage-admission prerequisite.
No successor candidate, fresh grant or device action is selected by this report.
