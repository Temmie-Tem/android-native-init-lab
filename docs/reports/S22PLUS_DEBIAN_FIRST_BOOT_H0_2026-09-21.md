# S22+ first Debian installation and full handoff preparation

Subsequent result: the [2026-09-23 P401 attempt](S22PLUS_DEBIAN_P401_FIRST_RUN_2026-09-23.md)
closed with Debian proof absent and healthy Android restored. The preparation
state below is historical; its candidate and installation claim are consumed.

Date: 2026-09-21. Target: `SM-S906N/g0q/S906NKSS7FYG8`.
Device effects at this preparation stage: **zero**.
Independent capability review passed for the final source closure, including
the exact host relocation below. Fresh connected preparation is separate from
the H0 results. The final fixed D0 preparation passed; no finite live grant
has been returned and no device transition or installation has occurred.

## Constructed candidate and scope

P401 `v0.4.0-rc.1` embeds the Debian root archive in a 96 MiB boot image.
It uses the exact retained FYG8 Image and boot-v4 packaging. Both builds are
byte-identical; AP has one regular `boot.img.lz4` member.

| Artifact | Size | SHA-256 |
| --- | ---: | --- |
| Boot image | 100,663,296 | `9153df32ad46ead59927ff5b386f322ab6c971352a0dce4e75022a2665f102be` |
| Boot-only AP | 74,127,401 | `978156d72ccb9bdf67d679f5a238b94d9d8928c8dae2dc2a4da45cc106c5da1c` |
| Device root tar | 202,014,720 | `ef8f10f95effcb92bf2b40525c9b8cb9c0e97857d2796c3b9e6c115a882df04f` |
| Embedded xz | 42,985,044 | `34ff200ec7b1cb28f735fa27bfb78bfb7b9f91a47b7557a6ee451a79e7c68601` |

The rootfs derives from the previously verified Debian 13 arm64 package
closure. The overlay binds unique private keys/USB identities, local NCM
configuration, restricted root qualification commands and an offline signed
`hello` package. The complete release label includes `rc.1`.

The fixed bootstrap retains the proven 73-module platform order and eight
stock UFS modules, with no DRM userspace. It resolves only the exact native
extent, verifies full GPT, filesystem identity/clean state and the existing
witness, and runs the fixed read-only checker. The whole-LU alias is removed
before Debian; mdev suppresses all other block nodes.

Only an empty witness-bearing native filesystem admits installation. A
durable exclusive start marker precedes extraction from a hashed sealed RAM
descriptor. Complete content/metadata readback, synchronization and clean
unmount precede completion. A partial/dirty installation cannot be retried.
The normal second boot verifies the installed inputs and never extracts again.
The bootstrap then execs Debian SysVinit as initial PID 1, with no resident
native supervisor. Debian owns logging, cron, USB/SSH and shutdown.

The overlay uses SysV serial service ordering and removes automatic
filesystem-repair/RTC startup links and e2scrub scheduling. The empty fstab,
single gadget owner and fixed role write avoid the specific conflicting
startup paths found during review. Bound package/configuration files remain
immutable for this first qualification pair; arbitrary updates are unqualified.

## H0 evidence

The actual-artifact qualifier independently reparses the AP and boot, compares
the retained kernel/header/signature/vbmeta identity, checks exact ramdisk
metadata/module sources, rederives both archive manifests, and joins private
keys/network configuration to the installed root. Saved pre-build source
bytes must match their declared identities and the current critical closure.

The `vm-2` run uses real ARM64 Linux 5.10 and the actual installer against a
4096-byte-sector disk with the complete sealed GPT and native ext4 geometry.
Virtual board discovery, module insertion and Ethernet are explicit substitutes.
Its keys and archive are separate H0 identities; critical C and qualification
service bytes match the physical candidate.

Actual raw observations prove completed installation, initial PID 1/root
handoff, the sole native block node, key-pinned SSH, lab PTY, logging/cron,
offline package execution, ordinary reboot with a distinct boot ID, retained
workload receipts and normal VM shutdown. The read-only host filesystem check
passes. These results do not prove FYG8 hardware boot or physical recovery.

`negative-2` contains six real ARM64 rejection cases. GPT corruption, wrong
UUID, changed witness, start-only installation and archive digest mismatch
stop before writes; their complete sparse data extents, positions, size and
mtime are unchanged. An authenticated archive/readback inconsistency leaves
a consumed partial installation. A second boot stops without modifying it.
The sparse comparison is an extent-aware equality check, not a whole-file hash.

Host owner tests cover raw control acknowledgments, contradictory identities,
host-epoch journal cuts, original finite-grant identity, actual transfer-body
timeout/resumption, consumed-A no-replay, reporting cuts, terminal tampering
and missing evidence. They replace only device/tool boundaries. Candidate-only
code loss cannot block the separately frozen Android recovery closure.

All artifacts, keys, machine identities and raw evidence remain under the
private `s22plus-debian-device-prep-20260921-1` output. The accepted artifact is
`artifact-7`, joined by `qualification-7.json`; earlier build prototypes do not
inherit its qualification. Prior P399/P400 terminals remain unchanged.

## Host SSD relocation discovered before connected preparation

The first preparation stopped at the global session lease, before any ADB
command, grant, F1 owner or candidate claim: both lock inodes had changed after
the host SSD migration. The original device-number-only exception correctly
rejected this case. The failed plan/review and empty journal are retained.

The old SSD was mounted `ro,noload` and its original registry validated against
the original lock inodes. All 84 consumed records, activation, head and lock
payloads match the new SSD byte-for-byte; there are no releases. Both copies
had no F1 owner or pending D1, and all four writer/session locks were held
nonblocking during immutable proof publication. No old registry bytes changed.

A separately reviewed exact-digest host-relocation receipt binds the new lock
identities to the original activation and complete retained consumed prefix.
The registry keeps that prefix and accepts later normal appends; unreviewed
receipts, prefix loss and another inode replacement fail closed. This is a host
identity repair, with no claim release, activation rewrite or device authority.
Other lanes' existing source approvals remain unchanged. Thirteen registry
tests, including four relocation cases, and 24 Debian owner tests pass.
The independent reviewer also held all four locks and compared both actual
copies. Its final `PASS_GO` binds request SHA-256
`ac7b27457051c0b5ed3f2f8fbb479c903ed9e10280ea448d5ec5c0bee0b8c206`.
The old SSD was then unmounted. This review creates no finite device grant.

## Fresh connected preparation

The next preparation retained one failed health read: ADB returned status zero
and the property response, but its first host-server startup messages appeared
on stderr. The strict reader rejected it. There was no timeout, overflow,
producer fault, grant or device transition; this read was not promoted to a
complete health result.

The profile's fresh bounded reobservation then completed 17 fixed D0 reads:
both rooted-health brackets, shell-v2 capability, complete GPT metadata and
native partition/statfs observation. The same Android boot remained healthy,
the full GPT was unchanged, and Android32 statfs totaled 34,357,624,832 bytes.
The actual original-A artifact/recovery basis and exact candidate remain bound.
The accepted plan is retained in `p401-first-boot-run-3`; the earlier failed
preparations and their raw evidence remain separate. Its journal has no effect
intent, and the finite attended grant has not been returned.

## Live completion criterion and recovery

The [new common-incorporated exception](../operations/S22PLUS_DEBIAN_FIRST_BOOT_V1.md)
admits only one first installation/workload/reboot/shutdown/Android-return unit
after independent review, current exact target health and an actual returned
attended grant of at most 7200 original BOOTTIME seconds. It preserves the
existing filesystem, witness, Android32 GPT and original-A identity. There is
no format, repair, partition-table write, Android staging or other-target action.

The global F1 owner and installation claim are durable before candidate launch.
One ordinary Debian reboot must show the previous boot's durable request and
a different healthy boot. SSH disappearance never proves shutdown or poweroff.
Normal return requests shutdown and then requires actual attended physical
Download entry, which ends the previous kernel before the single original-A
transfer. Failure uses that same physical recovery; no automatic recovery is
claimed. Expiry and candidate-only source changes do not renew research or
remove recovery ownership. An original-A intent never permits another transfer.

Final Android root/partition hashes, full GPT and exact Android32 statfs must
rederive independently. A conservative `NO_PROOF` candidate can close only with
that healthy Android result. Android return neither uninstalls Debian nor
proves native filesystem integrity after an unobserved shutdown. Internet,
Wi-Fi, display, hotplug, thermal behavior, later Debian sessions and mutable
root updates remain outside this first unit.
