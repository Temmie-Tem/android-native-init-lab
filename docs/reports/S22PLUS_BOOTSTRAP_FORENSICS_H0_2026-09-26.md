# S22+ bootstrap forensics after P407

Date: 2026-09-26 KST. Target: `SM-S906N/g0q/S906NKSS7FYG8`.

## Finding

No single bootstrap defect or historical stop instruction has been established.
The investigation did obtain new evidence: the failed boots did not register
their expected USB gadget in retained host kernel logs; P407 returned to a
Download USB generation before the host started recovery; and P406's retained
root contained no additional regular files beyond the known installation
markers and witness. Several concrete packaging, kernel-code, ELF and ABI
hypotheses were also checked against the actual consumed artifacts and rejected
or substantially weakened.

The strongest remaining question is the standalone bootstrap's progress before
and across root handoff, with P407's separate cleanup/observer startup also
unlocated. Missing SSH is not a diagnosis of switch_root. P407 deliberately
never executes switch_root, and its missing record does not prove that the
earlier pre-handoff code failed at the same instruction as P401/P404/P405.

This was H0 work only: retained-source and archive inspection, ELF/kernel/module
disassembly, host journal reads, primary-source research and host reproductions.
There were no device commands, new grants, image transfers, filesystem repair
or changes to consumed evidence. P407 remains consumed and closed with its
original healthy-Android terminal. P406's filesystem observation predates
P407; it is not evidence of the root's state after P407. A90/S20+ were untouched.

## New USB evidence

The existing run records were joined to retained host kernel journals, limited
to the two bound USB paths and the corresponding host boots. These logs are
independent of the Python endpoint selector.

| Case | Retained host lifecycle | Consequence |
| --- | --- | --- |
| P401, P404, P405 | Candidate Download generation disconnects; no intervening Debian NCM registration on the bound paths; a later Download generation appears. | No supporting evidence that an enumerated Debian gadget was merely hidden by an SSH, MAC or selector problem. |
| P406, positive control | Native `04e8:6861`, `S22+ E3 ACM`, `cdc_acm` and a tty registration appear 17.234 seconds after candidate Download disconnect. | The retained host log and shared physical path do record a working native gadget. |
| P407 | A new `04e8:685d` Download descriptor registers at grant elapsed 215.241 seconds, before research stops at 320.194 seconds. | Download had returned about 105 seconds before host recovery began, roughly 195 seconds after N transfer completed. |

The P407 registration corroborates the USB node birth time retained by its
recovery census. At that point the owner was only waiting for an endpoint;
there is no native open/AUTH/CONTROL record, and the fixed preflight producer's
failure branches park rather than request Download. This entry therefore
cannot be attributed to the V3 normal CONTROL path. Physical button activity,
device reset and bootloader fallback remain unresolved alternatives. No
automatic-recovery claim follows from this observation.

The historical P404 selector bug remains a real, reproduced bug. The additional
host lifecycle evidence does not support the claim that it hid an actual NCM
registration during P404. The run-local absence of negative USB samples remains
a historical limitation; the later host-journal analysis is separate evidence,
not a rewrite of that run.

All ten selected N/A transfer captures satisfy their existing bounded Odin
completion criteria. That establishes the retained transfer result, not kernel
entry. P407's host census/binding inputs match successful P406; its wait loop
still lacks individual negative tty/sysfs snapshots. The host journal cannot
prove that the target never attempted gadget configuration, only what the host
recorded as USB registration.

## What the P406 root actually excludes

The audit independently decoded the real P406 inspection table, compared it
with all 8,969 members of the retained P401 root archive, and reconstructed the
705-byte inspection stdout from CRC-checked wire frames. Its digest matches the
original authenticated closure.

| Inventory | Regular files | Directories | Symlinks | Regular-file bytes |
| --- | ---: | ---: | ---: | ---: |
| Archive and comparison table | 6,819 | 1,004 | 1,146 | 199,362,324 |
| P406 observation | 6,822 | 1,005 | 1,146 | 199,366,660 |
| Difference | 3 | 1 | 0 | 4,336 |

The validated start marker, completion marker and witness account for all three
additional regular files: `120 + 120 + 4096 = 4336` bytes. All expected paths
matched in metadata and content. Consequently, no other new regular file or
symlink remained at P406. The extra directory is consistent with lost+found,
but the captured aggregate digest alone does not directly identify its name.

The actual archive contains no `/var/lib/urandom/random-seed`,
`/var/log/dmesg` or `/var/lib/lab/boot-count`. Its serial service graph normally
creates these before `S02lab-usb`: urandom in rcS, then bootlogs and
lab-firstboot in runlevel 2. The archive's zero-length `/var/log/wtmp` also
still matched. These observations oppose an ordinary successful late boot
whose only problem was the host network selector. They do not prove that
Debian init never executed: an early stop, failed writes or other unobserved
behavior could leave the same filesystem state.

The matching [Debian SysVinit 3.14-4 source](https://sources.debian.org/src/sysvinit/3.14-4/src/utmp.c/)
attempts wtmp updates only when the existing file is writable. That conditional
behavior prevents treating an unchanged wtmp as unconditional proof of absent
PID 1 execution. Its [init implementation](https://sources.debian.org/src/sysvinit/3.14-4/src/init.c/)
also supports a null-console fallback; lack of an early terminal is not alone
a demonstrated init failure.

P401's validated completion marker is positive evidence that execution reached
the marker-creation point after module loading, checking, extraction and
content validation. The marker precedes the final unmount and superblock/GPT
checks; it does not prove their completion or later handoff. P403's chroot child
and P406's protected inspector supply different evidence: they operate under
the already working native runtime and do not independently demonstrate the
standalone cold preparation sequence or full Debian PID 1 replacement.

The clean superblock supplies a further **conditional inference**. In the
retained GKI ext4 source, successful journaled RW mounting sets RECOVER and
synchronously commits the superblock. P405's final mount has a journal and no
`noload`; mount moves and switch_root do not clear RECOVER. The later zero bit
therefore weakens the specific sequence “successful RW mount, then only a park
and abrupt reset.” An earlier stop is more consistent with it, but so are a
later clean unmount, remount-RO, freeze or recovery lifecycle. The configured
`errors=remount-ro` error branch aborts the journal without this clean-clear
sequence. These source conditions do not prove a historical mount or absence
of one. Orphan-head zero adds little localization.

## Actual artifacts, kernel code and ABI

| Hypothesis checked | Result and limit |
| --- | --- |
| Wrong P407 helper packaged | The sole AP member was decompressed and parsed again. `/init`, `/s22-prehandoff` and the reader match the retained build artifacts. |
| Vendor ramdisk overwrote the new init | The combined member model places generic boot `/init` last; no preexisting preflight intent or non-directory parent conflict was found. This is an archive/source check, not a capture of live unpacking. |
| P407 changed kernel execution code from P406 | Both extracted kernels are 41,490,944 bytes. All 34,139 differing bytes are confined to compressed IKCONFIG and the declared run-ID data span. Decompressed settings differ only in that run ID; no bytes outside those spans differ. Whole kernel hashes are intentionally different. |
| ARM64 ELF or missing bootstrap interpreter | Actual bootstrap/helper executables are static AArch64 ET_EXEC without PT_INTERP/PT_DYNAMIC. No required BTI/PAC/GCS property was found. This excludes a missing dynamic loader for the static bootstrap, not all later installed-code faults. |
| Missing close_range | The actual kernel wrapper and target UAPI support syscall 436; P403's successful setup also required it. P407 uses flags 0. |
| Static libc blocks waiting for entropy or requires RSEQ | The actual P407 helper reaches main under qemu-user despite unsupported RSEQ; startup getrandom is nonblocking. This is a representative host ABI check, not physical boot proof. |
| DEFEX rejects the new helper pathname | Actual P407 kernel disassembly confirms the PID 1 allow branch before DEFEX path checks. This excludes that specific explanation for the initial exec, not all LSM behavior or later children. |
| NCM function missing as an unloaded module | The extracted kernel has LIBCOMPOSITE, U_ETHER, F_NCM and CONFIGFS_NCM built in. Absence of an NCM module in the 81-module plan is not this defect. |

The ramdisk order agrees with the [AOSP vendor-boot specification](https://source.android.com/docs/core/architecture/partitions/vendor-boot-partitions).
The retained target's `init/initramfs.c` implements type replacement and regular
file truncation for later entries, consistent with the [Linux 5.10 source](https://github.com/torvalds/linux/blob/v5.10/init/initramfs.c).
The actual helper and outer-init disassemblies, extracted kernel configurations
and narrow kernel function-byte bindings are retained privately.

## Preparation, observation and watchdog paths

P407's 81 module bytes, order and empty parameters match P401/P405 after the
declared path change from `/s22-modules/` to `/lib/modules/`. The real module
scanner was compiled and exercised with all 81 exact runtime names in reversed
order: it accepted all entries, with EOF and no malformed rows. No hidden
73-module ceiling was found. Inspection of reachable observer consumers found
no mandatory side effect lost by removing the retired temporal callbacks.

This does not validate every physical driver probe. Synchronous module
insertion can stall outside the child runner's deadlines. The measured child
workloads have 30-second individual and 240-second total budgets, but no
retained P407 record establishes which child, if any, ran or timed out.

P407's evidence transport has a confirmed limitation: its observer starts only
after all 81 modules have completed and processes, descriptors, mounts and
partition checks have settled. Incomplete modules, timeout, output overflow,
unsettled children, failed unmount, failed final readback, invalid sealed record
or early exec failure can all leave no externally collected stage record.
Success in the virt tests does not remove this blind region. Weakening the
cleanup or module-adoption guards would not resolve it safely.

The exact Qualcomm watchdog module initializes kernel petting independently of
Android userspace. Disassembly gives 9.36-second pet and 11-second bark defaults;
initialization sets bite at 14 seconds. Userspace-pet activation is disabled in
the shipped module. The E1 token child performs no watchdog or boot-complete
operation. Samsung boot-stat is accounting code and is not loaded by this plan.
There is no identified 180–200-second Android boot-complete timer in these
reachable components. The enabled hung-task detector does not panic by default;
an actual oops/panic can reboot immediately. No retained target fault record
establishes such an event. Firmware/hypervisor state before Linux watchdog
initialization remains outside this evidence.

The retained root's udev startup link is not a conflicting running device
manager: its daemon is absent and the script exits at its initial executable
check. Serial rc ordering is selected by the archived `.legacy-bootordering`
file; mount-configfs precedes lab-usb. This rules out those particular static
service-graph hypotheses, without proving physical gadget configuration.

## Next bounded question

Prioritize an H0 design that returns a stage result before the currently silent
cold-entry/module/cleanup boundaries, using the existing proven native
bring-up and transport where applicable. Separate a preparation-complete
observation from replacement-PID-1 entry. A record that becomes readable only
after all of the suspected operations succeed repeats the present limitation.
Preserve the functional objective of full Debian ownership; a chroot remains
a diagnostic child, not the delivered architecture.

Do not change the filesystem, increase timeouts, add watchdog petting, replace
the kernel or switch root implementation on these findings alone. The prior
[switch_root study](S22PLUS_SWITCH_ROOT_RESEARCH_H0_2026-09-26.md) still applies:
the bootstrap's exec error branch catches failure to start BusyBox, not a later
failure inside the replacement BusyBox program. The exact physical boundary
still needs an independent observation. Any prospective device operation needs
its own applicable qualification and authority; no consumed image is replayable.

## Retained H0 evidence and validation

Private audit root:
`workspace/private/outputs/s22plus-bootstrap-forensics-h0-20260926-1/`.
It contains separate ELF/ABI, preparation/watchdog, transport and root-state
joins, the exact disassemblies and host journal slices, ramdisk and service
audit results, primary-source retrieval and reproducible audit scripts. Raw
identifiers and addresses remain private. Historical run records were read
without modification.

The 13-entry H0 evidence index is 2,258 bytes, SHA-256
`15a4d27bc7662694181316c33b8d60622312b7b6f462f47d38321f04380ce2fc`.

Web discovery requested 20 results across four source angles; only relevant
primary documents/source were used for technical claims. Matching Debian source
was fetched directly when the search fetch returned an access challenge.
Validation covers actual AP extraction, kernel byte/config comparison, real
module-parser execution, archive-to-inspection-table parity and raw wireframe
rederivation. These are targeted forensic checks, not another Samsung boot test.

See the unchanged [P407 live result](S22PLUS_NATIVE_PREFLIGHT_P407_FIRST_RUN_2026-09-26.md),
[P406 root observation](S22PLUS_NATIVE_ROOT_STATE_P406_FIRST_RUN_2026-09-26.md),
and [P405 live result](S22PLUS_DEBIAN_INSTALLED_BOOT_P405_FIRST_RUN_2026-09-26.md)
for their original authority, timeline and proof boundaries.
