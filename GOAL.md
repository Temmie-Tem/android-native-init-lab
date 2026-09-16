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

## Latest completed unit — Android32 layout and rooted return

P398 `v0.3.0-rc.2` completed the exact successor to P397's 128 GiB reservation.
Two fresh native installations/four healthy sessions and an actual original-GPT
read preceded one four-block apply. A physical restart proved the new extents;
one stock reset produced the expected reduced F2FS geometry. Original Magisk A
was installed once. Native storage remains unformatted.

Rooted Android checks before and after one ordinary reboot proved identical
complete GPT, `/data` statfs total 34,357,624,832 bytes, a different Android boot,
and numeric UID/GID 0 with exact original-A/supporting partition digests.
The feature is `RESERVED_ANDROID_REBOOT_VERIFIED` with
`PASS_CHANGED_BOOT_GPT_CAPACITY_AND_ROOT`; terminal is
`ANDROID_CLOSED_HEALTHY`, `recovered=false`.

The 7200-second/two-operation grant closed after 896.104 seconds with both
operations consumed and no F1 owner. There was no GPT restoration, restorative
reset, recovery transfer or repeated A. The prospective missing-su setup
exception was not needed. P397's consumed result and its distinct earlier
health-only recovery remain unchanged.

Device Care's photographed 64 GB total is a presentation observation. Actual
32 GiB GPT and filesystem geometry are proved; measured free space was about
31.82 decimal GB. The upstream Android sum-and-round capacity calculation is
consistent with the label, but the exact Samsung UI call path was not traced.
No arbitrary smaller partition size is qualified by this result.

See the [live result and canonical timeline](docs/reports/S22PLUS_ANDROID32_LIVE_2026-09-16.md),
[H0 preparation](docs/reports/S22PLUS_ANDROID32_AND_MINIMAL_ANDROID_H0_2026-09-16.md),
and [G2 policy](docs/operations/S22PLUS_NATIVE_GPT_RESERVATION_V1.md).
The preceding [P397 result](docs/reports/S22PLUS_NATIVE_GPT_128G_LIVE_2026-09-15.md)
is retained as the successor's original-layout provenance.

## Latest cleanup — closed after read-only reconciliation

The [fixed profile](docs/operations/S22PLUS_ANDROID_MINIMAL_V1.md) reused the
same-FYG8 Pass1 removals with 119 mandatory keep/debug exclusions. Of 41
installed candidates, 26 passed selection and were removed from user 0;
ten system/shared-UID and five customized/disabled states were excluded.
All 26 immediate post-states and the final snapshot confirm absence. The
installed system-package count is 439, not the historical 116 checkpoint.

One ordinary reboot completed, then USB disappeared during the first final
health sequence. The existing read-only reconciliation proved healthy original
A/root, unchanged home/input owners, full proposed GPT and 32 GiB capacity.
The final boot matches the briefly observed post-reboot boot; no extra reboot
was observed. The formal cleanup result remains `INCOMPLETE` with
`ANDROID_CLOSED_HEALTHY`; no effect replay or further work from that claim is permitted.
Host logs show target-port USB re-enumeration, but its initiating cause remains
unproved. The reviewed additional mode below subsequently qualified this exact
read-only stop for its prospective scope; the old verdict stayed unchanged.
The operator reported Android state.

Final available space was 31,645,573,120 bytes, 55,156,736 below the pre-cleanup
observation; no reclaimed-space gain is proved. Four earlier no-effect
preparations and all consumed G2/cleanup records remain unchanged. The fixes
have independent review and 22 passing focused tests. See the
[live report](docs/reports/S22PLUS_ANDROID32_LIVE_2026-09-16.md) for evidence,
capacity measurements and separate removal/final-health outcomes.

## Latest additional cleanup — 25 persistent removals, healthy Android

The operator explicitly requested additional cleanup. The reviewed
`additional-known` mode used only the four successful removal blocks in the
[same-FYG8 extra report](docs/reports/S22PLUS_SYSTEM_APP_EXTRA_DEBLOAT_2026-07-06.md):
38 historical resources, overlays and platform utilities. Existing keep,
APEX, system/shared-UID, persistent/default and customized-state exclusions
were retained. Fresh metadata selected 29 and excluded nine. All 29 uninstalls
and their immediate post-states succeeded, followed by one ordinary reboot.
Four navigation overlays reappeared; 25 newly selected packages remained absent.
The formal result is `INCOMPLETE / ANDROID_CLOSED_HEALTHY`, with no replay.

The complete final raw snapshot proves changed boot, exact original-A/root,
unchanged full GPT/capacity/home/input, and all 118 initially present system
keep packages. The safe-mode property was empty; this is a limited reported
signal. H0 publication reused this complete final evidence without another
device command or reconciliation session. The additional claim is closed; the original cleanup terminal remains unchanged.
The separately reviewed prospective user-app scope below is its only successor.

Smart Switch had reappeared before this run began. At that close, system packages
were 415 versus the original 465: 50 absent at that observation. This run itself went
440 -> 411 immediately -> 415 after reboot. Available space is 31,510,704,128
bytes, 34,955,264 above its own starting observation; no causal allocation
breakdown is proved. The 28 tests and independent source/terminal reviews passed.
See the [live report](docs/reports/S22PLUS_ANDROID32_LIVE_2026-09-16.md).
Native storage remains unformatted; no raw APK deletion or Debian staging occurred.

## Latest user-app cleanup — 11 persistent removals, healthy Android

The explicit YouTube/Play Store/Contacts/Clock request qualified the reviewed
`user-apps` successor. Fresh metadata selected 15 of the 16 installed declared
UI apps; Samsung Video was excluded for a declared shared UID. All 15 user-0
uninstalls and immediate absent post-states succeeded, followed by one ordinary
reboot. All 55 previously attempted names were excluded and no effect replayed.

A boot-completed read during final readiness returned ADB `error: closed`.
The sole 300-second read-only reconciliation proved healthy exact original-A
root, changed boot, unchanged full GPT/capacity/home/input, all 117 initially
present KEEP packages for this mode, and an empty safe-mode property. The USB
cause remains unproved. Four selected apps were present again: My Files,
Galaxy Store, Weather and Dictionary. The other 11, including all four apps
explicitly named by the operator, remained absent. The result remains
`INCOMPLETE / ANDROID_CLOSED_HEALTHY`, `reboot_verified=false`, with no replay
or effect replay. The old two terminals remain unchanged; only the separately
reviewed full-checkpoint successor below may follow this closed run.

At that close, the system-only package count was **404**, down from 415 at
that run's start and 465 before the three runs: **61 absent at that observation**. `/data` available space is
31,678,308,352 bytes, 185,667,584 above this run's starting observation; a causal
space breakdown is not proved. The 33 focused tests and independent source
review passed. The [live report](docs/reports/S22PLUS_ANDROID32_LIVE_2026-09-16.md)
records the incomplete cleanup separately from final Android health. The
191.4580078125 GiB native partition remains unformatted; Debian staging and
A90/S20+ effects were outside this run.

## Latest full checkpoint cleanup — 279 persistent removals, 127 apps

The complete user-0 APK census found 406 installed packages, including all 118
protected entries. One reviewed batch selected all 279 previously unattempted
packages outside effective KEEP; the nine restored prior attempts were excluded.
All 279 version-bound uninstalls and immediate absent post-states succeeded.
There were no refusals or retained-package outcomes. The pre-reboot total was
127: the protected 118 plus the nine prior residuals. One ordinary reboot ran.

The first final-health root read lost its ADB target after successful selector
and lane reads; its preceding properties response was truncated to the model
field and did not prove a complete post-reboot identity. The single 300-second read-only reconciliation
proved healthy exact original-A root, changed boot, unchanged full GPT/capacity,
HOME/IME and all 118 protected entries. Every one of the 279 new removals still
held after reboot. Final total is **127 installed user-0 APK apps**. This includes
Magisk manager and is not the earlier system-only census metric.

The only outside-KEEP residuals are Smart Switch, My Files, Galaxy Store,
Weather, Dictionary and four navigation overlays from earlier attempts.
They were not retried. The formal terminal remains
`INCOMPLETE / ANDROID_CLOSED_HEALTHY`, `reboot_verified=false`,
`checkpoint_reached=false`; its remaining-new-candidate list is empty.
The final read failure's initiating cause is unproved. All three earlier
terminals and all previous effect identities remain unchanged.

Available space is 31,675,633,664 bytes, 3,997,696 above this batch's initial
observation, without causal allocation accounting. Forty-three app tests,
four record tests, 12 boundary tests and independent source review passed.
The [live report](docs/reports/S22PLUS_ANDROID32_LIVE_2026-09-16.md) records the
full result and private evidence pins. This checkpoint claim is closed with
no descendant or replay. Native storage remains unformatted; A90/S20+ and
Debian staging were outside this run.

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

**Next unit: H0 design and compatibility preparation for full Debian handoff.**
Complete a concise kernel/init/device-manager compatibility matrix, select a
rootfs/init candidate supported by that evidence, classify the minimum native
boot dependencies by lifetime, and define the paired initramfs/rootfs handoff
and recovery behavior. Check the selected loader/basic commands on the host
where useful; cross-compilation or QEMU alone does not prove target-kernel
boot, device ownership or recovery. This unit creates no live grant or write.

Then qualify these bounded functional milestones in order:

1. **Dedicated filesystem:** ext4 is the first candidate. Check exact kernel
   features, formatter defaults and ARM64 behavior, then define one bounded
   format/mount/write experiment on the new native partition only. Prove a
   small synchronized file remains byte-identical after clean unmount and a
   fresh native boot, followed by verified rooted Android return.
2. **Matched rootfs and bootstrap:** prepare the selected minimal Debian root,
   device configuration and boot inputs together, then stage them only through
   a separately reviewed persistent-write capability. A diagnostic shell may
   check the ABI but does not replace the planned full handoff.
3. **Full init handoff:** prove Debian host PID 1 and root ownership, including
   bootstrap/helper cleanup and the post-handoff observation/recovery path.
4. **Headless Debian operation:** qualify Debian-owned networking, authenticated
   SSH, package management and the selected ordinary service in one run.
5. **Persistence and normal lifecycle:** qualify Debian restart, clean shutdown,
   fresh boot, retained data/configuration and separate Android return health.
6. **Later hardware/product features:** add Wi-Fi if not already qualified,
   display/input, audio or a desktop as Debian-managed capabilities after the
   headless base works. Their absence does not block the earlier milestones.

No Debian release, init binary, rootfs artifact, candidate, live budget or new
persistent-write capability is selected by this goal edit. Filesystem formatting,
rootfs staging, handoff and post-handoff recovery still require their exact
reviewed scopes under the binding contracts.

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
