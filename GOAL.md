# Goal: S22+ boots into Debian with full userspace ownership

Build a usable Debian arm64 system on dedicated storage, with Debian's init
as **host PID 1 in the initial PID namespace** and Debian owning the running
system's services, devices, networking, logging and shutdown. The operator
selected this full handoff on 2026-09-16: a resident native supervisor with a
Debian chroot or an isolated Debian child is not the product architecture.

The actual allocation is **32 GiB Android userdata and 191.4580078125 GiB
native storage**. Start with the FYG8 vendor kernel. Reduce native userspace to
the device-specific early boot work needed to start Debian, then replace that
bootstrap with Debian init. Do not implement a second general Linux runtime
inside native init. Existing native capabilities are implementation inputs;
they are not all prerequisites for Debian boot or permanent background owners.

First deliver an independently booted, persistent headless Debian system with
authenticated SSH and an ordinary package-managed service. Display/input and a
desktop are later capabilities. Android remains a separately booted management
and recovery environment, not a provider of the running Debian userspace.
This goal records state, never device authority. Select only the operator-owned
`SM-S906N/g0q/S906NKSS7FYG8` through `AGENTS.md` and its binding target contract.
A90 and S20+ remain isolated.

## Current synthesis and functional priority

The [integration synthesis](docs/reports/S22PLUS_DEBIAN_INTEGRATION_SYNTHESIS_2026-10-13.md)
retains P410/P413's installed-PID1/rcS-entry proof and the earlier logger findings.
[P425 H0](docs/reports/S22PLUS_DEBIAN_INTEGRATED_P425_H0_2026-10-13.md) retains its
reviewed VM service/SSH/shutdown evidence; its physical candidate is consumed.
P430 proves storage-first preparation; installed services, NCM and same-boot SSH remain the physical gap.

## P437/P438 closed healthy; first watchdog renewal remains the runtime gap

The [P437 run](docs/reports/S22PLUS_P437_RCS_OBSERVATION_RUN_2026-10-19.md) consumed
one N/A pair and closed ANDROID_CLOSED_HEALTHY, with no F1 owner or qualified
NCM/SSH in its 360-second window. Its 132 authenticated records prove installed
Debian PID1, rcS fork, checked fork-record persistence, child fd cleanup, exec
attempt, first WNOHANG wait and first 10ms sleep return. Last stage is
RCS_SLEEP_FIRST; child exec/rcS completion, services/SSH and clean shutdown are
unproved. One post-A ADB read failure was preserved before health-only closure;
the 16-capture retained-log D0 passed both same-boot brackets. A90/S20+ were untouched.
The [pre-transfer attempt](docs/reports/S22PLUS_P437_PRETRANSFER_STOP_2026-10-19.md)
remains separately consumed/closed N=0/A=1. The
[host correction](docs/reports/S22PLUS_P437_TRANSFER_GUARD_H0_2026-10-19.md) retains
43 tests, six integration cases and PASS_GO; runtime/41 VM cases were unchanged.

The [boot audit](docs/reports/S22PLUS_P437_BOOT_REQUIREMENTS_WATCHDOG_H0_2026-10-19.md)
separates two candidate boots. The first has gh-watchdog RT throttling at
11.988s and watchdog bark/bite/reset at 12.739s; the 317s messages belong to the
second boot. First heartbeat was due only around 16.175s. Exact missed-renewal
cause and second-boot write/rejection state remain unknown. The
[inactive observer](docs/reports/S22PLUS_WATCHDOG_OBSERVER_H0_2026-10-19.md) has
host/ARM64 task-state/CPU-time/wait-symbol checks using existing parents; it
remains disabled and unqualified for a new physical candidate.

The [P438 read](docs/reports/S22PLUS_AUTOBOOT_EVIDENCE_P438_RUN_2026-10-20.md) consumed
one N/A pair and closed ANDROID_CLOSED_HEALTHY, with no F1 owner. Its 10,972-byte
early file authenticates all 14 records of the first P437 boot; runtime file is
ABSENT_IN_HOME_VIEW with state=1/recover=1/orphan=0. No mount/replay/data write
occurred. One post-A ADB read failure preceded health-only closure. Exact root
admission remains unresolved; fixed journal-recovery/history assessment remains
separate from watchdog diagnosis. The consumed grant gives no further authority.
The [P436 read](docs/reports/S22PLUS_AUTOBOOT_EVIDENCE_P436_RUN_2026-10-18.md) retains
P432 installed PID1/rcS-fork proof. P432–P434/P436 are consumed/healthy; P434 is
RECOVERY_NOT_PROVED and P435 remains unstarted with its original prerequisite.

The [stock FYG8 comparison](docs/reports/S22PLUS_FYG8_STOCK_FIRST_WATCHDOG_H0_2026-10-20.md)
joins original firmware, effective source, module binaries and retained boots.
Stock selects qcom-cpu-lpm early; its compiled sleep_disabled default keeps
state 0/WFI, whereas P437 omits qcom_lpm and initially selects menu. Stock's first
periodic pet at 10.24s precedes post-boot scripts at 16s+. This is a concrete idle
policy difference, not a proved cause: P430 has the same actual diagnostic
kernel and 82 module rows as P437 and survives about 369s. Neither kernel is
byte-identical to the shipping Image. Further H0 binds WFE/data references,
the cpuidle.off-to-WFI path, actual ramdisk differences and FYG8 hyp pet/status
shared locks. P437's successful bark-time status constrains permanent shared-lock
deadlock; P430/P437 differ beyond rcS. The cause and a missing-service fix remain unproved.

## P430/P431 closed: early PID1 and durable file proved; Android healthy

The [physical report](docs/reports/S22PLUS_DEBIAN_P430_P431_PERSISTED_EARLY_PID1_RUN_2026-10-16.md)
records **PASS_PERSISTED_EARLY_PID1_PRE_UNMOUNT**: measured Debian initial PID1,
76 preparation modules, six later client returns and all 14 chained records in
a 10,972-byte file retrieved after Android recovery. RAM and file join the same
writer boot. The later mountless read is clean; writer unmount return remains
unproved. Both operations are consumed and **ANDROID_CLOSED_HEALTHY**, each
with one N/A pair and no remaining F1 owner. A90 and S20+ were untouched.
The [boot-flow audit](docs/reports/S22PLUS_DEBIAN_BOOT_FLOW_CODE_AUDIT_2026-10-16.md) maps the next autonomous Debian path.
Resolve evidence-file admission and coupled host gates before qualifying installed init/services/SSH.
P428/P429 remain consumed and closed healthy; their absent evidence grants no replay.

## P426/P427 closed: file absent; UFS preparation prefix; Android healthy

The [physical report](docs/reports/S22PLUS_DEBIAN_FILE_FIRST_P426_P427_RUN_2026-10-13.md)
records one P426 storage-first trial and one separately bound P427 mountless
reader, each under its returned attended 1800-second/one-operation grant.
N/A counts are 1/1 for each; both are **ANDROID_CLOSED_HEALTHY** and consumed.
Each preserved one post-A ADB device-not-found read, then completed health only
without repeating a transfer. No F1 owner remains; A90 and S20+ were untouched.

P426's returned-boot RAM capture authenticated 156 records: 75 completed
modules, last `ufshcd_crypto_qti`, followed by `ufs_qcom` BEGIN. This is partial
preparation evidence, not an exact stop/cause or full storage/initial-PID1 proof.
P427 completed its fixed partition-RO read without mount, replay or data write.
The superblock view was clean (`state=1`, `recover=0`, `orphan=0`); the sealed
P426 file was `ABSENT_IN_HOME_VIEW`. The joined result is **NO_AUTHENTICATED_FILE**.
File absence does not prove non-execution or authorize a replay. Physical
filesystem logging, installed Debian services and SSH remain unproved.

The [H0 qualification](docs/reports/S22PLUS_DEBIAN_FILE_FIRST_P426_H0_2026-10-13.md)
retains A/B artifacts, 14 writer/four reader ARM64 VM cases, 190 tests and
independent `PASS_GO`. Any successor needs a fresh bounded selection; diagnosis
must distinguish module return, storage admission, recording and retention.

## P425 closed: logger/providers proved; USB unproved; Android healthy

The [P425 physical report](docs/reports/S22PLUS_DEBIAN_INTEGRATED_P425_RUN_2026-10-13.md)
retains its consumed one-N/one-A ANDROID_CLOSED_HEALTHY closure, absent USB in
90 seconds, unsent integrated-start, deadline-tail/ADB read failures and
health-only continuation. Strict H0 rederivation of unchanged returned raw proves
146 same-boot records through logger binding, gpi completion, provider mask=7
and i2c_msm_geni BEGIN: PARTIAL_AUTHENTICATED_EARLY_PREPARATION. Exact stop,
initial-parent measurement, installed PID1, services/SSH and clean shutdown
remain unproved. No F1 owner remains; consumed authority is not renewed.

## P424 closed: authenticated PRE retained; Android healthy

The [P424 physical report](docs/reports/S22PLUS_NATIVE_LOG_CALIBRATION_P424_RUN_2026-10-13.md)
retains CALIBRATION_NEGATIVE (stage 4 ENODEV after module return, no POST) and
one authenticated PRE after return: PARTIAL_NATIVE_LOG_RETENTION. The device-name
predicate mismatch informed P425, without proving the old aggregate's exact
failing predicate. One N/A pair closed ANDROID_CLOSED_HEALTHY after preserved
USB inventory/ADB failures and health-only continuation; no F1 owner remains.
The [H0 report](docs/reports/S22PLUS_NATIVE_LOG_CALIBRATION_P424_H0_2026-10-13.md)
retains nine ARM64 cases, 108 tests, six malformed negatives and PASS_GO.
Complete calibration, earliest Debian PID1 and historical P421/P423 execution
are unproved. P420–P424 are consumed/closed; A90/S20+ were untouched.

## P423 closed: no authenticated early stage; Android healthy

P423 `debian-stage-probe-v1`, `v0.5.0-rc.7`, consumed its returned attended
1800-second/one-operation grant on 2026-10-13 KST. Fresh original-A health and
the qualified source/artifact/recovery bindings passed. One candidate transfer
and the original 90-second host window completed. The operator entered
physical Download, and one original-A transfer completed. See the
[physical report](docs/reports/S22PLUS_DEBIAN_EARLY_STAGE_P423_RUN_2026-10-13.md).

The first post-return ADB health read stopped with `error: closed`. The existing
health-only continuation then proved original boot/root, changed Android boot
and Android32/GPT health without another transfer: **ANDROID_CLOSED_HEALTHY**,
`recovered=true`, `research_closed=true`. N/A counts are 1/1. The candidate and
grant are consumed/closed, and no F1 owner remains. A90 and S20+ are untouched.

After closure, the fixed same-returned-Android-boot `last_kmsg` D0 read succeeded
with 2097136 raw bytes and healthy before/after brackets. The reviewed decoder
and process-blocked H0 rederivation returned **NO_AUTHENTICATED_STAGE**:
zero records, damaged candidates or foreign frames, and no `S22STG1` prefix.
Readable retained RAM does not establish that P423's boot was retained.
Debian early PID1, logger insertion/binding and completion remain unproved.
Absence cannot locate a stopping point, prove non-execution or permit replay.

The [H0 qualification report](docs/reports/S22PLUS_DEBIAN_EARLY_STAGE_P423_H0_2026-10-13.md)
preserves the six ARM64 cases, A/B artifacts, 109 tests and independent
**PASS_GO**. That capability evidence does not replace physical proof. P423
selected only one stock logger and no platform/USB/UFS/block-backed workload.
P421's stopping point remains unknown. P424's subsequent native calibration is
recorded above; it does not establish P423 execution. Full Debian/SSH ownership
remains unachieved.

Subsequent H0 inspection found only 52–59-minute kernel-style timestamps and
Android process text in the retained sample, while P423's candidate interval
was about 119 seconds. Older Android content is the supported interpretation,
not a proved P423 transcript. The physical report records the remaining blind
spot: several early checks can stop before the retention module is loaded,
whereas the VM observes serial output with Samsung module operations substituted.
An independently established earliest observation path is needed to separate
these cases; the exact failure stage remains unknown.

## P422 retrieval closed: no P421 file; Android healthy

P422 `v0.5.0-rc.6` consumed its own returned attended reader grant on
2026-10-13 KST. The fixed mountless reader completed, reporting
**PASS_ROOT_EVIDENCE_OBSERVED** with `state=1/recover=0/orphan=0`, partition RO,
no mount/replay/write, and a successfully settled child. P421's exact sealed
file was **ABSENT_IN_HOME_VIEW**. The reviewed collector joined both closed
operations and returned **NO_AUTHENTICATED_FILE**. See the
[retrieval report](docs/reports/S22PLUS_DEBIAN_FILE_P422_RETRIEVAL_2026-10-13.md).

One normal authenticated Download return and one original-A transfer passed
full root/original-artifact, changed-boot and Android32/GPT health:
**ANDROID_CLOSED_HEALTHY**, `research_closed=true`, `recovered=false` (normal
return, no fallback). N/A counts are 1/1, with no failed raw acquisition or
retry. H0 closure checked 646 raw captures, 261 frozen source paths and the
unchanged 18-row journal. The grant/candidate are closed/consumed; no F1 owner
remains. A90 and S20+ remain untouched.

The clean superblock view is later than P421, but is not full root admission,
P421 unmount proof or evidence of its stopping point. Missing records never
prove non-execution. P421's early Debian PID1, preparation and file write remain
unproved; it must not be repeated. Its original
[window and physical-return report](docs/reports/S22PLUS_DEBIAN_FILE_P421_RUN_2026-10-13.md)
retains the historical `AWAITING_OFFLINE_FILE_RECORD` close result. P422's later
collector supplies the separate final file verdict without rewriting that run.

P420–P422 are all closed. This result motivated P423's bounded early-stage
observation above; it did not authorize a replay or locate the writer's failure.

## P420 proved clean native_data and returned Android healthy

The operator selected native_data consistency first, then initial-Debian-PID1
file logging and retrieval of the same run after Android recovery on
2026-10-12 KST. The bounded route is P420 strict native_data recovery/check,
P421 `debian-file-pilot-v1`, then P422's separate sealed mountless reader.
Each has its own original-A closure; no old candidate or consumed grant is
reused. P420 consumed its one attended grant on 2026-10-13 KST. The
[physical report](docs/reports/S22PLUS_NATIVE_DATA_P420_RUN_2026-10-13.md)
records initial `state=1/recover=1/orphan=0`, successful strict journal
finalization, then `clean=1/recover=0/orphan=0`, a successful read-only checker
and all 8969 expected root entries matching with zero findings or extra paths:
**PROVED_CLEAN_ROOT**. Only the two finalization writes occurred (5120 bytes).
No ordinary filesystem repair or installed Debian execution was selected.

Normal authenticated Download and one original-A transfer completed. The first
Android-final ADB read lost the target; health-only continuation then proved
full original boot/root, changed-boot and Android32 GPT/capacity health without
another transfer. Terminal: **ANDROID_CLOSED_HEALTHY**, `recovered=true`,
N/A counts 1/1. The candidate and grant are consumed/closed, with no F1 owner.
P420 established the first route prerequisite. Its filesystem observation
predates P421 and does not prove P421 file retention or Debian boot.

P421 keeps Debian shell `/init` as initial PID1, reuses the 73+8 fixed module
plan, requires fresh complete clean-root admission, then creates one exclusive
run-bound file of at most 16 KiB. It needs no gadget or USB challenge. Checked
file/parent sync and one normal unmount are required; the final persistent
record is explicitly before unmount. Original Android return is physical.
After its healthy closure, P422 reads that exact file without mounting or
replaying a journal. H0 analysis joins the two closed operations and verifies
the file's run, source, boot and chained authentication from raw captured bytes.
Missing records do not prove non-execution, and Android health does not prove
native_data cleanliness. Records cannot exist before storage/root admission.

The [preparation report](docs/reports/S22PLUS_DEBIAN_FILE_ROUTE_P420_P422_H0_2026-10-13.md)
records actual A/B qualification, 12 file-route and six strict-recovery ARM64
cases, 110 focused tests and independent PASS_GO. P420 closure additionally
rederived 578 raw captures and 263 frozen source paths without device commands
or journal changes. P421 subsequently consumed its separate grant as recorded
above. P422 subsequently consumed its separate grant and closed with the
absent-file result and healthy Android return recorded at the top. All three
candidates remain consumed. A90 and S20+ remain untouched.

## P419 RAM-only trial closed healthy; USB still unproved

The operator selected the next minimum USB experiment on 2026-10-12 KST.
P419 `v0.5.0-rc.3` keeps Debian shell `/init` as initial PID1 and the retained
73-module platform/USB sequence. Its explicit `ram-only` build removes the
added `sec_log_buf` and printk readback prerequisites. Complete checked RAM
preparation records, actual parent identity and authenticated USB evidence
remain mandatory. No UFS/root/storage work is selected.

The one attended trial was consumed on 2026-10-12 KST. The
[physical report and timeline](docs/reports/S22PLUS_DEBIAN_USB_RAM_P419_RUN_2026-10-12.md)
record no exact early USB endpoint within 90 seconds, before tty/challenge
acquisition. USB/PID1 remains **NO_PROOF**. The operator observed an unchanged
boot screen with no bootloop; no internal-stage conclusion follows from that.
Physical Download and one original-A transfer completed, followed by a
health-only continuation after one failed ADB read. Full original boot/root,
changed-boot and Android32 GPT/capacity checks passed: **ANDROID_CLOSED_HEALTHY**,
`recovered=true`, N/A counts 1/1. The candidate and grant are closed/consumed,
with no F1 owner remaining.

The
[H0 preparation report](docs/reports/S22PLUS_DEBIAN_USB_RAM_P419_H0_2026-10-12.md)
records A/B artifact qualification, five ARM64 VM cases, 80 focused tests and
independent PASS_GO. Fresh fixed Android health/GPT/capacity preparation and
its H0 rederivation passed in `connected-2`; the first ADB-startup-banner read
failure is preserved. Physical closure revalidated 560 raw captures and 227
frozen source paths without device commands or journal changes.
This mode selected no post-return retained-log reader, and its RAM records
were not recovered. Removing the added logging prerequisites alone did not
establish USB; the internal failure location remains unknown. At closure no
successor was selected. P418 records are unchanged and P415 remains the last native_data
observation. A90 and S20+ were untouched.

## P418 partial retained-stage proof; USB unproved, Android healthy

P418 `v0.5.0-rc.2` consumed its one attended trial on 2026-10-09 KST.
The [physical report and timeline](docs/reports/S22PLUS_DEBIAN_USB_FIRST_P418_RUN_2026-10-09.md)
record no exact early USB endpoint within 90 seconds, before a challenge or
authenticated PID1 snapshot. Scientific USB/PID1 result remains **NO_PROOF**.
One original-A transfer and health-only continuation completed full rooted
original-boot/supporting, changed-boot and Android32 GPT/capacity checks.
Final state is **ANDROID_CLOSED_HEALTHY**, `recovered=true`, N/A counts 1/1.
The grant and candidate are closed/consumed; no F1 owner remains.

The fixed same-returned-boot Android D0 read recovered two intact HMAC-valid
records: `TARGET_GUARD_OK` and the first `sec_log_buf` `MODULE_BEGIN`. This is
**partial post-return retention proof**. Sequence 1 is damaged/interleaved
with older Android text, so the original strict decoder STOP is preserved.
Separate H0 analysis authenticated only exact contiguous captured bodies;
independent review confirmed them without reconstruction or relaxed checks.
The BEGIN record precedes both a presence check and the insertion syscall;
it proves neither insertion completion nor a stall. Missing later records
cannot locate the failure or establish non-execution.

The next bounded functional question is progress beyond that earliest recorded
point to a real USB channel, while accounting for damaged retained framing.
No follow-up candidate is selected. P418 selected no UFS/block/native_data access;
P415 remains the last native_data observation. A90/S20+ were untouched.
The [H0 qualification](docs/reports/S22PLUS_DEBIAN_USB_FIRST_P418_H0_2026-10-08.md)
and the physical outcomes retain separate meanings.

## P417 early-boot trial unproved; original Android recovered healthy

P417 `v0.5.0-rc.1` consumed its one attended experiment on 2026-10-08 KST.
The [physical report and canonical timeline](docs/reports/S22PLUS_DEBIAN_EARLY_P417_FIRST_RUN_2026-10-08.md)
record **NO_PROOF**: after one candidate transfer, the exact early USB endpoint
was not detected within 90 seconds, before any authenticated early snapshot.
Debian shell PID1, module/UFS preparation and protected metadata are not proved
on hardware. The timeout does not identify an internal stage or establish
non-execution; no authorized post-return RAM retrieval exists for this profile.

The operator entered physical Download and original A was transferred once.
The first post-A health read lost ADB; health-only continuation completed
without another transfer. Final state: **ANDROID_CLOSED_HEALTHY**, `recovered=true`,
exact original boot/supporting hashes, root, new Android boot and full Android32
GPT/capacity. N/A transfer counts are 1/1. H0 closure revalidated 564 captures,
219 frozen source paths and the unchanged 15-row journal/terminal. The grant
and candidate are consumed and closed; no F1 owner remains. A90/S20+ are untouched.

The next bounded question is establishing a real early observation channel
under Debian-owned initial userspace. Native_data was not observed by this
trial; P415's dirty-root evidence and the separate journal-recovery scope remain
unchanged. Root admission and installed Debian transition remain later units.

Requested same-boot Android D0 residual inspection subsequently found an empty
mounted pstore and the active ramoops node disabled. The 2,097,136-byte
`last_kmsg` contains long-running Android shutdown and bootloader records;
no P417 PID1/preparation proof was recovered. The actual candidate did not load
Samsung's `sec_log_buf` retention owner, and its own stage file was tmpfs-only.
The operator's visible boot-log/no-observed-loop account is retained separately.
A future native return needs a functioning retained-log producer and reader;
changing the return environment alone does not preserve tmpfs evidence.

## Retained Debian early boot and FYG8 preparation H0

The first implementation of the [architecture proposal](docs/reports/S22PLUS_DEBIAN_OWNED_EARLY_BOOT_FEASIBILITY_H0_2026-10-07.md)
passed its [ARM64 VM experiment](docs/reports/S22PLUS_DEBIAN_OWNED_EARLY_BOOT_H0_2026-10-07.md).
Debian's adapted shell `/init` starts as PID1 and its packaged `run-init` reaches
installed SysVinit, same-boot SSH, ordinary shutdown and clean ext4 without the
old native PID1 runtime. Wrong UUID and altered init are rejected before RW,
with entire negative fixture disks unchanged. Four final archives are identical;
independent H0 review passed. The retained VM kernel was neither changed nor
rebuilt, and Samsung hardware/boot/recovery remain unproved by this experiment.

The [FYG8 preparation port](docs/reports/S22PLUS_DEBIAN_FYG8_PREPARATION_H0_2026-10-07.md)
now carries the complete retained 73-module platform sequence plus eight UFS
modules in a Debian-built initramfs. All 3,926 imported symbol CRCs resolve
against the fixed Image and preceding modules. A small child verifies module
files, records each insertion attempt in bounded RAM evidence, binds exact UFS
geometry and observes GPT/superblock under partition-only RO. It always stops
before mounting or handing off to installed Debian. Eleven ARM64 VM scenarios
cover clean/dirty metadata, exact rejection boundaries, no replay and the
absent-console fallback; every copied disk is unchanged. Hardware insertion,
firmware readiness and physical storage discovery remain unproved by H0.

The operator requested continuation through a physical experiment. The
[P417 preparation](docs/reports/S22PLUS_DEBIAN_EARLY_P417_H0_2026-10-07.md) adds
authenticated early-PID1/RAM evidence and an existing V3 owner with physical
original-A recovery. Its first prospective trial stops after protected
GPT/superblock observation; full root admission and Debian's installed-root
transition remain later units. Actual boot-only A/B packages, the final three
ARM64 producer/consumer cases, 57 focused/regression tests and independent
`PASS_GO` completed before the physical trial above. Fixed connected Android
health/GPT/capacity preparation passed. These H0 results remain separate from
P417's missing hardware proof.
The physical P415 dirty native_data state still belongs to its separate
reviewed recovery owner. Later kernel modification/build/optimization remains
an operator-requested option where demonstrated need warrants it. No grant is
open, and the physical consumed results below are unchanged.

## Current P415 protected evidence capture; Android returned healthy

P415 `v0.4.0-rc.15` completed its one attended read-only experiment on
2026-10-07 KST. The [physical-run report and canonical timeline](docs/reports/S22PLUS_NATIVE_ROOT_EVIDENCE_P415_FIRST_RUN_2026-10-07.md)
record **PASS_ROOT_EVIDENCE_OBSERVED** and **ANDROID_CLOSED_HEALTHY** through
the normal same-boot CONTROL/original-A return, with no stop or extra recovery.
There was one N, one fixed reader command and one A; the grant and candidate
are consumed and closed, with no F1 owner remaining.

The mountless partition-protected view observed `state=1 recover=1 orphan=0`.
Native_data therefore requires separately authorized journal recovery before
clean-root admission. Eleven sealed legacy paths were absent from checkpointed
home blocks, and the present wtmp was empty. No new P413 progress can be proved
from those files. Newer records may remain only in the journal; absence does
not negate P413's authenticated installed-PID1/rcS-entry evidence or prove
non-execution. P415 mounted nothing, replayed nothing and made no filesystem
write. It read 275,456 bytes in 45 calls and preserved superblock/GPT readback.

Final original boot/supporting digests, root, changed Android boot and full
Android32 GPT/capacity passed. H0 closure revalidated 588 raw captures, 251
frozen source paths and the unchanged 18-row journal/terminal with device
commands blocked. A90 and S20+ were untouched. Durable per-run records and
USB-independent startup remain prospective work under their own scope.

## Prior P413 installed PID1 and rcS entry; Android recovered healthy

P413 `v0.4.0-rc.13` completed one attended attempt on 2026-10-03 KST.
The [physical-run report and timeline](docs/reports/S22PLUS_DEBIAN_HANDOFF_P413_FIRST_RUN_2026-10-03.md)
prove fresh clean-root admission and all 8,969 expected entries, one normal
native_data RW activation, the actual PID1 writable-root witness and installed
Debian init as PID1 in the same kernel boot. The installed-init hook proved
zero inherited ACM/state descriptors, accepted START and recorded rcS entry.

The host observation then ended with **EOFError**, after that entry record and
before any rcS-complete/runlevel-complete or 120-second runtime proof. No
authenticated STOP errno was received. The host sent no USB release, NCM/SSH
request or Debian shutdown. Result: **PASS_INSTALLED_DEBIAN_PID1**, with Debian
service progress, NCM and SSH still **NO_PROOF**. EOF does not establish a reboot,
panic, rcS failure or its cause.

The exact Download endpoint was bound and original A transferred once. A
pre-dispatch USB endpoint read failure and a later boot-time ADB read failure
were preserved; continuation performed only the remaining authorized recovery
and health work. Terminal: **ANDROID_CLOSED_HEALTHY**, `recovered=true`.
There was one N and one A, with no repeated handoff/control/transfer. The grant
and candidate are consumed and closed; the F1 owner is absent. All 1,759 raw
captures, 264 frozen source files and the unchanged 17-row journal/terminal
were revalidated in H0. A90 and S20+ were untouched.

Native_data was clean before P413's writable lifetime. Its post-return
cleanliness was unproved until P415 later observed RECOVER set without replay.
Android health does not preserve or renew P412's clean-root claim. The
[retained-evidence H0 assessment](docs/reports/S22PLUS_P413_EOF_FORENSICS_H0_2026-10-03.md)
completed without device commands or a new candidate. CLOCAL was already set;
the verified driver behavior and exact startup scripts do not establish a
simple ACM-close or direct rcS USB/reboot cause. The subsequent
[multi-angle causal analysis](docs/reports/S22PLUS_P413_CAUSAL_RESEARCH_H0_2026-10-03.md)
joined the EOF to an actual host USB-core disconnect and a spontaneous native
USB re-enumeration about 24.43 seconds later, before physical recovery was
requested. This explains the tty hangup/EOF path but does not distinguish a
same-boot USB restart from a kernel/SoC reboot. Ordinary carrier loss,
unsupported close_range, native-userspace watchdog petting and normal runtime
autosuspend do not supply a supported causal chain. The departure trigger
remains unproved. P413 grants no replay or filesystem repair.

The operator reports no physical unplug/replug during the cutoff. Intermittent
contact or electrical loss remains an unproved alternative, not an observed
fault; absence of plug manipulation does not alone establish reboot.

## Prior P413 prelive qualification

P413 `v0.4.0-rc.13` is the fresh archive-free handoff V2 candidate after
P412's clean-root proof. Its [prelive report](docs/reports/S22PLUS_DEBIAN_HANDOFF_P413_PRELIVE_2026-10-03.md)
records identical actual A/B boot packages, static ARM64 helpers, independent
**PASS_GO** over 264 frozen source files and 60 current focused tests.
Exact assembly/header/asset equivalence permits reuse of P411's 21 ARM64 VM
cases; their authenticated RX and TX records all rederive with the unchanged
strict consumer. No new VM execution or new Debian runtime feature was needed.

The corrected Android health consumer is included in a new capability record;
the consumed P411/P412 reviews, artifacts and journals remain unchanged.
Both guarded offline preparation and current connected fixed D0 preparation
passed. The latter revalidated rooted original Android, exact Android32 GPT,
capacity and the retained recovery binding in 19 private captures. The concrete
task hash is `cb86591156b7004700cafb49748cf77e10f1f743ddb3dc97f147dce0fb5d725a`.

That preparation opened no grant or operation and transferred no image. Its
later one-operation/3600-second physical attempt above is now consumed. Fresh
native-root admission remained mandatory and passed before RW. The retained
qualification is not physical service/NCM/SSH proof or authority to replay.

## Prior P412 clean-root proof and healthy Android closure

P412 `v0.4.0-rc.12` completed one attended operation on 2026-10-03 KST.
Its [physical-run report and timeline](docs/reports/S22PLUS_NATIVE_JOURNAL_RECOVERY_P412_FIRST_RUN_2026-10-03.md)
record **PASS_JOURNAL_RECOVERY_OBSERVED / PROVED_CLEAN_ROOT**. Native_data changed
from `clean=0 state=1 recover=1 orphan=0` to
`clean=1 state=1 recover=0 orphan=0`. The strict writer recorded only its two
successful finalization writes (5,120 bytes); no additional home-block replay
write was observed. After partition RO restoration, `e2fsck -fn` passed and
all 8,969 expected root entries matched within the existing mutable-data bounds.
Protected unmount and cleanup completed.

Authenticated native return and one original-A transfer completed normally.
The final health consumer initially selected the wrong historical GPT layout
because its operation list omitted `journal-recovery`. Both retained health
captures actually prove the unchanged Android32 GPT, original partition
hashes, rooted Android and expected capacity. An independently reviewed H0
routing correction rederived those bytes and appended only the missing final
health completion. No device command or transfer accompanied that correction.

Terminal: **ANDROID_CLOSED_HEALTHY**, `recovered=false`. One N and one A were
transferred; the one-operation/1800-second grant and candidate are consumed
and closed, with the F1 owner absent. The original failed parser log, 19-row
journal prefix, raw captures and consumed source/review pins are preserved.
A90 and S20+ were untouched. P412 executed no Debian init, service or SSH.

That clean protected-root result removed P411's observed dirty-root blocker;
P413 revalidated it before its later writable lifetime. It does not prove the
filesystem clean after P413's forced return. Fresh work still needs its own
current admission, source binding and grant. The old P412 activation stays tied
to its original source; its H0 closure review grants no new device action.

## Prior P412 H0 qualification

P412 `v0.4.0-rc.12` is the separately scoped archive-free native_data recovery
candidate. Its [H0 report](docs/reports/S22PLUS_NATIVE_JOURNAL_RECOVERY_P412_H0_2026-10-03.md)
records a byte-identical A/B boot-only package, 29 actual ARM64 tool tests,
six final kernel-VM paths, seven child-failure VMs and 92 focused unit/C/PTY
tests. The strict writer avoids ordinary e2fsck repair/orphan cleanup; the
parent restores partition RO before the fixed checker and full protected
root comparison. Independent review returned **PASS_GO** over the frozen
source/artifact closure. Concrete offline preparation passed with device
entrypoints disabled: **READY_H0_PRELIVE_ONLY**, candidate unclaimed and F1
owner absent. The new capability record preserves every consumed predecessor.

That H0 unit performed no device command, connected read, transfer, replay,
new boot or grant. P411's dirty native_data observation was its starting
evidence. The later physical operation above consumed this candidate under
the separate 1800-second scope; the original H0 evidence remains unchanged.

## Prior P411 dirty-root rejection and healthy Android closure

P411 `v0.4.0-rc.11` completed one attended attempt on 2026-10-01 KST. Fresh
fixed Android preparation passed before its one-operation/3600-second grant.
One N transfer and authenticated native health succeeded. Actual PID1 entry
and worker retirement were proved, then protected root admission observed
`clean=0 state=1 recover=1 orphan=0` on native_data.

The inspector kept partition RO, did not mount the filesystem and confirmed
unchanged superblock/GPT before cleanup. The handoff stopped with `EPROTO`
before writable activation or installed init. Result: **NO_PROOF Debian PID1**
with a proved dirty-root admission rejection. No START, 120-second service
observation, USB release, NCM, SSH or Debian shutdown occurred.

The exact Download endpoint was bound and original A transferred once. A
boot-time ADB read failed; health-only continuation then proved rooted original
Android, all original partition hashes, GPT and Android32 capacity. Terminal:
**ANDROID_CLOSED_HEALTHY**, `recovered=true`. There was one N and one A, with
no repeated control/transfer. The candidate and finite grant are consumed and
closed; the F1 owner is absent. A90 and S20+ were untouched.

The [physical-run report and timeline](docs/reports/S22PLUS_DEBIAN_HANDOFF_P411_FIRST_RUN_2026-10-01.md)
record the 1,436 operation captures, 261 frozen source files and unchanged
terminal/journal rederivation. Native USB presence after the stop does not
prove a new boot: ACM had not been retired, and no later authenticated boot
identity was acquired. The host sent no new native Download command.

The native filesystem required journal recovery when P411 observed it.
P411's Android health did not repair it or prove its later cleanliness, and
its grant authorized no repair, journal replay or reinstall. The separately
scoped P412 operation above later proved clean protected-root admission;
P411 itself remains consumed and cannot be replayed.

## Prior P411 H0 qualification

The [V2 policy](docs/operations/S22PLUS_DEBIAN_HANDOFF_V2.md) selects sequential
Debian-owned startup/120-second observation and retention of the first `g1`
for NCM. The [H0 report](docs/reports/S22PLUS_DEBIAN_HANDOFF_P411_H0_2026-10-01.md)
retains 21 ARM64 VM cases, 159 tests, identical actual boot/AP A/B bytes and
independent source-bound PASS_GO over 261 files. Its concrete task hash is
`4dba33825c8cea17463266ac2e1e8b3591a45641ed68a2fb1caa5dc93f696aa9`.
The later physical attempt above consumed that candidate and grant. Samsung
NCM/SSH and the 120-second service interval remain unproved because admission
stopped earlier; the H0 proof is not relabelled as a physical pass.

## Prior P410 installed PID1 reached; basic access failed and Android recovered

P410 `v0.4.0-rc.10` completed one attended operation on 2026-09-30 KST.
The physical authenticated transcript proves installed Debian init as host
PID1 under the writable native_data root: `PASS_INSTALLED_DEBIAN_PID1`.
This is the reached init boundary, not a successful Debian service boot.
No NCM endpoint appeared in the 180-second window and no SSH or shutdown
command was sent. About 51 seconds into that window the same P410 native ACM
identity reappeared. The reported advancing native screen is consistent with
later native startup; no later authenticated boot ID or reset-cause evidence
proves an actual reboot mechanism.

Research stopped. Attended physical Download and one original-A transfer
returned the device to `ANDROID_CLOSED_HEALTHY`, `recovered=true`. A USB read
failed before the A intent; later final-health ADB failure required only
health continuation. There was one N and one A transfer, with no repeated
handoff/control. Full rooted Android, original partition hashes, GPT and
Android32 capacity passed. Native_data cleanliness remains unknown after the
writable lifetime. The one-operation/3600-second grant and candidate are
consumed and closed; the F1 owner is absent. A90 and S20+ were untouched.

The [physical-run report](docs/reports/S22PLUS_DEBIAN_HANDOFF_P410_FIRST_RUN_2026-09-30.md)
records 1,779 raw captures, 257 frozen source files, unchanged terminal/journal,
the native USB reappearance and the limits of the PID1 proof.

Post-run H0 diagnosis confirmed a blocking USB ownership defect in the exact
P410 Image: Android configfs setup keeps the first gadget's global pointer.
The hook unbinds native `g1`, but Debian creates a second `s22-debian` object;
the old object's `unbind=1` blocks setup before NCM descriptor handling.
Independent exact-Image review and 16 source control-flow cases on host/ARM64
confirmed the mechanism. The physical run's post-hook reach and reset cause
remain unproved. Retiring native workers does not remove the kernel watchdog
petter, so that simple reset explanation is unsupported.

P411 implements the selected same-first-g1 correction under its own V2
scope. The P410 evidence and prior review remain unchanged; the root is not
assumed clean and no earlier consumed effect becomes replayable.

## Prior P409 proved readonly PID1 transition and healthy Android closure

P409 `v0.4.0-rc.9` completed one attended operation on 2026-09-30 KST.
The actual native PID1 replaced itself, settled its native workers, verified
the protected installed root and used the selected BusyBox to switch_root into
a distinct static RAM witness. Authenticated post-exec evidence proved PID1,
readonly ext4 root and partition RO, the witness executable, seven moved mounts,
only fd0–3, no other userspace and the same boot/ACM connection. Result:
`PASS_SWITCH_ROOT_WITNESS / PROVED_READONLY_HOST_PID1_ROOT_TRANSITION`.

The exact 8,969-entry root comparison passed. The witness's fixed Download
return and one original-A transfer completed. A final-health ADB boot read
failed; health-only continuation then proved rooted original Android, exact
partition hashes, full GPT and Android32 capacity. There was one N and one A
transfer, with no repeated effect. Terminal: `ANDROID_CLOSED_HEALTHY`,
`recovered=true`. Final health completed at 95.495 seconds and explicit grant
closure at 227.705 seconds; 553 raw captures and 247 saved source files were
verified. The candidate/grant are consumed and the F1 owner is absent.

The [first-run report and timeline](docs/reports/S22PLUS_SWITCH_ROOT_P409_FIRST_RUN_2026-09-30.md)
record Samsung proof of the shared retirement/root-transition/observation
mechanism. This run does not execute installed Debian init, start services,
establish NCM/SSH or test writable persistence. The closed P409 grant authorizes no successor effect. P410 subsequently
proved installed init, and P411 addresses its service/USB gap; A90 and S20+
remain isolated.

## Selected final architecture

```text
Samsung bootloader -> FYG8 kernel -> minimal device initramfs
                  -> root transition and exec -> Debian host PID 1
```

The early bootstrap identifies the exact root partition, prepares the storage
and essential device interfaces, mounts the Debian root, and transfers the
required mounts and console/log state. It then execs Debian init in the initial
PID namespace. The bootstrap does not fork Debian beneath a surviving native
PID 1, retain an independent native control plane, or leave an old-root process
tree running beside Debian. Select the root-transition mechanism against the
actual kernel and initramfs topology; a generic `pivot_root` assumption is not
an implementation plan.

| Responsibility | Before handoff | After handoff |
| --- | --- | --- |
| Root storage and essential hardware | Minimal bootstrap loads the necessary exact modules/firmware, creates required nodes and mounts the root | Debian owns filesystem policy, device events and subsequent initialization |
| Process and service lifecycle | Bootstrap manages only its temporary preparation processes | Debian init owns host PID 1, process reaping, service start/stop/restart and shutdown |
| USB, networking and display | Prepare only what root access or required boot observation needs | Debian services own configuration and device access; no competing native manager |
| Device-specific long-lived helpers | Identify their real lifetime and dependencies before choosing the handoff | Package and start them under Debian's service manager, with Debian-visible logs and explicit start/stop behavior |
| General Linux runtime | Use standard tools where suitable; do not recreate distribution services | Debian provides libraries, accounts/authentication, DNS, time, logging and package management |

Classify each reused native component as boot-only, a Debian-managed service,
or unnecessary for this product. A helper that cannot yet operate under Debian
is an explicit compatibility gap, not justification for hiding a second
supervisor or Android runtime behind the handoff. Existing kernel modules and
firmware may remain active: root transition does not reset the kernel or
hardware, and it does not by itself prove their later compatibility.

Build the initramfs and rootfs as a matched pair with declared versions,
paths, module/firmware dependencies, writable directories, device-manager
behavior, init/service configuration and SSH access. Prefer moving reusable
boot preparation into Debian's initramfs build hooks as compatibility permits.
No requirement to eliminate initramfs or replace the FYG8 kernel is introduced.
The steady-state rootfs should support normal Debian package and configuration
management on the dedicated partition; its initial mount mode and exact
persistent-write scope remain implementation and reviewed-capability work.

## Kernel and rootfs compatibility

Recheck the selected kernel artifact and target ABI before choosing the Debian
release, init and device manager. The retained
[FYG8 capability analysis](docs/reports/S22PLUS_FYG8_NATIVE_USERSPACE_BRINGUP_GAP_ANALYSIS_2026-07-22.md)
records disabled devtmpfs, PID/user namespaces, the cgroup PID controller and
SysV IPC. These are compatibility inputs to verify against the chosen artifact,
not a claim that a new Debian build has passed. Host PID 1 does not require a
new PID namespace.

Debian ownership does not imply a preselected systemd implementation. Assess
a small Debian init such as SysVinit against the existing kernel, and assess
systemd against its exact version's kernel/device requirements. Keep missing
kernel features explicit; do not emulate a general Linux environment inside
native init to conceal them. Any kernel change is a separate qualified unit.
Use [Debian's arm64 bootstrap documentation](https://www.debian.org/releases/stable/arm64/apds03.en.html)
for rootfs construction and
[initramfs-tools](https://manpages.debian.org/trixie/initramfs-tools-core/initramfs-tools.7.en.html)
for the standard early-boot lifecycle. Their generic kernel/bootloader setup
does not replace this target's existing boot and recovery process.

The [A90 comparison](docs/plans/A90_H16_H24_ISOLATED_DEBIAN_COMPARISON_BASELINE_2026-08-14.md)
and [firstboot audit](docs/reports/A90_H14_IMMUTABLE_FIRSTBOOT_ISOLATED_DEBIAN_MISMATCH_H0_2026-08-14.md)
are lessons: align mount/device assumptions, authentication, service ownership
and return behavior before integration. Do not import A90's selected native
supervisor architecture, consumed results or device authority. HUD, display,
boot chime and legacy SD evidence dependencies do not gate the first headless
Debian boot.

## Completion criteria for the first usable Debian system

These are prospective product criteria, not newly activated device gates:

1. **Actual Debian boot:** same-boot evidence identifies Debian init as host
   PID 1, the dedicated partition as its root, and the expected rootfs build.
   A child shell, a chroot, a namespace-local PID 1, an exec-intent marker or an
   open port alone does not establish this outcome.
2. **One userspace owner:** no independent native supervisor, competing device
   manager or surviving native old-root service tree remains. Required
   target-specific helpers have a declared Debian service owner and observable
   lifecycle. Mounts and inherited descriptors match the handoff design.
3. **Useful Debian runtime:** the selected standard command workload runs,
   package installation/configuration works, and one ordinary service can be
   started, stopped and restarted through Debian's init system. Record the
   tested packages and limitations; do not claim all Linux software works.
4. **Headless access:** a declared Debian-owned IP path supports authenticated
   SSH, DNS and the selected service workload. USB networking may qualify the
   first access path; Wi-Fi is a later capability if its dependencies are not
   ready. Port visibility alone is not authentication or service proof.
5. **Persistent operation:** a clean shutdown/reboot boots Debian again and
   preserves the selected package, configuration and synchronized test data.
   A normal boot does not depend on an interactive native shell or host daemon.
6. **Diagnosable failure and recovery:** boot-stage records connect to Debian
   logs, distinguish the last completed preparation stage from actual init
   execution, and identify the service that owns a failure. Demonstrate the
   separately authorized return/recovery path and final rooted Android health;
   report Debian functionality, recovery and terminal health independently.

Demonstrate the combined PID 1, root, ownership, SSH and workload claims in one
identified integrated run, followed by its qualified persistence/return checks.
Do not assemble a full-system PASS from unrelated experiments. Before Debian
exec, a preparation failure may stop in the bootstrap under its defined
procedure. After successful exec, the replaced native PID 1 is not available
as an automatic fallback. Post-handoff recovery must have its own demonstrated
reboot/physical-return route; no reverse root switch or automatic recovery is
assumed.

## Next bounded unit and milestones

The [stock-first-watchdog analysis](docs/reports/S22PLUS_FYG8_STOCK_FIRST_WATCHDOG_H0_2026-10-20.md)
supports an H0 candidate comparison with cpuidle.off=1 as the single changed
idle variable, retaining bounded observation of installed-init work. P430 is
the same-kernel/module/command-line surviving contrast; actual idle and ping
state remain unknown. This selects preparation only, not a new admission gate
or device authority. Watchdog and RT budget changes are not established fixes.

Keep Debian shell as initial owner and use fixed temporary preparation helpers.
Reuse root-transition, installed-init and same-first-gadget work, with the
[P414 observer](docs/reports/S22PLUS_DEBIAN_HANDOFF_P414_OBSERVER_H0_2026-10-03.md)
and current watchdog observations where useful. The product remains services
and same-boot SSH; diagnostics do not become a second general runtime.

P438's latest protected read is dirty with the runtime file absent in its home
view. Assess the existing fixed journal-recovery/history path before a future
writable boot, and require that boot's actual protected root admission. Older
clean-root observations do not establish current integrity. Android health,
native_data cleanliness and watchdog functionality remain separate claims.

1. **Integrated headless access:** qualify one complete Debian-owned boot path
   through platform preparation, protected root admission, installed PID1,
   rcS/runlevel 2, 120 seconds of sampled init/cron/sshd liveness, Debian NCM
   and same-boot pinned SSH. Include useful bounded observations in that path
   without turning each record into a separate whole-device milestone. Close
   through the selected fixed shutdown and original-A return/health procedure.
2. **Persistence and ordinary service:** after healthy closure, qualify
   package-managed service behavior, retained data/configuration and ordinary
   Debian reboot under the applicable separate scope.
3. **Later hardware:** Wi-Fi, display/input, audio and desktop follow the
   usable headless Debian base.

A future physical unit still requires a freshly qualified complete artifact,
current source-bound review, exact original-A health and applicable finite
authority, with its original recovery owner. No historical grant is reused.

ARM64 VM proof does not establish Samsung electrical USB behavior or target
service liveness. Installed-init proof, runtime progress, SSH, clean ext4 and
Android closure remain separate. Forced return can leave native_data dirty
while Android remains healthy; repair requires a separately selected scope.

## Completed history

The complete 754-line goal through P410's healthy closure and exact-Image USB
diagnosis is preserved byte-for-byte in
[the P410 closed snapshot](docs/archive/roadmaps/GOAL_THROUGH_P410_CLOSED_2026-10-01.md).
It retains the P401 installation, P403 fixed userspace, P406 root inspection,
P408 protected preparation, earlier storage/cleanup results and archive links.
Consumed claims, private journals and historical source pins keep their
original meaning and cannot be replayed.

## Continuing boundaries

Future device work requires its own current scope and exact target, artifact,
health, source and recovery binding. Never place an experiment over uncertain
health or repeat an uncertain write, transfer or control. Keep raw evidence and
identifiers private. A reporting failure permits evidence reconstruction, not
another device transition. Functional proof, recovery and terminal health remain
separate. The Debian direction selects preparation work only; filesystem
formatting, rootfs staging and runtime effects require their own reviewed
scope under the binding contracts.
