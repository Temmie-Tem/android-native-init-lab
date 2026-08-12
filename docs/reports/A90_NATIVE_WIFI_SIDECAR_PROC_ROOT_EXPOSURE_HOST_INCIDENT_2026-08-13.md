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

## Required decision gate

Before a final cable-free headless candidate exists, one separately qualified
no-payload Wi-Fi ownership test must answer whether native Wi-Fi companions can
be stopped and fully reaped while `wlan0` remains usable long enough for Debian
to take ownership.

If the result is positive, the production direction is:

1. native code performs the minimum vendor/firmware bring-up;
2. every native Wi-Fi helper and companion is stopped and proved gone;
3. a boot-private credential/config input is handed to Debian without SD;
4. Debian owns association, DHCP, DNS, and health;
5. `switch_root` proceeds only after the zero-sidecar proof is durable.

If the result is negative, the handoff must stop at H0. A nested PID-namespace
supervisor is then a separate architecture and hazard review; it is not an
implicit fallback and must not be added inside the existing critical path.
`hidepid`, a private mount namespace, `chroot`, path-name checks, or merely
dropping one file descriptor are not accepted substitutes for an exact
isolation proof.

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

The first closure is preferred because it removes runtime machinery instead of
adding a permanent supervisor.

## Contact and authority statement

This report was produced from public A90 source and documentation only.
Device, `/dev`, USB, network, `workspace/private`, S22+, S20+, payload,
partition, reboot, and live-command contacts are zero. It grants no D0, D1,
F1, candidate, flash, handoff, SD-removal, or device authority.
