# S22+ mainline RAM/USB first boot V1

Status: **REVIEW_GATED_CAPABILITY**

This is one ordinary attended F1 boot-only experiment for the operator-owned
`SM-S906N/g0q/S906NKSS7FYG8`. It implements the common
[Process-v2](DEVICE_ACTION_PROCESS_V2.md) state machine using the existing V3
Session, target lease, consumed-candidate registry, measured boot-only Odin
transport, physical original-A recovery and fixed rooted Android health.
The selected target adopts this exact mainline adapter. It does not activate
vendor-native baseline admission, a filesystem exception or unattended work.

## Scope and admission

The initial candidate is `ml001/mainline-ram-1/mainline-ram-v1`: the qualified
g0q uniLoader/mainline kernel, RAM PID1, reduced DT and USB2 NCM responder.
One private task binds its exact AP/member, key commitment, runtime artifacts,
retained artifact provenance, target, host lane, original-A rollback and
demonstrated recovery evidence. The actual boot-v4/AP is revalidated against
the qualified loader; matching repeated packages and actual ARM64/EL tests
remain H0 evidence. ABL acceptance and physical USB work are unproved until
the real run. No generic candidate override is exposed.

The source-bound independent `PASS_GO` receipt at
`workspace/public/src/device-action/bindings/s22plus_mainline_retained_v8_review.json`
qualifies the reachable mainline/Android/transport capability. It names the
selected source closure, including shared owner/adapter modules; unreachable
vendor-native branches add no authority. Artifact provenance remains separate
from current observer provenance. Changed execution-critical inputs or a new
hazard require the common independent review. Retained reviews and consumed
grants are never repinned.

The operator must return the generated exact approval and a statement of
physical attendance and usable Download recovery. One grant permits **one
operation in 1800 seconds**, on the same host boot, including suspend. Its
only normal graph is:

`fresh rooted Android health -> Download -> N once -> USB evidence -> physical Download -> A once -> rooted Android health`

Preparation is H0 and may reuse retained target/recovery records. It neither
opens a grant nor establishes current device health. Fresh source/artifact,
target, lane, host readiness, global-owner/consumption and rooted Android
health checks must pass before Download intent. The common preapproval
identity/health requirements still apply; a proposed task is not READY merely
because its H0 preparation passes.

The target's separately reviewed
[uniLoader-to-Android comparison](S22PLUS_LOADER_ANDROID_V1.md) adopts this
same named preapproval D0 and `ready` CLI with its own exact task/profile
validation. Its fixed original-A transcript, exclusion, durable evidence and
freshness are identical. This D0 reuse does not select a RAM candidate or
transfer this policy's runtime, grant, observation or continuation authority
to the distinct comparison operation.

The named `s22plus_mainline_task_v1.py ready` foreground D0 entry obtains only
the existing fixed Android identity/root/partition-digest health transcript,
selected host/lane checks and preapproval raw evidence. It requires no pending
F1 owner and no opened grant, and creates a durable task journal before approval.
The current foreground S22+ research task authorizes this fixed read without
physical attendance or another per-read request. A failed read ends that
invocation; a later fixed reobservation preserves it and does not discharge
another owner. A grant binds the latest completed readiness, same host boot,
and health no more than 300 seconds old when the grant opens. This freshness
check guards stale preapproval health, applies only before the first grant,
and expires with the task; later effect checks and recovery retain their own
rules. Missing readiness cannot be replaced by H0 qualification.

## Runtime and observation

The candidate executes only its reviewed RAM PID1 and fixed one-client NCM
evidence responder. Linux UFS is compiled out and its controller/PHY disabled;
there is no installed-root mount, native_data access, journal replay, repair,
package operation, persistent data write or device control command in the
observer. Ordinary boot-only transfer writes only the boot partition. Existing
firmware/bootloader behavior is not relabelled as Linux storage access.

USB observation is bounded by the original N launch timestamp plus **120
seconds**, further limited by the original grant deadline. Fixed sysfs reads
select only the retained lane's **CANDIDATE_TOPOLOGY USB2 path**, with exact
candidate serial, descriptor, NCM driver, host MAC, interface and generation.
Absence may be polled within that window; any different device or ambiguity
stops. The source Android/Download path cannot substitute for USB2 evidence.

The host may create one nonpersistent NetworkManager profile with a fresh
task-owned UUID, autoconnect disabled, fixed candidate subnet, no default
route/DNS and IPv6 disabled. It checks subnet conflicts and a direct route.
One socket is bound to the selected interface and source address. One fresh
nonce request is sealed before a single connection/send attempt; complete or
partial response bytes and producer status are sealed before interpretation.
There is no reconnect or request retry after uncertainty. The protocol proves
actual RAM PID1 identity, selected kernel release, live DT semantics and
reservations, one CPU, no block devices, timer health and a fresh authenticated
response. Descriptor visibility alone proves none of these.

### Optional early retained markers

An image carrying the schema-exact `retained_marker` qualification may add
only the reviewed `s22plus-mainline-retained-marker-v1`,
`s22plus-mainline-retained-marker-v2`, `s22plus-mainline-retained-marker-v3` or
`s22plus-mainline-retained-marker-v4`, `s22plus-mainline-retained-marker-v5` or
`s22plus-mainline-retained-marker-v6`, `s22plus-mainline-retained-marker-v7` or
`s22plus-mainline-retained-initcall-trace-v8` diagnostic writer. These formats
are mutually exclusive in one candidate. V2–V7 replace both preceding sites;
V8 replaces the pair with its finite trace defined below.
Absent that receipt, the image remains the RAM/USB variant and may not contain
instrumented loader/kernel marker bytes. The immutable qualification joins the
actual linked loader and kernel entry, candidate identity, generated frames,
unchanged-header bounds, instruction tests, actual-EL fixtures and independent
artifact review. A source/preparation marker without its complete receipt is
not an ordinary unmarked candidate. Existing consumed artifacts retain their
original provenance and reviews.

The exact RAM destination is the retained FYG8 `samsung,kernel_log_buf` slice
at physical `0x800200000`, size `0x200000`. Its 16-byte header remains unchanged.
For V1–V7, each site selects its own 128-byte half of a 256-byte span behind that site's
sampled byte index, using the reviewed contiguous placement. The selected span
can change if firmware moves the index between sites. Each eligible site writes
only its own slot with byte accesses, invalidates its commit prefix first,
checks all four header words before committing, and completes stores with
barriers. The V1 sites are loader handoff after all payload copies and mainline
`primary_entry` before `record_mmu_state`. Both independently require EL1/EL2,
little-endian data, MMU off and data cache off before any log access; unsuitable
state/header/index skips recording and continues the original boot. They do
not change mappings, header fields, interrupt controls, storage, watchdogs or
the logger. The existing no-map reservation is retained.

V2's first site is the start of `__primary_switch`, immediately before its
page-table register preparation and `__enable_mmu` call. It uses the same
EL1/EL2, little-endian, MMU-off, data-cache-off assembly writer and first slot.
Its second site is in `setup_arch`, after `early_fixmap_init` and
`early_ioremap_init` and before `setup_machine_fdt`. It independently requires
EL1/EL2, little-endian data and the current EL's MMU enabled. It maps only the
fixed 16-byte header and selected second 128-byte slot using
`early_memremap_prot` with non-executable Normal-NC attributes, including a
second page when that slot crosses a page boundary. Header reads remain four
aligned words and slot writes remain byte stores. It unmaps every successful
mapping in reverse order on success or rejection; unavailable mapping, invalid
header/index or changed header leaves no new complete frame. There are at most
two map attempts and no retry. The writer does not alter the no-map reservation,
create a cached alias or modify MMU control registers, interrupt controls,
peripherals, storage or watchdogs. This is a fixed early-kernel temporary
mapping, not general RAM-access authority.

V2 qualification additionally executes the actual linked C writer's bounds,
guards, mapping-failure and interrupted-store cases, and boots the same kernel
through real MMU setup and mapping/unmapping in QEMU. That fixture includes
cross-page placement, exhausted mapping slots and header changes, and verifies
that no temporary mapping remains. H0 cannot prove physical cache coherency or
retention. V2's distinct frame magic/version and stage IDs must be decoded from
the exact candidate qualification; V1 records retain their original meaning.

V3 replaces both V2 sites with two calls in `setup_arch`: immediately after
`setup_machine_fdt(__fdt_pointer)` and immediately after `paging_init`, both
before `early_ioremap_reset`. There is no assembly marker or pre-FDT C call.
Each call uses the same C writer mechanics, with only its compile-time symbol,
frame and fixed half-slot changed. The MMU/endian guards, two bounded Normal-NC
mapping attempts, header stability check, byte stores and reverse cleanup
remain unchanged; compiler stack/PAC protections are retained. Firmware may
move the header index between calls, so adjacency is not promised.

The post-paging site requires the exact candidate's active no-map log
reservation. Its additional qualification blocks a conflicting cacheable
linear alias: the exact Image runs with a QEMU-shaped no-map fixture, actual
page-table walks show no linear translation across the log slice while
adjacent ordinary RAM translates and is readable, and the Normal-NC temporary
writer and unmap finish. Both actual EL1 and EL2 paths and a first-site guard
skip followed by a positive second site are qualified. This check is scoped
to V3's post-paging writer; it does not gate V1/V2 or recovery. It is retired
only if a separately reviewed successor removes that post-paging mapping
hazard or replaces this evidence with equivalent mapping proof. Changed site,
mapping machinery or reservation is its review trigger. Generic QEMU RAM
without the no-map hole is not this qualification, and H0 is not physical
cache-coherency proof.

Actual linked calls must place the first writer after the FDT scan's success
path and read-only remap, and the second directly after `paging_init` returns.
The schema-distinct V3 frames are decoded only from their exact qualification;
older records retain their original meanings. A later positive with an absent
earlier record is valid positive evidence, not a contradiction or new stop.

V4 replaces both V3 sites with two calls in `start_kernel`, immediately after
`setup_arch(&command_line)` returns and immediately after `time_init` returns,
before `random_init` and ordinary IRQ enablement. It uses a fresh fixed
stage pair, schema, magic and integrity domain. `setup_arch` and the assembly
entry are unmarked. Its generated definitions precede the complete annotated
`start_kernel` declaration; the existing function attributes and helpers'
stack/PAC protections are retained. Writer guards, slots, Normal-NC attributes,
header checks, byte stores and reverse cleanup are unchanged.

Both V4 calls follow `early_ioremap_reset` and use this exact ARM64 tree's
late fixmap set/clear path. They retain V3's no-linear-alias requirement at
both new sites, including after core allocator initialization. Additional
qualification runs the exact Image through real EL1 and VHE EL2 with the
late-branch selector set, IRQs masked and `SYSTEM_BOOTING`. At both calls it
proves no linear translation for the fixed log slice, positive adjacent RAM
translation/read calibration, Normal-NC non-executable temporary mappings
and complete temporary PTE/slot cleanup. Both actual linked calls must follow
their named returns directly. Guard and mapping failure cases remain bounded.
The late-mapping qualification addresses lifetime, alias and cleanup hazards
only for V4; it is not a new prerequisite for older formats or recovery.
Its review trigger is changed callsite, mapping/lifetime machinery or
reservation. It retires only when a separately reviewed successor removes
the late writer or substitutes equivalent safety evidence. H0 proves no
physical cache coherency or physical page-table format.

V5 replaces both V4 sites with two calls in `start_kernel`: after
`early_boot_irqs_disabled = false` immediately before `local_irq_enable`,
and immediately before `rest_init`, after `kcsan_init`. Its new schema,
magic, integrity domain and stages 9/10 retain the same C template, two slots,
guards, attributes, header checks, byte stores and reverse cleanup. It does
not mask/unmask interrupts or change preemption itself. Both helpers remain
in init memory; the new candidate contains no earlier marker calls.

V5 qualification retains V4's real EL1/VHE EL2 late-mapping, no-linear-alias,
positive calibration, temporary-attribute and complete-cleanup evidence at
both sites. It additionally establishes that both calls run in the initial
bootstrap task on the boot CPU, with one online CPU, `SYSTEM_BOOTING`, and
low 32-bit preemption count 1; the upper reschedule field may vary. IRQs are
masked at the first point and unmasked at the second. These are qualified
source/context properties, not dynamically encoded fields in the static
physical records. The exact enabled source/config/DT closure must exclude
a competing early-map caller reachable from interrupts, softirqs or irq_work
before `rest_init`; `maxcpus=1` alone is insufficient. The first linked call
must immediately precede IRQ enablement, and the second must immediately
precede `rest_init`. The qualifier derives task offsets from that build's
generated definitions rather than assuming a historical structure layout.

This V5-only requirement addresses global early-map slot reentrancy and
bootstrap lifetime across IRQ enablement. Changed sites, context, enabled
callers, mapping machinery or reservation trigger review. It retires only
when a separately reviewed successor removes this writer/context hazard or
substitutes equivalent safety evidence. It adds no requirement to consumed
formats or original-A recovery and proves no physical interrupt delivery,
timer tick, cache coherency or later task execution.

V6 replaces both V5 calls with two calls in `kernel_init`: immediately after
`wait_for_completion(&kthreadd_done)` returns, and immediately after
`async_synchronize_full` returns, before the `SYSTEM_FREEING_INITMEM` store
and init-memory freeing. Its distinct schema, magic, integrity domain and
stages 11/12 retain the unchanged C template and two-slot bound. The `__ref`
caller reaches the init-only helpers and data while that memory is still live.
It adds no IRQ/preemption manipulation and contains no earlier marker calls.

Both V6 calls use the late fixmap path in the preemptible kernel PID1 task,
with `SYSTEM_SCHEDULING`, low 32-bit preemption count zero, IRQs unmasked and
one online boot CPU. Its actual EL1/VHE EL2 qualification observes these
properties at each helper's entry and return, including the same task as
`kernel_init` entry, PID1 and the initial PID namespace's child reaper.
It derives PID/reaper layout from that Image's compiler/config and generated
headers using a private host-only offset probe; CPU/preemption offsets are
calibrated against the build's generated definitions, and actual PID0/PID2
provide independent field calibration. Historical numeric offsets are not
answers. Physical static frames do not dynamically encode these properties,
and this kernel-task witness does not satisfy the RAM-userspace PID1/USB proof.

V6 retains the no-linear-alias, positive adjacent-RAM calibration, temporary
Normal-NC/XN attributes, bounded failure and complete cleanup evidence at both
new sites. The mapping fixture supplies the exact hash-bound candidate
initramfs so the later initialization path is reachable, and stops before
userspace execution. The separate full RAM-PID1 VM keeps its own VM initramfs
and unseeded/invalid-header skip path. The exact enabled caller/config/DT
closure must exclude competing task, work, async and interrupt early-map users
after initcalls and Linux consumers or aliases of the protected no-map slice.
One online CPU or `async_synchronize_full` alone does not establish exclusivity:
exclusive async domains, ordinary workers and future queued work remain outside
that synchronization. A writer-local guard cannot serialize a suspended peer.

This V6-only qualification addresses preemptible mapper reentrancy, init-memory
lifetime and post-initcall reservation ownership. Changed sites, enabled
callers, mapping/lifetime machinery, initramfs or reservation trigger review.
It retires only when a separately reviewed successor removes those observer
hazards or substitutes equivalent evidence. It adds no gate to older formats
or original-A recovery, and no forced scheduler-stress test without a concrete
uncovered hazard.

V7 replaces both V6 calls with two calls in `kernel_init_freeable`, immediately
before and after its sole `do_basic_setup()` call. Its distinct schema, magic,
integrity domain and stages 13/14 retain the same writer, two slots and guards.
The first point follows `page_alloc_init_late` and the earlier pre-SMP initcalls;
it is not before all initcalls. The second follows driver-model setup and the
regular initcall traversal, before the explicit `wait_for_initramfs` and the
remaining initialization tail. Both helpers and their caller remain init-only
and are reached before `kernel_init` frees init memory.

V7 adopts V6's same-build layout and actual PID1 entry/return context checks,
late mapping/attribute/cleanup, no-linear-alias and adjacent-RAM calibration,
physical-initramfs fixture binding, and enabled mapper/reservation exclusions
at its own new sites. The actual linked Image must show the calls surrounding
the compiled basic-setup region. When helpers are inlined, qualification binds
the actual boundary calls and regular initcall loop/cleanup rather than
requiring a nonexistent `do_basic_setup` call or historical instruction offsets.
The pre-SMP initcall loop remains before the first marker. Source generation
must preserve both loops and contain only one call to each recording helper.
The same mapper reentrancy, reservation and init-lifetime hazards, review
triggers and retirement conditions apply; older formats and recovery gain no
new prerequisite. This pair adds no IRQ/preemption manipulation or repeated
per-initcall writes.

For V1–V7, the 256 distinct payload bytes are a bound per two-site boot attempt, not a claim that a boot
loop touches only 256 bytes across the entire operation: firmware may move the
index between attempts. Each site runs at most once per entry, has a fixed
instruction/write bound and no internal retry. Header checks detect some
interference and do not establish exclusive ownership or future retention.
The existing finite experiment/USB observation and attended recovery limits
are unchanged.

These static candidate-bound records support positive **at-least-once stage
occurrence during the candidate's attempts**. Integrity validation and exact
artifact provenance are required; the embedded tag is not a fresh runtime
challenge response. Records do not prove one shared boot, last attempt, ordering
across resets, reset cause, PID 1 or authenticated USB. Missing, torn, foreign
or overwritten records never prove non-execution or where execution stopped.
The live USB/PID1 result and original-A recovery/health remain separate.
An observed V2 `pre-mmu` frame proves entry to that site's writer, not MMU
enablement. An observed `early-c` frame proves execution in the named
MMU-enabled `setup_arch` path, including prior entry to `start_kernel`; it does
not prove FDT setup, subsequent initialization or userspace.
V3 `post-fdt` proves the named post-FDT recording point in that candidate;
`post-paging` proves the post-`paging_init` point and return from that candidate's
preceding helper call along the sequential path. The preceding call may have
skipped writing. Neither record proves its own later unmap/return, any
subsequent initialization, or a historical candidate's writer return.
V4 `post-setup-arch` proves return from that candidate's `setup_arch` call;
`post-time-init` proves return from its `time_init` call and from the preceding
recording helper call along the sequential path. A preceding helper may have
skipped its write and some or all cleanup calls. Neither record proves its
own later cleanup/return, delivery of interrupts, working timer ticks or any
later initialization. Missing V4 records do not transfer an earlier candidate's
progress boundary into this candidate.
V5 `pre-irq-enable` proves its recording point before ordinary IRQ enablement;
`pre-rest-init` proves its recording point after the intervening initialization
and return from this candidate's earlier helper call. That call may have
skipped writing. The later point follows the IRQ-unmask instruction but proves
neither IRQ delivery nor timer ticks; `calibrate_delay` may use the frequency-
derived fast path. Neither record proves its own subsequent cleanup/return,
entry to `rest_init`, PID1, or an earlier candidate's helper return. A later-only
positive does not create a missing earlier record or a same-boot pair.
V6 `post-kthreadd-wait` proves its recording point in this candidate's
`kernel_init` after the named wait returned; it is not a sleep/wakeup, specific
scheduler-call, IRQ-delivery or timer-tick witness. `post-async-sync` proves its
point after `kernel_init_freeable`, the preceding helper call and
`async_synchronize_full` returned along the sequential path. The earlier helper
may have skipped writing and cleanup. Returned initcalls or synchronization do
not establish driver success, successful initramfs unpack/access or global
background quiescence. Neither record proves its own later cleanup/return,
freeing init memory, userspace exec or an earlier candidate's helper return.
A later positive with missing USB does not eliminate earlier nonfatal driver
defects or localize a fault after initialization. Missing or later-only records
retain the same non-localizing positive-only meaning as the earlier formats.

V7 `pre-basic-setup` proves the named recording point after the preceding
kernel-thread preparation and early initcalls returned, not the helper's own
return or entry into basic setup. `post-basic-setup` proves return from this
candidate's preceding helper call and basic setup along its sequential path;
the preceding helper may have skipped writing or some or all cleanup. It does
not prove successful initcall return codes, driver/probe success, initramfs
completion, global background quiescence, the helper's own later return or the
remaining tail. The early/pre-SMP and regular initcall loops are distinct.
Both/later-only positives require no shared-boot record pair. Any absent site
retains the existing non-localizing meaning and grants no replay or cause claim.

### V8 consolidated regular-initcall trace

V8 replaces the two-site writer with one finite parameterized C writer in
`init/main.c`. Slots 0–5 are respectively immediately before basic setup,
after `driver_init`, before command-line allocation in `do_initcalls`, after
basic setup, after the explicit `wait_for_initramfs`, and after
`async_synchronize_full` before init-memory freeing. The regular
`do_initcall_level` loop records immediately before and after each existing
`do_one_initcall` dispatch. Early/pre-SMP and module dispatches are unchanged.
No initcall is skipped, added, reordered or repeated by the instrumentation.

For the qualified final table of N regular entries, slots `6+2*k` and
`7+2*k` record dispatch entry and return for ordinal k. The declaration permits
1–2,045 regular entries and at most 4,096 128-byte slots, or 512 KiB of
payload per kernel-init attempt. Each reachable event has at most one attempt
and two temporary mapping calls; it has no internal retry. Ordinals come from
the actual four-byte PREL32 entry pointer with alignment/range/phase guards,
and the actual table extent must equal the compiled declaration. An invalid
ordinal or table extent disables further trace writes while ordinary boot
continues. A fresh final Image/ELF inventory binds ordinal labels, level
boundaries and the complete embedded frame array. A retained table or matching
count alone cannot supply the new build's function labels.

The 512 KiB ceiling counts distinct slot payload. Prefix invalidation adds
eight byte stores per committed record: the maximum is 4,096 × 136 = 557,056
log byte stores per attempt, all within those slots. Writer state and stack
remain ordinary init/task memory rather than additional log destinations.

Frames contain a fresh candidate identity, V8 magic/domain, event and table
count under the existing offline integrity construction. No runtime crypto,
function address, return code or timestamp is added. All code, constant frames
and small writer state remain in live init memory through the last call.
The six fixed slots take priority when available log history is short; their
numeric IDs are not chronological progress ranks.

V8 retains the exact 2 MiB no-map slice, unchanged 16-byte header, current-EL
MMU-on/little-endian guards and temporary Normal-NC/XN mapping mechanism.
At the first distinct event with a valid header and index at least 128, it
latches all four header words and one contiguous window. Effective span is
`floor(min(index, declared_span)/128)*128`. Its position is
`cursor-span` when `cursor >= span`, otherwise `payload_size-span`, with
`cursor=index%payload_size`. Only a complete slot inside that effective span
may be written. This keeps eligible short-history records inside the reader's
prefix without assuming that a later full returned log proves a large initial
index. A skipped earlier event is never retried; a later distinct event may
establish the window if none was latched.

Each record compares the current header with that initial snapshot before any
slot store and again before committing. Header drift permanently disables
further writes in that attempt; the window is never shifted or reopened.
Prefix invalidation, body byte stores, prefix-last commit and full barriers
remain mandatory. Every successful header/slot map is removed in reverse order
before returning, including after drift or mapping failure. A mapping failure
does not retry that event; a later distinct event may use the same latched
window. No early mapping is held across an initcall or the level-7 leak check.
Firmware reboot attempts retain independent per-attempt bounds and may select
different windows. Header equality proves neither firmware exclusivity nor
physical retention.

Fresh V8 qualification covers the actual linked ordinal wrapper, writer
guards, short-history/span boundaries, mapping failures before/after latching,
sticky header drift, interrupted stores and unchanged bytes outside each
permitted slot. Real EL1/VHE EL2 full traversal uses the physical candidate
initramfs, same-build calibrated PID1 context, no linear alias, Normal-NC/XN
temporary attributes and complete prior mapping-state restoration. It checks
each event's cardinality across the full path through the final pre-free call.
Timing measurements run separately without per-record debugger stops and are
H0 costs only; they do not promise unchanged physical reboot timing. Existing
enabled-caller/config/DT exclusions remain necessary for the non-reentrant
early mapper. Prior two-site case counts are not V8 qualification.

These V8-specific checks address parameterized write bounds, ordinal identity,
window overlap, mapper lifetime/reentrancy and evidence-size hazards. Their
scope is this format; changed sites, count/layout, writer, decoder, mapper,
enabled callers, initramfs or reservation trigger review. They retire only
when a separately reviewed successor removes the corresponding mechanism or
provides equivalent evidence. Older formats and original-A recovery gain no
new prerequisites. Expanded records require the fresh source-bound capability
review and exact candidate qualification; older reviews and grants do not
authorize them.

An entry record proves the point before wrapper dispatch, not entry into the
callback body. A return record proves that dispatch returned, not a successful
return code, driver match, probe or async work. The fixed later milestones
prove their named returns, not successful unpacking, global quiescence,
userspace exec or USB. Each positive remains at-least-once evidence for that
candidate's attempts. Missing return/other frames cannot identify a failed
function, last attempt or reset cause; grouped offsets and record counts do
not establish shared boots. The decoder groups duplicate offsets so a maximum
bounded capture fits the existing durable-record limit. Original raw evidence,
the final ordinal table, USB proof, original-A recovery and health stay separate.

### Fixed post-closure retained-marker D0

The named `s22plus_mainline_retention_v1.py` capture is a foreground D0 profile
for the current mainline research task, without attendance or another per-read
approval. It selects only an instrumented mainline task with rederived
`s22plus-comparison-task-closed-v1` closure, its exact one N and one original-A
transfer, candidate consumption, complete raw final Android health and no
unresolved F1 owner. It never invokes repair, changes old journals or borrows a
Debian/calibration task's authority. Current observer review is separate from
the preserved execution/artifact provenance.

Under the existing exact-target lease it reads fixed rooted Android health,
requires the same boot as the completed original-A return, checks ADB shell-v2,
then acquires `su -c 'cat /proc/last_kmsg'` once with a 30-second timeout,
4 MiB stdout and 16 KiB stderr bounds. Complete raw producer status and bytes
are sealed before projection. A second fixed health bracket must prove the
same target, partitions, properties and Android boot. No arbitrary proc path,
RAM read, control, transfer, storage command or grant is exposed.

Failure ends that invocation and preserves its raw prefix and stop record.
A later fresh invocation may repeat only these fixed read-only observations,
with the same closed owner and fresh health; it does not reuse a partial
capture, resolve another owner, renew an experiment or replay an effect.
Projection can be repeated from complete retained raw evidence without a new
device read. Marker output does not revise the closed USB/PID1 verdict.

The marker codec, artifact builders/tests and this post-closure collector are
not original-A recovery prerequisites. Their absence or failure cannot add a
candidate step before recovery; the existing owner, target, A, transfer and
raw-health checks remain mandatory.

## Return, interruption and evidence

After complete observation the owner asks for physical Download, within ten
minutes and the original grant. The normal A dispatch uses that return
request's deadline, not the initial Android Download window. Failure, expiry,
missing evidence or host interruption stops candidate work and retains the
owner for the original attended A recovery. Same-host recovery may follow the
existing expired-grant recovery rule; it never renews candidate authority.
Unknown activity and unproved automatic recovery remain explicit.

Candidate intent/consumption never replays. A started observation can only be
rederived from its complete original raw evidence. Missing/partial evidence
routes to physical recovery. A raw-proved result publication failure allows
H0 publication repair, never another request or transfer. A completed A with
missing final health permits only the existing fixed health handling; an
uncertain A transfer never repeats. Terminal publication repair is H0.
Candidate files, keys and host network tools are not recovery prerequisites;
the exact recovery code, A, target and demonstrated recovery remain required.

Owned host-profile cleanup follows A handling and cannot delay device
recovery. Its failure is reported separately and never invalidates proven A
health or authorizes an extra transfer. It may remove only the exact task UUID
after checking its name, MAC and interface. No unrelated host connection is
changed.

The final structured result distinguishes authenticated mainline PID1/USB,
original-A return/health, and automatic recovery (unproved). Failed mainline
proof can close as `NO_PROOF` only after the independent A/health requirements
are met. Keep the append-only journal, raw bytes, exact sources and canonical
timeline private. This first capability also gets a concise public report.

This initial one-candidate scope is reviewed again before a successor changes
runtime, storage, control, health or recovery semantics. It creates no lasting
device-safety exception or prohibition beyond the common permanent boundaries.
