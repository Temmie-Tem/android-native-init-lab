# S22+ mainline boot and observation discussion

Date: 2026-10-28. Target: SM-S906N / g0q / S906NKSS7FYG8.
Scope: external-model discussion and retained-source H0 fact checking.
No device commands, runtime edits, image builds, grants or activation occurred.
A90 and S20+ were untouched; the paused vendor boot-journal changes were preserved.

## Assessment

Keep the current boot-only ABL → uniLoader → mainline Image / private g0q DTB /
RAM initramfs route. The next useful work is to establish a discriminating
observation plan and resolve the remaining cheap entry questions against the
retained artifacts. There is no established ML001 root cause to repair yet.
Changing cache operations, relocation, kernel placement, idle policy and USB
profile together would obscure which change mattered.

[ML001](S22PLUS_MAINLINE_ML001_RUN_2026-10-28.md) proved one N transfer,
117 bounded samples with the fixed USB2 node absent, one attended original-A
return and final Android health. It did **not** prove ABL acceptance of the
candidate, uniLoader entry, mainline kernel/PID1 progress or automatic recovery.
The logo and warning are not execution markers. The samples are not a continuous
USB-bus trace and cannot exclude an attachment between samples.

The actual loader disables SIMPLE_FB/EARLYCON; the kernel disables DRM/FB and
uses `console=tty0` with a dummy console. PID1 sends diagnostic text to
`/dev/console`, falling back to `/dev/null`, and parks after failure. Thus an
unchanged display is expected to be uninformative even if considerable code ran.
There is an authenticated USB channel late in the boot; there is no qualified
independent early channel in this candidate.

## Boot chain and the evidence needed at each boundary

| Boundary | What is established | Missing physical evidence / useful next observation |
| --- | --- | --- |
| Odin → ABL raw-image handoff | Boot-only packaging and transfer; retained normal ABL path analyzed | Candidate acceptance, source placement and actual entry state |
| uniLoader entry → relocation | EL/state/range/collision guards and actual linked copy path qualified in H0 | Which guard, if any, rejected on g0q; a marker after relocation cannot answer this |
| Relocated C → kernel branch | Stack/BSS, actual kernel/initrd copies, DT rewrite, argument registers and ranges qualified in H0 | Actual branch execution and effective Gunyah memory/cache/trap conditions |
| Kernel entry → initcalls | Actual kernel and RAM userspace work in VM | Physical GIC/timer/PSCI, SCM, shared-resource and driver progress |
| initcalls → PID1 / UDC | Static initramfs and production gadget setup qualified in VM/dummy UDC | Actual PID1, supplier/probe state, UDC registration and PHY/link behavior |
| UDC bind → USB enumeration | NCM binding occurs before IP configuration in the real PID1 | Fixed-port attachment/reset/descriptor events and stable enumeration |
| Enumeration → authenticated NCM | Existing one-request protocol and host consumer | Same-boot authenticated PID1, kernel/DTB identity, memory/timer checks and block-device absence |
| Candidate → Android | ML001 used physical Download and exact original-A return | Automatic failed-component recovery remains unproved |

The kernel Image is embedded uncompressed. Do not treat the selected loader's
configuration name as evidence that this path decompresses an Image at runtime.
ARM64 Image/header placement, register, EL, cache, DTB and initrd requirements
remain the relevant architecture contract; emulation does not measure physical
coherency or firmware traps. [Linux arm64 boot protocol](https://docs.kernel.org/arch/arm64/booting.html).

## Claims checked against the actual retained consumers

| Proposed concern | Current evidence and disposition |
| --- | --- |
| Odd-sized initramfs causes an unaligned optimized copy | The actual linked `__optimized_memcpy` used by `arch_load_kernel` checks source/destination alignment, uses aligned word accesses only on that branch, and finishes with byte loads/stores. It is a separate C helper, not an alias of the assembly memcpy. No such fault was established. |
| Missing MAX77705/Type-C support necessarily prevents VBUS detection | This kernel's `dwc3_qcom_probe` already invokes the VBUS override in fixed peripheral mode. Physical PHY/cable behavior is still unobserved; adding charger/Type-C machinery is not justified by this argument alone. |
| Candidate cmd-db or SMEM is at the wrong address | Decoded retained Android FDT and compiled candidate DTB have identical base/size for both resources. Their node layout/bindings differ, so path or byte equality is the wrong comparison. This does not prove the firmware interfaces work. |
| Missing r0q DWC3 patch explains initial USB absence | The inspected port patch concerns host-mode system-suspend loss and xHCI resume. This canary is peripheral-only and does not select that workload. No applicable missing first-boot fix was identified in the scoped patch inventory. |
| r0q's reported qcrypto/display-clock failures are active in this image | The resolved config already has QCE, Qualcomm RNG and QSEECOM disabled, the crypto DT node is disabled, and SM8450 DISPCC is a module. This RAM initramfs has no modules or module-loading path. Those particular port warnings do not identify an active cause here; SCM, SMMU and PSCI idle remain separate reachable subjects. |
| No loader `dc civac` means ML001 has a proved cache bug | Retained ABL analysis records range clean/invalidate, whole-cache cleaning and explicit M/C/I clearing. Actual late firmware behavior and effective stage-2 attributes remain unmeasured. Adding a cache operation without establishing its premises is not a demonstrated repair. |
| I-cache/collision guards should be removed because they may reject | Those guards prevent unsupported execution and live-stub overwrite. The ABL normal path supports the intended cache-off entry; actual source placement remains unknown. A newly supported placement/state needs a precise reviewed change, not removal of a check to obtain progress. |
| Android's earlier kernel/initrd addresses establish ML001 placement | They are comparison evidence only. The candidate has different size and the ABL path includes EFI inputs and randomized displacement. A fallback constant is not the successful path's measured placement. |
| Matching splash reservation proves usable framebuffer output | The selected retained g0q panel DT declares command mode. Neither that fact nor matching splash bounds proves actual bootloader scanout/autorefresh, geometry, ownership, mapping or visible updates. Command mode also does not prove pixel updates are impossible. |
| Different SCM compatible strings prove an ABI mismatch | The actual mainline driver has firmware waitqueue count/IRQ queries and an optional DT IRQ fallback. Vendor properties cannot be copied mechanically. Reachable SCM calls and actual firmware behavior need separate assessment. |
| `nohlt`, deep-idle disabling or lower kernel placement are mandatory fixes | None is established by ML001. Busy idle has power/thermal consequences; lower placement changes the layout contract. Use only a specific, evidence-led experiment if needed. `maxcpus=1` does not select a particular little core. |

The retained source packet and additional consumers were checked without
changing them. The private fact-check receipt records matching shared-memory
ranges, the linked copy's alignment/tail path, the VBUS override and the existing
ABL cache evidence. It is an advisory fact check, not a new runtime PASS_GO.

## Observation choices

| Channel | What it can usefully distinguish | Conditions and limits |
| --- | --- | --- |
| Bounded fixed-port host events, started before transfer | Brief attach/detach, reset, descriptor errors, enumeration and interface creation that sampled sysfs may miss | Limit to the target port, time and metadata; retain raw ordering and capture errors. It cannot observe code before USB activity. Host privilege/privacy requirements still apply; no bus payload capture is implied. |
| Inherited display: loader marker, then a suitable kernel console | A changed, stage-specific pattern can provide positive progress independently of USB | Establish buffer address/bounds, format/stride, ownership, effective mapping and actual refresh behavior. Keep panel initialization out if the inherited path suffices. Negative output is ambiguous. Pre-guard writes change the existing zero-store rejection contract. |
| Existing NCM plus bounded stage/error reporting | PID1, UDC binding, IP configuration and final authenticated completion | Preserve the current authenticated success path. Descriptor presence is less evidence than PID1 authentication. Record stage/errno before parking, but an in-RAM record alone is not an external observation. |
| ACM or another small USB diagnostic profile | Reduces IP/socket dependencies after controller/PHY work | Shares the early USB dependencies; it cannot diagnose pre-USB failure. A functionless descriptor-only configuration must first be shown to bind/enumerate. A new profile also needs its matching host consumer and qualification. |
| Reset-return witness | Potentially a bounded control-flow observation after independent qualification | No reviewed mainline PSCI reset route exists here. Timing alone is not a unique stage marker. Conduit, state legality, identity, calibration, other reset sources, finite consumption and actual return/recovery would need to be defined. Do not default to a reboot loop or change rejection into reset. |
| Retained RAM / ramoops | Earlier logs if a complete writer → reset/Download → reader chain works | Requires a justified safe region, exact ownership/layout and demonstrated retention across the actual recovery path, with identity/integrity and a qualified reader. Neither an arbitrary reserved region nor another target's result suffices. Not necessarily limited to warm reset or an existing Android ramoops node. |
| UART / Gunyah console | Potential early output only if a usable transport exists | No qualified receive route is present here; the retained UART is disabled. UART/EUD writes and unreviewed hypervisor/PMIC manipulation are outside the selected scope. |

Linux's ramoops documentation likewise requires persistent RAM; enabling the
option alone does not establish retention through this phone's recovery chain.
[Ramoops documentation](https://docs.kernel.org/admin-guide/ramoops.html).

## Recommended bounded H0 follow-up

Produce one entry/observation decision record using the existing loader and
owner, rather than building another framework. It should contain:

1. ABL placement/state versus each existing entry rejection predicate, classified
   **excluded by retained evidence / possible / unknown**. Recover actual EFI
   allocation/displacement constraints if the retained binary permits it; record
   the limit if it does not. Do not demand physical certainty from static evidence.
2. A narrow observation specification: fixed-port event capture and an assessment
   of inherited display viability. Name the earliest stage each can show, the
   positive/negative result meanings, and the fallback when early display cannot
   be qualified. A negative next run could still remain pre-USB `NO_PROOF`.
3. A short dependency map from the actual compiled DT to enabled driver consumers:
   clocks/reset/RPMh/command database/regulators/interconnect/SMMU/PHY/DWC3.
   Inspect reachable suppliers and initialization, not every built-in driver.
   `clk_ignore_unused` and `pd_ignore_unused` are not universal power guarantees;
   they do not cover every regulator, interconnect, driver or inherited DMA effect.
4. A single proposed successor change only when the evidence or chosen observer
   justifies it, with its exact new effects, bounded qualification and result
   interpretation. Keep current firmware, boot-only carrier, RAM-only storage
   exclusion and the original-A recovery design.

Completion is a usable next-experiment design or a clearly identified missing
input/channel, with no further benefit from the bounded retained-source pass.
Do not turn every hypothesis into a new mandatory gate. The present discussion
does not build or arm ML002, change a consumed image, or require another physical
attempt merely to complete the report.

Reuse the successful unchanged layout/copy, actual-EL, protocol, VM and gadget
evidence with their original provenance. New event parsing should exercise real
producer/consumer and transient/error fixtures; display writes would need exact
bounds and consumer validation; changed entry machinery needs its affected
instruction/EL tests and independent review. Existing review rules determine
the required review, not model agreement. No full kernel rebuild is needed for
this report or a retained-source audit.

Replacing uniLoader with direct ABL boot, a new EFI loader, kexec or a recovery
carrier would add variables now. A vendor kernel dropped into the shim is not
automatically a valid control: its DT, bootconfig, module and storage expectations
differ. The existing carrier remains the preferred starting point, without
claiming it has physically entered on g0q.

The native_data M=40 issue remains separate and unresolved; no storage recovery,
mount or installed-root execution is added to obtain boot diagnostics. Future
device effects retain current exact-target health, reviewed capability, fresh
candidate binding, finite attended authority and usable original-A recovery.

## Discussion provenance

The operator requested both Claude and Gemini Argon at high or above. Calls used
Claude Opus 5.5 with `--effort high` and Gemini 4 Argon High with explicit high
effort. Each received retained-source evidence; their first completed answers
were then exchanged along with Codex's verified counterevidence for a second
round. Claude's first larger request reached its 600-second limit without a
completed answer; it was preserved and a smaller evidence packet completed at
the same model/effort. No lower-model fallback was used.

These are advisory conversations, not independent capability reviews. Claude
ran with tools disabled. Argon ran in plan/sandbox mode with a no-tools prompt
and a wrapper stopping unexpected tool calls; its CLI still advertised tools.
No tool use occurred in the completed discussions. Private prompts, complete
responses, stream records, source pins, fact checks and usage accounting are in
`workspace/private/outputs/s22plus-mainline-boot-observation-discussion-20261028-1/`.

The second-round answers reject the speculative multi-change requirement and
the reset-loop default. Claude prioritized the ABL placement/entry predicate
comparison; Argon prioritized active-driver and placement checks. Each saw the
other's first answer, so their last descriptions of disagreement partly refer
to proposals that the other had already withdrawn concurrently. Codex's final
resolved-config check further rejected Argon's suggested active qcrypto/DISPCC
cause. The useful shared outcome is a bounded entry/observation audit, not a
model-consensus root cause or an instruction to remove the existing guards.

Before/after quota snapshots and per-call usage, including the interrupted
attempt and partial counters, were appended to the private external-model ledger.
Account-wide quota changes are not per-call token counts; CLI list-price values
are not actual subscription charges. Incomplete usage is labeled incomplete.
