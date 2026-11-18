# S22+ reusable late-UFS capability V2

Status: **REVIEW_GATED_CAPABILITY**

On 2026-11-10 the operator selected application of the completed H0 changes
and one next attended physical experiment on SM-S906N / g0q / S906NKSS7FYG8.
The common boundary-3 delegation and the binding S22+ target adopt this shared
scope. It admits separately qualified, unconsumed key-only candidates through
one reviewed capability, without a new policy copy or capability review for
each key. Each physical operation still requires its own exact returned
one-operation 1800-second approval, current attendance and usable physical
Download recovery. This policy, H0 qualification and `PASS_GO` alone grant
no device effect. All source, artifact and runtime bindings must pass.

## Fixed reviewed capability and variable candidate data

One immutable capability record binds this policy, the machine-defined source
closure, the exact kernel, late module, DTB, configuration, four signed Debian
packages, network template, loader contract, observer compiler dependencies
and reviewed raw evidence. Its independent review binds that exact capability
record and the `S22PLUS_LATE_UFS_KEY_ONLY_V2` scope. An arbitrary review path or
candidate assertion cannot select a different scope or report version.

Within this narrow capability, new candidate data may change only a fresh
32-byte authentication key, its deterministic recipe identity and corresponding
MAC/serial fields, and artifacts derived by the unchanged producer from those
values. Output paths and an H0 descriptive name are not execution semantics.
The guest remains the four-package RAM SysVinit root, with fixed initial PID 1,
port, network addressing, authenticated protocol, module and late timing.
There is no marker, SSH service, storage/media operation or general
userspace extension in this schema. Kernel/module/configuration/DTB, package,
network, control, privilege, recovery, health, authority or evidence-acceptance
changes exceed key-only reuse and invalidate the affected capability binding.

The adopted fixed hardware artifacts are:

| Artifact | SHA-256 |
| --- | --- |
| Mainline Image with the reviewed six unused display BCM producers removed | `c4f8d9b0fad688d1a9682dc9c3aac2fd4ab2abfde9d14da858b2b89190ac7e72` |
| Retained report-v4 diagnostic and pre-effect-return module | `8e969ae4e9ce8cbb826395d2faa0e2edadea85c723e8c928d86eb757c4c93bfc` |
| Report-v5 same-read HCE and bounded HCI snapshot module | `f05ceefe7197dd7e914051bb7351879e457a3a19790688e7044cbc5055d9c8a5` |
| Report-v6 bounded HCE handoff module | `fd956216b5fa28eb9554947dbbeee2638b3f374916c893896818da5fdbf3bb9f` |
| Report-v7 dedicated reset configuration module | `24edd7cf011634fccc55e0cc90280d68349bab9234c284145fd44ecbc91c3f30` |
| Report-v8 disabled-HCS readiness module | `60cf605af0fda73615103480934e60b2e34f3a5f35494cf960b48401ee98a97b` |
| Report-v9 initial completion acknowledgement module | `4ec2d6082ab62c47b05fbe73ce458d374b229bdbf55e2b471c7650b182890c06` |
| Report-v10 CFG1 branch diagnostics module | `23c72b3c6cbe342fa41841f0cee0cf6bb12b1b5375b64f0e49cdf00be9396618` |
| Report-v11 ordered CFG1 selection module | `88beadd1a31b05fc8adc998eb99757849c6c83287fb9b4473d8590ab2b888fa3` |
| Report-v12 terminal link IRQ diagnostic module | `9176104a4c51ec21c6d845bd50f48ff2900447f654fbaa45e3718cde16ed89a2` |
| Report-v13 upstream link tolerance module (H0, review pending) | `5628f2990357f1ade9f4063627e3cf8e4f0351fe953d8f1f350dc0caf5175459` |
| Reduced no-display DTB | `f918d3094e31428fa3f44fcc919934dbbcd819e48020c2bd129d952fb21346a0` |
| Kernel configuration | `342fc5716c2cfdddc255dd1862c66d0feff848aa9381a70a3f108eb6d6e7fa72` |

The capability's exact fixed inputs bind these bytes and their retained build
provenance. An independently reviewed adoption receipt binds the complete
reachable source closure, including the common/target policy and original-A
owner; the earlier H0-only review is supporting evidence, not that adoption
receipt. The stage-two site and evaluated/failed masks preserve the original
short-circuit predicate evaluation, error semantics and guards. Unevaluated
conditions remain unobserved. V4 adds no MMIO read; the separately reviewed
V5 module adds only the five fixed reads below. V6 separately adds the bounded
handoff described below; V7 separately specializes its four reset-pin predicates
as specified below. V8 separately changes only the disabled-state UCRDY
predicates and same-read evidence below. V9 adds only the initial completion
acknowledgement below. V10 retains V9 effects and adds only the existing-read
CFG1 branch diagnostics below. V11 separately replaces only the immediate
bit-0 assertion with ordered selection and an unconditional budget check as
defined below. V12 adds the terminal link IRQ diagnostic below. V4/V5 do not inherit these changes. Each immutable capability binds
exactly one report mode and matching module/observer; mode is not candidate data.

### Version table

This table is the single list of report versions for this scope. The common
details, root contract, target contract and RAM policy refer to it instead of
enumerating versions. A version after v12 is adopted only under the common
[version envelope](DEVICE_ACTION_CONTRACT_DETAILS.md#permanent-device-safety-boundaries)
by a row here, its own section below, fixed artifacts and one coherent
independent review. The machine declaration of each version's compile mode
is `workspace/public/src/mainline/s22plus_ufs_link_h0/report_modes.py`.

| Version | Parent | Tag | Fields | State | Section |
| --- | --- | --- | ---: | --- | --- |
| v4 | ML035 module | `0x40000000` | 23 | adopted; consumed runs only | normal-return extension |
| v5 | v4 | `0x50000000` | 30 | adopted; consumed runs only | Report-v5 |
| v6 | v4 | `0x60000000` | 30 | adopted; consumed runs only | Report-v6 |
| v7 | v6 | `0x70000000` | 30 | adopted; consumed runs only | Report-v7 |
| v8 | v7 | `0x80000000` | 30 | adopted; consumed runs only | Report-v8 |
| v9 | v8 | `0x90000000` | 30 | adopted; consumed runs only | Report-v9 |
| v10 | v9 | `0xa0000000` | 33 | adopted; consumed runs only | Report-v10 |
| v11 | v10 | `0xb0000000` | 33 | adopted; consumed runs only | Report-v11 |
| v12 | v11 | `0xc0000000` | 33 | adopted; ML047 consumed | Report-v12 |
| v13 | v12 | `0xd0000000` | 38 | H0 implemented; independent review pending; no grant | Report-v13 |

### Report-v13 upstream link tolerance

The 2026-11-19 [upstream-tolerance audit](../reports/S22PLUS_MAINLINE_UFS_UPSTREAM_TOLERANCE_AUDIT_H0_2026-11-19.md)
found that each ML036–ML047 refusal with an upstream counterpart was a
condition upstream `ufshcd`/`ufs-qcom` accepts. ML047's UIC_ERROR during
DME_LINK_STARTUP matches the LINERESET that the selected Linux and FYG8
drivers expect: they enable only UIC completion and power-mode interrupts
during link startup, write-clear and ignore a latched UIC error, and read
UECPA after link startup. The operator selected one link attempt, UIC_ERROR
tolerance and the upstream QUNIPRO_SEL position.

V13 inherits V12. Its differences, each inside the common version envelope:

- (a) In the issued link command only, the existing IRQ_STATUS poll admits
  UIC_ERROR (`0x4`) together with UCCS and ULSS and keeps observing the
  already-issued command until completion or its unchanged 500 ms bound.
  Only (b) reads follow; the module issues no later write or command after
  the link command in any outcome. Every other bit keeps the V12 terminal
  refusal and its saved sample. Local commands are unchanged. The added
  stage-six requirement of a completed timely selection only refuses. The
  completion predicates (result zero, no HEI/DEI, device present) and the
  one-link limit are unchanged.
- (b) The module records the bitwise OR of every link-poll IRQ_STATUS sample.
  Only when that OR contains UIC_ERROR, after the poll ends by completion,
  refusal or timeout, it reads UECPA, UECDL, UECN, UECT and UECDME (`0x38`–
  `0x48` in the fixed HCI window) once each in that order, each only with
  time left in the original absolute module budget. These registers clear on
  read. Upstream reads UECPA after a successful link startup and all five in
  its error handler (`ufshcd_update_uic_error`); reading them after a failed
  or timed-out V13 link is a diagnostic extension admitted by (b), not
  upstream link-startup behaviour. No IS write, second pass or retry is added.
- (c) The existing write of pre OR bit 0, with its read immediately before
  and its read immediately after, moves from stage six to the end of stage
  four, after PHY calibration and before lane clocks: the position of
  `ufs_qcom_select_unipro_mode` in upstream `ufs_qcom_power_up_sequence`.
  Values, counts, outcome encoding and the following budget check are
  unchanged. Before the write, the selection re-evaluates, in V12's order,
  every check that preceded it at stage six: the 300 MHz core/UniPro rates,
  the full HCI quiescence check, PCS ready, HCE zero, and HCS without
  UCRDY/device-present. A refusal there issues no write and leaves the
  outcome unreached. Stage six repeats the same checks and requires a
  completed timely selection (outcome 1 or 3) before HCE one; a budget expiry
  ends at stage four, and later stage-five/six refusals carry the earlier
  CFG1 outcome. The paths on which V13 has written CFG1 where V12 would not
  have are exactly those that stop after the write and before V12's write
  position: a stage-five lane-clock failure or deadline; the stage-six
  module-deadline gate before `g0q_hci_link_once`; and a stage-six refusal
  by its repeated checks (rates, HCI quiescence, PCS ready, HCE zero, HCS)
  before HCE one. None issues any further write or command.
- (d) Tag `0xd0000000`, 38 fields: the 33 V12 fields, then the link-poll OR,
  a UEC read prefix mask (0, 1, 3, 7, 15 or 31), raw UECPA, raw UECDL, and one
  word packing UECN/UECT/UECDME code bits, layer error bits and
  reserved-bit-set flags. With every unconstrained word at ten digits the
  issued-link line is at most 254 bytes. Unread UEC words are zero. Guest and
  host reject a success without a completion sample, a union with refused
  bits outside the terminal sample, UEC data without UIC_ERROR, and non-prefix
  masks.

V12 behaviour without UIC_ERROR is reproduced exactly: the same link-phase
MMIO trace and first 33 fields in the focused fixtures, and the V12 module
rebuilt from the V13 source tree is byte-identical to ML047's `9176104a`.
A V13 link success is `UFS_LINK_COMPLETED` only with the full existing
UFS and power proof. A UIC_ERROR, UEC values or PA line-reset bit identify an
event class; they do not by themselves establish its cause.

The same-boot 300-second witness, 120/540/15-second limits, one module
permit, one link attempt, one N and one original A, the finite automatic
Download attempt, attended physical fallback and final health apply
unchanged. Fresh capability and candidate qualification, this version's
independent review and a separately returned one-operation 1800-second
attended grant precede any physical run.

### Report-v5 bounded HCI snapshot

The operator's 2026-11-10 continuation request selects H0 implementation and
one next attended experiment for the ML036 HCE rejection. V5 preserves the
full HCE word from the original stage-two read, without rereading HCE. Only
after the existing version checks and only when that word is exactly 1, 2 or 3
may it read HCS (0x30), transfer doorbell (0x58), task doorbell (0x78), interrupt
enable (0x24), then interrupt status (0x20), at most once each, in that order.
Each added read requires remaining time in the original absolute module budget;
expiry stops the snapshot at its completed prefix. These are added MMIO accesses,
not a claim of zero hardware activity. The access predicate confines diagnosis
to defined HCE states; it never permits the refused operation to continue.

The original HCE nonzero result still returns EBUSY at HCI/QUIESCENT. Its later
predicates remain unevaluated; raw captured values have a separate captured
mask and cannot become predicate PASS/FAIL or ownership/idle-DMA proof. HCE==0
continues the unchanged existing link path. Unknown HCE bits permit only the
same-read HCE record. No reset-pin, run/stop, auto-hibernate, request-list
pointer, PHY or UIC-error register read is added. The later pre-link check has
no snapshot. No added HCE write, status clear, reset reordering, guard relaxation,
new command, hardware retry or deadline extension is included.

The fixed v5 report has 30 decimal fields within the existing 256-byte envelope:
the original 23 fields with tag 0x50000000, followed by a six-bit captured prefix
mask and HCE/HCS/transfer-doorbell/task-doorbell/IE/IS raw words. Uncaptured
words are zero and decode to unavailable. The existing evaluated/failed masks
and errno retain their v4 meanings. Historical v1-v4 decoding stays explicit;
mixed report modes and impossible capture histories fail closed. Additional
captures exist only on the HCE-refusal path, where all later UFS/power-command
fields remain zero; capacity is qualified on those reachable paths.

V5 keeps the same pre-overlay normal-return certificate, requiring every new
snapshot word to be zero on that path. Stage-two refusal, including partial
snapshot or added-access failure, remains outside normal return. The attended
physical Download/original-A route is retained, without claiming ML036 already
proved recovery coverage for every new access failure. Changed producer,
schema, guest/host consumers, common/target adoption and exact artifacts need
one coherent independent review before a new capability can be selected.
The existing v4 capability, ML036 approval and consumed records are not repinned.

### Report-v12 terminal link IRQ observation

The operator selected one new attended experiment after ML046 reached all
six local commands and issued DME_LINK_STARTUP. Its retained V11 EIO and
unfilled completion fields narrow the failure to the first disallowed poll
sample. The actual ML046 word is unavailable.

V12 inherits V11 and selects the fixed module above with the complete V11
compile mode. The only hardware-path change is one scalar assignment after
the existing IRQ_STATUS read and failed mask predicate, only in the issued
link command. It records the full u32, including any coincident completion,
startup and high bits, into the existing interrupt field, then returns EIO.
The source uses the original register value. The six local commands, existing
completion handling, MMIO accesses, original polling order, command count
and timing limits apply. Additional reads, status clears and retries are
outside this scope.

The unsigned tag is `0xc0000000`. The 33 decimal fields fit the existing
256-byte envelope. A nonzero `irq & ~0x500` identifies the early refusal
only with EIO, six locals, an issued link, the admitted pre-link HCS sample,
the completed V11 prerequisites and unfilled code/post-HCS fields. The
host retains both the full sample and its unexpected bits. A recorded
completion uses 0x400 or 0x500 with the sampled code and post-HCS. An issued
link with an empty terminal sample requires timeout and zero code/post-HCS.
No link issue requires all four link words zero. A load/read error retains
its existing authenticated error record. V11 raw records keep their old
meaning. Link success requires the full existing UFS and power proof.

Fresh source and artifact review, qualification and a returned one-operation
1800-second attended grant bind each physical run. The same-boot 300-second
witness, 120/540/15-second limits, finite automatic Download attempt and
attended physical fallback followed by one original A and final health apply.
The diagnostic's success criterion on a refusal is an authenticated saved
sample. The bit combination identifies the reported event class. A silicon
cause requires separate evidence.

### Report-v11 ordered CFG1 selection

The operator's 2026-11-11 ML045 followup requests Argon analysis of the
bit-0 readback and its predicate, followed by one next attended experiment.
ML045 observed pre/post CFG1 `0x1c00052c`, took the bit-clear EIO branch and
did not evaluate the budget. Its cause is unproved. Earlier same-register
PHY-reset bit-1 readback success only narrows explanations at that earlier
calibration time; it is not present electrical state or bit-0 semantics.

Both selected Linux and FYG8 Samsung mode-selection functions write bit 0
without requiring its immediate readback to be one. The final upstream
`823150ecf04f958213cf3bf162187cd1a91c885c` diff removes the prior mb and adds
no read; despite its older title it explains that endpoint ordering is the
requirement. This is a software-contract basis for retiring the module's
extra immediate bit-0 assertion, not proof that the target bit is read-only,
strapped, latched later or protected. The reference drivers select before lane
clocks; this candidate deliberately retains its existing after-lane placement
so an ordering change is not combined with the predicate correction.

V11 inherits V10 except for this first stage-six CFG1 predicate. Retain the
same pre-read, one write of pre OR bit 0, and post-read, at the same place.
The post-read is diagnostic data only. Always evaluate the original absolute
module budget after that read and before the original HCE-one write. Expiry
records outcome 2 and returns EIO for either bit value, with no HCE/UIC issue.
A timely check records outcome 1 for bit clear or 3 for bit set, then reaches
the unchanged HCE-one statement. Thus the clock is newly evaluated once on
the formerly early-returning bit-clear path. No MMIO access, CFG1 write,
sleep, barrier, retry or ordering relocation is added. This changes functional
reach under a zero bit sample; it is not a zero-effect or key-only V10 reuse.
No new gate pins the observed whole CFG1 word.

Every other predicate and effect limit remains. The immediate pre-enable
HCI quiescence still checks full HCE zero, disabled HCS hazards, both doorbells,
both run-stop registers, IE, IS and AHIT; fresh PCS/HCE/HCS checks and exact
clock rates remain. The module allocates no request descriptors, starts no
lists and binds no generic SCSI/media path. These checks do not prove that
firmware left all descriptor pointers empty or that hardware cannot hang.
The existing 1-ms delay/50-ms HCE poll, enabled UIC readiness/error checks,
first local TX-state GET requiring HIBERN8, timer-consistency predicates,
late CFG1 bit-31 check and six-local/one-link limits remain unchanged. The
stage-four PHY-reset bit-1 checks are also unchanged. Software deadlines need
a responsive CPU/bus; ordinary restart can fail. Attendance and usable physical
Download remain required, with no new automatic-hang-recovery claim.

The new opt-in mode requires the complete V10 chain, unsigned tag
`0xb0000000U` and the same 33-field/256-byte report. Earlier modes retain their
original meanings and short circuit. V11 meanings and source constraints are:

| Outcome | Required evidence | Interpretation |
| --- | --- | --- |
| 0 | zero pre/post, HCE-started/local/link zero, negative rc and existing stage history | CFG1 not reached; budget unavailable |
| 1 | stage 6, PCS/HCE-started 1, eleven initial guards passed, no refusal site/words, post bit 0 clear | Ordered selection; budget passed; later result still required |
| 2 | same reached prerequisites, rc -5, local/link/result words zero, either post bit | Budget expired; no HCE-one issue |
| 3 | same reached prerequisites, post bit 0 set | Ordered selection; budget passed; later result still required |

For either continuing outcome 1/3, a zero local count requires no link/result
words and rc -110 or -16, reflecting only the existing pre-command paths.
With local commands, all existing downstream validation remains. A local-five
EIO may come from its command or the later bit-31 check and is not uniquely
attributed. C-guest successful-link validation admits only 1/3 with the matching
post bit; host successful-link validation retains every completion/power
predicate. Pre-effect certification requires all added fields zero. Mixed
V10/V11 tags or impossible histories refuse. Budget evaluated is true for
1/2/3 and expired only for 2. Raw V10 is never reclassified.

Passing the removed assertion and observing a later result is the bounded
functional criterion; full UFS link success is a separate claim. HCE/first-UIC
failure cannot prove lane-order causality or authorize another experiment.
The source/guard/schema change, fixed module, exact observer/host/owner and
common/target adoption require independent review and fresh qualification.
The 120/300/540/15 research limits, 555/570 guest and N-launch-plus-660 host
recovery limits, original A/health rules, exact finite attended approval and
physical fallback remain. ML045 and all consumed artifacts/approvals/journals
stay unchanged; this adoption alone opens no run.

### Report-v10 existing-read CFG1 branch diagnostics

The operator's 2026-11-11 ML044 followup selects Argon discussion, a correction
to the reconnect caller, and one next attended experiment. ML044 reached stage
six with PCS ready, HCE-started software flag set, zero local commands and EIO.
In its exact source this narrows to the first HCI_CFG1 bit-0 readback-or-budget
branch. The 1.923-second host permit-to-result interval favors readback failure
but is not the kernel clock predicate. Neither raw CFG1 nor that predicate was
recorded. HCE-started is set before the actual HCE-one write and cannot prove
that write or enabled state. V10 must not retrospectively assign ML044 a branch.

V10 inherits the exact V9 effects, predicates, ordering, budgets and recovery.
Only the first HCI_CFG1 (0xdc) operation changes its scalar evidence handling:
retain the existing pre-read, write exactly that value OR bit 0 once, retain
the existing post-read, then preserve the original short circuit. Post bit 0
clear records outcome 1 and returns EIO without evaluating the clock. Post bit
0 set evaluates the original budget exactly once; expiry records outcome 2
and returns EIO, otherwise outcome 3 precedes the unchanged HCE-one write.
There is no extra MMIO or clock access, wait, barrier, retry, write or predicate
relaxation. Added scalar stores/instructions can affect timing; timing identity
or zero hardware perturbation is not claimed. The module's static board starts
all three fields at zero; its atomic one-probe and HCE-started latches remain.
No reset of diagnostics authorizes or supports another invocation.

The distinct unsigned tag is `0xa0000000U`. The previous 30 decimal fields
retain their V9 meanings; the 33-field report appends outcome, raw pre and raw
post as u32 decimal fields in the same 256-byte authenticated envelope. Mixed
tag/field modes, invalid ranges and contradictory branch histories refuse.
The early-coverage certificate requires all three new fields to be zero.
The matching guest's successful-link check requires outcome 3 and post bit 0.
The host additionally enforces these source-derived conditions:

| Outcome | Required evidence | Interpretation |
| --- | --- | --- |
| 0 | pre/post zero, HCE-started/local/link zero, negative rc, existing stage/guard history | CFG1 not reached; samples and budget unavailable |
| 1 | stage 6, PCS and HCE-started 1, eleven guards passed, no refusal site/words, local/link/result words zero, rc -5, post bit 0 clear | Bit-readback branch taken; budget not evaluated |
| 2 | same reached predicates as 1, rc -5, post bit 0 set | Budget evaluated and expired |
| 3 | same stage/PCS/HCE-started/guard predicates, post bit 0 set; if local count zero, no link/result words and rc -110 or -16 | CFG1 check passed; later command/result validation remains required |

A zero sample is an observed word only when outcome is nonzero. Pre/post are
two observations, not proof of write efficacy, cross-reset clearing, clocks,
correct aperture selection or cause. A completed V10 diagnostic may still be
UFS NO_PROOF. Existing exact raw-result automatic return remains distinct from
functional proof and from demonstrated hang recovery. V1–V9 results keep their
original schema and source provenance. ML044 remains consumed; its artifacts,
approval, journal and result are never repinned.

### Fixed capture of the reconnect caller

ML044's ad hoc raw-capture invocation supplied unsupported keyword names and
failed before spawning the cue caller; its later corrected call was refused
by the unchanged more-than-60-seconds condition. The reviewed CLI now offers
an explicit capture directory for one fixed self-invocation of check, issue or
resolve, using the existing raw capture API and bounded output. Direct raw
acquisition is not constructed during the run. Before N, `capture-help` runs
the same self-capture path into its separate prepared directory. Issue and
resolution have distinct fresh directories; no capture or action is replayed
when a receipt exists or execution is uncertain.

Raw stdout/stderr and terminal status are sealed before success/JSON parsing.
Failure reports retain the fixed evidence location; an interrupted call may
need observation of that location and never implies that a cue was absent.
A captured actionable issue result must bind its exact operation-local cue;
a final original-window check suppresses the instruction if 60 seconds or less
remain. Suppression does not delete the cue or resolve its physical interlock.
No scheduler, new device command, new physical action, extra time or recovery
class is added. Actual operator completion/cancellation remains necessary for
an issued cue's resolution; notification delivery alone is not completion.

### Report-v9 initial UIC completion acknowledgement

The operator's 2026-11-11 request selects Mythos analysis of ML043 and one
next physical experiment. ML043 sampled IS `0x400` both before and after a
timely HCE stop; this is UIC_COMMAND_COMPL, not an error bit. The samples do
not identify its source, the same event surviving, a reset-clearing delay or
a hardware defect. Linux/Samsung initial setup explicitly acknowledges pending
status and EDK2 clears completion before a UIC command. These are software
precedents; W1C behavior while HCE is zero on this target remains to be observed.
Simply ignoring the completion before commands could accept an old event as
new completion. V9 therefore preserves strict later IS-zero conditions.

V9 inherits V8 with one narrow boundary-3 addition. Only initial stage two,
a real diagnostic record, a timely completed one-stop handoff (flags 0x1fff),
and the pre-stop exact IS `0x400` admit the existing post-stop IS sample of
exactly `0x400` as PENDING. This admission occurs at the original IS predicate;
all earlier predicates still short-circuit. The following AHIT and both pin
predicates must pass before the acknowledgement, so all eleven guards precede
its write and the existing rail-request opening. A later AHIT/pin refusal
preserves PENDING without any status effect. Initially zero IS takes the
original path without acknowledgement reads or writes. Cold-entry `0x400`,
pre-stop IS zero with post-stop `0x400`, and any other nonzero word refuse.

The acknowledgement checks the original 15-second absolute module budget,
reads full HCE exactly zero, checks time, reads full IS exactly `0x400`, checks
time, then consumes a board/module-lifetime one-shot latch and records ISSUED
before one constant 32-bit `writel(0x400, REG_INTERRUPT_STATUS)`. There is no
fallible call between that final budget check, latch/flag and store. These
nearby reads are not an atomic hardware snapshot and no new locking is added.
ISSUED means committed to the write, not proof that the bus write landed.
The latch cannot authorize another attempt after reload/reboot: the outer
one-permit, one-operation and consumed candidate rules remain mandatory.

If the budget still permits, exactly one full IS readback is captured. Zero
is recorded independently of the subsequent deadline check. Only timely zero
permits the unchanged downstream path. Known expiry before readback forbids
that read, leaving the state unknown; a late zero is evidence, never permission
to continue. Drift, nonzero readback or timeout refuses without retry. Nonzero
readback may be a new event; it does not prove an ineffective W1C. Zero does
not establish that this write caused the change. No RMW, fault-bit/all-bit
acknowledgement, extra poll/sleep, new interrupt/list configuration or new
command is added. Stage-six NULL-diagnostic quiescence and every enabled UIC
submission still require full IS zero. They cannot perform this initial clear.
The unchanged command path acknowledges only its own local completion and
retains terminal link status. A later reappearance is a later refusal, not an
initial acknowledgement failure or authority for another clear.

The distinct unsigned tag is `0x90000000U`. The 30-field, 256-byte report keeps
bits 0–27 of the stage-two word as before; bits 28–31 encode PENDING, ISSUED,
READBACK and ZERO. Only prefixes 0, 1, 3, 7, 15 are legal. Same-read HCS remains
`(word >> 22) & 0x3f`, never contaminated by this nibble. Nonzero prefixes need
the completed stop, pre-IS `0x400` and the admitted initial IS predicate. The
pre-effect certificate requires all diagnostic/history words zero. Legacy
V1–V8 records keep their meaning and reject nonzero new bits.

New failure sites are HCI operations 26 ACK_DEADLINE (-110), 27 ACK_DRIFT
(-16), and 28 ACK_READBACK (-5). They require stage two, all eleven observed
guards and zero failed guard bits. HCE stop metadata remains the original
completed-stop evidence; the existing refusal index/raw pair describes the
new phase separately. The exact reachable table is:

| Site | Prefix | Refusal index | Raw value |
| --- | --- | --- | --- |
| 26 | 1 or 3 | 0 | 0; no readback captured |
| 26 | 7 | 8 (IS) | nonzero late readback |
| 26 | 15 | 8 (IS) | zero late readback |
| 27 | 1 | 1 (HCE) | nonzero |
| 27 | 1 | 8 (IS) | anything except 0x400, including zero |
| 28 | 7 | 8 (IS) | nonzero timely readback |

Prefix 1 outside these sites is legal only at the following AHIT or pin
refusal. Prefix 3 or 7 cannot escape its listed failure. Prefix 15 outside
site 26 requires completed guards and a later stage-two resource failure or
progression beyond stage two. Prefix 15 alone never means success: rc, stage
and site remain mandatory. No failed earlier predicate is overwritten after
the effect. Guest normal-success and host proof acceptance enforce their
matching V9 provenance; the unchanged automatic-recovery guest may deliver a
complete raw failure without functional validation, and never upgrades proof.

The selected Image, DTB, configuration, overlay, power/reset/PHY/UIC flow,
120/300/540/15-second research limits, 555/570/660-second automatic attempt,
original-A and physical fallback stay fixed. Conditional unattended F1 stays
inactive. The coherent common/target/producer/consumer/owner review includes
actual ARM64 production, effect ordering and deadline/failure cases, strict
prefix/provenance rejection, real socket return, and retained V8 raw parity.
Fresh candidate qualification and the exact returned one-operation 1800-second
attended grant remain required. Review changes or concrete new hazards under
the existing common rules; no additional gate is created. ML043 stays consumed.

### Report-v8 disabled-HCS readiness

The operator's 2026-11-11 request to analyze ML042 with Mythos and proceed to
one next physical experiment selects this separately reviewed successor.
ML042 proved a timely single HCE stop, then sampled HCS `0x8` and refused
before later initialization. This is UIC_COMMAND_READY, not a host/device-error
bit. Its electrical/internal cause and persistence are unknown. Neither that
observation nor an advisory discussion grants a run or replay.

V8 inherits V7 and changes only UCRDY membership in three existing disabled-
state checks: initial stage-two cold/post-handoff quiescence, later stage-six
quiescence, and the final pre-enable HCS check. The first two masks change
from `0x39` to `0x31` (DEVICE_PRESENT and the two existing error indicators);
the last changes from `0x9` to `0x1` (DEVICE_PRESENT). No error check is added
or removed from the last site. One shared compile-time readiness mask governs
all three, including cold entry and the post-GCC-reset path. Each retains its
existing full-HCE-zero prerequisite, short-circuit order and remaining guards.
Doorbells, list RUN, IE, IS, AHIT, pin predicates, resources, pulse release and
all subsequent behavior remain unchanged. Unknown readiness origin is not
accepted as proof of inactivity, DMA ownership or complete hardware reset.

No MMIO read, poll, sleep, HCS/status clear, interrupt change, reset reorder,
retry or new slot is added. The same stage-two HCS read additionally retains
`raw & 0x39` in the existing bits 22–27 of the diagnostic word, on both passing
and failing paths. Its failure predicate is independently `raw & 0x31`.
Only an actual HCS evaluation can populate that slot; later stages cannot
rewrite it. A passing sample therefore reports UCRDY 0 or 1 without asserting
the full HCS word. Existing raw refusal fields still carry the full failing
word. The distinct tag `0x80000000U`, 30 fields and 256-byte envelope select
this interpretation. V1–V7 meaning and retained raw records stay unchanged;
V7's ready-only failure cannot be relabeled as a valid V8 failure.

Allowing UCRDY already high removes its previous clear-before-enable
corroboration. The unchanged final full HCE check, one HCE-start write, one-ms
post-write delay and 50-ms poll still require HCE exactly 1 and UCRDY set
before any local command. The existing enabled-command HCS/IE/IS predicate,
500-ms command deadline, first exact local-result check, six-local/one-link
limits and no retry remain. A passing poll proves sampled enabled/readiness
levels, not an independently observed UCRDY 0-to-1 transition or every internal
initialization event. Stage-six bare EBUSY remains unattributed; no telemetry
extension or speculative later guard relaxation is bundled.

The original 120/300/540/15-second research and 555/570/660-second recovery
bounds, one N and original A, attendance and usable physical Download remain.
A later attributed refusal is valid NO_PROOF evidence; complete link proof
retains every existing criterion. New physical reach into the existing
power/reset/PHY path does not imply automatic hang recovery. Conditional
unattended F1 remains inactive. The selected kernel, DTB, configuration and
late overlay are unchanged. Coherent common/target/producer/consumer/owner
review, actual fresh artifact qualification and the exact returned finite
approval are required before dispatch. Review changed inputs or concrete new
hazards under the existing common rules; this section adds no new gate.

### Report-v7 dedicated reset configuration

The operator's 2026-11-10 request to discuss ML040/ML041 with Mythos and proceed
to the next physical experiment selects this separately reviewed successor.
V7 inherits the complete V6 one-stop HCE transaction and automatic return/recovery
below, specializing only the four existing reset-pin configuration predicates.
ML040 observed CTL `0x0000000b` and refused before reading IO or writing HCE;
ML041 proved exact automatic Download arrival and original-A health without a
first protocol response, but did not identify the guest reset trigger. Neither
run grants V7 authority. Both remain consumed with their original evidence.

For this exact dedicated UFS_RESET group, V7 replaces the legacy CTL bit-31
output-direction test with whole-word `CTL == 0x0000000b`. IO still requires
only output-latch bit 0 set. This is an explicitly changed admission predicate,
not an assertion that the old masks were preserved. The complete CTL value
binds the ML040-observed configuration; its origin, electrical direction and
pad voltage remain unproved. A changed bit, including `0x8000000b`, refuses.
Unknown IO upper bits remain outside the predicate and are preserved by the
existing pulse read-modify-write. No whole-word `IO == 1` claim is made.

One shared definition governs the initial HCE-handoff precheck, the stage-two
post-handoff/cold check and both stage-three checks before and after the GCC
reset. Each site's existing read order, short-circuiting and budget checks stay
unchanged. Cold HCE entry also uses the exact configuration predicate; no
historical observation of that cold path is implied. No CTL write, generic TLMM
enabling, new pin read, extra pulse, status clear, hardware retry, sleep or
reset reordering is added. The existing active-low bit-0 pulse remains at its
original stage and always releases after an attempted low write, including a
failed low readback. A stage-three pin refusal stays bare `EBUSY`; the report
does not identify which side of the GCC reset refused.

V7 has the same 30 fields and 256-byte bound with distinct tag `0x70000000`.
Condition indices 10/11 decode as `RESET_CONFIG` and `RESET_LATCH_HIGH` only
for V7; earlier report modes retain their original meanings. A passed masked
latch predicate follows from the read prefix and progression, not a capture
flag alone. Existing raw refusal fields retain failing CTL/IO values. No new
telemetry field or electrical readback is added. Mixed versions refuse, and
all handoff fields must remain zero for the pre-overlay return certificate.
Legacy C enum/flag names containing OUTPUT are numeric slots, not a V7 direction
claim. The retained `S22PLUS_UFS_V6_CHILD_RESTART2_V1` recovery identifier names
the unchanged child mechanism and does not select the report schema.

The scope admits the existing pulse with CTL bit 31 clear; it does not prove
that the pulse reaches the device or that bit 31 has no electrical function.
Exact MMIO ownership is only among Linux resource users, not every possible
hardware actor. Newly reached HCE, reset, PHY and link behavior, and automatic
return after partial execution, remain physical questions. Current attendance,
usable physical Download, the original single-A owner, fixed 120/300/540/15-second
research bounds and 555/570/660-second automatic-recovery bounds remain required.
Conditional unattended F1 stays inactive. The kernel, DTB, configuration and
late overlay are unchanged. Changed producer, interpretation, common/target
adoption and actual owner branches require one coherent independent review,
fresh full artifact qualification and the exact returned finite approval.
V6 records are preserved by their original hashes, not relabeled as V7 proof.

### Report-v6 bounded HCE handoff

The operator's 2026-11-10 request to analyze ML039 with Mythos and proceed to
the next physical experiments selects this separate H0 implementation and
review scope. ML039 observed HCE `1`, HCS `0x10f`, zero doorbells/IE and IS
`0x400`; it did not prove ownership, an idle DMA engine, electrical validity
or a bootloader cause. V6 becomes selectable only after its coherent independent
common/target/producer/consumer/owner review and fresh artifact qualification.
It retains the exact returned per-operation attended approval below. This
definition and the advisory discussion alone grant no device effect.

Only the initial stage-two HCI check may perform the following transaction,
after the original USB coverage, access-power and version guards. HCE `0`
uses the existing cold-state predicate chain without a stop write. Any HCE
other than exactly `0` or `1`, including crypto-enable, is refused. For HCE `1`,
read HCS, transfer doorbell, task doorbell, IE, IS, reset-pin output mode and
reset-pin high state in that order, stopping on the first failed condition or
expired original budget. Require UIC-command-ready and no HCS host/device error,
zero whole-word doorbells and IE, IS exactly `0` or `0x400`, and the existing
output/high reset-pin conditions. These are sampled admission predicates;
they do not prove absence of every possible hardware actor. No pre-stop list
RUN, AHIT, UIC-error, list-pointer or PHY read is added. The two pin reads are
new reachable accesses on this enabled-controller path.

A final HCE read must still equal `1`; even drift to `0` refuses this transaction.
After a final original-budget check, the static board's one-shot latch precedes
exactly one whole-word `writel(0, REG_CONTROLLER_ENABLE)`. No RMW, status clear,
IRQ operation, retry or failed-stop re-enable is permitted. Poll only HCE,
with 10–20 microsecond sleeps, inside the lesser of the original 15-second
module deadline and a one-millisecond local ceiling established before the
write. A known expired ceiling permits no further poll read. Record a sampled
zero even if that read completes late, but require full-word zero and both
unexpired ceilings after the read before continuing. An unexpected nonzero
value other than `1` stops. This is deliberately stricter than the retained
upstream poll helper's final read/acceptance after local expiry; the one-ms
timeout parameter is source-grounded, not a claim that identical scheduling
or physical completion has been proved.

Only timely completion may supply its last HCE sample to the existing
short-circuit quiescent chain. HCS, doorbell, list RUN, IE, IS, AHIT and both
reset-pin predicates keep their original masks, order and refusal semantics.
The pin checks are fresh again after handoff. No read after a failed predicate
is added. Only their complete success permits the existing rate/supply,
host/device-reset, PHY, symbol-clock, HCE-start, six-local-command and single
link path. Any residual state stops without clearing it. The later stage-six
check still reads fresh HCE and cannot enter or repeat handoff. A stopped
handoff or later guard failure selects the separate automatic-return/recovery
attempt below. Its result remains NO_PROOF unless the independent functional
checks succeed. Prior HCE-unchanged refusals prove no new recovery coverage.

V6 uses tag `0x60000000` and 30 decimal fields within the unchanged 256-byte
envelope. Fields 0–22 retain the stage/result representation, with new HCI
failure operations 21–25 for admission, pre-write deadline, final-HCE drift,
stop timeout and unexpected stop state. The ordinary evaluated/failed mask
describes actual post-handoff or cold-path predicates, not a pre-HCE failure
later overwritten. Fields 23–29 separately contain transition metadata,
pre-HCE, pre-HCS, pre-IS, last captured HCE, refusal-condition index and its raw
value. Indices always use the same existing condition numbering in every
phase; flags, failure operation and predicate history jointly bind the phase.
For duplicate pre-HCS/IS evidence the values must match. Last HCE is valid
after the final pre-write read and is updated by each poll; flags distinguish
those cases. Final drift to zero is never cold-entry evidence.

Metadata bits 0–12 are the contiguous read/transition prefix: HCE, HCS,
transfer/task doorbells, IE, IS, output/high pin, final HCE, stop issued,
readback sampled, zero observed and timely completion. Bits 13–19 record
poll count saturated at 127; bits 20–31 record elapsed microseconds saturated
at 4095. Saturated values are lower bounds, and neither diagnostic drives the
live deadline. Unknown values remain unavailable. Reachable-state capacity
must cover high pre-HCS values coexisting with complete later power/link
fields, early arbitrary-value refusals and malformed histories. Host and guest
both require the explicit complete handoff/cold-entry form before successful
link return. The pre-overlay certificate separately requires all seven extra
fields zero. V1–V5 decoding and retained artifacts keep their original meaning.

The scoped admission blocks unknown/crypto-enabled state, sampled active
request/interrupt or error state, unsafe reset-pin prerequisites and effect-time
HCE drift. Review it on a new observed refusal, changed controller semantics
or a new hazard. It may be replaced only by a reviewed predicate/transaction
with equivalent target, no-replay, effect-time and recovery guarantees; a new
observation cannot silently broaden this scope. The existing original-A owner,
all research deadlines, one module permit, one N/A total and target isolation remain.

### V6/V7/V8/V9/V10/V11/V12 automatic Download attempt and original-owner recovery

The operator selected automatic return as the default on 2026-11-10, including
unclear experiment results where automatic recovery can still be attempted.
This reviewed V6 scope forks exactly one child before USB setup, after checking
the bound `nvmem-reboot-mode` driver, OF node, cell phandle, fixed bit/offset
properties and Download magic 21. Those checks read metadata, not PMIC contents.
The child alone owns one ordinary `RESTART2(download)` slot. Its parent never
issues a reboot syscall in this mode. It has no respawn, parent-death signal,
timer-renewal command, shell, blocking console/network output, alternative
reset or retry. A single local nonblocking socketpair carries challenges and
the one early commit. EOF/invalid IPC removes the descriptor and leaves the
fixed timer running; polling never spins on a persistent hangup or drains an
unbounded input queue. A spent syscall cannot be retried even if it returns.

Fresh local child replies are authenticated in separate base and late frames
binding candidate, boot, the original and late nonces, fixed recovery mode and
schedule. Both are required before the single module permit. They prove
child liveness at those challenge times, not future restart completion. Missing
arm proof blocks further UFS work but cannot block the original owner's
independent exact-Download recovery. Early commit requires the late challenge
and the existing complete-result digest, same socket/boot, authenticated
control, ACK, EOF and original final research deadline.
The child accepts the early IPC commit only before guest BOOTTIME 540 seconds;
after that, only the already armed timer remains. Once committed, its sole
recovery syscall still has the fixed 570-second latest-invocation bound.
Any complete valid authenticated V6/V7/V8/V9/V10/V11/V12 result may select return, including load/read errors or later
guard failures; successful return never upgrades the experiment result.
Malformed/partial/lost results send no new control and leave the timer armed.

The fallback triggers at guest absolute BOOTTIME **555 seconds**, giving a
15-second quiet interval after the unchanged 540-second experiment ceiling.
The child refuses a syscall at or after **570 seconds**. These are recovery
limits, not an extension of the first-response, witness, module or command
budgets. Delayed scheduling, child death, PID1 failure, kernel failure or a
blocked ordinary reboot can defeat the attempt. In particular the retained
kernel's reboot notifiers and `device_shutdown()` may wait on probe completion,
device/parent locks or runtime-PM; a hung UFS probe can therefore block it.
The selected module has no `.shutdown` callback and no generic UFS/SCSI host
binds. This adds no emergency restart, panic/RDX, hardware watchdog or separate
PMIC write. The one ordinary reboot retains its existing reboot-mode/SCM
NODUMP/PSCI path. Its finite invocation bound is not a completion guarantee.

On any experiment stop, the original host owner first classifies existing A
intents. If one exists, it only reconstructs raw completion and resumes health.
Otherwise it performs bounded read-only exact-Download observation in a separate
evidence directory, before any A step-start/transfer attempt. Its window is
fixed once from the original durable N launch intent plus **660 seconds**, on
the same host boot. It does not require completed N, candidate files/keys or
successful parsing. For an intended N, the measured USB identity must differ
from the launch's Download generation; mere continued presence of the original
Download is insufficient. Before N, only the original Android Download arrival
bound applies. The existing physical-cue interlock must be settled before host
transfer. The original-A implementation obtains a new lease, reobserves and
revalidates the exact endpoint and checks the same automatic cap at dispatch.
No ticket is transferred across leases and no second A slot exists.

Timeout or failure preserves raw evidence and the owner, then permits the
existing attended physical Download recovery with its own original semantics.
A stale automatic-wait record cannot renew that wait or force the later
physical path to use an expired automatic deadline. Once-armed recovery is
preauthorized within these finite caps and survives research-grant expiry;
it never renews the grant, research budget, candidate or control. No physical
action is requested while the automatic attempt is being observed. An actual
operator action must be recorded and cannot be attributed to automatic return.

Streamed raw evidence is saved before interpretation; reset may lose other
RAM-only diagnostics. Functional result, child arm/liveness, accepted control,
exact Download arrival, original-A completion and final health are separate
claims. An unknown result stays NO_PROOF. An observed arrival without an
authenticated trigger does not prove which trigger ran or arbitrary hang
recovery. Current attendance and usable physical fallback remain required for
each exact one-operation grant. Conditional unattended F1 remains NOT ACTIVE.
Review this scoped mechanism on changed boot/control/recovery semantics,
new failure classes or demonstrated missed recovery; no added gate becomes
permanent by this definition.

Candidate qualification uses the existing image/task preparation path. It
reproduces the complete observer ELF from its generated source and key,
validates the canonical CPIO and exact package members, and proves actual
AP-to-boot-to-loader-to-kernel/DTB/archive joins. Fresh actual ARM64 loader and
exception-level checks remain bound to each changed loader. System headers,
compiler/linker executables and their host libraries, startup objects and
linked static libraries are recorded and checked. Fresh complete reproduction
also measures GCC's declared linker plugin/wrapper and effective specs before
and after compilation; this does not backfill the original build receipt. A key-symbol mask is not
an acceptable substitute for complete producer reproduction.

Unchanged kernel/module and shared protocol/failure-path evidence remain
immutable with their original source, input, candidate and tool provenance.
They are reused as evidence of that unchanged machinery; they are not renamed
as fresh device, health, recovery or candidate-boot proof. Reproduction runs
only during H0 qualification. Session guards revalidate immutable records and
current source/artifact bindings; they never recompile or run a VM.

## Closed hardware scope and one-operation admission

This shared scope adopts the complete late hardware, witness, permit,
original-deadline and physical-recovery conditions of common boundary 3's
ML030 delegation. The existing ML034 bounded USB coverage conditions and
ML035 no-display producer correction also apply. This adopts those conditions,
not earlier artifact tables, approvals or consumed authority. The only return
specialization for V4/V5 is the narrow pre-overlay class below. V6/V7/V8/V9/V10/V11/V12 additionally
select the fixed automatic attempt above. The V5 diagnostic access, V6 HCE
handoff, V7 exact reset-configuration, V8 disabled-readiness and V9 initial
completion acknowledgement, V10 existing-read CFG1 diagnostics and V11 ordered
CFG1 selection plus V12 terminal link IRQ observation are limited to their
preceding fixed conditions; earlier report modes retain their meanings.

One healthy-Android-origin operation may transfer one boot-only N, authenticate
the first response within 120 seconds of its launch, then obtain a fresh
same-socket witness at least 300 seconds after sealing that response. It must
prove the same boot, kernel, DT, RAM SysVinit PID 1 and observer, at least
300 seconds of additional guest uptime and zero block devices before the
single durable module permit. The original 540-second host and guest ceilings
and 15-second module submission/command budget remain unchanged.

The sole fixed module retains the held-USB SH1/CN0 confirmation, fixed GDSC,
clock, PM8350 supply and the selected report mode's reset-pin preparation
(V7/V8/V9/V10/V11/V12 exact configuration/latch, earlier modes legacy output/high), qualified v4
Waipio PHY, six fixed local UniPro commands and at most one DME_LINK_STARTUP.
No generic UFS host/PHY/ICE or SCSI discovery path may bind the device. The
common SCSI library may remain compiled; this module registers no host or LU.
SCSI/media commands, fDeviceInit, LU/partition access, media-backed filesystems,
ICE/key operations, display clients, general commands and unattended effects
remain excluded. Uncertain requests retain their slots and never replay.

The existing physical-attach predicates and cue/control interlock remain
unchanged. The separately reviewed capture wrapper below only preserves the
fixed caller's raw result and suppresses late operator text. Current health, exact target/lane/host and original-A/recovery
checks precede effects. A new candidate requires validated prior healthy
closure and no unresolved owner. One N and one original A total are shared by
normal and physical return; neither failure nor later observation creates a
second attempt. There is no standing grant or same-candidate repeat lane.

## Narrow normal-return extension

Report v4, v5, v6, v7, v8, v9, v10, v11 or v12 is selected by the reviewed capability and matching module/guest
mode. It retains the 256-byte result envelope, authenticated result binding,
original one-shot controls and the 120/300/540/15-second limits. All existing
USB/PM/ICC/BCM and later UFS admission predicates remain in force, subject
to the explicitly reviewed V6/V7/V8/V9/V10/V11/V12 specializations above.

A normal Download may be represented by the H0 implementation after either
the existing successful link result or the new `PRE_EFFECT_REJECTION` class.
The new class requires an actual USB-coverage refusal before overlay dispatch,
no outstanding USB reference, no stage-two or later work, no fixed RPMh request
or error, and completed RPMh arena teardown. The module produces the certificate
only on that exact path; guest and host independently validate the matching
strict v4/v5/v6/v7/v8/v9/v10/v11/v12 encoding, including zero extra snapshot/handoff fields for v5/v6/v7/v8/v9/v10/v11/v12. A bare
stage-zero number, zero command count, failed function return
or `usb_released=false` is insufficient. Overlay attempts, partial preparation,
stage two and later failures, malformed/partial responses, unknown work and
expired windows remain outside that certified normal-return class. The separate
V6/V7/V8/V9/V10/V11/V12 recovery attempt does not reinterpret them as safe-idle or successful results.

Normal Download is still authenticated to the complete exact result, follows
one durable intent, requires the existing EOF and final deadline check, and
must reach exact Download before the one original-A transfer and final health.
Functional UFS status remains `NO_PROOF` for pre-effect refusal, even when
normal return succeeds. No earlier ML033–035 result is reclassified and no
consumed action gains replay authority.

## Authority, recovery and review reuse

The common permanent boundaries, selected target, exact rollback and usable
Download route, attendance, finite grant, lease/owner exclusion, durable
consumption and no-replay checks are unchanged. The existing mainline foreground
`ready` D0 profile applies to an exactly prepared V2 task; it creates no grant,
control or transfer. The returned finite approval and current physical
attendance remain required before dispatch. Review reuse covers only the
unchanged named capability; new hazards or changes outside its key-only scope
require review before use. Existing grants, source receipts and consumed
journals cannot be repinned. The immutable backend review must cover the
actual selected owner and recovery code before its selector advances.

Original-owner recovery obtains the selected review from the original immutable
task and capability metadata. It does not require candidate artifacts, keys,
compiler inputs, fresh qualification or a builder module. Its actual eagerly
imported owner, authority, transport, target, health and recovery dependencies
remain mandatory. Recovery and post-A health retain their existing durable
phase semantics and do not rerun pre-consumption absence checks.

The v1 exact declarations remain supported under their original policies and
reviews. They do not inherit this v4 mode or key-only reuse. A90 and S20+
contracts, authorities and artifacts are outside this specification.
