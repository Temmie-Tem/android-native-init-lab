# Native Init V694 PeripheralManager vndservice Query Live Report

- date: `2026-05-24 KST`
- status: `live-pass`; Wi-Fi external ping is **not** complete
- helper: `a90_android_execns_probe v117`
- helper build: `tmp/wifi/v694-execns-helper-v117-build/a90_android_execns_probe`
- deploy evidence: `tmp/wifi/v694-execns-helper-v117-deploy-live-serial1850/`
- live evidence: `tmp/wifi/v694-peripheral-vndservice-query-orchestrated-live-rerun/`
- decision: `v694-peripheral-vndservice-registration-confirmed`

## Scope

V694 inserted a bounded `/vendor/bin/vndservice list` query into the proven
service `74` positive private namespace. The query ran after `pm-service` and
after `pm-proxy` so the result can distinguish provider registration from the
previous V692 registry observability gap.

The proof remained below Wi-Fi bring-up. It did not start Wi-Fi HAL,
`wificond`, supplicant, or hostapd; did not scan/connect/link-up; did not use
credentials, DHCP, routes, or external ping; did not write subsystem sysfs
nodes; and did not write boot partitions.

## Result

| key | value |
| --- | --- |
| decision | `v694-peripheral-vndservice-registration-confirmed` |
| pass | `True` |
| helper marker | `a90_android_execns_probe v117` |
| helper sha256 | `4739699b794a4129f0bb84b61ecbbaf726e53eeb51ea93ad0a0b0497b60eeb83` |
| current boot prep | pass |
| service `180/74` | pass |
| `vndservice` query ran | pass |
| exact provider match | pass |
| Wi-Fi HAL start | `False` |
| scan/connect | `False` |
| external ping | `False` |

## Query Evidence

| phase | exit | timeout | exact match | stdout bytes | stderr bytes |
| --- | ---: | ---: | ---: | ---: | ---: |
| `after_per_mgr_probe` | `0` | `0` | `1` | `2416` | `1457` |
| `after_per_proxy_probe` | `0` | `0` | `1` | `2422` | `1457` |

Both phases reported `vendor_qcom_peripheral_manager_seen=1`, so the previous
hypothesis that `pm-service` never registers `vendor.qcom.PeripheralManager` is
no longer the primary blocker.

## Runtime Markers

| marker | count |
| --- | ---: |
| QRTR RX | `1` |
| QRTR TX | `1` |
| `sysmon-qmi` | `4` |
| service-notifier aggregate | `2` |
| service `180` | `1` |
| service `74` | `1` |
| CNSS netlink | `5` |
| CNSS `cld80211` | `2` |
| WLFW start | `0` |
| BDF | `0` |
| `wlan0` | `0` |

The provider registration gap is closed, but WLFW/BDF/`wlan0` still did not
advance in this no-CNSS-retry query mode.

## Deployment Notes

The first NCM install attempt targeted a reachable `192.168.0.1` address, but
that address was not the A90 NCM endpoint for the deploy path. The remote
`netcat/dd` receiver was cancelled with `q`, `selftest` was rechecked, and final
helper deployment used serial appendfile with safe `1850` chunks.

## Validation

Executed:

```bash
bash scripts/revalidation/build_android_execns_probe_helper.sh tmp/wifi/v694-execns-helper-v117-build/a90_android_execns_probe
python3 -m py_compile scripts/revalidation/native_wifi_peripheral_vndservice_query_v694.py scripts/revalidation/native_wifi_peripheral_vndservice_query_orchestrator_v694.py scripts/revalidation/wifi_execns_helper_v117_deploy_preflight.py
python3 scripts/revalidation/wifi_execns_helper_v117_deploy_preflight.py --out-dir tmp/wifi/v694-execns-helper-v117-deploy-live-serial1850 --transfer-method serial --serial-chunk-size 1850 --approval-phrase "approve v694 deploy execns helper v117 only; no daemon start and no Wi-Fi bring-up" --apply --assume-yes run
python3 scripts/revalidation/native_wifi_peripheral_vndservice_query_orchestrator_v694.py --out-dir tmp/wifi/v694-peripheral-vndservice-query-orchestrated-live-rerun --apply --assume-yes run
git diff --check
```

## Next Gate

Plan V695 as a provider-confirmed CNSS retry tail:

- keep the V694 provider registration query gate;
- after exact provider registration, start only the fresh `cnss-daemon` retry
tail;
- keep Wi-Fi HAL, `wificond`, supplicant, scan/connect, DHCP, credentials,
routes, and external ping blocked;
- classify whether the remaining blocker is still Binder `-22`, `pm_qos`, WLFW
service `69`, BDF, or `wlan0` creation.
