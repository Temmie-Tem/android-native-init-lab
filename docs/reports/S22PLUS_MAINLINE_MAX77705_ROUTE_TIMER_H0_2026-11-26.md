# S22+ MAX77705 route-timer: design and H0

Target: Galaxy S22+ `SM-S906N` / `g0q` / FYG8, Linux 7.2.11 mainline + Debian RAM PID1.
Nothing here grants device authority; the
[policy](../operations/S22PLUS_MAINLINE_MAX77705_ROUTE_TIMER_V1.md) and the
target contract govern any run.

This is the first unit of the
[hands-off cycle plan](../plans/S22PLUS_MAINLINE_USB_ROUTER_AND_HANDSOFF_CYCLE_2026-11-26.md).
It asks whether one boot can complete the whole cycle without physical
action. The cycle is Android, Download, one candidate, the routed USB
evidence exchange, an automatic Download, original Android and health.

## Why this composition

The plan's router v1 has attach epochs, which re-route after an unplug.
They matter only for replug tests, and those need an operator's hands
anyway. The no-touch cycle does not replug. So this unit reuses the
reviewed one-write Stage 2 producer unchanged, and puts the new work in
the composition and the host return. Attach epochs are the next router step.

The two parts were each reviewed and run on the device:

| Part | Device evidence |
|---|---|
| [Stage 2 route observer](../operations/S22PLUS_MAINLINE_MAX77705_ROUTE_V1.md) | [2026-11-26](S22PLUS_MAINLINE_MAX77705_ROUTE_RUN_2026-11-26.md): `ROUTE_CONFIGURED_WITHOUT_REPLUG`, no cue |
| [ML050 timed return](../operations/S22PLUS_MAINLINE_RAM_V1.md#ml050-timed-udc-return) | [2026-11-11](S22PLUS_MAINLINE_ML050_UDC_AUTO_RETURN_RUN_2026-11-11.md): new Download 590 s after N launch, cable untouched, original A, health |

The Stage 2 kernel Image and DT already contain the `nvmem-reboot-mode` node
with `mode-download = <0x15>`. They also contain the PMK8350 SDAM cell
(phandle `0x10c`, `reg <0x48 1>`, `bits <1 7>`) that the timer child checks.
No kernel or DT change was needed.

## Guest

[`max77705_route_timer_h0.py`](../../workspace/public/src/mainline/s22plus_canary_h0/max77705_route_timer_h0.py)
calls the unchanged Stage 2 staging, then:
- renames the wire identity. The board schema is
  `s22plus-fyg8-debian-max77705-route-timer-v1`, with its own domain and
  `G0QX` magics. The VM schema uses `G0QY`. The status and subject strings
  also differ. Every old string must disappear;
- inserts the ML050 arm, `recovery_begin()` and then the close of the IPC
  end, before `G0Q_RAM_PID1_BEGIN`. The arm therefore runs before
  `mx_begin()`, the first MAX77705 bus access, and before USB setup;
- includes `download-return.h` unconditionally, for `download_ready()`, and
  builds with `-DG0Q_AUTOMATIC_RECOVERY` and the `recovery.h` directory.

The producer header `max77705-usb-route.h` is byte-identical to the
reviewed one. No early commit (`recovery_commit`) is reachable.

## Host

New host code:
- **Binding module.** [`s22plus_mainline_max77705_route_timer_v1.py`](../../workspace/public/src/scripts/revalidation/s22plus_mainline_max77705_route_timer_v1.py)
  maps outcomes with no cue argument, because the board has no cue.
- **Profile.** It adds `max77705_route_timer_board()` and
  `timed_return() = timed_udc() or route-timer`. The session and
  automatic-recovery modules use `timed_return`. There are two return paths:
  - after the evidence exchange: `Coordinator.await_return()` calls
    `attempt()`;
  - after a stopped evidence step: `stopped()` calls `attempt()`.
- **Access.** It checks the review closure with `ordinary_cue=False` before
  importing candidate code. It refuses if a cue file exists, and it writes
  no attach closure.
- **Task.** The review closure binds the same shared imports as the cue
  scopes. It also binds the guest sources (`MXT_GUEST`). Recovery skips both
  the candidate module and the guest sources.

## Review history

Codex gpt-6.2-sol, read-only, reviewed the change.

**Round 1** confirmed several properties:
- wire separation across all four board and VM profiles;
- arm ordering, and a failed arm parks before the route observer and USB;
- no path from a route-timer task to a cue, the physical-return ready file,
  or a second automatic owner;
- original-A recovery works with the binding module absent.

It raised five blocking findings, each now addressed:
1. **Common-contract authority.** The ML050 timer exception is delegated in
   the common contract to the exact ML050 observer. A narrow paragraph now
   delegates the same slot and return to the exact route-timer observer.
   `AGENTS.md` pins the new details digest, and the live task check requires
   the delegation. Amending the common contract is the operator's decision.
2. **Guest composition binding.** The review now pins the guest sources. The
   binding module requires the qualified build manifest to contain exactly
   those bytes, the qualification's generators to match, and the
   qualification's recorded compile flags to equal
   `('-DCANARY_DEBIAN_RAM', '-DG0Q_AUTOMATIC_RECOVERY')`.
3. **Closure size.** The automatic wait produces more than the 2 MiB single
   raw index, as it did in ML041 and ML050. The policy selects the reviewed
   paged finalizer.
4. **No-touch claim.** The terminal reports `automatic_original_a_dispatched`
   only when the sole A launch is the automatic owner's. The policy also
   requires the operator's post-run statement.
5. **Host reboot before close.** Sealed arrival facts are rederived against
   the recorded host epoch. Live dispatch still checks the current boot.

**Round 2** confirmed the common-contract delegation, the board
qualification, the paged closure and the historical epoch. Two blocking
findings remained:
- **Gateway pins.** The gateway receipt pinned the guest build files, so a
  missing staging file would have blocked original-A recovery tools. The
  gateway now omits them. The task review still pins them, and recovery
  skips them.
- **Deadline equality.** Deadline equality alone could not distinguish an
  attended A whose bound happened to match. The adapter now records the
  automatic window receipt in the A launch, and only on the automatic
  owner's dispatch. The terminal requires that receipt.

**Round 3** checked those fixes with simulated missing guest files and with
attended, mismatched and out-of-window launches. It returned
`ROUTE_TIMER_PASS_GO` with no blocking findings. Codex session:
`01a214c1-ece7-74d2-9c17-565eb6bc8532`.

## H0 evidence

All of this ran on the host with no device actions.

- **VM, real 7.2.11 Image and Debian RAM archive** (QEMU 10.2.1, TCG, QMP
  shutdown reasons):
  - `ok`: authenticated with the timer domain, then `guest-shutdown` from
    the fixture;
  - `bad-key`: refused, park, no bytes;
  - `timer`: the response was authenticated, the fixture never powered off,
    and QMP reported `SHUTDOWN reason=guest-reset` 555.5 s after QEMU
    started.
- **Board artifact.** AP
  `2e58bfc741cf84b24521afcd7ef9d9f0b9285831345c87566e486627d16a0c74`;
  qualification `55bbeedf…806f`; decoder `e3974368…ae36`.
  - The Stage 2 Image and DT are unchanged. The loader-handed DT differs
    from both the Stage 1 and Stage 2 candidates only in
    `/chosen linux,initrd-end`.
  - The observer was rebuilt from regenerated sources and is byte-identical
    to the shipped member.
  - The producer header equals the reviewed bytes.
  - Six producer-record verdicts verified. Twelve rejections hold, including
    a frame with the Stage 2 response magic.
- **Binding.** Three producer records map through the module. Nine
  substitutions are rejected: AP, member, key, run ID, decoder, expected FDT,
  qualification, and the Stage 1 and Stage 2 schemas. A one-byte drift in
  any of the nine guest files is rejected.
- **Suites:** cue review closure, ordinary-cue cutover, route session,
  route-timer session (21 tests), route H0, SCM session, approved terminal,
  UDC timer return, attach cue, cue dialog, loader comparison, native
  session v3 and mainline live v1.

The private build and check directories are:
- `workspace/private/analysis/s22plus-max77705-route-timer-board.An2JnFfT`;
- `workspace/private/analysis/s22plus-max77705-route-timer-vm.krmIyLyV`.

## What a run would and would not show

A no-touch result shows that this one boot completed the cycle with no
physical action. It does not show the following:
- which caller reset the device;
- recovery from a hang before the child is armed;
- that every boot starts with the switch open.

It is one input to the plan's evidence ladder, not the activation of
Conditional Autonomous F1.

## Repeat builds for normal runs (v62)

The first run consumed AP `2e58bfc7`. The candidate registry admits each AP
once, so two more normal runs need two more board builds. Each build used the
same script with the staging read from main, where it is byte-identical to the
reviewed copy. Each has its own run ID and key.

| Build | Qualification | AP | Candidate |
|---|---|---|---|
| r1 (consumed) | `55bbeedf…806f` | `2e58bfc7…` | `f4df8483…` |
| r2 | `c42725e1…ec5b` | `ab4c68d5…` | `d84b517b…` |
| r3 | `9a19b32b…580f` | `5582ed47…` | `ca344384…` |

Each build passed the same checks as r1:
- loader qualification, the EL1/EL2/EL3 entry VM, and two identical packages;
- the rebuilt observer is byte-identical to the shipped member;
- the decoder is unchanged (`e3974368…`);
- six producer verdicts verified and twelve rejections held;
- the loader DT differs from the Stage 2 candidate only in
  `/chosen linux,initrd-end`;
- three outcomes mapped through the binding module, nine substitutions
  were rejected, and drift in any of the nine guest files was rejected.

The binding module now lists the three qualifications. That list is its only
behavioural change, and the v62 review set reflects it.
Private directories:
- `workspace/private/analysis/s22plus-max77705-route-timer-board-r2.lp9NKeVS`
- `workspace/private/analysis/s22plus-max77705-route-timer-board-r3.sYLUMaKz`

## Further repeat builds (v64)

Normal runs 1 to 3 consumed r1 to r3. The v64 set adds two more builds: one
for the run that verifies the readiness settle window and one spare. They used
the same build, check and binding scripts as r2 and r3.

| Build | Qualification | AP | Candidate |
|---|---|---|---|
| r4 | `821c15fa…7f9f` | `a9686f8a…` | `c8db88ae…` |
| r5 | `34763bed…a044` | `217842b2…` | `ac4f5b6b…` |

Each passed loader qualification, the entry VM, packaging and the package
check: six producer verdicts verified and twelve rejections held. The loader
DT differs from the Stage 2 candidate only in `/chosen linux,initrd-end`.
Against the v64 binding module, each mapped the three outcomes, rejected the
nine substitutions and rejected drift in each of the nine guest files.
Private directories:
- `workspace/private/analysis/s22plus-max77705-route-timer-board-r4.EXmhpaXg`
- `workspace/private/analysis/s22plus-max77705-route-timer-board-r5.INV6v1tS`
