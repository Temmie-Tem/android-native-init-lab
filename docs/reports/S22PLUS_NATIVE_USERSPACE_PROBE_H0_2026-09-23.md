# S22+ P403 stage 3: fixed installed-Debian execution preparation

Date: 2026-09-23. Exact target: `SM-S906N/g0q/S906NKSS7FYG8`.

The operator selected preparation of the next bounded userspace test after
[P402's protected root match](S22PLUS_NATIVE_ROOT_INSPECTION_P402_FIRST_RUN_2026-09-23.md).
P403 `v0.4.0-rc.3` reuses that installed root and the working native UFS/ACM
runtime. It adds one fixed unprivileged diagnostic chroot, without installing
another rootfs, starting Debian init, changing PID 1, or exercising networking.

Preparation is complete: actual A/B boot packages, the physical/virtual helper
join, 17 real ARM64 VM cases, 125 focused host checks, independent `PASS_GO`
and all 17 fixed connected Android reads passed. No grant has opened, new
experiment image has transferred, or Debian command has run on the Samsung
device during this preparation.

## Concrete bounded operation

One attended operation lasts at most 1800 original BOOTTIME seconds:
healthy Android A → one fresh P403 N → protected-root probe/DETACH → same-boot
native health/CONTROL → one original-A transfer → full rooted Android32 health.
The image earns no reusable native admission. The operation includes no E,
reinstall, filesystem repair, service startup, ordinary Debian reboot or PID 1
handoff. The [separate policy](../operations/S22PLUS_NATIVE_USERSPACE_PROBE_V1.md)
defines current source review, fresh bindings and the future returned finite
grant; neither this report nor the candidate artifacts grant a device effect.

The existing inspector protects only the exact native partition with kernel
RAM block RO before any mount, retains the clean-superblock prerequisite and
performs its complete marker/witness/table comparison. Execution requires all
8,969 expected entries and only the three fixed records plus empty `lost+found`
outside the archive. An added loader input, missing file or incomplete install
therefore cannot enter the child workload.

The parent retains its private readonly/noexec mount. One child creates its own
mount namespace, uses a readonly **bind remount** to clear only that mount's
NOEXEC flag, and reopens the selected mount before chroot. It closes inherited
extra descriptors, replaces stdin with an empty pipe, drops all UIDs/GIDs to
65534, removes supplementary groups, verifies zero capabilities and enables
`no_new_privs`. No `/proc`, `/sys`, `/dev` or writable temporary filesystem is
mounted inside the chroot.

The single declared shell workload checks numeric identity, executes external
`printf`, runs a synchronous nested shell and observes a nested exit code 23.
It exercises the installed dynamic loader and libraries needed by those
programs. This is not a claim that all Debian programs or services work.
Exact stdout, empty stderr, complete setup/exec evidence, actual wait status,
complete reaping and parent mount/partition protection must all agree.
Ordinary unmount and unchanged complete superblock/GPT checks follow.

The child stays in the original ACM command process group. A 30-second child
bound, finite resource limits, 4096-byte stdout/stderr limits and the existing
240-second outer command bound prevent unbounded observation. A timeout,
overflow, unknown exec state or unsettled process stops research. Original-A
recovery follows the existing owner; an uncertain command or transfer never
replays. Fully observed synchronous negative workloads remain separate from
missing proof and from final Android health.

## Actual artifacts and source join

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| Boot-only AP | 32,071,721 | `f67f53ff13528aaaca4cdd03e64a10a9098daf58fd4641512434b54129c9ba2d` |
| Boot image | 100,663,296 | `4361227ed8bb7f5775562e9930fcd69a582aba41b30af21d49179486766c1a8b` |
| Static ARM64 probe helper | 921,296 | `c79e68c0373aa93bf3e225d95b259523d335528bca4f33275596d66ca9557b77` |
| Existing root comparison table | 875,961 | `76ff68e40489d846993842490adfab40fda74200f24d879cd0bc9c2aba85eac6` |

A/B packages and helper builds are byte-identical. The Image transformation
changes only the two declared identity spans and reverses exactly to its
retained input. The actual artifact validator accepts the AP/member, module
composition, helper/table and fixed workload joins. The qualification also
rederives P402's protected-root result, original-A transfer and final health
from retained raw evidence without reopening its owner or changing old reviews.

The physical helper and selected virtual helper use the same C sources, table,
target/filesystem seal, workload and run identity; virtual block discovery is
the explicit substitution. The source closure contains 162 runtime files.
The workload SHA-256 is
`5c3b5dbbd41feb090e037a80ab243db70dc815612a1b9ecd707cda5d40c9fcca`;
expected child stdout SHA-256 is
`1b968a668eb78a2484c93e3b520e178f2058f192ee51694101defc247f5e6577`.

## Behavioral qualification

All VM disks were writable private regular files. Every case left their full
allocated extents, positions, size and mtime unchanged. The native partition
alone became block-readonly; whole-disk and userdata flags stayed clear.

| Cases | Observed result |
| --- | --- |
| Exact complete root | Actual protected mount, unprivileged Debian workload, exact output/exit proof, reaping and ordinary unmount |
| Empty root, partial install, changed expected file, added loader file | No child execution; completed negative root finding |
| RECOVER or orphan state | Mount and execution skipped |
| Wrong filesystem UUID or changed GPT | Rejected before mount/child |
| Directory checksum error | Actual protected ext4 read failed; no child execution or disk change |
| Wrong output, nonzero exit, synchronous setup failure | Completed negative workload; no userspace PASS |
| Early zero exit without setup proof | Rejected as unknown exec state |
| Timeout, output overflow, live orphan | Rejected; inherited process group settled by the explicit VM fixture owner |

These are 17 cases: ten root/execution cases and seven compiled virtual-only
fault cases. The fault binary cannot compile without the virtual-board define
and is never packaged for Samsung. Its small fixture group owner is explicit;
it does not claim to be the production ACM supervisor. Separate actual C/PTY
tests exercise the production wire/owner behavior, durable pre-EXEC intent,
output accounting, DETACH, raw rederivation and required cleanup semantics.
The unchanged outer cancellation behavior and the actual ARM64 child's group
membership are distinct evidence inputs.

The first development VM attempts correctly reported a completed negative
when dash's background-child path tried to open absent `/dev/null`. A same-fd
stdin redirection did not remove that dependency. The final fixed workload
uses synchronous children and preserves the no-device-mount scope. Those raw
attempts and their helper bytes remain private and unselected. An independent
intermediate review also identified that empty exec-setup evidence must be
NO_PROOF; both producer and decoder now enforce this, and the real early-zero
case verifies it. No failed device action was involved in either repair.

All 125 focused owner, adapter, task, parser, actual C/PTY, storage-health,
output-drain and prior Debian-owner checks pass. Relevant Python compiles and
the C output is a static ARM64 ELF. These results establish H0 qualification,
not Samsung userspace execution, target PID 1 handoff or SSH.

## Review and readiness

The final review request binds 71 owner/capability files, 162 runtime files,
the actual image, VM results and retained FYG8 kernel inputs. Its SHA-256 is
`c33a9a505b02c44f97d0d04526c209381efa360207f7f0d81525d9bb6f97a016`.
The independent reviewer verified those pins, actual A/B artifact joins,
all 17 raw VM results, eight current and nine retained target-kernel sources,
the P402 raw closure and 16 focused userspace tests. Final verdict is
`PASS_GO` with no blocking findings. The private immutable review is 62,263
bytes, SHA-256
`6fc00f11422bfafa5702d81e7b34ba57da6d878eb79af7a0c3e567559ef7f91e`.
The separate public capability receipt validates the current 71/162 source
closure; no old review, consumed artifact or grant was repinned.

`prepared-1` then passed all 17 fixed D0 captures on the first invocation:
rooted original-A health before and after shell-v2, complete GPT and Android32
statfs. Both brackets identify the same current healthy Android boot, original
partition hashes and unchanged GPT; statfs total is 34,357,624,832 bytes.
The preparation projection was rederived from its raw captures. No reboot,
mode change, native mount or A90/S20+ target command was issued.

The ready task SHA-256 is
`3551fdb6215347efac476b33bc62a77330a9acafddc417be8bafd51fcfe468df`.
It contains only `userspace-probe`, one operation, 1800 seconds and attended
original-A recovery. Current live task validation passes; there is no grant,
operation or F1 owner. When the operator returns the concrete start while able
to perform physical Download recovery, the existing grant opener can start its
original clock and the fixed owner repeats fresh health and all machine checks.
Preparation does not substitute for that finite attended grant.

Private artifacts and raw evidence are retained under
`s22plus-debian-userspace-probe-h0-20260923-1` and the P403 build output.
P399/P400/P401/P402 artifacts, consumed claims, journals and terminal meanings
remain unchanged. The next actual experiment is only this fixed diagnostic
workload; Debian host PID 1 and headless networking remain later work.
