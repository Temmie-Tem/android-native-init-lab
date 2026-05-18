# Native Init V261 PID1 Orphan Reaper Plan

## Summary

- Cycle label: `v261`
- Native build target: `A90 Linux init 0.9.60 (v261)`
- Goal: add a PID1-level orphan/zombie reaper so adopted child zombies are collected even when they are not tracked in the service registry.
- Trigger: V260 found `5900 Zs [cnss-daemon]` under `PPid: 1` even though `pidof cnss-daemon` returned rc=1.

## Problem

Current v159 has service-specific reaping:

- `a90_service_reap_all()`
- `a90_service_reap(service)`
- tracked PID cleanup through `a90_run_*`

This misses children that become orphaned and are reparented to PID1 after an external helper exits or is interrupted. Once such a process exits, it remains a zombie until PID1 calls `waitpid()` for it.

## Scope

Implement a minimal generic reaper:

- Add `a90_reaper.c/h`.
- Use `waitpid(-1, &status, WNOHANG)` in a bounded loop.
- Track summary counters:
  - total reaped
  - last pid
  - last status
  - last reap timestamp
  - last poll count
- Call the reaper in safe PID1 locations:
  - before each shell prompt
  - after each command dispatch
  - inside service-list/status paths via `a90_service_reap_all()`
- Add shell command:
  - `reaper`
  - `reaper status`
  - `reaper run`
  - `reaper verbose`
- Add `pid1guard` coverage for reaper availability/summary.

## Non-Goals

- Do not run another live CNSS retry in v261 implementation.
- Do not start `cnss-daemon`.
- Do not scan/connect/link-up Wi-Fi.
- Do not change QRTR/QMI probing yet.
- Do not reboot/flash without a separate explicit validation step.

## Implementation

- Copy `init_v159.c` and `v159/` include tree to `init_v261.c` and `v261/`.
- Bump `a90_config.h` to:
  - `INIT_VERSION "0.9.60"`
  - `INIT_BUILD "v261"`
- Add changelog entry:
  - `0.9.60 v261 PID1 ORPHAN REAPER`
- Add `a90_reaper.c/h` to the native init build.
- Add `a90_reaper_reap_orphans()` calls:
  - `a90_service_reap_all()`
  - `shell_loop()` before prompt and after command handling
- Add `cmd_reaper()` and command table entry in `v261/80_shell_dispatch.inc.c`.

## Validation

Static/local:

```text
aarch64-linux-gnu-gcc -static -Os -Wall -Wextra -o stage3/linux_init/init_v261 ...
strings stage3/linux_init/init_v261 | rg 'A90 Linux init 0.9.60 \\(v261\\)|A90v261|0.9.60 v261 PID1 ORPHAN REAPER'
git diff --check
python3 -m py_compile scripts/revalidation/a90ctl.py scripts/revalidation/native_init_flash.py scripts/revalidation/wifi_cnss_zombie_audit.py
```

Boot image:

```text
stage3/ramdisk_v261.cpio
stage3/boot_linux_v261.img
```

Real-device validation after explicit flash approval:

```text
python3 scripts/revalidation/native_init_flash.py stage3/boot_linux_v261.img --from-native --expect-version "A90 Linux init 0.9.60 (v261)" --verify-protocol auto
python3 scripts/revalidation/a90ctl.py version
python3 scripts/revalidation/a90ctl.py status
python3 scripts/revalidation/a90ctl.py pid1guard verbose
python3 scripts/revalidation/a90ctl.py reaper verbose
python3 scripts/revalidation/wifi_cnss_zombie_audit.py --out-dir tmp/wifi/v261-cnss-zombie-audit-after-flash
```

Regression:

```text
python3 scripts/revalidation/a90ctl.py selftest verbose
python3 scripts/revalidation/a90ctl.py service list
python3 scripts/revalidation/a90ctl.py storage
python3 scripts/revalidation/a90ctl.py mountsd status
python3 scripts/revalidation/a90ctl.py statushud
python3 scripts/revalidation/a90ctl.py autohud 2
python3 scripts/revalidation/a90ctl.py hide
```

Optional reaper exercise after flash:

```text
python3 scripts/revalidation/a90ctl.py run /cache/bin/toybox sh -c '(/cache/bin/toybox sleep 1 &) ; exit 0'
python3 scripts/revalidation/a90ctl.py reaper run
python3 scripts/revalidation/a90ctl.py reaper verbose
```

## Acceptance

- Local build and boot image generation succeed.
- New binary reports `A90 Linux init 0.9.60 (v261)`.
- `reaper` command is present and returns framed rc=0.
- After real-device flash, the old `cnss-daemon` zombie is gone.
- Future live Wi-Fi gates can require process-table cleanliness, not only `pidof` absence.

## Execution Note

- The implementation phase itself did not execute CNSS.
- After v261 flash and clean-state audit passed, the operator explicitly approved one bounded live retry.
- That retry passed with `start-only-pass`, `reaped=1`, `postflight_safe=1`, and postflight CNSS process clean.
