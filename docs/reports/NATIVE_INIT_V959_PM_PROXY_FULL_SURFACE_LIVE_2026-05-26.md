# V959 PM-Proxy Full-Surface Matrix Live Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| live wrapper | `scripts/revalidation/native_wifi_pm_proxy_full_surface_capture_v959.py` | `py_compile pass` |
| bounded full-surface capture | `tmp/wifi/v959-pm-proxy-full-surface-live/manifest.json` | `v959-wlfw-precondition-missing-no-open` |

V959 reran the V957 `pm-proxy` matrix order with `cnss_surface_mode=full` and
a shorter helper timeout. The run stayed fail-closed and captured the lower
surface needed to classify the remaining WLFW gap.

## Findings

- `surface_mode=full`
- `surface_poll_count=16`
- `pm_proxy_started=1`
- `mdm_helper_esoc0_fd_seen=1`
- `cnss_diag_started=1`
- `cnss_daemon_started=1`
- `wlfw_precondition_observed=0`
- `subsys_esoc0_open_attempted=0`
- `wifi_hal_start_executed=0`
- `external_ping=0`

Full-surface evidence shows:

- `cnss-daemon` reaches `cld80211` netlink;
- ICNSS/QCA6390 platform surfaces are readable;
- MHI device list remains empty;
- `wlan0` remains absent;
- WLFW/BDF markers remain absent.

## Guardrails

- No `pm_proxy_helper`.
- No `/dev/subsys_esoc0` open.
- No eSoC notify or boot-done.
- No Wi-Fi HAL start.
- No scan/connect/link-up.
- No credentials, DHCP/routes, or external ping.

## Device Health

Post-run checks:

- `bootstatus`: `BOOT OK`, `selftest: fail=0`
- `selftest`: `fail=0`
- `netservice`: flag disabled, `ncm0=present`, `tcpctl=stopped`

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_pm_proxy_full_surface_capture_v959.py
python3 scripts/revalidation/native_wifi_pm_proxy_full_surface_capture_v959.py plan
python3 scripts/revalidation/native_wifi_pm_proxy_full_surface_capture_v959.py \
  --helper-timeout-sec 8 \
  --toybox-timeout-sec 52 \
  --allow-mountsystem-ro \
  --allow-selinuxfs-mount \
  --allow-mdm-helper-cnss-service-manager-matrix \
  --allow-cleanup-reboot \
  --assume-yes \
  run
python3 scripts/revalidation/a90ctl.py bootstatus
python3 scripts/revalidation/a90ctl.py selftest
python3 scripts/revalidation/a90ctl.py netservice status
```

## Next

Classify whether the current WLFW-precondition gate is circular before any
subsystem-open or HAL/scan expansion.
