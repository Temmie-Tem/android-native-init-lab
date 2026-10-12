# S22+ P423: observe Debian early boot before file creation

Status: **DESIGN_SELECTED; H0 ONLY; NOT DEVICE_READY**.

The operator requested H0 analysis of progress before P421's file creation and
preparation of the next minimum experiment. P420–P422 remain consumed and
closed healthy. P422 observed a clean superblock and no selected P421 file;
it did not locate P421's stopping point. See the
[retrieval report](S22PLUS_DEBIAN_FILE_P422_RETRIEVAL_2026-10-13.md).
Only `SM-S906N/g0q/S906NKSS7FYG8` is selected. A90 and S20+ are untouched.

## Decision and completion criterion

Prepare **P423, a logger-only Debian early-stage probe**, with the retained
kernel, Debian shell `/init`, minimal RAM setup and exactly one stock
`sec_log_buf` module. Select zero platform-prefix modules and no USB, UFS,
block discovery, root admission, filesystem writer or installed init.
Its bounded question is whether actual Debian PID1 identity and logger
insertion/binding milestones can be authenticated after original-A return.

H0 completion requires an actual reproducible boot-only A/B artifact,
representative ARM64 producer/consumer and failure cases, independent review,
and a concrete offline task using the existing one-operation attended owner.
No device reads, control, transfer, live grant or device recovery are part of
this request. Physical execution later needs its own returned finite grant,
fresh machine binding and usable attended original-A recovery.

## Why this is the next minimum

P421's file writer runs only after Debian's early RAM setup, all 73 platform
and eight UFS modules, protected storage identity/metadata, a clean checker
and complete root admission. A missing file cannot distinguish any of these
prerequisites from a later record failure. Its checked RAM log is lost on
physical return when no separate observation channel is available.

P418 proved that two exact short authenticated stage records survived one
physical original-A return: target guard and logger-module BEGIN. That is the
only established early retained-record path in this lineage. It did not prove
logger insertion completion or locate a stall. Its full selected module set
was also checked before the first insertion. P423 removes those unrelated
module checks and measures the parent before loading the logger.

| Option | Relevant limitation | Decision |
| --- | --- | --- |
| Existing file record | Depends on the entire storage/admission path | Too late for the present question |
| Existing early USB | Depends on the 73-module platform path; P419 obtained no channel | Keep for later functional work |
| Stock retained-RAM logger | Partial physical retention precedent; independent of storage and USB | Qualify a logger-only probe first |
| Direct RAM mapping, panic or kernel changes | New mechanisms and hazards without present necessity | Not selected |

The known P418 damaged framing must remain visible. Its old decoder and raw
records are unchanged. The prospective protocol will use short fixed-size
frames, a separate HMAC domain, and exact contiguous extraction with offsets.
No line reconstruction, shortened body, missing-byte synthesis or promotion of
gaps to a complete result is allowed. Current-ring acceptance and post-return
retention remain separate properties.

## Fixed observation design

After the existing `/dev` and `/run` RAM setup, one child records target-bound
entry; verifies `/proc/1/exe`, exact parent command line and actual shell,
`/init` and helper hashes; pins the sole logger module; records the imminent
single insertion; records its return; checks module/driver/last_kmsg readiness;
and emits a terminal stage before returning to Debian PID1's park loop.
A pre-call marker is not invocation, return or binding proof.

Each compact independently authenticated frame carries run, kernel boot,
sequence, event and one bounded measurement. A fresh record uses one checked
printk write and the existing bounded exact ring-readback pattern. Logging
failure stops later effects. Module insertion is never retried. Read-only
readiness polling is bounded and cannot repair a stalled module syscall.

A fixed host opportunity window is anchored to the original N transfer and
claims only elapsed time with device activity unknown. Attended physical
Download and one original-A transfer, followed by full Android32 health,
precede the existing same-returned-Android-boot bounded `last_kmsg` acquisition.
Only the new profile's decoder interprets its frames. Complete, partial,
rejected and absent evidence remain distinct from Android health.

The earliest record still follows initial shell and RAM setup. No retained
record therefore cannot locate an earlier failure or prove non-execution.
Successful logger-only evidence would qualify this observation boundary; it
would not establish platform/UFS preparation, P421 behavior, installed Debian,
SSH, clean unmount or automatic recovery. Future extension would require its
own bounded candidate and qualification.

## Review and implementation status

An independent preliminary review agreed that logger-only with zero platform
modules is the minimum useful scope and identified parent measurement,
framing, exact module/probe prerequisites and actual archive inspection as
required H0 checks. This is design review, not capability PASS_GO.
Implementation, qualification and the final source-bound review are pending.
