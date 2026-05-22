# Native Init V641 Firmware-Backed Boot-Window Disabled-Smoke Live Report

- date: `2026-05-23 KST`
- cycle: `v641`
- status: `disabled-smoke-pass`; Wi-Fi external ping is **not** complete
- evidence: `tmp/wifi/v641-disabled-smoke-20260523-063157/`
- committed prep: `ee578f1`

## Scope

This live gate flashed the V641 boot image with no one-shot arm flag present.
The purpose was only to prove that the firmware-backed sibling SSCTL proof is
disabled by default and that the device still reaches the native serial shell.

No proof action, sibling SSCTL write, service-manager start, Wi-Fi HAL start,
scan/connect/link-up, credential handling, DHCP, route change, or external ping
was executed.

## Flash Result

```text
local image marker: A90 Linux init 0.9.67 (v641)
local image sha256: f957e1db0a270f71af4273072a5ca61772cd738ab86954f48ce4f74861064e15
remote image sha256: f957e1db0a270f71af4273072a5ca61772cd738ab86954f48ce4f74861064e15
boot block prefix sha256: f957e1db0a270f71af4273072a5ca61772cd738ab86954f48ce4f74861064e15
cmdv1 verify: version/status rc=0 status=ok
```

## Runtime Evidence

`bootstatus`:

```text
boot: BOOT OK shell 4.2s
selftest: pass=11 warn=1 fail=0
pid1guard: pass=11 warn=1 fail=0
exposure: guard=ok warn=0 fail=0 ncm=absent tcpctl=stopped rshell=stopped boundary=usb-local
runtime: backend=sd root=/mnt/sdext/a90 fallback=no writable=yes
```

`timeline`:

```text
00 init-start rc=0 errno=0 A90 Linux init 0.9.67 (v641)
16 console rc=0 errno=0 serial console attached
17 autohud rc=0 errno=0 started refresh=2
18 shell rc=0 errno=0 interactive shell ready
```

Proof state:

```text
/cache/native-init-sibling-fwssctl-v641.log: No such file or directory
/cache/native-init-sibling-fwssctl-v641: No such file or directory
timeline wifi-v641-fwssctl marker: absent
V641/pm_qos dmesg marker query: exit 0 with no matching marker output
```

The generic boot dmesg still contains early baseline kernel warnings unrelated
to this proof. The V638-specific blocker marker `pm_qos_add_request()` did not
appear in the V641 disabled-smoke marker query.

## Decision

```text
decision: v641-disabled-smoke-pass
pass: True
reason: V641 boots to shell with no arm flag, no proof log, no proof flag, no wifi-v641-fwssctl timeline marker, and no pm_qos proof marker.
next: run the V641 one-shot armed proof once, then classify service 74/WLAN-PD/WLFW/BDF/wlan0 or warning/timeout outcome.
```

## Current Device State

The device is currently running `A90 Linux init 0.9.67 (v641)` in unarmed mode.
This is acceptable for the next gate because V641 is disabled by default and
the arm flag is absent.

## Next Gate

Proceed to V641 armed proof once:

1. create `/cache/native-init-sibling-fwssctl-v641` with content `run`;
2. reboot into the same V641 image;
3. capture proof log, timeline, bootstatus, dmesg markers, and mount state;
4. classify:
   - service `74`, WLAN-PD, WLFW/BDF, firmware-ready, or `wlan0` advancement;
   - any `pm_qos_add_request`, timeout, unreaped child, or mount failure;
5. rollback to v319 if warning/timeout/boot instability appears.
