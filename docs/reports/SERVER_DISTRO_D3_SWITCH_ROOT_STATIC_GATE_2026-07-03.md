# Server Distro Endgame - D3 Switch Root Static Gate

- Date: 2026-07-03 KST / 2026-07-02 UTC
- Unit: D3 static design gate for `switch_root` / PID1 handoff.
- Design: `docs/plans/NATIVE_INIT_SERVER_DISTRO_ENDGAME_DESIGN_2026-06-30.md`
- Decision: `server-distro-d3-static-gate-blocked-design-decision-required`
- Device action: none for D3. No flash, no hot-reload, no `switch_root`, no mount, no format, no
  `userdata` touch.
- End state: the last live D2 post-run health left the resident device on
  `v2321-usb-clean-identity-rodata` with standalone `selftest pass=11 warn=1 fail=0`.

## Scope

After D1 and D2 passed, the next rung is D3:

> `switch_root`: distro init = PID 1; persistent vendor-glue daemons survive handoff.

This report records the required static gate before any PID1 handoff attempt. It intentionally does
not run a live `switch_root` probe.

## Static Findings

The current staged Debian rootfs is valid for D1/D2 chroot work, but it is not yet a D3 rootfs:

- No `/sbin/init`.
- No `/usr/sbin/init`.
- No `/lib/systemd/systemd`.
- No `/etc/inittab`.
- Installed init-related packages are helper utilities only:
  - `init-system-helpers`
  - `sysvinit-utils`
- `sysvinit-core`, `systemd-sysv`, `openrc`, and `runit` are not installed.

The design document explicitly deferred the init-system choice to the switch-root stage:

- Debian was chosen, but systemd-vs-sysvinit was deferred until A.2.
- It notes that systemd on the stock 4.14 kernel may be frictional and suggests sysvinit/OpenRC as
  mitigation if systemd fights the old kernel.

Therefore the current rootfs has no distro init that can honestly satisfy "distro init becomes PID1."

## Control-Path Issue

D3 is not just "call busybox switch_root." Once native-init PID1 is replaced:

- The native-init serial command protocol is no longer PID1.
- The D2 chroot proof shows dropbear can work over the native-init USB/NCM path, but D3 must decide
  whether observation/recovery comes from a pre-started chrooted dropbear that survives the handoff,
  a distro init service that starts dropbear after handoff, or another bounded marker/reboot path.
- Recovery must be explicit: the unit must return/reboot/roll back to v2321 with `selftest fail=0`.

Running `/bin/sh` or an ad-hoc script as PID1 would be a different proof than the design's
"distro init = PID1" milestone. It may be a useful lower rung, but it is not D3 as written.

## Stop Decision

This is a true design ambiguity, not a transient tool failure:

1. Pick the D3 init system for the Debian rootfs.
2. Pick the D3 observation/recovery control path after native-init PID1 is gone.
3. Only then build the bounded handoff unit.

Per `GOAL.md`, D0-D3 should proceed continuously unless there is a real design ambiguity. This is
that ambiguity, so the loop stops here instead of improvising a PID1 replacement.

## Recommended Next Charter

The lowest-risk next D3 charter is:

1. Host-only rootfs update: install `sysvinit-core` in the Debian image/tree and add an explicit D3
   marker service or rc script.
2. Preserve a control path: either keep a D2-style key-only dropbear reachable across the handoff or
   have sysvinit start dropbear early.
3. Add a checked native-init handoff helper or hot-reloadable PID1 wrapper that mounts the SD image
   and executes `switch_root` only after SHA/path checks.
4. Live proof: observe a Debian-side D3 marker over the chosen control path, then trigger a bounded
   reboot/recovery to resident v2321 and confirm `selftest fail=0`.

Do not attempt D3 live until those choices are explicit.
