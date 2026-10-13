# S22+ P426/P427: file absent, retained UFS preparation, Android healthy

Status: **CONSUMED_NO_AUTHENTICATED_FILE_ANDROID_CLOSED_HEALTHY**

The exact operator-owned `SM-S906N/g0q/S906NKSS7FYG8` completed one P426
storage-first writer trial and one separately bound P427 mountless reader.
Each used its returned attended 1800-second/one-operation grant, one fresh
boot-only candidate N and one original Android A. Both grants/candidates are
closed/consumed; both final outcomes are **ANDROID_CLOSED_HEALTHY** with
`research_closed=true`. No F1 owner remains. A90 and S20+ were untouched.

P427 successfully read its sealed file table under partition RO, without a
mount or filesystem write. The P426 file was **ABSENT_IN_HOME_VIEW** and the
observed superblock was clean (`state=1`, `recover=0`, `orphan=0`). The joined H0
result is **NO_AUTHENTICATED_FILE**. Physical filesystem logging, full P426
storage preparation and initial-parent measurement are not proved.

The complementary same-returned-Android-boot RAM capture preserved **156
ordered authenticated records**, including 75 completed modules. The last
completion is `ufshcd_crypto_qti`; the last authenticated record is
`MODULE_BEGIN ordinal=76 name=ufs_qcom`. This establishes a preparation prefix,
not the exact point or cause of a stall, successful storage admission, file
creation, installed Debian PID1, services or SSH.

## Scope and current bindings

The [H0 report](S22PLUS_DEBIAN_FILE_FIRST_P426_H0_2026-10-13.md) retains the
actual A/B packages, 14 ARM64 writer cases, four exact-run reader cases,
190 focused tests, nine negative qualifications and independent `PASS_GO`.
Implementation commit `7fb2aada50` and the frozen working-tree execution closure
were unchanged throughout the two operations. The scoped commit projection and
pre-existing unrelated working changes retain their documented meaning.

The operator returned both exact `attended` approval strings in response to the
prepared execution/attendance request. The writer grant opened first. The reader
grant opened only after P426's validated original-A closure and retained-log
capture. Fresh fixed D0 preparation and each execution preflight verified exact
original boot/supporting hashes, root, target and Android32/GPT/capacity.
Those Android reads did not inspect or admit native_data.

The [file-first policy](../operations/S22PLUS_DEBIAN_FILE_FIRST_V1.md) owns the
P426 automatic lifetime and physical return. Its persistent write surface was
one exclusive bounded file after clean-only complete protected root admission.
The [mountless-reader policy](../operations/S22PLUS_NATIVE_ROOT_EVIDENCE_V1.md)
owns the separate P427 read and original-A return. Neither operation selected
journal replay, repair, reinstall, installed init or a repeat of a consumed run.

## Physical timelines and return

Times are host BOOTTIME seconds from each original grant opening; they do not
infer device execution timestamps. Complete journals and canonical timelines
remain private.

| Event | P426 writer | P427 reader |
| --- | ---: | ---: |
| N transfer intent | 30.070 | 15.181 |
| N transfer completion | 31.591 | 16.676 |
| Live native readiness / fixed EXEC intent | Not observed | 41.912 |
| Fixed observation completion | 391.659 | 42.931 |
| Original A transfer intent | 464.565 | 51.138 |
| Original A transfer completion | 465.959 | 52.693 |
| Complete final Android health | 562.287 | 102.139 |
| Validated task closure | 615.792 | 139.124 |

P426's original 360-second host window completed without USB queries or control.
Its `AWAITING_OFFLINE_FILE_RECORD` result established only the elapsed window,
with unknown device activity and no live PID1/write/clean-unmount proof. The
operator then reported starting manual Download entry. The exact machine-bound
Download endpoint was acquired and A transferred once.

P427 completed authenticated native health, one sealed partition-RO reader
invocation, descriptor settlement and the fixed native Download return. Its
original A also transferred once. In each operation, one post-A health read
returned ADB device-not-found. Both raw failures were preserved. The existing
recovery continuation reconstructed the already proved A transfer and performed
health only; no image, storage action or control request was repeated.

Final original boot/supporting hashes, root, changed Android boot identity and
Android32/GPT/capacity all passed. Each terminal has `recovered=true` because
health completion used that continuation. This is original-A recovery health,
not a rollback of native_data or proof of P426's unmount return.

## Retained RAM and file evidence

Before P427, the fixed P426 returned-boot D0 acquired 2,097,136 bytes and passed
both health brackets on the same Android boot as P426's final health. Strict
H0 rederivation authenticated 156 records from one P426 kernel-boot identity.
The logger binding and provider barrier passed; 75 MODULE_DONE and 76
MODULE_BEGIN records were recovered. No complete preparation terminal or
physical parent-measurement record was established. The result remains
`AUTHENTICATED_PARTIAL_RECORDS`, with no exact-stop or non-execution claim.

The capture and H0 audit were already successfully published when a final
console-formatting loop requested a nonexistent `offset` field. That private
wrapper exited with `KeyError`; the source and traceback are preserved. The
raw capture, strict decoder, health brackets and audit had succeeded. Only
saved results were inspected afterward; the capture was not repeated.

A bounded H0 look at surrounding kernel text found UFS/SCSI discovery messages,
but the retained buffer also contains interleaved older text. These unauthenticated
lines are diagnostic context only. They do not upgrade the last authenticated
BEGIN into successful module return or establish `ufs_qcom` as the root cause.

P427 returned `PASS_ROOT_EVIDENCE_OBSERVED`, partition RO retained, no mount,
no data write, no journal replay, and the clean superblock view above. Its
sealed P426 pathname was absent. The H0 collector rederived both closed owners,
original candidate claims, raw reader result and writer/reader selection with
process/device acquisition blocked. It returned `NO_AUTHENTICATED_FILE` /
`ABSENT_IN_HOME_VIEW`; original journals and terminal records were unchanged.

Absence is not non-execution proof, including the general home-block/journal
visibility limitation. The clean reader view is a separate current observation,
not complete root admission or proof of a successful P426 write and unmount.
No old writer, reader or grant may replay. The current useful boundary is the
last authenticated storage-preparation prefix; explaining the missing later
record requires a new bounded H0 diagnosis, not a claimed causal conclusion.

## Durable evidence and completion

Private evidence is under
`workspace/private/outputs/s22plus-debian-file-first-p426-h0-20261013-1/`:
`connected-writer-1/task`, `connected-reader-1/task`, `retention-1`,
`retention-audit.json`, `retention-reporting-note.json`, `retrieval-1` and
`retrieval-audit.json`. Each task includes its original grant, append-only
journal, raw captures, terminal, closure audit and closed record. Closure
rederived 1,023 writer and 618 reader raw captures and checked their frozen
host/runtime sources. Source snapshots, approvals, raw identifiers and logs
remain private; consumed evidence was not relabelled or edited.

The requested physical writer, separate retrieval, original-A recovery and
result classification are complete. The desired physical file-logging outcome
was not achieved. No additional experiment, kernel modification or push was
performed in this unit.
