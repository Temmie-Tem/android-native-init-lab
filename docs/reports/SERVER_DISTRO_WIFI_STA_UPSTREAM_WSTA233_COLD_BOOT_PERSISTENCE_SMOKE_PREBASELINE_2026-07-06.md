# WSTA233 Cold-Boot Persistence Smoke Pre-Baseline

Date: 2026-07-06 KST
Scope: attended cold-boot persistence smoke measurement pre-baseline

## Verdict

SUPERSEDED BY LIVE PASS.  The later attended run completed the cold-boot
measurement and rollback; see
`docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA233_COLD_BOOT_PERSISTENCE_SMOKE_LIVE_PASS_2026-07-06.md`.

PENDING.  WSTA233 started the chartered cold-boot persistence smoke measurement
and captured the pre-power-cycle baseline, but the required physical cold-boot
evidence did not occur during the observation window.  USB serial never
disappeared, so no cold-boot post-state comparison or v2321 rollback was run.

This is not a D-harden or server scaffold.  It is the first half of the single
chartered measurement.

Follow-up source work added the bounded WSTA233 measurement runner so the same
run can resume with post-cold-boot capture, persistence-gap classification, and
explicit v2321 rollback through the checked helper.

A second attended wait using that runner also timed out without USB serial
disconnect/reconnect evidence.  The device remained on the same native boot and
`selftest fail=0` after the timeout.

## Private Evidence

Pre-baseline run directory:

```text
workspace/private/runs/server-distro/wsta233-cold-boot-persistence-smoke-20260705T150908Z/
workspace/private/runs/server-distro/wsta233-cold-boot-persistence-runner-prebaseline-20260706T0021KST/
```

Key private files:

```text
wsta233_private_summary.json
pre-version.json
pre-selftest.json
pre-status.json
pre-runtime.json
pre-service-status.json
pre-netservice-status.json
pre-rshell-status.json
pre-port-tcpctl.json
pre-port-admin-ssh.json
pre-port-loopback-smoke.json
```

Recorded monitor event:

```text
operator_cold_boot_wait_aborted_no_disconnect
```

Runner representative decision:

```text
wsta233-cold-boot-persistence-prebaseline-pass
wsta233-blocked-cold-boot-disconnect-not-seen
```

Runner wait result:

```text
disconnect_seen=false
reconnect_seen=false
timeout=true
post_classify_not_run=true
rollback_v2321_not_run=true
post_timeout_selftest_fail_zero=true
post_timeout_uptime_continued=true
```

## Pre-Baseline Result

Redacted compact baseline:

```text
native_version=v3402-dpublic-hud-presenter-restart-policy
selftest_fail_zero=true
boot_ok=true
runtime_sd_writable=true
autohud_running=true
tcpctl_running=true
tcpctl_port_reachable=true
uptime_sec=4121.93
rshell_running=false
admin_ssh_port_reachable=false
loopback_smoke_port_reachable=false
```

Interpretation before cold boot:

- Native init was already healthy and serving the USB control plane.
- SD-backed runtime was mounted and writable.
- Native HUD/control services were up.
- Debian/admin-SSH and the smoke service were not running at baseline.  A post
  cold-boot measurement should therefore classify whether they remain absent and
  require manual re-bring-up, rather than claiming an auto-start regression.

## Safety

These runs performed read-only host/device observation and a passive USB serial
presence wait.

It did not perform boot flash, native reboot, Wi-Fi connect, DHCP, public tunnel,
public smoke, packet-filter mutation, rootfs mutation, userdata write, LSM
profile load, switch-root, or v2321 rollback.  At the time of this report,
rollback was still required after the actual post-cold-boot measurement.
That follow-up measurement and rollback later completed in the live-pass report.

No raw public URL values, tunnel credentials, Wi-Fi credentials, confirm tokens,
or route endpoints are included in this report.

## Validation

Static compile:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/server-distro/run_wsta233_cold_boot_persistence_smoke.py tests/test_server_distro_wsta233_cold_boot_persistence_smoke.py
```

Focused WSTA233 tests:

```text
PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest tests.test_server_distro_wsta233_cold_boot_persistence_smoke
```

Result: `7 tests OK`.

Full server-distro regression:

```text
PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest discover -s tests -p 'test_server_distro*.py'
```

Result: `857 tests OK`.

## Current Status

Superseded.  The later attended WSTA233 live-pass run captured the cold-boot
post-state, classified the persistence gap, and rolled boot back to v2321 with
`selftest fail=0`.  No resume action remains from this pre-baseline report.
