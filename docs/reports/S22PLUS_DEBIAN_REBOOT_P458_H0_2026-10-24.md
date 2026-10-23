# P458: ordinary Debian reboot feasibility and checklist audit

## Result and scope

**PASS_H0_REBOOT_FEASIBILITY**: the isolated ARM64 component completed two real
Debian boots, one ordinary SysV reboot and one final power-off. Both boots
supplied authenticated PID1/service evidence and pinned SSH for over 120
seconds. First-boot final files survived into the second boot byte for byte.
Five mount-frontier cases, fifteen interruption/reader cases, three first-boot
failure cases and eleven focused host tests pass. Independent review rederived
the raw producers, decoders, saved results and actual initramfs contents.

The [design](S22PLUS_DEBIAN_REBOOT_P458_DESIGN_H0_2026-10-24.md) was committed as
`1f44a382d7` before implementation. Its bounded H0 completion criterion is met.
This is not a physical candidate, complete-root admission, Samsung reboot/USB
proof, policy activation or a new device grant. No device, A90, S20+ or server
action occurred; all 46 pre-existing changed files retain their original bytes.
[P456](S22PLUS_DEBIAN_MINIMAL_P456_RUN_2026-10-24.md) and
[P457](S22PLUS_AUTOBOOT_PERSISTENCE_P457_RUN_2026-10-24.md) remain consumed and
closed healthy. No live F1 owner was created.

## Executed component

The new H0-only directory is
`workspace/public/src/debian/s22plus_reboot_h0/`. Nothing imports it into the
production automatic runtime or device-action entry points. Its C guard checks
the QEMU `linux,dummy-virt` model. Every disk is a checked private regular-file
fixture; SSH uses an isolated loopback QEMU forwarding port and the sealed key.

The normal run uses the retained generic Linux 5.10.226 ARM64 kernel, the sealed
Debian archive, actual packaged SysVinit, the P456 minimal rcS dispatcher and
packaged rc2/rc6. The original rc6 ends in `umountroot` then `reboot`. The VM
substitutes virtio storage/networking for FYG8 preparation, uses RAM-bound
configuration and an empty RAM crontab, and adds fixed component records. It
pauses the second boot before RW only to copy a clean private fixture. That
pause is not a proposed physical host-release gate. Actual FYG8 modules, UFS,
the production complete-root checker and first-gadget NCM are not exercised.

| Normal producer evidence | Observed result |
| --- | --- |
| Initial ownership | Two actual initial `/bin/sh` PID1 starts in one QEMU process |
| Installed ownership | Packaged SysVinit PID1; executable identities checked for init, cron and sshd |
| Service observations | 16 samples per boot; BOOTTIME spans 124,786 and 124,275 ms |
| Control | One ordinary reboot dispatch, then one final shutdown dispatch |
| Identity | Different authenticated boot identities, same pinned SSH host key |
| Persistence | Exact final first-boot early/runtime bytes in the second boot and saved binary snapshots |
| Phase tails | First runtime ends with reboot intent; second runtime ends with shutdown intent |
| Filesystem views | Clean state 1 / RECOVER 0 / orphan 0 at mount counts 0, 2 and 4 |
| Raw/terminal result | 65 captures reopened; saved 97,959-byte result independently rederived |

The component's signed completion records require at least 120,000 ms from
prepared runtime. The host also checks the actual sample span, executable/PID
identity, file chains, common initial mount count and per-boot clock joins.
Intent is not proof that a command was accepted or the cause of a later reset.
The two boot identities do not prove that no unobserved kernel start occurred.

## Consumption boundary and interruption evidence

Both retained generic and FYG8 ext4 sources increment the 16-bit mount counter,
set RECOVER and call `ext4_commit_super(sb, 1)` during successful RW setup.
The synchronous superblock write requests FUA when BARRIER is enabled. RW
mounts in this component explicitly select `barrier=1`; inherited filesystem
defaults are not the safety argument. RO-to-RW remount also uses this setup.
This source comparison and VM behavior are not hardware power-loss proof.

Let M be the initial count authenticated in the first early record. Each boot
uses two writable lifetimes: early evidence, then installed root. Before the
second boot's first RW mount, require clean state, the exact authenticated first
pair including completion and intent, absent second-phase files and count M+2.
M must be at most 65,531 so four increments cannot wrap. No raw superblock writer
or counter reset is part of the runtime.

| Executed case | Outcome on the next read-only observation |
| --- | --- |
| Second boot stopped before RW mount | Still admissible; disk content, extents and mtime unchanged |
| Stopped after RW mount, before file | Dirty state rejected before another write |
| Stopped after early file creation | Dirty state rejected before another write |
| Successful RW mount then clean error-unmount, without a file | Clean count M+3 rejected; file absence does not reopen admission |
| Bad MAC, partial runtime, missing intent, foreign run, cross-boot records | Actual ARM64 reader rejects the relevant authentication/shape/join |
| Overflow or wrong authenticated baseline | Actual ARM64 reader rejects before RW |
| Existing empty second early file | Metadata rejection; empty does not mean absent |
| Third boot after normal completion | Second phase already consumed; no new write |
| Extra RO-to-RW remount | Unexpected increment rejected |
| Initial count overflow | Rejected before RW |
| Reboot intent recorded, command not issued | One timed-out host dispatch; dirty root rejected, no accepted/restart claim |
| rc6 stopped before root remount | Accepted request, no restart; dirty root rejected |
| Root remount deliberately omitted before reboot | Restart occurs, next boot rejects dirty root |

The first four plus eight record mutations and the final third-boot/remount/
initial-overflow cases form the 15-case corpus. The three first-boot failure
cases use fresh roots and actual 120-second service runs. A separate five-case
mount probe establishes the mount-before-file boundary independently.

The bound is on the second boot's admitted writable work after valid first-boot
evidence. It is not a bound on physical kernel starts, every failed mount
attempt, or first-boot pre-record uncertainty. In this H0 component, when both
first-phase files are absent, the initial count is selected from the current
clean filesystem. That does not independently prevent all earlier first-phase
attempts. P457's fixed reader retained clean-state fields, not a mount-count
baseline. A physical design must preserve this limit or separately establish
the baseline needed for any stronger claim. No absent file authorizes replay.

## Actual mutable paths and shutdown semantics

Read-only offline content/path inventories contain 8,990, 8,993 and 8,996 entries
before boot, after boot one and after boot two. They identify eight and nine
changed paths respectively: the two phase files, boot-count, random-seed,
dmesg, dmesg.0, messages and wtmp; the second boot also creates dmesg.1.gz.
All 17 changed-path inode observations were independently reparsed. The two
rotated dmesg files are regular, single-link, root:adm, mode 0640 in this VM.

The current production mutable declaration includes dmesg but omits dmesg.0
and dmesg.1.gz. A successor must declare the exact finite rotation outputs and
check their metadata/size through the existing full-root consumer. These VM
paths are not evidence that particular files exist on the physical root.
The offline dump's known post-copy ownership warnings are retained; copied
ownership is not used as proof. Changed-path inode metadata comes from separate
read-only `debugfs stat` captures. This inventory is not complete root admission.

The packaged `umountroot` script ends in `:`, so its exit 0 can mask a failed
root remount. Neither that status nor a reboot message proves a clean root.
The next protected admission supplies the clean-state decision. The omitted-
remount VM case verifies this distinction without changing packaged scripts.

## Past-failure checklist reconciliation

The [existing eleven IDs](../operations/S22PLUS_FYG8_PAST_FAILURE_CHECKLIST.md)
were checked before the VM work and again against actual saved results. No new
approval stage or checklist ID is introduced.

| ID | Status and evidence for this bounded H0 unit |
| --- | --- |
| ABI | Checked: target/generic ext4 source and relevant UAPI, ARM64 static cross-compilation, real mounts, remounts, BLKRO control and BOOTTIME. Target storage behavior remains unproved. |
| IO | Checked for this component: retained bounded raw capture, real SSH output, serial bounds, partial-record rejection and timeout cleanup. No new transport or producer/filter ABI. |
| SEMANTIC | Checked: real packaged init/services, accepted versus intent-only control, masked remount failure, clean-state/counter checks and explicit physical limits. |
| WIRE | Checked: actual C records through Python decoder; MAC, phase, baseline, boot, PID, clock, whole-file and exact tail joins; malformed/missing/duplicate cases fail. |
| PERSIST | Checked after correction: file and parent-directory sync for host intents, raw-before-parse, actual result reopen, 97,959-byte positive result, exact historical receipt resolution and sparse-disk pins. |
| ROUTE | Checked after correction: actual SSH factory and original receipt consumer exercised; negative corpus uses the sealed ARM64 guard. No production route is claimed. |
| ARTIFACT | Checked: actual 23-member initramfs unpacked; guard, seven assets, shell/libs and six frozen source inputs match their retained build receipts. |
| HOST | Checked: private regular-file disks, loopback-only forwarding, exclusive intents and cleanup. The test-only snapshot pause is explicitly excluded from physical design. |
| AUDIT | Checked: raw evidence, failed attempts and frozen source versions preserved; independent rederivation of normal, failure, inventory and negative results. |
| RETURN | H0 checked: one dispatch per control, no retransmission after timeout or publication failure, dirty next-boot rejection and final VM power-off. Samsung Download/original-A recovery remains untested here. |
| DISPLAY | Not applicable: no display code or physical display claim. |

H0 review found and corrected mixed-baseline/clock/PID joins in the summary
decoder, Path objects passed to the real raw SSH factory, and relative paths in
published receipts. Eleven focused tests include original-consumer roundtrip,
directory-fsync failure before dispatch, no retry after uncertain control and
preservation of a primary failure when optional diagnostics also fail.
The debugfs mutation consumer now accepts only its exact version banner on
stderr after verifying producer status, timeout and output bounds; an error
line remains a failure even with exit 0.

Original evidence is not rewritten. The positive run's historical relative
build receipt is resolved only under the exact known repository root in a
separate audit, with its original size/hash checked. The final source change
after VM completion only normalizes future published paths to absolute paths;
guest and decoder bytes are unchanged. All six original build source snapshots
remain available. Earlier compile, prelaunch and harness failures retain their
own source/raw evidence and do not inherit a later PASS.

## Smallest physical successor decision

Proceed with the retained minimal Debian architecture, rather than a package
installation, cron workload, longer soak or a replacement supervisor. The
physical implementation is a separate bounded unit with these concrete changes:

1. Extend the existing protected full-root admission with exact P456 history,
   finite dmesg rotation rules, two declared phases and the checked ext4 counter
   relationship. Preserve clean checks, immutable-root closure and no repair.
   Resolve the first-phase baseline claim in that actual design; this prototype
   does not supply a stronger first-boot bound.
2. Extend the existing authenticated evidence/control grammar for completion,
   reboot intent and final whole-file snapshots. Reuse its real source closure,
   collector and parser; do not import this separate H0 protocol as qualified
   production machinery.
3. Extend the actual owner from one installed lifetime to two: one durable
   reboot intent/dispatch, a second observation window starting from that fixed
   host event, new boot identity with the same SSH key, one final shutdown and
   attended original-A recovery. Per-boot BOOTTIME and the finite host grant
   remain separate; no uncertain command is retransmitted.
4. Review the resulting runtime, owner and explicit boundary specialization,
   then qualify actual artifacts and failure consumers. The current automatic
   policy permits one installed lifetime; its consumed grants cannot be reused
   for this reboot successor. No physical READY or approval is claimed here.

The H0 feasibility question is answered. Target reset behavior, USB return,
current physical full-root eligibility and physical recovery remain the actual
successor's evidence obligations, not reasons to repeat the completed VM work.

## Private provenance

All private evidence is under
`workspace/private/outputs/s22plus-debian-reboot-p458-h0-20261024-1/`:
`mount-probe-1`, `build-6`, `normal-3`, `cuts-2`, `failures-1`, `inventory-2`
and `closure-audit-1`. The closure audit reopens 65 normal, 27 mutation,
99 first-boot-failure and 20 inventory captures, preserves the exact historical
receipt mapping, verifies all 46 pre-existing file hashes and records Python
compilation. C compilation and `file` confirm static ARM aarch64 executables.
This report contains no raw device data or private identifiers.
