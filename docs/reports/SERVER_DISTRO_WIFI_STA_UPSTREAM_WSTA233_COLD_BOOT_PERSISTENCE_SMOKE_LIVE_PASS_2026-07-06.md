# WSTA233 Cold-Boot Persistence Smoke Live Pass

Date: 2026-07-06 KST
Scope: attended cold-boot persistence smoke measurement and v2321 rollback

## Verdict

PASS.  WSTA233 completed the single chartered persistence-smoke measurement with
real cold-boot evidence, captured the post-boot service state, classified the
persistence gap, and rolled boot back to v2321 through the checked helper.

This is a measurement only.  It does not add a service supervisor, auto-start
policy, public tunnel, Wi-Fi connect, DHCP, or new D-harden lever.

## Private Evidence

Run directory:

```text
workspace/private/runs/server-distro/wsta233-attended-coldboot-20260706T004455KST/
```

Key files:

```text
wsta233_result.json
wsta233_private_summary.json
pre-*.json
post-*.json
rollback-final-*.json
rollback-v2321-checked-helper.json
```

Decision:

```text
wsta233-cold-boot-persistence-smoke-live-pass
```

## Cold-Boot Evidence

The runner observed both USB serial disappearance and stable reappearance:

```text
disconnect_seen=true
reconnect_seen=true
serial_disconnect_reconnect=true
uptime_drop=true
pre_uptime_sec=5525.80
post_uptime_sec=33.89
```

Event timing:

```text
pre_baseline_done=2026-07-05T15:44:59Z
serial_disconnect_seen=2026-07-05T15:46:11Z
serial_reconnect_stable=2026-07-05T15:46:32Z
post_baseline_done=2026-07-05T15:46:51Z
rollback_v2321_done=2026-07-05T15:48:14Z
```

## Persistence Classification

Classification result:

```text
native-pid1-and-usb-control-persisted-debian-admin-services-manual-rebringup-required
```

Pre and post compact state matched on the native control-plane items that the
charter asked to measure:

```text
native_version=v3402-dpublic-hud-presenter-restart-policy
selftest_fail_zero=true
boot_ok=true
runtime_sd_writable=true
autohud_running=true
tcpctl_running=true
tcpctl_port_reachable=true
```

Debian/admin services were not running before the cold boot and did not
auto-start after it:

```text
admin_ssh_was_running_pre=false
admin_ssh_auto_started=false
loopback_smoke_was_running_pre=false
loopback_smoke_auto_started=false
rshell_running=false
admin_ssh_port_reachable=false
loopback_smoke_port_reachable=false
```

Interpretation: native PID1, USB/NCM control, SD-backed runtime, HUD, and tcpctl
survive the cold-boot path.  Debian admin SSH and loopback smoke remain manual
re-bring-up/productization work, not a regression from the baseline captured for
this smoke.

## Rollback

The runner confirmed rollback preconditions and used the checked flash helper to
return boot to v2321.  The final compact state was:

```text
native_version=0.9.285 build=v2321-usb-clean-identity-rodata
selftest_fail_zero=true
boot_ok=true
runtime_sd_writable=true
autohud_running=true
tcpctl_running=true
tcpctl_port_reachable=true
uptime_sec=34.07
```

Additional explicit post-run health:

```text
version: 0.9.285 build=v2321-usb-clean-identity-rodata
status: selftest pass=11 warn=1 fail=0
selftest: pass=11 warn=1 fail=0
```

## Safety

Device action occurred only inside the recoverable envelope:

```text
boot_flash=true
checked_helper_used=true
native_reboot=false
wifi_connect=false
dhcp=false
public_tunnel=false
public_smoke=false
packet_filter_mutation=false
rootfs_mutation=false
userdata_touch=false
lsm_profile_load=false
switch_root=false
secret_values_logged=0
public_url_value_logged=false
```

No raw public URL values, tunnel credentials, Wi-Fi credentials, confirm tokens,
or route endpoints are included in this report.

## Validation

Live runner completed with return code `0`.

The final explicit bridge health checks passed after rollback:

```text
python3 workspace/public/src/scripts/revalidation/a90ctl.py version
python3 workspace/public/src/scripts/revalidation/a90ctl.py status
python3 workspace/public/src/scripts/revalidation/a90ctl.py selftest
```

## Next

WSTA233 is complete.  The remaining chartered close-out item is the
server-distro epic close report, then halt for the operator's next-target
charter.
