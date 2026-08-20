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

## A90 Validation Discipline

This section binds how A90 claims about this repository and about device
evidence are established. It grants no device authority and changes no tier.
It exists because the dominant recorded cause of A90 ordinal loss is host-side
observation defect, not device failure, and because every such defect entered
the record as a confident claim.

### Tree state is re-derived, never inherited

A conversation summary, prior report, memory note, or earlier turn is a
hypothesis about the tree, never evidence about it. Before asserting what an
A90 file contains, or that a named defect is live:

1. Establish the working HEAD with `git log --oneline -3`.
2. Establish that file's own history with `git log --oneline -5 -- <path>`.
   An empty `git diff HEAD` proves the worktree matches HEAD; it does not
   prove HEAD is the generation being reasoned about.
3. Re-read the current bytes and quote that fresh output, with line numbers,
   inside the claim.
4. Read the consumer, not only the declaration. An emitted marker, constant,
   or manifest string is a claim about intent; only its reader proves behavior.

Establish the current generation before reasoning about design: `GOAL_A90.md`
`## Exact Current State`, the builder `versions/` listing, and
`git log -- GOAL_A90.md`. A line-number citation whose source was not
re-derived is not a finding, and a defect list carried forward from an earlier
generation is not a work item until step 3 passes.

### Instrument failure and device failure are separate terminals

Classify every failed proof by what actually failed before assigning a verdict.

| Failure | Terminal | Ordinal effect |
|---|---|---|
| Device reported state contradicting health | `REFUTED` | Consumed; never replayed |
| Host could not reach, parse, or decide | `NO_PROOF_OBSERVER` | Freezes new device effects; does not close the campaign |

Only device-attributable evidence may burn an ordinal or force a no-replay
conclusion. A missing, late, or malformed observation enters health
classification and stops that host invocation; passive reads, host-only
observer repair, and the exact predeclared recovery may continue.
If an observer defect and a device-attributable contradiction coexist, the
device contradiction wins; the observer defect must not downgrade it to
`NO_PROOF_OBSERVER`. When attribution remains unresolved,
`NO_PROOF_OBSERVER` freezes every new non-recovery device effect and never
permits candidate replay; only passive reads, H0 observer repair, or the exact
journal-bound recovery allowed by the higher-precedence contract may continue
until exact resident health or the recovery terminal is established.

Observation is not attribution. A responding port, a written marker, a visible
screen, or an exposed endpoint proves only that the observation occurred. The
process, root, namespace, and identity that produced it must be bound
separately by same-intent evidence. A marker emitted before the effect it names
— including a stage marker logged ahead of its own syscall — is not proof that
the effect occurred.

`unproved` is never promoted to either `PROVED` or `REFUTED`. Absence of
evidence for a capability is not evidence that the capability failed, and
absence of evidence for a failure is not evidence of success. State the scope
actually searched inside the claim.

### Validator changes follow a fixed taxonomy

A failing validator is repaired by class, never by loosening whatever rejected.

| Class | Symptom | Required repair |
|---|---|---|
| Shape | Rejects a cosmetic form the device never promised | Relax. Permissive about shape. |
| Substance | Accepts a record carrying no health assertion | Tighten. Strict about state. |
| Drift | Producer changed, paired consumer did not | Replace both with one generated source; do not hand-maintain two encodings of one fact |
| Binding | An exact per-generation identity no longer matches | Extend to the new generation exactly; never widen, alias, or make optional |
| Budget | A declared bound aborts a healthy run | Re-derive from measurement or from the bounded implementation; a policy allowance is not an upper bound |

`Shape` is inapplicable to any field whose equality, presence or absence,
hash, version/build, target, ordinal, process/namespace identity, or health
value is part of a binding or predicate. A formatting difference affecting
one of those fields is `Binding` or `Substance`, not a reason to relax.

Every validator assertion carries adversarial fixtures: one record that must
pass, and one that must fail for the stated reason. A validator whose only
tests are happy-path is not qualified. Where a producer and a consumer encode
the same fact, they are bound in one reviewed artifact and the built binary is
checked against the pinned strings.

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

The installed H24 shell is not a D0 reader: PID 1 invokes its generic orphan
reaper before the prompt and after every dispatched command. Until a fresh
resident provides an independently qualified non-mutating reader, H24 D0 is
limited to passive host/transport observation that sends no shell command. Any
required live H24 command must be represented by a separately reviewed D1/F1
action and its exact authority; harmless-looking output does not lower its
tier.

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

The H24 shell-based W0 path is retired before qualification or live use. Its
`cat`/`run` commands trigger generic PID-1 reaping, so inventory was not D0;
separate inventory/stop frames also left a capability-set race before
`SIGTERM`. No W0 qualification, D0, approval, intent, signal, terminal, or
recovery exists to resume, and the removed host runner/tests are not evidence.

The non-permanent `A90_WIFI_OWNERSHIP_ATOMICITY_GATE_V1` addresses
`H24_COMMAND_BOUNDARY_REAPER_EFFECT` and
`WIFI_HELPER_SPLIT_INVENTORY_STOP_TOCTOU`. It blocks every ownership path
without a different independently reviewed replacement. The attempted atomic
diagnostic is `NO_GO_RETIRED`: reproducing H24's distinct post-fork Android
UID/GID/capability roles under its accumulated filter/broker contract required
more permanent security machinery than the production handoff. It never gained
identity, qualification, D0/D1/F1, signal, reboot, or recovery authority.

The selected H0 direction is
`docs/plans/A90_HEADLESS_NATIVE_WIFI_ISOLATED_DEBIAN_DESIGN_2026-08-14.md`.
It performs no ownership-stop experiment. Native PID 1 remains a minimal
headless safety supervisor with the exact native Wi-Fi owner. One direct child
becomes Debian PID 1 in fresh PID, mount, IPC, UTS, and network namespaces, mounts one
matching procfs, constructs the exact consoleless `/dev` described below,
privately validates and pivots to
the read-only UFS root, detaches the complete old root, drops bootstrap/network
capabilities, and execs Debian init. `chroot`, shared procfs, shared network
namespace, and path-name hiding are not substitutes.

The successor Debian `/dev` is a bounded fresh tmpfs containing only manifest-
fixed `/dev/null` (1:3, 0666), `zero` (1:5, 0666), `full` (1:7, 0666), and
read-only-mode `urandom` (1:9, 0444). `/dev/random`, `/dev/console` (5:1),
`ttyGS0`, generic `tty`, `ptmx`, `pts`, `shm`, every physical/native character
node, every block node, every submount, and native devtmpfs are forbidden. No
devpts is mounted and no PTY allocation is a product function. The minimal
rootfs is consoleless, Dropbear rejects PTY requests, the attended proof uses
non-PTY SSH, the child has no controlling tty and proves `tty_nr=0`, and fd
0/1/2 share one verified open description for its private `/dev/null`. Before
exec the complete `/dev` tmpfs is remounted read-only and its exact four-node
tree, rdevs, modes, ownership, link counts, byte/inode bounds, and absence of
submounts are reread. An extra node, writable root `/dev`, devpts, or PTY is
`NO_GO`. DAC-override/read-search, fowner, and mknod capabilities are absent,
so node metadata and the read-only urandom mode cannot be bypassed.

The matching child procfs uses fixed `nosuid,nodev,noexec,hidepid=2`, shows
only the child PID/net/IPC/mount views and an exact finite read-only scalar
allowlist, proves its superblock differs from native procfs, and is finally
remounted read-only before exec. Trusted bootstrap
masks all of `/proc/sys`, `sysrq-trigger`, key listings, KASLR/kernel/module/
device/interrupt/I/O maps, and every non-allowlisted top-level entry with exact
immutable read-only empty masks. It rejects unknown entry/type drift, verifies
representative global and per-task writes including `oom_score_adj` fail, and
forbids later native module load/unload. A global proc scalar is allowed only as
a named read-only evidence value; no native task, root, FD, namespace, device,
or control endpoint is exposed. Writable proc or an unbounded global view is
`NO_GO`.

The native side retains `wlan0`; Debian receives only a bound veth peer and
closed default-drop forwarding/NAT policy. No native task, procfs, Binder,
property socket, abstract AF_UNIX namespace, Wi-Fi control socket, devtmpfs,
block/userdata/DRM node, old-root handle, or network-administration capability
is nameable from Debian. The Debian IPC namespace must also differ from native,
begin with empty SysV IPC state, inherit no `/dev/mqueue`, expose no `/dev/shm`,
and allow no SysV IPC or POSIX-mqueue/shared-memory creation. Because keyrings
are not IPC-namespace objects, trusted
bootstrap must reject any inherited thread/process keyring, replace the
inherited session with one proved-empty anonymous child session, preserve the
directly subscribed thread/process/session serial/link/count snapshot unchanged,
never resolve `KEY_SPEC_USER_KEYRING` or `KEY_SPEC_USER_SESSION_KEYRING`, never
call the get-or-create `KEYCTL_GET_PERSISTENT`, hide `/proc/keys` and `/proc/key-users`,
and install one reviewed inherited classic-seccomp isolation filter on every
supported ABI before exec. It denies `keyctl`, `add_key`, `request_key`,
`unshare`, `setns`, `mknod`, `mknodat`, all `clone3`, every legacy `clone` with
a namespace or unknown service flag, and the complete supported post-bootstrap
mount/root API family. It is static, inherited, and non-removable. The exact
consoleless PID-1/Dropbear/workload trace must prove both compatible finite
fork flags and no dependency on denied calls. Thus later user-namespace
creation cannot regain mount/device capability even when the kernel supports
unprivileged user namespaces. The UFS root is `nodev`; the exact private `/dev`
is the only non-`nodev` device filesystem, and node creation, new mounts, native
devtmpfs paths, and inherited device FDs are all absent. Any unsupported ABI,
unknown clone flag, filter gap, or service mismatch is `NO_GO`.

The filter also permits direct `socket()` only for exact traced AF_INET TCP
stream and UDP datagram forms. It denies `socket(AF_UNIX, ...)`; only an exact
internal AF_UNIX `socketpair()` form may be allowed because it creates no
pathname/abstract endpoint and both FDs remain child-local. Every unknown or
non-INET family/type/protocol is denied, including QRTR, netlink/kobject,
packet/raw, Bluetooth, NFC, VSOCK, CAN, XDP, and key/control families. Compat
`socketcall` is denied completely and the rootfs is exact AArch64-only. No
native/preexisting socket FD reaches the service identity. The sole
bootstrap-created listener remains only in the distinct filtered key daemon,
and the forced dispatcher receives only exact bounded channel ends. Positive
service traces and negatives for every prohibited family/ABI are mandatory.

The final execution envelope also uses an exact environment, empty
supplementary groups, and two non-aliasing manifest-fixed nonzero identities
unused by every native task and file. The service UID/GID owns PID 1, the only
login account, forced probe, and workload. A distinct non-login
SSH-key-daemon UID/GID owns only the Dropbear listener/session engines and the
private server-key tree.
default catchable-signal dispositions, empty signal mask, disabled alternate
stack, and fixed umask/cwd/rlimits. Missing namespace, veth, netfilter, pivot-root,
capability-drop, cleanup, or exact H24 Wi-Fi support is `NO_GO`; neither a
shared namespace nor a userspace proxy is an allowed fallback.
Trusted bootstrap installs the boot-private client public key only as one
mode-0600 `authorized_keys` owned by that service UID/GID under its
manifest-fixed home, final-remounts the bounded auth tmpfs read-only, and
proves the historical H24 `/root/.ssh` overlay absent. It creates the separate
host-key tree mode 0700 and private key mode 0400 owned only by the key-daemon
UID/GID. The two identities, groups, homes, files, and mounts may not alias. A
root-owned, service-readable, or mutable successor private-key/authorization
path is `NO_GO`.

Server-side client authentication is a separate mandatory boundary from the
Dropbear server-host-key receipt. The separately versioned rootfs manifest
must bind the exact Dropbear binary hash, source/configuration provenance,
feature matrix, argv, account database, fixed service username/UID/GID and
home, forced-command dispatcher, and canonical `authorized_keys` grammar. The
only login-eligible identity is that fixed nonzero service account and the only
accepted client credential is its one run-bound boot-private public key.
Password, empty-password, `none`, keyboard-interactive/PAM, root login,
alternate accounts, alternate homes or key sources, and duplicate names/IDs
must be structurally disabled and negatively tested. The distinct key-daemon
account, root, and every other retained system identity are locked and
non-login; the service account has no general shell.

The proved-clean bootstrap never reads private key bytes. It opens only the
exact key/public/account/dispatcher objects and forks one child that performs
an exact manifest-bound static key-daemon `execveat(AT_EMPTY_PATH)` before key
read, listener bind, or accept. The clean daemon closes every unneeded source/
path/directory FD, changes all IDs to the distinct key-daemon UID/GID, sets
itself permanently non-dumpable, uses keep-caps only during that trusted
transition, retains exactly `CAP_SETUID`/`CAP_SETGID`, clears keep-caps, locks
securebits, sets `no_new_privs`, installs its static filter, emits one fixed
`KEY_DAEMON_CLEAN_READY` on its sole transient internal status pipe only after
its own exact mapping check and before key load/listener bind. It may then load
and close the exact key FD and bind/listen while external ingress remains
blocked, emits exactly `KEY_DAEMON_LISTEN_READY`, and closes that status writer
to produce EOF before any `accept`. The proved-clean bootstrap validates both
frames and EOF and, as the sole native-receipt writer, forwards only their
canonical scalar summary. Native PID 1 must independently verify the summary,
exact pidfd/executable/ID/capability/filter/FD set and `maps`/
`map_files` provenance with no inherited native/shared/file/device/deleted/
memfd/unexpected mapping before the daemon may contribute to `LOCAL_PERSISTENT`;
this verification itself never opens ingress or permits an accepted connection.
A missing, reordered, or drifted proof parks with ingress closed. The
service identity cannot traverse the private tree or inspect the
daemon: child procfs has no hidepid bypass, and the inherited service filter
denies ptrace, process-vm, pidfd-getfd, process memory/FD duplication, dumpable
regain, and access to the daemon's proc mem/fd/maps/ns surfaces.

The daemon retains only `CAP_SETUID`/`CAP_SETGID` under a filter that permits
one authenticated child to call only the exact service-GID `setresgid` then
service-UID `setresuid` transition. Empty groups, no keep-caps, locked
securebits, one explicit exact zero-`capset`, ambient clear, complete capability
and ID reread, and denial of every alternate identity/capability/file/exec path
are mandatory; nonzero-to-nonzero setuid is never treated as an implicit cap
clear. Before the forced dispatcher,
no client-controlled code runs; all child-side private-key copies are
explicitly zeroed, every key/config/listener FD is absent or close-on-exec, and
one exact `execveat(AT_EMPTY_PATH)` of the prebound immutable dispatcher
replaces the address space. The dispatcher receives only bounded non-PTY
channel FDs. The listener/session parents remain non-dumpable key-daemon
processes and may use private material only for SSH signing/rekey. Missing
source proof, service-readable key bytes, retained key FD/buffer, proc access,
saved-ID/capability regain, second listener, or restart is `NO_GO`.

The exact server build/launch and independently validated one-line key options
must reject arbitrary commands and subsystems, PTY, local or remote forwarding,
agent forwarding, and X11 forwarding. One immutable bounded read-only
PID-1/workload probe dispatcher is the sole accepted session. Any option or
key restriction is authority only after its exact selected-version
source/help/parser semantics are bound; missing support is `NO_GO`, never a
permissive fallback. The attended host may connect only after the exact current
`INGRESS_OPEN` record and must use the one service username and
private counterpart with strict server-host-key checking, public-key-only
batch/identity-only behavior, no agent/PTY/forwarding, and the fixed probe. Its
receipt binds the negotiated public-key method, accepted client-key
fingerprint, account, forced result, and target/resident/boot/run/cache
identity. A connection accepted through any other method, credential, account,
command, subsystem, or forwarding feature is a security failure.

Before release the parent must normalize and reread the blocked child to exact
manifest-fixed `SCHED_OTHER`, priority 0, `SCHED_RESET_ON_FORK`, a bounded
nice value of +10, a reviewed CPU-affinity/cpuset subset that preserves native
control CPUs, `IOPRIO_CLASS_BE` priority 7, and the selected current-kernel
uclamp state. No inherited FIFO/RR/DEADLINE parameters or Android scheduler
boost may remain. The envelope binds `RLIMIT_RTPRIO=0`, `RLIMIT_RTTIME=0`,
`RLIMIT_NICE=0`, and absence of `CAP_SYS_NICE` and
`CAP_SYS_RESOURCE`; the default-deny filter blocks later scheduler, affinity,
nice, ioprio, uclamp, and rlimit-raising changes. All descendants inherit the
same lower-priority state, and exact before/after evidence proves native PID 1
and Wi-Fi scheduling state unchanged.

The inherited all-ABI filter is a static default-deny policy. The separately
versioned rootfs manifest binds the complete positive syscall and argument
allowlist for the exact nonprivileged consoleless PID 1, non-PTY Dropbear, and
workload trace. Every unlisted syscall fails, and the named keyring,
namespace, mount, device, and socket denials above are mandatory assertions,
not an exhaustive blacklist. The positive policy also denies unneeded global
kernel-object allocators and controls including `perf_event_open`, `bpf`,
`userfaultfd`, io_uring and legacy AIO setup, inotify/fanotify setup, POSIX
mqueue and SysV IPC, module/kexec/syslog control, and all untraced multiplexed
ioctl/fcntl/prctl operations. `getrandom` permits only flags 0 or
`GRND_NONBLOCK`; `GRND_RANDOM` is denied and `/dev/random` is absent. Queued
real-time signal APIs and untraced signal sends are denied. Missing positive
trace coverage or an allowed unbounded object class is `NO_GO`.

Per-process rlimits are not aggregate containment. Before child release, the
still-blocked child must be the sole member of one nonce-bound, manifest-frozen
A90 cgroup layout that provides exact pids, memory plus swap (or proven no
swap), CPU quota/period, fresh-UFS-device I/O bounds, and the exact cpuset/
uclamp or equivalent controls required by the normalized `SCHED_OTHER` state
while reserving enough
global capacity for native PID 1, Wi-Fi, evidence, and recovery. H0/static
evidence selects and independently reviews exactly one v1 or v2 backend before
identity allocation. The later candidate unarmed F1 self-check only verifies
that manifest-frozen selection before D1; runtime selection/fallback or mixed
hierarchies are forbidden. Controller mount/ancestor/
group identities, limits, membership, counters, empty teardown, and unchanged
native/ancestor state are durable evidence. The cgroup filesystem and FDs are
never child-visible. Missing controller or reserve proof is `NO_GO`; uncertain
cleanup is `RECOVERY_PARKED`.

Cgroups do not close every global or per-UID kernel allocator. The manifest
therefore binds `RLIMIT_NOFILE`, `RLIMIT_SIGPENDING`, `RLIMIT_MSGQUEUE=0`,
`RLIMIT_MEMLOCK`, `RLIMIT_CORE=0`, stack and process limits, then proves that
`pids.max * RLIMIT_NOFILE`, all allowed socket/pipe/epoll/timer objects, both
dedicated UIDs' pipe pages, and their worst-case charged or
conservatively bounded kernel memory leave an exact native PID-1/Wi-Fi/
evidence/recovery reserve in the global file table and every relevant counter.
No devpts/ptmx exists, so no PTY ID is allocatable. Preflight reads but never
writes global limits; cleanup proves the child PID namespace empty, both
dedicated UIDs have no remaining charged object, and native/global counters stay
within their permitted monotonic deltas. An uncharged, unobservable, or
unbounded allowed object class is `NO_GO`; unreadable/overflowed cleanup
counters are `RECOVERY_PARKED`.

The clone/exec boundary uses three exact pidfd-controlled stop barriers. Before
durable handoff intent, the native cloning thread must already be ordinary
`SCHED_OTHER`/priority-0/nice-0 with no RT/RR/DEADLINE or Android boost; the
runner never mutates native state to satisfy that precondition. The new child
receives exactly two `pipe2(O_CLOEXEC)` scalar pipes and one manifest-bound
static bootstrap executable FD. Its inherited-mm branch may only close FDs,
temporarily clear `FD_CLOEXEC` on the two child pipe ends, and make one exact
`execveat(AT_EMPTY_PATH)` before any effect. The clean bootstrap immediately
re-arms both close-on-exec bits, closes every other FD, emits one no-effect
`CHILD_READY` frame, and blocks on the empty control pipe. The parent binds the
same pidfd, exact executable/fd/fdinfo and exact `/proc/<pid>/{maps,map_files}`
provenance: no inherited native anonymous secret, shared/file/device/deleted/
memfd mapping, unexpected executable, or writable-executable VMA may remain.
The parent revalidates the mapping/FD proof at every stop barrier, then sends a
pidfd `SIGSTOP` from the ancestor namespace and proves the stopped event before
installing resource and scheduler state. Native PID 1 never enters the child
network namespace: it moves only the peer with the bound netns FD and exact
`IFLA_NET_NS_FD`. The parent opens exactly one `O_RDONLY|O_CLOEXEC` child nsfs
FD, binds its number/flags/link target/`st_dev:st_ino`, proves no duplicate,
uses it in the sole move message, and closes it immediately after the exact
rtnetlink acknowledgement. Before native-end configuration or any continuation
it enumerates its own fd/fdinfo and proves no descriptor references that child
namespace inode. Every later namespace observation is path-based or uses one
scoped close-on-exec FD that is closed and followed by the same zero-reference
proof before a result is published. It then configures the native end and outer rules, and leaves the
child peer down and unaddressed. It durably publishes `NETWORK_PREP_INTENT`,
atomically writes the one-byte `N` (`NETWORK_PREPARE`) opcode, then sends one
pidfd `SIGCONT`. The trusted child may configure and reread only its own peer,
route, child-local sysctls and traffic-control handles, must send no packet,
then permanently drop `CAP_NET_ADMIN`, emit the unique `NETWORK_PREPARED`
receipt, and block on the empty pipe. The parent sends a second pidfd
`SIGSTOP`, proves that stop, receipt, native-side digests, and capability
absence plus the exact two-pipe FD set, unchanged clean mapping provenance,
and no retained netlink socket, then
durably publishes `ROOT_PREP_INTENT`. Only the one-byte `R`
(`ROOT_PREPARE`) opcode and second pidfd `SIGCONT` permit private root/key
preparation. The child emits the unique `ROOT_PREPARED` receipt and blocks
again before pivot, UID/filter transition, or exec. The parent sends a third
pidfd `SIGSTOP` and proves the stop, frame, scheduler, network, mount, file,
key, empty-pipe, exact two-pipe FD-set and clean-mapping digests. It durably publishes
`CHILD_RELEASE_INTENT`,
atomically writes one-byte `X` (`RELEASE`), then sends one final pidfd
`SIGCONT`. Exact successful results for all three token/signal dispatches
publish `CHILD_RELEASED` without enabling retry; a missing result is uncertain.
Only that final token/continuation permits pivot/exec. Pipe EOF, a PID-number
signal, early exec, wrong or missing token/stop/frame, extra dispatch, crash
ambiguity, child-network drift, retained `CAP_NET_ADMIN`, native `setns`, or
replay of any phase is `RECOVERY_PARKED`.

The fresh UTS namespace receives one fixed public hostname and empty domain;
native UTS values must remain unchanged. The first proof is IPv4-only. Native
PID 1 requires compatible preexisting `net.ipv4.ip_forward=1` and exact
all/default/wlan forwarding, `rp_filter`, `accept_redirects`, `send_redirects`,
and `proxy_arp` values before any network effect. It never writes those existing
native scalars. Only nonce-created veth and child-network-namespace fields may
be written and reread. IPv6 is disabled only inside the child network namespace;
native IPv6 is untouched. Cleanup removes the rules/veth and proves all native
preconditions unchanged. A mismatch is zero-effect `NO_GO`; source or runtime
evidence of an `ip_forward` or existing all/default/wlan write fails closed.

Cgroups do not account all softirq, skb/qdisc, conntrack, or Wi-Fi airtime
caused in the native network namespace. H0/static evidence must therefore
freeze one exact supported parent-owned traffic-control and conntrack design
before identity allocation. Before release, both nonce-created veth ends have
fixed MTU/txqueuelen plus exact ingress/egress packet/byte rate, burst, and
queue-depth limits. Permitted traffic uses one dedicated conntrack zone with
exact new-flow-rate and concurrent-flow bounds; flow/hardware offload is
forbidden for the first proof. The same pre-release transaction installs and
binds one exact dormant SSH-ingress gate: its complete forwarding/NAT rule and
named set/handle exist, the sole manifest-bound activation element is absent,
and default drop prevents a match. Every qdisc/filter/action/zone/table/chain/
set/rule handle, empty-element prestate, counter, interface identity, target/
boot/run nonce, and close-only cleanup operation is bound and reread. Global conntrack settings, existing Wi-Fi qdiscs,
and other interfaces never change. Cleanup blocks new traffic, removes only
the zone's state and nonce-bound handles/interfaces, and proves complete
absence plus unchanged native configuration/identity; ordinary existing
Wi-Fi counters may only advance monotonically and are never reset. Missing
per-zone accounting/removal,
unsupported limits, unreadable/wrapped counters, reserve failure, or cleanup
ambiguity is `NO_GO`/`RECOVERY_PARKED`.

Native PID 1 journals one child launch, uses one bootstrap-only scalar control
pipe, drains the separate bootstrap-only scalar receipt pipe into cache-backed
SD-free evidence, supervises the exact pidfd and bound network rules, and
remains available for deterministic fallback. Both pipes are close-on-exec and
no descriptor is inherited by Debian init. Post-exec health
is not inferred from an undeclared rootfs writer: the native parent records
only externally observed pidfd/exec/network facts, while a separate host
observer must authenticate through the exact SSH path and bind the same run.
Local persistent evidence also rereads the single key-daemon/listener tree,
non-login IDs, non-dumpable state, two-cap filter, bounded session count, and
exact clean-exec mapping provenance plus zero service-side key FD/proc access;
the `LOCAL_PERSISTENT` proof must also reread the exact dormant gate, absent
activation element, zero pre-open counters, and default-drop policy. It still
cannot open ingress or claim authentication.

Only after durable `INGRESS_OPEN_INTENT` binds that local proof, exact table/
chain/set/rule/element identities, empty prestate, counters, one reviewed atomic
activation and the close-only cleanup may native PID 1 dispatch one insertion
of the prebound element. It never creates/replaces a rule or dispatches the
activation twice. Exact return plus independent handle/element/policy/counter
readback must be durably recorded as `INGRESS_OPEN` before any host connection;
all other ingress remains default-drop. Missing/torn return, wrong or duplicate
element/handle, drift, or read failure is never resent. When exact identity is
complete, reconciliation removes only that element with the predeclared close-
only cleanup, proves the gate dormant, and enters `RECOVERY_PARKED`; incomplete
identity parks without guessing or flushing global state. Return and failure
cleanup always close and prove this element absent before terminating child
services or deleting the remaining bound network objects, and independently
prove no parent nsfs FD or duplicate can pin any child namespace before claiming
that namespace gone. A wrong/stale/duplicated/retained namespace FD, flag/inode
drift, move-ack or close failure, result published before zero-reference
enumeration, or cleanup with a parent-pinned namespace is `RECOVERY_PARKED`.

Those two pipes are the only native-facing pipes, and the proved-clean
bootstrap is the sole native-receipt writer. Generator and key-daemon helper
forks may only close both main-pipe ends before clean exec and never carry or
write them across that exec. For each helper, one at a time, bootstrap
creates one transient internal `pipe2(O_CLOEXEC)` status channel, retains its
read end, and gives the helper only the write end plus the exact manifest-bound
object FDs required by that exec. The helper fork closes every unrelated FD,
temporarily clears `FD_CLOEXEC` only on that exact set for one static exec, then
re-arms and rereads every retained descriptor before emitting as the sole
writer. The generator emits exactly `GENERATOR_CLEAN_READY` followed by one
bounded public-only `GENERATOR_PUBLIC_COMPLETE`, closes before exact exit/reap,
and reaches EOF. The daemon emits exactly `KEY_DAEMON_CLEAN_READY` followed by
`KEY_DAEMON_LISTEN_READY`, closes before any accept, and reaches EOF while it
remains live. Bootstrap binds the helper pid/start/pidfd, frame order, byte cap,
FD set, and EOF, closes the internal read end, and alone forwards the canonical
summary on the native receipt. At every main stop only the original two
bootstrap ends remain. Wrong or multiple writer, inherited main-pipe end,
extra FD, interleaved/partial/duplicate/extra frame, premature or late EOF,
helper crash, or internal-pipe residue is `RECOVERY_PARKED` and is never
inferred or replayed.

Before child release, trusted bootstrap must generate exactly one per-boot
Ed25519 Dropbear host key in the child's private mode-0700 tmpfs using the exact
manifest-pinned helper. The proved-clean bootstrap forks it only through an
exact static generator exec; a pre-key barrier must bind its executable,
`maps`, and `map_files` with no inherited native mapping. That helper is the
sole bounded transient generator
memory exception before `ROOT_PREPARED`: before generation it is permanently
non-dumpable with `RLIMIT_CORE=0`, an exact executable/argv/environment/ID/
capability/stdio/FD set, and no core/log/socket/foreign output sink. Exact
source and negative fixtures must prove one absent `O_EXCL` key file, one
bounded public-only `GENERATOR_PUBLIC_COMPLETE` internal frame after
`GENERATOR_CLEAN_READY`, terminal EOF, zero private output, exact exit/reap, and no
remaining PID, FD, address space, core, log, temporary file, or second key;
crash, signal, output, reap, or residue ambiguity is `RECOVERY_PARKED`.
During that exact generation only, private bytes may exist in the one file and
the generator address space. After proven reap and before daemon launch they
may exist only in the file; after load they may exist only in that file and the
filtered non-dumpable key-daemon memory required for signing. The file is mode
0400 and owned only by the distinct non-login key-daemon identity. Only its
algorithm, public key, SHA-256 fingerprint, and target/resident/boot/run/pidfd/
cache binding may enter the native receipt. The service UID, PID 1, forced
probe, workload, logs, and retrieval never receive a key FD, buffer, or byte.
Bootstrap binds the exact inode/size/hash locally, remounts the exact
`/etc/dropbear` tmpfs read-only, rereads the mount and file binding, and proves
descendants cannot replace, unlink, rewrite, rotate, traverse, or read the key
outside the key daemon. Before any SSH attempt the host
must retrieve that exact receipt through the dedicated target-bound read-only
frame, construct a no-clobber private `known_hosts`, and require
`StrictHostKeyChecking=yes`. TOFU, first-seen network pinning,
`StrictHostKeyChecking=no`, stale receipt reuse, within-run rotation, missing or
duplicate keys, and fingerprint or presented-key drift fail closed. Only then
may it perform the exact public-key-only client authentication described above;
success additionally requires the one fixed service account, accepted
client-key fingerprint, forced read-only probe, and zero password/interactive/
alternate-account/command/forwarding path. Exact child cleanup destroys the
private key only after blocking new sessions, reaping every bound
listener/session engine, and proving every key-daemon PID/FD plus both
dedicated-UID resource sets gone; a later boot requires a fresh key and
receipt.
On every selected isolated-Debian failure branch, native PID 1 first blocks all
new veth traffic and SSH accepts/sessions, then durably appends the immutable
original stage/return/errno plus cleanup intent and exact bound identities.
Only after that record may it terminate/reap the exact namespace members and
remove the bound network/cgroup state. Cleanup outcomes append separately and
never replace or aggregate away the original failure; any missing record,
identity, or cleanup proof is `RECOVERY_PARKED` and never replays handoff.
Before child release the parent may reap the blocked bootstrap and remove only
its exact zone state, qdiscs/actions, veth/rules, and empty child cgroups. After
release it never launches a second child;
uncertainty is recovery-parked. While Debian is live state is
`HEALTH_PENDING_PERSISTENT_DEBIAN`; only attended return/recovery plus exact
native health closes `RESIDENT_HEALTHY`.

This architecture is H0 until its kernel/toolchain feasibility, complete
execution-critical source, crash prefixes, cleanup, performance cost, and
negative isolation corpus receive independent review. No successor identity or
live action is allocated. The ownership gate retires only after an isolated-
Debian successor proves no ownership-stop path is reachable and its exact live
terminal/recovery closure succeeds; the gate itself grants no authority.

After that decision, a successor may define a headless persistent-server lane
that compile-disables the persistent native HUD and firstboot overlay. Such a
lane must retain the exact read-only UFS, boot-private authentication, minimal
Debian `/dev` with no devpts/PTY, final Wi-Fi, one-shot/no-replay, rollback,
cleanup, recovery, and resident-health boundaries.
Its persistent result may prove Debian PID 1, authenticated SSH, exact minimal
Debian `/dev`, final Wi-Fi, and persistent service health while explicitly
making no display or HUD claim. While Debian remains live, device safety stays
`HEALTH_PENDING_PERSISTENT_DEBIAN`; only an attended return or recovery and
exact native checks may close `RESIDENT_HEALTHY`. It must not inherit a
HUD-enabled result predicate.

The exact audit in
`docs/reports/A90_H14_IMMUTABLE_FIRSTBOOT_ISOLATED_DEBIAN_MISMATCH_H0_2026-08-14.md`
rejects the immutable H14/H24 demonstration content for that successor: its
12,092-byte firstboot also configures legacy NCM, smoke, HUD-intent, and Debian
Wi-Fi paths and has no post-exec receipt writer. A separately versioned minimal
Debian content manifest must therefore be built and independently reviewed
before candidate allocation. Its eventual installation is a separate
target-contract capability and attended authority, and additionally requires a
separately reviewed higher-precedence boundary change because the current
common contract activates no direct UFS filesystem-content mutation. This H0
decision authorizes no UFS write, overlay, or non-boot partition payload.

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

The common contract delegates one exact A90-only boot-control exception needed
to leave this TWRP. Only after the selected `boot` image has been written once
and its exact prefix SHA-256 read back, `native_init_flash.py` may invoke TWRP
System reboot once. Immediately before that invocation it must revalidate TWRP
`3.7.0_12-0` and the direct regular root-owned executable
`/system/bin/rebootsystem.sh`, mode `0755`, size `89`, SHA-256
`3c3058563bbe775505fb5c0be8b94ae4a5e44787b5971ca17fd49e599ae7dd07`.
Those exact bytes contain only the fixed zero-source write of `bs=256 count=1
conv=notrunc` to `/dev/block/by-name/misc`; TWRP then reboots. The runner never
executes that `dd` directly, cannot select another path/offset/count, and does
not retry TWRP System reboot after a send or response uncertainty. Any helper,
TWRP, script, recovery-identity, ordering, or readback drift stops before this
exception. It grants no general raw-block, `misc`, recovery-partition, or other
target authority.

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

The one fixed H27 `EFBIG` incident dated 2026-08-21 may retire its retained
host guards only through
`a90_h27_pretransfer_abort_reconcile_v1.py`. This exception is limited to run
`a90-h27-f1-20260820-01` and its immutable manifest/journal/helper receipts.
The reconciler accepts no caller-selected input. It must verify both the exact
archived review bytes named by the historical manifest and a current
`PASS_GO` review whose closure contains the reconciler; the latter review SHA
is part of the durable reconciliation and must remain exact during any
post-publication guard cleanup. It must then cryptographically bind
the complete candidate and rollback stdout/stderr bytes back to each journaled
effect-receipt SHA-256 by exhaustively resolving the sole bounded integer
duration, prove both helpers stopped before sealed-copy completion, `adb push`,
boot write, and boot readback, and obtain a fresh exact healthy H24 observation.
It then durably publishes `PRETRANSFER_ABORTED_NO_BOOT_WRITE` before removing
only that run's exact active and candidate guards. A crash after publication may
only finish those same exact guard removals. Any missing, duplicate, malformed,
unbound, advanced-stage, unhealthy, or changed byte parks without removal.

That exact durable receipt proves that the H27 candidate was not transferred
and permits one later fresh run and approval to select the same candidate bytes;
it does not relabel the failed terminal, authorize a device effect, or create a
general retry rule. The exception expires after its exact reconciliation record
is published and cannot apply to another run, candidate, helper failure, or
future incident. Future reusable pre-transfer recovery requires a separately
reviewed structured helper stage receipt rather than parsing prose logs.

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
