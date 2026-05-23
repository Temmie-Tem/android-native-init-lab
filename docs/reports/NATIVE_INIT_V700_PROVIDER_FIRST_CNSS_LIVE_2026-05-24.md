# Native Init V700 Provider-first CNSS Live Report

- date: `2026-05-24 KST`
- status: `bounded-live-pass-with-finding`; Wi-Fi external ping is **not**
  complete
- helper marker: `a90_android_execns_probe v119`
- helper sha256:
  `53c7d74d9a7d4ec2cbbaf7dc98e37af9bb165a9ccaabc45616dc3c12949d794c`
- deploy evidence:
  `tmp/wifi/v700-execns-helper-v119-deploy-run-safe/`
- live evidence:
  `tmp/wifi/v700-provider-first-cnss-orchestrated-run/`
- decision: `v700-provider-first-cnss-gap-persists`

## Scope

V700 deployed helper v119 and ran one bounded provider-first CNSS proof. It did
not start Wi-Fi HAL, `wificond`, supplicant, or hostapd; did not scan/connect,
use credentials, run DHCP, change routes, or ping externally; did not write
sysfs subsystem state, `esoc0`, boot images, or partitions.

## Result

| check | result |
| --- | --- |
| helper v119 serial deploy | pass |
| current-boot V641/V401/V490 prep | pass |
| service-notifier `180/74` gate | pass |
| initial pre-provider `cnss-daemon` suppressed | pass |
| `vendor.qcom.PeripheralManager` exact query | pass |
| post-provider `cnss-daemon` retry started | pass |
| cleanup reboot health | pass |
| WLFW/BDF/`wlan0` progression | finding: still absent |

## Live Finding

V700 removed the V698 confounder. The old initial pre-provider
`cnss-daemon` failure path was not executed:

```text
initial_cnss_daemon: index=-1 observable=0 cleanup_safe=1 suppressed=1
```

The provider-first path itself worked:

- service-notifier `180`: `1`
- service-notifier `74`: `1`
- `vendor.qcom.PeripheralManager` exact match: `true`
- `cnss_daemon_retry.start_order`: `11`
- `cnss_daemon_netlink`: `5`
- `cnss_daemon_cld80211`: `2`
- CNSS Binder transaction failure: `0`
- generic Binder transaction failure: `0`

However, the lower Wi-Fi surface still did not advance:

- `qmi_server_connected`: `0`
- `wlfw_start`: `0`
- `wlfw_service_request`: `0`
- `wlan_pd`: `0`
- `bdf_regdb`: `0`
- `bdf_bdwlan`: `0`
- `wlan_fw_ready`: `0`
- `wlan0`: `0`

Marker summary:

```text
qrtr_rx=1 qrtr_tx=1 sysmon_qmi=4 service_notifier=2 kernel_warning=1
wlfw=0 bdf=0 wlan0=0
```

## Interpretation

The V666/V667 cnss2/WLAN-PD direction was correct, but V700 proves the latest
provider-first userspace chain no longer fails on the previously observed
Binder `29189/-22` attribution. The remaining blocker is now after service
`180/74` and after provider-confirmed CNSS retry, but still before WLFW service
`69`, BDF download, firmware-ready, or `wlan0`.

The next unit should classify the remaining pre-WLFW trigger rather than repeat
old Binder-only retry loops.

## Validation

Executed:

```bash
python3 -m py_compile \
  scripts/revalidation/native_wifi_provider_first_cnss_v700.py \
  scripts/revalidation/wifi_execns_helper_v119_deploy_preflight.py \
  scripts/revalidation/native_wifi_provider_first_cnss_orchestrator_v700.py

python3 scripts/revalidation/native_wifi_provider_first_cnss_v700.py \
  --out-dir tmp/wifi/v700-provider-first-cnss-plan-check plan

python3 scripts/revalidation/wifi_execns_helper_v119_deploy_preflight.py \
  --out-dir tmp/wifi/v700-execns-helper-v119-deploy-preflight-check preflight

python3 scripts/revalidation/wifi_execns_helper_v119_deploy_preflight.py \
  --out-dir tmp/wifi/v700-execns-helper-v119-deploy-run-safe \
  --apply --assume-yes \
  --approval-phrase "approve v700 deploy execns helper v119 only; no daemon start and no Wi-Fi bring-up" \
  run

python3 scripts/revalidation/native_wifi_provider_first_cnss_orchestrator_v700.py \
  --out-dir tmp/wifi/v700-provider-first-cnss-orchestrated-run \
  --apply --assume-yes run

python3 scripts/revalidation/a90ctl.py selftest
```

Results:

```text
execns-helper-v119-deploy-pass
v700-provider-first-cnss-gap-persists
selftest: pass=11 warn=1 fail=0
```

## Deployment Note

An attempted `--serial-chunk-size 3000` deploy was rejected by the helper
deploy line-safety check before writing chunks:

```text
serial chunk size is unsafe for the native console line limit
```

The successful deploy used the safe default chunk size and wrote `739` serial
chunks. NCM was not configured on the host during this run, so transfer fell
back to serial.

## Next Gate

Plan V701 as a pre-WLFW trigger classifier using the V700 evidence:

- inspect the single kernel warning around the provider-first retry window;
- compare CNSS/cnss2/icnss/QCA6390 dmesg near service-notifier `180/74`;
- capture relevant read-only cnss2/platform/sysfs state after the retry;
- keep Wi-Fi HAL, scan/connect, DHCP, credentials, route changes, and external
  ping blocked until WLFW/BDF/`wlan0` advances.
