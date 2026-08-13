# A90 native Wi-Fi sidecar `/proc` root-exposure host incident

Date: 2026-08-13
Target: operator-owned Samsung Galaxy A90 5G only
Tier: H0 static analysis
Device or live effect: none
Disposition: design blocker; no successor candidate allocated

## Summary

The proposed headless handoff cannot safely inherit H24's persistent native
Wi-Fi companion unchanged. H24 starts the Wi-Fi helper and Android companion
processes before `switch_root`, keeps them in the original PID namespace, and
uses a private **mount** namespace only. The handoff then moves `/proc` into
Debian. A privileged Debian process can therefore potentially address a
surviving companion through `/proc/<pid>/root`, `/proc/<pid>/fd`, or
`/proc/<pid>/ns/mnt` and recover capabilities into that process's retained old
Android root and mount graph.

This is the same class of capability leak that invalidated designs which left
an old root reachable through a surviving HUD process. A private mount
namespace does not hide a process from a shared PID namespace. It can make the
retained mount graph more persistent while `/proc` still exposes the process.

No device observation is claimed here. The finding is a fail-closed static
design result: the current sources do not prove the required non-exposure, so
the next headless design may not claim it.

## Public source basis

- The installed H24 manifest compiles
  `A90_WIFI_PERSISTENT_HANDOFF_V1=1` and
  `A90_WIFI_AUTOCONNECT_PRIVATE_MOUNT_NS=1`.
- The automatic direct path starts the persistent Wi-Fi helper and native
  autoconnect before calling `a90_auto_handoff_run_once()`.
- The helper's persistent loop intentionally keeps required companion children
  and the modem holder alive. Its isolation primitive is `CLONE_NEWNS`; the
  reviewed path contains no new PID namespace boundary.
- The UFS handoff calls `d3_move_core_mounts(true, ...)`, which moves `/proc`
  and `/sys` into the Debian root before `switch_root`.
- The existing H24 observer proves the intended HUD private root and Debian
  `/dev` shape, but it does not prove that every surviving Wi-Fi or Android
  companion has no old-root, file-descriptor, or mount-namespace capability
  reachable from Debian.

These facts are sufficient to reject the exposure claim. They do not prove
that an exploit occurred, that H24's consumed D1 reached this point, or that
the device currently exposes anything. H24 stopped earlier at the HUD stage.

## Scope and consequences

- H24 remains the exact installed native resident and its consumed D1 remains
  terminal native `RESIDENT_HEALTHY` after clean fallback.
- H24 D1 did not reach Wi-Fi bind, core-mount move, or `switch_root`; no new
  live incident is inferred.
- The discarded uncommitted headless prototype created no manifest authority,
  qualification, approval, artifact, transfer, reboot, or device effect.
- No H26 identity, version, enable/latch namespace, artifact, or evidence is
  reserved by this report.
- H25 remains `NO_GO_RETIRED`; its identity and evidence remain unusable.

## Selected decision gate

The atomic ownership diagnostic is now `NO_GO_RETIRED`. Independent review
showed that reproducing H24's service set safely required a new Binder/AF_UNIX/
process-broker runtime and still conflicted with its distinct post-fork Android
UID/GID/capability identities. It never gained identity or live authority.

The selected H0 direction is
`docs/plans/A90_HEADLESS_NATIVE_WIFI_ISOLATED_DEBIAN_DESIGN_2026-08-14.md`.
Native PID 1 retains Wi-Fi and supervises Debian in separate PID, mount, and
network namespaces. Debian receives only a veth/IP boundary, fresh procfs,
minimal `/dev`, and read-only UFS; native processes, old root, AF_UNIX/Binder/
property state, `wlan0`, and device control are not nameable from Debian.

Kernel/toolchain support, veth/netfilter policy, pivot-root cleanup, capability
drops, SD-free evidence, crash-prefix no-replay, and performance must pass an
independent review before any fresh identity. Shared proc/network namespaces,
`hidepid`, `chroot`, path-name checks, or a userspace proxy are not fallbacks.

## Subsequent host-only correction

The attempted follow-up that reused H24's installed `cat` and `run` surface is
also retired before qualification or live contact. Static inspection proved
two independent defects:

1. H24 PID 1 invokes its generic command-boundary orphan reaper after every
   shell command. A `run`-based inventory could therefore reap unrelated PID-1
   children and is a device mutation, not connected read-only D0.
2. Inventory and `SIGTERM` were different command frames. A helper could fork,
   exec, reparent, change process group/session, or change mount namespace in
   the gap. A host journal makes replay conservative but cannot make that
   device-side capability set atomic.

The unqualified W0 runner and tests were removed. There was no connected read,
approval, device intent, signal, terminal, reboot, recovery, or evidence to
resume. H24 remains the healthy installed resident and is not modified for this
experiment.

The later atomic design closed several additional theoretical races but was
retired when its own exact H24 source dependency proved the design
disproportionate and internally incompatible. Its detailed document is kept as
negative design evidence only. No diagnostic command, journal, or recovery
state exists to reconcile.

## Retirement evidence

This blocker retires only after one of these independently reviewed closures:

- `DEBIAN_OWNS_WIFI_ZERO_NATIVE_SIDECARS`: all native Wi-Fi/Android companion
  processes are stopped and reaped before handoff, Debian brings up and keeps
  final Wi-Fi from boot-private non-SD input, and the same run proves no foreign
  root, fd, or mount-namespace capability in Debian `/proc`; or
- `NESTED_PID_NAMESPACE_ISOLATION`: Debian runs as PID 1 in a fresh nested PID
  namespace with a freshly mounted matching procfs, the native supervisor and
  all sidecars are absent from Debian `/proc`, and rollback, cleanup, no-replay,
  and terminal-health semantics are independently requalified.

The atomic attempt made the first closure disproportionate. The selected path
is the second closure extended with a separate Debian network namespace and
veth boundary; it still requires fresh independent implementation and live
proof.

## Contact and authority statement

This report was produced from public A90 source and documentation only.
Device, `/dev`, USB, network, `workspace/private`, S22+, S20+, payload,
partition, reboot, and live-command contacts are zero. It grants no D0, D1,
F1, candidate, flash, handoff, SD-removal, or device authority.
