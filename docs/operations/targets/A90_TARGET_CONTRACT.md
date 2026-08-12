# A90 Binding Target Contract

Contract-Revision: **2** (supersedes revision 1; 2026-08-03)

Status: **BINDING**

This contract specializes `AGENTS.md` for the operator-owned Samsung Galaxy A90 5G. It is not authority for S22+, another A90, or an ambiguous USB endpoint.

`GOAL_A90.md` owns the changing experimental state and next objective. This file
alone neither arms A90 nor opens a D1/F1 campaign. Standing D0 and autonomous use
of D1 presence modes require the active trial and live inputs. The permanent A90
exception survives retirement but grants no authority by itself.

## Inheritance and Precedence

Read contracts in this order:

`AGENTS.md -> A90_TARGET_CONTRACT.md -> GOAL_A90.md`

Every common invariant and permanent device, repository, and evidence boundary
in `AGENTS.md` applies. This contract may specialize only the delegated A90
H0/D0/D1/F1 workflow. It cannot relax boot-only payload scope, the forbidden
raw-action list, exact target isolation, rollback availability, candidate
no-replay, private evidence handling, or the requirement for demonstrated
physical recovery. The active common trial controls procedural conflicts;
otherwise the more restrictive applicable rule wins.

The following documents remain implementation references beneath this target
contract:

- `docs/operations/NATIVE_INIT_FLASH_AND_BRIDGE_GUIDE.md`;
- `docs/operations/A90_F1_ATTENDED_OBSERVATION_V1.md`; and
- `docs/operations/A90_RESIDENT_BOOT_PROMOTION_V1.md`.

They do not independently grant authority. During the common trial, their
stricter v1 state machines are implementation compatibility constraints on
existing runners until changed and tested; they do not narrow trial policy or
require a campaign-level planner.

## Target Isolation

- Resolve exactly one A90 target and its private profile before every D0, D1,
  or F1 action. Keep serials and topology identifiers private.
- When multiple devices are attached, inventory them first, select A90
  explicitly, and report that S22+ and every other target were untouched.
- A90 commands, health evidence, rollback artifacts, approvals, and transport
  identities never apply to S22+.
- Any target ambiguity, unexpected identity change, or lost physical recovery
  path ends the current live session.

## Operating Model

The A90 experiment economy is:

`one attended F1 resident install -> many D1 no-payload experiments`

F1 deploys an exact boot-only native-init candidate and keeps an exact V2321
rollback ready. D1 performs switch-root, return, reboot, display, and service
experiments without another partition payload. A D1 result never qualifies a
new boot image and cannot be used to disguise an F1 action.

Device safety state and experiment proof are separate axes:

| Axis | Results | Meaning |
|---|---|---|
| Device safety | `BASELINE_HEALTHY`, `RESIDENT_HEALTHY`, `RECOVERY_REQUIRED` | Whether the exact A90 remains controlled and recoverable |
| Experiment proof | `PROVED`, `REFUTED`, `NO_PROOF_OBSERVER` | Whether the requested handoff/display/return claim was established |

`REFUTED` and `NO_PROOF_OBSERVER` do not by themselves make a previously
verified resident boot unsafe. Conversely, a visible screen, USB notification,
or parser PASS cannot override a device-safety failure.

## A90 H0

H0 includes source/build work, rootfs and boot-image inspection, deterministic
build checks, parser and framing-codec replay, report generation, and dry runs
with all target access hidden. It grants no device authority.

- Use captured raw logs as a replay corpus. Correct known historical
  misclassifications instead of treating the old verdict as ground truth.
- A host parser, report, or observer failure stops that host invocation, not
  the resident candidate line. Diagnose, repair, and focused-test it at H0.
- Repeating the same observer defect stops that observer implementation until
  repaired; it does not force a candidate flash or rollback.
- A pure parser/classifier update may be recorded per observation without
  invalidating resident boot identity. A change to command dispatch, retry
  count, allowlist enforcement, transfer, or recovery logic requires focused
  safety review and any new binding enforced by the current runner, but still
  does not require an unchanged resident image to be reflashed.

## A90 D0

D0 is exact-target, bounded, connected read-only inspection.

- Permit identity, current native version/build, health, sysfs/procfs, pstore,
  host USB inventory, and existing-file metadata reads with explicit bounds.
- Do not reboot, hand off, enter recovery, start or stop a service, mutate a
  file or setting, or send a payload.
- A D0 observer failure closes only that read. It creates no D1/F1 authority
  and does not make an otherwise controlled resident unsafe.
- With more than one attached device, name A90 as the selected target and
  explicitly confirm S22+ received no command.

## A90 D1 Resident Session

The namespaced risk label is `TIER_D1_TRANSIENT_NO_PAYLOAD_CONTROL`; historical stage names such as `STAGE_D1_CHROOT_MVP` are not risk labels.

Under the active trial, the agent selects and iterates exact allowlisted D1 effects while
the exact resident is `HEALTHY` and one presence mode below holds. Policy imposes no per-action approval or action/time budget.

**Attended mode.** For a bound `RESIDENT_HEALTHY` A90 with a proved return channel, the
operator is present and able to stop D1. Download entry is not required for D1. A90 F1 is always attended and requires physical recovery entry.

**Qualified unattended mode (`A90_UNATTENDED_RESIDENT_D1_V1`).** This permanent A90-only
exception requires the exact target and resident identity from the last durable
`RESIDENT_HEALTHY`, reconfirmed by fresh bounded D0 before every ordinal. Automatic
native return must remain proved; physical recovery remains demonstrated and available when the operator returns. S22+ never inherits this exception.

The unattended allowlist contains only an exact, previously qualified no-payload
resident action using unchanged reviewed dispatch and return machinery;
`SWITCHROOT_EXPERIMENT` is the currently qualified action. Its expected terminal is automatic native return. F1, payload/partition writes,
persistent settings, credentials, security state, package/rootfs/recovery mutation,
and actions expected to need physical entry are ineligible. Each ordinal has one
durable intent, one dispatch, and no automatic replay. No next ordinal starts until exact `RESIDENT_HEALTHY` is durable.

An absent or late ACM/NCM endpoint after an announced transition enters common
`HEALTH_PENDING`; it is not by itself target ambiguity or resident-health failure.
Permit passive inventory, bounded health reads, USB-epoch stabilization, H0 observer repair, or a recovery park.
Never start a new ordinal before exact resident `HEALTHY`, and never resend the uncertain action.

In unattended mode, control loss or `RECOVERY_REQUIRED` parks with no new effect;
operator return and predeclared recovery are then required. Target ambiguity,
resident mismatch, or lost physical recovery stops the lane under the permanent
boundaries. Explicit operator stop also ends it. The agent may repair an H0 observer
and start a new ordinal without acknowledgement only after independently re-establishing
exact health; the same unresolved observer defect must not become a blind loop.

The existing v1 runner implements only attended `A90_D1_ATTENDED_SESSION_V1`
and requires `--operator-attended`. Until a reviewed runner implements the
unattended mode, that lane is policy-ready but not executable. Never assert
`--operator-attended` while the operator is absent or asleep.

The legacy v1 session binding must contain:

- the exact A90 target/profile and current resident boot identity;
- the exact ready rollback identity and recovery path;
- an exact command/action allowlist;
- an explicit positive duration no greater than eight hours; the immutable host
  template does not expire before use, and consumption durably fixes opening and
  expiry;
- an explicit positive action budget no greater than 32; and
- the return-health predicate and device-effect runner closure.

The legacy v1 runner rules are:

1. Announce each action, send it once, append one compact result, and decrement
   the budget. No blind automatic loop is permitted.
2. Allow only transient actions named in the binding, such as native-init UI
   hide/show, one switch-root handoff, one bounded native return or reboot, and
   transient start/stop of an already-installed Debian experiment service.
3. Forbid partition payloads, arbitrary shell expansion, persistent settings,
   credential/security changes, package/rootfs changes, and recovery mutation.
4. Expected USB disconnect/re-enumeration during an announced reboot or
   handoff is an observation, not by itself a failure.
5. End this attended compatibility session on expiry/budget exhaustion,
   operator absence, identity change, lost rollback/recovery, an unallowlisted
   effect, operator stop, or device-safety failure.

If framing, timeout, or parsing fails after an action but the previously
verified resident remains operator-controlled and an independent bounded check
can distinguish observer failure from device failure, close that experiment
`NO_PROOF_OBSERVER`. Never automatically resend the uncertain device action.
After exact cleanup and health, the operator may acknowledge the result and
start one new ordinal with the unchanged observer, or repair it at H0. This
legacy acknowledgement is not replay: it requires new durable intent and
consumes another action. A second observer-only no-proof with that observer
closes the session. Continue only while target, resident, rollback, allowlist,
effect runner, expiry, and budget are unchanged.

If observer failure cannot be distinguished from target ambiguity, control loss, or resident-health failure, end the session and select the predeclared recovery path. The same confirmed device-effect failure twice stops live A90 experimentation; the same host parser defect twice stops only that parser implementation.
The separately reviewed attended D1 sub-capability `A90_ATTENDED_SD_ROOTFS_GC_V2` may unlink one nonempty manifest-selected set of at most 32 obsolete A90 SD rootfs files only from exact V3406 `RESIDENT_HEALTHY`. The runner derives every selection from an exact successful absent-only staging result, its unchanged prepared-manifest binding, and the same exact private host-preserved bytes. Each device object remains a single-link regular mode-`0600` 2 GiB file bound by path, size, SHA256, device/inode, and an allowlisted Debian-rootfs filename. The current resident source, incident-preserved image, work/staging paths, symlinks, directories, hardlink aliases, mounted or loop-backed files, open file descriptors, other mount namespaces, and current-root references are never selectable.
A fresh D0 inventory and immutable execution binding replace per-file phrases or per-set review; the runner may generate its legacy compatibility token internally because it is not a policy authority gate. The manifest and split live preflight bind the exact canonical bridge generation, complete transitive source closure, current physical V2321 rollback/recovery identity, and the successful absent-only publication evidence for every selected byte identity. Every serial control frame is bounded below the resident `cmdv1x` envelope; the one effect frame uses a host-proved compact selector that round-trips only to the fixed allowlisted runtime paths and carries ordered filesystem/inode identities, never a staged script or arbitrary path. After all bounded hashes and use checks, the runner rechecks inventory age, exact target, the same bridge generation and source closure, rollback/recovery binding, and exact V3406 health immediately before durable intent. One durable transaction then permits one nonrecursive unlink dispatch for the whole selected set with no retransmit. Response or host-process loss after durable dispatch may resume only from that exact journal for read-only reconciliation/health, never to resend cleanup. A repaired exact canonical bridge generation may replace the pre-effect generation only for this observation and exact recovery; every new cleanup effect still requires fresh D0 and its bound process. Partial/unknown effect, protected drift, or unproved health parks.
After unlink dispatch only, exact absent selected bytes may be restored while attended through a separate sequential durable no-clobber recovery transaction; restoration is never automatic, and an uncertain reserve, transfer, or publish is never replayed. Recovery response or host-process loss after a durable restore start likewise resumes only journal-bound read-only reconciliation/health and never repeats reserve, transfer, publish, or cleanup. PASS requires all selected paths absent, all protected identities exact, work and restore staging absent, increased bounded free space, and final exact V3406 health.
Cleanup sends no payload, and recovery may transfer only the manifest-bound preserved SD-file identities; neither path writes a partition, configuration, credential, or security state, grants arbitrary path or shell authority, or applies to S22+, userdata, another removable device, another A90, or an unreviewed identity.

The one-use attended D1 sub-capability
`A90_ATTENDED_V2321_H3_SOURCE_RECLAIM_V1` addresses the bounded hazard
`SD_CAPACITY_EXHAUSTION_WITH_INCIDENT_SOURCE_COLLATERAL_DELETION`. It may unlink
only the exact host-preserved H3 run-10 keyed source after the closed H4 run-11
incident has restored exact V2321 health. The H4 run-11 keyed source is one
separately exact protected identity and is never selectable. Selection and
protection are fixed by run ID, path, 2 GiB size, mode `0600`, single link,
SHA256, filesystem device and inode, successful absent-only staging evidence,
and exact private host-preserved bytes. The exact boot-only V2321 rollback and
attended physical Download or TWRP path remain required.

A fresh inventory no older than 15 minutes must bind the exact A90 and bridge
generation, exact V2321 health, selected and protected identities, absent work
and all known staging paths, and bounded filesystem capacity. Immediately
before durable intent, the runner revalidates the complete source/evidence and
rollback closure, target, bridge, V2321 health, both file identities, and every
visible PID mount namespace, open file descriptor, loop backing file, and
current-root reference for the selected source. One durable intent permits one
nonrecursive host-encoded unlink dispatch and no retransmission. Before that
dispatch, one capability-wide exclusive receipt consumes the capability across
all run IDs and remains consumed after PASS, non-PASS, ambiguity, interruption,
or later external restoration. Missing or
malformed response permits only journal-bound read-only reconciliation with a
fresh exact A90 bridge generation; it never resends unlink.

PASS requires the selected H3 source absent, the protected H4 incident source
exact, work absent, bounded free-space gain consistent with one 2 GiB file, and
final exact V2321 health. A non-PASS terminal parks without retry. Host
preservation is evidence but grants no restore authority; restoration would be
a separate reviewed transaction. This capability sends no payload, flashes no
partition, changes no configuration, credential, or security state, and never
applies to S22+, userdata, another path, removable device, or A90. It retires
after its first exact PASS, on any selected/protected identity or closure
change, or at `2026-08-06T00:00:00Z`, whichever comes first. Capture, manifest,
and execution fail closed at expiry; post-dispatch read-only reconciliation may
continue. Extension requires review.

An automatic-handoff resident candidate must publish one versioned compiled
rootfs binding receipt before candidate intent. The candidate version/build,
compiled Debian image path and SHA256, and versioned enable/latch paths in that
receipt must equal the immutable F1 keyed source and handoff command, the
resident terminal manifest/journal interpretation, and the D1 remote
path/rootfs SHA256. Missing, duplicate, stale, or unequal values stop before a
device effect. Every replacement candidate uses a new build identity, absent
rootfs destination, and absent versioned state paths; a prior enable/latch pair
is never reused, cleared, or reinterpreted to authorize the replacement.

The separately reviewed `A90_DIRECT_UFS_READONLY_ROOT_V2` capability is the
only alternative to that SD-image binding. It applies solely to the existing
A90-owned ext4 appliance selected by the exact userdata `PARTNAME`, block
device name, sector count, filesystem UUID, label, appliance marker, and one
versioned public content-manifest semantic SHA256. The manifest binds the
exact mode, owner, size, and SHA256 of every executable or library required for
PID 1, SSH, display, NCM, and Wi-Fi startup; private authorized-key and Wi-Fi
enable files are checked only for exact safe structure and are never hashed or
logged. Public-tunnel enablement and every unreviewed network configuration
must be absent.

The numeric block `dev_t` is not a cross-boot identity: the kernel may assign a
different major:minor to the same `sda33` userdata partition after reboot.
V2 therefore resolves it afresh from the sole `PARTNAME=userdata` sysfs entry
inside each qualification/handoff session. That runtime value may only create
and validate the private block node in the same session. The stable checks
remain exact `sda33`, sector count, size range, writable-capable block state,
unmounted state, UUID, label, appliance marker, and content manifest. Any
existing by-name or private node must match the freshly resolved `dev_t`; a
duplicate userdata `PARTNAME`, stable-identity drift, or same-session node
mismatch fails closed.

This capability never formats, repairs, replays, populates, copies, stages,
hashes as a whole, or otherwise writes userdata. Qualification and handoff
open the exact block node read-only, require an ext4 clean state with no
recovery-needed flag, mount only with `ro,noload,nosuid,nodev`, and prove the
mounted filesystem is read-only. Any disagreement or mount/cleanup ambiguity
stops before handoff. The Debian namespace receives a private minimal `/dev`
with no userdata block node, the reviewed writable tmpfs set, and only the
reviewed evidence and Wi-Fi handoff binds. A failed pre-exec path must either
restore every moved mount and unmount userdata or retain control in an explicit
recovery-required state; it never retries switch-root.

H14 is a consumed incident candidate and is never replayed. Its exact boot
write and readback succeeded, but native preparation synchronously waited 20
seconds for the persistent Wi-Fi ready publication before consulting the
unarmed handoff state. That publication had not arrived, so H14 returned
`-ETIMEDOUT` before any UFS mount and closed only after the exact V2321 rollback
was written, read back, and proved healthy. H15 replaced that timing defect.
On an unarmed or latched boot it consults the durable handoff state before
starting Wi-Fi or NCM preparation and stays native. On an armed boot it requires
the private-mount/shared-network Wi-Fi companion process to be alive, but does
not make its eventual readiness publication a pre-switch-root timing gate. The
companion continues asynchronously across switch-root through the reviewed
read-only handoff bind. This changes no final PASS requirement: same-intent
Wi-Fi readiness and health remain mandatory, and absent or failed Wi-Fi proof
closes only as no-proof/refuted while exact resident recovery is established.

Its F1 transaction transfers only one exact boot candidate and, when needed,
the exact V2321 boot rollback. It has no rootfs payload, SD source, work copy,
stage, publish, copy, cleanup, or rootfs SHA pass. Before either transfer, a
fresh attended approval binds the current common-contract authority mode,
exact target, candidate, rollback, recovery evidence, action limits, manifest,
and complete execution closure. Its token is durably consumed before candidate
intent. The later D1 ordinal likewise consumes one fresh attended approval
bound to the installed current capability terminal, exact target/recovery, one
combined arm-plus-reboot action, transaction directory, expiry, and execution closure.
Capability qualification is not either run approval. The flash process group
waits behind a one-byte release gate; its exact launch is
durable before release, and rollback is forbidden until that group and every
descendant are proved quiescent. An intent without a launch proves no release;
a launch without a result is reconciled only from its bound log and
process-group evidence. A session/write marker or uncertain transfer count
always parks for the exact bound rollback; current running health never proves
the on-disk boot bytes unchanged. A rollback intent without a launch resumes
only that same bound rollback. An uncertain released rollback is never replayed
or closed from running baseline health; it remains explicitly recovery-pending.
Every intent, launch, result, and health publication crash boundary has a
no-candidate-replay continuation or an explicit recovery park. F1 success
requires the new resident healthy and its fresh
versioned enable/latch paths absent; candidate replay is forbidden. A later
attended D1 ordinal durably records one intent and dispatches one combined
native arm-plus-reboot command. If the reboot syscall returns, native code
cancels only that exact enable intent and fsyncs the cache directory. Exact
`0,0` state closes as no persistent effect only with the same-intent post-fsync
cancellation log; an intent-only host prefix otherwise preserves the dispatch
count as unknown and does not close. Exact `1,1` may finalize the native return
only after the benchmark and native failure log prove either successful handoff
or clean restoration with userdata unmounted. Any `recovery_required=1`, dirty
mount restoration, or retained root parks recovery rather than claiming healthy
closure. Exact `1,0` also parks recovery without replay. The successful lane proves the
same-intent UFS root/PID1/display/SSH/NCM/Wi-Fi evidence and returns once to
exact resident health. It never replays an uncertain arm, reboot, or handoff.

H15 run01 then exposed the new `UFS_DEVT_CROSS_BOOT_DRIFT` incident. Its arm-time
qualification passed at `sda33` `259:17`, but the armed boot resolved the same
stable userdata identity as `259:36`. H15 compared the stale compiled numeric
tuple before runtime resolution and returned `-EPERM` before latch or UFS
mount. H15 arm/reboot/handoff is consumed and never replayed. H16 is the only
replacement lane and implements the V2 same-session runtime-`dev_t` rule above
with fresh versioned enable/latch paths. Its exact V2321 boot rollback remains
mandatory.

H16 run01 exposed the separate
`PERSISTENT_DEBIAN_RETURN_AND_OBSERVER_BINDING_MISMATCH` incident. The exact
armed boot reached the read-only UFS `switch_root` marker and a live A90 NCM
endpoint, but the appliance intentionally has no automatic-return timer and
its installed root authorized key did not match the manifest observer key.
The original observer therefore could not prove authenticated SSH, PID 1,
DRM, display ownership, or the final Wi-Fi state, and the operator returned the
device physically. Neither that return nor later exact resident health may be
reported as an automatic return or as full personal-server PASS.

One incident-specific attended no-replay finalizer may close only that exact
H16 run01 journal. It accepts the immutable four-record prefix after the one
arm-plus-reboot dispatch, the released host guard, the exact predecessor
manifest/install/closure hashes, and a separately reviewed finalizer closure.
It sends only bounded read-only resident commands. Before appending the two
terminal host records it requires exact H16 identity and self-test, exact
`binding=1 enable=1 latch=1`, a same-intent unique H16 UFS handoff benchmark
ending at `switch_root_exec`, and a fresh read-only proof that userdata is not
mounted after the operator-confirmed physical return. Its terminal must keep
automatic return, authenticated SSH, PID 1, DRM/display, final Wi-Fi, and full
server readiness false or unproved. It never arms, reboots, mounts, hands off,
transfers a payload, flashes, writes userdata, or replays the consumed action.
Because the finalizer has no device effect, it needs attendance and independent
incident qualification but no new live-effect approval. It retires after the
exact journal has both terminal records, on target or source drift, or on any
new incident, whichever comes first.

The replacement capability `A90_H17_PERSISTENT_UFS_SERVER_V1` addresses only
the H16 observer-key mismatch and persistent-display gap. It starts from exact
H16 `RESIDENT_HEALTHY`, retains the H16 dynamic same-session userdata identity,
and changes only one boot candidate. The builder accepts one exact private
Ed25519 public key, validates its canonical structure, and places it at the
fixed boot-ramdisk path `/a90/h17/authorized_keys`. The key bytes, host path,
and private key never enter a tracked manifest, log, report, or repository
artifact; the private build receipt and later F1 manifest bind their SHA256
identities. No file other than the boot-only candidate is a device payload.

During the read-only UFS handoff, native-init first validates the unchanged H14
public content manifest and the existing private-key file structure. It then
mounts a fixed `nosuid,nodev,noexec` tmpfs over `/root/.ssh`, copies only the
boot-bound public key to mode-`0600` `authorized_keys`, and read-only
bind-mounts the reviewed H17 firstboot script over `/etc/a90-d3-firstboot`. It
also creates the
fixed shared HUD run tmpfs, starts one native HUD child, requires that child to
open DRM and present a bootstrap frame before the mount move, and binds the
shared run directory into Debian. The firstboot overlay preserves only the PID
recorded by that HUD service after rechecking its `/init` executable and DRM
file descriptor, publishes one bounded intent, and confirms that the same
process remains alive with a DRM file descriptor. Every overlay is
inside the mounted UFS tree or comes from the boot ramdisk; none changes UFS
bytes. Any pre-exec failure stops the HUD, unbinds firstboot and shared run,
unmounts the auth tmpfs, restores moved core mounts, unmounts userdata, and
returns native without retry. Ambiguous cleanup parks recovery.

H17 installation is an ordinary attended F1 boot-only transaction with the
exact V2321 rollback and fresh approval required by the retired-trial policy.
After exact H17 resident health is durable, its one persistent-server handoff
is a separately approved attended D1 ordinal. Automatic native return is
intentionally disabled and must not be required, inferred, or reported. The
bounded key-only USB-NCM observer proves Debian `/usr/sbin/init` as PID 1, an
ext4 read-only root, the tmpfs auth overlay, exact Dropbear listener ownership,
the native HUD PID and DRM FD with successful intent presentation, operator
visible confirmation, and final Wi-Fi carrier/readiness. It sends no payload
and performs no reboot, mount, service control, file write, or network tunnel
action.

The experiment terminal `PASS_A90_H17_PERSISTENT_SERVER_LIVE` means only that
the attended persistent Debian server is live and proved. Its device-safety
state remains `HEALTH_PENDING_PERSISTENT_DEBIAN`; it is not
`RESIDENT_HEALTHY`, grants no next D1 or F1 effect, does not close the ordinal,
and does not disarm recovery. While it remains live, permit only passive
bounded observation or the predeclared attended physical return/recovery.
Closure requires a later exact native resident-health terminal after that
physical return, without replaying the handoff. Public tunnels remain disabled.
The capability never applies to S22+, another A90 or userdata identity, a
writable UFS mount, an unattended D1/F1 action, or a non-boot partition. Its
independent qualification is reusable only while the execution-critical
closure and these hazard assumptions are unchanged and no new incident occurs.

H17 D1 run01 exposed the separate
`H17_POST_ROOT_MOUNT_NATIVE_FALLBACK` incident. The one arm-plus-reboot action
is consumed and is never replayed. The armed boot durably created the matching
latch, released native display ownership, revalidated the same userdata
identity, mounted the exact UFS appliance read-only, and then returned native
before `writable_set_ready`. Its retained log records
`cleanup_clean=1 root_mounted=0 recovery_required=0 userdata_unchanged=1
userdata_write=0`, followed by `handoff_failed_native`,
`auto_handoff_returned_native`, and `native_fallback_ready`. This proves a
failed attempted handoff with clean native restoration; it does not prove
Debian PID 1, authenticated SSH, persistent HUD, display, Wi-Fi, or successful
`switch_root`. The generic visible `E1` is only the outer `EPERM` and does not
identify the inner post-root-mount stop point.

One incident-specific attended no-replay finalizer may close only that exact
H17 run01 five-record journal. It binds the immutable consumed prefix, exact
manifest/install/predecessor closure, exact private read-only diagnosis, and a
separately reviewed finalizer closure. After one fresh exact read-only approval
it may send only the bounded commands needed to prove exact H17 health,
`binding=1 enable=1 latch=1`, same-intent enable/latch/evidence bytes, the
unique failed-handoff benchmark and clean-restoration markers, and the sole
runtime-resolved userdata identity unmounted. It appends only `final-health`
and `closed` host records. It never arms, reboots, hands off, mounts, starts or
stops a service, transfers a payload, flashes, writes userdata, clears the
latch, or asserts an operator physical return. Its terminal keeps persistent
server, Debian PID 1, authenticated SSH, persistent HUD, display, and final
Wi-Fi false or unproved while establishing exact native `RESIDENT_HEALTHY`.
The terminal is
`REFUTED_H17_PERSISTENT_SERVER_NATIVE_FALLBACK_HEALTHY`: the persistent-server
claim is refuted by the unique same-intent failed-handoff segment, while the
separate device-health result is exact native health. The finalizer is a new
incident adapter and never modifies or recomputes the consumed H17 D1 runner's
predecessor execution closure. It binds the five predecessor journal files by
byte hash. If `final-health` is durable but `closed` is absent, a later
host-only resume may append only the identical `closed` record without another
device read or approval; every other incomplete state remains open.

The first finalizer read exposed
`H17_TCPCTL_NORMAL_IDLE_EXIT_HEALTH_OBSERVER`: exact H17, self-test, PID 1
guard, native HUD, serial control, and NCM remained ready, while tcpctl had
exceeded its compiled 3600-second idle interval, exited with status zero, and
was reaped without restart. A replacement independently reviewed finalizer may
accept this as exact native resident safety only when the latest H17 boot
segment contains one same-PID spawn and authenticated-listener start, a later
zero-status reap and exit at least 3600 seconds after start, and no later
tcpctl start; current status must simultaneously prove serial and NCM ready,
tcpctl `starting` with no port, and NCM as the upload and preferred control
path. The alternative remains exact current tcpctl `ready`. The terminal
must state whether tcpctl is running and may not turn a normal idle exit into
persistent TCP-control or server-readiness proof. This is read-only observer
interpretation only: it grants no service start, stop, restart, reboot,
handoff, mount, state write, payload, flash, or userdata write. The old
qualification is retired by this new incident; fresh independent review and a
fresh exact read-only approval are required. The replacement uses distinct
incident-specific review, qualification, approval-file, and token namespaces;
it validates the new review's internal scope, closure, verdict, findings, and
no-contact disposition instead of trusting only a report-file hash.

It retires after the exact journal closes, on target/source/evidence drift, or
on any new incident, whichever comes first.

The H15 run01 pre-latch incident activates one attended recovery primitive for
the exact `1,0` state only. It binds the consumed D1 journal prefix, its exact
intent, current H15 identity and health, the sole H15 enable path, and the
byte-exact regular mode-0600 enable record. Before deletion it preserves those
small bytes under `workspace/private/`. After a fresh exact approval and a
durable unlink intent, it may dispatch one fixed unlink-and-sync command for
that enable path only. It sends no payload, does not reboot, hand off, flash,
mount userdata, remove the latch path, or touch another file. A lost or
uncertain response is never replayed; read-only reconciliation may close only
on exact `binding=1 enable=0 latch=0`, exact H15 health, and the bound preserved
bytes. Any other state remains recovery-pending. This primitive retires after
its first exact PASS, on closure or target drift, or on another incident,
whichever comes first. Independent qualification and a fresh attended approval
are mandatory and grant no authority to another target or action.

The capability never
applies to S22+, another A90, another userdata identity, a writable UFS mount,
or any non-boot partition transfer. Its independent `PASS_GO` is reusable
across ordinals, manifests, and campaigns only while the named
execution-critical hashes and these hazard assumptions are unchanged and no
new incident occurs.

H24 run01 exposed the separate `H24_PERSISTENT_HUD_BOOTSTRAP_EINVAL`
incident. The exact H24 resident install remains healthy, but its one D1 arm,
reboot, and handoff attempt are consumed and never replayed. The same-intent
record proves only the outer `persistent-hud rc=-22 errno=22` stop after the
read-only UFS root and writable set were mounted; it does not prove which
private-root syscall failed. Clean restoration, zero userdata writes, and the
terminal native `RESIDENT_HEALTHY` are separate facts. H24 qualification and
live authority are retired by this new incident.

H25 `0.11.193` was a host-only attempted successor and is
`NO_GO_RETIRED`. Review proved that its `chroot` design retained the old mount
graph as a namespace capability and that its HUD boot self-test was replayable,
could mutate or leave parent mount state, and did not fail closed across every
reap, parser, and receipt boundary. H25 never gained qualification, runner,
approval, connected D0, transfer, reboot, or handoff authority. Its identity,
state paths, artifacts, and evidence are never reused or reinterpreted.

Only a fresh successor identity may replace H24. Before allocating that
identity, the Wi-Fi ownership boundary must be selected. H24's persistent
native Wi-Fi companion uses a private mount namespace but remains in the PID
namespace whose procfs is moved into Debian. That is not proof of isolation: a
surviving process may expose its retained old root, file descriptors, or mount
namespace through `/proc/<pid>`. No headless successor may inherit this process
model while claiming minimal Debian exposure.

The preferred selection is one separately qualified, attended, no-payload D1
Wi-Fi ownership test. It may bring up Wi-Fi, durably record one stop intent,
stop and reap the exact native Wi-Fi helper group once, and observe bounded
redacted `wlan0` state. It must not arm handoff, mount UFS, reboot, transfer a
candidate, or claim Debian health. Its only terminals are
`TRANSFER_FEASIBLE`, `TRANSFER_REFUTED`, or `NO_PROOF`; an uncertain stop is
never replayed. This paragraph defines the required capability shape, not
standing D1 authority. A fresh execution closure, independent review, exact
resident/recovery binding, and fresh attended approval remain mandatory.

`TRANSFER_FEASIBLE` permits a later fresh successor to require every native
Wi-Fi/Android companion gone before `switch_root` and give association, DHCP,
DNS, and final Wi-Fi health to Debian using a boot-private non-SD input.
`TRANSFER_REFUTED` or `NO_PROOF` grants no candidate authority. A nested PID
namespace with native supervisor is then a separate H0 architecture and hazard
review; `hidepid`, `chroot`, a private mount namespace, or path-name checks are
not implicit alternatives.

After that decision, a successor may define a headless persistent-server lane
that compile-disables the persistent native HUD and firstboot overlay. Such a
lane must retain the exact read-only UFS, boot-private authentication, minimal
Debian `/dev`, mandatory devpts, final Wi-Fi, one-shot/no-replay, rollback,
cleanup, recovery, and resident-health boundaries.
Its persistent result may prove Debian PID 1, authenticated SSH, exact minimal
Debian `/dev`, final Wi-Fi, and persistent service health while explicitly
making no display or HUD claim. While Debian remains live, device safety stays
`HEALTH_PENDING_PERSISTENT_DEBIAN`; only an attended return or recovery and
exact native checks may close `RESIDENT_HEALTHY`. It must not inherit a
HUD-enabled result predicate.

Display is a separate optional capability after headless server health is
established, preferably with Debian as owner. Any future persistent native HUD
or boot-time HUD self-test requires a fresh hazard design and independent
review; it may not reuse the H25 `chroot` or replayable-self-test design. Every
successor F1 and D1 remains separately approved, attended, one-shot, and
no-replay under the ordinary live gates.

The one-use attended D1 sub-capability
`A90_ATTENDED_H5_H4_SOURCE_RECLAIM_V1` addresses only the bounded hazard
`SD_CAPACITY_EXHAUSTION_BLOCKING_FRESH_SOURCE_AND_WORK_COPY`. It may unlink
only the exact host-preserved H4 run-11 keyed source after its closed incident
has performed one non-replayed candidate attempt, one exact V2321 rollback,
and exact final recovery. The installed H5 run-12 keyed source is one separate
exact protected identity and is never selectable. Both identities are fixed
by run ID, path, 2 GiB size, mode `0600`, single link, SHA256, filesystem
device/inode, successful absent-only staging evidence, and exact private
host-preserved bytes. The H5 run-13 resident install terminal and D1 run-09
terminal remain immutable no-replay evidence.

A fresh inventory no older than 15 minutes must bind the exact A90 and bridge
generation, exact H5 `0.11.173` resident health, exact H5 auto-handoff state
`binding=1 enable=1 latch=1`, selected and protected identities, absent work
and all known staging paths, and bounded filesystem capacity. The immutable
manifest must additionally bind the exact H4 incident, H5 publication,
resident-install and D1 terminal evidence, both private host-preserved byte
identities, the exact boot-only V2321 rollback, attended physical Download or
TWRP recovery, and the complete execution-critical source closure. Immediately
before durable intent, the runner revalidates that manifest closure and every
visible PID mount namespace, open file descriptor, loop backing file, and
current-root reference for the selected source. One capability-wide exclusive
receipt then consumes the capability across all run IDs and permits one
nonrecursive host-encoded unlink dispatch with no retransmission. A missing or
malformed response permits only journal-bound read-only reconciliation with a
fresh exact A90 bridge generation; it never resends unlink.

PASS requires the selected H4 source absent, the protected H5 source exact,
work absent, free-space gain consistent with one 2 GiB file, final exact H5
health, and the same latched auto-handoff state. A non-PASS terminal parks
without retry. Host preservation is evidence but grants no restore authority;
restoration is a separate reviewed transaction. The capability sends no
payload, flashes no partition, changes no configuration, credential, security
state, H5 state path, or H5 source, and never applies to S22+, userdata,
another removable device, path, or A90. It retires after its first exact PASS,
on any selected/protected identity or execution-critical closure change, on a
new hazard or incident, or at `2026-08-07T00:00:00Z`, whichever comes first.
Post-dispatch read-only reconciliation may continue after expiry.

The separately reviewed attended D1 sub-capability
`A90_ATTENDED_CACHE_TMP_RECLAIM_V1` may unlink only the fixed stale temporary
file `/cache/a90-runtime/pkg/.boot_linux_v3355_boot_write_e5_full.img.tmp.2899667.1782985070`
to recover enough block space for the installed H2 automatic-handoff marker.
It applies only from exact H2 `0.11.170` `RESIDENT_HEALTHY` with the exact
V2321 rollback and demonstrated physical TWRP/Download recovery, exact
`binding=1 enable=0 latch=0`, both H2 state paths absent, `/cache` at zero
available blocks with free inodes, and the selected object proved to be one
non-symlink regular single-link file with manifest-bound path, size, mode,
owner, device/inode, block count, and SHA256. The exact bytes must first be
preserved as a private host regular mode-`0600` file with the same size and
SHA256. Every visible PID mount namespace, loop backing file, and open file
descriptor must prove the selected path unused immediately before intent and
again inside the one fixed host-encoded unlink frame, which must remain below
the resident 3800-byte `cmdv1x` envelope.

One durable intent permits one nonrecursive unlink dispatch and no retransmit.
An uncertain response permits only read-only presence, free-space, exact H2
state, and resident-health reconciliation; absence may prove the one dispatch
completed but never authorizes another cleanup. PASS requires the selected
path absent, positive `/cache` available blocks, both H2 state paths still
absent, exact unarmed H2 status, and final `RESIDENT_HEALTHY`. The preserved
host bytes are recovery evidence but do not grant an automatic restore; any
restore is a separate reviewed attended transaction. This capability cannot
select another cache object, directory, symlink, boot image, current log,
configuration, credential, security state, recovery artifact, userdata, or
partition, and never applies to S22+, another A90, or an unattended operator.

The one-use attended D1 sub-capability
`A90_ATTENDED_H5_HISTORICAL_IMAGE_GC_V1` addresses only the bounded hazard
`SD_CAPACITY_EXHAUSTION_FROM_SUPERSEDED_EXPERIMENT_IMAGES`. It may unlink the
fixed set of twenty obsolete files under `/mnt/sdext/a90/runtime`: twelve
superseded V3406 rootfs images, five older rootfs or clean-image copies, and
three WSTA 1.5 GiB snapshots. The installed H5 run-12 source is a separate
exact protected identity and is never selectable. A fresh inventory binds
every selected and protected object by fixed allowlisted path, expected size
and mode, single link, filesystem device/inode, allocated blocks, and SHA256;
the protected source SHA256 must remain the installed H5 binding. Every
selected byte identity must have an exact private mode-`0600` host-preserved
regular recovery copy with the same size and SHA256. Existing absent-only
publication bytes cover the twelve V3406 images; the eight legacy or snapshot
objects require a fresh bounded device-to-host read-only preservation receipt
before a cleanup manifest may be built.

The immutable manifest binds exact H5 `0.11.173` resident health and
`binding=1 enable=1 latch=1`, the closed H5 resident/D1 evidence, exact V2321
boot-only rollback and attended Download or TWRP recovery, exact target and
bridge generation, bounded filesystem capacity, absent work/staging paths,
and the complete execution-critical source closure. Immediately before durable
intent, the runner rechecks every selected metadata identity, rehashes the
protected H5 source, proves every selected inode absent from visible mount
namespaces, open file descriptors, loop backing files, and current roots, then
rechecks target, closure, health, rollback, and inventory age.

One capability-wide durable receipt permits one nonrecursive unlink dispatch
for the entire fixed set with no retransmission. A missing or malformed
response permits only journal-bound read-only reconciliation and H5 health
observation; it never resends cleanup. PASS requires all twenty selected paths
absent, the protected H5 source exact, work and staging absent, bounded free
space gain consistent with the selected allocated blocks, and final exact H5
health with the same latched auto-handoff state. Host preservation is recovery
evidence but grants no automatic restore; any restoration is a separate
reviewed attended no-clobber transaction. Cleanup sends no payload and flashes
no partition, changes no H5 state, configuration, credential, security state,
recovery artifact, userdata, or other path, and never applies to S22+, another
removable device, or another A90. It retires after its first durable dispatch, on selected/protected or
execution-critical closure drift, on a new incident or hazard, or at
`2026-08-08T00:00:00Z`, whichever comes first. Post-dispatch read-only
reconciliation may continue after retirement.

The separately reviewed attended recovery sub-capability
`A90_ATTENDED_RETAINED_WORK_SOURCE_DISTINCT_CLEANUP_V2` may unlink only the
fixed `/mnt/sdext/a90/runtime/d3-handoff-work.img` after a closed ordinary F1
has restored exact V2321 health but left that work copy behind. It requires the
closed run's one candidate, one rollback, no-replay, and final-health evidence;
fresh exact V2321 D0; the exact 2 GiB work bytes preserved on the host; the
adjacent run-specific source as a distinct exact regular mode-`0600` file with
its separately bound SHA256; an absent run stage; no mount or loop use; and
attended physical recovery. The source and work hashes may differ because the
Debian session writes only the work copy; equality is neither inferred nor
required. Live dispatch requires the awake operator to assert
`--operator-attended` while physically able to enter Download or TWRP; never
assert it while absent or asleep. The adjacent source is protected and never
selected for unlink.
One durable intent permits one nonrecursive unlink dispatch for the fixed work
path, with no retransmit after an uncertain response. Every cleanup control
frame is host-encoded and statically bounded to at most 3800 bytes; an
oversized frame fails before durable intent or dispatch. Reconciliation is
read-only. PASS requires work absent, the protected source still exact, stage
absent, and final exact V2321 health. It sends no payload, writes no partition,
configuration, credential, or security state, and grants no arbitrary path or
shell authority. It does not extend rootfs GC selection and never applies to
S22+, userdata, another removable device, another A90, or an unreviewed
identity.

The separately reviewed attended F1 incident-recovery sub-capability
`A90_ATTENDED_RESIDENT_INSTALL_EXISTING_SOURCE_WORK_PRESERVED_V1` may install
one exact boot-only resident candidate from exact V2321 health without
replaying a failed cleanup. It applies only after an ordinary F1 has closed on
one candidate, one rollback, no replay, and exact final V2321 health, and after
the retained-work cleanup journal has closed on one non-retransmitted uncertain
dispatch with work still reported present, the distinct source reported exact,
and the run stage reported absent. That cleanup terminal proves the dispatch was
not repeated; it does not prove decoder-level no-effect. A subsequent fresh
connected D0 is the sole current-state authority and must prove the exact work
and source bytes presently exist before the immutable manifest binds the
predecessor and cleanup journals, candidate and rollback,
source and work paths, sizes, modes, link counts, SHA256 values, distinct
device/inode identities, host-preserved bytes, exact target/current realpath,
physical recovery, execution closure, and fresh capability review.

This lane sends no rootfs payload and never invokes staging, copy, unlink,
mount, cleanup, or handoff. It verifies source, work, stage, every visible PID
mount namespace through `/proc/[0-9]*/mountinfo`, loop backing, open file, and
current-root state through eight separately bounded read-only frames before
candidate intent and after candidate health. One durable candidate intent
permits one boot transfer; candidate replay remains forbidden and any
post-intent ambiguity permits only the exact bound V2321 rollback. Success is
the distinct terminal `PASS_A90_RESIDENT_INSTALLED_WORK_RETAINED` with exact
resident health, unchanged protected bytes, zero staging/copy/cleanup counts,
and `handoff_eligible=false`. It is not a resident D1 baseline and grants no
switch_root authority. Rollback closure likewise requires exact V2321 health
and unchanged protected bytes. It never applies to S22+, a non-boot partition,
another source/work identity, another A90, or an unattended operator.

The separately reviewed capability
`A90_RESIDENT_PRESERVED_WORK_CLEANUP_AND_D1_BASELINE_V1` may convert that one
exact successful preserved-install terminal into a D1 baseline, but only in
this order: fresh connected D0 proves the installed resident healthy and the
bound source/work files exact, distinct, and unused; one attended durable
intent authorizes one unlink dispatch for the fixed work path; passive
reconciliation proves the work absent, source exact, and installed resident
healthy; then a second connected D0 repeats the absent-work, exact-source, and
resident-health proof.  The unlink is never retransmitted, even when its
response is missing or malformed.  A non-PASS cleanup result or missing
post-cleanup D0 cannot be reduced into a baseline.

The reducer is host-only and may run once for that cleanup terminal.  Its
immutable output binds the preserved-install manifest, result, canonical
journal, cleanup manifest/result, post-cleanup D0, exact boot rollback,
resident identity, source bytes, observer key, target, recovery path, reviewed
execution closure, and the fixed absent work path.  The original
`PASS_A90_RESIDENT_INSTALLED_WORK_RETAINED` terminal remains directly
ineligible for D1.  Only the exact reduced baseline may feed the attended D1
manifest builder, which must still perform a fresh opening D0 before any
handoff and must clean up the newly created work copy after native return.

## A90 F1 Resident Install

A90 F1 uses the checked `native_init_flash.py` path and may transfer only the
exact boot candidate or its exact V2321 rollback. TWRP/Download is a
preflight-proven recovery environment, not permission to write the recovery
partition or any non-boot partition.

Before any F1 effect, prove the exact healthy A90 starting state, exact candidate
and rollback regular files and SHA256 values, boot-only membership, exact
rootfs input and work-copy disposition when applicable, an empty durable
journal, checked flash/bridge closures, and physical recovery availability.

Trial policy needs no per-candidate approval, but the existing v1 runner still
requires one fresh `A90_F1_RESIDENT_INSTALL_V1` binding for one candidate plus
its exact rollback. Candidate replay is forbidden: the runner must never retry
the candidate. Once candidate execution begins, rollback never waits.

After the candidate transfer:

- candidate transfer ambiguity, wrong identity, explicit initial-health
  failure, inability to establish initial control, or lost recovery requires
  exact rollback;
- initial resident health requires exact candidate version/build, the bound
  native self-test/health predicates, a working bounded control response, and
  preserved physical recovery; and
- once `RESIDENT_HEALTHY` is durably recorded, a later Debian experiment
  refutation or observer-only no-proof does not retroactively fail installation
  and does not require rollback.

A successful install terminal is `PASS_A90_RESIDENT_INSTALLED`. A failed or
ambiguous install uses one exact rollback and closes only after V2321 health is
verified. A rollback failure is `RECOVERY_REQUIRED`. The existing v1 runner's
first use of this terminal requires its schema update, focused tests, review,
connected preflight, and compatibility binding; this document alone creates no
active campaign.

## Attended F1 Pre-Handoff

The existing reviewed attended pre-handoff exception remains narrow. It may
retry only a positively proven channel-input failure before any handoff intent,
inside the predeclared deadline and attempt budget. The runner must durably
record handoff intent before dispatch. After that point, it never retries the
handoff or candidate. This F1 exception is separate from the post-install D1
resident session.

## Evidence and Reporting

- Routine D0 needs only the bounded read result.
- Routine D1 uses one session record plus compact ordered action entries; it
  does not require one policy, manifest graph, prose report, or review ladder
  per action.
- A resident-install terminal may be reduced once to one immutable resident
  baseline binding. Routine D1 preparation derives its canonical journal from
  that resident manifest; the operator must not select a second independent
  journal path.
- F1 uses one structured result, one append-only journal, private raw logs, and
  a compact target-specific timeline. Record exact candidate/rollback transfer
  counts and no-replay status.
- A parser or reporting failure after a proven transition never repeats that
  transition.
- Write prose only for a policy change, new capability/hazard, incident,
  recovery deviation, or genuinely ambiguous device-safety result.

## Review and Change Control

- Changes to this binding target contract require one independent safety review.
- Review must confirm common boot-only, forbidden-action, exact rollback,
  no-replay, isolation, physical-recovery, and private-evidence rules remain
  intact.
- Review machinery only when device-effect, transfer, recovery, schema, or
  hazard closure changes. Parser-only H0 repairs need tests, not a review ladder.
- A90 `PASS_GO` qualifies a capability across ordinals, manifests, qualifications, and campaigns;
  re-review only after a critical hash change or new hazard/incident.
- Keep current candidate hashes, consumed approvals, run IDs, and experimental
  frontier in `GOAL_A90.md` or private evidence, not in this stable contract.
