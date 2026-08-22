# A90 RTIC stock-equivalence requirement recalibration — H0

Date: 2026-08-22
Target: Samsung Galaxy A90 5G only
Tier: H0 host-only evidence and sequencing decision
Device contact: none
Authority: none — no candidate, D0, D1, F1, approval, manifest, transfer,
reboot, rollback, replay, or live authority is created

## Verdict

Literal byte equality with the stock 1,624-byte RTIC MP is **not** the correct
next gate for a rebuilt kernel. The MP describes the kernel being booted. A
candidate-specific layout field is allowed—and may be required—to differ from
stock when the candidate's linked memory extent differs.

The current stock-shaped rebuild is still not ready for candidate
qualification. Its four task-structure offsets are emitted as
`0xffffffff`, even though the same unmodified parser recovers the exact stock
values when pointed directly at the three correct object files. That is a
known host locator defect, not an unknown device-acceptance question, and it
remains a static `NO_GO` until regenerated without sentinel values.

After that repair, the remaining proprietary-acceptance uncertainty is an
explicit hazard bundle, not another indefinitely expandable static
equivalence gate. It includes the non-stock MPGen content version, the
candidate-derived extent/range, public tool/catalog provenance, and any
proprietary RTIC/QHEE or whole-Image enforcement absent from available source.
The public interface is `30.3`, but exact A90 consumer behavior is unavailable.
A bounded boot canary is the discriminator once all known static defects are
removed and the complete bundle receives independent review.

## Evidence being reclassified

The stock-shaped deterministic rebuild already proves all of the following:

- the historical public catalog has the exact stock ordered feature set:
  RO 3, WK 1, WU 2, AW 0;
- all six generated asset records match stock in name, address, length,
  attributes, digest where applicable, and writer address/length where
  applicable;
- the MP address is `0xffffff8009f00000`, the raw-Image offset is
  `0x01e80000`, and interface is `30.3`;
- the generated RTIC DTB selects the generated in-Image MP and its SHA-256
  matches exactly; and
- two output trees produce identical MP source/XML/DTS/DTB, `System.map`, and
  initramfs bytes under the fixed clock.

Stock and rebuild MP are equal in length and differ in exactly 22 bytes:

| Delta | Classification | Required treatment |
|---|---|---|
| content-version suffix: `f86a6` vs `26468` | tool provenance and unproved RTIC-consumer compatibility | retain honestly; do not forge the stock string; bind in the full reviewed canary hazard |
| kernel extent: `0x03973000` vs `0x039d3000` (+`0x60000`) | candidate-specific linked-layout measurement whose proprietary acceptance is unproved | require derivation from rebuilt symbols/output, do not force stock equality, and bind acceptance in the same hazard |
| task offsets: `(88,1704,1728,2144)` vs four `0xffffffff` | deterministic public locator failure | repair before qualification; sentinel values remain `NO_GO` |

## Why kernel-size equality is the wrong predicate

The generated MP and its RTIC DTB are a matched producer/consumer pair for the
rebuilt Image. Replacing the generated extent with the stock extent merely to
make the MP bytes equal would describe a different kernel and could leave a
candidate-specific memory range outside the declared measurement. The safe
predicate is therefore not `candidate_size == stock_size`; it is:

> the unmodified generator derives the extent from the same final candidate
> link products, the extent contains the intended kernel range, and the RTIC
> DTB hashes the resulting exact MP bytes.

This report does not claim that `0x039d3000` is accepted by proprietary RTIC.
It classifies it correctly: a self-consistent candidate value, not a known
stale-binding defect. Exact stock equality cannot prove acceptance either,
because the candidate Image is not the stock Image.

## Why the task offsets remain blocking

The four `0xffffffff` values are not an unavoidable custom-kernel difference.
The public locator sees 3,943 compilation units but fails to map the relevant
out-of-tree `O=` paths. Running its unchanged decoder directly on
`init/main.o`, `init/version.o`, and `init/init_task.o` yields the stock-exact
values `88`, `1704`, `1728`, and `2144`.

The next build must fix path discovery rather than patching MP output:

1. keep the selected public MPGen Git tree byte-clean;
2. expose the exact hashed object files through the path form expected by the
   unmodified locator, using a build-wrapper mapping outside the MPGen tree;
3. reject missing, duplicate, or ambiguous object matches;
4. require the generator itself to emit the four non-sentinel offsets; and
5. compare those values to an independent direct-object decode before link
   output is accepted.

Hard-coding or post-editing the four offsets is forbidden for this control.
The point is to prove the producer works on the actual build closure.

## Exact next build gate

One private-host rebuild may advance only if it records all of these facts:

- pinned OSRC/config/Snapdragon LLVM 10.0.7/GNU 4.9 and historical public
  MPGen identities;
- stock-fixed MP time without modifying MPGen source bytes;
- exact object-path mapping plus every mapped object's size and SHA-256;
- zero fatal catalog or locator warning;
- exact ordered RO/WK/WU/AW `3/1/2/0` set;
- task offsets `88/1704/1728/2144`, with no `0xffffffff` sentinel;
- candidate-derived kernel extent and the symbols/inputs from which it was
  derived, without a stock-equality assertion;
- one `rtic_mp` symbol, one RTIC DTB, one `MP_DATA`, interface `30.3`, in-Image
  range, marker, and exact MP SHA-256 equality;
- build-input/path normalization that makes `DW_AT_comp_dir` stable before
  linking; post-link build-ID or Image byte patching is forbidden;
- a fresh final MPGen pass after that normalization, followed by two
  independent output trees whose complete Image, MP source/XML/DTS/DTB,
  `System.map`, and initramfs bytes are pairwise identical; and
- one exact hazard statement binding all residual acceptance uncertainty:
  non-stock content version `2.7.e26468.30`, candidate-derived extent/range,
  public tool/catalog provenance, proprietary RTIC/QHEE behavior, and any
  proprietary whole-Image measurement remain unproved.

The build output remains H0. It is not a boot image or candidate merely
because these checks pass.

## Candidate decision after the build

If the locator and deterministic-build repairs succeed, independent review
should decide whether the complete residual hazard bundle is acceptable for
one attended boot canary. No member may be omitted merely because the MP/DTB
pair is structurally self-consistent. That canary's claim is narrow:

> Does stock-platform A90 accept one structurally self-consistent,
> stock-policy-shaped RTIC kernel produced by the available public 2.7 tool?

It does not claim production-tool equivalence, general kernel stability,
BinderFS readiness, or final isolated-Debian readiness. A failure must use the
already implemented first-opportunity TWRP evidence and one-shot rollback
paths; it cannot replay H34 or any future candidate.

Even after a review accepts the hazard, a fresh candidate identity,
candidate-specific qualification and manifest, current owner/continuation/
postrollback bindings, connected D0, attendance, and the exact F1 approval
remain separate prerequisites.

## Independent H0 design review

The initial adversarial review returned `NO_GO` with one medium and one low
finding: the residual hazard statement named only the content-version delta,
and the deterministic-build gate did not explicitly exclude post-link
build-ID patching or require a fresh final MPGen pass over two complete
independent outputs.

This report was amended to bind the complete proprietary-acceptance hazard
bundle and to require pre-link input/path normalization, forbid post-link
Image changes, rerun MPGen, and compare the complete output set pairwise. A
bounded delta re-review then returned `PASS_H0_DESIGN` with no high, medium, or
low finding. That verdict qualifies this host-only sequencing decision only;
it is not a candidate qualification, capability activation, or live review
lease.

## Boundary

This decision used tracked source, validators, and existing reports only. It
did not read `workspace/private`, enumerate `/dev`, contact USB, invoke ADB,
open recovery/serial/network transports, or touch another target. It changes
no current review and grants no device or candidate authority.
