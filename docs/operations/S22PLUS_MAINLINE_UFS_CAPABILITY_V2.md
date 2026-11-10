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
predicates and same-read evidence below. V4/V5 do not inherit these changes. Each immutable capability binds
exactly one report mode and matching module/observer; mode is not candidate data.

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

### V6/V7/V8 automatic Download attempt and original-owner recovery

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
Any complete valid authenticated V6/V7/V8 result may select return, including load/read errors or later
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
specialization for V4/V5 is the narrow pre-overlay class below. V6/V7/V8 additionally
select the fixed automatic attempt above. The V5 diagnostic access, V6 HCE
handoff, V7 exact reset-configuration and V8 disabled-readiness specializations are limited to their
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
(V7/V8 exact configuration/latch, earlier modes legacy output/high), qualified v4
Waipio PHY, six fixed local UniPro commands and at most one DME_LINK_STARTUP.
No generic UFS host/PHY/ICE or SCSI discovery path may bind the device. The
common SCSI library may remain compiled; this module registers no host or LU.
SCSI/media commands, fDeviceInit, LU/partition access, media-backed filesystems,
ICE/key operations, display clients, general commands and unattended effects
remain excluded. Uncertain requests retain their slots and never replay.

The existing prepared physical-attach caller and cue/control interlock remain
unchanged. Current health, exact target/lane/host and original-A/recovery
checks precede effects. A new candidate requires validated prior healthy
closure and no unresolved owner. One N and one original A total are shared by
normal and physical return; neither failure nor later observation creates a
second attempt. There is no standing grant or same-candidate repeat lane.

## Narrow normal-return extension

Report v4, v5, v6, v7 or v8 is selected by the reviewed capability and matching module/guest
mode. It retains the 256-byte result envelope, authenticated result binding,
original one-shot controls and the 120/300/540/15-second limits. All existing
USB/PM/ICC/BCM and later UFS admission predicates remain in force, subject
to the explicitly reviewed V6/V7/V8 specializations above.

A normal Download may be represented by the H0 implementation after either
the existing successful link result or the new `PRE_EFFECT_REJECTION` class.
The new class requires an actual USB-coverage refusal before overlay dispatch,
no outstanding USB reference, no stage-two or later work, no fixed RPMh request
or error, and completed RPMh arena teardown. The module produces the certificate
only on that exact path; guest and host independently validate the matching
strict v4/v5/v6/v7/v8 encoding, including zero extra snapshot/handoff fields for v5/v6/v7/v8. A bare
stage-zero number, zero command count, failed function return
or `usb_released=false` is insufficient. Overlay attempts, partial preparation,
stage two and later failures, malformed/partial responses, unknown work and
expired windows remain outside that certified normal-return class. The separate
V6/V7/V8 recovery attempt does not reinterpret them as safe-idle or successful results.

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
