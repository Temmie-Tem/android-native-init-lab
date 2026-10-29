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
`workspace/public/src/device-action/bindings/s22plus_mainline_retained_v1_review.json`
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
only the reviewed `s22plus-mainline-retained-marker-v1` diagnostic writer.
Absent that receipt, the image remains the RAM/USB variant and may not contain
instrumented loader/kernel marker bytes. The immutable qualification joins the
actual linked loader and kernel entry, candidate identity, generated frames,
unchanged-header bounds, instruction tests, actual-EL fixtures and independent
artifact review. A source/preparation marker without its complete receipt is
not an ordinary unmarked candidate. Existing consumed artifacts retain their
original provenance and reviews.

The exact RAM destination is the retained FYG8 `samsung,kernel_log_buf` slice
at physical `0x800200000`, size `0x200000`. Its 16-byte header remains unchanged.
Each site selects its own 128-byte half of a 256-byte span behind that site's
sampled byte index, using the reviewed contiguous placement. The selected span
can change if firmware moves the index between sites. Each eligible site writes
only its own slot with byte accesses, invalidates its commit prefix first,
checks all four header words before committing, and completes stores with
barriers. The sites are loader handoff after all payload copies and mainline
`primary_entry` before `record_mmu_state`. Both independently require EL1/EL2,
little-endian data, MMU off and data cache off before any log access; unsuitable
state/header/index skips recording and continues the original boot. They do
not change mappings, header fields, interrupt controls, storage, watchdogs or
the logger. The existing no-map reservation is retained.

The 256 distinct payload bytes are a bound per two-site boot attempt, not a claim that a boot
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
