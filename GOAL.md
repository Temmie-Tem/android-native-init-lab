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

## P421 closed healthy; same-run file evidence awaits P422

P421 `v0.5.0-rc.5` consumed its returned attended file-pilot grant on
2026-10-13 KST. One candidate transfer and the original 360-second host window
completed. The operator then entered physical Download; one original-A
transfer and a health-only continuation after one failed ADB read proved
**ANDROID_CLOSED_HEALTHY**, `recovered=true`, N/A counts 1/1. The grant and
candidate are closed/consumed, with no F1 owner remaining.

The [physical report](docs/reports/S22PLUS_DEBIAN_FILE_P421_RUN_2026-10-13.md)
keeps the scientific result **AWAITING_OFFLINE_FILE_RECORD**. This profile
made no live USB acquisition: the time window does not prove module progress,
Debian PID1, file creation, unmount or current native_data consistency. P420's
clean-root proof predates this potentially writing boot. P421 must never be
repeated because a file is absent or unavailable.

H0 closure rederived 820 raw captures and 244 frozen source paths without
device commands or journal changes. The next bounded unit is the already
qualified P422 mountless reader, sealed to P421's exact run, followed by its
own original-A closure and H0 raw-file authentication. P422 is unconsumed and
requires its own returned attended grant and fresh binding. A90 and S20+
remain untouched.

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
above. P422 retains its concrete offline preparation and still needs its own
returned attended grant and fresh runtime binding. A90 and S20+ remain untouched.

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

P415's protected read-before-write census is complete and closed healthy.
The [run report](docs/reports/S22PLUS_NATIVE_ROOT_EVIDENCE_P415_FIRST_RUN_2026-10-07.md)
preserves the observed dirty native_data and limited home-block evidence.
The next functional improvement remains bounded durable per-run evidence and
separation of USB reporting from startup progression. Any next writable boot
must first address the observed RECOVER state through a separately selected
reviewed recovery scope and fresh protected admission. P415's consumed grant
supplies neither that recovery nor a successor boot.

The [P414 observer H0 unit](docs/reports/S22PLUS_DEBIAN_HANDOFF_P414_OBSERVER_H0_2026-10-03.md)
implements a close-return/reopen barrier and parent-only ACM observation during
ordinary rcS/rc2. Fresh revision-3 helpers preserve child descriptor isolation,
original deadlines and one-shot execution; partial boundaries never authorize
release or reconnect. Host and ARM64 qualification are recorded in that report.
This is prospective instrumentation, not a demonstrated repair or causal proof
for P413's USB departure. Existing D0/AUTH cannot provide a preparation-free
post-loss boot-ID observation; a separate future design remains unimplemented.

At the operator's 2026-10-07 request, future experiment design should consider
**bounded device-local persistent evidence alongside live USB observation**,
including recovery of those records after transport loss or reboot. The next
S22+ H0 design should assess per-run/boot identity, verified stage records,
checked durable writes, storage bounds and later retrieval. Review the coupling
between USB reporting and startup progress. Missing records must not imply
non-execution, and local service liveness must not imply external SSH success.
This is a prospective design preference; persistent receipts are not yet
implemented or activated and P414's existing qualification remains separate.

The next device-related unit requires a **freshly qualified complete artifact,
exact original-A health and applicable finite authority**. Current native_data
admission must pass at the protected boundary before any writable handoff.
P414 H0 opens no grant and has not
built or activated a full boot image. P415 has since observed native_data
RECOVER set; neither journal replay nor repair is inferred from its reader grant.
P410/P413 installed-init proof and P411's same-gadget H0 qualification retain their separate limits.

1. **Headless access:** with a fresh candidate and exact health/root admission, prove rcS and
   runlevel 2, 120 seconds of sampled init/cron/sshd liveness, Debian NCM and
   same-boot pinned SSH. One fixed shutdown and physical original-A return
   close this prospective unit.
2. **Persistence and ordinary service:** after that unit closes healthy,
   qualify package-managed service behavior, retained data/configuration and
   ordinary Debian reboot under a separately selected scope.
3. **Later hardware/product features:** Wi-Fi, display/input, audio and desktop
   are Debian-managed capabilities after the headless base works.

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
