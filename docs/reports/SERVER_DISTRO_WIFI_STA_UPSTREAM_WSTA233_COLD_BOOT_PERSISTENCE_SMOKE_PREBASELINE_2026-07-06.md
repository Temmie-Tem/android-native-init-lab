# WSTA233 Cold-Boot Persistence Smoke Pre-Baseline

Date: 2026-07-06 KST
Scope: attended cold-boot persistence smoke measurement pre-baseline

## Verdict

PENDING.  WSTA233 started the chartered cold-boot persistence smoke measurement
and captured the pre-power-cycle baseline, but the required physical cold-boot
evidence did not occur during the observation window.  USB serial never
disappeared, so no cold-boot post-state comparison or v2321 rollback was run.

This is not a D-harden or server scaffold.  It is the first half of the single
chartered measurement.

Follow-up source work added the bounded WSTA233 measurement runner so the same
run can resume with post-cold-boot capture, persistence-gap classification, and
explicit v2321 rollback through the checked helper.

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
profile load, switch-root, or v2321 rollback.  Rollback is still required after
the actual post-cold-boot measurement completes.

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

## Next

Resume WSTA233 by physically power-cycling the device once, then capture the
same post-state baseline, classify the persistence gap, and roll boot back to
v2321 with `selftest fail=0`.

The supported resume command shape is:

```text
python3 workspace/public/src/scripts/server-distro/run_wsta233_cold_boot_persistence_smoke.py \
  --run-dir workspace/private/runs/server-distro/wsta233-cold-boot-persistence-runner-prebaseline-20260706T0021KST \
  --wait-serial-cold-boot

python3 workspace/public/src/scripts/server-distro/run_wsta233_cold_boot_persistence_smoke.py \
  --run-dir workspace/private/runs/server-distro/wsta233-cold-boot-persistence-runner-prebaseline-20260706T0021KST \
  --capture-post-classify
```

After post classification, run the explicit v2321 rollback gate:

```text
python3 workspace/public/src/scripts/server-distro/run_wsta233_cold_boot_persistence_smoke.py \
  --run-dir workspace/private/runs/server-distro/wsta233-cold-boot-persistence-runner-prebaseline-20260706T0021KST \
  --rollback-v2321 --ack-rollback-to-v2321
```
