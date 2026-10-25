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
   The separate exact S22+ native ext4 exception below permits one filesystem
   initialization and fixed witness only within the retained native_data extent;
   all image transfers remain boot only and Android32 userdata is preserved.
   The separate exact S22+ Debian first-boot exception below permits one
   installation into that existing native_data filesystem and its declared
   Debian lifetime. It permits no format, repair, GPT change or Android stage.
   The separate exact S22+ installed-Debian exception below permits one fresh
   boot of that already completed root, its declared filesystem lifetime and
   one reviewed P399 boot-only normal restoration. It grants no installation,
   format, repair, GPT change, Android stage or replay of prior P401/P399
   effect intents.
   The separate [native-first Debian handoff exception](S22PLUS_DEBIAN_HANDOFF_V1.md)
   below permits one protected admission followed by an installed-Debian
   native_data writable lifetime, basic access and fixed shutdown, with
   physical original-A return. It adds no install, repair, GPT mutation,
   other-partition access or replay of any consumed predecessor.
   The separate [Debian-owned integrated boot exception](S22PLUS_DEBIAN_INTEGRATED_V1.md)
   permits its measured Debian initial PID1, fixed platform/USB/UFS preparation,
   complete protected root admission and one native_data writable installed-init
   lifetime with bounded service evidence, same-boot SSH and fixed shutdown.
   All transfers remain boot only, with physical original-A return and no repair,
   installation, GPT change, other-partition write or consumed-action replay.
   The separate [automatic Debian boot exception](S22PLUS_DEBIAN_AUTOBOOT_V1.md)
   permits its fixed automatic preparation, one bounded early-file lifetime and
   one installed-root lifetime, each after complete protected admission, with
   distinct bounded records and one first-gadget NCM attempt. One fresh N owns
   the startup; physical original-A return, no repair and no replay remain.
   Its separately reviewed [bounded reboot specialization](S22PLUS_DEBIAN_REBOOT_V1.md)
   permits two admitted boots and four exact writable lifetimes, sealed count M,
   one ordinary reboot and final shutdown under the same attended finite owner.
   Each boot retains both complete admissions; no further startup is admitted.
   The separate [bounded cron specialization](S22PLUS_DEBIAN_CRON_V1.md)
   adds only fixed packaged cron lifecycle, one boot-1 integrity report and
   exact boot-2 retention checks inside those same four writable lifetimes.
   Its schedule and bounded temporary-file storage are RAM only.
   The separate [persistent cron configuration specialization](S22PLUS_DEBIAN_CRON_CONFIG_V1.md)
   permits one exact boot-1 cron.d file, one boot-2 integrity report and one
   successful-path unlink of that same configuration inside those four
   lifetimes. Failure cleanup remains RAM only; no installation or repair.
   The separate [fixed native_data journal recovery exception](S22PLUS_NATIVE_JOURNAL_RECOVERY_V1.md)
   permits only one sealed internal JBD2 replay and exact journal/primary
   superblock finalization on entry 41. It adds no ordinary fsck repair,
   reinstall, formatting, GPT mutation or other-partition payload.
   The separate [Debian logger-only stage probe](S22PLUS_DEBIAN_STAGE_PROBE_V1.md)
   narrows stock retained-RAM observation to one logger module and measured
   early parent/stage records, with no USB/platform/UFS/storage work, direct
   RAM mapping or block-backed data write; original-A return remains attended and physical.
   The separate [native log calibration](S22PLUS_NATIVE_LOG_CALIBRATION_V1.md)
   adds one fixed root-child stock logger and bounded current/returned retained
   evidence on the retained native carrier, with only RAM node/marker writes,
   no partition command or filesystem data write, and physical original-A return.
   The separate [Debian early file pilot](S22PLUS_DEBIAN_FILE_PILOT_V1.md)
   permits only its fixed bounded native_data directory/file writes and ordinary
   ext4 metadata after fresh clean protected admission, with no installed code,
   replay, repair, format, GPT change or other-partition write.
   The separate [storage-first file sibling](S22PLUS_DEBIAN_FILE_FIRST_V1.md)
   retains that exact file/write surface, with storage before the last six
   platform clients and checked records before their fixed insertion calls.
3. Never use raw host `dd`, fastboot outside the exact S20+ census and
   boot-support exceptions below, partition-table actions, qdl/Sahara/Firehose, RAM dump, EUD/UART
   writes, fuse/QFPROM actions, format operations, or an unreviewed panic/RDX
   path. Only the exact S22+ G2 exception below specializes GPT mutation and
   ordinary stock-recovery formatting for that one target/layout transaction.
   The separate exact S22+ native ext4 exception below specializes formatting,
   filesystem reads/mounts and fixed witness writes only on its sealed entry 41.
   The separate exact S22+ Debian first-boot exception specializes only the
   declared read-only GPT binding, native_data mounts and rootfs writes; it
   authorizes no formatting, repair or partition-table mutation.
   The separate installed-Debian exception specializes only protected checks,
   native_data mount and declared Debian rootfs writes after completed-root
   validation; it adds no formatter, repair, partition-data writer or host
   storage-control command.
   The separate [native root inspection V1](S22PLUS_NATIVE_ROOT_INSPECT_V1.md)
   permits only exact native_data metadata/file reads and a protected read-only
   mount. Its sole block control is partition-only `BLKROSET=1`, retained until
   reboot; it grants no block-data write, flag clear, repair or installed-code
   execution. All image transfers remain boot only.
   The separate [mountless root evidence V1](S22PLUS_NATIVE_ROOT_EVIDENCE_V1.md)
   adds only its fixed bounded private historical-file reads under the same
   exact partition RO protection, including a dirty home-block view without
   mount or journal replay; it permits no filesystem data write or execution.
   The separately reviewed [bootstrap preflight V1](S22PLUS_NATIVE_PREFLIGHT_V1.md)
   permits its fixed automatic read-only preparation, partition RAM RO,
   unprivileged loader checks and sealed-result native observer only. It adds
   no filesystem data write, repair, installation or Debian PID 1 handoff.
   The separately reviewed [streamed preparation V1](S22PLUS_NATIVE_STAGED_PREFLIGHT_V1.md)
   permits one fixed protected checker/loader command after native health,
   with partition RAM RO and bounded stage evidence. Partial evidence grants
   no completion, recovery or replay. No filesystem write or handoff is added.
   The separately reviewed [readonly root-transition witness V1](S22PLUS_SWITCH_ROOT_WITNESS_V1.md)
   permits one fixed actual-PID-1 switch_root to a pinned RAM executable under
   the readonly native_data root. Partition-only RAM RO remains set; it adds
   no filesystem data write, installed init execution or writable lifetime.
   The separately reviewed [native-first Debian handoff V1](S22PLUS_DEBIAN_HANDOFF_V1.md)
   permits one exact-root protected admission followed by partition-only RAM
   RO clear, a fresh normal native_data RW mount and installed Debian init,
   basic SSH and fixed shutdown. Ordinary writes are confined to entry 41;
   no formatter, repair, extraction, raw block-data writer or other-partition
   write is added. Attended physical original-A recovery remains required.
   The separately reviewed [handoff V2 successor](S22PLUS_DEBIAN_HANDOFF_V2.md)
   admits only its finite declared post-P410 mutable data under otherwise exact
   clean-root checks, then Debian-owned service observation and reconfiguration
   of the same first USB gadget. It adds no repair, reinstall, journal replay,
   other-partition access or renewed consumed effect.
   The separately reviewed [Debian-owned integrated boot V1](S22PLUS_DEBIAN_INTEGRATED_V1.md)
   specializes only the exact fixed preparation, protected current-root checks,
   one partition RAM RO clear/RW mount, installed PID1/service lifetime and
   bounded local records on native_data. Its authenticated compound start,
   fixed continuations and same-g1 access cannot replay after uncertainty.
   The separately reviewed [automatic Debian boot V1](S22PLUS_DEBIAN_AUTOBOOT_V1.md)
   adds only its two sequential admitted native_data lifetimes, exact sealed
   historical-file input, checked same-boot early-file admission and automatic
   installed services/first-gadget attempt. N-transfer intent consumes startup;
   the declared absolute deadline and one-shot recovery owner remain binding.
   The [bounded reboot specialization](S22PLUS_DEBIAN_REBOOT_V1.md) expressly
   replaces only that single-boot lifetime limit with two admitted boots/four
   fixed lifetimes and one ordinary reboot, retaining per-boot absolute device
   deadlines, fixed host windows and the same physical original-A recovery.
   Its separately named pre-build D0 permits only the existing native_data
   node's first 4096-byte read after exact GPT and health admission; no write,
   mount, RO ioctl, node creation or staged helper is added by that read.
   The [bounded cron specialization](S22PLUS_DEBIAN_CRON_V1.md) adds one
   exclusive authenticated native_data report from a fixed packaged-cron job,
   fixed RAM schedule transitions and a bounded RAM `/tmp` mount. It retains
   the same two boots, admissions, original deadlines and physical A recovery;
   it adds no package installation, persistent configuration or repair.
   The [persistent cron configuration specialization](S22PLUS_DEBIAN_CRON_CONFIG_V1.md)
   separately permits only its exact configuration creation, second-boot
   consumption and successful-path retirement. It retains both admissions,
   all original deadlines, no replay and the same physical original-A return.
   The separately reviewed [fixed journal recovery V1](S22PLUS_NATIVE_JOURNAL_RECOVERY_V1.md)
   permits one partition-only RO clear, one pinned pathless strict JBD2 writer
   and RO restoration after conclusive child settlement, followed by the fixed
   read-only checker and exact root comparison. Partial writes stay consumed;
   boot-only original-A return is not a filesystem rollback. Generic block
   writers, ordinary repair, orphan cleanup, external journals and installed
   execution remain forbidden.
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
  repeated reboot. The incorporated policy's four known inventory preparation
  cases may instead use H0 no-effect retirement and one child preparation per
  retired parent, each with a fresh 900-second window under the original explicit
  foreground request. The unique immutable claim chain must preserve every
  original claim/source and rederive same-boot rooted health and existing empty
  journals for every ancestor. Raw reads must succeed except the acquisition
  case's exact final host-enforced metadata stdout-limit termination. It needs
  its explicit exceeded flag, full retained limit, host SIGTERM, empty stderr,
  no timeout/producer fault and successful prior reads; truncated metadata
  remains unproved. The capture-label case requires a complete successful
  metadata prefix and the first invalid label rejected before any command or
  stream creation. Any execution start,
  effect intent, other failed/uncertain raw command, missing journal, duplicate open,
  second child or unsupported parser source blocks this exception. The chain
  reaches only one effectful cleanup and renews no consumed effect or G2 authority.
  Source review, current target/health, no pending F1 owner,
  raw-first evidence and separate cleanup/final-health outcomes are required.
  A new direct additional-cleanup request may use the incorporated policy's
  separately reviewed `additional-known` mode, limited to its exact historical
  extra declaration with every existing runtime exclusion. One immutable child
  of a closed original-mode cleanup binds the complete prior effect sequence,
  exact healthy changed-boot GPT/root/package state and a fresh finite window.
  The policy's qualified same-boot read-only transport stop may be resolved for
  this prospective scope under boundary 7; no uncertain effect qualifies and
  no old verdict changes. This is separate from inventory retirement. Prior
  journals remain effectful and immutable, a second additional child is
  forbidden, and all new effects remain attended and one-shot. The policy's
  separately reviewed `user-apps` successor may follow one closed additional
  run under the new explicit consumer-UI request. It has one immutable claim,
  the fixed 31-name declaration minus all prior attempted names, and the same
  finite limits. Only Play Store is excepted from historical KEEP, and ordinary
  enabled states 0/1 are allowed only in this mode. All provider/service and
  runtime exclusions remain. Both effectful ancestors and their journal
  lengths/tails must rederive; the qualified retained partial additional closure
  preserves its incomplete verdict. No uncertain effect qualifies, no previous
  effect is renewed. Complete retained final
  health may close its persistence stop as incomplete in H0 without another read.
  The policy's separately reviewed `checkpoint-complement` mode may follow that
  closed user-apps run once under the new full-checkpoint request. Its declaration
  is the complete current user-0 APK list minus effective KEEP/default components
  and all prior attempted names. This mode adopts the historical checkpoint's
  APK removals across ordinary system/shared UIDs, persistent flags, APKs inside
  APEX paths and non-system apps; true APEX modules remain excluded. Hidden or
  suspended states remain excluded; enabled states 0 through 4 are eligible.
  Require the policy's complete protected set and exact root/health. The qualified
  prior readiness read failure and its existing healthy reconciliation must
  rederive; neither uncertain effects nor old verdict promotion are allowed.
  One immutable claim binds all three effectful ancestors, 3600 seconds, a
  preflight-sized 2052-row maximum journal and one ordinary reboot, followed if
  needed by the existing single 300-second close-only observation. Explicit
  complete Package Manager refusals or retained identities may continue the
  original batch only as the policy defines; unknown failures still stop.
  Every attempt remains consumed. There is no retry, checkpoint descendant,
  disable fallback, global uninstall or partition/permission operation.
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
exact G2 and native ext4 exceptions below.

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

## S22+ native root inspection

The [native root inspection V1](S22PLUS_NATIVE_ROOT_INSPECT_V1.md) is adopted
only through V3's separate `root-inspect` operation. One returned attended
grant allows one operation and at most 1800 original BOOTTIME seconds:
healthy original A, one fresh inspector N transfer, authenticated health and
one fixed inspection, same-boot health/CONTROL, one original-A return and exact
Android32 final health. The one-shot image earns no N admission and cannot
enter bootstrap, experiment, storage census or another native role.

Only entry 41 of the unchanged retained Android32 GPT may be inspected.
Exact device/GPT binding precedes the RAM-only partition `BLKROSET=1` control;
the authenticated control intent is durable before EXEC. Block RO readback,
the existing clean-superblock gate, and `ro,noload,nodiscard,nodev,noexec,nosuid`
precede bounded file-tree/marker comparisons. Dirty or recovery-needed state
is reported without mounting. No filesystem data write, repair, extraction,
chroot, flag clear, GPT mutation or userdata file access is authorized.

The retained target-kernel error/orphan paths make block protection a permanent
inspector invariant, including for initially clean filesystems. Failed or
uncertain execution never retries. All previous format, install and candidate
claims remain consumed; no negative observation releases them. V3's existing
global exclusion, same-host-boot, attended physical Download, one-shot A and
health-only recovery rules remain binding. Source-bound independent review,
actual artifact qualification and the returned grant are separate prerequisites.
The named foreground preparation D0 is read-only Android health/GPT/statfs,
not native_data mount or file access, and grants no experimental transfer.

## S22+ fixed mountless native_data evidence

The separately reviewed [root evidence V1](S22PLUS_NATIVE_ROOT_EVIDENCE_V1.md)
is adopted only as V3's `root-evidence` operation. One returned attended grant
permits one Android-origin reader N and one original-A return within 1800
original BOOTTIME seconds, with the existing exact health, endpoint, exclusion,
one-shot intent, no-replay and physical recovery requirements. It earns no N
admission and permits no other operation, E, reconnect or HUD.

Exact entry-41/GPT binding and partition-only RAM RO protection precede a
mountless unprivileged static reader. This separate path may read its fixed
bounded historical files from validly identified clean or dirty native_data;
it never mounts, replays JBD2, clears RO, writes data or executes installed code.
The older inspector's clean-only mount and digest-only observation stay intact.
Only the policy's sealed file list, sizes and private raw suffixes are allowed;
no caller-selected path or arbitrary file access is introduced. A dirty home-
block view can miss committed journal updates, so absence is never proof of
non-execution. Acquisition, Debian runtime proof and filesystem health remain
separate. Raw bytes remain private. Independent review, actual qualification
and a returned finite grant are distinct prerequisites. Offline preparation
proves no current health and grants no effect.

## S22+ fixed installed-Debian userspace probe

The separately reviewed [userspace probe V1](S22PLUS_NATIVE_USERSPACE_PROBE_V1.md)
is adopted only through V3's `userspace-probe` operation. One returned attended
grant permits one operation/1800 original BOOTTIME seconds: healthy A, one fresh
probe N, fixed authenticated probe/DETACH, same-boot health/CONTROL and one
original-A return with full rooted Android32 health. It grants no N admission,
other operation, E, reentry option, reconnect or HUD.

The fixed inspector's exact GPT/partition binding, permanent RAM block-RO
protection, clean-only readonly mount and complete root comparison precede
execution. Only this new profile may enable execution in a child's private
mount namespace through a per-mount bind remount, chroot and run its fixed
verified shell/libc/fork/exit workload with all UIDs/GIDs 65534, no capabilities,
no_new_privs, no inherited extra descriptors and finite process/output bounds.
The parent retains noexec and its existing ACM process-group recovery owner.
There is no filesystem data write, repair, extraction, format, block-RO clear,
GPT change, userdata file access, service, network operation or PID 1 handoff.

Actual child output/exec/wait, complete reaping, normal unmount and unchanged
superblock/GPT proof are independent from Android recovery. Uncertainty stops
research and retains only V3's unchanged original one-shot A recovery. All
prior consumed claims and grants remain consumed. Its separate source-bound
review, actual qualification and finite grant are required; its named fixed
foreground Android preparation D0 grants no mode change or experimental image.

## S22+ installed-bootstrap preflight

The separately reviewed [preflight V1](S22PLUS_NATIVE_PREFLIGHT_V1.md) is adopted
only as V3's `preflight`: one returned attended grant, one operation and at most
1800 original BOOTTIME seconds. One fresh N transfer from healthy original A
owns and consumes the automatic fixed preparation before its first boot. One
sealed current-boot result read, normal native health/CONTROL, one original-A
return and full rooted Android32 health close it. There is no N admission,
other operation, E, prior tail, optional reentry, reconnect or HUD.

P405's exact 81-module preparation and protected root/checker/loader checks
stop before writable mount or root handoff. Partition-only RAM block RO,
clean admission, both mount protection readbacks, fixed unprivileged loader
children, finite child/output accounting, ordinary unmount, complete FD and
mount release and unchanged superblock/GPT are mandatory. The existing native
observer may restart only from the same-run/current-boot sealed result and
adopt the exact already-loaded module set; old temporal insertion witnesses
do not apply. Incomplete modules, timeout, output overflow, unsettled children
or cleanup uncertainty park for the unchanged attended original-A recovery.
No filesystem write, repair, extraction, flag clear, GPT change, installed init,
service/network startup or Debian PID 1 handoff is authorized. Earlier claims
remain consumed. Source review, actual qualification and returned finite grant
are separate; the named fixed Android preparation D0 changes no mode or image.

## S22+ Debian-owned early boot

The separately reviewed [Debian-owned early boot V1](S22PLUS_DEBIAN_EARLY_BOOT_V1.md)
specializes initial userspace and observation ownership only for V3's exact
`debian-early` profile. One fresh attended boot-only candidate owns the retained
73+8 module initialization, exact GPT/superblock reads, partition-only RAM RO,
and one fixed ACM gadget. Debian's shell remains PID1; a fixed child exports
only authenticated bounded RAM evidence. There is no native console, CONTROL,
N admission, E, root mount, RO clear, repair, installed init or filesystem data
write. One returned 1800-second/one-operation grant includes mandatory attended
physical Download, one original A and full Android32 health. No uncertainty
permits replay; normal return's explicit physical phase and expired-work
recovery retain the exact owner and original A. The removed native thermal
service is not inherited as a health/safe-quiescence claim. All other targets,
existing profiles and consumed records are unchanged.

The separately reviewed [Debian USB-first V1](S22PLUS_DEBIAN_USB_FIRST_V1.md)
is an expressly adopted sibling runtime profile under the same `debian-early`
owner. It replaces 73+8/storage preparation with the retained 73 platform
modules and one fixed USB evidence channel. A build-declared `ram-only` subset
uses mandatory checked RAM preparation records and authenticated USB retrieval;
it adds no logger module, printk dependency or post-return `last_kmsg` capture.
The `retained` variant adds the stock `sec_log_buf` retention owner before the
same module sequence. Only bounded authenticated stage lines through ordinary
printk into that existing RAM backend are added, with bounded checked ring
readback and a fixed post-closure Android `last_kmsg` D0 read. It adds no UFS,
block access, direct memory writer, DT/sysctl change, filesystem data write or
native-return experiment. The same fresh finite attended grant, physical
original-A recovery, exact health, global consumption and no-replay rules
apply. Ring acceptance, post-return retention and PID1/USB proof stay separate.

## S22+ Debian logger-only early stages

The separately reviewed [stage probe V1](S22PLUS_DEBIAN_STAGE_PROBE_V1.md)
is adopted only as `debian-stage-probe-v1` under V3's `debian-early` owner.
One returned attended 1800-second/one-operation grant consumes one fresh N,
one stock logger insertion, bounded measured-parent/printk stages and one
physical original-A return with full Android32 health. The fixed 90-second
host window proves no execution. No platform/USB/UFS or block-backed filesystem work,
new reserved-memory writer, panic, installed init or recovery retry is added.
The stock logger uses its existing region/hooks. After healthy closure, only
the fixed same-returned-Android-boot bounded `last_kmsg` D0 reader is adopted.
Complete/partial/rejected/absent record meanings and current-ring/retention/
Android health stay distinct. Independent review and actual qualification
precede a concrete grant; offline preparation remains H0 only.

## S22+ native retained-log calibration

The separately reviewed [native calibration V1](S22PLUS_NATIVE_LOG_CALIBRATION_V1.md)
is adopted only as `thermal-v3-reconnect-ufs-drain-log-calibration-v1` under V3's
`log-calibrate` operation. One returned attended 1800-second/one-operation grant
binds one fresh N on the retained native UFS/drain carrier, one authenticated
fixed root child, one absent-before-call stock logger insertion, two bounded
markers and one physical original-A return with full Android32 health. The
child's exclusive checked RAM character alias and stock reserved-RAM markers
are its only additional writes. Current-ring acceptance, current-backend
membership, same-returned-Android-boot bounded `last_kmsg` D0 evidence and
Android recovery stay separate. No storage command, mount, persistent data
write, Debian execution, normal native CONTROL return or replay is adopted.
The original owner preserves failure stops and one-shot physical recovery;
independent review and A/B/ARM64 qualification precede any concrete grant.

## S22+ Debian early file pilot

The separately reviewed [file pilot V1](S22PLUS_DEBIAN_FILE_PILOT_V1.md)
specializes boundaries 2 and 3 only for `debian-file-pilot-v1`, using V3's
existing attended `debian-early` owner. One fresh N transfer consumes its fixed
73+8 module initialization, clean protected checker/root admission, one
native_data-only RO clear/RW mount, conditional fixed `var/lib/lab` directory
and one exclusive run-bound evidence file of at most 16384 bytes, including
ordinary ext4 metadata/journal writes. Checked file/parent synchronization,
one ordinary unmount and post-unmount partition RO/GPT/clean checks retain
separate completion facts. Debian shell stays initial PID1; there is no gadget,
USB request, installed-code execution, replay, repair or other-partition write.
New RO-clear, RW-mount, directory and file effects in the persistent-write
phase require kernel BOOTTIME below 300 seconds. A fixed host
window 360 seconds after the original N completion grants only the declared
physical-return phase, with offline proof pending and device activity unknown.
One returned 1800-second/one-operation attended grant, one original A, full
Android32 health and all existing no-replay/physical-recovery rules remain.
Prior consistency recovery and later mountless-file retrieval are separate
reviewed owners; neither is silently included in this pilot. All other target
and boundary conditions remain unchanged.

## S22+ Debian storage-first file evidence

The separately reviewed [storage-first sibling](S22PLUS_DEBIAN_FILE_FIRST_V1.md)
specializes boundaries 2 and 3 only for `debian-file-first-v1` and its fixed
`debian-failure-observer-v1` variant under the existing attended early-file owner. It retains every file-pilot lifecycle, exact target,
clean full-root admission, 16 KiB exclusive-file, absolute deadline, one-shot
cleanup and physical-return limit. Its sole preparation change is stock logger
plus the retained 67-module prefix, then the existing eight UFS modules, then
protected admission and checked file header/log/READY before the six remaining
fixed module insertions. Version-2 chained BEGIN/result records require checked
write, synchronization and readback before each later effect. Stock retained-RAM
logging and same-returned-boot bounded retrieval reuse the integrated logging
mechanism. No gadget, host challenge, installed code, replay, repair or additional
partition write is authorized. Separate reader and recovery owners remain separate.
The same policy separately adopts `debian-failure-observer-v1`: only its fixed
per-helper supervisor/worker pair, anonymous shared RAM, bounded authenticated
kernel-log outcomes and version-3 supervised file evidence are added. All
storage surfaces, original deadlines, physical recovery, separate-reader and
no-replay limits remain unchanged. Missing/reaped/pending worker records add no
cancellation, descendant-settlement, cleanup or recovery proof.

## S22+ streamed protected preparation

The separately reviewed [staged preflight V1](S22PLUS_NATIVE_STAGED_PREFLIGHT_V1.md)
is adopted only as V3's `staged-preflight`: one returned attended grant, one
operation and at most 1800 original BOOTTIME seconds. Healthy original A,
one fresh N, authenticated native health, one intended fixed EXEC, DETACH,
same-boot CONTROL, one original-A transfer and Android32 final health form
the complete graph. There is no admission, E, reentry, reconnect or extra probe.

The root inspector's exact entry-41/GPT/RO/clean-root guards and owned cleanup
remain. The fixed pinned `e2fsck -fn` executes before mounting; no ambient
checker configuration or external journal is admitted. After full root
closure, only two fixed unprivileged loader checks may use private readonly
exec mounts. Checker/loader children have zero capabilities, no_new_privs,
closed extra fds, fixed resource/output limits and the inherited outer ACM
command group. No filesystem write, repair, module reload, mdev scan,
installed-init execution, service/network startup or PID 1 handoff is added.

Each stage's raw stdout is durably captured through the existing authenticated
transport. H0 prefix rederivation may identify only received stage markers;
it cannot turn a missing EXIT/DETACH/close or unresolved cleanup/group into
completion, native health, recovery or a retry. Existing V3 physical original-A
recovery and health-only continuation retain their no-replay rules. Separate
independent review and image qualification are required before the exact
target may activate a finite grant. Fixed preparation D0 is the unchanged
Android root-health/shell-v2/GPT/statfs profile, with no control or transfer.

## S22+ readonly root-transition witness

The separately reviewed [root-transition witness V1](S22PLUS_SWITCH_ROOT_WITNESS_V1.md)
is adopted only as V3's `switch-root`: one returned attended grant, one
operation and at most 1800 original BOOTTIME seconds. Healthy original A,
one fresh N, authenticated first-boot native health, a fixed parent-PID1
terminal request, readonly root transition, separate post-exec witness and
one fixed Download/original-A return form the complete graph. There is no
admission, E, prior tail, reconnect, reentry or additional operation.

The unique pre-request compound intent consumes both the terminal transition
and its sole fixed witness return. A separately durable continuation receipt
binds that return to the original intent/run/boot/nonce and target departure
snapshot. Neither partial delivery nor later observation renews any effect.

The exact three native worker slots must settle before protected checker/root
admission. Partition-only BLKROSET, clean-superblock and full root/GPT checks
retain their no-write invariants. PID1 owns checker failure settlement itself.
Only the pinned static BusyBox and RAM witness execute; native_data retains
readonly/nodev/nosuid/noexec and block RO until reboot. Explicit mount moves,
ordinary old-run/work-tmpfs unmounts, descriptor closure and sealed same-boot state
precede the irreversible switch_root. The same ACM descriptor and gadget
survive this readonly unit; installed Debian init and NCM are not selected.

Actual post-exec PID1/root/executable/mount/FD and worker proof is distinct
from a pre-exec marker, return acceptance and final health. Authenticated
prefixes may preserve a reached witness but grant no replay or closure.
BusyBox late exec/kernel failure may leave unknown activity; existing
attended physical original-A recovery remains the only authorized fallback,
without an automatic-recovery claim. Exact A transfer and full rooted Android32
health retain their one-shot/health-only continuation semantics. Separate
source review, A/B qualification and returned finite grant remain required.
The fixed foreground Android preparation D0 performs no mode change or image
transfer. No previous candidate, installation or task claim is reopened.

## S22+ fixed native_data journal recovery

The [separate V1 policy](S22PLUS_NATIVE_JOURNAL_RECOVERY_V1.md) is incorporated
only for the exact S22+ FYG8 Android32/native_data layout. Its V3
`journal-recovery` operation starts from fresh healthy original Android,
consumes one fresh N and one pre-EXEC writer intent under a returned attended
one-operation grant of at most 1800 seconds, and returns once to original A.

The strict writer may replay only the validated internal journal and perform
its exact successful finalization within entry 41. No ordinary fsck repair,
format, installation, GPT change, Debian handoff or external journal is added.
Conclusive child settlement, partition-only RO restoration, full read-only
checker/root admission and unchanged surrounding layout are distinct proof
requirements. Timeout, malformed evidence or I/O uncertainty selects attended
physical recovery without repeating an effect. Original A does not undo
native_data writes; partial recovery is possible and never grants a retry.
Independent review must cover this permanent write exception, source/tool
provenance, real ARM64 failure tests and the existing no-replay owner. H0 and
retained bindings open no grant and prove no current device health.

Its separately qualified `post-autoboot-p432-v1` comparison selection adds only
the two exact authenticated closed-run historical files adopted by automatic
boot V1 and canonical boot-count values 1 through 99999. The strict writer is
unchanged. All immutable metadata/content, single-link checks and complete
finite accounting remain required after replay. An unexpected file, including
a previously unseen runtime record, is a comparison failure, never authority
to delete, admit, repair or repeat replay.

## S22+ Debian-owned integrated initial boot and services

The separately reviewed [integrated boot V1](S22PLUS_DEBIAN_INTEGRATED_V1.md)
is incorporated only for `SM-S906N/g0q/S906NKSS7FYG8`, V3 operation
`debian-integrated` and profile `debian-integrated-v1`. It specializes boundaries
2 and 3 for one fresh boot-only N, one returned attended one-operation/3600-second
grant and one physical original-A return. No prior lane or consumed grant
selects this composition.

Debian shell is initial PID1. Fixed sequential children measure its actual
identity and prepare stock logger plus retained platform modules; the exact
pre-client SPMI provider barrier precedes consumer insertion. One temporary
PID1 entry owns the first raw ACM gadget, then one durably journaled and
separately authenticated compound start owns the eight UFS modules, complete
clean protected root admission, child/FD settlement, one native_data RAM RO
clear and fresh RW mount, root transition, installed SysVinit and fixed
rcS/runlevel-2/service continuations. No old native worker or native admission
is inferred. Display modules and native thermal workers are absent; this
composition claims no physical readiness, quiescence or automatic recovery.

The exact V2 immutable-root and individually bounded mutable-data comparison
remains mandatory before RW; no repair, replay, formatter, reinstall, archive
extraction or other-partition access is added. One original 300-second device
deadline includes 13 liveness samples over at least 120 seconds. Revision-4
bounded authenticated records and checked synchronization are adopted exactly
as defined in the integrated policy. Only its classified reporting I/O loss
after durable START may continue the already-authorized fixed service work
with ACM permanently disabled; all other required failures park. That branch
permits no reopen, RELEASE, gadget change or SSH.

Complete live runtime proof permits release of ACM and reconfiguration of the
same first g1 for pinned same-boot NCM/SSH health, then one separately journaled
fixed shutdown. Physical Download and one original A close normal or failed
outcomes, with no transfer replay and health-only continuation after proved A.
Userspace deadlines cannot recover a kernel stall. Initial, installed-PID1,
service, SSH, local record and final Android health proofs remain separate.
Only the already bounded same-returned-Android-boot retained-log D0 retrieval
is available after healthy closure. H0 qualification opens no grant.

## S22+ automatic Debian initial boot and installed services

The separately reviewed [automatic boot V1](S22PLUS_DEBIAN_AUTOBOOT_V1.md)
is incorporated only for exact FYG8/Android32 native_data entry 41, profile
`debian-autoboot-v1` and V3 operation `debian-autoboot`. It specializes boundaries
2 and 3 for one returned attended one-operation/3600-second grant, one fresh
boot-only N and one physical original-A return. Its unique transfer intent
owns the entire automatic startup; no old approval or consumed image selects it.

The policy's fixed logger/prefix68/UFS8/six-client preparation retains measured
Debian initial PID1 and checked child settlement. Complete clean protected root
admission precedes each of exactly two sequential writable lifetimes: one
bounded exclusive early file with checked sync/unmount/RO restoration, followed
by one installed-root lifetime. The second admission requires RO already set,
repeats complete root checks and verifies the exact owned early file against
its authenticated RAM copy. The original one-file and separately qualified
exact two-file `post-autoboot-p432-v1` selections retain their original meaning.
The separately reviewed `post-autoboot-p436-v1` adds only the third exact
historical P432 runtime file authenticated by the closed P436 reader, with
sealed path, root-owned 0600 single-link metadata, exact size and content hash.
Its two existing complete same-boot admissions remain mandatory before their
respective writes; the second additionally admits only the current owned early
file. Existing bounded mutable extras and canonical boot count remain unchanged.
No separate read-only N is required for this new selection; P434's old result
and P435's separate-P434 prerequisite remain unchanged. No wildcard history,
repair, replay, formatter, installation, raw
block-data writer, GPT change or other-partition write is added.

The fixed RAM witness and installed SysVinit use one absolute 300000 ms device
BOOTTIME deadline, bounded revision-5 local records, reaped rcS/rc2 children and
120-second service observation. The first g1 is attempted once directly as NCM;
network failure may leave local service proof without external access. There
is no early ACM or host continuation. Exact same-boot pinned SSH evidence/health
and one fixed journaled shutdown are separate from local completion. The host
has one original N-completion-derived 360-second observation window. Physical
Download/original-A return and complete health close the owner; uncertain
control never replays. A does not roll back native_data. No quiescence, watchdog
or automatic recovery is claimed. Later storage retrieval requires a separate
qualified finite reader. All other permanent boundaries remain unchanged.

The original separately qualified transition observer uses the existing stock logger
from five existing actors only: file worker, its supervisor, automatic entry,
RAM witness and initial installed hook. Independent authenticated bounded
records observe calls, results and explicit stops without adding a process,
storage file or workload prerequisite. Each actor has at most 96 records of
512 bytes and a 2000 ms cumulative userspace logging budget, clipped to the
unchanged device deadline; kernel stalls are not cancellable. Only this
qualified variant may select the fixed post-closure, same-returned-Android-boot
`last_kmsg` D0 read, at most 4 MiB in 30 seconds, with exact closed owner,
reviewed sources, raw-first capture and before/after health. This adds no
pre-closure read or new control. Missing returns/retention never locate a stall,
prove non-execution or authorize replay.

The separately qualified `post-autoboot-p436-v1` rcS variant adds only the
already existing rcS hook invocation and its immediate fork child as two
distinct actors, for seven total under those same per-actor limits. It observes
the existing record-write/sync/readback/close tail, first wait/sleep/heartbeat,
child reaping, rcS completion and child descriptor cleanup/exec attempt.
Source measurement inheritance is limited to the same pre-exec fork, with
separate sequence/budget and parent/fork identity joins. Post-BEGIN deadline
checks precede fork, record write and exec; original cleanup and failure
semantics remain. No new process, persistent output, writable lifetime or
workload prerequisite is added. The same fixed post-closure D0 and proof limits
apply; a pre-exec record alone never proves successful execution.

The separately qualified `post-autoboot-p440-v1` watchdog/idle variant adds
exactly the P437 early/runtime pair authenticated by the closed P440 reader,
for five immutable historical rows. Each row retains sealed path, root-owned
0600 single-link metadata, exact size and hash; both complete same-boot clean
admissions and existing mutable rules remain unchanged. It selects the same
retained kernel/modules with either the unchanged boot command line or exactly
one appended `cpuidle.off=1`, positively checked against the actual AP/boot and
fixed vendor-boot command line. No other header change or kernel modification
is permitted by this selection. Disabling cpuidle can increase idle power; the
existing deadlines and attended physical recovery remain required.

This variant selects the existing bounded watchdog observer in both idle
choices. Actor eight is the existing runlevel parent; the existing rcS parent
and runlevel parent may each make at most five proc observations before
12.5 seconds BOOTTIME, with 250 ms cumulative proc work per owner, 100 ms
discovery and 25 ms cached-read limits, within the same 2000 ms logging budget.
Only bounded comm/stat/wchan reads of one uniquely identified gh-watchdog
kernel thread are selected. No process, persistent file, watchdog/control
write, scheduler setting, workload prerequisite or deadline extension is added.
Read/logging failures end sampling without changing workload behavior; kernel
stalls remain uncancellable. The same fixed post-closure D0 applies. Samples
can perturb timing and prove neither pet success nor cause or recovery.
The variant still needs its own returned attended finite grant and current
qualification/review; consumed P437/P439/P440 actions are never reused.

The separately qualified `post-autoboot-p444-v1` phase variant adds only the
P441 early/runtime pair authenticated by the closed P444 reader, for seven
exact historical rows under the same metadata and two current-root admissions.
It replaces the optional proc samples with twelve fixed module-local entry/
offset kprobes from the sealed phase declaration and a RAM copy of the exact
serial rcS dispatcher. Only the existing rcS/runlevel parents configure and
read their initially absent `s22phase` tracefs group/instance; no extra process,
watchdog write, return probe, memory fetch or scheduler change is selected.
The instance is bounded to eight CPUs and at most 20 KiB per CPU. At most 28
kernel observations and 34 nonblocking dispatcher packets share one 2000 ms
phase budget, with 500 ms reserved for cleanup, and one authenticated RAM
handover. The original per-actor logger limits remain. Event admission and
normal pumping stop at 15 seconds BOOTTIME; this is not a hard kernel stop. Owned
disable/readback is attempted at the first scheduling opportunity, even after
a budget overrun. The remaining cleanup budget may drain and summarize already
owned records, admitting only event timestamps before that cutoff; it grants
no resumed sampling or rearming. Failed or unobserved cleanup leaves activity
unknown until physical original-A return. No rearming or uncertain-write retry
is permitted. Exact lifecycle, descriptor closure, loss semantics, callsites
and physical limits are in the incorporated automatic-boot policy. This
selection requires independent review, fresh qualification and its own
returned attended finite grant; P441 through P444 remain consumed.

The separately qualified `post-autoboot-p447-v1` single-CPU selection adds only
P445's complete early file authenticated by closed P447, for eight exact
historical rows; its runtime file is not admitted. Existing metadata, hash,
full-tree and both same-boot clean admissions remain mandatory. It uses the
P441 proc observer without phase instrumentation and appends exactly
`cpuidle.off=1 maxcpus=1` to the retained kernel command line, rejecting CPU/
idle conflicts in actual boot/vendor-boot input. It adds no CPU hotplug,
watchdog/control write, process, persistent file or writable lifetime.

Fixed CPU-online `0` is required before first admission. Before second
admission and at fifteen existing progress points, bounded CPU/driver-disable/
CPU reads must each return `0`, with revision-6 durable records binding sampled
CPU and software-enabled state. Two same-boot/count pinned SSH health responses
report CPU `0` and device uptimes at least 120000 ms apart inside the unchanged
300000 ms device and 360-second host limits and shared thirty-read budget.
These are sampled-state/access proofs, not continuous CPU/access, pet success,
hardware renewal or recovery proof. Local service proof and fixed shutdown
remain separate. Exact interfaces and read semantics are in the incorporated
policy. Independent review, fresh qualification, a returned attended finite
grant and physical original-A return remain required; no prior action is
reopened, repinned or replayed.

The separately qualified `post-autoboot-p451-v1` successor adds only P448's
complete early/runtime pair authenticated by closed P451, for ten exact history
rows. The closed physical producer and clean read-only source, exact metadata,
sizes and hashes remain bound. Both complete current-root admissions and the
single-CPU/revision-6 checks above remain mandatory. It replaces optional proc
sampling with the shared RAM serial dispatcher/channel only: no tracefs/kprobe,
observer handover, new process, persistent file or writable lifetime. The
existing rcS parent admits up to 34 fixed script packets and eight sparse
progress records in one 120000 ms relative window clipped to the original
300000 ms deadline and existing 2000 ms/96-record actor budget. Observation
admits at most 1500 ms and leaves 500 ms for later original records; kernel
stalls remain uncancellable. Each nonblocking
pump and final reap drain are bounded as specified in the incorporated policy.
Observation failure closes the channel without gating the original workload.
No service/helper inherits its descriptor. Collection time, individual script
status, dispatcher reap and functional service proof remain distinct; missing
records never prove a stall or non-execution. The unchanged host window,
functional proof, fresh qualification/review, returned finite attended grant
and physical original-A return remain required. No consumed predecessor or
historical complete-root rejection is changed.

The separately qualified `post-autoboot-p455-v1` minimal-boot selection adds
only P452's exact early/runtime pair authenticated by the closed clean P455
reader, for twelve historical rows. Both complete current-root admissions,
metadata/content checks and P454's negative comparison remain unchanged. Its
additional sealed required RAM asset checks inherited virtual mounts/devices
and the RAM lock directory, creates only absent RAM random/urandom character
nodes 1:8 and 1:9 with checked root-owned 0666 metadata, then runs hostname, mdev, urandom and
bootmisc before unchanged runlevel-2 services. The existing rcS child always
selects this minimal program, independently of optional channel success.
Required-input or script failure stops the workload. The five-step channel
admits at most twelve packets under the original budgets; it adds no process,
persistent file or writable lifetime. Script/packet completion is distinct
from service, SSH and shutdown proof. All original CPU/idle checks, deadlines,
physical original-A return, no-repair/no-replay rules, current independent
review and actual qualification precede a new attended finite grant. It adds
no recovery guarantee and does not repin consumed predecessors.

The separately reviewed [bounded ordinary-reboot specialization](S22PLUS_DEBIAN_REBOOT_V1.md)
adds only `post-autoboot-p457-reboot-v1`: two admitted boots and four fixed
native_data writable lifetimes sealed to pre-build mount count M, one ordinary
reboot and final shutdown, two original fixed host windows within the same
one-operation/3600-second attended grant, and original physical A recovery.
Both complete protected admissions remain mandatory in each boot. It adds
only its exact current/history files, finite packaged-log rotation rules and
optional producer-derived old shutdown file; no wildcard, repair or replay.
Its named `debian-reboot-baseline-d0-v1` permits the current foreground task's
fixed existing-node 4096-byte native_data read with exact closed-return/GPT/
Android32 binding and same-boot health brackets after current review/adoption.
It requires no physical attendance or per-read request, adds no mount, ioctl,
node, helper, write or control, and is not full-root admission. Synthetic H0
baselines cannot admit physical use. No consumed artifact or grant changes.

The separately reviewed [bounded cron specialization](S22PLUS_DEBIAN_CRON_V1.md)
adds only `post-autoboot-p458-cron-v1`: fixed packaged cron stop/start/restart
before the unchanged stable-service observation, one fixed boot-1 job and one
512-byte exclusive report on native_data, authenticated by both boot-2
admissions and compared exactly with its acknowledged first-boot bytes.
Its exact RAM crontab is armed once and retired before the output attempt;
an exclusive RAM intent prevents retries by already queued invocations.
Only its separately owned one-shot RAM revocation remains allowed on failure
or expiry: revoke the exact READY and mounted schedule inodes, set the schedule
mtime to zero to invalidate cron's cached system table, and record their
outcomes in RAM. It adds no disk write, control retry, renewed workload budget
or quiescence claim; in-flight effects remain uncertain and physical A is required.
Original PAM behavior is retained and temporary output is confined to an
8 MiB/512-inode RAM `/tmp`. It retains the original two-boot/four-lifetime
owner, fixed pre-build D0, no-replay rules and physical original-A return.
The four exact final P458 snapshots are prospective producer-derived input,
not post-Android retention proof. Package installation, persistent-config
changes, wildcard admission, filesystem repair and automatic recovery remain
outside this specialization. Current review, real qualification and a fresh
attended finite grant are still required; no consumed record is repinned.

The separately reviewed [persistent cron configuration specialization](S22PLUS_DEBIAN_CRON_CONFIG_V1.md)
adds only `post-autoboot-p459-cron-config-v1`, namespace `p460`. Boot 1 creates
one sealed root:root 0644 cron.d file after daemon/cron-process settlement;
scheduled first-boot invocations cannot claim an intent or write a report.
Both boot-2 admissions require its exact contents, inode and nanosecond
mtime/ctime joined to authenticated first-boot creation and reboot records.
One real second-boot cron job creates a 512-byte exclusive native_data report.
Checked completion, a final atomic RAM success publication and worker
settlement precede any retirement. Normal retirement requires a fresh
successful RAM gate-revocation claim, one daemon stop, settled current-root
cron/PAM processes, exact held-file verification, one unlink and parent sync,
then one verified daemon start before completion. A prior abort claim or a
readable failed completion/revocation record cannot authorize retirement.
Only fixed one-shot RAM gate revocation remains allowed after failure/expiry;
there is no disk cleanup, control retry or guaranteed configuration removal.
The same two-boot/four-lifetime attended owner, fixed baseline D0 and physical
original-A return remain. Five P459 final producer snapshots are prospective
exact expectations, not post-return retention or present-clean-state proof.
Package installation, general configuration mutation, repair, automatic
recovery and any consumed-operation replay remain outside this specialization.

## S22+ native-first installed-Debian handoff

The separate [handoff V1 policy](S22PLUS_DEBIAN_HANDOFF_V1.md) specializes
boundaries 2 and 3 only for exact FYG8/Android32 native_data entry 41. One
returned attended V3 `debian-handoff` grant permits one operation and 3600
original BOOTTIME seconds. It starts from healthy original A, installs one
fresh archive-free N, proves native first-boot health and performs the fixed
protected worker/checker/full-root admission before a single writable lifetime.

The unique compound intent owns ordinary unmount of the protected root, one
partition-only RO clear/readback, a fresh normal RW mount, actual PID1
switch_root/RAM witness, installed init and native ACM retirement. The witness
and first synchronous SysVinit hook use the original run/nonce/boot and
300-second deadline. Fixed continuations require independently retained prior
proof and cannot renew authority. Failed hooks park and cannot release rcS.
Only fixed RAM overlays and device-node preparation are added; the physical
artifact excludes VM substitutions, an installation archive and formatters.

The hook proves actual installed PID1 and native-fd retirement before native
ACM unbind. Exact NCM selection and pinned SSH must join that same kernel boot.
Only health and one separately journaled fixed shutdown are selected. There
is no package workload, ordinary reboot, generic remote command or N admission.
Normal return pauses for attended physical Download under one original bounded
continuation. Existing exact endpoint/Odin revalidation precedes one original
A transfer and full rooted Android32/GPT health. Uncertainty never replays
the handoff, shutdown or A. Completed A permits only remaining health reads.

This permits normal Debian root/service writes only on native_data, with no
repair, reinstall, partition-table change or access to Android data. Forced
return may leave that filesystem dirty; Android health and NCM departure do
not prove clean ext4. Current independent source review and A/B qualification
are prerequisites, never live authority. All older consumed records remain
immutable. The fixed predecessor preparation D0 remains separately bounded.

### Debian progress and same-gadget successor V2

The separate [V2 policy](S22PLUS_DEBIAN_HANDOFF_V2.md) specializes the same
exact FYG8/Android32/entry-41 exception for a fresh one-operation attended
V3 grant. P410 V1 is consumed and closed; its frozen source, review and grant
do not acquire V2 semantics. Only profile
`thermal-v3-reconnect-ufs-drain-debian-handoff-v2` selects the successor.

Protected admission keeps the exact archive except its one declared mutable
wtmp data file, and individually checks only the V2 policy's bounded optional
log/seed/boot-count paths. All other additions and mutations are rejected.
Clean superblock, complete unprivileged checker, exact GPT/markers/witness and
partition RO remain mandatory. Dirty or ambiguous roots stop before RW, with
no repair or journal replay. The prior pristine comparison is not relabelled
as evidence of the current root.

Fixed read-only RAM overlays select sequential Debian wait children: installed
init proof, host-retained START, actual rcS, actual runlevel 2 and thirteen
same-boot/init/cron/sshd samples spanning 120 seconds. Native preparation and
Debian observation retain one 300-second deadline through authenticated release
acceptance. Started services or an uncertain later USB operation may remain
active; failure requires the bound attended recovery. Every executed rc child has
closed ACM/state descriptors; there is no competing native manager or respawn.
The system crontab is temporarily empty; no package workload is selected.

For fresh reviewed revision-4 helpers only, V2 additionally permits one
exclusive bounded per-run evidence file and its fixed parent on native_data
after protected admission. Checked durable START precedes its ACK. A known
reporting I/O loss after START may disable ACM permanently for the remaining
fixed startup/service observation under the same deadline. The authenticated
local chain must record the loss before continuation; subsequent hooks cannot
reopen/send, receive RELEASE, change USB or request shutdown. They finish the
bounded local observation and park for the bound attended physical recovery.
Storage, identity, authentication, close, child/service and deadline faults
remain fatal. Exact paths, 15,616-byte bound, error classes, checked sync and
no-replay limits are in V2. This specializes only reporting failure behavior
inside that already-owned operation; it leaves pre-RW admission unchanged and
grants no persistent-file retrieval action or authority for a later boot.

The existing compound intent owns all phases. Independently retained runtime
proof precedes fixed release, final ACM close and exact UDC unbind. Debian
then reconfigures the same original g1; it must not delete that gadget or
create a second one. Partial transition uncertainty stops without replay.
Same-boot pinned SSH, one fixed shutdown, original physical Download/A recovery
and Android32 health retain their original limits. Independent changed-closure
review and exact A/B qualification are required; H0 opens no grant and does
not establish fresh device health or current filesystem admission.

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

## S22+ native ext4 initialization and witness

The [native ext4 V1 policy](S22PLUS_NATIVE_EXT4_V1.md) is a separate review-gated
exception to boundaries 2 and 3 for only `SM-S906N/g0q/S906NKSS7FYG8`. It uses
the completed P398 Android32 layout without any GPT changes: entry 40 remains
32 GiB userdata; entry 41 native_data spans 4096-byte LBAs 12,115,456 through
62,305,023 (205,576,470,528 bytes). Every other partition remains unchanged.
Only the reviewed fixed native helper may format this exact partition once,
mount it, create/read one fixed 4096-byte witness, synchronize and cleanly
unmount. Its later fresh-boot verification is read-only with `ro,noload` and
`e2fsck -fn`, never repair. The fixed format options exclude discard, offsets,
external journals, population and caller-selected paths/options.

It expressly permits the private RAM-only block nodes, private mount namespace,
whole-LU read-only full GPT comparison and bounded filesystem/checker reads
described by that policy. The whole disk is never writable. The live sysfs
userdata/native maps and sealed GPT must agree before filesystem access.
The ordinary ext4 journal and filesystem metadata writes remain confined to
entry 41. There is no raw host writer, userdata reset, GPT restoration, Debian
staging, key request or additional partition authority.

This capability uses the existing V3 owner and finite attended grant, at most
two operations and 7200 original BOOTTIME seconds: optional fresh reader-N
bootstrap and one fixed N/E/N/A transaction. One target/partition claim and
durable pre-EXEC intent consume initialization even on timeout or uncertainty.
UUID/image changes cannot renew it. Unknown writers permit no further
filesystem commands. Actual attended bootloader Download arrival precedes the
one original-A transfer; the closed P398 Android32 return basis remains bound.
No recovery reformat is permitted. Android return does not undo initialization
or prove a filesystem whose result is incomplete. Final Android root health,
unchanged full GPT and exact capacity are independently required.

The exact target adoption, independent review of this exception and reachable
owner/native closure, actual A/B artifact qualification and an explicit returned
finite task grant are required before any effect. This is a permanent narrow
exception, not a temporary gate or an extension of consumed G2 authority.

## S22+ Debian first installation and full PID 1 handoff

The [Debian first-boot V1 policy](S22PLUS_DEBIAN_FIRST_BOOT_V1.md) is incorporated
at this same common-contract precedence as a separate review-gated exception
to boundaries 2 and 3, only for `SM-S906N/g0q/S906NKSS7FYG8`. One fresh boot-only
image embeds a content-bound archive and fixed installer. It may populate only
the existing exact native_data extent and then exec Debian SysVinit as initial
PID 1. It preserves the complete Android32 GPT, filesystem identity and witness;
it has no formatter, repair, GPT writer, Android staging or other-partition
authority. Private RAM block aliases, full read-only GPT checks and the fixed
filesystem checker have precisely the incorporated policy's scope.

One attended grant binds at most 7200 original BOOTTIME seconds, one candidate
transfer/installation, one fixed service/package workload, one ordinary Debian
reboot, one shutdown request and one original-A restoration. A durable host
installation claim precedes any possible candidate boot. An exclusive synced
device start marker precedes extraction; partial/dirty state never reinstalls.
Debian owns its declared services and local pinned-key NCM/SSH link. The policy
explicitly admits ordinary native_data metadata/journal and declared rootfs
writes; it does not claim a zero-write Linux lifetime.

The shared target lease/F1 owner/content registry remain mandatory. A durable
effect survives host loss; recovery journal epochs preserve earlier intents
without renewing research. Only actual attended exact Download arrival permits
the original-A transfer, and an A intent permits no retransmission. Recovery
does not depend on candidate-only inputs or unexpired research time. Android
root/partition hashes, unchanged GPT and exact Android32 capacity close the
return separately from native filesystem integrity. This permanent narrow
definition needs exact target adoption, independent source review, actual
artifact qualification and an explicit returned finite grant before effects.

## S22+ installed Debian PID 1 and native return

The [installed Debian boot V1 policy](S22PLUS_DEBIAN_INSTALLED_BOOT_V1.md) is
incorporated at this same common-contract precedence as a separate narrow
exception to boundaries 2 and 3 only for `SM-S906N/g0q/S906NKSS7FYG8`. It
reuses the completed P401 root as a sealed input without reinstalling: one
fresh boot-only P405 successor has no root archive or installation path, verifies
the completion markers, full retained root files and exact native_data/GPT
identity before writable handoff to Debian SysVinit as initial PID 1. Ordinary
ext4 metadata/journal and declared Debian root writes remain confined to entry
41. No filesystem repair, reformat, GPT change, userdata mutation, rootfs
replacement or other partition payload is permitted.

P404 remains consumed and closed with proved original-A health. Its result is
not replay authority or proof of current native_data health. The P405 bootstrap
must establish clean exact storage and the retained root before writable
handoff; an interrupted or dirty root is never repaired by this exception.

One finite, physically attended, 3600-second BOOTTIME grant binds one P405
transfer, bounded authenticated Debian health, one orderly shutdown request,
one attended Download arrival and one distinct boot-only P399 `v0.3.1-rc.1`
normal restoration. The consumed P399 admission is evidence for this exact
normal role, not reusable authority from its old grant. A fresh authenticated
native boot, clean read-only filesystem witness, DETACH and descriptor close
may end in a healthy native terminal without transferring A. Failure instead
retains one separately intended, attended original-A transfer and exact final
Android32 rooted/GPT/partition/capacity health. There is no automatic or
deferred physical recovery. An intended transfer/control never replays; proved
raw completion permits only journal/report/health continuation.

The global target lease, F1 owner and content registry remain mandatory.
Candidate-only source drift and grant expiry never cancel an already-owned A
recovery, while current recovery-critical sources and exact A/target binding
remain required. This exception does not renew P401 installation, P399's old
roles, or any other S22+/A90/S20+ capability. It requires exact target adoption,
independent final source/authority `PASS_GO`, actual P405/P399/A qualification,
current health and an operator-returned attended grant before effects.

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
