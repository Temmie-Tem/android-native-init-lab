# Native Init V697 CNSS Binder Runtime Target Report

- date: `2026-05-24 KST`
- status: `host-only-pass`; Wi-Fi external ping is **not** complete
- evidence: `tmp/wifi/v697-cnss-binder-runtime-target-classifier-rerun/`
- decision: `v697-cnss-vndbinder-transaction-framing-targeted`

## Scope

V697 used existing evidence only. It did not contact the device, start daemons,
start Wi-Fi HAL, scan/connect/link-up, use credentials, run DHCP, change
routes, ping externally, write sysfs/debugfs, or write boot partitions.

Inputs:

- V684 manifest:
  `tmp/wifi/v684-cnss-daemon-vndbinder-target/manifest.json`
- V695 manifest:
  `tmp/wifi/v695-provider-confirmed-cnss-retry-orchestrated-live/manifest.json`
- V696 manifest:
  `tmp/wifi/v696-post-provider-retry-blocker-classifier-rerun/manifest.json`
- V695 helper output:
  `tmp/wifi/v695-provider-confirmed-cnss-retry-orchestrated-live/arm-v695-v118-provider-confirmed-cnss-retry/live/native/companion-start-only-with-holder.txt`
- V695 native dmesg:
  `tmp/wifi/v695-provider-confirmed-cnss-retry-orchestrated-live/arm-v695-v118-provider-confirmed-cnss-retry/live/native/dmesg-delta.txt`

## Relationship To V666 Direction

The V666 causal-chain direction is correct, but it is no longer the current
execution point. V667/V681 already consumed the service-notifier `180/74` versus
cnss2/WLFW progression question and showed that service-notifier publication
does not advance to WLFW service `69`, BDF, firmware-ready, or `wlan0` in
native.

V697 starts from the newer evidence:

- V684 statically narrowed the Binder target to
  `cnss-daemon` -> `libperipheral_client` -> `/dev/vndbinder` ->
  `vendor.qcom.PeripheralManager`.
- V695 proved `vendor.qcom.PeripheralManager` registration and a fresh
  post-registration `cnss-daemon` retry.
- V696 showed Android reaches WLFW/BDF/FW-ready while native stops at
  `cnss-daemon` Binder transaction `29189/-22`.

## Result

| check | status |
| --- | --- |
| input evidence ready | pass |
| provider registration proven | pass |
| static CNSS target is PeripheralManager/vndbinder | finding |
| `cnss-daemon` uses `/dev/vndbinder` | finding |
| `vndservicemanager` ready on `/dev/vndbinder` | finding |
| CNSS domain and SELinux preexec OK | finding |
| CNSS Binder transaction failure stable | finding |
| generic context-manager ioctl demoted | finding |
| duplicate `pm_qos` remains secondary | finding |

## Evidence

| surface | result |
| --- | --- |
| provider query | `vendor.qcom.PeripheralManager` appeared twice in V695 helper output |
| initial `cnss-daemon` fd | `/dev/vndbinder` count `1` |
| retry `cnss-daemon` fd | `/dev/vndbinder` count `1` |
| `vndservicemanager` fd | `/dev/vndbinder` count `2` |
| `servicemanager` fd | `/dev/binder` count `1` |
| `hwservicemanager` fd | `/dev/hwbinder` count `1` |
| CNSS SELinux context | `u:r:vendor_wcnss_service:s0` for initial and retry |
| CNSS Binder failure | `transaction failed 29189/-22`, count `1` |
| WLFW start | count `0` |
| duplicate `pm_qos` | count `1`, tracked as secondary |

## Interpretation

V697 demotes the earlier generic service-manager/hwservice-manager ioctl `-22`
noise because the active target path is `/dev/vndbinder`, and V695 proved both
`vndservicemanager` readiness and `vendor.qcom.PeripheralManager` visibility.
The remaining failure is no longer a provider-registration, Binder devnode, or
SELinux preexec problem.

The next unit should target the `cnss-daemon` vendor Binder transaction itself:
transaction framing, target service/method expectations, or
`libperipheral_client` runtime assumptions inside the private namespace. Wi-Fi
HAL start, scan/connect, DHCP, route changes, credentials, and external ping
remain blocked until WLFW/BDF/`wlan0` progression exists.

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_cnss_binder_runtime_target_classifier_v697.py
python3 scripts/revalidation/native_wifi_cnss_binder_runtime_target_classifier_v697.py \
  --out-dir tmp/wifi/v697-cnss-binder-runtime-target-classifier-rerun \
  run
```

Result:

```text
decision: v697-cnss-vndbinder-transaction-framing-targeted
pass: True
device_commands_executed: False
wifi_hal_start_executed: False
scan_connect_executed: False
wifi_bringup_executed: False
external_ping_executed: False
```

## Next Gate

Plan V698 as a narrow `cnss-daemon`/`libperipheral_client` vendor Binder
transaction capture or repair gate:

- keep the provider registration sequence from V695;
- capture or repair only the `cnss-daemon` vendor Binder transaction path;
- do not start Wi-Fi HAL, scan/connect, run DHCP, use credentials, change
  routes, or external ping.
