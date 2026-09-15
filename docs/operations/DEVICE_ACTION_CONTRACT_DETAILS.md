# Common device-action contract details

Status: **BINDING — incorporated into AGENTS.md at common-contract precedence.**

These sections retain the device boundaries, tier definitions,
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
   D1 lane defined below, or the exact S22+ deferred-physical native-baseline
   or proportional-research scope
   exception below, each separately activated by its
   binding target contract. F1 remains attended outside that exact activated
   lane, and authority never transfers between targets.
2. The only partition payload permitted by the ordinary process is **boot**.
   Never send a partition image, raw block write, or flashing operation to
   recovery, vendor_boot, DTBO, vbmeta, vbmeta_system, BL, CP, CSC, super,
   userdata, persist, EFS, sec_efs, RPMB, keymaster, modem, bootloader, or any
   other partition. An exact reviewed D1 action performed through normal
   Android Package Manager or shared-user-storage APIs is an OS-mediated data
   write, not a partition payload; it is permitted only within the closed
   package/file staging rules or the exact S22+ Android-minimal cleanup profile
   below, and never authorizes block or filesystem
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
   The separate exact S22+ G2 exception below permits only its native GPT
   metadata replacement and the declared ordinary stock-recovery reset effects.
   It permits no partition-image transfer except the existing boot-only N/A
   roles and grants no generic userdata, EFS, param or misc access.
3. Never use raw host `dd`, fastboot outside the exact S20+ census and
   boot-support exceptions below, partition-table actions, qdl/Sahara/Firehose, RAM dump, EUD/UART
   writes, fuse/QFPROM actions, format operations, or an unreviewed panic/RDX
   path. Only the exact S22+ G2 exception below specializes GPT mutation and
   ordinary stock-recovery formatting for that one target/layout transaction.
   The reviewed `S22PLUS_NATIVE_STORAGE_CENSUS_V1` profile below is a D0
   metadata-read exception to partition-table actions for only the exact
   S22+ V3 owner. It may read LU0's primary six and final five 4096-byte blocks
   after exact UFS-controller/LU0 ancestry, block-device identity, capacity and
   logical-block-size checks, bracketed by matching live userdata/parent
   geometry. It permits no write ioctl, output block operand, other-LU read,
   userdata filesystem contents, key retrieval, partition mutation or format.
   Because this native runtime has tmpfs `/dev`, the profile may create one
   mode-0400 block-node alias `/dev/.s22-gpt-$$` in the existing `/dev` tmpfs,
   with its unique shell-PID name and exact LU0 device number. Creation must
   refuse an existing path; only that newly created alias may be removed.
   Successful census closure includes its removal. A failed command preserves
   an unproved cleanup result and never sends another cleanup command; this
   RAM-only alias changes neither storage nor access privilege.
   Complete primary/backup headers and entry arrays must fit those captures
   and agree with their CRCs and the live geometry before metadata qualifies.
   The separately adopted `S22PLUS_ANDROID_STORAGE_CENSUS_V1` uses an exact
   controller/LU0 six-initial/nine-final-block metadata read on already healthy
   original-A Android through explicit `lu0-tail9-v2`. The observed backup
   array begins nine blocks from the end, beyond userdata; the userdata end
   is checked against that boundary before reading. Existing block-node device
   numbers are verified before reading; it creates no alias or device state.
   Historical Android tail5 and native reads keep their original bounds and
   meanings; this change does not replay or relabel a consumed read.
   Its fixed foreground D0 transcript, source review, closed Android-return
   provenance, fresh before/after health, bounds and failure behavior are in
   [Android storage census V1](S22PLUS_ANDROID_STORAGE_CENSUS_V1.md).
   It grants no mode change, module load, other-LU read, storage write or
   format, and does not reuse or renew a closed V3 transition grant.
   Separately, the reviewed [S22+ native UFS V1](S22PLUS_NATIVE_UFS_V1.md)
   F1 profile may initialize its eight fixed FYG8 stock drivers. This permits
   their ordinary controller/PHY/ICE setup, UFS device attribute/feature
   initialization, supported HPB buffer management and SCSI LU discovery, including kernel partition-metadata
   probing of the enumerated LUs. This is not D0 or a zero-device-write claim.
   It permits no added host partition-data write, table update, discard,
   format, filesystem mount, caller SCSI command, RPMB data transaction or
   key request. Only its exact target/V3 adoption, reviewed source closure and
   actual finite F1 grant activate it. Later explicit metadata capture retains
   its separately declared bounds. The UFS profile alone does not qualify or
   authorize GPT mutation/restoration; the separate exact G2 exception is required.
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
   actions whose execution, repetition or required starting health is uncertain.
   Never replay an uncertain write, transfer, reboot or CONTROL. Exact
   preauthorized recovery resumes only from durable journal state. A reviewed
   target observation profile may explicitly permit fresh bounded read-only
   reobservation after a failed read, preserving its raw failure and checking
   the actual target, transport and session state. Such a read does not repeat
   the failed state-changing effect, retire its owner or prove recovery.
   Prospective repeat experiments require the separately activated scope below,
   complete prior closure and current health; historical consumed records stay
   consumed. Other continuation must be represented by the selected target
   contract and satisfy its proof conditions. More restrictive legacy modes
   retain their existing stops until explicitly specialized by a new mode.

## Proportional Device Actions

Classify every action using
`docs/operations/DEVICE_ACTION_RISK_TIERS.md` and the selected target contract:

- **H0:** host-only work. No device approval.
- **D0:** connected read-only work. Exact target and bounded reads. A binding
  target may adopt a reviewed reusable observation profile under its current
  foreground research task, including bounded reobservation after failure.
  Routine use needs no per-read approval or independent review while its
  hazard-relevant inputs are unchanged. A failed observation remains NO_PROOF;
  repeatable observation does not imply repeatable state-changing execution.
  A binding
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
  The exact S22+ target may additionally adopt
  [Android-minimal V1](S22PLUS_ANDROID_MINIMAL_V1.md) after its independent
  source-bound review. This is a closed foreground D0/D1 Package Manager
  cleanup exception following a proved, closed Android32 G2 result. A current
  direct operator request to remove unused optional apps supplies scope; fresh
  machine-derived inventory selects only the fixed optional declaration and
  excludes required/shared-UID/system-service packages. Effects are attended,
  primary-user-only uninstalls, each with one durable intent and no replay,
  plus one final ordinary reboot. No raw APK/partition deletion, remount,
  permission change, generic package operation or F1/GPT action is delegated.
  Inventory and cleanup share 900 same-host-boot seconds; an error permits only
  one 300-second close-only read reconciliation, never renewed cleanup or a
  repeated reboot. The incorporated policy's two known inventory-parser
  cases may instead use H0 no-effect retirement and one child preparation per
  retired parent, each with a fresh 900-second window under the original explicit
  foreground request. The unique immutable claim chain must preserve every
  original claim/source and rederive successful raw reads, same-boot rooted
  health and existing empty journals for every ancestor. Any execution start,
  effect intent, failed/uncertain raw command, missing journal, duplicate open,
  second child or unsupported parser source blocks this exception. The chain
  reaches only one effectful cleanup and renews no consumed effect or G2 authority.
  Source review, current target/health, no pending F1 owner,
  raw-first evidence and separate cleanup/final-health outcomes are required.
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
receive no waiver from this section. Unattended F1 requires its actual
failure-specific automatic-recovery evidence under Conditional Autonomous F1,
except the separately incorporated S22+ deferred-physical native-baseline mode
and the deferred option of its proportional-research scope below.

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
binding for each candidate within its explicit grant. The separately activated
S22+ proportional-research scope below also permits spontaneous in-scope
candidate selection under one original task approval.
The retired trial grants no approval waiver. Once candidate execution begins,
rollback never waits, except under the exact S22+ deferred-physical modes below.
Uncertain candidate execution never replays. New prospective repeat operations
are permitted only by the explicit closed-health exception below.

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

The [S22+ attended resident native baseline V2](S22PLUS_NATIVE_BASELINE_V2.md)
is a distinct permanent-boundary exception, incorporated at this same precedence
with the policy SHA256 below. Its exact reviewed owner may use an admitted
resident N, one distinct globally one-shot E and the prebound admitted N normal
restoration, with one shared exact Android A exit/fallback per operation. Live
bootstrap qualification alone admits N; its original content claim stays
consumed. E never inherits that exception. Normal E-to-N return requires proved
E health/workload and exact timely Download. Uncertainty stops every further
native role and retains only the original one-shot A recovery. At most three
reservations/600 suspend-aware seconds and actual attendance are bound by a
separately returned grant. The resident service has no normal lifetime ceiling;
its signed 64-bit admission counter and finite host/session bounds remain
separate. Current independent review, artifact qualification, exact authority
and live N admission remain required; the definition alone is H0. V1's bytes,
pin and consumed claims, ordinary F1 and every other target remain unchanged.
Native baseline V2 policy SHA256: `653aba9bdd29ddf0f26487755c3a0c9ca3c1fae50bbeff8b73ebffacb4c2c8fd`.

The [S22+ native baseline with deferred physical recovery V1](S22PLUS_NATIVE_BASELINE_DEFERRED_RECOVERY_V1.md)
is a separate permanent-boundary exception at this same precedence. Only its
explicit fresh `deferred-physical-v1` request may waive attendance for one
native-origin V2 experiment, at most one reservation/600 BOOTTIME seconds.
Its normal N -> E -> N proof, admitted N and globally one-shot E rules remain
unchanged. Failure stops research, retains ownership and defers physical A
recovery with unknown powered device activity until actual attendance. This
expressly specializes boundary 1, immediate rollback and V2's attendance rule;
it does not claim Conditional Autonomous F1's automatic-recovery qualification.
All other boundaries, original one-shot A, no replay, exact health, current
source-bound review and returned finite approval remain required. This policy
definition creates no grant or device action.
Deferred physical V1 policy SHA256: `6f67b4db753f5e91c226337ea3ba291affab750a3832a022a1c3c19d3f3ece16`.

Keep host rejection, local parser failure, device-session start, transfer
start/completion, observation, rollback, and final health distinct. A dry run
or pre-session host failure is not a candidate transfer, but any changed
execution-critical closure requires a new exact binding before live use.

Use ordinary absolute artifact paths. Do not pass `/proc/self/fd/*`, sealed
memfd paths, or runtime path-rebinding adapters to a transfer tool. Revalidate
the opened regular file after the tool returns.

F1 PASS requires both the intended bounded observation and the target-specific
healthy terminal state. Candidate boot or transfer success alone is not PASS.

## Task-scoped proportional S22+ research

The [S22+ proportional research V1](S22PLUS_PROPORTIONAL_RESEARCH_V1.md)
policy is incorporated at common-contract precedence, with its bytes bound by
the capability review, parent authority and child recovery closures. Its new
mode permits one finite operator-approved task to select later in-scope E
candidates and its named D1/F1 transitions without per-candidate human approval.
Every child still binds actual verified artifacts, current reviewed machinery,
exact target/health and its original one-shot recovery before effects.

Its independently reviewed fixed D0 observer may reobserve after a pure read
failure under the current foreground task. A successful new observation is
separate evidence; it does not rewrite the old failure or close an unresolved
state-changing owner. A new-mode E may become repeat-eligible only after its
original global claim and complete healthy operation are proved. Each later
repeat is a fresh intended operation, never a release or replay of an old
claim. Historical consumed E images remain ineligible.

The explicit deferred option accepts later attended physical A recovery
without claiming automatic failure recovery or device quiescence. Task budgets
replace the old one-E/600-second limit only in this new mode; protocol and
individual effect bounds remain. Boundaries 2–6, target isolation, private
evidence, intent-before-effect and no uncertain state-changing replay remain.
Other targets, old approvals and absent-mode runners receive no waiver.

## S22+ native session V3

The [S22+ native session V3](S22PLUS_NATIVE_SESSION_V3.md) is a separate
common-incorporated, review-gated specialization of the proportional S22+
research scope. Its clean owner may bootstrap one fresh N from healthy A with
actual attendance, then select fresh in-scope E candidates and restore its
V3-admitted N. Bootstrap requires two N installations and four authenticated
health/close sessions; normal N/E/N requires starting-N health/CONTROL, the
selected E health/CONTROL and one final N health/DETACH with actual descriptor
close. Its fixed task budget is one to three operations and 60–7200 original
BOOTTIME seconds. A new runtime scope requires scoped independent review.

`S22PLUS_NATIVE_STORAGE_CENSUS_V1` adds one fixed D0 operation on an already
admitted N: authenticated health, the bounded LU0 metadata census above and
DETACH with actual descriptor close. It consumes one operation when its unique
native attempt begins, including a completed negative census. Pure host
preflight failure remains unconsumed. Normal census execution sends no CONTROL
or AP payload. Complete negative metadata is `NO_PROOF` independently of
proved native health. Protocol uncertainty retains only the task's original
attended one-shot A recovery, since the census has changed no partition.
Neither census success nor that existing boot recovery qualifies GPT-write
recovery. Partition writes and formatting remain forbidden outside the separate
exact G2 exception below.

Only an explicitly granted deferred V3 task waives attendance for native-origin
operations; it retains unknown powered device activity and later attended
physical A recovery after uncertainty. This specializes boundary 1 and the
immediate-recovery rule without claiming automatic recovery. Physical USB
reconnect trials and bootstrap remain attended. Every normal transition retains
timely measured departure/Download, target and artifact binding, global F1
exclusion, original one-shot A and no uncertain replay. Historical claims,
admissions and grants confer no V3 authority. Current independent review of
the reachable owner, host installation and native source scope plus an actual
returned finite grant are required; definition alone grants no device effect.

## S22+ G2 fixed GPT reservation and stock initialization

The [exact G2 policy](S22PLUS_NATIVE_GPT_RESERVATION_V1.md) is incorporated as
a separate review-gated exception to boundaries 2 and 3 for only the
operator-owned `SM-S906N/g0q/S906NKSS7FYG8`. Its first sealed 128 GiB
reservation (P397, consumed and closed) made entry 40 95.4580078125 GiB userdata
and entry 41 128 GiB `native_data`. A separately reviewed exact Android32
successor may reduce entry 40 to 32 GiB and expand entry 41 to
191.4580078125 GiB by moving its start left to LBA 12,115,456; entry 40 ends
at 12,115,455. That successor preserves the existing native GUID, type, name,
attributes and end, and its restoration target is the completed P397 pair,
never the pre-reservation stock pair. Both preserve the other 39 entries and every other byte
outside LU0 GPT LBAs 1, 3, 62,305,272 and 62,305,279. Only the fixed reviewed
native endpoint may write these blocks; raw host writes and arbitrary payloads
remain forbidden. One apply and, if needed, one original-metadata restoration
are separate nonreplayable roles under the same global F1 owner.

The exact stock recovery may perform one ordinary candidate factory reset
after fresh kernel discovery of the reduced layout. This expressly includes
userdata/cache/metadata formatting, two 64-byte MDF writes at param end minus
2048, the traced conditional UCM/post-wipe files in EFS/sec_efs, recovery cache
log maintenance, and the 2048-byte misc BCB clear. Only those stock operations
are permitted, with no host raw access to their destinations. If a candidate
reset was intended and recovery restores original GPT, one distinct restorative
stock reset at original userdata size is permitted; it does not restore erased
user data. The native partition remains unformatted. No recovery image, PIT,
BL/CP/CSC, super, key material, RPMB or other partition payload is permitted.

This exception specializes the V3 A-only recovery rule: after a GPT intent,
exact A is forbidden until full original GPT is restored (plus restorative
reset geometry if required), or the reduced GPT and fresh filesystem geometry
are proved. Recovery may install the already qualified exact N once to restore
original metadata, using the reviewed stock PE serial-write-state model and
attended physical Download. Once A is intended, N cannot overwrite it and A
cannot replay. An uncertain restoration stops further effects; the owner stays
held. Ordinary A remains boot recovery only. The declared model does not claim
recovery from arbitrary media failure or guaranteed hardware durability.

Fresh actual read-only qualification of the new native endpoint is required
before apply. Fixed reads are full six/nine-block GPT capture, matching live
userdata/native-entry geometry, and after reset only 216 exported F2FS geometry
bytes from two fixed 4096-byte reads; UUIDs and filesystem data are not exported.
After exact A and attended setup, bounded full GPT/statfs reads between rooted
health brackets precede and follow one ordinary Android reboot. Normal closure
requires changed Android boot, preserved exact GPT/capacity and numeric root.
Physical reset, reboot and setup remain attended; no deferred mode is adopted.
The Android32 initial-health missing-su result may use only the exact
prospective setup-pending classification in the incorporated policy. It retains
the original grant/owner and failed raw attempt, requires an actual renewed
setup-completion report, and permits only new reads before the still-unconsumed
ordinary reboot. P397's stop, incident completion and consumed effects remain
unchanged. Post-reboot read failure uses the existing health-only recovery.

The exact target adoption, independent review of this exception and reachable
owner/native closure, fresh qualified N/A artifacts, usable physical recovery,
and an actual separately returned finite grant are all required. Its task is
at most two operations (bootstrap and G2) and 7200 original BOOTTIME seconds.
An optional bootstrap origin is an exact healthy previously admitted V3 N whose
closed tail and unchanged ancestor source closure are machine-bound. It still
performs two fresh-N installations and four health sessions before admission.
No prior grant, consumed image or unactivated document grants an effect.

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
