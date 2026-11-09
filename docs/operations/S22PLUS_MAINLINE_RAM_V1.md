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
`workspace/public/src/device-action/bindings/s22plus_mainline_ufs_link_bcm_alias_v1_review.json`
qualifies the reachable mainline/Android/transport capability. It names the
selected source closure, including shared owner/adapter modules; unreachable
vendor-native branches add no authority. Artifact provenance remains separate
from current observer provenance. Changed execution-critical inputs or a new
hazard require the common independent review. Retained reviews and consumed
grants are never repinned.

The operator must return the generated exact approval and a statement of
physical attendance and usable Download recovery. One grant permits **one
operation in 1800 seconds**, on the same host boot, including suspend. Its
normal graph for the read-only variants is:

`fresh rooted Android health -> Download -> N once -> USB evidence -> physical Download -> A once -> rooted Android health`

The separately qualified Download variant and its schema-exact rc-managed SSH
successor replace that physical normal return with one authenticated RAM
Download command. Both retain the original attended physical recovery if
normal control fails.

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

The separately adopted [ML030 mainline UFS link policy](S22PLUS_MAINLINE_UFS_LINK_V1.md)
defines its own fixed module, late witness and result-bound normal-return
scope. It requires an explicitly reviewed ML030 implementation and schema.
The separately adopted [ML031 followup](S22PLUS_MAINLINE_UFS_LINK_FOLLOWUP_V1.md)
uses the same bounded protocol for its distinct exact candidate and own grant;
ML030's consumed authority remains unchanged.
The separately adopted [ML032 refreshed-census followup](S22PLUS_MAINLINE_UFS_LINK_CUE_REFRESH_V1.md)
retains the same bounded hardware/protocol scope for its exact candidate and
own grant, with corrected cue ordering and unchanged final checks. ML030 and
ML031 stay consumed; their approvals and source bindings are not renewed.
The variants described below retain their own runtime and time bounds.

The base candidate executes its reviewed RAM PID1 and fixed one-client NCM
evidence responder; the schema-exact packaged SSH variant below adds only its
declared daemon and fixed unprivileged command. Linux UFS is compiled out and its controller/PHY disabled;
there is no installed-root mount, native_data access, journal replay, repair,
package operation or persistent filesystem data write. The base and SSH observers expose
no device control. Only the distinct Download variant and its rc-managed SSH
successor below admit their schema-exact normal control. Ordinary boot-only transfer writes only the boot partition. Existing
firmware/bootloader behavior is not relabelled as Linux storage access.

USB observation is bounded by the original N launch timestamp plus **120
seconds**, further limited by the original grant deadline. Fixed sysfs reads
select only the retained lane's **CANDIDATE_TOPOLOGY USB2 path**, with exact
candidate serial, descriptor, NCM driver, host MAC, interface and generation.
Absence may be polled within that window; any different device or ambiguity
stops. The source Android/Download path cannot substitute for USB2 evidence.

The first valid endpoint is an identity anchor, before any host profile exists.
After the existing full guard and immediately before the first profile intent,
one fresh complete census must match every anchor field except the interface
name. That current name is bound once in both the endpoint and profile intent.
The address-conflict check excludes only the anchored integer ifindex, so a
changed name cannot exclude an unrelated interface using the old label.
The original-window clock check remains after durable publication and before
profile creation. Once bound, all existing name-inclusive endpoint, profile,
socket, route and SSH checks remain strict; no later rebind or retry is added.
This replaces ML025's premature name freeze without a settling delay, repeated
equality requirement or dependency on a particular host naming policy. The
fresh pre-create check addresses changes before first binding; review it when
selection or profile binding changes, and retire this capture only when the
replacement supplies equivalent fresh identity at that binding point.

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

### Optional packaged Debian RAM PID1

The schema-exact `debian_ram` qualification admits only
`s22plus-mainline-debian-sysvinit-ram-v1`, mutually exclusive with `entry_park`.
The kernel directly executes `/init`, a symlink to the exact signed Debian
arm64 SysVinit 3.14-4 executable. Its fixed RAM closure contains only that
executable, the matching loader/libc/libselinux/libpcre2 members from four
qualified packages, the fixed static observer, required directories, fixed
console/null nodes and symlinks, and the two-line inittab. Runlevel 2 starts
the observer once, directly through the `@` executable form. No shell, getty,
shutdown helper, module loader, package manager or installed root is included.
Linux UFS remains compiled out. No new persistent-storage exception is granted.

The packaged init retains its standard startup: signal handling, console and
RAM utmp/runlevel/initctl state, and the CAD-disable call with `reboot(0)`
semantics. Its linked libselinux may mount proc/sysfs, try the fixed unavailable
selinuxfs locations and detach its temporary proc mount before init starts the
observer, with libselinux's original proc/sysfs mount flags of zero. The
selected kernel has no SELinux support or policy input. The
observer checks an inherited `/sys` with `statfs` and uses it only if it is
actually sysfs; otherwise it performs its original fixed sysfs mount and any
failure stops the observer. No generic EBUSY acceptance is permitted.
Standard package signal and failure handlers are not claimed absent: the
SIGRTMIN+4 shutdown executable is excluded, and SIGSEGV handling may fork and
attempt a core file in RAM. The fixed inittab requests no reset/reboot/halt.
This base schema exposes no control request. This adds no automatic recovery or claim
that all package/inherited hardware activity stops when the observer parks.

The separate wire magic/domain and 352-byte authenticated body retain all
original kernel/DT/CPU/block/timer fields and additionally bind the measured
observer PID above 1, PPID 1, single-level NSpid and equal PID namespace
consistency, runlevel 2/previous N, actual observer executable and fixed inittab
hashes. The original PID1 executable field must equal the actual package init
hash. Namespace equality alone does not prove the initial namespace: this
claim also requires the reviewed direct kernel-to-package startup with no
namespace creation, exact fixed CPIO and actual same-kernel ARM64 VM boot.
Legacy canary or VM proof cannot acquire physical Debian meaning.

Fresh qualification must join physical and explicitly VM-marked observer
builds from identical source/config/runtime inputs; exact signed package
members; actual CPIO types, nodes, symlinks and data; the changed loader and
boot/AP package; a complete positive authenticated VM capture; and the real
wrong-key one-request rejection. Complete raw inputs and current independent
exact-artifact review are required. Physical success is separately reported
as `PASS_DEBIAN_SYSVINIT_RAM_PID1` only after the ordinary original-A return
and complete final health. It establishes this bounded RAM PID1/direct-child
workload, not full Debian services, persistent Debian, SSH or endurance.

The finite attended grant, original 120-second window, one connection/request,
physical Download/original-A return, health-only continuation and no-replay
rules are unchanged. A candidate may retain the separately reviewed
[ML021 physical attach procedure](../reports/S22PLUS_MAINLINE_ML021_USB_ATTACH_H0_2026-11-04.md):
all of that procedure's cue, completion and no-replay conditions apply.
at most one phone-end detach for about three seconds, preserving cable/host
port/orientation and without buttons. Issue its explicit cue only after
raw-complete N and its completed install step, a published active original
window with more than 60 seconds left, the latest complete sealed USB census
showing ENOENT with no children, and no selected endpoint, request, stop, return
or terminal and no active N/A transfer. These are cue-issuance checks;
enumeration or a request may begin before
the operator's later physical action. Such a race retains the ordinary
one-shot fail-stop rules, with no request/connection replay. The action never
restarts or extends observation.
Resolve any outstanding cue as completed or cancelled before requesting a
separate physical Download confirmation. A replug answer is not that
confirmation. This physical condition proves neither that replug was required
nor a specific Type-C mechanism.

### Optional normal Download from packaged Debian RAM

Only `s22plus-mainline-debian-download-ram-v1`, with its separate exact
`download_return` qualification, selects the `mainline-download` Session
action. It uses the same fixed four-package RAM SysVinit closure and direct
observer child, without the SSH package/session variant. One connection carries
the authenticated 352-byte base body, its tag and complete length-framed FDT,
then at most one 88-byte fixed `download` command and one 120-byte acceptance
ACK. The separate domain, request/response/control/ACK magics, fresh nonce,
candidate identity and measured boot ID exclude legacy or other-boot commands.
There is no shell, generic command, additional connection or control retry.

The host seals the received prefix before interpreting its bounded FDT length,
then seals the complete frame before checking authentication, actual package
PID1/observer/inittab, kernel, live DT, existing health fields and the driver
readiness flag. Partial and rejected bytes remain private raw evidence.
Length completion does not claim EOF or a closed descriptor: the same socket
remains open. Driver readiness requires the exact reboot-mode class output,
platform driver and OF-node links. The current kernel's `reboot_modes_show`
returns one trailing NUL byte after its newline; this exact output is bound,
not trimmed or generalized. Readiness proves registration/binding, not the
later write, reset, firmware consumption or clearing of the reboot reason.

After full base validation, the existing original 120-second host window and
the device observer's separate original 120-second deadline still apply.
Before control, `s22plus_mainline_attach_v1.py` serializes actual cue publication,
resolution and closing further cue issuance under an operation-local lock;
it never reacquires the executing owner's global target lease. The cue's
existing fixed census/window checks run under this lock, and the issued record
must be durable before its instruction is emitted. A publisher refuses a
closed issuance record. An actually issued unresolved cue waits only within
the original observation window for an actual operator completion or explicit
cancellation, bound to that operation and cue. Silence and timeout are neither.
With no issued cue, issuance closes immediately without another human gate.
These interlocks prevent an outstanding physical replug instruction from
overlapping normal automatic A return. They apply to this Download variant and its rc-managed SSH successor; review them when attach or automatic-return sequencing changes,
and retire them only with evidence that no issued physical instruction can
overlap control/transfer or after removing this automatic-return capability.

The fresh Session check and unique durable effect intent precede the sole
control send. The intent binds the sealed base, exact command bytes, attach
closure and original observation deadline. At that intent it fixes once the
normal Download-arrival deadline to the earlier of 600 seconds later and the
original grant expiry. Neither ACK parsing nor a continuation renews it.
A final current endpoint and clock check precedes dispatch. Any uncertain
send is consumed, with no resend or reconnect. The device verifies the fixed
command, original nonce/boot binding, deadline and exact driver readiness,
then sends its authenticated ACK and shuts down only its socket write half.
The host retains ACK bytes and actual final connection status separately.
The device requires EOF without extra bytes within its original deadline,
rechecks deadline/readiness, then calls exactly one `RESTART2("download")`.
EOF establishes neither verified host receipt nor new authority. An absent
EOF, extra bytes, failed check or returning syscall parks without an alternate
reset, fallback syscall or repeated control.

This normal D1 control uses the qualified mainline built-in reboot chain:
`nvmem-reboot-mode`, the PMK8350 SID 0 SDAM peripheral at `0x7100`, its exact
one-byte cell at offset `0x48`, and bits 1 through 7. The sole DT addition is
`mode-download = <0x15>`; the existing NVMEM bitfield read/modify/write preserves
bit 0 and requests `0x2a | original_bit0`. The stock strict `download` table,
retained stock DT and actual mainline source/cell/config join are qualified
H0 inputs. The existing mainline SCM shutdown path separately requests
NODUMP in its TCSR download-mode field before the ordinary cold-default PSCI
SYSTEM_RESET path. This SDAM and SCM scope is normal reboot control, not Linux
storage or partition access. No raw NVMEM writer, new SMC, vendor module,
`reboot=warm` override, FULLDUMP, emergency-download command, bootloader write
or reset-core change is admitted. The reboot-mode notifier does not propagate
a cell-write failure to abort reset, so a mislanding remains possible and
requires the original attended physical recovery; registration is no promise
of recoverability.

Fresh qualification joins the actual ARM64 physical/VM observer builds,
same kernel, exact DT/config, complete framed positive and wrong-request-key
captures, actual QEMU normal restart plus wrong-control-key/boot/schema,
extra-byte, partial-control and missing-EOF cases, and fixed physical-binding,
final-deadline and returning-syscall C fixtures. QEMU has no Samsung PMIC;
its explicit readiness fixture proves protocol/reset behavior only. Host
raw/intent, cue race, normal-A and no-replay failure paths and independent
exact-artifact review remain required. Old read-only qualifications cannot
select this control.

After complete ACK/connection evidence, the existing coordinator automatically
waits for an exact Download arrival ticket and revalidation, transfers only
original A once, and obtains complete final rooted Android health. No extra
human Download confirmation is required for this machine-proved normal
arrival. `PASS_MAINLINE_DOWNLOAD_RAM` additionally requires the original
control intent, completed `install-android` transfer within that fixed return
window and final A health; a later permitted health-only continuation may
finish this same normal A. A physical `recover-android` transfer cannot
substitute for normal return proof. Failure preserves independently validated
base PID1/USB evidence while reporting the Download unit as `NO_PROOF`.
ACK, EOF and USB disappearance alone never prove reset or Download arrival.
This capability establishes neither full SysV shutdown nor automatic failure
recovery, unattended execution, persistence or Linux UFS access.

### Optional packaged Debian SSH in RAM

The distinct `debian_ram.schema=s22plus-mainline-debian-ssh-ram-v1` extends the
packaged SysVinit mode with one ordinary OpenSSH service and one fixed,
noninteractive public-key session. It remains mutually exclusive with
`entry_park`. The signed package/member allowlists and configuration in
`ssh_ram.py` define its complete closure: SysVinit, the three packaged OpenSSH
executables (`sshd`, `sshd-session`, `sshd-auth`), packaged dash and their
recursive ELF dependencies. Required PAM/Kerberos/audit libraries are included
as ELF dependencies; PAM, password, keyboard-interactive, GSSAPI and host-based
authentication are disabled. No package manager, PAM modules, standalone
SFTP server helper, module loader or installed root is included. The packaged
internal-SFTP implementation is unreachable through the fixed configuration.

The three-line inittab starts the existing observer and `sshd -D -e` as
parallel direct runlevel-2 `once` children, without a restart loop. sshd binds
IPv4 wildcard port 22 so its startup does not depend on the later USB address
assignment; there is no IPv6 listener. The exact CPIO includes root `.` as
root:root 0755, fixed secure ancestor directories, static console/null/zero/
urandom nodes, empty root-owned 0755 `/run/sshd`, files-only NSS accounts,
a locked root/privilege-separation account and one unexpired UID/GID 1000
`probe` account whose `NP` password field cannot provide a password login.
The root-owned authorized key is fixed outside the user's home. `StrictModes`
remains enabled. Host private key mode is 0600 and private images/keys remain
under `workspace/private/`; consumed evidence is retained unchanged.

Only a fresh per-candidate Ed25519 client key is admitted. The server rejects
root login, PTY, user RC/environment and all forwarding/tunnels. System sshrc,
login denial files and subsystem definitions are absent from the exact CPIO.
`ForceCommand` always selects the root-owned fixed probe through packaged
dash's normal `-c` behavior, regardless of the requested command. Undefined
subsystem requests, including SFTP, are rejected before command execution.
The probe uses only shell builtins to read this boot's ID and its own
UID/GID/groups/effective-capability status; it has no caller-supplied command,
path, reset or storage operation. Successful output must report every UID/GID
as 1000, supplementary group 1000 only and zero effective capabilities.

OpenSSH retains its actual standard startup and session behavior: entropy and
cryptographic initialization, socket/auth parsing, privilege separation,
seccomp/chroot, account checks, process/fd/signal handling and the nonroot shell
execution. Its Linux OOM helper may write its own proc OOM adjustment and
children restore the previous value; if proc is not yet mounted it skips that
adjustment. Its RAM pidfile and ordinary package RAM accounting/log attempts
are in scope. This is not a claim that a RAM kernel cannot affect hardware:
BLOCK, DEVMEM and KEXEC configuration is not changed, and standard privileged
sshd parsing is a new reviewed runtime surface. The fixed nonroot command,
exact file closure and absent Linux UFS access bound this experiment.

After accepting and authenticating the single original observer request, the
observer waits at most ten seconds, within its original absolute boot deadline,
for a complete decimal sshd pidfile and a matching live `/proc/<pid>/exe` path.
Exact package source publishes the pidfile after listen. Missing/partial or
nonmatching data never supplies readiness. This positive startup indication
is not authentication or continued-life proof. It is carried in a distinct
SSH wire domain/magic with the existing 352-byte body and reserved fields.
If not ready, the base response may still prove Debian PID1/USB; it does not
permit an SSH attempt or any retry. This bounded check addresses the concrete
parallel-start connection-refusal race; it is reviewed again when startup or
package behavior changes and may retire when a successor provides equivalent
readiness without an additional connection.

After the complete base proof, the host may invoke its qualified `/usr/bin/ssh`
exactly once, with config loading, agent use, password methods, proxying,
connection reuse, PTY and forwarding disabled. It pins the candidate host key,
client key, selected source IP and port 22, and uses one connection attempt.
The installed client's address bind is not `SO_BINDTODEVICE`. Immediately
before SSH, an unconstrained route lookup from that exact source must select
the already bound NCM interface directly, with no gateway; the endpoint
censuses and cryptographic host/boot join remain required. The invocation has
a maximum twenty-second timeout, further bounded
by the remaining original 120-second N observation window, reserving the
existing raw producer's four-second termination settlement. Its absolute
`CLOCK_BOOTTIME` deadline includes host suspend and is rechecked before spawn,
around acquisition polling and while waiting for the client to exit. This is deadline
accounting, not atomic cancellation of a remote child on host suspend.
Complete endpoint
censuses immediately before and after must retain the selected USB generation.
The durable intent is published before spawning; stdout, stderr and exit/
timeout status are sealed before parsing. Any failure, partial result, changed
endpoint, expired window or uncertainty stops this unit without another client
invocation, connection or request. The ordinary physical original-A recovery
owner remains available. SSH KEX/auth contains normal protocol exchanges;
`MaxSessions 1` is per connection, not a claim of one lifetime server session.

H0 qualification includes the actual signed closure and canonical CPIO,
matching physical/VM sources and SSH keys, same-kernel packaged startup, the
existing wrong-HMAC rejection, and complete one-connection SSH cases for valid
key, wrong key, root, ignored arbitrary command and denied PTY/forwarding/SFTP.
The tested host SSH executable is bound
into the task. Independent review covers this coherent runtime/host/evidence
change and the exact candidate artifacts. Physical success requires one
successful fixed SSH result joined by boot ID to the authenticated base proof,
followed by original-A return and complete final health; its terminal label is
`PASS_DEBIAN_SSH_RAM`. Failed SSH cannot erase separately proved base PID1/USB,
but cannot obtain that SSH success label.

The same finite attended grant, physical attach cue conditions, separate
Download confirmation, original-A return, health-only continuation and consumed
no-replay rules remain binding. The twenty/120-second limits govern observation
and the host client; they do not stop sshd, PID1 or the kernel and do not prove
automatic recovery. The daemon may continue listening until physical return.
This scope establishes bounded standard SSH access and a packaged nonroot
workload in RAM, not a general interactive shell, persistence, endurance,
physical entropy timing, replug necessity or automatic recovery.

### Optional fixed entry park

The schema-exact optional `entry_park` qualification admits one fixed diagnostic
variant of V1: the actual Image executes `wfe` and a back-branch immediately
after `s22_retained_kernel` returns in `primary_entry`, before
`record_mmu_state`. This is an unconditional build-time source transformation,
without a runtime or VM-specific escape. It adds no RAM write, MMIO, reset,
storage effect or recovery command beyond the existing V1 writers and owner.
The qualified Image intentionally does not reach RAM PID1 or USB; its expected
USB absence is not a functional fault or a diagnostic stage observation.

This diagnostic requires complete changed-Image/source and measured loader
layout qualification, the existing actual-loader/marker guard tests, and the
actual packaged loader and Image executing to the fixed park in QEMU at real
EL1 and EL2. The exact receipt must prove preserved entry EL, the linked two
loop instructions and a bounded PC trace remaining in the park, no
`record_mmu_state` reach, unchanged header/outside-slot bytes,
both fresh V1 frames on eligible inputs, and park reach after invalid-magic and
short-index writer skips. A WFE that remains waiting does not prove execution
of the back-branch; the fixture injects no wake event or execution-state change.
An unparked Image's RAM-PID1 VM result cannot replace
these checks. The optional source declaration, binary, raw cases and diagnostic
receipt must join the image and its independent exact-artifact review; a
missing declaration or qualification fails admission. The existing finite
attended grant, fixed 120-second observation, physical Download/original-A
recovery, health, no-replay and post-closure reader are unchanged.

Positive returned frames retain V1's build-specific stage-occurrence meaning;
they do not prove physical stop PC, continuous park, a unique attempt, a
same-boot pair or the cause of any earlier result. Missing frames do not prove
park reach, execution depth, skipped writes or retention loss. This diagnostic
is optional research, never a prerequisite for RAM-PID1/USB admission. ML018
selects one such candidate; its result does not authorize another park or an
unchanged repeat. Further work must be selected from its bounded evidence and
any concrete new source fact under the ordinary contract.

### Optional early retained markers

An image carrying the schema-exact `retained_marker` qualification may add
only the reviewed `s22plus-mainline-retained-marker-v1`,
`s22plus-mainline-retained-marker-v2`, `s22plus-mainline-retained-marker-v3` or
`s22plus-mainline-retained-marker-v4`, `s22plus-mainline-retained-marker-v5` or
`s22plus-mainline-retained-marker-v6`, `s22plus-mainline-retained-marker-v7` or
`s22plus-mainline-retained-initcall-trace-v8` or
`s22plus-mainline-retained-deferred-probe-v9` or
`s22plus-mainline-retained-deferred-probe-v10` diagnostic writer. These formats
are mutually exclusive in one candidate. V2–V7 replace both preceding sites;
V8–V10 replace the pair with their finite observations defined below.
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

### V9 deferred-probe observations

V9 replaces V8's complete regular-initcall trace with six unchanged fixed
PID1 milestones, a sparse final-table selection and bounded observations
inside `deferred_probe_initcall`. It preserves the exact RAM slice, unchanged
header, latched contiguous window, prefix invalidation/body/prefix-last stores,
barriers, two temporary Normal-NC/XN mappings and reverse cleanup. It permits
at most 4,096 128-byte slots, 512 KiB of distinct payload and 557,056 log byte
stores per kernel-init attempt. Each event is attempted at most once, with its
seen bit consumed before mapping, including failed or skipped writes. Header
drift disables remaining writes without obstructing lifetime closure.

The fresh final ELF supplies every regular PREL32 entry and level boundary.
The sparse selection is the first entry of each nonempty level and every entry
from `boot_wait_for_devices` through the final regular entry. That anchor must
be unique and followed by `sync_state_resume_initcall` and
`deferred_probe_initcall`; overlapping ordinals are deduplicated. Generated
selection arrays, frames and original dispatch order are checked against the
final linked code. Earlier candidates' tables do not qualify a new Image.

The exact candidate DTB supplies all nodes with `compatible` or `reg` and all
their ancestors, regardless of status. Before basic setup, PID1 resolves those
absolute paths and holds node references. Lookup and reference release run
outside preemption exclusion. NULL lookup entries never match a NULL device
node. No-OF and unlisted-OF observations have separate fallback buckets;
there is no nearest-parent substitution. A match identifies only an OF-node
association: multiple devices or drivers can share one node. Missing lookups
and noncatalog devices do not gain an inferred identity.

Persistent device hooks are armed at the first statement of
`deferred_probe_initcall`, preventing earlier probes from consuming their
events. Phase 1 begins there; PID1 sets phase 2 immediately before the second
trigger. The phase describes what an entry hook observed, not which trigger
caused an asynchronous callback. Per phase/node, the five points are before
the worker's PM-list move and `bus_probe_device`, after that bus call returns,
before `device_set_driver` after supplier checks, and directly before/after
the selected bus or driver probe callback. Neither callback branch means no
callback event. The setup point does not prove subsequent pinctrl, DMA or
power-domain preparation completed; a bus return can merely queue async work.

Only the first admitted entry attempt for a phase/node/point receives a local
return token, including when its mapping fails. The return uses that token's
original phase and node without rereading either. Nested or later entries
sharing an event receive no token. The worker entry/return pair follows the
same rule. This avoids a nested invocation filling the first invocation's
return slot within an attempt; it does not establish paired records across
firmware attempts or complete retry history.

Ten body milestones cover function entry, debugfs-call return, both trigger
and flush boundaries, the return from the optional timeout scheduling call,
and the point before final exit. The scheduling marker does not inspect the
boolean queueing result. The timeout worker and any callback beginning after
disarm are outside this observation window. Their absence from records is not
evidence that they did not run. No heartbeat, new workqueue, timeout change,
driver suppression, callback return-code interpretation or runtime crypto is
added.

PID1 and worker writes share the same state under preemption exclusion on the
sole online boot CPU. The persistent wrapper first rejects non-task contexts
and, under exclusion, rejects multiple online CPUs or the wrong CPU before
reading its live dispatcher pointer. The exact forced `maxcpus=1` command
line, delivered DTB and enabled-caller closure must exclude CPU onlining and
competing IRQ/softirq/NMI early-map users throughout the window. A runtime CPU
check alone is not that proof. Interrupt masking and ordinary driver/workqueue
behavior remain unchanged; the mapping path must not sleep or allocate.

The pointer is NULL before preparation. Under the same exclusion, the sole
deferred-initcall exit clears it even if recording has already failed. Thus
no worker can still execute or re-enter init code through this hook when PID1
leaves that function.
Persistent hooks thereafter are inert. Direct `__init` PID1 markers continue
through the post-async milestone; final cleanup clears the pointer and drops
held references before init-memory freeing. An async flush is not treated as
a drain of every ordinary or delayed worker. No mapping survives a hook.

Fresh qualification includes actual linked write bounds, seen-event behavior,
failed maps, sticky drift and interrupted stores; the actual hook's guard,
token, nested-node, phase-crossing, reference and post-free no-op paths; and
real EL1/EL2 PID1/worker contexts with full init traversal, no linear alias,
temporary mapping attributes and restored mapping state. A same-build layout
probe binds task/device offsets. Mocked APIs remain explicitly distinguished
from real MMU and scheduler evidence. QEMU catalog fixtures bind the DTB
actually delivered at entry rather than assuming the requested DTB survives
loader edits. Separate timing runs have no per-event counter breakpoints.

These checks address shared-mapper, stale-init-pointer, wrong-node/token and
expanded-evidence hazards only for V9. Changed sites, writer/gate, context,
catalog rules, table selection, decoder, enabled callers or reservation trigger
review. They retire when a reviewed successor removes those mechanisms or
supplies equivalent evidence; they add no prerequisite to original-A recovery.
The schema/domain, source-bound capability and exact artifact qualification
are separate from older formats. Old grants and reviews do not authorize V9.

Every accepted frame remains at-least-once evidence in this candidate's
attempts. A pre-call point does not prove callback-body entry or the recording
helper's subsequent return. A post-call point proves a return, not success.
Missing frames cannot locate a failure or reset, and static records establish
no same-boot sequence, last attempt, unique driver, retry count, userspace or
USB. Physical execution still requires the exact finite attended grant and
the unchanged original-A recovery/health path.

### V10 early and TLMM observations

V10 retains V9's sparse final-table selection, exact DT-derived node catalog,
generic deferred-probe hooks and finite write/lifetime boundaries. It uses
one C writer and one shared latch. It adds direct `__init` calls immediately
after `early_ioremap_init` and before `setup_machine_fdt`, immediately after
`setup_arch` returns, and on entry to `kernel_init_freeable`. These precede
the existing twenty fixed points. No assembly marker or second window is
combined with this format.

The effective span and contiguous window retain V9's formula. A complete
eligible event e uses `window + effective_span - 128*(e+1)` only after checking
`128*(e+1) <= effective_span`. Lower event IDs therefore occupy the newest end
of this window, including short history. This is a placement property, not
proof of improved physical retention. The first distinct event that reads a
valid header and an index of at least 128 latches all four header words and
the window; its own slot eligibility is checked afterward. An earlier
failed/skipped event never retries. An early latch extends the interval over which header equality
is required. Any observed drift still disables later writes permanently and
does not obstruct disarm or final cleanup. No relatching or recovery writer
is added.

The early call requires the actual bootstrap task/stack, sole boot CPU and
pre-scheduler preemption state, live early fixmap tables, current-EL MMU-on
and little-endian guards. Qualification verifies its complete preemption
restoration, masked IRQ state, Normal-NC/XN mapping attributes and absence of
another mapping over the log slice in the live early translation tables.
The post-setup point additionally qualifies the transition to the late
fixmap selector and no linear alias. Neither call resolves OF nodes or
publishes the persistent dispatcher. Existing PID1 preparation does so before
regular initcalls, and remains responsible for held references.

V10 adds one exact OF association, `/soc@0/pinctrl@f100000`, to a token-scoped
`msm_pinctrl_probe` observation. Three groups describe the phase sampled on
entry: prepared but not yet armed, deferred phase 1, and deferred phase 2.
They are not retry ordinals or trigger provenance. Each group's first admitted
entry receives one local token even if its recording fails. Repeated or nested
entries in that group receive no token. All later points use that token's
original group and task owner, never a newly sampled phase. Only exact token
encodings and declared point IDs are accepted; a classified return closes
that group's active token. Generic device hooks retain their V9 arm boundary.

The seventeen TLMM points are entry, resource-mapping return, before/after
IRQ lookup, before/after pinctrl registration, after the pinfunction loop and
before pinctrl enable, after pinctrl enable, GPIO helper entry, after its
wakeup-parent branch, before/after gpiochip addition, after the GPIO-ranges
branch, GPIO helper return, and three distinct final return classes: zero,
`-EPROBE_DEFER`, or another value. Post-call points precede the existing error
checks and prove return only. A wrapper preserves the original exported
signature, calls the original body once, records its return class and returns
the unchanged value. Its sole GPIO helper receives the local token. Existing
conditions, error side effects and ordinary driver calls remain unchanged.
No per-GPIO, IRQ-handler or locked callback instrumentation is added.

Persistent TLMM helpers reach init memory only through the same task-only,
sole-CPU, preemption-protected dispatcher. Before preparation and after the
deferred-initcall exit they are inert. Original direct init markers continue
through the pre-free async return; final cleanup releases the OF references.
No mapping spans a hook or driver call. No extra MMIO, storage, watchdog,
interrupt-mask change, workqueue or runtime cryptography is permitted.

The catalog places the twenty-three fixed events first, then the three
seventeen-point TLMM groups, sparse initcall pairs and generic node events.
Frame IDs and C constants derive from this single declaration. The same
4,096-slot, 512-KiB payload and 557,056-byte-store ceilings apply. A fresh
final ELF/DTB inventory binds the actual count, linked hooks, catalog, frames
and init/persistent sections. Old V9 artifacts and decoders retain their
original identities and interpretation.

Fresh qualification covers early-to-late latch continuity, reversed bounds
and short history, early and later mapping failures/drift, actual bootstrap
and PID1/worker contexts, token/owner/nesting/phase/return behavior, preserved
driver-body semantics and inert post-free hooks. These V10 checks address
early mapper/context, event-label, token and init-lifetime hazards in this
format; changed inputs trigger review, and a reviewed successor may retire
them only by removing the mechanism or providing equivalent evidence. They
add no prerequisite to original-A recovery.

Every positive remains at-least-once occurrence in this candidate's attempts.
A return-class record proves that class occurred; it establishes neither
successful overall boot nor causality of a board-data correction. Records
from a group need not share a boot or invocation in the retained payload.
Missing later/high-numbered records prove neither failure localization nor
overwrite, short initial history or non-execution. Earlier latch drift and
unresolved return/retention continuity remain possible limitations. USB/PID1,
original-A return, final health and physical retention coverage stay separate.
The existing exact finite attended grant and recovery graph are unchanged.

### Fixed Debian rc-managed SSH cycle in RAM

The distinct `s22plus-mainline-debian-rc-ssh-ram-v1` manifest and wire
domain specialize the packaged SSH and normal Download variants for **one
SSH service cycle**. The signed package closure in `service_ram.py` adds
only the fixed rc and SSH scripts, their helpers and dependencies. There
is no general rc directory or hook population. A direct PID-1 wait child
prepares the fixed RAM mounts, and another runs packaged `/usr/lib/init/rc 2`
with only S01ssh. Its one wrapper invokes unmodified `/etc/init.d/ssh start`.
The responder runs once as a direct child eligible in both levels 2 and 6.
The startup frame authenticates the same-boot start/rc records and exact
packaged master executable, PID, start ticks and PID-1 parent. Neither the
script exit code nor a listening port alone counts.

On the existing framed base socket, close cue issuance and resolve an actual
outstanding replug instruction before the one permitted fixed UID/GID 1000 SSH
command on its own connection. Recheck the endpoint, route, SSH raw completion
and same boot before the fresh Session intent binds those exact bytes. A
failed or uncertain SSH command cannot be retried or followed by control.
One authenticated command on the original base socket permits exactly one
packaged `/usr/sbin/init 6` submission. The only rc6 link K01ssh invokes the
same wrapper and unmodified stop script against the original master. Record
exclusive intents, original boot, levels, script and rc completion, old
master disappearance, absence of the pidfile and zero matching packaged
SSH executables. No other halt, shutdown, signaling sweep, mount transition
or package service is exposed. A zero telinit or script status alone is
insufficient. A deadline can leave a submitted transition incomplete; no
stage, SSH session, control, reset or transfer may replay.

The 168-byte authenticated ACK binds that stop evidence to the original
master, observer, nonce and boot. It does not prove reset. The existing
write-half shutdown, empty peer EOF, exact reboot-mode binding, final clock
check and one normal Download restart apply. Extra bytes or late EOF after a
valid request may leave SSH stopped; neither permits a reset or a second
request. Original observation/grant/return deadlines, N/A transfer limits,
physical Download fallback and final Android health remain unchanged.

Exact qualification uses both signed CPIOs with the same kernel, packaged
service success and failure cases, same-boot SSH and control raw evidence,
source/driver joins, and current independent capability/artifact review. Only
the full cycle followed by actual normal Download, original A and complete
health can earn `PASS_DEBIAN_RC_SSH_CYCLE_RAM`. Earlier evidence may survive
a later failure. This does not establish complete system shutdown, signal
causality, storage, persistent Debian or automatic failure recovery. Review
this variant again if package links, evidence, privilege, dispatch, deadlines
or return semantics change; retire its extra stage checks only with equivalent
service proof or removal of the service-cycle variant.

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

Only the mainline original-A return-health path selects
`MainlineReturnAndroid`, including a later permitted health-only continuation.
Its existing readiness shell read prints the Android boot ID before
`boot_completed`; its existing properties read prints the same nine fields with
the boot ID first. It adds no connected command or snapshot read. Readiness
still uses the original deadline, at most 256 inventory iterations and the
existing 0.5-second interval. Successful EOF-truncated outputs that are lexical
prefixes of the fixed readiness grammar remain not-ready; only a complete
UUID and `boot_completed=1` establish readiness. Malformed non-prefix output,
unexpected producer failure, diagnostics, overflow or source/owner failure
retain the existing stop behavior. The fixed seven-read health bracket,
same-boot target/partition checks and full-health acceptance remain unchanged.
Preapproval, preflight, post-closure D0 and other profiles retain their existing
commands. This class does not select the separate native in-call root-read
reobservation exception.

Existing raw receipts preserve observed boot IDs for offline return-continuity
analysis. A readiness observation has only its exact inventory/serial binding;
it does not inherit a missing topology observation or constitute health.
An abandoned property prefix is likewise not a complete health bracket.
Diagnostic ID agreement or disagreement never gates original-A recovery or
final health and never reuses a prefix in a new health attempt. Earliest
observed identity is not earliest actual boot; different observed identities
do not establish that candidate frames existed or were erased, and equal IDs
do not diagnose the mechanism of an ADB disappearance. These checks address
the ML012/ML013 missing-return-identity observation gap. Changes to the command
grammar, scope or acceptance trigger review; a reviewed successor may retire
them by replacing the observation with equivalent evidence or removing it.

For the read-only variants, after complete observation the owner asks for physical Download, within ten
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
