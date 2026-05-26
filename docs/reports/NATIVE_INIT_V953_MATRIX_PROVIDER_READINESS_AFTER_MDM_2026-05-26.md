# V953 Matrix Provider-Readiness After-MDM Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| live wrapper | `scripts/revalidation/native_wifi_matrix_provider_after_mdm_capture_v953.py` | `py_compile pass` |
| bounded live capture | `tmp/wifi/v953-matrix-provider-readiness-after-mdm-live/manifest.json` | `v953-wlfw-precondition-missing-no-open` |

V953 ran helper `v158` with `service_manager_order=after-mdm-helper-esoc-fd`.
The run preserved `pm-service` until the service-manager phase, then still
failed closed before any `/dev/subsys_esoc0` open.

## Provider Finding

| Phase | svc | hwsvc | vndsvc | pm-service | pm vndbinder | pm-proxy | pm-proxy-helper |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `after_per_mgr_settle` | `0` | `0` | `0` | `1` | `1` | `0` | `0` |
| `after_mdm_helper_spawn` | `0` | `0` | `0` | `1` | `1` | `0` | `0` |
| `after_service_manager_start` | `1` | `1` | `1` | `0` | `0` | `0` | `0` |
| `after_cnss_daemon_start` | `1` | `1` | `1` | `0` | `0` | `0` | `0` |
| `final` | `1` | `1` | `1` | `0` | `-1` | `0` | `0` |

Interpretation: `pm-service` is healthy before service-manager start but loses
the observed provider surface after the service-manager phase. WLFW still does
not appear.

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
python3 -m py_compile scripts/revalidation/native_wifi_matrix_provider_after_mdm_capture_v953.py
python3 scripts/revalidation/native_wifi_matrix_provider_after_mdm_capture_v953.py plan
python3 scripts/revalidation/native_wifi_matrix_provider_after_mdm_capture_v953.py \
  --allow-mountsystem-ro \
  --allow-selinuxfs-mount \
  --allow-mdm-helper-cnss-service-manager-matrix \
  --allow-cleanup-reboot \
  --assume-yes \
  run
```

## Next

Classify whether a bounded `pm-proxy` comparator is justified.
