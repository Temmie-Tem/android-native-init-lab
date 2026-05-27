# Native Init V1163 Late pm-proxy eSoC Live Report

Date: `2026-05-27`

## Result

- Decision: `v1163-pm-service-exited-before-late-per-proxy`
- Pass: `true`
- Live runner: `scripts/revalidation/native_wifi_late_per_proxy_esoc_live_v1163.py`
- Helper: `a90_android_execns_probe v216`
- Evidence: `tmp/wifi/v1163-late-per-proxy-esoc-live/manifest.json`
- Summary: `tmp/wifi/v1163-late-per-proxy-esoc-live/summary.md`

## Summary

V1163 executed the bounded late `pm-proxy` gate introduced in helper `v216`.
The gate did not reach late `pm-proxy` start because `pm-service` exited cleanly
before the post-PM `mdm_helper` `/dev/esoc-0` readiness window became positive.

This closes the immediate V1160 hypothesis as currently implemented:

```text
expected:
  upper PM/CNSS path
    -> mdm_helper /dev/esoc-0 positive
      -> late pm-proxy
        -> pm-service Binder thread opens /dev/subsys_esoc0

observed:
  upper holder + firmware mounts + QRTR RX
    -> pm_proxy_helper holds /dev/subsys_modem
      -> pm-service exits with rc=0 before mdm_helper observable window
        -> late pm-proxy gate stays closed
```

## Key Evidence

| key | value |
| --- | --- |
| `mss` | `OFFLINING -> ONLINE -> ONLINE` |
| `mdm3` | `OFFLINING -> OFFLINING -> OFFLINING` |
| `qrtr_rx_seen` | `true` |
| `qrtr_services` | `{"69": 0, "74": 0, "180": 0}` |
| `per_proxy_initial_start_executed` | `0` |
| `child.per_proxy.skip_reason` | `deferred-until-mdm-helper-esoc-fd` |
| `child.per_mgr.exit_code` | `0` |
| `mdm_helper_observable` | `0` |
| `late_per_proxy_gate_positive` | `0` |
| `late_per_proxy_started` | `0` |
| `wlan0` markers | `0` |
| `WLFW/service69` | `0` |

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_late_per_proxy_esoc_live_v1163.py
python3 scripts/revalidation/native_wifi_late_per_proxy_esoc_live_v1163.py plan
python3 scripts/revalidation/native_wifi_late_per_proxy_esoc_live_v1163.py \
  --allow-tracefs-mount \
  --allow-tracefs-write \
  --allow-vendor-mount \
  --allow-selinuxfs-mount \
  --allow-pm-service-trigger-observer \
  --allow-cnss-daemon-start \
  --assume-yes \
  run
```

Result:

```text
decision: v1163-pm-service-exited-before-late-per-proxy
pass: True
late_per_proxy_started: False
wifi_hal_start_executed: False
wifi_bringup_executed: False
external_ping_executed: False
```

Post-cleanup device health:

```text
A90 Linux init 0.9.68 (v724)
selftest: pass=11 warn=1 fail=0
netservice: enabled=no ncm0=absent tcpctl=stopped
```

## Safety

- Allowed live scope: tracefs/vendor/selinuxfs mounts, global modem holder,
  PM observer, CNSS daemon start, `mdm_helper` observer.
- Wi-Fi HAL, scan/connect/link-up, credential use, DHCP, route, external ping,
  partition writes, boot image writes, and flash were not executed.
- Cleanup reboot completed by health proof even though the reboot command
  naturally lost its END marker during restart.

## Next Gate

V1164 should classify why `pm-service` exits with rc `0` before `mdm_helper`
becomes observable in the v216 late gate.  The most direct next checks are:

1. Compare V1139-positive and V1163-negative helper output and environment.
2. Capture `pm-service` stdout/stderr and init/property/socket preconditions in
   the v216 order.
3. Verify whether the v216 order lost the provider-ready condition before CNSS
   and `mdm_helper`.
