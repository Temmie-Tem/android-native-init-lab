# Common device-action contract details

Status: **BINDING — incorporated into AGENTS.md at common-contract precedence.**

These sections retain the complete Revision 8 device boundaries, tier definitions,
and delegations. They are not an archive, a lower-priority runbook, or an
activation. Root AGENTS.md binds this file by SHA-256. Changes require updating
that pin and the existing independent review; a stale root pin grants no changed
authority. Interpret paths below relative to the repository root, as in the
original contract. Cross-references such as "boundary 1", "below", and "this
revision" preserve their original scope; no consumed action is renewed.

Read the applicable tier/delegation and any invoked exception before a device
action. A summary in root AGENTS.md does not replace these exact conditions.
Keep target-contract activation and current runner binding separate from the
permission to perform host-only work.

## Permanent Device Safety Boundaries

1. Work only on an explicitly identified operator-owned device. Device effects
   require attendance except the exact A90 resident D1 lane, an exact S20+
   bounded autonomous-research lane, the S22+ pre-F1 autonomous lane, or the
   conditional boot-only F1 lane below, or the single S20+ PMSG ordinary-reboot
   transaction expressly delegated below, or a reviewed bounded machine-controlled
   D1 lane defined below, each separately activated by its
   binding target contract. F1 remains attended outside that exact activated
   lane, and authority never transfers between targets.
2. The only partition payload permitted by the ordinary process is **boot**.
   Never send a partition image, raw block write, or flashing operation to
   recovery, vendor_boot, DTBO, vbmeta, vbmeta_system, BL, CP, CSC, super,
   userdata, persist, EFS, sec_efs, RPMB, keymaster, modem, bootloader, or any
   other partition. An exact reviewed D1 action performed through normal
   Android Package Manager or shared-user-storage APIs is an OS-mediated data
   write, not a partition payload; it is permitted only within the closed
   package/file staging rules below and never authorizes block or filesystem
   access to a partition mount outside that normal API.
   One narrow S20+ recovery-canary T0 exception is activated only by the exact
   S20+ target contract under the `F2` tier below. It is limited to one
   SHA-pinned candidate and one SHA-pinned exact-stock rollback, each an Odin
   AP with exactly one regular `recovery.img.lz4` member. It transfers no
   authority to TWRP T1, a caller artifact/path/partition, another target, or
   another partition.
   Its first candidate intent permanently consumes that candidate. This
   delegation grants nothing while any common, risk-tier, target-contract,
   runner, hostile-test, independent-review, mechanical-activation, fresh
   preparation, approval, attendance, or physical-recovery gate is absent.
   A second exact S20+ TWRP T1 exception is activated only by the exact S20+
   target contract under `F2-T1`. It is limited to candidate AP SHA-256
   `3ed8498243ff09399ffd93fa3b0e90044a3cfe1709b7204dac53fe190647260f`
   and the same exact-stock rollback AP SHA-256
   `ac9745b642c7fbd950d988671f707e47d58f8e2092464b27a37bede2267d7157`,
   each with exactly one `recovery.img.lz4`. It gains no authority until its
   separate profile, connected owner, hostile tests, target section, risk-tier
   section, independent review, and mechanical activation all close together.
   Preparation must mechanically revalidate the exact completed T0 terminal,
   its source closure, both proved transfers, final stock digest, and current
   serial continuity; documentation of those facts is not a substitute.
   A third exact S20+ TWRP T2 exception is activated only by the exact S20+
   target contract under `F2-T2`. It is limited to candidate AP SHA-256
   `6d10b3154f2e899ee64305f3f3279d7d5243eb917f1fedb413b8f88d22ec88cb`
   and the same exact-stock rollback AP SHA-256
   `ac9745b642c7fbd950d988671f707e47d58f8e2092464b27a37bede2267d7157`,
   each with exactly one `recovery.img.lz4`. Preparation must rederive the
   completed T1 `NO_PROOF` terminal, both T1 transfers, final stock digest,
   exact private T1 observer receipt and bytes, its sole `mtp,adb` distinction,
   and current serial continuity. T1 remains `NO_PROOF`; its evidence grants
   no T2 command before separate review and mechanical activation.
3. Never use raw host `dd`, fastboot outside the exact S20+ census and
   boot-support exceptions below, partition-table actions, qdl/Sahara/Firehose, RAM dump, EUD/UART
   writes, fuse/QFPROM actions, format operations, or an unreviewed panic/RDX
   path.
   One narrow S20+ classic-fastboot census exception may be activated only by
   the exact S20+ target contract. It permits the SHA-pinned official Google
   `fastboot` tool to send exactly four fixed read-only requests, in this order:
   `getvar product`, `getvar is-userspace`, `getvar version-bootloader`, and
   `getvar max-download-size`. The endpoint must be the sole `18d1:d00d`
   `ff/42/03` interface on the freshly prepared S20+ physical topology, with
   exact serial continuity from healthy Android and an attended operator-entered
   bootloader. An unsupported variable is evidence and is never replaced by a
   wider query. The exception forbids `getvar all`, every caller-selected
   variable/tool/serial/path, every download or payload phase, and every `boot`,
   `flash`, `erase`, `reboot`, `oem`, `flashing`, `set_active`, `fetch`, lock, or
   unlock command. Return is only the physical on-screen `START` selection
   followed by fresh exact Android health. It grants no evidence or authority
   for temporary boot support, another fastboot endpoint, or another target.
   It grants no later invocation except one separately reviewed replacement
   ordinal explicitly activated by the exact S20+ target contract. That
   replacement must mechanically bind a pinned predecessor terminal proving
   zero fastboot entry observation, zero query intent, fresh healthy Android
   return, and an absent shared guard; it retains the identical four requests
   and permits no third ordinal.
   One narrow S20+ retained-T2 volatile-fastbootd census exception may be
   activated only by the exact S20+ target contract. It starts in the already
   proved retained T2 recovery and permits one fixed no-input root-ADB control
   script to create only one volatile `ffs.fastboot` function, then mount
   exactly one volatile FunctionFS instance named `fastboot` on the existing
   direct `/dev/usb-ffs/fastboot` directory with fixed options, start the existing
   `fastbootd` service, and rebind only that recovery boot's
   configfs/FunctionFS gadget from ADB to exact
   `18d1:4ee0` fastboot. The script may touch only volatile service, configfs,
   FunctionFS, and `/tmp` state; it sends no partition payload, opens no block
   device, and changes no persistent file, persistent property, package,
   module, or recovery image. The fixed `ctl.start fastbootd` write is a
   volatile service control. Its intent is one-shot and uncertainty never
   replays it.
   One distinct S20+ Q2 successor may be activated only after it mechanically
   rederives the consumed Q1 preparation `PASS` and healthy return. Q2 receives
   one new intent and retains the exact target, physical topology, corrected
   create-before-mount order, volatile service/configfs/FunctionFS surface,
   `18d1:4ee0` endpoint, four fixed read-only requests, physical return, and all
   prohibitions of this exception. The census, first preparation probe, and Q1
   remain consumed; they grant no replay or second Q2 invocation.
   After exact serial/topology continuity, the SHA-pinned official Google
   `fastboot` tool may send exactly four fixed read-only requests in this order:
   `getvar is-userspace`, `getvar product`, `getvar version-bootloader`, and
   `getvar max-download-size`. The first must return `yes` before any later
   request. The exception forbids `getvar all`, `download`, `boot`, `flash`,
   `erase`, `set_active`, `reboot`, `continue`, `fetch`, OEM, logical-partition,
   lock/unlock, every caller-selected command/artifact/path, and every other
   fastboot request. Return is only through attended TWRP UI or physical keys,
   followed by fresh exact healthy Android. It grants no PID1 claim, partition
   authority, recovery-image change, or later fastboot invocation.
   One narrow S20+ fastboot-boot support exception may be activated only by
   the exact S20+ target contract. It permits one SHA-pinned official Google
   `fastboot` invocation shaped exactly as `fastboot -s <bound-serial> boot
   <bound-resident-boot.img>`. The sole 67,108,864-byte image has SHA-256
   `d67d0af219d40d29f9e4d34da873e7aa33577d56fab68e2beccfe707418f7efc`
   and is the previously proved healthy resident-Magisk rollback boot. A fresh
   exact prepare and returned approval must bind the healthy Android boot,
   same-topology classic-fastboot endpoint, image, tool, one-use intent,
   private raw output, physical power/`START` recovery, and final Android
   health. It permits a RAM download/boot attempt but no partition write and
   no `flash`, `erase`, `reboot`, `getvar`, `oem`, `flashing`, `set_active`,
   `fetch`, lock, unlock, other artifact, or second attempt. Accepted command
   output proves only boot-command support; PID1 requires a later fresh
   candidate and direct witness. Uncertainty never replays.
   One narrow A90 boot-control exception may be activated by the A90 target
   contract: after an exact reviewed `boot` write and readback, the fixed TWRP
   System-reboot hook may clear exactly the first 256 bytes of `misc` BCB and
   nothing else before reboot. The hook path, complete bytes, size, SHA-256,
   TWRP version, recovery identity, ordering, and one-shot behavior must be
   fixed by reviewed code. It accepts no caller path, offset, count, command,
   or payload; drift or a second invocation stops. This exception grants no
   other `misc` access and never transfers to another target or process.
   The S20+ T0/T1 exceptions and any later activated exact T2 exception use
   only the pinned `/usr/bin/odin4` recovery-only AP transfer. None permits `dd`,
   direct block writes, fastboot, PIT/partition-table actions, or a caller-
   selected Odin option.
4. Never flash unless the exact rollback artifact is present, readable,
   hash-verified, and usable through a demonstrated recovery path.
   For an exact S20+ recovery-only exception, this means the demonstrated
   exact-target physical Download path, a host-validated exact-stock rollback
   AP, a fresh pre-write on-device stock recovery digest, and an attended
   direct-to-Recovery key path. T0 did not presume that the first recovery
   transfer worked; T1/T2 must rederive their named predecessor evidence.
   Stock rollback remains mandatory after absent proof, and any rollback
   uncertainty parks without replay.
5. Never flash a new experiment over an unhealthy or unverified device.
   Recover first, verify health, and stop that experiment.
6. A target ambiguity, unexpected archive member, forbidden partition signal,
   changed artifact, missing rollback, journal inconsistency, or lost physical
   recovery path is an immediate stop.
7. After an unexplained failure once a device or transfer session starts, stop
   the current experiment. The exact preauthorized rollback may resume only
   from durable journal state; candidate replay is forbidden. Any non-rollback
   continuation or retry must already be defined by the selected target
   contract and satisfy its predeclared proof conditions; otherwise stop.

## Proportional Device Actions

Classify every action using
`docs/operations/DEVICE_ACTION_RISK_TIERS.md` and the selected target contract:

- **H0:** host-only work. No device approval.
- **D0:** connected read-only work. Exact target and bounded reads. A binding
  target contract may additionally activate one independently reviewed,
  filename-grammar-bounded retrieval of an operator-created derived artifact
  from normal shared user storage into `workspace/private/`; it must enumerate
  only that closed artifact class, require exactly one match, publish host-side
  no-clobber, and compare device and host hashes.
- **D1:** attended non-partition control or an exact reviewed routine setup
  action. A current direct operator request authorizes one target-contract
  allowlisted invocation. A target may explicitly activate a reviewed foreground-
  goal lane for named attended D1 actions: one direct operator goal request may
  authorize repeated invocations inside that declared action set while the same
  foreground goal remains open. Each effect still requires actual attendance,
  current target/health binding, durable one-shot intent and bounded result
  observation. Goal closure/cancellation, scope drift or unexplained failure
  ends that grant; neither a goal string nor a CLI attendance flag creates
  authority. This exception waives only repeated consent prompts, not attendance,
  recovery, no-replay, or any permanent boundary. It grants no unattended D1 or
  F1 action. Routine setup is limited to one pinned
  non-privileged Package Manager APK install or one pinned inert file staged
  no-clobber to shared user storage under
  `docs/operations/ROUTINE_CONNECTED_ACTIONS.md`. It never authorizes launch,
  patch, permission grants, arbitrary files/packages, partition payloads, or
  security/configuration changes. A target contract may also define reviewed
  cleanup or `docs/operations/targets/S22PLUS_FYG8_PREF1_AUTONOMOUS_RESEARCH_POLICY_V1.md` as `DEFINED_NOT_ACTIVE`; that pre-F1 catalog never grants F1 or persistent mutation. The separate conditional F1 delegation below may cover only its own bound entry, observation and rollback controls.
  The exact S20+ target contract may additionally activate one attended
  read-only classic-fastboot census ordinal delegated by permanent boundary 3. Its
  operator-entered mode transition makes the complete census D1 even though
  the four host requests are read-only. It grants no payload or partition
  action and no fastboot command beyond the fixed `getvar` list.
  The exact S20+ target contract may additionally activate
  `S20PLUS_PMSG_WARM_REBOOT_D1_DELEGATION_V1`: one operator-authorized transaction writes
  one internally generated, fixed-grammar marker through the verified PMSG
  character-device API into reserved RAM, requests one ordinary Android reboot,
  and compares only that marker in one bounded first-observed-return record.
  It requires independent review of the common/target delegation, fixed runner,
  generated scripts, strict journal and hostile tests before activation.
  Fresh exact target/topology/current-boot and healthy rooted Android binding,
  a shared action interlock, and durable intent before each effect are required.
  No caller bytes, paths, shell fragments or device numbers are accepted.
  It grants no raw-memory/block access, partition payload, persistent file or
  system-configuration change, log-body export, pstore deletion, module/package
  action, recovery transition or autonomous session. An uncertain intent is
  consumed; continuation is bounded read-only health/marker observation only.
  After activation, a current direct operator request for this single
  transaction permits execution without physical attendance or visual screen
  confirmation. This is the sole PMSG attendance exception to boundary 1;
  it grants neither standing authority nor a reusable autonomous session.
  Reboot evidence requires a changed boot ID plus exact serial/topology/build,
  completed Android boot, enforcing SELinux and the fixed root/Magisk/PID1
  health checks; boot ID alone is insufficient. These checks establish observed
  return, not automatic recovery capability. Nonreturn or failed health retains
  HEALTH_PENDING and the shared guard: stop new effects and use only the fixed
  read-only resume. Physical recovery, if needed, waits for separately
  authorized attended handling; no automatic reboot or flashing is permitted.
  Success proves only ordinary-reboot marker retention, never native PID1 or
  Download/recovery/power-loss retention. No second trial is delegated.
- **R1:** an attended exact privileged root-data transaction activated by one
  target contract outside D1/F1. It uses fixed no-input root commands for one
  pinned data-only payload in a finite surface, durable one-shot journal, and
  reviewed recovery owner. It grants no caller-supplied `su`, arbitrary module/
  path/configuration mutation, or partition payload; root grants no R1.
- **F1:** a boot-only transfer process defined by the selected target contract.
  Attendance is the default; conditional autonomous F1 requires the separate
  target activation below.
  The exact S20+ contract may activate the one-use non-persistent fastboot-boot
  support probe delegated by permanent boundary 3; it grants no partition
  write or later PID1 candidate.
- **F2:** the single-target S20+ recovery-canary T0 exception only. It permits
  one exact recovery candidate attempt and one exact-stock recovery rollback
  attempt under the separately activated target process; it never generalizes
  to TWRP T1, another recovery image, another target, or ordinary F1.
- **F2-T1:** the separately reviewed exact-target S20+ TWRP retained-recovery
  exception. Its sole candidate is consumed; the active owner now permits only
  journal validation and terminal re-emission, never another candidate run.
- **F2-T2:** a separately reviewed exact-target S20+ TWRP retained-recovery
  exception. Its sole candidate is consumed and TWRP is retained; the active
  owner permits journal validation/terminal re-emission only, not another run.
- **X:** forbidden by the permanent boundaries.

Do not split a higher-risk action into lower-tier commands. A device-connected
action is not H0 merely because it sends no partition payload.

## Bounded Machine-Controlled D1

A selected target contract may activate a reusable, independently reviewed D1
lane without physical attendance when the allowed device states can safely
remain stopped after failure or have an already authorized, demonstrated
machine recovery route. Safe stopping must describe the device state and any
time-sensitive hazard; killing the host process alone is not such evidence.
Use existing runners and journals where practical, not a new framework merely
to express this delegation. Activation requires the exact target/action list,
reachable implementation, fixed observations, failure/stop or recovery evidence,
and focused failure-path validation to close together under independent review.

One explicit operator grant binds a finite scope with positive time and action
limits. Within that unchanged, activated scope, the agent may select named
allowlisted actions, refresh target/boot/health bindings, observe results and
perform the bound recovery without another request at each step. The agent
cannot expand or renew the grant. Reserve required recovery capacity before an
effect; expiry blocks new experiments but not already authorized recovery.

This delegation covers only non-partition D1 actions expressly allowed by the
common boundaries. It permits no new persistent privileged-data write, generic
shell/root command, configuration/security change, or partition payload. A
separately delegated exact data operation such as PMSG keeps its own single-use
limits. R1/F1/F2, fastboot exceptions and other existing physical-return lanes
receive no waiver from this section. Unattended F1 still requires its actual
failure-specific automatic-recovery evidence under Conditional Autonomous F1.

Source/scope/target drift, a new hazard, exhausted limits, unhealthy starting
state, lost recovery or unresolved session failure blocks the next effect.
Intent-before-effect, no replay, shared guards, bounded observation, final
health and target isolation remain mandatory. An allowed stable failure state
may park without new effects; any required physical intervention is requested
then, unless the reviewed failure model requires attendance before starting.
Defining this reusable delegation activates no target or current session.

## S20+ Bounded Autonomous Research Delegation
The S20+ target contract may activate one independently reviewed autonomous
research session without per-invocation attendance. It grants no authority
until the target section, exact runner, hostile tests, and execution-critical
identities receive independent `PASS_GO` and are mechanically activated.
The lane is exact `SM-G986N/y2q/y2qksx/G986NKSS8IYC2` only. Each session starts
with bounded public ADB inventory, requires one healthy match, binds hashed
serial/topology/current boot, and expires on disconnect, unowned reboot,
identity/build/source drift, unhealthy Android, foreign guard, or endpoint
ambiguity. Other rows receive zero commands.
Only reviewed named actions are selectable: bounded public D0 collection;
fixed no-input root-read-only profiles with complete commands, paths, node
types, bounds, and parsers; `reboot-system`; and a separately reviewed atomic
`download-roundtrip` choreography with its own guard/finalizer.
Callers supply no path, shell, property, service, executable, mount, credential,
or destination.
Root profiles may report only fixed bounded metadata, digests, and explicitly
parsed proc/sys text into `workspace/private/`; they extract no file bytes.
The lane forbids Odin payload/archive/partition transfer, F1 dispatch, root or Magisk/configuration
mutation, packages, shared-storage writes, mounts, deletion, permission,
property/service/security changes, and generic `su`.
Intent precedes each effect; uncertainty never replays. Entry/return intent is
one atomic no-replace node containing both child/campaign counter snapshots;
debit-only or partial-scope state grants nothing. Recovery requires a canonical
campaign/session/ordinal/source/endpoint/predecessor chain. Only the fixed
`/usr/bin/odin4 --reboot -d <bound-endpoint>` payload-free return may leave
Download. One attended opening creates a finite monotonic campaign. A reserved
return survives expiry only for bound arrival/return/final health and grants no
new baseline, entry, transaction, or capacity. Pre-F1 readiness stops before
F1 intent/entry/approval/transfer; F1/R1 remain freshly attended.

## Common R1 Invariants

R1 exists only for a target-contract-named persistent privileged-data experiment outside D1/F1. Its runner, schema, artifact closure, fixed commands, cleanup, recovery, and hostile tests require review before activation; capability PASS prepares no run or live authority.

One fresh attended approval binds the exact target/current boot, payload bytes, finite state/staging/module surface and inventory, root commands/reboots, cleanup, and recovery. The shared guard and intent-before-effect journal make each effect one-shot and retain the guard after uncertainty or malformed state. Strict typed JSON rejects duplicate keys, bool/integer substitution, indirect nodes, and raw-receipt mismatch. A post-intent write/fsync cut is `uncertain-consumed`: never replay it, but keep exact preauthorized recovery reachable. Callers select only named actions, never a path, shell fragment, ID, property, service, mount, credential, or executable.

An R1 journal final name exposes only complete file-fsynced bytes via atomic no-replace publication and directory fsync: before publication it is absent; afterward it is complete and parseable. Direct final-name writes are not durable R1 receipts.

Staging and installation are separate; staging intent is not a root-data attempt. Before install intent, exact prepared-only decline or same-target recovery may remove owned staged bytes and close with zero installs; install intent consumes the attempt without a result. Recovery revalidates only branch inputs and remains reachable without candidate build inputs. Before Magisk BusyBox use or disable-marker change it re-reads prepared Magisk and exact helper bytes. Stock AP remains required through transfer, but an exact completed-transfer health finalizer must not reopen it.

A privileged R1 sink must not reopen a payload from normal shared user storage. Stage it only in one fixed, exclusively claimed non-shared directory inaccessible to untrusted app UIDs; bind the direct non-symlink directory by owner, mode, and exact child set, and bind each direct regular payload by owner, mode, link count, exact size, and SHA-256 immediately before the sink. Directory link counts are filesystem-dependent and are not authority receipts. Concurrent independently authorized writers with the same staging UID are outside the lane and constitute an immediate stop. Ordinary, stock/root-absent, and abrupt-cut cleanup must remain available to that non-root staging owner and remove only bounded regular remnants at the fixed names without replaying installation.

Normal terminal requires bounded observation, one-shot replay proof, disablement, healthy exact-target return, and owned-stage cleanup. Each reboot rebinds its exact current source boot immediately before intent, and no returned observation may reuse the prepared or any earlier durable boot ID. Recovery never waits after an effect; Android-root recovery touches only the named disable marker. If exact rooted Android is unavailable, only separately reviewed stock recovery may consume a durable handoff and one prebound boot-only stock artifact; another F1 grants no authority. Physical Magisk Safe Mode is outside ordinary R1 because it can mutate Magisk database/configuration state in addition to module markers; a future target may authorize it only after separately binding and reviewing every such persistent side effect. Install, reboot, disable, cleanup, and stock transfer never replay after their durable intents.

Stock Download attribution requires an empty baseline, durable attended physical-action intent, and one exact bound arrival. The initial wait is finite. After an intent-only cut, a later invocation may observe the current sole exact endpoint once and publish arrival, but cannot repeat baseline or physical action. Legacy baseline-only, malformed arm/arrival, or a different endpoint grants no transfer. After rollback intent, missing/partial transfer results permit observation and recovery only, never Odin replay. Later exact root-absent health may close while retaining an unproved outcome; it cannot relabel completion or stock provenance.

Device one-shot evidence uses only the reviewed writer/parser's exact canonical bytes; semantic JSON equivalence, escaped fixed tokens, and out-of-range numbers are invalid. Cleanup may remove a bounded partial regular file only at its fixed owned staged name after staging intent; symlink, hardlink, special/oversized file, or extra namespace entry remains a stop.

Every host-reporting cut resumes without repeating a device effect. Durable branch terminal input, including stock health and transfer state, precedes cleanup. A finalizer may derive it from a complete journal, accept consumed partial cleanup only after read-only stage absence, publish a missing terminal, release a post-terminal guard, or re-emit an exact terminal after that guard was already released and only stdout was lost. A present foreign guard still rejects. Except for those terminal-only cuts, it repeats fresh target/root/branch reads; older health is not a standing lease.

R1 never weakens forbidden partitions, permits raw block access, or makes root general maintenance authority. Target/build, Magisk, payload, namespace, command/schema, recovery artifact/transport, or health-model drift expires it.

## Common F1 Invariants

The reusable ordinary F1 design is
`docs/operations/DEVICE_ACTION_PROCESS_V2.md`. Before approval, its runner must
prove the exact target/profile, regular candidate and rollback artifacts at
stable absolute paths, exact size and SHA256, permitted archive membership,
known healthy starting state, demonstrated physical recovery, a new durable
journal, and bounded observation/final-health requirements.

Ordinary attended F1 requires one fresh approval binding one candidate and
recovery. An activated bounded attended F1 session or conditional autonomous
F1 session below may replace that human approval with a fresh machine-validated
binding for each candidate within its explicit grant.
The retired trial grants no approval waiver. Once candidate execution begins,
rollback never waits. Candidate replay is forbidden.

The separately reviewed [S22+ native roundtrip first qualification V1](S22PLUS_NATIVE_ROUNDTRIP_FIRST_QUALIFICATION_V1.md)
is incorporated at common-contract precedence, SHA256
`a6017cc22041c99814e5900a65c20945d3bf3eecb750aecc387dfd895fd4e087`.
Its exact one-transaction S22+ FYG8 specialization permits only a second
transfer of the same native N after proved first native health and exact
Download arrival. It retains the original permanent consumed claim, a separate
one-shot restoration intent and one A cleanup/fallback, with no native retry
after a research stop. This definition is dormant until its complete owner is
independently reviewed/qualified and its exact finite attended grant is current.
Ordinary F1, historical candidates and every other target retain their existing
no-replay and recovery rules. This is an explicit permanent-boundary exception,
not a role-label bypass or a standing native-baseline lease.

The separately reviewed [S22+ P384 native roundtrip followup V2](S22PLUS_NATIVE_ROUNDTRIP_FOLLOWUP_V2.md)
is a distinct common-boundary exception, incorporated at common-contract
precedence with the SHA256 declared below. Only its exact unconsumed P384
AP/member and fixed manifest/run selection may use one N installation, one
same-N restoration after proved first health/timely Download, and one exact
A cleanup/fallback. It uses a separate immutable V2 claim and original finite
deadlines. V1's policy digest, closed budget, claims and records stay unchanged.
No record is renamed or released; ordinary F1 and all other targets retain the
content-keyed no-repeat boundary. V2 likewise requires independent completed
owner qualification and a fresh finite attended approval before any effect.
V2 policy SHA256: `6f62dbe4d53be7839e9a5f06dfcb922bc1af39545f30734d499dfe73caccff4e`.

The [S22+ bounded attended native baseline V1](S22PLUS_NATIVE_BASELINE_V1.md)
is a separate permanent-boundary exception, incorporated at common-contract
precedence with the policy SHA256 below. Only its reviewed exact owner may end
a qualified operation in healthy `NATIVE_CLOSED`, and only a complete live
bootstrap qualification may admit its exact native image/physical target for
subsequent normal baseline installation/restoration. This explicitly specializes
ordinary content-keyed no-repeat and mandatory Android cleanup for that role.
The original native installation claim and every role intent remain consumed;
ordinary candidates and the closed P383/P384 exceptions are unchanged.
At most three operation reservations/600 suspend-aware seconds are bound by one
separately returned attended grant. Bootstrap alone has two declared native
roles; each reservation has one shared exact Android exit/fallback role. An
unexplained failure never authorizes another native role. Before current review,
source-qualified preparation, attendance and a finite grant, the definition is
H0 only. Normal reuse also requires the retained live admission proof. Boot-only
membership, exact A recovery, source/target identity and all other-target limits
remain permanent.
Native baseline V1 policy SHA256: `7fa75b712fbdaa8a84dd3920f2dd56eb3bc9337205ea07058d21992b482400e7`.

Keep host rejection, local parser failure, device-session start, transfer
start/completion, observation, rollback, and final health distinct. A dry run
or pre-session host failure is not a candidate transfer, but any changed
execution-critical closure requires a new exact binding before live use.

Use ordinary absolute artifact paths. Do not pass `/proc/self/fd/*`, sealed
memfd paths, or runtime path-rebinding adapters to a transfer tool. Revalidate
the opened regular file after the tool returns.

F1 PASS requires both the intended bounded observation and the target-specific
healthy terminal state. Candidate boot or transfer success alone is not PASS.

## Bounded Attended F1 Sessions

This delegation activates no target, runner, or session. A target may adopt it
only after independent review of its contract and reachable execution closure.
Existing runners retain their exact per-candidate approval checks until that
activation; a prepared approval token must never be synthesized as human consent.

- One explicit operator grant binds one exact operator-owned target, a stated
  research scope, reviewed candidate set, runner/transport/observer identities,
  exact rollback artifact and demonstrated physical recovery route. The operator
  remains physically present and able to perform the declared recovery action
  throughout device effects. Attendance must come from the operator's current
  session statement, never an agent-created flag or ordinary ADB responsiveness.
- The initial delegation allows at most three durable attempt reservations and
  two hours from grant creation, with smaller operator limits permitted. The
  agent cannot renew, enlarge or reset the grant. A fresh run still checks the
  exact target/boot, health, candidate and rollback bytes, archive membership,
  execution closure and recovery binding before any device effect.
- Reserve each attempt durably before Download intent; bind its grant identity,
  ordinal and fresh candidate/rollback binding in the existing run journal.
  A crash or partial reservation cannot free an ordinal for replay. Serialize
  reservations through the existing target owner/lease. No next candidate starts
  while a prior reservation lacks a reconciled durable terminal outcome.
- Continue only after a validated closed run with the required healthy terminal,
  no unexplained session failure and recovery still within its demonstrated
  scope. A positively proven pre-effect host abort may consume its reservation
  without stopping the remaining grant; it never reuses that run or its intent.
  An expected unproved observation is not itself a safety fault, but cannot
  stand in for missing health, recovery or terminal evidence.
- Unproved or unavailable recovery for the encountered failure, unexpected
  control/transfer/recovery failure, target ambiguity, or uncertain effect
  occurrence closes the grant to new experiments immediately. Stopping is not
  recovery proof. A later healthy read does not clear an unexplained session
  stop. Follow only already authorized recovery from durable journal state;
  when that route is unavailable or uncertain, park for the required physical
  intervention or separately reviewed recovery authority. Never improvise a
  recovery command or replay the candidate.
- Expiry, exhaustion, withdrawal or loss of attendance blocks new experiments,
  but does not cancel the current run's already authorized rollback and final
  health. Reserve their capacity before candidate intent. Scope, critical
  source or recovery changes require appropriate review and a new explicit
  grant. No grant resets consumed candidates or unresolved device-session stops.

This is attended execution. It does not establish automatic recovery or grant
conditional unattended F1. Permanent device/evidence boundaries are unchanged;
A90 and S20+ receive no activation through another target's adoption.

## Conditional Autonomous F1

This revision defines a delegation; it activates no target or session.
All current target F1 processes remain attended until their exact contract and
runner explicitly activate this lane after one independent safety review of
the changed execution closure and its interaction with the common boundaries.
Existing pre-F1, resident-D1, R1, F2 and fastboot exceptions do not inherit it.

- One explicit operator grant opens a finite session for one exact target,
  candidate-change scope, runner/transport/observer, exact rollback and
  automatic recovery route, with positive time and candidate-count limits.
  Existing session records and journals should carry these facts; do not
  introduce a new orchestration framework merely to express the grant.
- Within that scope, the agent may build new candidates and perform Download
  entry, boot-only flash, bounded tests, exact rollback and final health without
  another human approval per step or candidate. Each candidate still requires
  fresh artifact, current target/boot, health and recovery binding before any
  effect. A session grant is not a caller-selected shell or transport API.
- Eligibility requires demonstrated automatic recovery for the failure modes
  of the allowed experiment. Current ADB access or a successful normal reboot
  is insufficient. Recovery must remain reachable if the candidate component
  being tested stops responding; host simulation alone is not device proof.
  Known failures requiring keys or cable intervention remain attended F1.
  Demonstrated physical recovery remains available as a fallback.
- Changed scope, new hazard, target ambiguity, unhealthy starting state, or
  lost/changed recovery prevents the next effect. Expected re-enumeration may
  be observed only through the bound route. Unexpected control loss suspends
  new experiments; follow only the preauthorized journal-bound recovery, and
  park for physical intervention when automatic recovery is unavailable.
- Reserve the current run's bounded rollback and final-health capacity before
  candidate intent. Expiry, exhausted research budget, or operator stop blocks
  new experiments but not that already-authorized recovery. Limits cannot be
  renewed or reset by the agent. No next candidate starts before durable close
  and exact healthy return; an unexplained transfer/recovery failure retains
  the permanent stop rule even if a later health read succeeds.
- Every effect remains one-shot at its journal boundary. Neither a new session
  nor this revision resets consumed candidates, guards, approvals or history.
  Existing archive, forbidden-action, privacy and rollback rules still apply.

Activating a target needs its actual automatic-recovery evidence, exact runner
implementation and focused normal/failure-path validation. Policy approval,
capability PASS_GO, a ready manifest and this revision are not that activation.
