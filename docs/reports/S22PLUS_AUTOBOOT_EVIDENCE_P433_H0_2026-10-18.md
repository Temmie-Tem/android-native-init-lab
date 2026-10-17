# S22+ P433: fixed two-file read of P432 boot evidence

Status: **READY_AWAITING_FINITE_ATTENDED_GRANT**. No P433 grant, mode change or
image transfer exists. Fixed connected D0 preparation is complete.
The operator requested preparation of a read experiment and a determination of
how far P432 booted. Only S22+ FYG8 is selected; A90 and S20+ are excluded.

The [P432 run](S22PLUS_DEBIAN_AUTOBOOT_P432_RUN_2026-10-18.md) is consumed,
`NO_PROOF` and `ANDROID_CLOSED_HEALTHY`, with one N/A pair and no F1 owner.
Its original records and outcome remain unchanged. This reader never starts
P432 again and does not execute installed Debian.

## Bounded unit and completion criterion

Prepare one fresh P433 `v0.8.0-rc.2` boot-only reader under the existing
[root-evidence owner](../operations/S22PLUS_NATIVE_ROOT_EVIDENCE_V1.md), with
one operation, 1800 original BOOTTIME seconds and original-A return. The new
`autoboot-pair` selection replaces the historical log table with exactly
`var/lib/lab/s22-early-<sealed-run>` and `var/lib/lab/s22-evidence-<sealed-run>`
for P432. Their full-file bounds are respectively 16,384 and 15,616 bytes.

The unit is ready only after actual A/B packaging, representative ARM64 reader
and failure qualification, protocol/collector negatives and an independent
source-bound review pass. Connected fixed D0 preparation may establish fresh
Android health but opens no grant. Execution needs its separate returned finite
attended grant and current usable Download recovery. Completion then requires
the bounded capture, original-A health/closure and an evidence-limited report.

## Retained restrictions and interpretation

Exact GPT/UUID and partition-only RAM RO checks, unprivileged static libext2fs,
the inherited read budgets and settled-child proof are retained. The reader
mounts nothing, replays no journal, writes no filesystem data and follows no
caller-selected paths or symlinks. Both files require root-owned 0600 regular
single-link metadata. Missing, unreadable, rejected or oversized files remain
separate outcomes, with no invented contents or second invocation.

The pair's maximum binary result is 32,256 bytes including both row headers and
framing. The 65,536-byte parent cap remains unchanged. The same sealed selection
derives the C child/supervisor limits and Python parser bounds; the default
historical selection remains at 24,576 bytes. Qualification must exercise both
maximum files through the real producer/consumer and complete outer framing.

The H0 collector preserves both raw files before interpretation and authenticates
P432's exact physical run/key and source hashes. Each valid prefix is useful
independently. When both are present, boot and derived nonce must agree. A
runtime-only header's boot, nonce and root device are authenticated local facts;
they are not an external transition or SSH witness. The final report separates
initial PID1/preparation, pre-unmount progress, installed-init/rc stages and
service duration. Missing home-block records never prove non-execution, and a
valid prefix cannot establish later cleanup or clean shutdown.

The physical writer image, VM substitutions and earlier consumed reader images
keep their own provenance. A new dedicated P433 review selects the updated
reader; no P431 or P432 approval/review is repinned. Private paths, keys and raw
contents stay under `workspace/private/`.

## Qualification and corrections

The final paired ARM64 helper passes 16 real-VM cases: clean, dirty,
journal-only, missing, symlink, hardlink, oversize, directory/inode/group
descriptor checksum, wrong UUID/GPT, both files at maximum size, and missing,
oversized or hard-linked runtime evidence. Each writable regular-file disk
fixture remains byte-identical after acquisition. The default historical
selection also passes a real ARM64 clean read. These are virtual-board tests,
not Samsung execution or persistence evidence.

The first inode-checksum case exposed a pinned libext2fs 1.47.2 cache defect:
failed checksum validation can replace a cache slot's bytes while preserving
its old inode number. The next file lookup then used the wrong inode bytes.
The reader now checks RAM-only `ext2fs_flush_icache()` before each sealed path.
The same corrupted fixture preserves the first file's checksum error and
retrieves all second-file bytes. The independent review reproduced the cause
with the exact ARM64 libraries; storage callbacks and global I/O budgets remain
unchanged. The original failing result is retained privately.

The first full build also rejected a kernel identity substitution whose
compressed configuration changed its frozen span length. Bounded fresh-identity
selection and the actual checked forward/inverse transform resolved this H0
failure; the layout guard and failed build record are retained.

All 49 focused tests pass, including actual C/PTY maximum-output collection and
raw rederivation, task/artifact scope checks, partial authenticated prefixes,
missing peers, conflicting authenticated headers, physical versus VM source
identity rejection, and raw-first collector plumbing. All 11 touched Python
files compile. Physical and virtual helpers are static AArch64 ELFs with
byte-identical independent A/B builds.

Past-failure applicability: ABI/IO/WIRE are confirmed by the actual ARM64
reader and C/PTY maximum frame. SEMANTIC/AUDIT distinguish per-file read failure,
authenticated prefix, combined-boot conflict and missing home-block data.
PERSIST/ROUTE cover empty/raw-before-parser saves, physical installed-init
metadata and the real collector entry point. ARTIFACT is confirmed by the final
actual A/B package audit and independent source-bound review. HOST preparation
passes the fixed connected D0 and actual task validation; RETURN still requires
the later attended operation. DISPLAY is outside this reader's success
criterion. No qualification result grants device authority.

Private qualification evidence is under
`workspace/private/outputs/s22plus-autoboot-evidence-p433-h0-20261018-1/`:
`helper-physical-2`, `helper-virt-2`, `vm-2`, `vm-legacy-2`,
`focused-tests-final.log`, `producer-fixtures` and `review`.

## Ready binding

The independent final review is **PASS_GO**, with no unresolved findings. It
binds 137 reachable host sources, 165 physical runtime sources, the actual
qualified `package-2/image.json`, both independently built AP payloads and the
collector's physical-versus-virtual identity checks. The new dedicated
`s22plus_native_root_evidence_p433_review.json` preserves all earlier review
files. The exact reviewed sources are retained in a private snapshot.

The fixed connected preparation completed exact original-A health brackets,
shell-v2, GPT and Android32 statfs checks. Its raw projection rederives, the
prepared live task validates, and the shared F1 owner is absent. The concrete
task selects only `root-evidence`, one operation, 1800 BOOTTIME seconds and
attended original-A recovery. No grant is opened and no operation is reserved.

The next permitted step is the operator's exact returned finite approval and
current attendance with usable physical Download recovery. The reader then
captures its two sealed files once, returns to original A, proves Android
health and closes before H0 interpretation. P432's physical internal progress
remains unknown until that separate acquisition supplies authenticated records.
