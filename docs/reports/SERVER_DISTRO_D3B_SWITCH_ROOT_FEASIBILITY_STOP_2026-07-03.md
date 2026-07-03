# Server Distro Endgame - D3B Switch Root Feasibility Stop

- Date: 2026-07-03 KST / 2026-07-03 UTC
- Unit: D3B live checked `switch_root` feasibility gate.
- Decision: `server-distro-d3b-switch-root-feasibility-stop-design-contradiction`
- Device action: read-only/harmless command-surface checks only. No flash, no hot-reload, no mount,
  no `switch_root`, no format, no `userdata` touch.
- End state: resident stayed `v2321-usb-clean-identity-rodata`; no D3B live handoff was attempted.

## Context

D3A prepared the private sysvinit rootfs/image successfully. The next chartered D3B unit says:

- stage the D3 image to SD,
- stage a per-run temporary SSH key,
- invoke a checked handoff that verifies image SHA/path,
- prepare/move `/proc`, `/sys`, `/dev`,
- execute `switch_root <distro-root> /sbin/init`,
- observe `A90D3_MARKER` over SSH,
- let the mandatory auto-reboot return to v2321.

The same charter also says **NO flash**.

## Live Feasibility Evidence

Resident version:

```text
A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)
```

Resident command surface does **not** include hot reload:

```text
cmdv1 reload
[err] unknown command: reload
rc=-2 status=unknown
```

Running BusyBox `switch_root` through the existing `run` command cannot satisfy D3, because `run`
spawns a child process and BusyBox requires PID 1:

```text
cmdv1 run /bin/busybox switch_root
Usage: switch_root [-c CONSOLE_DEV] NEW_ROOT NEW_INIT [ARGS]
...
PID must be 1. NEW_ROOT must be a mountpoint.
rc=1 status=error
```

Therefore the current resident v2321 command surface cannot execute the D3 handoff:

- `run` is not PID1 and is rejected for `switch_root`.
- `reload INIT-RELOAD-EXECVE` is absent from v2321, so there is no no-flash path to inject a new PID1
  handoff command.
- Adding a native-init handoff command would require a new boot artifact and a checked flash, which
  contradicts the current D3B `NO flash` guardrail.

## Stop Decision

This is a design contradiction, not an implementation failure:

1. D3B needs PID1 to execute `switch_root`.
2. The resident PID1 lacks any command that can do that.
3. The charter forbids the only established way to add such a command to resident v2321: a checked
   boot flash to a D3-capable native-init.

Per the D-ladder rules, live D3B stops here instead of improvising an unsafe or non-D3 handoff.

## Recommended Next Charter

Pick one of these explicitly:

1. Amend D3B to allow one checked boot flash via `native_init_flash.py` to a D3-capable native-init
   candidate, with normal rollback gates and no `userdata` touch. This is the direct path to a real
   PID1 `switch_root` command.
2. Or first flash/recover to a hot-reload-capable resident, then hot-reload the D3 handoff command.
   This still requires one checked flash because current v2321 has no `reload` command.
3. Or downgrade the next live proof to a non-PID1 chroot/pivot experiment. That would not satisfy the
   current D3 DoD (`distro init = PID1`) and should be named as a separate lower rung.

Do not attempt D3B live under the current "NO flash + resident v2321" constraints.
