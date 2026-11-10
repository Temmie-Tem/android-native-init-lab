# ML044: bounded initial UIC completion acknowledgement

## Outcome and scope

The operator requested Mythos analysis/discussion of ML043's post-HCE-stop
IRQ_STATUS `0x400`, followed by one next attended physical experiment. Two
Mythos 5.2 discussions completed. The implemented V9 candidate permits one
initial acknowledgement of this exact completion indication after the complete
stop/guard sequence. Later command admission still requires IS zero.
Implementation, actual artifact validation and independent review are H0;
physical dispatch additionally needs the exact returned approval, current
attendance, fresh target/health binding and usable physical Download.

ML043 remains consumed and closed healthy. Its original raw result is decoded
with the changed checker and every field agrees with its stored result; V9
interpretation of those V8 bytes is rejected. A90, S20+, the unrelated candidate
manifest and attachment directory are outside this change.

## What the evidence establishes

ML043 observed HCE/HCS/IS `1`/`0x10f`/`0x400` before the stop. One HCE-zero
write observed zero in one poll within the original limits. The post-stop
masked HCS `0x8`, two doorbells, two RUN registers and IE passed. The subsequent
full IS read was `0x400`; AHIT and both post-stop pin predicates were unobserved.
There was no status clear, fixed power request, reset pulse, PHY preparation,
local command or link command. Automatic Download and one original-A transfer
completed, with all seven final health reads after one preserved failed read.

The selected Linux and FYG8 Samsung headers name bit 10 UIC_COMMAND_COMPL.
Both drivers' initial setup reads and acknowledges pending status before
registering their interrupt handler. EDK2 also handles completion before a new
UIC command. Those software precedents support an explicit initial cleanup;
they do not prove why this target sampled the bit or whether the same event
persisted across the stop. The other-controller AMD register reference labels
UCCS W1C, but its HCE-clear retention notes concern card-event bits, not UCCS.
It is not an SM8450 guarantee of W1C behavior while HCE is zero.

Primary source versions and complete supplied excerpts are retained by hash in
the private evidence directory. Relevant public precedents are the pinned
[EDK2 UIC command implementation](https://github.com/tianocore/edk2/blob/6bee033c69e2c4050cb65c378d282b8f23ca0a36/MdeModulePkg/Bus/Ufs/UfsPassThruDxe/UfsPassThruHci.c#L1650)
and the [AMD UFS interrupt-status register reference](https://docs.amd.com/r/en-US/am052-versal-aie-prime-pcm-gen2-register-reference/IS-UFS_XHCI-Register?contentId=PmalJW9O5YbkLu4Ep8p9pA).
Neither is treated as device authority or target-specific causal proof.

The original IS-zero predicate was a conservative refusal, not proof of a
hardware fault. Keeping that condition before enabled commands is necessary:
simply ignoring an old completion could accept it as the new command's result.
The chosen change acknowledges only the exact initial completion under the
closed V9 conditions, before extending reach into the existing hardware path.

## Implementation and discussion decisions

The new compile mode requires the complete V8 mode chain. Initial IS `0x400`
is PENDING only after a timely HCE stop whose pre-stop IS was also exactly
`0x400`. AHIT and both pin predicates must then pass. The original zero path
adds no access; cold-entry `0x400`, pre-stop-zero/post-stop-`0x400` and all other
nonzero words retain refusal. All eleven guards precede the new effect.

Immediately before the effect, the code checks time, reads full HCE zero,
checks time, reads full IS `0x400`, then checks time again. A board-lifetime
latch and ISSUED flag precede one constant 32-bit `writel(0x400, IS)`. There is
no RMW, fault-bit acknowledgement, wait, poll or retry. If time remains, one
full IS readback is captured; only timely zero permits the existing rail
opening and later flow. An expired-before-read or late/nonzero readback stops
without another write. The nearby reads are not an atomic hardware snapshot.

The first Mythos discussion proposed the initial full-guard acknowledgement.
The followup tested a fresh HCE check, exact state-table encoding, interrupted
and late readback behavior, and legacy preservation. The final design records
commit-to-write separately from readback/zero, and explicitly permits late zero
only as refusal evidence. Neither zero nor nonzero establishes write efficacy,
causality or event identity. Prefix 15 is not success by itself. A later strict
IS refusal retains a completed initial acknowledgement, with no new clear.

The unsigned V9 tag is `0x90000000U`. Four high bits of the existing stage-two
word encode PENDING/ISSUED/READBACK/ZERO, with only 0/1/3/7/15 legal. HCS remains
in bits 22–27. ACK_DEADLINE/DRIFT/READBACK use new operations 26/27/28 and the
existing refusal index/raw fields. The host rejects inconsistent prefixes,
site, deadline, provenance and phase; guest normal-success validation requires
the corresponding completed history. The existing automatic-recovery guest
can deliver complete raw failure without granting functional proof.

The shared V2 policy and common/target routing explicitly incorporate this
new status write. The same kernel, DT, configuration, late overlay, fixed
power/reset/PHY/UIC path, 120/300/540/15 research bounds, 555/570/660 automatic
return bounds, original-A owner and attended physical fallback remain.
Conditional unattended F1 remains inactive. No old approval, capability,
artifact or journal is repinned.

## Validation and review

Actual extracted C functions run on the host and ARM64/QEMU with traced MMIO.
Tests cover exact store cardinality/order after all guards, the unchanged zero
path, cold/pre-zero/fault refusals, AHIT/pin rejection, near-effect HCE/IS drift,
all five new budget boundaries, absent/nonzero/late-zero readback, and a second
helper invocation. Stage-six NULL-diagnostic and enabled-command predicates
remain strict; initial acknowledgement cannot run there. The prefix/site corpus
and normal-success guest checks reject impossible histories and old-mode
high-bit reinterpretation. Real socket tests cover V9 negative results,
authenticated return, malformed/partial packets and expired controls. Existing
automatic-arrival, one-A and health-only continuation tests cover V9 selection.

The actual ARM64 module, observer, initramfs, loader and AP/boot envelopes were
built and qualified against the retained kernel/DT/configuration. Module
command records select V9, and its disassembly retains the constant status
store. Complete producer reproduction and byte joins use fresh key-derived
identity, distinct from consumed ML043. The actual maximum-width producer,
bounded reader and ARM64 guest accept 30 fields in 161 bytes (limit 256).

One initial build attempt supplied the already-pruned compilation header; its
identity check refused before compilation. The retry used the retained complete
five-table header, preserving table parity. Two test-invocation mistakes
(missing import path and wrong class name) were corrected; their logs remain.
These were H0 failures and caused no device transition or safety-check change.

The aggregate suite passed 121 tests with no skips, including six actual
artifact cases. Touched Python passed py_compile; scoped privacy, local links,
details digest and git diff checks passed. Independent final review returned
PASS_GO with no findings on packet `270e1b397f2515d286c159c010346316eb113881979ee89a12b817fe1960fb83`
and capability `b67e6f1530054526990a487a6efc03780ac4ebb758ce4d7b769b2f63f27319b2`.
The review independently passed 62 tests, complete observer reproduction and
artifact joins, exact retained V8 parity and all 542 prior raw captures. Its
immutable receipt is `d638c292b26ba75f064cdbc109fccd9f251b11193a0e9d05f1095a5429864fca`.

The reviewed capability was adopted for one fresh qualified ML044 task, and
the v45 backend binding was published with no unresolved owner. The existing
worker remained connected and unchanged. This enables reviewed preparation,
not device execution; the generated exact approval and current attendance
were subsequently returned and the physical run is now consumed and closed
healthy; see the [ML044 run report](S22PLUS_MAINLINE_ML044_RUN_2026-11-11.md).
The initial fixed foreground D0 passed all seven raw health
reads, with zero controls/transfers and no grant or operation at preparation.
The separate unchanged paged finalizer is eligible only
after this run has a durable healthy terminal and no remaining owner.

## Private evidence and external-model accounting

Evidence is under
`workspace/private/outputs/s22plus-ml044-uic-status-h0-20261111-1/`.
It includes both discussion prompts/responses and source pins, exact supplied
source snapshots, CLI usage captures, provider accounting, module/artifact
checks, test logs, retained V8 parity and the immutable review/task.

Both bounded inference calls used actual `claude-mythos-5-2`, with tools,
MCP and browser access disabled. The first used high effort; the focused
followup used low effort after quota reached 96%. Total provider input was
33,483 tokens (4 uncached plus 33,479 cache creation; zero cache reads), and
output was 17,868 tokens including thinking. CLI-reported API-equivalent cost
was $1.250416; subscription billing is unavailable and is not inferred from
that value. Live session quota was 79% before, 96% after round one and 99%
after round two; weekly was 19% to 20%, Fable 37% to 40%. No fallback, credits
enablement or account-setting change occurred. Before/after token and quota
records were appended privately; no credential is stored in these artifacts.
