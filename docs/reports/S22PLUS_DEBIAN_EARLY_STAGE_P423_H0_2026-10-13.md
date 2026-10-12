# S22+ P423: observe Debian early boot before file creation

Original H0 status: **READY_H0_PRELIVE_ONLY; independent PASS_GO**.

**Subsequent physical operation:** P423 consumed its separate returned grant
and closed **ANDROID_CLOSED_HEALTHY** after one N and one original-A transfer.
The post-closure retained-log reader returned **NO_AUTHENTICATED_STAGE**.
See the [physical report](S22PLUS_DEBIAN_EARLY_STAGE_P423_RUN_2026-10-13.md).
The qualification discussion below preserves the state before that execution;
its artifacts, review, consumed journal and original window verdict are unchanged.

Implementation, qualification and a concrete offline task are complete.
No device read, control, transfer or grant was performed/opened. Current
connected health and physical retention remain unproved by this H0 work.

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
records are unchanged. The prospective protocol uses short fixed-size frames, a separate HMAC domain,
and exact contiguous extraction with offsets.
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

## H0 qualification and independent review

The initial design was recorded and committed as `82559211da` before
implementation. The exact stock logger declares no module dependencies; all
71 imported symbol CRCs match the retained kernel. Source inspection confirmed
that previous retained RAM is copied before current early-ring import, that
the early import has a 256-byte text buffer, and that the strategy-3 hook
writes a prefix and text separately. These are framing hazards, not a causal
diagnosis of P418 or P421. The new 153-byte fixed marker reduces record size;
it does not promise atomic or lossless retention.

The actual helper is a 706560-byte static ARM64 ELF. Its selected workload has
one logger, no VM marker and no USB/storage/control linkage. A/B initramfs,
boot and boot-only AP contents match. The combined vendor/Debian VM archive
preserves vendor files while the sole selected module path is
`lab/modules/sec_log_buf.ko`; no ambient module loader or later workload runs.

| ARM64 case | Actual result |
| --- | --- |
| Normal | Eight authenticated current-ring records; measured Debian PID1; one substituted module invocation |
| Parent image mismatch | Actual `/init` bytes changed; rejected before module invocation |
| Module insertion error | One invocation; explicit failed return, no binding/completion |
| Missing binding | One invocation; rejected without a binding/completion claim |
| Logger publication disabled | Kernel mode readback confirmed `off`; no authenticated record or module invocation |
| Expired kernel BOOTTIME | Actual 61-second wait; no record or module invocation |

All six actual captures rederive through the production decoder, and all
sentinel disks are byte-identical. Board identity, module insertion and probe
binding are VM substitutions; Debian PID1, executable measurement, printk,
ring readback, BOOTTIME and frame encoding/decoding are actual ARM64 behavior.
VM serial is current-boot evidence, not Samsung post-return retention.

Ten additional projections from actual ARM64 producer bytes reject or preserve
partial damaged, bad-authentication, missing, duplicate, reversed, mixed-boot
and absent records. VM helper measurements cannot supply physical-image PID1
proof. Four coherently repinned malformed qualifications are rejected: virtual
build, extra module, foreign VM run and promoted failed-case result.

All **109 focused tests** pass in a scoped export containing only this task's
changes over the committed base. They include 17 new stage/projection tests,
15 existing file tests, and 77 early/USB/session/root/evidence/boundary tests.
The new H0 projection tests reject a changed returned Android boot and preserve
all raw bytes and prior records after decoder rejection. Touched Python
compilation, ARM64 compilation and repository-boundary/content/link/diff checks
complete the validation. H0 fixture/compile failures were repaired without any
device action; their private outputs remain retained.

Independent review returned **PASS_GO with no unresolved findings** for the
stage producer/consumer, post-return D0/H0 path and scoped common/target
amendments. It independently verified actual A/B artifacts, all six raw VM
cases, both negative corpora and current/frozen joins: 113 host, 152 build and
175 VM source paths. Existing P418 image qualification and closed P421/P422
raw projections remained valid; consumed journals and terminals were unchanged.

A full eight-frame result proves emission of the terminal milestone after the
measured parent, insertion and binding stages. It does not prove the last
frame's readback/close, helper return or parking. Those three proof flags remain
false. No outcome in this report is physical Samsung stage proof.

## Concrete offline preparation and provenance

The reviewed [stage policy](../operations/S22PLUS_DEBIAN_STAGE_PROBE_V1.md)
uses the existing `debian-early` physical-return owner and the reused bounded
post-return acquisition. The new stage decoder does not change P418's old
parser or reinterpret its original failure. The file profile keeps its original
360-second window; P423 has a separately selected 90-second window. Window
budget checks apply before N, never to A recovery or health-only continuation.

Offline preparation and its complete policy/artifact revalidation ran with
all subprocess and device acquisition blocked. It verified the unconsumed
candidate, closed predecessor route and absent F1 owner. The exact task is
ready without a grant or fresh connected-health claim. Physical execution
would still require the returned attended grant, fresh machine health/target
checks and usable physical Download, followed by original-A closure before
retained-log acquisition. P420–P422 stay consumed.

Private evidence root:
`workspace/private/outputs/s22plus-debian-stage-p423-h0-20261013-1/`.
`offline-1/task/task.json` is the concrete preparation;
`offline-1/task/proposal.json` contains its exact prospective approval string.
`host-source-snapshot-1/`, `build-1/`, `vm-1/`, `package-1/`, both negative-corpus
folders, `independent-review.json` and `ready-audit.json` preserve provenance.
The new current capability record is `s22plus_debian_stage_probe_v1_review.json`;
previous capability tips and consumed bindings were not repinned.

Qualification binds the complete frozen working-tree closure over committed
base `82559211da`. Three shared contract files retain unrelated pre-existing
working changes. The scoped commit contains only the independently reviewed
P423 delta and a matching common-details pin for that projection; it does not
replace the frozen working-tree input used by the prepared task. All unrelated
tracked bytes were checked unchanged, and A90/S20+ received no action.

| Receipt | SHA-256 |
| --- | --- |
| Host source manifest | `803537e992c16c81eb481d705a7d47acb8aab58501c30746ab13585fba59d9a0` |
| Actual A/B build | `ff75c72218ec9ec2813aef15721fec675b39fa3bea5cda938c5c6c7435af57d6` |
| Six-case ARM64 VM result | `cdce6b8aac47ccedf011ac58e0dc4eb98a808c88bcee4f3a96368ad6d09f5e7f` |
| Qualified image | `d083650825d2e4046ee8d616317051ecefad521cdd68802327936806c9fb5933` |
| Boot-only AP, 31969321 bytes | `80b49d8c1ee60db3e0840d282931d639a87a3c03fc018e7547c0e22158d31046` |
| Offline task | `d47ef923272a1b5b009a747468400a403b4f72a29fbce92a8f1c702c65b68314` |

P423 is prepared only. Its eventual records may establish positive early
milestones; absent records still cannot locate a failure before setup or
separate non-execution from lost evidence. The independent Debian/SSH goal and
P421's stopping point remain unresolved.
