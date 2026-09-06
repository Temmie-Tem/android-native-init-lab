# S22+ FYG8 Binding Target Contract

Status: **BINDING**

This contract specializes `AGENTS.md` for the attended Samsung Galaxy S22+
FYG8 target `SM-S906N` / `g0q` / `S906NKSS7FYG8`. It is not authority for any
other model, firmware, target profile, or connected device.

`GOAL.md` owns the current experimental state. This file alone neither arms the
target nor opens a D0/D1/F1 action. The common Fast-Loop trial is retired; it
grants no standing D0, attended autonomy, or per-candidate approval waiver.

Conditional autonomous F1: **NOT ACTIVE**. AGENTS Revision 6 defines the
delegation but does not qualify this target's automatic recovery or change its
current runner. The attended F1 and physical-recovery requirements below remain
in force until a separately reviewed exact target activation.

## Inheritance and Precedence

All common invariants and permanent safety boundaries in `AGENTS.md` apply.
This contract may specialize delegated H0/D0/D1/F1 and pre-session failure
rules only. The retired common trial is historical evidence and resolves no
procedural conflict; the more restrictive applicable live rule wins.

The ordinary S22+ F1 mechanism is
`docs/operations/DEVICE_ACTION_PROCESS_V2.md`. Full-stock evidence under
`docs/operations/S22PLUS_FYG8_STOCK_FIRMWARE_EVIDENCE_POLICY_2026-07-08.md`
is recovery evidence only and never authorizes full-firmware or non-boot
flashing. Historical `DRAFT`, `EXCEPTION`, `ACTIVE_CLAUSE`, and archived files
do not grant authority.

## Target Isolation

- Resolve the exact S22+ target and target profile before every D0, D1, or F1
  action. Device serials remain private.
- When multiple devices are attached, inventory them first, select the exact
  S22+ explicitly, and record that every other device was untouched.
- Any ambiguity between S22+, A90, transport endpoints, Download-mode devices,
  or rollback identities is an immediate stop.
- A90 approvals, health evidence, transports, artifacts, and resident-promotion
  rules never apply to S22+.

## S22+ H0

H0 includes source and artifact inspection, intent and contract design,
building, Full-LTO A/B, static and linked audits, package construction,
offline promotion, manifest construction, and dry runs with all device access
hidden. H0 may create private payload artifacts but grants no right to use
them on a device.

### Source identity

- Before intent derivation, freeze the complete byte-affecting change list and
  print the selected `SOURCE_KEYS` with their paths. Compare them against
  Git-derived tracked and untracked changes in both directions.
- After intent derivation, do not change a `SOURCE_KEYS` byte. A Tier-1 change
  invalidates the run identity and requires a new intent and qualification,
  including a new Full-LTO A/B pair when applicable.
- Verifiers, decoders, evidence adapters, and documents may remain outside
  candidate identity only when the selected contract says so and the approval
  or live-binding bundle pins their exact bytes. Such a repair must prove `CHANGED_KEYS=[]`
  and cannot alter the candidate artifact.
- Do not change a running Full-LTO build's bound inputs. Stop that build before
  changing its closure; unrelated H0 work may continue without changing those
  inputs or misrepresenting the build's source identity.

### S22+ Rule 7: evidence-led pre-session repair

A material failure is identified by its failed invariant, input/producer
contract, and causal mechanism, not merely by exception spelling or line
number.

Before any connected device command is sent and before a transfer tool begins
or reports a device session:

1. Preserve the failed invocation's evidence and repair the bounded host task
   without another approval or a fixed one-repair limit. Each retry must have
   new evidence or a relevant correction; unchanged retry loops are not progress.
2. Record the observed input or fixture, changed closure, and whether candidate
   identity is preserved in the existing change description. Run the relevant
   checks before using the corrected result. Changed candidate inputs still
   require a fresh identity and the qualification they actually affect.
3. Stop the approach when it makes no evidence-based progress, exhausts its
   resource budget, or needs a scope change. Do not rename the same failure to
   evade a stop or weaken a safety assertion to obtain PASS.
4. Before a later live window, exercise the representative actual entry,
   producer/consumer and result paths with real input or a captured fixture.
   Reuse that qualification while its relevant inputs remain unchanged.

H0 request hashes and re-entry packets are evidence bindings, not device
authority; a host correction does not need a new packet by default. A particular
operator authorization may deliberately impose a narrower stop condition; if
so, that narrower text controls that invocation.

After the first connected device command, Download-mode handoff, or transfer
tool device session begins, the common immediate-stop rule applies. No bounded
host repair in this section can be used to continue the live candidate.

## S22+ D0

D0 is bounded, connected, read-only observation of the exact S22+ target.

- Use explicit target selection and bounded commands. Reads may include exact
  identity, boot health, sysfs/procfs state, and host USB inventory.
- Do not reboot, alter modes or settings, create device files, restart a
  service, write sysfs, or send a payload.
- A D0 ambiguity or unexplained failure ends that D0 invocation. It grants no
  F1 authority and does not consume or replay a candidate transfer.
- With multiple attached devices, report the selected S22+ and explicitly
  confirm that the other target received no command.

## S22+ D1

D1 is one exact, transient, no-payload control action.

**Attendance predicate.** The operator must remain present and able to perform
the action's predeclared return or recovery step. If the action can remove the
working control channel or require a physical restart, the operator must be
able to perform that physical step within its bound. Attendance loss freezes
new effects; it never authorizes replay of the uncertain action.

- D1 requires the fresh exact authority specified by the live common and target
  rules. Any helper binding of target, command, recovery, and return health is
  an additional compatibility constraint and never substitutes for authority.
- Permit no partition payload, persistent setting, security-state change, or
  cross-target command.
- Send the bound action once. An unexplained failure after it begins stops
  D1. Do not turn it into a retry loop or an F1 substitute.
- Predeclare any attended hardware-restart contingency and its trigger. Do not
  invent a recovery action during the session.
- Verify and report the expected healthy terminal state. The sole S22+ attendance/ordinal exception is `docs/operations/targets/S22PLUS_FYG8_PREF1_AUTONOMOUS_RESEARCH_POLICY_V1.md`; it remains `DEFINED_NOT_ACTIVE` until its exact coordinator, tests, independent `PASS_GO`, activation manifest, and attended session approval are mechanically present, and it never grants persistent mutation, F1, or partition transfer.

## S22+ F1

S22+ F1 is the ordinary Process-v2 boot-only candidate transfer followed by
its mandatory exact rollback and verified final health.

**Attendance predicate.** For S22+ F1 the operator must be able to perform a
physical Download entry within the profile's recovery bound, not merely be
present. A run awaiting that physical step parks, remains F1-armed, and resumes
from durable journal state. Host-only work continues during the park.

Endpoint absence or late host discovery during that interval enters
`HEALTH_PENDING` and then `RECOVERY_PENDING_PARKED`; it is not by itself a
candidate, device-health, or recovery failure. No next candidate may be armed
and the uncertain candidate is never replayed. Passive host observation and
the exact predeclared rollback continue until final FYG8 health is proved or
the predeclared recovery path is exhausted.

**Physical-topology continuity.** From the exact Download endpoint binding
through rollback transfer and verified final-health close, the operator must
not disconnect, move, or reroute the data cable, dock, or host port. The
observer must never widen its selector or open an unapproved endpoint.

This is the permanent `S22PLUS_F1_PHYSICAL_TOPOLOGY_CONTINUITY` boundary. It
blocks physical endpoint drift from invalidating candidate attribution or
rollback authority, applies only to S22+ F1 endpoint observation and recovery,
and has no expiry. Any change to endpoint identity, topology/controller
capture, phase classification, recovery rebinding, or selector semantics
requires a new independent boundary review.

**P324 exact Type-C lane binding.** For the P324 S22+ observer and only the
exact P325, P326, and P327 successors defined below, the
approval must bind and the runner must capture/revalidate the exact `port0`
lane pair `usb:2-1.3` (`usb2-port1`, controller `0000:00:0d.0`) and `usb:3-1.3`
(`usb3-port1`, controller `0000:00:14.0`) with their shared connector/location
identity. Both lanes may be recorded, but the candidate observer may open only
the explicitly approved exact candidate endpoint at `usb:3-1.3`; foreign,
duplicate/ambiguous, incomplete, or malformed endpoint state fails closed. This
does not generalize to USB4, a shared topology suffix, another host, or another
target. Same-run Type-C partner continuity is corroborating evidence only and
never replaces the operator's no-disconnect/no-move/no-reroute condition. Any
change to this pair, its approval-bound capture/revalidation, or its
single-endpoint selector requires a fresh independent boundary review.

**P325 exact tty guard-property repair.** P325 may reuse the unchanged P324
`port0` lane capture, revalidation, single-endpoint selector, transient udev
rule, P300 passive trace, and rollback choreography only under a fresh P325
candidate identity, execution closure, connected preparation, and attended
approval. Its sole observer change is that both existing read-time
ModemManager guard property probes resolve the exact selected tty class node
instead of the USB interface node. The existing matcher must still require
both `ID_MM_DEVICE_IGNORE=1` and `ID_MM_PORT_IGNORE=1`; no parent/interface
fallback, one-flag acceptance, selector widening, retry, or extra device action
is permitted. P324 is closed and consumed and grants no replay or standing
authority. Any further guard, rule, lane, or selector change requires a fresh
independent review.

P325 D0 may classify one retained predecessor baseline as current-run clean
only when the complete raw `/proc/last_kmsg` is exactly 2,097,136 bytes with
SHA-256 `e64815cf43f0772226518d39e566d6b8670f225a0469bca89022e50a9d918552`
and the P324 decoder independently finds one integrity-clean, foreign-free
`NO_PROOF_OBSERVER` record at offset 1,657,196 for the consumed P324 run. This
exception applies only to P325 preparation, admits no other P324 bytes or
semantics, grants no replay or standing D0/F1 authority, and expires on raw
identity drift or P325 candidate intent.

P325 candidate intent has now occurred and the exact candidate is closed and
consumed. Both P325 clauses above are retained evidence only and grant no new
prepare, approval, candidate action, or replay.

**P326 fixed bidirectional-console successor.** P326 may reuse the unchanged
P324 `port0` lane selector and the proved P325 tty-class two-property guard.
It changes neither endpoint, udev rule, ModemManager predicate, P300 passive
trace, nor rollback choreography. After the exact fresh 49-byte P326 banner,
the observer may write only the two fixed run-bound lines `PING` and `SHELL`
(77 bytes total). PID 1 must return the exact run-bound `PONG ... pid=1`, and
the fixed `/bin/busybox ash` child must return the exact
`SHELL-OK ... busybox=1`; the complete device transcript is exactly 145 bytes
and is retained through the inherited raw writer before classification. Any
immediately available trailing byte is also retained and rejects the proof;
the BusyBox `ash` child exits after its fixed reply.

The P326 ramdisk may add only direct regular `/bin` and
`/bin/busybox`; the latter is the static AArch64 BusyBox 1.36.1 binary of
2,237,056 bytes with SHA-256
`d4e1ca8235fd5c47a7dfca5c9c60ad2243f5d17d3c43d58a7c42355f10fa2cba`.
The candidate remains a boot-only AP, the shell child is ephemeral, and exact Magisk
rollback plus final rooted FYG8 health remain mandatory. The two proof writes
do not authorize a caller command, a persistent shell, ADB/MTP, a package or
filesystem mutation, or a USB/Max77705 causal claim. Any command beyond those
two fixed lines, or any guard/rule/lane/selector/rollback change, is outside
P326. This clause remains H0 and inactive until its exact execution-critical
closure receives independent review and a ready declaration is published;
neither event is a device approval.

**P327 bounded framed-command successor.** P327 may reuse the exact P326
BusyBox payload and the unchanged P324/P325 topology, tty guard, udev rule,
P300 passive trace, Carrier supplement, and rollback choreography. Its sole
live-protocol change replaces the fixed P326 `PING`/`SHELL` exchange with a
16-byte little-endian `S327` version-1 frame header, CRC32, and payloads of at
most 1,024 bytes. After the exact fresh run-bound banner, the host must send
one `OPEN`, exactly the following three `EXEC` payloads in order, and one
`CLOSE`: `/bin/busybox id`, `/bin/busybox uname -a`, and the exact run-bound
`/bin/busybox echo P327-NONCE ...`. The device returns one `READY`, bounded
`DATA` plus one `EXIT` for each command, and one `DONE`. Sequence, CRC, length,
run ID, command list, and terminal status must all match.

Each child has a ten-second PID-1-owned timeout and 128-KiB output bound;
PID 1 must isolate, kill, and reap the complete child process group on timeout
or closure. The observer retains received bytes through the inherited raw
writer before classification. After `DONE`, any immediately readable trailing
byte is also retained and rejects proof. Proof requires all three fixed
commands to exit zero, root `id` evidence, a bounded Linux `uname` line, the
exact nonce reply, and clean session closure. A caller-selected or fourth
command, interactive PTY, persistent shell, filesystem mutation, ADB/MTP
substitution, selector or recovery change, or causal USB/Max77705 claim is
outside P327. The candidate
remains a boot-only AP and exact Magisk rollback plus final rooted FYG8 health
remain mandatory. This clause is H0-only until its exact execution-critical
closure receives independent review and a ready declaration is published;
neither event is a device approval.

**P328 authenticated bounded-command successor.** P328 may reuse the exact
P327 BusyBox payload, child timeout/output/process-group cleanup, P324/P325
lane and tty guard, raw-first capture, Carrier supplement, and rollback
choreography under a fresh candidate, run, preparation, and approval.  Its
protocol change replaces the public run-ID-only OPEN with one per-session
32-byte kernel-random challenge and HMAC-SHA256 authentication using one
private 32-byte key.  The key may exist only in the private candidate material
and the exact private host input; tracked files and durable results retain only
its size and SHA-256.  A short, zero, unavailable, mismatched, or replayed
challenge/tag fails before any child is created.  AUTH, READY, every EXEC, and
CLOSE bind the fresh run ID, challenge, frame role, sequence, and exact command
bytes; device comparisons are constant-time.

This symmetric-key prototype authenticates possession of that private
candidate/key pair; it does not claim hardware-backed secrecy, and anyone who
obtains the private candidate image can recover the embedded key.  That limit
must remain explicit in the P328 qualification report and any resident
successor.

The P328 live proof sends only `/bin/busybox id`, `/bin/busybox uname -a`, and
the exact run-bound BusyBox echo command.  Unlike P327, those strings are not a
device-side allowlist: the authenticated non-PTY runtime accepts one to sixteen
printable caller-selected command payloads, each bounded by the frame, a
15-second timeout, 128-KiB output, stdin `/dev/null`, and complete process-group
kill/reap for the original session group.  This establishes an authenticated
bounded command transport, not
an interactive PTY or standing command authority.  Any other P328 live
command, unauthenticated fallback, persistent session, resident retention,
filesystem or security mutation, ADB/MTP substitution, selector/recovery
change, or causal USB/Max77705 claim is outside this campaign.  P329 resident
retention is not implied; later retained command use requires its own
activated successor lane.

The candidate remains a boot-only AP and exact Magisk rollback plus final
rooted FYG8 health remain mandatory.  This clause is H0-only until the final
execution-critical closure and this boundary change receive one independent
review and a ready declaration is published; neither event is device approval.

**P329 bounded udev-settle successor.** P329 may reuse the exact P328
authenticated protocol, private key, BusyBox, command/process bounds, P324
lane, P325 two-property tty guard, raw-first capture, Carrier supplement, and
rollback choreography under a fresh P329 run identity, distinct boot-only AP,
connected preparation, and attended approval. Its only live-observer change
is a maximum 500-ms settle, polled no faster than every 25 ms, between exact
candidate endpoint selection and tty open. Every poll must keep the guard
healthy and the exact tty class node, character-device numbers, USB identity,
and approved `usb:3-1.3` topology unchanged. The observer may open only after
both `ID_MM_DEVICE_IGNORE=1` and `ID_MM_PORT_IGNORE=1` are simultaneously
present on that exact tty node. It has no parent/interface fallback, one-flag
acceptance, endpoint widening, open retry, device action, or protocol retry.
Stable absence through the bound is `guard-property-timeout`; identity or
guard drift still fails immediately.

The P328 `S328` wire magic, HMAC domains, and `P328-NONCE` proof namespace are
retained compatibility labels; all carry the fresh P329 run bytes. Reusing
those protocol labels or the same private key does not authorize P328 replay,
resident retention, an interactive PTY, or later commands. The candidate
remains boot-only and exact Magisk rollback plus final rooted FYG8 health are
mandatory. This clause is H0-only until the changed execution-critical
closure and timing boundary receive one independent review and a ready
declaration is published; neither event is device approval.

**P330 bounded pre-auth diagnostic successor.** P330 may reuse P329's exact
endpoint, 500-ms two-property udev settle, S328 HMAC protocol, private key,
command/process bounds, topology lane, raw-first capture, and rollback under a
fresh run identity and distinct boot-only AP. Its device delta emits only two
fixed type-`0x86` eight-byte diagnostic frames: `OPEN_PARSED` after exact OPEN
validation and `RNG` after nonce acquisition. `getrandom` may retry at 100-ms
cadence no more than 64 times and only for `EAGAIN`; no endpoint, open,
protocol, command, or other error is retried. The host retains actual partial
TX/RX and a bounded stage/type/hash record after raw capture closes.

Diagnostics localize failure only. They never establish challenge, HMAC,
command, shell, closure, or candidate proof; PASS still requires the unchanged
authenticated command exchange and final healthy rollback. P330 requires a
fresh preparation, exact approval, and attendance. This clause is H0-only
until the changed execution-critical closure has independent review and a
ready declaration; neither event is device approval.

**P331 bounded resident-reconnect precursor.** P331 may reuse the exact P330
endpoint, two-property settle, pre-auth diagnostics, HMAC key and framing,
command child cleanup, Type-C lane, raw-first capture, Carrier supplement, and
rollback under a fresh run identity and distinct boot-only AP. Its only device
runtime extension permits exactly two authenticated sessions and one clean
reconnect. Each session requires a fresh nonzero nonce, the unchanged HMAC
exchange, exactly one fixed heartbeat/status command, zero exit, authenticated
close, and no trailing byte. The host closes and reopens only the same exact
tty between sessions; an unclean close, timeout, authentication failure,
replayed nonce, changed endpoint, exhausted cap, or partial exchange stops
without reconnect or command replay.

This bounded two-session proof is a resident precursor only. It does not
retain the candidate after F1, install a Magisk module, create an Android
service, grant an interactive PTY or unrestricted shell, permit file transfer,
or activate A90 resident authority. Exact Magisk rollback and final rooted
FYG8 health remain mandatory. A later retained-boot or Android-resident install
requires its own target-contract lane, recovery owner, independent review, and
fresh authority. This clause is H0-only until its exact changed closure has
independent review and a ready declaration; neither event is device approval.

P331 D0 may treat one retained P330 baseline as current-run clean only when
the complete raw `/proc/last_kmsg` is exactly 2,097,136 bytes with SHA-256
`3136c504434fac224f9fb9ffe1f688d1bf73062fbb75cb0da8117a885f3e05c6`
and the fixed P330 decoder finds exactly one integrity-clean, foreign-free
`NO_PROOF_OBSERVER` Carrier record at offset 1,657,877 for consumed run
`c330f1e0a90b5e6d7c8a9b0c1d2e3f0b`. This preflight exception proves only
that the fresh P331 run is absent; it does not reuse P330 ACM proof or grant
candidate authority. It applies only to P331, and expires on raw identity
drift or P331 candidate intent.

**P332 same-FD logical-session successor.** P332 may reuse the exact P330
authenticated three-command exchange, private key, pre-auth diagnostics,
child cleanup, P329 endpoint settle, P324/P325 lane and guard, raw-first
capture, Carrier supplement, rollback, and final-health choreography under a
fresh run identity and distinct boot-only AP. Its only live runtime change is
two sequential complete P330 exchanges on one already-open tty descriptor.
The host opens and closes that descriptor once for the observation window;
there is no physical close/reopen, transport reconnect, fallback, or retry.
Session two starts only after session one returns success, both challenges
must be fresh, and proof requires both fixed-command sessions, clean closure,
zero trailing bytes, and exact ordered raw TX/RX binding.

This is a bounded logical-residency check, not a retained install or standing
session. It adds no persistent state, Android service, interactive PTY,
caller-selected command, arbitrary file transfer, selector widening, or USB/
Max77705 causal claim. Exact Magisk rollback and final rooted FYG8 health
remain mandatory. This clause is H0-only until its exact changed closure has
independent review and a ready declaration; neither event is device approval.

P332 D0 may treat the one retained P331 baseline as current-run clean only
when the complete raw `/proc/last_kmsg` is exactly 2,097,136 bytes with
SHA-256 `f33384fbedd604deca988bfb8ac9522e492aa930f5e81a816348730a5d0e3238`
and the fixed P331 decoder finds exactly one integrity-clean, foreign-free
`NO_PROOF_OBSERVER` record at offset 1,767,463 for consumed run
`c331f1e0a90b5e6d7c8a9b0c1d2e3f9b`. This proves only that the fresh P332 run
is absent; it does not reuse P331 session evidence. It expires on raw identity
drift or P332 candidate intent.

**P333 OPEN-entry diagnostic successor.** P333 keeps P332's exact two
sequential authenticated P330 exchanges on one tty descriptor, fixed three
commands, private key, endpoint settle, lane/guard, raw-first capture, Carrier
supplement, rollback, and final-health choreography under a fresh run identity
and distinct boot-only AP. Its only runtime delta emits the existing bounded
diagnostic frame with stage `0` and code `0` immediately before each of the two
out-of-line console calls. The host still sends OPEN only after the native PID1
banner, requires stage `0` before the existing OPEN-parsed and RNG diagnostics,
and performs no retry. Missing, malformed, or reordered stage `0` remains
no-proof and proceeds to the mandatory rollback.

P333 adds no framing, command, retry, reconnect, persistent state, interactive
PTY, caller-selected input, file transfer, or USB/Max77705 causal claim. Exact
Magisk rollback and final rooted FYG8 health remain mandatory. This clause is
H0-only until its exact changed closure has independent review and a ready
declaration; neither event is device approval.

P333 D0 may treat the retained P332 rollback baseline as current-run clean only
when the complete raw `/proc/last_kmsg` is exactly 2,097,136 bytes with SHA-256
`455eec000b3aa14e8fca155b857910b4ed4c16285e55e390e59dcfb2f3386ab4`
and the fixed P332 decoder finds exactly one integrity-clean, foreign-free
`NO_PROOF_OBSERVER` record at offset 1,658,084 for consumed run
`c332f1e0a90b5e6d7c8a9b0c1d2e3f8b`. This proves only that fresh P333 is
absent; it reuses no P332 session evidence and expires on raw drift or P333
candidate intent.

**P334 first-console-return diagnostic successor.** P334 keeps P333's exact
two sequential authenticated P330 exchanges on one tty descriptor, fixed
three commands, private key, stage-0 diagnostics, endpoint settle, lane/guard,
raw-first capture, Carrier supplement, rollback and final-health choreography
under a fresh run identity and distinct boot-only AP. Its only runtime change
captures the first outer console call's return and writes it into the existing
post-rollback checkpoint terminal detail: `0xB000 | errno` for return `0` or
`-1..-4094`, and `0xBFFF` when the call was not reached or the return is outside
that domain. It adds no checkpoint generation, tty response, frame, command,
retry, reconnect or persistent write. The detail identifies the first
read/OPEN boundary only when the same run retains stage 0 and no later
OPEN-parsed stage.

P334 remains a bounded diagnostic rather than a retained install or standing
session. Exact Magisk rollback and final rooted FYG8 health remain mandatory.
This clause is H0-only until the exact changed closure receives independent
review and a ready declaration is published; neither event is device approval.

P334 D0 may treat the retained P333 rollback baseline as current-run clean only
when complete raw `/proc/last_kmsg` is exactly 2,097,136 bytes with SHA-256
`ce236dfaddd23c9edd5165cee871d576cb8bb106ad4dbbf508c2861162ae617d`
and the fixed P333 decoder finds exactly one integrity-clean, foreign-free
`NO_PROOF_OBSERVER` record at offset 1,652,363 for consumed run
`c333f1e0a90b5e6d7c8a9b0c1d2e3f7b`. This proves only that fresh P334 is
absent; it reuses no P333 session evidence and expires on raw drift or P334
candidate intent.

**P335 attended current-boot resident lease.** A fresh exact P335 approval may
leave the ordinary F1 journal at `OBSERVED` after one exact candidate transfer
and the manifest-bound authenticated listener proof. Only after a separate
no-clobber lease and guard are durably published and directory-fsynced may the
candidate-observer guard and host session lock be released. The lease permits
at most one attended hour and 16 named read-only actions from the immutable
manifest during that same boot. Every action freshly revalidates the exact
target, endpoint, topology, candidate identity, unchanged nonzero per-boot
identity, private key receipt, catalog and recovery owner, then records one
durable intent and one result. The reviewed host runner never accepts a caller
command, shell fragment, path, executable or environment, and an uncertain
intent or dispatch is never replayed. The inherited device parser can accept a
bounded printable authenticated command and is not claimed as a device-side
allowlist; direct use outside the named host runner has no authority.

The lease is an intermediate nonterminal observation state, not
`RESIDENT_HEALTHY`, Android health, a reboot-persistent promotion, F1 closure,
standing authority or a new candidate. Failure or ambiguity before listener
proof takes the ordinary immediate rollback branch. Lease expiry, operator
stop, attendance loss, target or closure drift, unexpected reboot, listener
failure, recovery-path loss or an uncertain action permits only the originally
approved exact Magisk rollback. Candidate replay and a replacement artifact
remain forbidden. The F1 result and campaign-ledger row are published only
after exact rollback and final healthy rooted FYG8 Android return.

The ordinary `OBSERVED` transition and its subsequent `candidate_boot_ready`
event must both be durable before lease publication, preserving the order
`OBSERVED -> candidate_boot_ready -> lease/guard`. The lease uses schema
`s22plus_fyg8_p335_resident_lease_v1`, owns its monotonic one-hour deadline,
and keeps a separate append-only action intent/result journal. Initial proof is
exactly two same-FD sessions followed by one host close/reopen session. After
that proof the listener admits at most one authenticated session for each of
the 16 lease actions; neither the proof nor an action creates an extra retry or
reconnect budget. Named actions exist only inside the active P335 F1 lease and
are not independent D1 or standing authority.

P335 reuses P334's authenticated S328 framing, fixed BusyBox child isolation,
three named commands and exact rollback under a fresh run identity and distinct
boot-only AP. It adds only two initial same-FD logical sessions, one exact host
tty close/reopen session, a single per-boot identity shared by all sessions,
and the low-duty listener needed for later lease actions. Expected idle or
no-peer outcomes may return only to the wait state; protocol,
authentication, command, child-cleanup or unexpected I/O failure parks the
listener. P335 adds no persistent file, Android service, interactive PTY,
file transfer, generic shell authority, package, mount, property/service
change, reboot, unattended control or non-boot payload. This clause is H0-only
until its complete changed execution closure receives independent review and a
ready declaration; neither event is device approval.

**P336 long-idle resident resynchronization.** P335 is consumed and grants no
P336 session or replay authority. A fresh exact P336 candidate may retain the
same three-command, current-boot, attended lease only to repair the observed
long-idle host reopen boundary. Its initial three-session candidate proof and
all P335 lease, recovery, target, topology, authentication, command, time and
action-count restrictions remain unchanged.

Before a later P336 action reads a candidate preamble, the host sends exactly
one run-bound protocol OPEN on the freshly rebound tty and then consumes a
finite byte-bounded sequence. Before exact OPEN_PARSED, that sequence may
contain only complete exact P336 banner plus stage-zero diagnostic preambles;
foreign, partial, malformed, excessive or out-of-order bytes stop the action.
This is synchronization, not a retry: only one OPEN, AUTH and command tuple may
be sent for one durable action intent.

Every P336 post-intent exit, including a parser or timeout exception, durably
retains bounded partial TX/RX and the exact audit stage before publishing its
successful or uncertain action result. An uncertain result immediately selects
the existing rollback owner and never reopens the lease. The finalized action
runner and activation identities are part of the fresh preparation/approval
closure; no runner may be invented after candidate transfer.

P336 adds no command, caller-selected shell, interactive PTY, file transfer,
persistent state, reboot, Download request, unattended control or non-boot
payload. This clause is H0-only until its changed execution closure receives
independent review and a fresh ready declaration; neither is live authority.

**P337 first-OPEN failure diagnostic.** P336 is consumed and grants no replay.
P337 keeps its successful wire exchange, fixed three-command catalog, 300-second
observation, boot-only transfer and exact rollback unchanged. Only when the
first framed OPEN read fails, the device may make one best-effort existing
type-0x86 diagnostic write at stage 3 with the bounded negative errno; a
complete but rejected OPEN uses stage 3/code 1. The original failure is then
returned. No retry, extra wait, command, action lease or new authority is added.
The raw receipt remains authoritative if this best-effort diagnostic is absent.
Fresh D1/D0 baselines, independent review, preparation and attended F1 approval
remain required; success still requires the complete intended proof and healthy
post-rollback return.

**P338 first-OPEN branch diagnostic.** P337 is consumed and grants no replay.
P338 keeps P337's successful session, three fixed commands, 300-second
observation, boot-only transfer, exact rollback, lease, and pre-arm label
unchanged. Its sole delta is one existing stage-3/type-`0x86` diagnostic code
for the first framed OPEN read: `0` header-read errno, `1` header validation,
`2` body-read errno, or `3` CRC rejection. The original read/validation errno
is returned unchanged; the diagnostic is best effort and never changes the
success path. No retry, wait, command, lease, shell, reconnect, or global gate
is added, and the branch receipt never proves candidate success or causality.

P338 uses a distinct overlay, run, schemas, source closure, predecessor
rejection, accepted/rejected receipt path, final-stock projection, and
pre-arm lease/label. Fresh D0 preparation may use exactly one retained P337
rollback baseline only when the complete raw `/proc/last_kmsg` is exactly
2,097,136 bytes with SHA-256
`64ac7a5b6666c4a21ce23effce2ec13015cdbdb985555300202ad46d8fe26a11`, and the
current P337 adapter classifies exactly one `c337f1e0a90b5e6d7c8a9b0c1d2e3f3b`
record at offset `1,657,825`, exact/long count `1`, foreign count `0`,
`candidate_success=false`, proof class `NO_PROOF_OBSERVER`, and integrity issue
`p320-stock-envelope-shape`. This exception proves only that fresh P338 is
absent, admits no P337 replay or standing authority, and expires on raw
identity drift or P338 candidate intent. If the fresh raw differs or rejects,
the separately authorized attended D1 fallback remains the only route; this
clause creates no P338 D0/D1 clone script. P338 still requires fresh
preparation, independent review, attended approval, and healthy exact
post-rollback return.

**P339 rejected-OPEN header capture.** P338 is consumed and grants no replay.
P339 keeps the P338 success path, three fixed commands, session/reconnect
bounds, 300-second observation, boot-only transfer, exact rollback, lease, and
timeouts unchanged. Stage 3 now separates header grammar (`1`) from a
grammar-valid but semantically rejected OPEN (`4`). For only those two
rejections, stages 4 through 7 may best-effort carry the rejected 16-byte
header as four little-endian 32-bit words using the existing type-`0x86`,
8-byte diagnostic payload. Partial word capture remains no-proof. No frame
type, payload width, retry, resynchronization, drain, wait, handshake, command,
shell, reconnect, or gate is added; the original failure is returned.

P339 uses a fresh run, overlay, schemas, source closure, artifact and observer
namespaces. Fresh D0 preparation may admit exactly the retained P338 rollback
raw only when it is 2,097,136 bytes with SHA-256
`321b03b24c488aa86f9cd2809dfdfdd2fa28fc8f5905183bbfe510cb1d58ab23`,
contains the P338 run ID exactly once at byte offset `1,658,754`, contains no
P339 run ID, and the P338 adapter reproduces
`P320_STOCK_WITNESS_BASE_SHAPE_FAILURE`, one foreign family, zero exact/long
records, `candidate_success=false`, `NO_PROOF_OBSERVER`, and sole integrity
issue `foreign-or-malformed-v2-long-record`. This narrow exception proves only
that fresh P339 is absent; it expires on raw drift or P339 candidate intent.
If it does not match, only the already reviewed attended D1 baseline fallback
may create a new boot before a new D0. No P339 D0/D1 clone is introduced.
P339 still requires independent review, fresh preparation, attended F1
approval, mandatory rollback, and healthy exact return.

**P340 initial failure-capture repair.** P339 is closed and consumed, with no
replay. P340 preserves its device success/failure behavior, fixed three-command
catalog, HMAC, session/reopen bounds, deadlines, boot-only AP and exact rollback;
only the candidate identity changes on the device. The host's real initial
reader may retain at most four existing 24-byte diagnostics at stages 4–7
after stage 3/code 1 or 4, using the same descriptor, raw writer and original
deadline. It then returns the original failure to the rejecting parser.
Partial, malformed or absent suffix bytes remain retained no-proof evidence.
The fresh P340 receipt accounts for stage 0 before the stage-3 reason, without
reinterpreting the consumed P339 result. No transmission, retry, reconnect,
resynchronization, timeout extension, new frame or command, caller shell,
standing authority, or new execution gate is added. P340 uses its own run,
overlay, schemas, source closure and preparation. Existing D0/D1 baseline
rules, independent review, fresh attended F1 approval, mandatory exact rollback
and healthy return still apply; this creates no campaign-specific D0/D1 clone.

**P341 host-first OPEN.** P340 is closed, consumed and never replayable. This
successor retains the same three authenticated sessions, fixed command tuple,
HMAC, deadlines, boot-only payload and mandatory exact rollback. After existing
exact-target raw-TTY setup, the host sends the existing run-bound OPEN once
before reading a banner. The device consumes and validates that OPEN before
its sole session banner and stage-0/OPEN_PARSED diagnostics. Initial, same-FD
and reopened session entries share this ordering; no second OPEN, new frame,
resynchronization scan, retry, longer deadline or caller command is introduced.
No-input waiting emits no unsolicited bytes. Any partial OPEN consumption
survives an error and cannot be mistaken for empty idle or replayed. Malformed
pre-banner diagnostics remain bounded raw NO_PROOF evidence; the observer must
not invent a banner to normalize them. Existing authentication and command
failures still stop. This ordinary F1 closes through exact rollback and health;
it does not activate later resident actions or transfer the P335/P336 lease.
New identity, source closure, artifact qualification, independent review,
fresh preparation and returned attended F1 approval are required. This clause
grants no device authority on its own.

**P342 bounded same-FD idle reuse.** P341 is closed and consumed, never replayable.
A fresh P342 identity preserves its device listener, host-first OPEN, HMAC,
fixed three-command tuple, 30-second per-session bound, exact endpoint guards,
boot-only AP and mandatory Magisk rollback. The initial observer runs two
complete same-FD sessions, waits at least 120 seconds without transmission on
that same open descriptor, runs a third same-FD session, and closes/reopens
once for the fourth session: twelve fixed command executions total.
The idle phase may occupy at most 180 seconds, reserving four 30-second
exchange windows within the existing 300-second observation bound; it never
extends that outer bound. Unexpected idle bytes are retained and stop the
trial rather than being drained or treated as a synchronization preamble.
Any failure retains partial session/idle evidence and takes ordinary rollback;
no session, command, OPEN, descriptor reopen or uncertain action is retried.
Success requires the exact four-session proof and same-FD idle timing receipt
bound together in the immutable candidate receipt, followed by exact rollback
and healthy rooted FYG8 return. This activates no later-action lease, generic
shell, interactive PTY, persistent state or autonomous mode control.
P342's exact `live-state.json` uses the existing terminal-result 64-KiB bound
because four sessions plus decoded supplemental state exceed 32 KiB; its
fields and capture limits are unchanged and other journal records stay 32 KiB.
Fresh artifact qualification, changed-closure independent review, ordinary D0
preparation and returned attended F1 approval remain required. The existing
D1 baseline fallback is used only when needed; no new D0/D1 wrapper is created.
This clause alone grants no live authority.

**P343 named read-only exploration.** P342 is CLOSED and consumed. This fresh
successor retains host-first OPEN, HMAC, raw capture, exact current-boot binding,
initial four-session/120-second idle proof and boot-only Magisk rollback. It
reuses the P335 attended current-boot lease journal in a distinct P343 namespace:
at most one hour and sixteen later named sessions, with no renewal or replay.
The initial proof still executes the original identity/kernel/nonce tuple.
After that proof, `OBSERVED` and `candidate_boot_ready` must be durable before
lease/guard publication; successful guard release is required before returning
an active intermediate lease. This is not F1 closure or Android healthy state.

Each later session executes exactly `id`, one selected query, then the run-bound
nonce command through the existing BusyBox child. The only query names and
bytes are `kernel` (`/bin/busybox uname -a`), `processes` (`/bin/busybox ps`),
`mounts` (`/bin/busybox head -c 8192 /proc/mounts`), `memory`
(`/bin/busybox head -c 4096 /proc/meminfo`), and `usb-state`
(`/bin/busybox cat /sys/class/udc/a600000.dwc3/state`). Both host catalog and
device sequence-4 validator use this closed list. Sequence 3 and 5 keep their
exact identity/nonce checks; framing and HMAC are unchanged. No caller shell,
path, executable, environment, write, package, service, mount, persistent file,
interactive PTY, reboot or Download action is exposed by this catalog.

The action runner uses the ordinary prepared manifest/run address and accepts
only a named action. The fresh F1 execution closure binds its code, catalog,
lease core, observer, key and recovery owner; no second activation JSON or
per-query human approval is required within that attended exact lease.
Target/transaction locks serialize actions with recovery. Before every effect
the runner revalidates lease/target/topology/key, durably records one intent,
and authenticates the unchanged per-boot ID before the first EXEC. One session
has at most 30 seconds, clamped to remaining lease time immediately before
OPEN; existing command/output bounds remain. Partial RX/TX and failure details
are preserved privately. Uncertain intent, failed authentication/command,
expiry, drift, attendance loss or operator stop permits only the already bound
rollback. This does not establish automatic recovery if the listener fails.

P343 exploration PASS requires initial proof, at least one completed named
action and no unresolved/failed action, exact rollback and final rooted FYG8
health. The close record derives the bounded action summary from the retained
lease and result receipts; initial USB proof and later exploration proof remain
separate. No action or only unproved actions yields NO_PROOF after healthy
rollback, never replay. The current P342 trial remains consumed. P343 needs
independent review of this changed closure, qualified artifacts, fresh ordinary
preparation and returned attended F1 approval before execution. Until those
steps complete this capability is H0 only.

**P344 result-publication successor.** Consumed P343 remains CLOSED and NO_PROOF.
P344 retains the exact P343 five-query catalog, host-first authentication,
four-session/120-second initial idle proof, one-hour/sixteen-action attended
lease, timeouts, boot-only payload and mandatory exact rollback. The device
behavior changes only by fresh identity; the host reads CommandResult.term_signal
into the unchanged signal_number result field. P344 receives separate run,
schema, source, artifact, action/lease and journal namespaces. Actual observer
arming and action-result publication/summary regressions, changed-closure review,
qualified artifacts, ordinary fresh preparation and returned attended approval
remain required. No replay, new control/shell, baseline exception or new D0/D1
wrapper is introduced; the existing D1 fallback is used only if needed.

**P345 bounded read-only shell qualification.** P344 remains
CLOSED, consumed and never replayable. This first successor qualifies free
ash syntax within a fixed read-only child view, not a resident lease or
unrestricted root shell. The only live command sequence is the immutable
five-session qualification in the reviewed P345 observer: child read/write-denial
canary, expected nonzero exit, timeout, authenticated cancel, and successful
pipeline/substitution afterward. Every session retains fixed parent identity
and fresh-run nonce witnesses. It uses one exact already-bound tty descriptor,
five distinct authenticated challenges and one unchanged authenticated per-boot
identity; no reopen, retry, resynchronization or later caller command is allowed.

The five-session limit is enforced by the reviewed host qualification path,
not a device-side hard counter. After the fifth session the host probes for
unexpected trailing bytes, closes its descriptor and proceeds to mandatory
rollback without sending another command. The inherited device listener remains
available while awaiting physical rollback; that capability grants no sixth
session, later sender/key use, lease or standing command authority. This process
does not claim that the device listener terminates after five sessions.

Only sequence 4 enters the fixed child mount namespace. It makes mount
propagation private, constructs a volatile tmpfs view containing only static
BusyBox and the reviewed finite proc/sys text snapshots, remounts that view and
BusyBox read-only, chroots, closes extra descriptors, drops groups/UID/GID and
capabilities, applies resource limits and no_new_privs, then installs the
reviewed inherited syscall filter. Setup failure exits before ash and retains
a bounded error marker. No device nodes, storage mounts, proc process/fd/root
paths, network or control channel enter the view. The parent PID1/USB owner is
not placed inside this child restriction. Shell text validation is not the
write barrier, and this lane makes no kernel-exploit resistance claim.

S328 framing and existing authentication remain; type 5 is an authenticated
sequence-4 CANCEL bound to current run and session challenge. EXIT followed by
type 0x88 ACK0 proves active cancellation; ACK1 identifies already-completed
work without repeating a device effect. A normal nonzero exit, timeout,
truncation or cancellation is a command outcome only with proved cleanup and
terminal framing. Missing terminal, invalid/partial cancellation, identity
drift or transport uncertainty stops qualification. Existing 15-second child,
128-KiB output and 300-second outer observation bounds remain. This first
qualification requires its exact expected outcomes, not merely absence of a
transport error, and no expected failure is relabeled successful execution.

Complete qualification still requires ordinary boot-only exact Magisk rollback
and final rooted FYG8 health. It opens no later-action lease, interactive PTY,
persistent installation, reboot/Download shell command, autonomous recovery or
standing shell authority. Fresh source/artifact qualification, independent
changed-boundary review, ordinary preparation, and returned attended F1
approval are required. This capability is active only for the exact independently
reviewed P345 execution closure and its published ready declaration. Without
both matching inputs it remains H0; neither source tests nor this definition
alone authorizes a device action or waives the fresh attended F1 approval.

**P346 numeric-witness and result-projection successor.** P345 is CLOSED,
healthy, consumed and never replayable. P346 retains its five same-descriptor
qualification sessions, fixed read-only child view/filter, authenticated CANCEL,
expected exit-7/timeout/cancel/pipeline outcomes, deadlines, output bounds,
boot-only payload and mandatory exact Magisk rollback. It requests numeric
child UID/GID separately, shares numeric parent-ID validation, stores JSON-stable
metadata and uses its own receipt projection. Fixed P345 canary/setup/CANCEL
markers are inherited protocol vocabulary; fresh run ID, banner, authenticated
nonce witnesses, Image/init join, schemas and execution closure identify P346.
No syscall, command authority, lease, reopen, retry or recovery scope is added.
P344 remains the pinned packaging construction base; consumed P345 artifacts,
journals and outcomes are preserved. Successor artifact validation is read-only;
only fresh build creation publishes its new result. Independent changed-closure
review, fresh source/artifact qualification, matching raw-first audit and ready
bindings, ordinary D0 preparation and returned attended F1 approval remain
required. Existing attended normal-reboot D1 may be used only when needed for
the baseline under current operator authority; no new D0/D1 runner or baseline
exception is introduced. This clause alone grants no device authority.

**P347 output-integrity and timing successor.** P345 and P346 remain CLOSED,
consumed and never replayable. P347 keeps their five same-descriptor sessions,
fixed read-only child view, UID/GID/capability drops, resource limits, authenticated
CANCEL, 15-second child and 300-second observation bounds, 128-KiB output bound,
boot-only payload and mandatory exact Magisk rollback. Parent sequence-3/5
identity and nonce witnesses remain fixed. It opens no later shell lease.

Before child exec, P347 makes only the new output pipe's write end blocking;
the parent read end remains nonblocking, so existing timeout/cancel/cleanup
ownership is unchanged. An output setup failure exits 126. Sequence 4 ash
uses pipefail; expected-denial control flow is retained and set-e is not added.
The versioned read-only child adds only AArch64 clock_nanosleep with clock ID
CLOCK_REALTIME and flags 0, matching the fixed BusyBox relative sleep call.
Other clock IDs/flags and the inherited default-denied surface remain denied.
This permits no clock setting, sysinfo, limit mutation, new filesystem view,
process escape, network or device control. Consumed P345/P346 child sources
are not repinned or replaced.

The qualification remains exactly five sessions and fifteen commands. Canary
snapshot/ID reads now check command status. The final session checks a nonempty
fixed version snapshot via checked substitution, then exactly 120,000 bytes of
bounded awk output followed by the existing pipeline marker. The observer
requires the full expected output bytes and a timeout duration of at least
15 seconds, including retained-receipt reopening. This qualifies the named
snapshot reads and fixed witnesses, not arbitrary BusyBox applets' semantic
correctness; unsupported ulimit/uptime/free remain outside this proof.

P347 needs its own fresh run/banner, Image/init/AP and complete executed-source
closure, independently reviewed implementation and raw-first path, fresh
artifact/static/ready qualification, ordinary D0 preparation and separately
returned attended F1 approval. Existing attended ordinary-reboot D1 may be used
only when needed for baseline preparation under current operator authority;
no new D0/D1 runner, baseline exception, retry, reopen, recovery deviation or
standing authority is introduced. This capability grants no device authority
without those matching inputs.

**P348 attended retained read-only shell.** P344 and P347 remain CLOSED,
consumed and never replayable. This successor retains P347's isolated read-only
child view, resource/UID/GID/capability restrictions, syscall filter, blocking
output writer, pipefail, 15-second child limit and 128-KiB output cap. It adds
an attended current-boot shell lease with at most one hour and 16 later actions.
It does not activate an unattended session, interactive PTY, persistent install,
writable filesystem, network, new syscall, reboot or Download shell command.

Initial qualification uses the five P347 semantic cases on the fresh candidate
and one further fixed witness after exactly one clean tty close/open and at
least 120 seconds idle, inside the 300-second observer bound: six sessions,
18 commands, fresh challenges and one unchanged authenticated per-boot identity.
The first five use one descriptor; the sixth verifies clean reopen. There is no
retry, resynchronization or extra session after uncertainty. Accepted observation,
OBSERVED and candidate_boot_ready precede durable no-clobber lease/guard
publication and verified observer-guard release. ACTIVE is an intermediate F1
state, not Android health or terminal success. Publication/release failure
permits only the already bound exact rollback.

The reviewed host action runner accepts one private file containing 1–1,023
bytes under the existing shell encoding rules, binds the exact bytes to a
one-shot intent, and sends only the parent identity / selected isolated shell /
fixed nonce tuple. Each action creates a fresh child; it transfers no shell
variables, working directory or background jobs to the next action. No caller
executable, environment, transport or recovery parameter is accepted. Under
existing target/transaction locks it revalidates source, lease, target, topology,
key, candidate, host clock/boot epoch and recovery owner, opens the exact tty
once and proves unchanged authenticated device boot before EXEC. The full
30-second session window must remain before OPEN; its deadline never exceeds
lease expiry. Host reboot/suspend, pending intent, malformed receipt, drift,
expiry, budget exhaustion or attendance loss blocks further actions and requires
rollback. Neither a new invocation nor a reporting cut renews or replays work.

A complete nonzero result (except 126/127), timeout, bounded truncation or
cancel may permit another action only after valid cleanup, terminal frames and
final nonce witness. Preserve actual outcome, flags, code, signal and output
length; protocol completion is not command success. Codes 126/127 remain
stop-and-recover under the inherited ambiguous exec-failure encoding. CANCEL
is sent once by the existing descriptor owner; ACK0 and ACK1 retain their
active/already-completed meanings. Missing or inconsistent terminal evidence
is uncertainty, never a retry. Terminal raw/result evidence survives expiry or
receipt failure without rewriting consumed action intent or effect history.

P348 reuses the existing physical Download and exact Magisk boot-only rollback
owner. Malformed shell evidence must not prevent that already bound recovery.
Final capability PASS requires initial qualification, the reviewed later-action
acceptance sequence with exact outcomes and no unresolved action, exact rollback
and final rooted FYG8 health. Functional proof and rollback health remain separate;
short observed use does not prove an hour of residency or arbitrary applet meaning.

This capability is H0-only until its actual execution-critical closure, raw-first
paths, host clock and retained-receipt consumers pass independent review and
fresh artifact/static/ready qualification. Ordinary current D0 preparation and
separately returned attended F1 approval remain mandatory. Existing ordinary
reboot D1 may be used only when needed for fresh baseline preparation under
current operator authorization. No new D0/D1 profile or baseline exception is
introduced. This clause by itself grants no device effect or later shell use.

**P349 attended current-boot RAM workspace and hour witness.** P348 remains
CLOSED and consumed. P349 retains the preceding P348 attendance, exact binding,
locks, source closure, initial six-session/120-second reopen qualification,
authentication, no-replay, stop, raw evidence and physical Download/Magisk
rollback requirements. Its separate fresh candidate, schemas and journals never
reuse a consumed lease. The only child filesystem expansion is a fixed `/work`
bind of a parent-created tmpfs, bounded to 8 MiB and 256 inodes, owned by
UID/GID 65534 with nosuid/nodev. Parent setup occurs once before the listener;
the parent never traverses or processes caller-created workspace paths. A
fresh isolated child can create/read/modify/remove files and invoke the fixed
BusyBox interpreter on a workspace script. Files persist only within this
candidate boot; shell variables, cwd and background jobs do not persist.

The rest of the child view remains read-only: one fixed BusyBox and the six
bounded snapshots. The inherited privilege drop, closed inherited descriptors,
no capabilities, no_new_privs, private mount namespace and default-deny seccomp
remain required. The target filter adds write flags on openat and mkdirat,
unlinkat and renameat only within that isolated filesystem. No privileged
shell, device node, network, persistent storage, mount, reboot, separate
executable-upload API or recovery command is added. Only fixed BusyBox script
execution is qualified; arbitrary ELF execution is unqualified. The executable
workspace is still subject to the same privilege and syscall limits. Resource bounds remain
15 seconds per child, 128 KiB output, 64 KiB per file, 64 MiB address space,
16 processes and 32 descriptors. Capacity exhaustion/cleanup is host-qualified;
that evidence is not an on-device capacity claim.

The attended lease is at most 3,900 seconds with 16 later actions. Every action
still needs its complete 30-second window before expiry. Functional PASS
requires the ordered checked-snapshot, RAM create, cross-child modify, script
execution, exit-7, timeout, cancel and post-cancel success roles, followed by
20/40/60-minute workspace witnesses. The durable action intent for each timed
witness must be issued at least 1,200/2,400/3,600 seconds after durable lease
opening. Reopened authenticated raw frames must prove each command and the same
device boot. Late result publication, lease duration, wall-clock scheduling or
rollback health alone cannot prove the hour. This proves sampled residency and
workspace retention, not continuous monitoring or arbitrary applet behavior.
Exact rollback and final rooted FYG8 health remain separate required evidence.

P349 is H0-only until its execution-critical closure and higher-precedence
interactions pass independent review and fresh artifact/static/ready
qualification. Current D0 preparation, any needed already-authorized ordinary
reboot D1, and separately returned attended F1 approval remain required. This
clause grants no unattended use or device effect by itself.

**P350 attended fixed display observation.** This is a separate boot-only
successor; P349 remains unchanged. Keep the existing 73-module USB plan and
indices. After authentication, one exact `P350_DISPLAY_ONCE` command may run
the fixed packaged renderer, with its boot-local slot consumed before fork.
It loads only the nine hash-bound display additions in their checked dependency
order, using current primary-panel command-line parameters. No arbitrary root
command, secondary panel, module replay/unload or later-action lease is added.
The parent retains the existing pipe, cancellation and failure handling; only
this command has a 60-second bound. A blocked kernel call still requires the
ordinary attended physical Download recovery; killing a process is not recovery.

The fixed child creates only the primary DRM character node under checked RAM
`/dev`, opens DRM master, then drops to UID/GID 65534 with no capabilities. It
uses two WC buffers and ten counter frames, reusing a buffer only after a matching
flip-completion event. It refuses conflicting scanout and completes a disable
before normal cleanup. Persistent storage, diagnostic sysfs, POC erase/program and arbitrary device-node
access are outside this path. The retained automatic gamma-read sequence is
separately reviewed; common POC and DDI-SPI implementations are excluded. The reduced module's
existing diagnostic guards and reviewed source/config identities remain bound.

Qualification is three same-descriptor authenticated sessions: a read-only USB
witness, the fixed display command, then a read-only USB witness on the same boot.
There is no idle/reopen campaign or repeated shell qualification. The host bound
is 150 seconds, with 75 seconds for the display session. Machine PASS establishes
completed DRM events and USB return; visible run-ID/counter output needs operator
corroboration and must remain UNPROVED without it. Exact rollback and final FYG8
health are mandatory independently of display success.

P350 remains H0-only until independent execution review and fresh artifact/static
qualification pass. Fresh connected preparation and the ordinary returned
attended F1 approval are still required. This clause grants no device effect.

**P351 attended fixed display successor.** P350 is consumed and never replayable.
P351 keeps its three authenticated same-descriptor USB/display/USB sessions,
60-second child bound, 75-second display-session bound, 150-second host bound,
privilege drop, fixed DRM operations and mandatory attended physical recovery.
Only the fresh `P351_DISPLAY_ONCE` literal selects the one-shot child; no lease,
arbitrary root command or additional display attempt is authorized.

The unchanged 73-module USB plan precedes twelve exact display additions:
`pmic_class`, S2DOS05, the reviewed GPIO-I2C module restricted by platform ID to
the root `i2c@50` bus, then the existing nine additions. The generic GPIO-I2C
module is not substitutable. Its no-`reg`, pins 20/21, index 50, sole S2DOS05
child/address and reviewed initialization properties remain exact. No
`driver_override` write is permitted. All applicable merged DTs must pass the
source-bound display supplier, device-creation and driver-consumed prerequisite
closure; a symbol/CRC graph alone is insufficient.

After each insertion has completed once, the child may poll for at most 15
seconds with 200-ms intervals. It reads only the two exact driver symlinks,
bounded cached regulator `name` attributes and primary DRM `dev` attribute;
two further fixed display-driver symlinks are diagnostic only. Success requires
two fresh complete snapshots of the expected bus/PMIC bindings, four unique
panel power-regulator names and DRM `226:0`. Previous snapshots cannot fill
missing fields. This is prerequisite observation, not proof that all probes or
frame operations will succeed. The parent retains its total deadline and
physical recovery ownership if a kernel call blocks.

Only a failure during that post-insertion readiness phase permits one fixed
`syslog(SYSLOG_ACTION_READ_ALL, ..., 32768)` attempt before privilege drop. It
does not clear or consume the log and is never retried, including on error.
The last readiness snapshot and bounded tail are emitted through the existing
private framed capture; no raw log is tracked. Tail coverage cannot establish
absence of earlier errors. Module-insertion and later DRM failures do not arm
this diagnostic. This fixed exception does not authorize diagnostic sysfs,
`READ_CLEAR`, arbitrary logs, additional module loading or new recovery actions.

The renderer uses the checked white-background layout with a large counter,
green status block and run ID. Machine qualification requires twelve ordered
insertions, the fresh readiness record, ten completed flips, completed disable
and same-boot USB return. Visible panel output remains UNPROVED without operator
corroboration. P351 is H0-only until independent changed-closure review and fresh
artifact/static qualification pass; connected preparation and the ordinary
returned attended F1 approval remain separate requirements.

**P352 attended source-bound display successor.** P351 is consumed and never
replayable. P352 retains its twelve exact additions, fresh readiness observation,
white layout, three same-descriptor sessions, one-shot slot, privilege drop,
60/75/150-second bounds, and mandatory attended physical recovery. Only the
fresh `P352_DISPLAY_ONCE` literal selects the fixed child. There is no later lease.

The renderer requires the exact vendor DRM name `msm_drm`. It selects exactly
one returned `1080x2340x30xcmdHS` mode with the source-derived full timing tuple
in `s22plus_fyg8_display_kms_contract_h0.py`; absence, duplicate or changed timing
stops the attempt. Preferred-mode metadata is retained from the returned mode.
The distinct 30Hz PHS timing is not a fallback. TEST_ONLY, flip binding,
competing-state refusal and completed disable requirements remain unchanged.

Failures may additionally emit only bounded cached ioctl context: numeric
operation/object identifiers, fixed requested property names, up to 31
driver-name bytes encoded as hex and at most sixteen mode summaries. This
performs no new device read and does not arm the readiness-only kernel-log
diagnostic for later failures. Successful output qualification remains exact.

The source-derived nominal mode fixture covers all applicable stock DT merges;
it does not prove the runtime mode filter, panel output or recovery. P352 remains
H0-only until independent changed-closure review and fresh artifact/static
qualification pass. Connected preparation and the ordinary returned attended
F1 approval remain separate requirements. This clause grants no device effect.

If a P327, P328, P329, P330, P331, P332, P333, P334, P335, P336, P337, P338, P339, P340, P341, P342, P343, P344, P345, P346, P347, P348, P349, P350, P351, or P352 candidate transfer occurs, the same
reporting unit that confirms `CAMPAIGN_CLOSED` must append exactly one matching
`s22plus-fyg8-p327`, `s22plus-fyg8-p328`, `s22plus-fyg8-p329`,
`s22plus-fyg8-p330`, `s22plus-fyg8-p331`, `s22plus-fyg8-p332`,
`s22plus-fyg8-p333`, `s22plus-fyg8-p334`, `s22plus-fyg8-p335`, `s22plus-fyg8-p336`, `s22plus-fyg8-p337`, `s22plus-fyg8-p338`, `s22plus-fyg8-p339`, `s22plus-fyg8-p340`, `s22plus-fyg8-p341`, `s22plus-fyg8-p342`, `s22plus-fyg8-p343`, `s22plus-fyg8-p344`, `s22plus-fyg8-p345`, `s22plus-fyg8-p346`, `s22plus-fyg8-p347`, `s22plus-fyg8-p348`, `s22plus-fyg8-p349`, `s22plus-fyg8-p350`, `s22plus-fyg8-p351`, or `s22plus-fyg8-p352` F1 closure row derived from that
run's retained journal and result. This is post-terminal
bookkeeping, not a pre-execution gate; no F1 row is written before the effect.

Process-v2 evidence must retain the exact endpoint identity, topology, host
controller/device path, and immutable raw-snapshot receipt at approved Download
start and candidate-observer closure. Before rollback transfer it must retain a
fresh exact Download/rollback binding with the same fields. A normal unchanged
path is `rollback_bound_exact`: it is a fresh revalidation of the original
predeclared rollback authority and does not require a new independent recovery
review. A missing, truncated, or unreadable snapshot is an observer failure,
not proof of path continuity.

Classification is phase-specific. A non-exact Download-start binding is a
pre-session stop and has no consumed-run proof class. Candidate-end drift is
`NO_PROOF_EXPERIMENT_PRECONDITION`, but an exact, complete same-path observer
window with no host endpoint remains eligible for the experiment's declared
host-silent device-result classification. Rollback-endpoint drift or absence
parks recovery and never changes an already retained experiment result.

For a P3.18 timing successor, “no host event” is not a default value. It is
admissible only when an exact DWC3 event latch was registered, its write-once
gate was read back before the sole UDC bind, bit 7 proves that no qualifying
host event linearized before that gate transition, the retained gate-write
timestamp is no later than the diagnostic pre sample on the same monotonic
clock, and the complete candidate-end host receipt has no endpoint. The
module-enforced `latch_install <= gate_write` order remains a structural
consistency check and diagnostic value; it is not causal evidence. An
endpoint-present receipt combined with the no-event mask `0xef` is an observer
contradiction. An incomplete or unavailable host receipt is an observer
failure and can never support a no-event claim. A latched host event under
mask `0xff` combined with a complete no-endpoint receipt is the distinct
`DEVICE_RESULT_DWC3_HOST_EVENT_NO_ENDPOINT`, not a host-silent result. A
missing install, gate-write, or pre-gate-absence bit means “host event not
observable,” never “no host event,” and cannot support a MUX ordering claim.
Legacy masks `0x6f` and `0x7f` therefore have no causal authority. Envelope-v4
`TIME_MASK=0xff` allocates all eight validity bits; another witness needs a new byte or reviewed Envelope-v5, never reinterpretation.

The P3.18 `gate_write` sample is a module-owned, write-once pre-UDC gate
timestamp from the same `ktime_get_ns()` clock as latch installation. It is
not gadget exposure or configfs bind time. The latch and gate transition share
one atomic state so a qualifying event cannot race the transition and leave a
false zero count. A qualified runtime must read back that exact gate marker
and only then perform its sole configfs UDC bind; the existing
gadget-evaluability witness must prove that bind completed. Until the producer,
pre-gate count, readback-before-bind order, and sole-bind property are
source-bound together, the gate sample and every derived no-event claim are
unavailable.

A drifted topology does not authorize rollback against the new path. Mandatory
rollback remains required, but the run parks without new device effects until
a bounded, independently reviewed recovery-only path establishes
`recovery_rebound_exact` for one exact current rollback endpoint under a new
immutable recovery binding ID. Only then may the predeclared exact rollback
resume from durable journal state. The new binding may name a different
physical path; it is recovery authority only and does not retroactively
validate candidate attribution. `rollback_bound_exact` and
`recovery_rebound_exact` are distinct authority states; the latter cannot be
inferred from an ordinary fresh rollback revalidation. Candidate replay
remains forbidden.

- Use Odin with ordinary regular `.tar.md5` paths. Each candidate and rollback
  AP must contain exactly one regular `boot.img.lz4` and no forbidden member.
- Process-v2 requires a new immutable manifest, exact D0, one fresh
  candidate/rollback binding, and the fresh exact approval required after
  Fast-Loop retirement. No retired trial clause waives per-candidate approval.
- One candidate intent covers only that attempt and its exact rollback.
  Never replay it. Once candidate execution begins, rollback does not wait.
- Journal before invoking Odin and after every state transition. Recover only
  from durable journal state.
- A host rejection or local parser failure that is positively proven to occur
  before Odin begins or reports a device session is a pre-session H0 failure,
  not a candidate attempt. Apply the bounded Rule-7 rule above. Any repaired
  execution-critical closure requires a new exact legacy-runner binding before
  live use. Tool creation alone is not proof that a device session started.
- Once Odin identifies or contacts the device, Download handoff starts, or any
  device command is sent, an unexplained failure is an immediate stop. Only the
  predeclared exact rollback path may continue; the candidate may not.
- Candidate boot or Odin success alone is not PASS. PASS requires the intended
  bounded observation, exact rollback, and verified healthy stock terminal
  state.

## Evidence

Routine D0/D1 evidence is proportional; F1 retains a structured result, journal,
private raw logs, exact transfers/no-replay, rollback, canonical order, and health:
`live_session_start -> candidate_flash_start -> candidate_flash_done -> candidate_boot_ready -> rollback_flash_start -> rollback_flash_done -> rollback_boot_ready -> live_session_end`.


**Raw-first observer preservation.** Every S22+ D0/F1 device-observation
subprocess output or endpoint byte stream used by a parser or classifier is bounded, no-clobber, mode-0400 and
file/directory-fsynced before parsing; parsers accept only its immutable handle, and an active-closure source audit rejects bypasses. The permanent
`S22PLUS_D0_F1_RAW_FIRST_OBSERVER_PRESERVATION` boundary blocks the P3.03/P3.19
`WRITE_AFTER_PARSE_DEVICE_EVIDENCE_LOSS` hazard, has no expiry, and requires review when acquisition, handle ABI, parser signature, or active observer reachability changes. Normal boot remains operator observation, not formal proof.

## Review and Change Control

- Changes to this binding contract require one independent safety review.
- Review must check that boot-only, rollback availability, no replay, target
  isolation, post-session immediate stop, and private-evidence rules remain
  intact.
- Re-review execution machinery only when its execution-critical closure or
  hazard class changes. A new candidate with unchanged machinery needs fresh
  qualification and any legacy runner binding, not a new policy ladder.
- This target contract may be made more precise without copying current
  campaign state into it. Put changing frontier and authority state in
  `GOAL.md`.
