# S22+ native source refactor 1A — H0 implementation

Status: **implemented; source/build equivalence PASS; independent PASS_GO.**
Target: SM-S906N / g0q / S906NKSS7FYG8.
Scope: the behavior-preserving 1A unit in the
[phase-1 preparation](../plans/S22PLUS_FYG8_REFACTOR_PHASE1_PREPARATION_2026-09-10.md).

## Result and implementation boundary

The new [direct generator](../../workspace/public/src/scripts/revalidation/s22plus_native_source_v1.py)
reads five explicit public helper fragments and one renderer template, rather
than executing historical candidate Python projections. Candidate namespace,
run identity, display version and private key injection are explicit fields;
the encoded nonce-command run identity is a separately declared C-escaped slot.
The memory census and display module header are generated from typed metadata.

The [source directory](../../workspace/public/src/native-init/s22plus_runtime_v1/README.md)
separates protocol, fixed return preparation, commands/output, HUD ownership and
session entry. Existing internal protocol names and native algorithms remain
unchanged. In particular, HUD startup/ticks/cleanup are still inside the
post-authentication console. Display/console lifetime separation is 1B and has
not been implemented. The USB arrival failure is not repaired by this change.

The historical P381/P382/P383 entrypoints and all consumed source bindings remain
unchanged. The new generation path is exercised by the
[H0 build harness](../../workspace/public/src/scripts/analysis/s22plus_native_refactor_h0_v1.py).
That harness imports the old generator as a comparison oracle and retains the
existing platform compiler/boot reader/packager; the direct production generator
imports no historical candidate code. Deeper source-matched platform source and
F1/evidence orchestration are deliberately preserved. The platform envelope and
compiler still bind `k_run_id`; a future candidate must use the same explicit
identity for that boundary and the helper. No new candidate, live
manifest, source repin, device grant, baseline adoption or version promotion is
created by 1A. Functional v0.1.2 and P383 NO_PROOF/CLOSED/19 remain unchanged.

## Equivalence evidence

Actual production helper materialization is byte-identical for P381, P382 and
P383 identity settings using fixed H0 test keys. Renderer generation likewise
matches those three versions. This includes the encoded identity field; checking
only readable strings would have missed it.

The P383 build comparison then used the retained actual private key and matched
the real materialized helper inside the hash-bound platform runtime. It compiled
that fresh assembly and renderer with the repository toolchain, inspected static
ARM64 ELF outputs, and compared the results with the consumed reference. It
packaged A and B independently with the existing boot-only packager and checked
both complete inventory and transmitted AP identities.

| Output | Bytes | SHA256 / result |
| --- | ---: | --- |
| Public helper template | 68,846 | `2480436b9013fb4c2f59edc396f6a2f4788d7a04448eac2a1323473146b13920` |
| Actual materialized helper | 69,049 | Byte-identical to the retained keyed production helper; bytes stay private |
| Renderer C | 73,589 | `730c514f70492f226d9ce502d11bb59633afe76903cd422eec224eb586d7dc2b` |
| ARM64 `/init` | 149,448 | `28860f110806cc5d8b27d3741bba476f5ad3f09af6d8679e7b20403483fee55a` |
| ARM64 renderer | 778,904 | `a641739898b96bae04ad502707517a67edd523783b508f1368b2842c27521c67` |
| A/B AP | 31,150,121 | `16d723931a86bcb9efe894743995fde8d151991520bd2adbc0853bb71ab8b119` |
| Display module plan | 992 | Byte-identical, 13 ordered display/telemetry entries |
| Boot/package join | — | Both 45-entry ramdisks, all 18 added module payloads, inherited child and fixed Image match |

The new direct source receipt contains 12 inputs: the generator, six templates
and five reachable quoted C includes. This is not the complete platform/build
closure: 348 historical comparison/build inputs and 187 retained compiler/header
inputs are checked separately before and after the H0 build. The generated plan,
configuration, renderer and observation specification have separate receipts.
The existing 86 P383 prepared execution-source receipts remain unchanged.

Final build result: `PASS_H0_NATIVE_SOURCE_EQUIVALENCE`, size34,060,
SHA256 `0cbc62f299505172844f2780625d42e0ffb1fe452908c95cc65ea34a1603315b`.
Private evidence is under
`workspace/private/outputs/s22plus-native-refactor-phase1a-20260910-1/`.
No compiled payload, key or raw device evidence is added to tracked files.

## Behavioral checks and limits

The new focused suite passes **12 tests**. It checks production templates and
keyed source equality, renderer/census/plan equality, invalid identity/key/metadata
rejection, and a clean-process import without candidate namespace dependencies.
Its native health tests run the direct production helper through real host
fork/exec/pipes and the unchanged authentication/raw-replay consumer, including
failed health and freshness rejection. HUD/collector/renderer integration covers
normal commands, memory observation and absent/blocked collection.

The old host fixture requested a larger test-only helper with retired child
support. The new test adapter explicitly substitutes the direct **production**
helper and removes only the unused fixture witness that called the retired
function. It does not silently compare or execute only the test-only branch.
Hardware, root/mount, USB and DRM facts remain explicit fixtures; these tests are
not new target health, physical display or ARM64 device-ABI proof. No syscall
flag or native behavior changed, and the actual target ELF bytes match the
retained baseline. Relevant prior ABI evidence is preserved, not promoted.

Four additional existing backpressure checks passed: host partial-frame credit
retention, host dual-stream burst with a paused reader, and ARM64/QEMU dual-stream
burst plus CONTROL under backpressure. These exercise the unchanged output
implementation; they are separate from the 12 direct-source tests. Target ABI
semantics are not inferred from host fixtures. Touched Python passes py_compile.
Historical unrelated ledger/count failures are outside the touched paths and
were not rerun to qualify this source refactor.

## H0 storage interruption and component reuse

The first build successfully produced identical A/B ARM64 init/child/renderers,
then root filesystem exhaustion interrupted the first package repack. The failure
log, partial package and source evidence are retained. Only this task's generated
`kernel` and `base.img` copies were removed after proving byte equality with their
retained input files, reclaiming142,154,240 bytes. No unrelated data was removed.
The duplicate identities and interruption are recorded in
`build-1-storage-failure.json`; the earlier incomplete output is not called PASS.

Build2 rechecked unchanged direct source inputs, platform source files, renderer
source/header, compiler inputs and exact binary identities before reusing those
compiled components. It performed both package builds in mode0700 temporary RAM
scratch, retained command logs and receipts, and removed scratch only after the
complete package/inventory matched the immutable retained oracle. Identical AP
payloads remain at that original private reference. A failed future scratch build
is preserved with its failure marker; it is not silently deleted.

The final whitespace check then identified extra blank lines at fragment EOF.
Four fragments now end with a single line feed; explicit generator separators
reconstruct the exact prior helper bytes. The initially reviewed inputs remain
in `build-2/reviewed-source-snapshot`, with their original hashes. The harness
also stopped copying unused fixed-Image/module duplicates into the output folder;
those verified inputs remain at the retained reference and feed packaging in memory.

**Build3** freshly compiled both ARM64 userspace and renderer sets under the final
source closure (`components_reused_from=null`), then rebuilt both packages in RAM
scratch. Its full output and metadata match the same consumed oracle. Five source
equivalence tests passed again; earlier production integration results are reused
because their emitted C and final ELF bytes are unchanged. The amended independent
review checked the final delta and build3 receipts.

These H0 storage/formatting corrections changed neither native behavior nor device
recovery. No device commands, transfer or replay occurred.

## Independent review

Independent **PASS_GO**, with no actionable findings, covers the direct generator,
six templates and reachable includes, H0 comparison/packaging harness, test
adapters and source README. The reviewer independently ran all five source
comparison tests; checked a fresh H0 identity including escaped nonce bytes;
rehashed the 12 direct inputs, 348 frozen historical inputs and 12 assembled
platform sources; checked both ARM64 init/child/renderer sets against the oracle;
and verified all 86 prepared execution-source receipts. It reviewed the parent’s
12-test production/consumer integration results without repeating firmware builds.
The final review amendment independently rechecked all five source tests, final
source receipts and both freshly compiled component sets, configuration, assembled
platform sources and A/B package receipts. It returned PASS_GO with no findings.

| Reviewed input | SHA256 |
| --- | --- |
| Exact `source-inputs.json` (sorted keys, indent2, trailing LF) | `8bd73eb469e913607c81c1c95882dd82d967531ae57f1878755bd6896131155e` |
| Direct generator | `09634b4363cfc47d5b2b30d1f1392e6e2a0c68523d84c8167ad34d3f486a46c2` |
| H0 harness | `fc5139a4bc36b85a8b5ecd0f36b0dda7eed3ce030d76c51c430cc9a17d7fd86f` |
| Tests | `9926c0e904720f9dc44d2bb9c62d12f5ba65b4ff2b3be4b7a0b5b3baa61e0be8` |

The review qualifies the prospective H0 common-source implementation. No current
live generator, target contract, candidate identity or consumed claim was changed.
Post-authentication HUD lifetime remains deliberate 1A behavior; this is not
independent boot display, fresh target ABI/device proof or recovery qualification.

Documentation links/fragments, scoped privacy, repository boundary and whitespace
checks complete the bounded unit. Further tests or builds are needed only for
changed paths, findings or subsequent work. Next is the separate 1B lifecycle
design/implementation, with the host arrival investigation kept distinct.
