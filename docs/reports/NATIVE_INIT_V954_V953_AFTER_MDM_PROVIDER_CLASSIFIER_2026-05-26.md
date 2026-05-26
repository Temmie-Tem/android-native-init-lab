# V954 V953 After-MDM Provider Classifier Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| host-only classifier | `tmp/wifi/v954-v953-after-mdm-provider-classifier/manifest.json` | `v954-pm-proxy-matrix-comparator-selected` |

V954 classifies V953 as evidence that `pm-service` alone is insufficient once
the matrix service-manager phase starts. The next safe comparator is bounded
`pm-proxy`, not `pm_proxy_helper`.

## Findings

| Marker | Value |
| --- | --- |
| provider keys | `667` |
| pre-service-manager `pm-service` alive | `true` |
| post-service-manager trio present | `true` |
| post-service-manager `pm-service` degraded | `true` |
| before-CNSS `pm-service` absent | `true` |
| V856 `pm-proxy` precedent | `true` |
| WLFW missing | `true` |
| fail-closed safety | `true` |

## Next

Add a bounded matrix comparator that starts `/vendor/bin/pm-proxy` after
`per_mgr` is observable. Keep `pm_proxy_helper`, `/dev/subsys_esoc0`, Wi-Fi HAL,
scan/connect, credentials, DHCP/routes, and external ping blocked.

## Device Health

Post-run checks after V953/V954:

- `bootstatus`: `BOOT OK`, `selftest: fail=0`;
- `selftest`: `fail=0`;
- `netservice`: flag disabled, `ncm0=present`, `tcpctl=stopped`.
