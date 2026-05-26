# V951 Matrix Provider-Readiness Before-CNSS Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| live wrapper | `scripts/revalidation/native_wifi_matrix_provider_readiness_capture_v951.py` | `py_compile pass` |
| bounded live capture | `tmp/wifi/v951-matrix-provider-readiness-before-cnss-live/manifest.json` | `v951-wlfw-precondition-missing-no-open` |

V951 ran helper `v158` with `service_manager_order=before-cnss`. The run stayed
fail-closed: service managers, `mdm_helper`, `cnss_diag`, and `cnss-daemon`
started, but WLFW did not appear and `/dev/subsys_esoc0` remained unopened.

## Provider Finding

| Phase | svc | hwsvc | vndsvc | pm-service | pm vndbinder | pm-proxy | pm-proxy-helper |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `after_service_manager_start` | `1` | `1` | `1` | `0` | `-1` | `0` | `0` |
| `after_per_mgr_settle` | `1` | `1` | `1` | `0` | `-1` | `0` | `0` |
| `after_mdm_helper_spawn` | `1` | `1` | `1` | `0` | `-1` | `0` | `0` |
| `after_cnss_daemon_start` | `1` | `1` | `1` | `0` | `-1` | `0` | `0` |
| `final` | `1` | `1` | `1` | `0` | `-1` | `0` | `0` |

Interpretation: starting service managers before `pm-service` does not preserve
an observable `pm-service` provider surface in this native matrix.

## Guardrails

- No `pm_proxy_helper`.
- No Wi-Fi HAL start.
- No scan/connect/link-up.
- No credentials, DHCP/routes, or external ping.
- No controller eSoC notify or boot-done.
- No `/dev/subsys_esoc0` open.

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_matrix_provider_readiness_capture_v951.py
python3 scripts/revalidation/native_wifi_matrix_provider_readiness_capture_v951.py plan
python3 scripts/revalidation/native_wifi_matrix_provider_readiness_capture_v951.py \
  --allow-mountsystem-ro \
  --allow-selinuxfs-mount \
  --allow-mdm-helper-cnss-service-manager-matrix \
  --allow-cleanup-reboot \
  --assume-yes \
  run
```

## Next

Classify against V947 and try `after-mdm-helper-esoc-fd` if selected.
