# Goal: S22+ Debian on native storage

Build a usable Debian arm64 environment on dedicated native storage, following
the operator's A90-style direction. The selected prospective allocation is
32 GiB Android userdata and approximately 191.458 GiB native storage; the
completed device layout below still has 128 GiB native storage. Start from the FYG8
vendor kernel and native hardware bring-up, retaining observable native
control and bounded recovery while Debian execution is qualified.
This goal records state, never device authority. Select only the operator-owned
`SM-S906N/g0q/S906NKSS7FYG8` through `AGENTS.md` and its binding target contract.
A90 and S20+ remain isolated.

## Latest completed unit — storage reservation

**128 GiB native storage is reserved, and rooted Android is retained.** The
operator-authorized G2 run reduced userdata to 95.4580078125 GiB, created the
128 GiB `native_data` entry, preserved the other 39 entries, and initialized
Android through the unchanged stock recovery. Native storage remains unformatted.

P397 `v0.3.0-rc.1` completed two-installation/four-session native admission and
actual complete original-GPT read qualification. One apply wrote four metadata
blocks with synchronized full readback. Fresh native boots proved the proposed
GPT and kernel geometry both before and after the single stock factory reset.
The existing exact Magisk A was installed once.

Android Device Care displayed 128 GB in the operator photograph. Machine reads
before and after the single planned ordinary Android reboot proved identical
complete GPT, the 128 GiB native entry, `/data` statfs total 102,495,141,888 bytes,
and numeric UID/GID 0 with exact A/supporting partition hashes.
The final verdict is `RESERVED_ANDROID_REBOOT_VERIFIED` with
`PASS_CHANGED_BOOT_GPT_CAPACITY_AND_ROOT` and `ANDROID_CLOSED_HEALTHY`.

The initial root probe returned missing-su rc127 during operator setup. A later
rooted health bracket passed; a setup-period boot change was observed without
assigning its cause. A separately reviewed fixed completion entry preserved the
original stop and sources and issued only the remaining planned checks/reboot.
The first final-health attempt lost ADB before its root command. Existing
health-only recovery then supplied the complete final proof. The terminal
therefore retains `recovered=true`; neither failed read was relabelled.

The original 7200-second/two-operation grant is closed after 3193.642 seconds,
with both operations consumed and no F1 owner. There was no GPT restoration,
restorative reset, extra native recovery installation or repeated A transfer.
No standing grant or further format/partition authority remains.

See the [live result and canonical timeline](docs/reports/S22PLUS_NATIVE_GPT_128G_LIVE_2026-09-15.md),
[layout and H0 qualification](docs/reports/S22PLUS_ANDROID_STORAGE_CENSUS_H0_2026-09-15.md),
and [G2 scope](docs/operations/S22PLUS_NATIVE_GPT_RESERVATION_V1.md).

## Debian direction and next bounded unit

The operator selected 32 GiB Android userdata for a minimal management/return
environment, with unused apps cleaned up after Android reinitialization. The
last retained final-health snapshot reported 2,806,255,616 bytes (about
2.614 GiB) used in `/data`; this is an initialization-time observation, not
qualification of a smaller filesystem or a prediction of long-term usage.
Keeping the current combined userdata/native extent gives approximately
191.458 GiB for Debian. These sizes describe actual partitions, not Samsung's
rounded storage-UI labels.

P398 `v0.3.0-rc.2` now passes H0 construction of that exact successor, the
actual ARM64 stock-formatter geometry check and byte-identical A/B image/AP
qualification. It starts from the closed P397 GPT and preserves the existing
native identity. The [preparation report](docs/reports/S22PLUS_ANDROID32_AND_MINIMAL_ANDROID_H0_2026-09-16.md)
records its setup, recovery and validation scope. A fresh finite attended G2
grant and actual new-endpoint read qualification still precede any new device
effect. Qualify reduced Android capacity, rooted return and reboot persistence
before native filesystem use. The consumed P397 grant cannot implement this successor.

App cleanup will follow fresh package/dependency and storage inventory. Select
unused optional apps through Android package management, preserving required
system components, settings, connectivity, ADB and Magisk. Distinguish package
disablement from deletion of app updates/data/cache, and measure actual `/data`
space reclaimed; disabling a system APK does not resize its source partition.
The separate [fixed optional-app profile](docs/operations/S22PLUS_ANDROID_MINIMAL_V1.md)
binds the existing explicit cleanup request, independent source review, one
cleanup open per closed Android32 task and actual attendance. It follows the
proved G2 closure and measures final capacity/root after one ordinary reboot.
An uncertain uninstall or reboot never replays. No app inventory or cleanup
device effect has yet occurred, and this goal grants no device authority.

Prepare the Debian storage structure alongside this layout design.
Ext4 is the first candidate: check the exact FYG8 kernel features, arm64
formatter and mount behavior, then define one bounded format/mount/write
experiment. Its functional criterion is a small synchronized test file that
remains byte-identical after clean unmount and a fresh native boot, followed
by verified rooted Android return. For this filesystem experiment, only the
new native partition is the proposed persistent-write target; no device
format or mount is activated here.

The subsequent milestones are prospective and separately qualified:

1. Prepare a minimal Debian arm64 root filesystem on the host and prove its
   loader and basic commands against the target ABI before device staging.
2. Execute a bounded Debian shell/basic workload from native storage, with
   explicit process, mount and device ownership and a proved native return.
   A shell result alone does not prove Debian init or an independent boot.
3. Establish Debian service startup, a qualified IP path and authenticated SSH;
   verify persistence and cleanup/recovery across the selected reboot path.
4. Add display/input or a desktop environment after the headless path works.
   Full init handoff versus a supervised Debian namespace remains a later
   S22+-specific design decision, not a prerequisite for the first shell proof.

[A90's current goal](GOAL_A90.md) provides references for UFS filesystem
identity, mounting, Debian startup and native fallback. Its isolated-Debian
architecture and earlier separate feature observations do not constitute a
completed integrated S22+ capability or transfer A90's device authority.
Use [Debian's arm64 bootstrap documentation](https://www.debian.org/releases/stable/arm64/apds03.en.html)
for base-system construction; its generic kernel/bootloader installation
steps are not the selected FYG8 boot path. No Debian release, rootfs artifact,
candidate, live budget or new persistent-write capability is selected yet.

## Completed history

The complete previous 798-line goal, including P396 live closure, P397 H0
preparation and all earlier archive links, is preserved byte-for-byte in
[the goal through P397 H0](docs/archive/roadmaps/GOAL_THROUGH_P397_H0_2026-09-15.md).
Historical state is evidence only; consumed claims and private journals retain
their identities and cannot be replayed.

## Continuing boundaries

Future device work requires its own current scope and exact target, artifact,
health, source and recovery binding. Never place an experiment over uncertain
health or repeat an uncertain write, transfer or control. Keep raw evidence and
identifiers private. A reporting failure permits evidence reconstruction, not
another device transition. Functional proof, recovery and terminal health remain
separate. The Debian direction selects preparation work only; filesystem
formatting, rootfs staging and runtime effects require their own reviewed
scope under the binding contracts.
