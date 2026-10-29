# S22+ ML006: post-setup-arch and post-time-init progress markers

Preparation checkpoint: **READY_H0_AND_CURRENT_D0_NO_EXPERIMENT**.
The subsequently approved [ML006 run](S22PLUS_MAINLINE_ML006_RUN_2026-10-30.md)
is consumed and closed healthy, with both return witnesses recovered. The
readiness receipts and absence-of-grant statements below describe preparation
before that execution and remain historical.

Final independent source/artifact review is **PASS_GO**, with no unresolved
findings. Production qualification, task preparation and the connector bundle
reopened the exact candidate after the receipt-path correction. The unchanged
ordinary-terminal worker selected reviewed backend v15 and completed the fixed
preapproval D0. Current readiness was rederived from raw Android health and
the durable journal; process exit alone was not accepted. This point-in-time
health still must satisfy freshness and effect-time checks when a grant opens.

| Preparation receipt | SHA-256 |
| --- | --- |
| Independent review | `665a50fdbbc0f50acc88d3c2b41be318c6f82281e96a506a89080499351f9ba4` |
| Mainline capability | `8b63b28cbbb28e7f817b96aabee6e005de2b9321f6f31d7776b872071c3c2883` |
| Backend v15 | `b8ea30e974df1dbde081691725f41da3a2f16514acb4d6c1aeac22755e31a9b8` |
| Exact task | `31d4ebbc3fdb1eaa84f72478c395d6556ea29e99c9b3939b0dcae0d178c7e005` |
| Current readiness | `b3d33242b76cf722aba21a21c6e5d1835d0c2ec35e2c88143d837505428a1824` |
| Pre-experiment summary | `4e5b0aec40e9d539c1ef5a7866e62bec2eacc0a36793fb3c9eef77989ad4b9b8` |

No operator-approval record, grant or candidate operation exists. Controls and
partition transfers remain zero. The exact returned finite approval and actual
attendance are still required before the physical experiment.

ML005 proved at-least-once progress through the post-FDT and post-paging
recording points, while authenticated RAM PID1/USB remained NO_PROOF. The
operator subsequently confirmed that its boot loop persisted, without a
numeric reset period. Original A and first final Android health passed.
The consumed ML005 run and its immutable evidence are unchanged.

The next bounded unit is a fresh two-site V4 candidate: immediately after
`setup_arch(&command_line)` returns and immediately after `time_init()`
returns, both in `start_kernel`. Its completion criterion is exact linked
calls, guarded writer and actual late-fixmap qualification, independent
source/artifact review, current task admission/readiness, and then one
separately approved attended experiment with original-A return and the
existing post-closure retained-log read. H0 alone grants no device effect.

## Selection and proof limits

Claude Opus 5.5 and Gemini 4 Argon High each completed an initial critique and
a cross-model challenge. Both ultimately accepted the selected pair. Moving
the first point outside `setup_arch` makes return from that function the named
completion. Placing the second before `random_init`, canary initialization
and perf keeps a distinct boundary after core memory, scheduler, IRQ and
timer setup. The region also contains firmware-dependent paths; it is not
purely software. No reset cause is established.

The discussion corrected overclaims about earlier writer cleanup, raw log
offsets counting resets, reusing the V3 stage domain, and inventing generic
diagnostic-corruption or iteration-count stops. A later positive proves the
preceding helper call returned along that candidate's sequential path; it
need not have written or executed both unmaps. Missing, torn or foreign
records are diagnostic outcomes. They do not block original-A recovery or
locate a failure. Neither record proves its own later return, one shared boot,
the last attempt, a boot count, reset cause, PID1 or USB.

V4 has a new schema, magic, integrity domain and fixed stages 7/8. It replaces
both V3 calls; `setup.c` and `head.S` return to their unmarked base bytes.
The existing C template mechanics, two 128-byte slots, 16-byte untouched
header, Normal-NC temporary mappings, guards and reverse cleanup are retained.
Both definitions are included before the complete annotated `start_kernel`
declaration, preserving that function's attributes and the helpers' stack/PAC
protections. Storage, watchdog, DT, config, command line and RAM PID1/NCM
behavior are unchanged.

## Pre-build source checks and qualification scope

The exact ARM64 tree defines late set/clear fixmap operations through
`__set_fixmap`; its clear path calls `flush_tlb_kernel_range`. The page tables
are permanent kernel data, and early-map slot state remains live until
init memory is freed. The two sites precede IRQ enablement and canary
initialization; PSEUDO_NMI, KASAN and shadow call stack are disabled, while
per-task canaries and kernel PAC are retained. An independent initial design
review found no concrete blocker; it is not approval of the unwritten final
implementation or artifact.

Candidate and retained live DTs both specify PSCI 1.0 with the SMC conduit.
The actual non-stub DT and forced command line select the DT path in
`acpi_boot_table_init`; no new whole-board emulator or ACPI gate is needed.
Existing fixed no-map and artifact checks remain applicable. The VM fixture
models QEMU hardware, with the exact Image using its 48-bit non-LPA2 fallback;
it does not prove physical cache coherency or the physical table format.

The added evidence is actual EL1/VHE EL2 late mapping at both calls,
IRQ masking and boot state, no linear alias across the log slice with positive
neighboring-RAM calibration, temporary PTE/MAIR attributes and complete
cleanup. The existing bounded guard, map-failure and interrupted-store corpus
exercises both linked writers. Earlier formats retain their old meanings.

| Check | Result |
| --- | --- |
| Fresh full kernel producer | Standard ARM64 build completed; complete source-tree comparison finds only `init/main.c` and the generated header changed |
| Linked writer and callsites | 318 cases passed; each actual call follows its named return directly; old marker symbols are absent |
| Compiler protections and unmap primitive | Both helpers contain PAC and per-task canary checks; linked `__set_fixmap` contains TLB invalidation and barriers |
| Exact Image with real mappings | 13 EL1/VHE EL2 cases passed, including both page crossings, mapping pressure, header mutation and earlier-skip/later-positive |
| Late context, aliases and attributes | Both sites run with the late selector set, IRQs masked and boot state; all 512 log pages lack a linear alias, positive neighbors translate/read, and temporary PTE/MAIR values are Normal-NC and non-executable |
| Cleanup | Both actual helper calls return with temporary PTEs cleared and slot state restored |
| Full kernel VM with distinct VM PID1 | Authenticated RAM PID1 observer passed; complete raw capture rechecked offline |
| Loader and carrier | 20 linked loader cases, 1,051 copy cases and actual EL1/EL2 entry plus EL3 rejection passed; two 96-MiB boot packages and their AP archives are identical |
| Historical formats | New codec reproduces complete retained V1/V2/V3 results without acquisition; original proof and journal bytes stay unchanged |
| Focused Python suite | 76 tests passed after the producer correction, including rejection of missing V4 qualification evidence and unchanged V3 admission; touched Python compiles |

The V4 mapping fixture reserves the two neighboring calibration pages without
`no-map`. They retain ordinary linear translations while their sentinel data
stays outside buddy allocations. This is only a QEMU positive control and
does not alter the physical DT or conceal a mapping inside the log hole.
The full PID1 VM also uses a shaped no-map DT, with its invalid log header
exercising the write-skip path. It proves no physical peripheral boot.
After current capability publication, the production post-closure reader also
rederived ML005's complete retained projection with acquisition blocked and
all 23 protected proof/journal records unchanged. No old close was republished
and no consumed artifact or review was repinned.

Final review found a pre-existing H0 producer mismatch: image qualification
hardcoded earlier test-directory names, while the new package correctly named
its own successful receipts. The producer now takes explicit loader-test and
entry-VM directories, checks their hashes against the package before output
creation, and retains the exact reviewed receipt paths. Missing or mismatched
receipts fail without creating an output directory. This changes no candidate
bytes, consumed record, runtime authority or no-replay rule; no rebuild was
needed. The new regression and affected qualification tests passed.

Past-failure applicability: ABI covers real EL/PAC/canary and mapping lifetime;
SEMANTIC/WIRE preserve positive-only stage meanings; ROUTE/PERSIST cover the
new source location and exact format admission; ARTIFACT binds actual linked
calls and the boot-only package; HOST covers the existing emulator and terminal
route; RETURN preserves original-A and no replay. No transport implementation
or display channel changes. Unchanged checks may be reused on unchanged inputs.

## Private evidence and external-model accounting

Discussion evidence is under
`workspace/private/outputs/s22plus-mainline-ml005-next-discussion-20261030-1/`.
Fresh candidate evidence is under
`workspace/private/outputs/s22plus-mainline-ml006-h0-20261030-1/`.
Only S22+ FYG8 is selected; A90 and S20+ remain untouched.

Four external calls completed without failure, refusal, fallback or tool use.
Thinking is included in output totals. Claude reported 4 uncached input,
46,595 cache-creation input and 24,845 output tokens, including 17,455 thinking
tokens; its CLI list-price equivalent is USD 0.869676, not a subscription bill.
Argon reported 58,063 input and 24,040 output tokens, including 16,006 thinking
tokens, for 82,103 total; cost was unavailable. Claude five-hour utilization
moved from 13% to 17%; Argon weekly remaining moved from 77.76% to 75.18%.
These account snapshots are not exact per-call quota attribution. Private
append-only before/after records contain no credentials.
