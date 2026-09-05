# AGENTS.md - repository operating contract

Contract-Revision: **7** (supersedes revision 6; 2026-09-05)

The retired Interim Fast-Loop trial contract is preserved byte-for-byte at `docs/archive/policy/AGENTS_INTERIM_FAST_LOOP_RETIRED_2026-08-03.md`; it is historical evidence only and grants no current authority.

---

This file contains the repository-wide invariants and the binding target registry.
Select exactly one target contract before target-specific work. A registry goal describes current state and objectives but never grants device authority.
Historical or draft policies under `docs/archive/` or elsewhere are evidence only, even if their text says `ACTIVE`.

The default work cycle is:

`STATE -> SELECT -> DESIGN -> IMPLEMENT -> STATIC VALIDATE -> DEVICE -> REPORT -> COMMIT`

Do not add a device step when host-only work can answer the question.

## Authority and Precedence

The effective contract is, in descending order:

1. the common invariants in this file;
2. the selected binding target contract in the registry below;
3. the shared risk-tier and execution-process documents named by that target;
4. the immutable live binding required by the active policy or current runner.

The more restrictive applicable rule wins. A target contract may specialize
only behavior explicitly delegated by this file and may never relax the
permanent safety boundaries. A manifest, approval string, goal, report,
archived clause, helper string, or sub-goal cannot override a higher layer.

No document grants standing device authority unless this common contract or the
selected target contract expressly activates it and all required live inputs
are current. An unactivated policy edit remains H0 only.

The development and review rules below govern routine H0 work across targets.
They do not waive an existing runner check, source/artifact binding, or a
device-session stop. Changing those mechanisms requires the scoped review
below; a general instruction to work autonomously is not such a change.

## Binding Target Registry

| Target | Current state | Binding target contract | Binding live process |
|---|---|---|---|
| Samsung Galaxy S22+ FYG8 (`SM-S906N` / `g0q` / `S906NKSS7FYG8`) | `GOAL.md` | `docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md` | `docs/operations/DEVICE_ACTION_PROCESS_V2.md` |
| Samsung Galaxy A90 5G | `GOAL_A90.md` | `docs/operations/targets/A90_TARGET_CONTRACT.md` | `docs/operations/targets/A90_TARGET_CONTRACT.md` sections `A90 D1 Resident Session`, `A90 F1 Resident Install`, and `Attended F1 Pre-Handoff` |
| Samsung Galaxy S20+ 5G (`SM-G986N` / `y2q` / `G986NKSS8IYC2`) | `GOAL_S20PLUS.md` | `docs/operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md` | Active exact-target routine D0/D1 including payload-free Download return; classic-fastboot census ordinals 1/2 consumed, with ordinal 2 four-query PASS and healthy return; fastboot-boot support F1 consumed with NO_PROOF healthy return; retained-T2 TWRP-fastbootd census consumed and first staged preparation probe consumed with NO_PROOF healthy return; staged fastbootd preparation Q1 consumed with PASS healthy return; TWRP-fastbootd census Q2 consumed with NO_PROOF healthy return; attended fixed root-health D0 active; attended boot-only bootstrap, resident Magisk, and recovery-canary B0 F1 active; recovery-canary T0 and TWRP T1 F2 candidates consumed; TWRP T2 recovery retained and candidate consumed; reviewed attended native-canary R1 active |

Targets, profiles, rollback identities, transports, approvals, and health evidence never transfer between registry rows. Without an exact matching contract, remain H0.

For A90 work, read this file, then `docs/operations/targets/A90_TARGET_CONTRACT.md`, then `GOAL_A90.md`. The goal cannot grant or extend live authority.

## Permanent Device Safety Boundaries

1. Work only on an explicitly identified operator-owned device. Device effects
   require attendance except the exact A90 resident D1 lane, an exact S20+
   bounded autonomous-research lane, the S22+ pre-F1 autonomous lane, or the
   conditional boot-only F1 lane below, or the single S20+ PMSG ordinary-reboot
   transaction expressly delegated below, each separately activated by its
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

## Permanent Repository and Evidence Boundaries

Do not commit firmware, boot images, ramdisks, compiled payloads, raw device
logs, credentials, device serials, PARTUUIDs, MAC/BSSID/IP values, KASLR
slides, or tunnel URLs. Keep private inputs and run evidence under
`workspace/private/`.

Changing a permanent device, repository, or evidence boundary is a separate
policy change and requires an independent safety review. A target contract
refactor must prove that these boundaries remain semantically unchanged.

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
  allowlisted invocation. Routine setup is limited to one pinned
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
recovery. Only an activated conditional autonomous F1 session below may replace
that human approval with a fresh machine-validated binding for each candidate.
The retired trial grants no approval waiver. Once candidate execution begins,
rollback never waits. Candidate replay is forbidden.

Keep host rejection, local parser failure, device-session start, transfer
start/completion, observation, rollback, and final health distinct. A dry run
or pre-session host failure is not a candidate transfer, but any changed
execution-critical closure requires a new exact binding before live use.

Use ordinary absolute artifact paths. Do not pass `/proc/self/fd/*`, sealed
memfd paths, or runtime path-rebinding adapters to a transfer tool. Revalidate
the opened regular file after the tool returns.

F1 PASS requires both the intended bounded observation and the target-specific
healthy terminal state. Candidate boot or transfer success alone is not PASS.

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

## Evidence and Reporting

- Routine H0/D0/D1 work needs only the evidence required by its tier and target
  contract.
- Routine R1 output is one exact private run, append-only one-shot intents and
  results, bounded private raw command evidence, and one terminal structured
  result. A new R1 capability, recovery deviation, or incident also requires a
  prose report.
- Routine F1 output is one structured result, one append-only journal, private
  raw logs, and the target contract's canonical timeline.
- Write a prose report for a new capability, new hazard class, incident,
  ambiguous result, recovery deviation, or policy change.
- A reporting or parser failure after a proven transition must not cause that
  device transition to be repeated. Resume only from durable journal state.
- Preserve bounded raw failure evidence before result interpretation can fail,
  within the selected target's existing capture/privacy rules; this does not
  expand permitted raw collection or replace a digest-only evidence boundary.
  Record the source version and evidence location in the existing close record
  so later audit does not depend on the moving working tree. Routine narrative
  may be a concise commit body; do not duplicate it across per-run documents.

## Review Rules

- One independent review is required when a common/target contract, F1 runner, schema, transfer/archive/recovery machinery, boundary, or hazard changes.
- Review changed execution-critical closure and higher-precedence interactions;
  ignore unreachable legacy helpers.
- An independent `PASS_GO` qualifies a capability, not a run. Reuse it across candidates,
  campaigns, manifests, qualifications, and ordinals while its named execution-critical hashes are unchanged and no new hazard or incident occurs. Fresh qualification and any runner binding still apply.
- Scope review to reachable execution and the stated threat model in
  `docs/operations/DEVICE_ACTION_RISK_TIERS.md`. Out-of-model speculation does
  not automatically create mandatory machinery. A concrete new hazard stops
  the affected scope and changes that review scope. Do not reopen resolved
  work without changed inputs or new evidence.
- Track whether old findings affect the current path, are explicitly covered,
  or belong to a retired path. Different-topic PASS is not automatic coverage;
  unrelated historical pending counts are not a blanket gate on new work.
- Every new non-permanent gate must name the hazard or incident class it
  blocks, its scope, objective retirement evidence, and an expiry or review
  trigger. A gate without a retirement condition must be explicitly designated
  permanent and reviewed as a boundary; do not carry a temporary gate forward
  by default.

## Development and Commit Discipline

- Read this file, the selected target contract, and every affected goal; inspect
  `git status --short` and keep edits scoped.
- Keep each active goal focused on current state and the selected bounded unit.
  Review completed history for archival above 800 lines; 900 lines is the hard
  limit for any goal file.
- Use canonical paths under `workspace/public/src/`, `workspace/private/`, and
  `docs/`. Do not recreate legacy root trees.
- State the bounded task and completion criterion briefly. Read current bytes
  and the actual consumer before diagnosing a past incident; consult history
  when generation or cause is uncertain, not before every unchanged read.
- For the selected goal, prioritize the smallest useful working capability
  within existing safety and proof requirements. Keep functional evidence
  independent from detailed causal analysis and optional diagnostics; do not
  gate that capability on their completion unless needed for safe execution
  or its stated success criterion.
- Before an expensive build or device experiment, use already available
  evidence and existing low-cost checks to resolve questions they can answer.
- Prefer the smallest working change and existing tools. Avoid speculative
  frameworks and candidate-specific copies; derive repeated registration,
  encoding and result rules from one existing declaration where practical.
  New daemons/proxies must justify their in-scope benefit and must not break
  the existing transport or recovery through resource contention.
- Validate touched Python with `py_compile` and focused tests. Cross-compile
  touched C with the repository toolchain and inspect the output with `file`.
  Exercise representative real producer/consumer and failure paths, not just
  unrelated helpers. Use fixed fixtures and behavioral invariants; do not pin
  growing ledger counts or the checkout's current activation state as answers.
  Historical snapshot tests must bind their historical input.
- Reuse successful checks and build outputs while their relevant inputs are
  unchanged. Expand validation only for changed paths, failures or new evidence.
  Documentation-only changes need content/link/diff checks, not image builds;
  a contract's semantic change still needs review. Unrelated census counts and
  other-target changes should not be execution identity. Remove accidental
  bindings through reviewed code changes, never by bypassing current checks.
- Keep prepare, activation, consumption, recovery and terminal prerequisites
  distinct. A stage must not invalidate itself by creating its normal output;
  recovery must not rerun a pre-consumption absence check. Actual target,
  artifact, authority and no-replay checks remain mandatory at the effect.
- Stop expanding a task once its completion criterion and relevant checks pass.
  Put necessary validation rationale in the existing change description rather
  than adding a separate approval or evidence layer for every correction.
- Use scoped staging; never `git add -A` or `git add .`.
- Run `git diff --check` before commit. Commit only after the selected bounded
  unit is validated.
- Redact all private identifiers from tracked diffs.

## Stop and Escalate

Stop new device effects when target, effect occurrence, health, authority or
recovery is uncertain, a boundary would need to bend, or the action is not
represented by the selected tier and target contract. Preserve the journal;
continue only allowed observation, H0 diagnosis and preauthorized recovery.
An expected negative or unproved research result is not itself a safety fault;
any next experiment still requires a closed run, exact health and its own
current authority. Unexplained device-session failures retain boundary 7.

H0 build, parser and test failures may be repaired and rechecked within the
same authorized task without a new approval or a fixed failure-count stop.
Stop an approach when it repeats without new evidence, exhausts its resource
budget, or needs a scope change. This replaces blanket first-failure and
one-repair H0 rules; it never permits replay of a device effect, editing a
consumed journal, relaxing a safety assertion to obtain PASS, or ignoring an
explicitly narrower operator instruction.
