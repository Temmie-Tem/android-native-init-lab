# S22+ foreground-goal research capability v1

This capability is executable only when its tracked review receipt says
`PASS_GO` and matches every declared source hash. A definition or goal alone
does not activate the runner. It specializes D0 and **attended** D1 only;
F1, unattended D1 and the dormant pre-F1 catalog are unchanged.

## Operator goal and authority

A direct operator request to pursue an S22+ research goal may authorize use of
the named profiles below where necessary for that goal. The foreground agent
records the operator's concrete objective, selected action subset and a private
exact-target binding from an existing D0 observation in `grant.json`. Opening a
grant is H0. It does not itself certify the target or permit unrelated work.
Do not invent a new goal, broaden its actions, or reopen a failed goal. Close
or stop using the grant when the objective completes, the operator cancels,
scope changes, or attendance required for an effect is unavailable. One review
is reused while its execution-critical inputs are unchanged; no per-read or
per-reboot confirmation is required inside the valid explicit goal scope.

`--attended` records attendance already established in the conversation. It
cannot manufacture presence. For every D1 effect the operator must remain able
to perform the existing physical recovery. Presence is unnecessary for D0.
Safe parking and automatic recovery are not claimed by this attended lane.

## Named scope

| Action | Tier | Fixed operation |
| --- | --- | --- |
| `identity` | D0 | root `id` and kernel release |
| `processes` | D0 | root PID, PPID, UID, state and process name census; no arguments/environment |
| `memory` | D0 | root `/proc/meminfo` and `/proc/vmstat` |
| `status-hud` | D0 | fixed bounded `/proc/meminfo`, two aggregate `/proc/stat` samples one second apart, and battery `type`, `capacity`, `status`, `temp` attributes |
| `mounts` | D0 | root `/proc/mounts` |
| `usb-state` | D0 | ordinary Android USB configuration/state property reads |
| `health` | D0 | existing exact rooted FYG8 boot/supporting hash and Android-health profile |
| `normal-reboot` | D1 | one selected-serial ordinary Android reboot, followed by bounded exact healthy return |

All profiles bind `SM-S906N/g0q/S906NKSS7FYG8`, the operator-owned private serial
and USB topology. They use the existing ADB client, private bounded raw captures
and target session lock. Initial and final identities must agree; D0 requires
the same boot. D1 requires the new healthy boot, exact original boot/supporting
hashes and Download absence. The read profiles are ordinary status interfaces;
this does not authorize arbitrary procfs/sysfs/debugfs/device-file reads.
Raw private output can contain identifiers and remains under `workspace/private`.

The status-HUD profile reads only `/sys/class/power_supply/battery/`'s four
named attributes, with bounded text prefixes and explicit unavailable markers.
It does not enumerate other supplies or read serials, uevent, charging controls,
thermal zones or GPU interfaces. Android availability does not establish native
boot availability. It loads no provider module and changes no charging setting.
CPU sampling sleep is observation spacing, not a reboot or mode transition.

No caller shell, root command text, device path, register, package, process kill,
service restart, module operation, security/configuration mutation, panic,
watchdog, dump, Download/Recovery, image or partition operation is accepted.
New action semantics require one scoped implementation/review; a different
research question using unchanged profiles does not require a new review.

## Effect and failure ownership

The existing shared S22+ target-session lock prevents concurrent F1/research
effects. Prospective Process-v2 F1 also publishes a durable exact-run owner
before Download intent. Named research D1 refuses a parked F1 owner, and F1
recovery requires the matching run/binding. Only validated CLOSED publication,
or a validated pre-effect abort with no Download intent or transfer start,
retires that owner. An interrupted owner publication remains blocking.
Activation review binds the existing P367 CLOSED/19 migration baseline and
confirms no current open authorized effect; historical claims are not counted
or rewritten. All future F1 runs must use the reviewed prospective owner path.
Existing consumed runs grant no new effects through owner absence. Each normal reboot records its fresh health and goal identity, then publishes
the shared pending record as the authoritative durable intent before its local
mirror and the single ADB dispatch. A fixed pending-intent record survives
host interruption and blocks new ordinary F1/research effects. The observer
waits at most 360 seconds for exact changed-boot health. Expected absent/offline
ADB enumeration during this requested reboot is observed within that window;
malformed/failed commands, unexpected identity or authorization state stop.
Once the exact serial/topology is online, a successful fixed nonroot
`getprop sys.boot_completed` read may return empty or `0` while booting; these
values wait within the same original deadline and one-second polling interval.
Only `1` enters the unchanged strict property and health checks. Any other
readiness value or failed raw capture stops; readiness alone proves no health.
Shell failures are not retried as ordinary boot settling.

Normal completion publishes the result before clearing the pending marker.
Failure closes the goal and retains intent/raw evidence. No candidate or reboot
is replayed. Read-only pending reconciliation may verify the exact changed
healthy boot and end recovery bookkeeping. It neither upgrades the failed
bounded action to PASS nor reopens the old goal. If that proof is unavailable,
the effect guard remains; required physical recovery must be separately handled
under its existing authority. Killing a host process is not device recovery.

This durable stop addresses uncertain D1 dispatch/completion and host cuts.
Its scope is the pending exact S22+ transaction, retirement is joined changed-
boot health or a separately reviewed recovery disposition, and review is
triggered by changes to action, target, observation or recovery semantics.

## Owner and usage

Owner: [s22plus_goal_research_v1.py](../../../workspace/public/src/scripts/revalidation/s22plus_goal_research_v1.py).
Review: [s22plus_goal_research_v1_review.json](../../../workspace/public/src/device-action/bindings/s22plus_goal_research_v1_review.json).

The foreground agent opens a grant with `--open-goal`, `--target-file` and
the necessary `--actions` subset, then uses `--grant` and `--action` for named
operations. Close the grant with `--grant … --close-goal` at completion or
cancellation; this never clears a pending effect. D1 additionally requires
`--attended`. `--reconcile` is a fixed
read-only health entry for an existing pending reboot; it never sends control.
Existing consumed manifests, journals and approvals are not modified or repinned.

Implementation qualification is host-only unless a separate connected run is
explicitly recorded. H0 fixtures do not prove unattended recovery or real
device behavior for every failure state.
