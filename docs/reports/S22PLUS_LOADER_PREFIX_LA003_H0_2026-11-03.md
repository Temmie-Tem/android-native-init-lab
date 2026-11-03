# LA003 mainline prefix live witness — H0 preparation

Status: H0-qualified and independently reviewed; the separately approved
[November 4 run](S22PLUS_LOADER_PREFIX_LA003_RUN_2026-11-04.md) is consumed and
closed healthy with positive current-boot prefix-return proof.
Preparation began on November 3 and continued on November 4, 2026 (KST).

After ML016 again returned no retained V1 frames, two rounds of independent
Claude Opus 5.5 and Gemini 4 Argon High discussion selected a different
observation: enter a fixed early mainline prefix and return to the exact
vendor Android kernel in the same attempt. The final product remains mainline
Linux with Debian host PID 1. This bounded witness supplies no complete
mainline boot, PID1, USB or historical-cause claim.

## Design and concrete correction

The candidate embeds two full Images and uses one payload destination in two
phases. Its mainline `primary_entry` calls the existing V1 writer and returns
before `record_mmu_state`; the resident loader then overwrites that destination
with the exact original-A vendor Image. The live ABL FDT and assembled initrd
remain the vendor inputs. This differs from the historical mainline-DTB path.

Independent design review found that adding the second Image to the old
staging address would overlap a retained firmware reservation even though the
96 MiB boot envelope has capacity. LA003 therefore uses staging at `0xaa000000`.
The actual enlarged file, BSS/stack, source, live FDT/initrd, union payload
runtime and final FDT must pass current placement checks. Other variants keep
their original staging; unsafe geometry parks.

The fresh 256-byte final-FDT report records the actual returned entry PC and
CPU state, plus external before/after LOGM headers and post-call slot byte
comparisons. Exact LA002 live-FDT layout guards are shared without changing
their conditions. The unchanged V1 assembly writers return no status, so
matching static bytes do not prove current-attempt stores or commits. Header
samples do not prove absence of intervening writes. No reset/retention or
ML012–ML016 cause is inferred.

The existing owner collects one fixed report between complete same-boot
Android proofs, then performs its normal Download/original-A return. Failure
retains physical Download and the original one-shot A. No post-closure log
reader, new peripheral control, storage effect or generic context restore is
introduced. The finite attended approval remains a separate final step.

## Validation and review

The fresh full mainline Image build retains the corrected ML012 configuration
and DTB preparation provenance; only its returning entry recipe is selected.
The DTB is provenance for this build and is not the live prefix argument.
The complete loader is 85,525,184 bytes. Its staging runtime is
`[0xaa000000, 0xaf392000)`, below the nearest retained reservation. The shared
payload interval covers the larger 44,826,624-byte runtime. The original
96 MiB boot envelope is retained; two independent boot/AP packages are
identical and each AP contains only `boot.img.lz4`.

- 113 actual instruction cases cover pre-store rejection, all 64 retained
  source displacements and four complete dual-copy/return/vendor paths.
- 43 actual prefix cases cover index/wrap boundaries, preexisting frames,
  CPU/layout skips, all four header-word drifts at both sites, interrupted
  stores and bad returned PC/CPU/cookie. Callee-saved registers and SP survive.
  Local diagnostic cases accelerate only the separately qualified Image copy;
  the full-loader and actual-EL cases execute the complete copy instructions.
- Four maximum-input/allocation cases cover the real FDT producer's 768-byte
  headroom and fixed report. The existing 1,051-case aligned-copy corpus passes.
- Real EL1 and EL2 QEMU fixtures execute both full copies, actual Image-header
  and prefix return, then exact vendor handoff. EL3 rejects before stores.
  No debugger register injection supplies these execution levels or results.
- Six actual compiled-producer reports pass sealed-raw/production-decoder
  rederivation, including all three final report states and unfinalized rejects.
  Host observation tests pass 55 cases; terminal/recovery tests pass 78.
  Touched Python compiles and touched C objects are ARM64.

The initial loader patch application failed in H0 because a generated diff
hunk lacked suitable trailing context; a regenerated exact diff applied cleanly.
The first forward-copy fixture put its synthetic FDT inside inherited initrd;
the next placed its source stub inside the later staging BSS. Existing access
invariants rejected both. A disjoint FDT and source beyond the complete staging
runtime passed. Only that incomplete case was rerun; unchanged successful
functions and the complete retained FDT outputs were checked before reuse.
Neither fixture failure required a runtime guard change.

Independent source review also found an eager marker-generator import in the
new host codec that made an unrelated generator a recovery import dependency.
The terminal corpus reproduced it. Lazy candidate-only import corrected it,
and all 78 terminal tests then passed. Fresh loader rebuilding produced
byte-identical loader and ELF files. Current parsing of the retained actual-EL
and complete-copy FDT reports matches the original results. The shared LA002
LOGM-layout extraction also produces a byte-identical original LOGM object.
Original producer pins/bytes and current checker provenance remain distinct.

Final independent source/artifact review returned `PASS_GO` with no unresolved
findings, binding 76 source files and 370 artifact/raw-evidence pins. The new
`s22plus_loader_prefix_v1_review.json` capability and persistent backend V25
receipts are published. The connected ordinary-terminal worker confirms V25
with its two stable sources unchanged; it required no restart.

The fresh task binds the exact candidate, original A and the preceding closed
ML016 recovery evidence. The named fixed preapproval D0 completed successfully;
all seven raw health captures rederived exact original-A health before approval.
The operator subsequently returned the exact 1800-second, one-operation
attended approval and confirmed usable physical Download recovery. N and A
each transferred once. Current-FDT prefix-return proof passed; after one
preserved ADB read failure, a health-only continuation proved final original-A
health. That operation and grant are consumed and cannot be reused.

Historical receipts and consumed tasks remain unchanged. The separate
mainline capability has not been renewed for the changed shared source closure;
this review covers the selected loader-prefix operation. A90, S20+ and the
preexisting unrelated Debian changes remain untouched.

Applicable past-failure rows are ABI, WIRE, SEMANTIC, ARTIFACT, ROUTE, PERSIST
and RETURN: exact prefix calling convention, live report/raw rederivation,
static-frame proof limits, two-image packaging/source identity, descriptor
selection and unchanged original-owner recovery are verified by the cases above.
Other-target and unrelated Debian work remain outside this unit.

## External discussion accounting

All four discussion calls completed without a model fallback. Claude reported
4 input, 48,253 cache-creation and 27,575 output tokens, with 20,316 thinking
tokens included in output. Its account five-hour usage moved from 0% to 5%;
the delayed account meter is not per-call attribution. Argon reported 60,853
input and 34,854 output tokens, including 26,765 thinking tokens, and 95,707
total tokens. Its weekly remaining meter moved from 44.53% to 41.14%.
Private before/after records retain timestamps and raw provider evidence.
The Claude list-price equivalent of USD 0.93754 is an estimate, not a
subscription invoice or measured charge.
