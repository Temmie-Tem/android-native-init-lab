# S22+ Debian-owned integrated boot: P425 H0 implementation

Status: **READY_H0_PRELIVE_ONLY**

The operator requested execution-code correction and qualification of a complete
Debian-owned initial boot through installed init, services and SSH. This report
recorded the structural design in commit `175123203a` before changing the integrated runtime.
It follows the [integration synthesis](S22PLUS_DEBIAN_INTEGRATION_SYNTHESIS_2026-10-13.md).
The selected target is only `SM-S906N/g0q/S906NKSS7FYG8`. No device action,
candidate consumption or grant is part of this H0 implementation.

## Bounded result

P425 `v0.6.0-rc.1` is a fresh, unconsumed boot-only integrated candidate with
reproducible artifacts, an actual ARM64 Debian initramfs-to-installed-SysVinit/
SSH rehearsal, meaningful negative paths and independent **PASS_GO** review.
The offline task is prepared. Samsung-specific hardware substitutions remain
explicit; H0 qualification does not establish physical services, SSH or recovery.

P424 remains consumed and closed healthy. Its retained PRE and the earlier
P418 raw evidence motivate the binding correction; no historical execution,
source snapshot, journal or qualification is relabelled.

## Reuse and initial ownership

The retained FYG8 kernel starts the Debian-generated `/init` shell as actual
initial-namespace PID1. Fixed temporary children perform the minimal platform
preparation and measure that shell, `/init`, their source-bound executable and
current boot. The shell then execs a small fixed root-transition entry as PID1;
it owns no general native console, renderer or resident service manager. The
existing protected root admission, RAM witness, installed init and sequential
Debian startup hooks are reused. The final owner is installed SysVinit.

The first ACM descriptor is acquired by the temporary PID1 entry. The initial
shell measurement is explicitly a preceding same-boot observation, not a claim
that the shell remains PID1 after exec. Host challenge, root-transition proof,
installed-init proof, service progress and pinned SSH must join that same boot.
The native predecessor's `three-workers-reaped` claim is not applicable here;
actual absence of other userspace/children is required with a distinct label.

## Hardware sequence and observations

Correct the stock logger path to the observed `8.samsung,kernel_log_buf` and
distinguish module, driver link, resolved target and proc-backend failures.
The fixed module inputs keep their actual Image/export CRC and digest checks.

Compare actual effects with the successful native carrier, including intermediate
provider settlement rather than only the final module list. The native path has
a SPMI/PM8350c/GPIO binding barrier after platform module 67 and before the
GENI/I2C/Max77705 consumers. The prior early helper omitted that barrier.
The native path also publishes the first USB gadget before its UFS preparation;
the integrated order must account for this difference. Source review found no selected USB/UFS consumer dependency on the 16 display
modules from the former native display path. They are excluded. This is a
changed composition; H0 does not establish display-free Samsung readiness.

Use the existing first `g1` object throughout ACM-to-NCM transition. Preserve
the fixed service observation: rcS and runlevel completion, then 13 samples of
init/cron/sshd over at least 120 seconds, before the authenticated release.
Keep bounded early RAM/retained evidence and the existing post-root durable
records. USB evidence loss, local progress and actual network access remain
separate results. Missing records never prove non-execution.

## Storage, closure and validation boundaries

Before native_data becomes writable, require the existing exact target/GPT,
partition RO, clean superblock, restricted checker and full immutable-root
admission, including the narrowly declared mutable data. No format, reinstall,
repair, general block writer or other-partition mutation is introduced.
Do not infer current dirty state from P415 or full current integrity from P422.

The intended terminal flow is the selected fixed SSH shutdown followed by one
attended physical original-A return and complete Android32 health. Unknown
execution or failed startup stops the candidate; original-A recovery remains
separately owned and never replays an uncertain transfer. Physical use requires
the reviewed exact integrated scope, current bindings and a fresh finite grant.

Validation covers the actual binding predicate on host and ARM64, A/B
helpers/initramfs/boot packaging, the real installed root and startup children,
same-boot authenticated service/SSH evidence, clean VM shutdown, and rejection
of wrong identity, incomplete providers, dirty/mismatched root and bad protocol
transcripts. Samsung module/UDC behavior remains a hardware substitution in VM.

## Current implementation evidence

The shared fixed logger predicate and all three existing consumers are corrected.
Fourteen binding fixtures passed on both host and ARM64 (28 executions), including
the observed name, the historical wrong name, missing nodes, wrong types/owners
and a dangling driver link. All three physical ARM64 consumers compile. These
results establish the correction's logic, not live probe completion.

The runtime and host owner are implemented under the separately adopted
[integrated policy](../operations/S22PLUS_DEBIAN_INTEGRATED_V1.md). Candidate
P425 `v0.6.0-rc.1` remains unconsumed. Final artifact qualification, independent
review and offline readiness pass; no grant is open.

## Integrated implementation

| Boundary | Implemented behavior |
| --- | --- |
| Logger | One shared exact binding predicate uses the observed device name and distinguishes module, link, target, and required proc nodes. Three earlier consumers use it prospectively; consumed results keep frozen sources. |
| Initial ownership | Packaged Debian `/init` is real PID1. Fixed platform and measurement children precede its exec of the temporary transition entry. An authenticated RAM record binds the earlier parent's shell, `/init`, helper, log and kernel boot. |
| Hardware order | Stock logger plus 73 retained platform modules; exact SPMI/PM8350c/GPIO barrier before client modules; first raw ACM publication; then eight UFS modules as one reaped child. |
| Root transition | No native workers are claimed. Actual userspace/child settlement and FD checks precede protected GPT/clean-root/checker/full archive admission. The original deadline is checked before the sole RO clear, RW mount and installed-init exec. |
| Installed services | Reused SysVinit and RAM startup hooks prove rcS and runlevel-2 child completion, then 13 samples of init, cron and sshd over at least 120 seconds. |
| Evidence loss | Revision-4 bounded exclusive records use checked synchronization and readback. Only classified reporting loss after durable START can disable ACM permanently while fixed service observation continues, then parks. No reopened reporting, RELEASE or SSH follows that branch. |
| Access and return | Live runtime proof precedes release and reuse of the first g1 for NCM. Pinned SSH health must join the same boot. One fixed shutdown is separately journaled; physical Download and one original A retain the existing recovery owner. |

The integrated first request has a distinct authentication domain and is an
**effectful compound start**. Its original intent is durable before any wire
write, and intended raw bytes are fsynced before each transmission. CONTINUE,
START and RELEASE require the preceding root/init/runtime proofs within the
same compound operation. An interrupted start never becomes a read retry.
The RX loop preserves bounded raw data under the original clock window; full
live source/target guards run at open and before every outgoing continuation.

The existing host access path now pins the current fixed SSH and NetworkManager
executables at fresh preparation. The retained target keys, root identity and
historical receipts are unchanged. An earlier VM prototype exposed a replaced
host SSH binary; it was not worked around with relaxed host-key verification.

## Qualification and recovery checks

The focused suite contains 160 passing tests, including the shared binding
predicate on host/ARM64, provider failures, protocol cross-phase identity,
retained-record domain isolation, raw publication failures, original intent
ordering, one-A ownership and health-only continuation after proved A. A later
host-only RX guard adjustment passed the 10 affected owner/observer tests again.

The actual ARM64 VM uses Debian initramfs-tools, the retained stock vendor
ramdisk followed by the Debian archive, the actual installed root and SysVinit,
real block ioctls/checker/root comparison, actual child processes, authenticated
C protocol producers, same-boot SSH and controlled shutdown. Hardware-only
substitutions cover Samsung board checks, module insertion/presence, provider
binding, UFS sysfs discovery, ACM and the virtual network device.

The nine cases are normal completion; changed module bytes; missing provider;
altered parent measurement; valid-CRC bad HMAC; UFS insertion failure; leaked
FD; dirty ext4; and changed root metadata. Negative cases must stop before root
transition and preserve the whole sparse disk fingerprint, with no SSH or
writable lifetime. An earlier bad-auth prototype changed the CRC-covered MAC
without reframing, so its result is only malformed-frame rejection; the final
fixture explicitly preserves valid CRC and tests the authentication failure.

The package consumer connects actual AP member bytes to the exact boot image,
qualified initramfs and retained carrier kernel/header/signature/footer. Its
first packaging attempt rejected the existing UFS policy source input before
creating an AP. The correction admits only that exact policy alongside public
source files; a new source-frozen build/VM/package set is used for final readiness.
Old successful raw results and unsuccessful attempts remain private and unchanged.

The old signed AVB metadata is retained as part of the unlocked research
carrier. It is not a newly valid payload signature for this changed ramdisk.
All AP archives still contain only `boot.img.lz4`; no other partition payload
or kernel modification is introduced.

Final construction is `build-3`, `vm-2`, `package-2` under the private
`s22plus-debian-integrated-p425-h0-20261013-1` output directory. Physical and VM
source snapshots retain 236 and 260 inputs respectively, with all 14 generated
headers retained in each. The 124-file host snapshot is separate. Actual AP
inspection joins 430 CPIO members, exactly 82 declared modules and 13 payloads.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| Debian initramfs, A/B identical | 10594573 | `380cd43afb7c6ef26a02593179baa092b516b335367cc8e8f0587a55ec3b31f4` |
| Boot image, A/B identical | 100663296 | `f8d897f7c52047e1c52d383d77602b1c2f3d99288b411bc55f4ca0b0d5d68940` |
| Boot-only AP, A/B identical | 37898281 | `ed3affee491af084fa75c0d5f7a4bd6c719e8a3d22c2c2ecd11c2e1e83a6be93` |

The final normal VM proves 13 service samples over 120073 ms, same-boot SSH,
accepted fixed shutdown, clean ext4, durable boot count 2 and 26 authenticated
local records. Each of the eight integrated negative cases preserves the whole
sparse disk fingerprint before RW. Eight additional coherently repinned
qualification mutations are rejected: virtual physical build, extra module,
short service window, promoted negative proof, foreign VM run, replaced AP,
replaced outer boot/AP pair and incorrect ramdisk digest. Their consumer audit
blocks every process launch and device acquisition.

## Limits and provenance

No phone command, connected D0 read, control, transfer, native_data write or
grant opening belongs to this implementation. The VM result establishes the
integrated userspace path with explicit hardware substitutions; it does not
establish Samsung USB/UFS readiness, physical services, physical SSH, normal
physical shutdown, automatic recovery or the cause of every earlier failed run.
The PDIC module's conditional firmware requirement remains hardware-dependent.

The source bundle adopts the already present revision-4 handoff implementation
as a necessary dependency and subjects the resulting integrated closure to the
new review. Old review tips, consumed images/journals and other-target work are
not repinned. The final private source snapshots identify the full qualified
working tree separately from any scoped commit projection. A90 and S20+ receive
no commands or edits from this unit.

The earlier P416 durable-evidence work had an interim review, not a completed
PASS_GO. Its 15 retained real-ARM64 cases are audited as individual raw facts
against their helper and CPIO bytes. Unchanged evidence/observer code covers
classified send loss, storage short-write/sync errors, pre-START loss and the
original deadline. Missing terminal result files remain missing; interrupted
files make no clean-shutdown claim. The changed reopen/close/endpoint branches
and exclusive-file refusal pass four fresh current-source ARM64 cases for P425.
The loss case completes its 120-second authenticated local service observation
with reporting disabled; the other three park without release or access. Their
private regular-file root derivatives do not execute the phone candidate.

Independent review is **PASS_GO**, with no remaining findings. It covers the
current authority, first-wire intent, source/protocol closure, protected root,
revision-4 dependency, actual AP payload and original-A owner. Its receipt
SHA-256 is `3cef56d7c67f6ead92cc077b1c34c28e6e7d2c95bb67da1024bbc3c537b99767`.
The new `s22plus_debian_integrated_v1_review.json` binding preserves every old
review tip. This is capability qualification only and opens no device grant.

The final offline preparation ran with both process launch and device
acquisition blocked. It rederived the retained P424 Android health, checked its
closed owner and the unused P425 identity, validated the new review and actual
archive, and prepared one attended `debian-integrated` operation with a
3600-second proposal. `ready-audit.json` records **READY_H0_PRELIVE_ONLY**;
`offline-1/task/task.json` and the proposal remain private. No grant, fresh
connected health, current root admission or image transfer is claimed.

The commit includes the S22+ implementation and necessary revision-4 dependency.
Its AGENTS projection omits only the two preexisting S20+ changes while preserving
the working file and the exact common-details pin. The private review covers
both policy forms. Prepared execution remains bound to the complete frozen
working-tree source receipts; a clean checkout is not an implicit rebinding.
All 60 unrelated/preexisting file contents outside the four deliberately
updated shared inputs remain byte-identical to this unit's initial snapshot.
