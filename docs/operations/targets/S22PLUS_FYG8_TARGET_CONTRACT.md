# S22+ FYG8 Binding Target Contract

Status: **BINDING**

This contract specializes `AGENTS.md` for the attended Samsung Galaxy S22+
FYG8 target `SM-S906N` / `g0q` / `S906NKSS7FYG8`. It is not authority for any
other model, firmware, target profile, or connected device.

`GOAL.md` owns the current experimental state. This file alone neither arms the
target nor opens a D0/D1/F1 action. The common Fast-Loop trial is retired; it
grants no standing D0, attended autonomy, or per-candidate approval waiver.

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
- Never repair repository files while Full-LTO is running. Stop the build and
  report the proposed edit first.

### S22+ Rule 7: bounded pre-session repair

A material failure is identified by its failed invariant, input/producer
contract, and causal mechanism, not merely by exception spelling or line
number.

Before any connected device command is sent and before a transfer tool begins
or reports a device session:

1. The first novel material host-only failure stops that invocation, preserves
   its evidence, and permits one bounded H0 diagnosis, one scoped repair, and
   one corrected execution of the failed bounded unit.
2. The repair must cite the observed input or fixture, the exact changed
   closure, and why candidate identity is preserved or invalidated. It must run
   focused validation before the corrected execution.
3. The same material failure a second time stops the line of work. Renaming an
   exception, moving the failure, or changing only its representation does not
   make it novel.
4. Distinct novel failures receive separate signatures, but this rule never
   authorizes retry-until-pass loops, speculative repeated builds, or a device
   action.
5. Every step intended for a later live window must first be exercised outside
   that window with the real input or, when live input cannot exist yet, a
   captured representative fixture. Do not make attended live
   execution the first execution of host code.

H0 request hashes and re-entry packets are evidence bindings, not device
authority. Do not make them stricter than this rule by default. A particular
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

If a P327, P328, P329, P330, P331, P332, P333, P334, P335, P336, P337, or P338 candidate transfer occurs, the same
reporting unit that confirms `CAMPAIGN_CLOSED` must append exactly one matching
`s22plus-fyg8-p327`, `s22plus-fyg8-p328`, `s22plus-fyg8-p329`,
`s22plus-fyg8-p330`, `s22plus-fyg8-p331`, `s22plus-fyg8-p332`,
`s22plus-fyg8-p333`, `s22plus-fyg8-p334`, `s22plus-fyg8-p335`, `s22plus-fyg8-p336`, `s22plus-fyg8-p337`, or `s22plus-fyg8-p338` F1 closure row derived from that
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
