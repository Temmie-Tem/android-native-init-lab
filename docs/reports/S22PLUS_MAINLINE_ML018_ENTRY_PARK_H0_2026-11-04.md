# S22+ ML018 ordinary-route entry park — H0 preparation

Target: Samsung S22+ `SM-S906N/g0q/S906NKSS7FYG8` only.

Status: **PASS_GO; production preparation and fixed preapproval D0 pass.
No new F1 approval or grant.**
ML017 remains consumed and closed original Android healthy. A90 and S20+ are
untouched. Existing unrelated edits and all consumed artifacts are preserved.

## Selection and question

After the [ML017 result](S22PLUS_MAINLINE_ML017_RUN_2026-11-04.md), two rounds
with Claude Opus 5.5 and Gemini 4 Argon High selected one ordinary-route kernel
entry park. The first Argon attempt returned no answer at its ten-minute CLI
limit; one shorter retry completed. All attempts, available account quotas and
token counters are retained privately, including the incomplete attempt's
rounded UI counter. Its timeout-zero CLI counters are not zero-consumption
evidence. Quota changes, token counters and Claude's list-price equivalent
remain separate from actual subscription billing.

Source inspection rejected the first-round suggestion that later final-Android
logging or delayed D0 acquisition wrapped `/proc/last_kmsg`: the pinned FYG8
reader copies the old ring into a separate snapshot before current logging.
Its exported bytes omit the header index. Text banners cannot authenticate a
candidate boundary or prove coverage of an absent slot. The ordinary mainline
loader also uses its embedded DTB; it does not parse the incoming vendor live
FDT used by the separate LA003 comparison. Current loaded module behavior was
not newly measured, and no historical reset or retention cause is inferred.

ML018 asks whether fresh V1 records are observable after the ordinary loader
route and original-A return when the candidate's normal kernel continuation
has been replaced by an early park. It does not run PID1 or USB. A positive
answers only this candidate's bounded occurrence/retention question; a zero
does not establish execution depth or park reach. This is one diagnostic, not
a required gate for functional work or a sequence of progressively later parks.

## Exact change

The ordinary loader, ML017 DT and kernel configuration, two V1 writers and
normal original-A recovery remain selected. The fresh candidate's
`primary_entry` calls its unchanged V1 writer and then executes exactly `wfe`
and a branch back to that instruction, before `record_mmu_state`. It contains
no runtime or VM-specific escape. The complete new Image is built from the
retained source with only the fresh frame and fixed park source change.

The optional `entry_park` declaration and qualification join the exact source,
Image, loader, package and independent review. Omitting diagnostic metadata
cannot turn the parked artifact into an ordinary RAM-PID1 candidate. The
actual full loader/Image must reach and remain within the park at real QEMU EL1 and
EL2, preserving entry EL; invalid-magic and short-index cases must skip both
writers and still reach the park. The existing loader guard and marker
boundary/interruption tests remain applicable. Exact linked bytes prove the
WFE/back-branch structure; the bounded debugger PC trace may remain waiting at
WFE and does not claim that the branch executed. Prior unparked PID1 VM evidence
is component history only and is not ML018 qualification.

The [mainline policy](../operations/S22PLUS_MAINLINE_RAM_V1.md) and
[target adoption](../operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md) retain
the finite 1800-second, one-operation attended grant, fixed 120-second
observation, physical Download/original-A return, health and no-replay rules.
There is no new MMIO, reset, storage or recovery command. Existing V1 RAM-write
bounds are unchanged. Expected USB absence carries no stage or causal meaning.

## Interpretation fixed before any run

| Returned V1 records | Supported observation | Next decision |
| --- | --- | --- |
| Loader and kernel | Both fresh-build stages occurred at least once and matching bytes survived to the returned snapshot. | Select further full-progress work only from a concrete source-backed hypothesis; no park ladder. |
| Loader only | Loader-stage occurrence and returned bytes; kernel frame absent. | No bounded handoff-failure inference; inspect only a concrete new skip/state question if one exists. |
| Kernel only | Kernel-stage occurrence and returned bytes; loader frame absent. | No inference that the loader failed to execute; any next work needs independent justification. |
| Neither | No candidate frame in the complete capture. | Stop this park approach; no unchanged repeat. Seek a concrete functional fact or a separately justified observable. |

No row proves physical stop PC, continuous WFE, a unique attempt, same-boot
pairing, historical execution depth or a cause of ML012–ML017's zeros. A later
healthy Android return is recovery/health evidence, not candidate success.

## Validation and review

The complete source comparison confirms only the fresh V1 frame and fixed park
in `head.S`; the DT and kernel configuration equal ML017. The actual Image is
43,969,024 bytes, runtime 44,826,624 bytes, and the ordinary loader remains
44,461,936 bytes after measured layout validation. No unchanged geometry was
assumed before building.

The actual V1 instruction matrix passes 342 cases and six real-EL writer
fixtures. Existing loader checks pass 1,051 aligned-copy subcases, 20 placement/
full-loader cases and three real-EL entry fixtures. Both independent boot/AP
packages match. Four actual full-loader/park fixtures pass, including EL1, EL2,
invalid magic and short index; their raw buffers pass the production decoder
with the expected positive/negative frames and reject a wrong key. All bounded
PC traces remain at WFE; no back-branch execution is claimed.

The actual diagnostic consumer rejects 17 mutations, including simultaneous
surface-declaration omission, wrong Image/source, missing EL2, wrong state,
escaped PC, false physical/PID1 claims, missing raw evidence and raw/summary
mismatch. Six fixed-source/admission tests, 18 retained-marker source tests and
82 host/terminal regressions pass. Touched Python compiles; the new Image and
entry object have the expected ARM64 formats. The existing init compiler output
is checked as a component only, without claiming it executes in this candidate.

Two early QEMU fixture attempts incorrectly required an unprompted WFE to
advance under debugger stepping. Both failures are retained; removing the
hardware breakpoint alone did not fix that assumption. The corrected bounded
PC observation keeps exact linked-byte validation and injects no event/state.
The raw consumer then found QEMU's termination message appended after the
initial stderr hash. Sealing now follows producer exit and stream closure;
only those four affected diagnostic fixtures were repeated on identical
artifacts. Stable loader, marker and package checks were reused. QEMU/GDB
identities remain H0 producer provenance, not effect-time device dependencies.

Final independent source/artifact review is **PASS_GO with no unresolved
findings**. It independently reproduces all four full-loader park cases and
their raw bytes, verifies source/ELF/loader/AP joins, admission negatives and
ordinary ML017 compatibility. The source-declaration omission and missing
checker evidence pin were corrected before publication.

The fresh mainline entry-park capability and backend V27 receipts are
published; the stable worker is unchanged. The distinct loader-Android
capability is not renewed by this mainline review. Unmocked production image
qualification, task preparation and the named fixed seven-read preapproval
D0 pass. Readiness is rederived from its sealed raw health and durable journal;
process exit alone is not its proof. No candidate control, partition transfer,
approval record or grant exists. Fresh machine binding and the exact returned
attended approval remain required before any prospective F1.

Past-failure checklist applicability: ARM64/ABI and ARTIFACT apply to the actual
entry instructions, EL, full Image and package identity; ROUTE and PERSIST apply
to diagnostic declaration/receipt admission and raw-to-summary joins; WIRE and
AUDIT retain positive-only interpretation and immutable source/raw provenance;
RETURN and HOST retain the unchanged attended recovery and health-only
continuation. Installed-root persistence, display and peripheral-control rows
are inapplicable to this RAM-only early park. No H0 result establishes physical
entry, USB/PID1, current health or device authority.

Private preparation: `workspace/private/outputs/s22plus-mainline-ml018-h0-20261104-1/`.
Discussion: `workspace/private/outputs/s22plus-ml017-next-discussion-20261104-1/`.
