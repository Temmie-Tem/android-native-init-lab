# S22+ FYG8 P364 preparation diagnostics

## Result and scope

P364 adds fixed authenticated preparation stage/errno evidence to the consumed
P363 candidate design. It retains the exact P361 renderer, five stock modules,
module order/parameters, bounded Download CONTROL, physical fallback and
mandatory exact Magisk rollback. The operator later returned the exact prepared approval. P364 is now consumed
and CLOSED/19 after one candidate and one exact Magisk rollback, with
`NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`, `NO_PROOF_OBSERVER` and
recovery_required=false. No next F1 is authorized. P363 remains consumed and
CLOSED/19; P364 does not retrospectively prove its original failure errno.

## Changed behavior

The former silent preparation park now emits bounded ENTER/RETURN records for
file verification, finit_module, close, providers, debugfs, registry and writer
binding, followed by pipe, clock, clone and optional child outcome. A final
original error is signed when the channel and fixed 60-second diagnostic
deadline permit. A blocking kernel call has no new timeout; ENTER without RETURN
means return unobserved. Child creation does not prove exec or display output.
The child deadline begins later than the diagnostic deadline, so a stalled child
may leave no signed terminal error after diagnostic expiry.

Frame 0x8b has a fixed 40-byte payload, run/session-bound HMAC and separate
monotonic ordinal, capped at 48 records without per-poll output. A failed write
stops subsequent parent operations except cleanup. Diagnostics end before the
CONTROL ACK. Incomplete preparation never permits CONTROL. The host rederives
partial progress from immutable raw RX/TX on both successful and failed receipts;
cached progress is not accepted as independent proof.

## Qualification

The full generated native preparation and console were compiled and exercised
with bounded syscall fixtures. All 15 P364 tests passed, including each module
insertion failure, file/provider/registry/writer/pipe/clock/clone errors, partial
or failed diagnostic writes, an unreturned call, early child exit, deadline
expiry and missing progress. Actual partial native-C evidence passed the generic
receipt consumer; tampered cached progress was rejected. All 24 P363 regression
tests passed. Sixteen touched Python files passed py_compile. Repository
boundary and diff checks passed.

The initial host fixture compile errors were corrected before qualification.
Image identity derivation was corrected for both the raw run identifier and
compressed embedded configuration before building. No consumed input or device
evidence was changed. The qualified A/B build is byte-identical:

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| Boot-only AP | 31,006,761 | `956d44ad1422244dff750400da781690bf521a0880450ab8671be4e501399ada` |
| Native init | 150,632 | `7f7c6b8ac1ed30f574f38436eb99eb3000aec2f5136f2ae0c009b75f8f2f3932` |
| Retained renderer | 710,040 | `5e66fea1f312aa81853aa499336a35bc397886b7fbdafb7421b8db8d69d68919` |
| Image | 41,490,944 | `b016cfd9d7999de4c3eab4aec16c9b2b7b3819d361726695944737e3ec678b67` |

Candidate static qualification passed with SHA-256
`bb56431d388a3f7718d8e5486b9f88fdb44989ac269eae3cdd04891fe55ac4e6`.
The real common offline bundle verifier passed promotion rehearsal.
Independent native/target and host/protocol/receipt reviews returned scoped
PASS_GO with no blockers. Their private receipts have SHA-256
`176aa498d0bd38beb34114ac8279351793026d6bd1b33f003ae174e683f8ecba`
and `5e369d61fc1144840662324cd3be629f899915715c21a549176da25ac538118b`.
These are capability findings, not live diagnostic or recovery proof.

Private build, raw tests and review receipts are retained under
`workspace/private/outputs/s22plus_fyg8_p364/`. No private identifiers or raw
device data are published. A90 and S20+ remain outside this task.

## Connected preparation

The first prepare invocation stopped in host run-directory allocation: the
requested output directory was outside the required direct-child F1 run root.
No run directory was allocated and no connected command occurred. Its private
log is preserved. The corrected invocation uses the existing canonical run root;
source, candidate and execution identity were unchanged.

Fresh connected preparation `p364-ready1-prepared-20260908-1` passed exact D0
with `PASS_DEVICE_ACTION_D0_V2_CONNECTED_READ_ONLY`. The prepared record is
32,273 bytes, SHA-256
`82c7a65e9813ff60fa3d746a888d8bc6728e888bec27b795259a4718dab7864f`.
It binds 72 execution sources, the source-qualified candidate, exact rollback,
raw D0 and target continuity. No reboot, device write, Odin invocation or
partition transfer occurred; no D1 was needed. The F1 approval token remains in
the private prepared record and is not run authority until separately returned
by the attended operator. No A90 or S20+ command occurred.

The actual `load_prepared` execution consumer reopened the complete prepared
binding successfully after D0. This host-only check revalidated source/artifact
identity and raw preparation evidence without device contact. The bounded
preparation task is complete; live diagnostics, display and Download return
remain unproved for P364.

## Approved execution and retained diagnostics

The exact P364 candidate and exact Magisk rollback each completed once. The
original execute observed physical Download entry and completed rollback and
final health without a device recovery invocation. Rooted FYG8, original boot
and supporting partition hashes, Android health and absent Download passed.
The journal reached CLOSED/19 at 2026-09-07T18:16:10Z.

Authentication, kernel boot identity, parent identity and the complete host
sequence-4 display request were observed. Twenty-eight authenticated diagnostic
frames preserve preparation entry and zero returns from the first four module
file checks, finit_module calls and closes. Stage 30, the SDAM provider checker,
returned -22/EINVAL; the signed terminal frame repeated -22. This localizes the
failure to that checker, without identifying its particular inner operation.
No fifth-module preparation, renderer creation, CONTROL intent or ACK followed.
The software return window is `not-requested`; native Download and display
remain unproved. Physical Download was used for the authorized exact rollback.
These useful diagnostic facts do not upgrade the full candidate qualification.

## Host terminal-publication incident and repair

After verified final health and journal closure, the original terminal writer
failed with `host-first state carries a foreign candidate namespace`. The
P364 state legitimately retained `p363_control_intent` and `p363_return_window`
as shared return-host field names, but the generic foreign-prefix assertion
rejected them. The candidate and rollback were never replayed.

A narrowly reviewed host repair first loaded the unchanged prepared closure,
required its exact binding, CLOSED/19 and final-health/completion flags, and
reproduced the original error. It then substituted only the validator with an
exact shared-name exception for return owners. The existing CLOSED-only
finalizer and complete result validation ran with a backend that rejects every
action and with state writes forbidden. Dry-run and publication preserved all
7,119 prior run files byte-for-byte, including prepared state, journal and raw
evidence. Only the terminal result and separate private repair evidence were
created. A later applicability audit established that the repairing
`Journal.reopen` also replaced the same-byte journal-head index; its inode and
timestamps were not covered by the byte-only preservation check. This was
content-preserving host finalization, not a strictly read-only filesystem audit.
The final result is 32,974 bytes, SHA-256
`8f121d45b5ae8678493d64432a4a1362c0551de81ed07b03208b6e396a59fbb5`.

The independent repair review is private, SHA-256
`477315f0d6d745c2bb52bbb8cda32a104395fcebbe1b4efacc7f3059fc563705`.
The original execution source is retained at SHA-256
`91869378a84d12f464e424fcaa36e07ef5b4d6b599cebc2718bb2b4277f70037`.
The private repair source is SHA-256
`4f254ca9231f0f3dee94e0e6d17354fffd077e0f55a86ca519e1b2be546fef75`.
These receipts are under the existing private P364 output namespace.

After terminal publication, the same reviewed correction was applied to the
reusable validator. Only the three existing shared return-state names are
admitted for return owners; foreign candidates and suffix lookalikes remain
rejected, and durable receipt verification still runs. Consumed preparation,
source pins and candidate bytes are unchanged and confer no replay authority.

The production correction passed four namespace/durable-validation regression
tests, all 24 P363 regression tests, py_compile and repository boundary/diff
checks. The ledger taxonomy command retained an identical pre-existing failure
before and after this appended row: `log row 547 has an unknown evidence
outcome`. That historical taxonomy issue was not changed or claimed fixed.

## Post-run H0 diagnosis: ARM64 open-flag ABI mismatch

The bounded analysis identified an architecture-specific defect in the actual
P364 binary. The code supplied literal `0200000` while intending O_DIRECTORY.
Samsung's ARM64 UAPI defines that value as O_DIRECT; O_DIRECTORY is `040000`.
The generated directory open therefore passes `0x90000` (O_CLOEXEC | O_DIRECT)
to ARM64 openat syscall 56. The transferred init disassembly confirms this mask
at 0x409460 and the exact `/sys/bus/nvmem/devices` path. The syscall wrapper
passes the flags without translation. These ELF locations are static artifact
locations, not live addresses or KASLR evidence.

The source-matched kernel's open path rejects O_DIRECT with EINVAL when the
opened inode's address-space operations lack direct_IO. Kernfs assigns such
operations to sysfs inodes. Thus the intended existing sysfs directory cannot
be opened successfully with these flags. This is a confirmed compiled defect
and reproduces the signed stage-30 failure. The live witness still reports the
whole checker, not a separately captured inner openat return; that distinction
is preserved.

| Intended behavior | Literal used | ARM64 meaning | Correct ARM64 flag |
| --- | --- | --- | --- |
| Open a directory | `0200000` | O_DIRECT | O_DIRECTORY = `040000` |
| Reject module-file symlinks | `0400000` | O_LARGEFILE in kernel UAPI | O_NOFOLLOW = `0100000` |

The second mismatch affects module opens in both the original return-module
helper and the new diagnostic module helper. Their intended O_NOFOLLOW
protection was absent. Exact packaged module bytes and existing hashes are
unchanged; no symlink substitution was observed. This is a real protection
defect, not evidence that a substitution happened. The compiled module-open
mask `0xa0000` is confirmed at 0x409a4c. These ABI findings supersede the prior
review's incorrect interpretation of those flags, without changing the retained
live transcript, rollback or final health.

### Real-syscall host reproduction

A private H0 harness extracts the exact frozen P364 provider function. Only
its fixed sysfs path is mapped by wrappers to a private fixture; openat,
getdents64, readlinkat and close are real syscalls. The fixture contains the two
expected provider-link suffixes and inert regular/symlink files. No connected
device, module insertion, reboot or production candidate change is involved.
Static ARM64 binaries were cross-compiled and inspected with `file`, then run
under qemu-aarch64. An x86 build provides an architecture comparison.

- Unchanged ARM64 function: first openat returns -22, before any getdents call.
- Changing only the directory flag to ARM64 O_DIRECTORY: open, directory reads,
  both link checks and close succeed; the provider function returns zero.
- Unchanged x86 function: returns zero, because that architecture assigns the
  original literal to O_DIRECTORY.
- ARM64 module-file fixture: the old literal follows a symlink; O_NOFOLLOW
  rejects the same link with -40/ELOOP. No module is loaded in this test.

The 15 earlier H0 diagnostics tests compiled for the host and stubbed module
and NVMEM opens without checking their flags. They verified error framing and
control-flow behavior, but could not detect this target-ABI mistake. Build and
static source matching preserved the mistake faithfully; they did not establish
that the numeric flags had the intended ARM64 semantics.

The reproduction receipt is retained under
`workspace/private/outputs/s22plus_fyg8_p364/provider-abi-analysis/`, SHA-256
`28f2a1ff6f11c223010f276a86829848e3376a74781f014c7fa3a4175ee28175`.
The report does not promote the corrected host fixture to a working live
candidate: later preparation, renderer operation and native Download still
require their own evidence. No successor has been built or activated. A future
successor must use target-correct directory/no-follow constants and validate
these real ARM64 syscall semantics before its existing review and qualification.
Consumed P363/P364 sources, approval pins and journals remain unchanged.

An independent read-only analysis confirmed both ABI defects, exact Samsung
kernel source semantics, frozen C/init instruction identity and the init-to-AP
to-live-transfer digest join. It reviewed the ARM64/x86/symlink reproduction
and found no additional flag mismatch within the new return helpers. Its
private receipt has SHA-256
`cb50ac262c39b3f63d156144339ab6d1452b108c06d0deead9457dd0142eac07`.
This analysis supersedes its prior flag interpretation only and grants no
implementation or device authority. Documentation link/diff and repository
boundary checks passed.

The subsequent [historical applicability audit](S22PLUS_FYG8_P364_HISTORICAL_FAILURE_APPLICABILITY_AUDIT_2026-09-08.md)
records that metadata distinction, reproduces a representative successful-state
writer overflow and maps earlier fixes to the current path. No consumed evidence
or production source was changed by that audit.
