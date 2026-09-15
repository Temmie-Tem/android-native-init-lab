# Goal: S22+ Debian on native storage

Build a usable Debian arm64 environment on dedicated native storage, following
the operator's A90-style direction. The actual current allocation is **32 GiB
Android userdata and 191.4580078125 GiB native storage**. Start from the FYG8
vendor kernel and native hardware bring-up, retaining observable native
control and bounded recovery while Debian execution is qualified.
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

## Debian direction and next storage unit

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
