# S22+ ML007: IRQ-enable and rest_init boundaries

Preparation checkpoint: **READY_H0_AND_CURRENT_D0_NO_EXPERIMENT**.
Final independent review is **PASS_GO**, with no unresolved findings. Production
qualification, exact task preparation and the unchanged terminal worker's
reviewed backend v16 all passed. The fixed preapproval D0 completed on its
first invocation; seven complete raw Android health captures and its durable
journal rederive current readiness. Process exit alone was not accepted.
No approval, grant, control or partition transfer is armed. Point-in-time
health remains subject to freshness and effect-time checks before execution.

| Preparation receipt | SHA-256 |
| --- | --- |
| Independent review | `7f02862194c2912c9d1c30aa4d2a09c213ae95b9396ce6c4edb3bb9a69a094e4` |
| Mainline capability | `edb6da498eab75075aff8d3af69f1fa5b9a07ee576c9a53e095b13cc3de4bc75` |
| Backend v16 | `0fb267d963849fb84547717fe51e978b84105fc9c583f4f0af789ebf2c9031ca` |
| Exact task | `3ffd6b7258090ecdaeea1455f2e778d3d1a8c4912a063b53c2eb1d0404fd2fe3` |
| Current readiness | `ce8bc9a180a40f9a0fb4f9a8e16cbdae275a076f01d9b34b6dcdb93d0fb489bb` |
| Pre-experiment summary | `a2ea06815ce999d09b6509db065454b89bbc2e24eb099573876be08a14564938` |

The bounded unit is a fresh V5 candidate with one retained marker immediately
before ordinary IRQ enablement and one immediately before `rest_init`. Complete
linked-source and actual-EL qualification, independent review and current
readiness precede its exact one-operation attended approval, physical test,
original-A recovery and the existing post-closure log read. H0 is capability
evidence only. A90 and S20+ remain untouched.

## Selection and proof limits

ML006 recovered six intact post-setup-arch and six post-time-init records and
closed healthy original A. USB/PID1 remained NO_PROOF. Its run is consumed;
there is no separate operator report of its reset behavior. The earlier
ML005 boot-loop observation does not describe ML006 automatically.

Claude Opus 5.5 and Gemini 4 Argon High each completed an initial critique and
a cross-model challenge. Their initial suggestions jumped into `kernel_init`
and its freeable initialization. Both accepted the final narrower pair after
comparing exact task creation, preemption, init-memory lifetime and early-map
callers. The second point covers substantial core initialization without
introducing post-initcall workers, driver ownership or multiple task contexts.
It is not selected to identify reset cause from a missing marker.

Both calls remain in `start_kernel`, on the initial task before `rest_init`
creates PID1 and kthreadd. `sched_init` initializes the low preemption count
to 1, so normal IRQ exit cannot preempt this task. This reasoning does not
rely merely on `maxcpus=1`. Enabled IRQ/softirq/irq_work paths must also lack
a competing early-map user. A writer-local IRQ guard would not serialize an
already suspended competing mapper and is not added.
The preliminary independent static audit pins 39 source/input files and
examines 20 mapper-reference files. Its exact config/DT excludes reachable
ACPI/EFI-family, SDEI and other compiled-out mapper routes before `rest_init`;
no enabled hardirq, softirq or irq_work competitor was found. This is scoped
static evidence; final artifact PASS_GO separately confirms the joined scope.

Stage 9 is after `early_boot_irqs_disabled = false` and immediately before
`local_irq_enable`. Stage 10 is immediately before `rest_init`, after
`kcsan_init`. Stage 10 follows the IRQ-unmask instruction and intervening core
initialization, including console and delay calibration. However, `time_init`
sets `lpj_fine` from the timer frequency, and `calibrate_delay` can bypass a
jiffy-based loop. Neither stage proves IRQ delivery or working timer ticks.
The static records do not encode live DAIF, PID, CPU or preemption count.

A later positive proves that the preceding helper call returned on that
candidate's sequential path; the helper may have skipped recording. It does
not create a missing earlier record, prove a same-boot pair, or prove either
record's own later cleanup/return. Earlier candidates' removed helper calls
remain historical. Missing, damaged or foreign records do not locate a crash,
count attempts, identify the last boot, establish reset cause or create a new
recovery stop. RAM PID1/USB and original-A health remain separate results.

## Implementation and qualification

V5 introduces distinct schema/magic/integrity domain and stages 9/10. The
C writer template is byte-unchanged; only generated names, frames, slot choices
and callsites differ. The two 128-byte slots, untouched 16-byte header,
Normal-NC non-executable temporary mappings, guards, header recheck and reverse
cleanup remain. No IRQ/preemption controls, watchdog, storage, DT, config,
command line, RAM PID1/NCM behavior, transfer or recovery semantics change.
Historical V1-V4 formats retain their original admission and interpretation.

The fresh source comes from the retained unmarked preparation. Complete
comparison confirms only `init/main.c` and its generated marker header differ.
The first manual comparison used a nonexistent conventional source path;
it was corrected to the source path in `prepared.json` and rerun. That H0
check failure did not change any candidate bytes or consumed evidence.

New qualification checks actual linked calls directly before IRQ-unmask and
`rest_init`, with superseded marker symbols absent. The actual Image must pass
real EL1 and VHE EL2 mapping tests at both sites, including no linear alias
across all log pages, positive neighboring-RAM calibration, temporary PTE/MAIR
attributes, slot/PTE cleanup and bounded failure cases. V5 adds initial-task,
boot-CPU, one-online-CPU, low-32-bit preemption-count and IRQ-state observations.
Task offsets come from this build's generated definitions; the upper reschedule
field is allowed to vary. QEMU uses shaped virt hardware and the kernel's
48-bit non-LPA2 fallback. It is not physical cache/page-table proof.

The new codec redecoded complete retained V1/V2/V3/V4 raw captures, preserving
12/12/10/12 records respectively and their original projections. Protected
proof/journal bytes remained unchanged; no new device read was performed.

| Check | Result |
| --- | --- |
| Fresh ARM64 kernel | Image built without errors, warnings or section mismatches; only the two intended source files differ |
| Linked call order and protections | First BL directly precedes `msr daifclr, #3`; second BL directly precedes `rest_init`; PAC and per-task stack canaries remain |
| Actual linked C writer | 318 guard, bounds, mapping failure, header-change and interrupted-store cases passed |
| Exact Image, real EL1/VHE EL2 | 13 mapping cases passed, including each page crossing, slot exhaustion and earlier-skip/later-positive |
| Bootstrap context | Initial task, boot CPU, one online CPU, low preemption count 1, SYSTEM_BOOTING and the two expected IRQ states observed |
| Alias, attributes and cleanup | No linear mapping for 512 log pages; adjacent RAM translates/reads; temporary mappings are Normal-NC/non-executable; PTEs clear and slots restore at both sites |
| Full Image and RAM PID1 | Authenticated VM observer passed, then complete raw evidence rechecked without another VM boot |
| Loader/carrier | 20 linked cases, 1,051 copies, real EL1/EL2 entry and EL3 refusal; two 96-MiB boot images and AP archives match |
| Python regression coverage | 80 distinct focused tests passed across the full suite and the affected retention rerun; touched Python compiles |
| Historical records | V1-V4 complete raw captures reproduce unchanged; protected proof/journal bytes remain unchanged |

The final review packet pins 68 sources and 332 artifacts/raw evidence files.
The independent reviewer verified those joins, the loader-rewritten DT and
complete raw outcomes, and independently rederived frame integrity, package
contents and historical projections. The new public capability and backend
receipts preserve every earlier receipt; the stable worker needed no restart.
Its first construction attempt incorrectly applied the strict nonempty native
record reader to generic H0 artifacts. No packet was published. The private
packet helper was corrected to hash bounded regular artifacts, including empty
logs, and its first source snapshot was retained. Native runtime readers and
all safety checks are unchanged; no image rebuild or test replay was needed.

After capability publication, the current production reader also rederived
the complete ML006 closure and retained projection with acquisition blocked.
All protected proof/journal bytes remained unchanged; no old close was
republished. The new task uses that exact healthy predecessor and original A.

Past-failure applicability: ABI covers exact task layout and actual EL, PAC,
canary and mapping lifetime; SEMANTIC/WIRE preserve positive-only claims;
ROUTE/PERSIST cover V5 producer/consumer admission; ARTIFACT binds the linked
calls and boot-only carrier; HOST retains raw emulator and existing terminal
evidence; RETURN keeps original-A ownership, health and no replay. DISPLAY is
unchanged. Unchanged checks remain reusable on unchanged inputs.

## Private evidence and external-model accounting

Discussion evidence is under
`workspace/private/outputs/s22plus-mainline-ml006-next-discussion-20261030-1/`.
Fresh candidate evidence is under
`workspace/private/outputs/s22plus-mainline-ml007-h0-20261030-1/`.

Four calls completed without failure, refusal, fallback or tool use. Claude
reported 4 uncached input, 39,952 cache-creation input and 24,587 output tokens,
including 17,812 thinking tokens. Its CLI list-price equivalent was USD
0.811372, not a subscription bill. Argon reported 53,058 input and 29,883 output
tokens, including 23,412 thinking tokens, for 82,941 total; cost was unavailable.
Claude five-hour utilization moved from 19% to 22%; Argon weekly remaining
moved from 75.40% to 73.79%. These account snapshots are not exact per-call
quota attribution and may lag. Before/after records were appended privately
without credentials.
