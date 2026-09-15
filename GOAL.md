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

## Current bounded unit — cleanup closed after read-only reconciliation

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
`ANDROID_CLOSED_HEALTHY`; no effect replay or additional cleanup is permitted.
Host logs show target-port USB re-enumeration, but its initiating cause remains
unproved. Resolve the applicable session stop before any prospective device
effect. The operator reported Android state.

Final available space was 31,645,573,120 bytes, 55,156,736 below the pre-cleanup
observation; no reclaimed-space gain is proved. Four earlier no-effect
preparations and all consumed G2/cleanup records remain unchanged. The fixes
have independent review and 22 passing focused tests. See the
[live report](docs/reports/S22PLUS_ANDROID32_LIVE_2026-09-16.md) for evidence,
capacity measurements and separate removal/final-health outcomes.

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
