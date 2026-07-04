# Server-Distro WSTA19 Native-Owned Chroot Wi-Fi Boundary

- Date: 2026-07-04
- Scope: native-owned Wi-Fi with Debian chroot consumer
- Native resident: `0.11.140 (v3384-server-distro-hardware-contract)`
- Public exposure: not started
- Final device state: native V3384, `selftest fail=0`

## Summary

WSTA18 showed that full `switch_root` loses the vendor WLAN control plane: Debian keeps
enough kernel objects to see `wlan0`/phy/rfkill, but WCNSS/WMI goes down and direct scans
return `Invalid argument`.

WSTA19 validates the low-risk ownership model instead.  Native PID1 stays alive and owns
the WLAN control plane; Debian runs as a chrooted service consumer over USB/NCM.  Live
result: after a fresh native reboot and the WSTA2 materialization preflight, native scan
passed before the chroot, SSH reached Debian inside the chroot, and native scan still
passed while the chrooted Debian `dropbear` was active.

Final decision:

```text
wsta19-native-owned-chroot-wifi-boundary-pass
```

## Source Changes

Added a no-flash WSTA19 runner:

- `workspace/public/src/scripts/server-distro/run_wsta19_native_owned_chroot_wifi.py`

The runner:

1. requires resident V3384;
2. runs a WSTA2-style `wifi softap iftype-probe` preflight if `wlan0` is not admin-up;
3. requires a native pre-chroot `wifi scan` with visible BSS;
4. SHA-checks and, if needed, re-stages the SD-backed Debian ext4 image;
5. loop-mounts the image and starts temporary key-only `dropbear` inside the chroot;
6. proves host SSH reaches Debian over USB/NCM;
7. runs native `wifi scan` again while the chroot/dropbear is active;
8. cleans up dropbear, shadow/key changes, mount, and loop node, then verifies final selftest.

Safety markers stay below association and public exposure:

```text
boot_flash=false
switch_root=false
userdata_touch=false
no_wifi_association=true
no_dhcp=true
no_ping=true
no_public_tunnel=true
temporary_key_only=true
```

Added focused tests:

- `tests/test_server_distro_wsta19_native_owned_chroot_wifi.py`

## Static Validation

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/run_wsta19_native_owned_chroot_wifi.py \
  tests/test_server_distro_wsta19_native_owned_chroot_wifi.py

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests/test_server_distro_wsta19_native_owned_chroot_wifi.py \
  tests/test_server_distro_wsta2_native_materialization.py \
  tests/test_server_distro_wsta15_handoff_scan_boundary.py

Ran 12 tests in 0.001s
OK
```

## Live Validation

Private pass run:

```text
workspace/private/runs/server-distro/wsta19-native-owned-chroot-wifi-retry-20260704T001922Z/wsta19_result.json
```

No boot flash ran.  A native reboot was used to clear the known stale `flags=0x1002` /
`SIOCSIFFLAGS EINVAL` WLAN state before the final pass.

Materialization preflight:

```text
before_wlan0_present=false
before_wlan0_admin_up=false
iftype_probe_requested=true
wlan0_wait_elapsed_ms=69042
link_up_rc=0
link_up_errno=0
decision=softap-iftype-probe-pass
after_wlan0_present=true
after_wlan0_admin_up=true
```

Native scan before the chroot:

```text
attempts_completed=1
decision=wifi-scan-pass
scan_result_count=9
```

SD image staging:

```text
remote_sha_before=4bc983c0ecb6e98470159866a94365719968ac6f6426aa45c5b58e68d859ee2d
remote_sha_after=210fc1f92d4eb8bf291fb5b362154a29ca2b579a22a0a41cb1aaa89b5b6cb0dc
```

The remote SHA mismatch is expected after prior rw chroot mounts changed the ext4 image.
The runner re-staged the pinned local image before mounting it.

Debian chroot SSH proof:

```text
A90D2_SSH_MARKER
debian_version=12.14
stage_marker=present
```

Native scan while Debian chroot/dropbear was active:

```text
attempts_completed=1
decision=wifi-scan-pass
scan_result_count=11
```

Cleanup and final health:

```text
shadow_restored=true
mount_cleanup_ok=true
loop_cleanup_ok=true
post_mount_absent=true
post_loop_node_absent=true
post_dropbear_absent=true
final_version=0.11.140 build=v3384-server-distro-hardware-contract
selftest: pass=12 warn=1 fail=0
```

The immediate cleanup marker still saw `dropbear_cleanup_absent=0`, but the bounded
postcheck two seconds later confirmed `post_dropbear_absent=1`; the runner's final
`cleanup_ok` uses the postcheck.

## Failed First Attempt

The first WSTA19 run used the same chroot/SSH/during-scan sequence but did not include
the WSTA2 materialization preflight.  It proved Debian SSH and cleanup, but native scan
was already blocked before the chroot:

```text
decision=wsta19-blocked-native-pre-scan
pre_scan decision=wifi-scan-link-up-failed
link_up_errno=22
```

Manual BusyBox/Toybox `ip link set wlan0 up` reproduced the same `SIOCSIFFLAGS: Invalid
argument`; a same-boot WSTA2 iftype-probe also failed at `softap-iftype-probe-link-up-failed`.
This matches earlier WSTA7/WSTA13 stale-state behavior: a fresh native reboot plus WSTA2
materialization is the reliable precondition.

## Interpretation

WSTA19 confirms the practical ownership answer to WSTA18:

- full `switch_root` makes direct Debian Wi-Fi ownership lose the WCNSS/WMI control plane;
- keeping native PID1 alive preserves native Wi-Fi scan capability while Debian runs as a chrooted service;
- the chroot path is viable for a Wi-Fi-enabled appliance service boundary below association;
- future native-owned designs should expose bounded scan/connect/status service APIs to Debian instead of
  making Debian own the raw WLAN driver immediately.

This does not make chroot a security boundary.  It is a control-plane preservation and bring-up
model.  A production server posture still needs the separate D-harden containment work before any
persistent public exposure.

## Hygiene

- No public tunnel was started.
- No association, DHCP, gateway ping, DNS, API POST, or cloudflared path ran.
- No Wi-Fi SSID, PSK, BSSID, DHCP lease, concrete private Wi-Fi address, gateway, DNS server,
  public URL, or generated hostname is recorded in this report.
- Raw transcripts, SSH keys, and the Debian image remain under `workspace/private/`.
- The device ended on native V3384 with `selftest: pass=12 warn=1 fail=0`.
