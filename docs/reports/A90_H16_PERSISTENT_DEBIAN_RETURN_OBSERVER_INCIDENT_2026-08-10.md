# A90 H16 persistent Debian return and observer incident

Date: 2026-08-10
Target: operator-owned Samsung Galaxy A90 5G only
Run: `a90-h16-ufs-f1-20260810-03/h16-d1/run01`

## Classification

`PERSISTENT_DEBIAN_RETURN_AND_OBSERVER_BINDING_MISMATCH`

This is a host contract and observer-profile incident, not a boot-write,
userdata-write, or recovery failure. The consumed D1 ordinal is never replayed.

## Facts

- The journal durably records one combined arm-plus-reboot dispatch and a
  released candidate-return host guard.
- The same-intent native log reaches the H16 read-only UFS handoff sequence and
  `switch_root_exec`.
- The exact A90 later exposed its Debian NCM endpoint and SSH port, but the
  manifest observer key was rejected by the persistent appliance root.
- The installed appliance first-boot contract intentionally disables automatic
  reboot. The original D1 runner's 300-second automatic-return assumption was
  therefore inapplicable.
- The operator used the available physical path to return to native. Fresh
  read-only checks then proved exact H16 `0.11.184`, self-test `11/1/0`, state
  `binding=1 enable=1 latch=1`, and no userdata mount.
- Current same-intent on-device PID1/DRM/Dropbear evidence is absent. The black
  display observed while Debian networking was live is not enough to diagnose
  DRM ownership.

## Judgment

The run proves that native reached the H16 UFS `switch_root` boundary. It does
not prove automatic native return, authenticated SSH, Debian PID 1, DRM master,
visible display ownership, final Wi-Fi readiness, or full personal-server
readiness. Exact resident health after the operator's physical return is a
safe terminal health fact, not a substitute for those missing observations.

## Closure

An incident-specific no-replay finalizer may append only the original H16 D1
journal's `0004-final-health.json` and `0005-closed.json`. It is bound to the
exact private manifest, install result, four-record journal prefix, predecessor
execution closure, current H16 resident identity, released guard, same-intent
handoff log, and an unmounted-userdata receipt. It performs no arm, reboot,
handoff, mount, payload transfer, partition write, flash, or userdata write.

A later server-readiness candidate must bind an observer key that the existing
root can consume without mutating the UFS appliance during qualification, and
must separately establish the intended persistent-return policy and direct
DRM/display observation. This incident invalidates reuse of the earlier H16
capability review for that future execution machinery.
