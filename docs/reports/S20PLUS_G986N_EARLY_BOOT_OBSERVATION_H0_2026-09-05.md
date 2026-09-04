# S20+ G986N early-boot observation paths — H0

Date: 2026-09-05
Target: `SM-G986N / y2q / y2qksx / G986NKSS8IYC2`
Result: **H0_STATIC_OBSERVATION_PATHS_IDENTIFIED_NOT_LIVE_PROVED**

## Decision

Select a **fixed read-only pstore/PMSG readiness D0** as the next experiment.
Its exact reader/profile still needs H0 implementation and the target's
required review and activation. This report creates no connected authority.

The retained firmware contains a concrete ramoops reservation and PMSG path,
so an independent early-boot observation channel has a stronger static basis
than the earlier configuration-only evidence. First establish whether that
existing path is instantiated and readable on the exact live target. A later
controlled marker-and-return experiment must prove retention before another
direct-PID1 candidate depends on it.

The completed P0 V3 remains consumed and `NO_PROOF`. Its current C entrypoint
parks without emitting a stage receipt on PID, mount, configfs, gadget, or ACM
open failure. It creates `/dev/kmsg` but never writes a diagnostic there and
has no PMSG writer. The first external positive is the final ACM banner.
Consequently its missing banner does not identify the failed stage or disprove
PID1 execution. See [current P0 state](../../GOAL_S20PLUS.md#current-p0-pid1-odin-f1-state).

## Inputs and artifact findings

All extraction, decompression, DT overlay application and source inspection
were host-only. Original inputs were read through the existing private storage
layout. No candidate was built, activation changed, journal resumed, or device
contacted. S20+, S22+, A90 and other-target command counts are all zero.

The exact firmware ZIP and source bundle hashes were freshly verified against
the [acquisition record](S20PLUS_G986N_STOCK_ARTIFACT_ACQUISITION_H0_2026-08-13.md).
The nested target-source ZIP and `Kernel.tar.gz` hashes also matched. Only
selected source files and offline image components were extracted privately.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| stock boot | 67,108,864 | `29fde3a189b906ea20ed0e14fcd7a448e005597b82e3adceea64196284bd31ab` |
| resident boot | 67,108,864 | `d67d0af219d40d29f9e4d34da873e7aa33577d56fab68e2beccfe707418f7efc` |
| consumed P0 V3 boot | 67,108,864 | `dd4f1d0347983ac35f7d2692ff6fc4ad89ccc1a895b948bf7c330c736f6af073` |
| retained T2 recovery artifact | 82,694,144 | `d46a1f72743a28acc4c820184d7318df9801ee43d425c22d092778e4b63d1f89` |
| stock boot DTB bundle | 1,580,275 | `09ce85eab63208c985486bba8b450d17fd5907839361b53bf1971e0eeaceb883` |
| stock DTBO image, offline extraction | 10,485,760 | `b1135536cc5016352fa38a5406d42c67197c8134d5215cba8e5bba65f9d9dded` |
| source `Kernel.tar.gz` | 214,726,875 | `4ed0aa2f390d9d847eee313693fe8b9b726f4decefc40b3ba8fde1b64272ae6d` |

Stock, resident and P0 embedded final configurations are byte-identical at
SHA-256 `5e4e4a986f7aae396dc3ebb03818a4c0b9bea5f6948c5e17eb6abaf8d988f760`.
Resident and P0 kernels are byte-identical to each other; they differ from
stock in three bytes. Source-derived behavior below is not a claim of a
reproduced stock kernel build or direct proof of its runtime behavior.

## Ramoops and PMSG

The boot DTB bundle contains three platform trees for kona v2.1, v2 and v1,
plus one RTIC metadata blob. None alone contains a ramoops node. The separate
stock DTBO has two Y2Q Korean board overlays, board IDs 13 and 14, plus one
version metadata entry. **Both board overlays add the same ramoops node to
reserved memory.** Looking only at boot's base DTBs would miss it.

All six platform-tree/board-overlay combinations applied successfully with
`fdtoverlay`. Independent `dtc` decoding and `fdtget` property reads agreed:

| Property | Static value in every merged pair |
| --- | --- |
| compatible | `ramoops` |
| reserved region | 1,048,576 bytes |
| record-size | 262,144 bytes |
| console-size | 262,144 bytes |
| ftrace-size | 262,144 bytes |
| pmsg-size | 262,144 bytes |
| node and ancestor status | no disabling status |

These are region sizes, not guaranteed usable payload capacities; the driver
accounts for its headers. Physical addresses and full DT extracts remain in
private evidence. The live bootloader's actual DT selection was not observed.

The embedded configuration enables `CONFIG_PSTORE`, `CONFIG_PSTORE_RAM`,
`CONFIG_PSTORE_CONSOLE` and `CONFIG_PSTORE_PMSG`. Exact source inspection shows:

- `fs/pstore/ram.c:684` parses the DT region and sizes; `ram.c:981` registers
  the driver at `postcore_initcall`. Probe success remains a runtime question.
- `fs/pstore/platform.c:598` registers the PMSG frontend when the backend
  provides a PMSG zone. `fs/pstore/pmsg.c:64` allocates a dynamic character
  major and creates `pmsg0`; a future witness must derive the actual device
  number rather than copy another target's number.
- `pmsg.c:22 -> ram.c:463 -> ram_core.c:350` accepts userspace bytes into the
  PMSG RAM zone, independently of USB enumeration and console output. This
  path does not require a panic or a raw block write.
- `ram_core.c:493` recognizes a valid previous RAM buffer and saves its old
  bytes. `ram.c:630` prepares a new console/PMSG zone while retaining the old
  snapshot; `ram.c:241` exposes old records through pstore.

There is no stock devtmpfs support. A direct-init witness therefore needs a
reviewed way to obtain the dynamic PMSG device number and create its volatile
node. The current P0 implements neither operation for PMSG.

**Unproved:** live backend registration, current node accessibility, buffer
retention through the exact physical/Download/rollback route, record freshness,
and reader availability before a subsequent kernel boot replaces the old
snapshot. Power-cycle survival cannot be inferred from reserved RAM or from
successful offline DT application.

## Recovery reader and secondary logging path

Fresh unpacking of the retained T2 artifact verified that its kernel, boot
header and base DTB are byte-identical to stock. Its embedded recovery-DTBO
container has three entries, each byte-identical to the corresponding stock
DTBO entry above. Its ramdisk includes a pstore mount in
`system/etc/init/hw/init.rc:148` and a `/dev/pmsg0` ueventd rule at
`system/etc/ueventd.rc:45`. These are static reader prerequisites, not proof
that a particular recovery boot has mounted or retained records.

The alternate Samsung path is also worth checking. Embedded configuration
enables `CONFIG_SEC_LOG_BUF_NO_CONSOLE` and `CONFIG_SEC_LOG_LAST_KMSG`.
`kernel/printk/printk.c:709,3455` copies stored printk messages through a hook
that is independent of console registration. `/dev/kmsg` writes reach this
store path. `drivers/samsung/debug/sec_log_buf.c:102,163` copies the previous
Samsung log and creates `/proc/last_kmsg`.

That Samsung path depends on the `sec_log` early parameter and successful
mapping/initialization. The static boot header contains `console=null` and
`printk.devkmsg=on`, but no `sec_log` parameter. A bootloader-appended value and
the live initialized state were not established here. The stock reboot
notifier also has a debug-partition storage branch (`sec_log_buf.c:290`);
this report does not propose invoking or reading that partition path.

A saved kernel line announcing `Run /init as init process` is emitted before
`do_execve` (`init/main.c:1355`); it proves an attempted dispatch, not a first
userspace instruction or successful native PID1 execution. A future positive
PID1 receipt must be emitted by the intended candidate after its own PID check.

## Watchdog interpretation

The relevant built-in driver is `CONFIG_QCOM_WATCHDOG_V2`, with DT compatible
`qcom,msm-watchdog`; the unrelated `CONFIG_QCOM_WDT` is disabled. Every offline
merged tree has a 9,360-ms pet interval and 11,000-ms bark interval. The source
programs bite three seconds after bark, starts a kernel pet thread, and sets
`user_pet_enabled=false` during initialization (`watchdog_v2.c:652,951,960`).

Source therefore supports a quiet sleeping PID1 while the kernel continues
petting its watchdog. It does **not** establish a 14-second automatic recovery
deadline for a P0 park. Live overrides, driver initialization and other reset
sources remain unobserved. No watchdog manipulation is proposed.

## Next bounded experiment

Implement and qualify one **fixed read-only pstore/PMSG readiness D0**. Reuse
the exact-target inventory and pre/post healthy-current-boot binding of the
reviewed S20+ root-health approach. Do not run the existing root-health profile
as a substitute for the additional, currently unapproved reads.

The new profile should answer only:

1. Does the live DT's fixed ramoops property set match the offline geometry,
   and does the bound platform device have the expected driver?
2. Is the pstore backend `ramoops`, with the expected PMSG/console sizes, and
   is `/sys/fs/pstore` already mounted as pstore?
3. Does the fixed PMSG class entry agree with the direct `/dev/pmsg0` character
   node, and are the closed previous-record filenames and `/proc/last_kmsg`
   readable under bounded metadata checks?
4. What are the fixed watchdog driver's read-only pet/user-pet state fields?

Return fixed typed facts, matches and private digests; do not export full DT,
command line or log contents. An unmounted pstore is an observation, not an
instruction to mount it. Missing records do not disprove backend support or
the previous candidate's execution. No marker write, reboot, pstore deletion,
configuration change, new candidate or payload belongs to this D0.

If readiness is established, the following separately reviewed experiment can
test one uniquely bound finite marker across the intended return route. Its
reader must collect the first returned kernel's old snapshot before an extra
boot loses attribution. Only positive retention evidence would justify using
that channel in a new stage-reporting PID1 candidate. N3-U0 remains an alternate
USB-specific investigation; it is not the next selected experiment here.

## Verification and durable evidence

Private audit root:
`workspace/private/work/s20plus-early-observation-h0-20260905-4rc4tpir/`.
`verification.json` SHA-256:
`b353150c586f9b09111b2eeb66e89bfd06ab8ffc05e149dd1ef7b67560945e89`.

The private `verify_findings.py` passed `py_compile` and rechecked component
hashes, embedded configuration extraction, complete base-DTB byte coverage,
all six merged DT results, recovery component equality and source receipts.
Supporting files include `boot-components.json`, `dtb-index.json`,
`dtbo-index.json`, `overlay-validation.json`, `merged-status-and-watchdog.json`,
`recovery-dtbo-comparison.json`, `t2-init-log-paths.json`, `kernel-delta.json`
and the exact extracted source subset. Firmware, compiled DTs, raw image
components and private results remain untracked.

The source receipt map binds the cited files to the freshly verified source
archive. Neither these static checks nor this research decision activate D0,
F1, R1, recovery, autonomous research, or a consumed candidate.
