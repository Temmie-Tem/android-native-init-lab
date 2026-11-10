# ML046: ordered CFG1 selection without an unsupported readback assertion

## Scope and conclusion

The operator requested Argon analysis/discussion of why ML045's CFG1 bit 0
remained clear and whether the immediate readback condition was appropriate,
then one next attended physical experiment. Two bounded Argon High discussions
completed. The selected V11 change retains the existing ordered bit-0 write
and both diagnostic reads, makes the post-read data rather than a hard gate,
and always checks the original budget before the original HCE-one statement.
All other predicates and effect limits remain.

The source evidence supports removing this extra software assertion. It does
not identify the target's physical bit semantics. This is a reviewed change
to functional admission, not key-only reuse, a claim of zero device effects,
or permission to reinterpret ML045. The bounded unit ends after one reviewed
fresh ML046, its separately approved attended run and original-A healthy
closure/report; link success and silicon-cause identification remain separate.
A90, S20+ and unrelated dirty work are outside the unit.

## Evidence and competing explanations

ML045's authenticated V10 record captured pre/post `0x1c00052c`, took the
bit-clear EIO branch, skipped the clock check and never reached HCE one.
All initial guards and timely IS acknowledgement passed, eleven power records
settled, and PHY readiness was set. The existing earlier PHY calibration
checked bit 1 assert/deassert in that same CFG1 register. Those earlier checks
narrow wholesale aperture/clock/cache explanations at calibration time; they
do not prove stage-six electrical state, bit-0 writability or absence of
selective protection/shadowing. Read-only strapping, split/later latching,
lane-order effects and posting remain hypotheses, not identified causes.

Both the selected Linux and FYG8 Samsung `ufs_qcom_select_unipro_mode()`
functions write QUNIPRO_SEL at offset 0xdc without asserting its immediate
readback value. The Linux code resets/calibrates the PHY, selects the mode,
then enables lane clocks before HCE. Samsung's selected PHY/mode path also
selects before lane clocks. Our bounded module currently selects after its
lane preparation. That ordering difference is real; its causal role is unknown.
The earlier conditional suggestion that selection might precede host reset
is not a description of the selected Linux source.

Upstream commit `823150ecf04f958213cf3bf162187cd1a91c885c` is especially relevant:
its older title mentions readback, but the final diff removes `mb()` and adds
no read. Its rationale requires endpoint ordering, without forcing completion
at this point. See the [maintainer stable backport and rationale](https://cos.googlesource.com/third_party/kernel/+/8a4a516a7fdd58257a7aac04df6a4b960744b395)
and [final patch submission](https://lkml.iu.edu/hypermail/linux/kernel/2403.3/12957.html).
An earlier RFC proposing a dummy read is not the adopted behavior. This is
software-contract evidence; it is not an SM8450 register manual or proof that
bit 0 legitimately reads zero in every state. The general [Linux MMIO rules](https://docs.kernel.org/driver-api/device-io.html)
likewise distinguish ordering/completion from the value semantics of a register.
Primary bytes and selected source excerpts are retained with hashes privately.

The bit-0 assertion first entered this module in commit `e581b888a6`. Its
existing tests validated that coded rule; they did not establish a target
hardware requirement for the rule. The bit-1 reset checks, CGC flushes and
later bit-31 predicate are different operations and are not removed by analogy.

## Discussion and chosen experiment

Argon recommended changing only the immediate bit-0 gate. Moving the mode
write before lane clocks while retaining the unsupported assertion would
combine ordering/phase changes with a predicate that could refuse again for
other reasons. Arbitrary delays, additional polls/barriers or post-HCE reads
lack supporting evidence. ML046 therefore retains the existing position and
accesses; it does not combine that correction with a second ordering experiment.

The followup challenged and corrected several overstatements: earlier bit-1
success cannot rule out present electrical failure; polling limits do not
guarantee a responsive MMIO bus or reboot; and a later HCE/UIC refusal cannot
identify the lane-order cause. Local-five EIO can arise inside its command or
at the later bit-31 check. Argon's second response named an incorrect fifth
command attribute; the actual source uses UNI_40NS `0x9007`, and the code/tests
follow that source. No new downstream telemetry or whole-word `0x1c00052c`
gate was introduced. No further external-model call was needed.

The existing full quiescence predicates observe HCE, doorbells, run-stop bits,
IE/IS and AHIT before enable, with fresh PCS/HCE/HCS checks and exact clock
rates. They do not prove empty firmware descriptor pointers or prevent every
hardware hang. The module allocates no descriptors, starts no transfer/task
list and binds no generic SCSI/media driver. Existing HCE/ready polling and
the first local TX-state GET constrain progression before timer changes and
the one link command. Ordinary automatic return is a finite attempt; attended
physical Download remains mandatory fallback.

## Implementation and validation

`G0Q_CFG1_ORDERED_SELECTION` requires the complete V10 diagnostic mode chain.
The same pre-read, write of pre OR bit 0 and post-read execute at the same
position. V11 then always checks the original absolute deadline. Expiry
records outcome 2 and returns EIO for either bit value without HCE/UIC issue.
Otherwise it records outcome 1 for bit clear or 3 for bit set and continues.
Only the formerly early-returning bit-clear path gains one clock evaluation.
There is no added MMIO, write, sleep, barrier, retry or ordering relocation.
The later bit-31 operation remains a read-modify-write whose bit 0 comes from
that later read; the first sample/write cannot prove persistent selection.
No new mode-persistence claim is made. V10's original short circuit and
historical encoding remain distinct.

The new unsigned tag is `0xb0000000U`, with the existing 33 decimal fields and
256-byte envelope. Host and C-guest validators distinguish the new outcome
meanings and reject old-tag substitution or inconsistent prerequisites,
bit/errno/command histories. Outcomes 1/3 indicate a timely budget, not HCE or
link success. With no local command they admit only the original timeout or
pre-command-busy paths. Outcome 2 requires EIO and zero command/result words.
A pre-effect certificate requires all added fields zero. Existing complete
link/power validation is unchanged. V10 raw evidence is rederived exactly and
rejected as V11 rather than repinned.

Actual C functions run on host and ARM64/QEMU for bit-clear/set crossed with
budget pass/expiry. Traces verify identical CFG1 accesses, unconditional V11
clock-before-HCE, no HCE/UIC after expiry, and unchanged V10 bit-clear behavior.
The real command implementation exercises all six local commands and one link
under either bit value, and verifies early guards, first TX-state mismatch,
pre-command IS refusal, timer disagreement, final local-command errors,
bit-31 refusal and one-shot behavior. The producer/reader/guest maximum-width
record remains 185 bytes. Strict typed host/guest and real-socket paths cover
success, both CFG1 values, both budget-expiry values, earlier acknowledgement
failure, load/read failure, malformed/partial packets and recovery limits.

The exact ARM64 module and fresh observer/initramfs/loader/AP are built against
the retained kernel/DT/configuration/overlay. Actual byte joins and complete
producer reproduction, current-source focused tests and independent review
must finish before new task preparation and physical authority. The common,
target, RAM and shared policy route V11 explicitly; the new module is fixed
by hash. Research 120/300/540/15 and recovery 555/570/N+660 limits, one N/A,
health, no-replay and conditional-unattended-inactive state remain unchanged.

The aggregate suite passed 168 tests without skips, including six actual
artifact cases. Thirteen touched Python files passed py_compile; scoped
privacy/local links, common-details digest, immutable prior evidence and diff
checks passed. Independent final review returned PASS_GO with no findings on packet
`5c91d10e5b479e4369231c8398485be801991f1156e0a6b7c605ab967cef6a3f`
and capability `40a66e0d64ec4bc34035eada5a8585e7722dc0745d48d56a576138bbe4ff2a44`.
Its immutable receipt is
`f51e294d11f96f357345dbd8ddc12aa549a638cbc3fb25b4d0bbf879ed532d6b`.
It independently passed 75 tests and 1,482 pin checks, complete artifact joins,
actual disassembly, prior raw parity and all 532 prior task captures/pages.
The reviewed v47 backend is selected with the stable worker connected and
unchanged. Fresh exact ML046 qualification and task preparation completed;
fixed foreground current-health D0 passed all seven raw health reads with
zero controls/transfers. No grant or operation is opened by those preparations;
the exact returned approval and current attendance/physical Download remain
required before dispatch.

## Evidence and usage accounting

Private evidence is under
`workspace/private/outputs/s22plus-ml046-cfg1-selection-h0-20261111-1/`.
It contains both discussion inputs/results and immutable supplied source
snapshots, primary commit/diff, dispositions, usage records, actual component/
artifact tests, old-result parity and source-bound review inputs. An initial
GitHub fetch returned HTTP 429; the primary maintainer stable commit/diff was
retained from Google's source mirror instead. No account or quota setting changed.

Both actual calls selected `gemini-4-argon-high`, strict permissions and no
tool use. Provider totals were 49,305 input tokens, 15,036 output tokens
(including 9,417 thinking tokens), and zero cache-read tokens. Weekly remaining
quota was 88.65% before, 88.03% after round one and 87.52% after round two.
These account snapshots are separate from tokens; cost and subscription
billing were not reported. Before/completed/after usage rows were appended
privately. No fallback model or extra credits were used.

Past-failure applicability: ABI/SEMANTIC compare the actual selected operation
and upstream final diff, without promoting a modeled readback into a hardware
requirement. WIRE/ROUTE/ARTIFACT validate actual producer/consumer/ARM output,
complete byte joins and exact mode selection. IO/PERSIST/AUDIT retain raw and
old source provenance, with no replay after reporting failure. RETURN keeps
the actual owner, finite automatic attempt and attended physical fallback.
The unchanged cue repair remains qualified and receives an actual prepared
help-capture check. Display work is inapplicable; notification is not physical
completion or authority. No extra gate or speculative diagnostic framework
is added.
