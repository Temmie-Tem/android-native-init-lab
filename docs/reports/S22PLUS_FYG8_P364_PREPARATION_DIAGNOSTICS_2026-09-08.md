# S22+ FYG8 P364 preparation diagnostics

## Scope and current authority

P364 adds fixed authenticated preparation stage/errno evidence to the consumed
P363 candidate design. It retains the exact P361 renderer, five stock modules,
module order/parameters, bounded Download CONTROL, physical fallback and
mandatory exact Magisk rollback. The current task ends at connected preparation
and new F1 code issuance. No candidate transfer or F1 execution is authorized.
P363 remains consumed and CLOSED/19; its original failure errno remains unproved.

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
