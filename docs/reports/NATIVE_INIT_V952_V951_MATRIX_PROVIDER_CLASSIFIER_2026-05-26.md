# V952 V951 Matrix Provider Classifier Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| host-only classifier | `tmp/wifi/v952-v951-matrix-provider-classifier/manifest.json` | `v952-after-mdm-helper-esoc-fd-provider-comparator-selected` |

V952 compares V951 against V947 and selects `after-mdm-helper-esoc-fd` as the
next safe matrix comparator.

## Findings

| Marker | Value |
| --- | --- |
| provider keys | `559` |
| service managers present | `true` |
| before-CNSS `pm-service` absent | `true` |
| before-CNSS `per_mgr` fd absent | `true` |
| V947 runtime `pm-service` alive | `true` |
| `mdm_helper` `/dev/esoc-0` seen | `true` |
| WLFW missing | `true` |
| fail-closed safety | `true` |

## Next

Run the same helper `v158` matrix with
`service_manager_order=after-mdm-helper-esoc-fd`, still blocking
`pm_proxy_helper`, `/dev/subsys_esoc0`, Wi-Fi HAL, scan/connect, credentials,
DHCP/routes, and external ping.
