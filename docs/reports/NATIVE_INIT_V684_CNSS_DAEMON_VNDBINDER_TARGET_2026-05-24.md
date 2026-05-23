# Native Init V684 cnss-daemon vndbinder Target Report

## Result

- decision: `v684-cnss-daemon-peripheral-manager-target-candidate`
- pass: `true`
- evidence: `tmp/wifi/v684-cnss-daemon-vndbinder-target/`
- device commands: `false`
- Wi-Fi bring-up: `false`

V684 did not run live device actions. It classified existing V682/V683 evidence
and local exported vendor binaries.

## Interpretation

The current blocker remains after service-notifier `180/74` and before WLFW
service `69`, BDF download, firmware-ready, and `wlan0`.

V684 adds a concrete Binder target candidate:

```text
cnss-daemon
  -> libperipheral_client.so
    -> /dev/vndbinder + defaultServiceManager
      -> vendor.qcom.PeripheralManager
```

This does not prove the live service is registered in native init. It proves the
next live proof should target `vendor.qcom.PeripheralManager` availability or
start order before another CNSS retry.

## Evidence Summary

| Surface | Finding |
| --- | --- |
| V683 input | `v683-cnss-daemon-vndbinder-pre-wlfw-trigger-classified`, pass |
| `cnss-daemon` | imports/contains `libperipheral_client.so`, `pm_client_register`, `pm_client_connect`, `wlfw_start` |
| `libperipheral_client.so` | contains `libbinder.so`, `/dev/vndbinder`, `defaultServiceManager`, `IPeripheralManager`, `vendor.qcom.PeripheralManager` |
| `libqmiservices.so` | does not contain `libbinder.so` or `vendor.qcom.PeripheralManager` |
| V682 live | `cnss-daemon` count `123`, `libperipheral_client.so` count `8`, Binder `29189/-22` count `1` |
| V682 live markers | service-notifier `180=1`, `74=1`, CNSS netlink `10`, CLD80211 `4`, WLFW/QMI/BDF/firmware-ready/`wlan0=0` |
| live target literal | `vendor.qcom.PeripheralManager` count `0`, so live registration remains unproven |

## Static ELF Fingerprints

| Binary | Size | SHA256 |
| --- | ---: | --- |
| `cnss-daemon` | `95112` | `bced9853a77cfb02252571196584efa535be14f8f3fd9ce32712ddee224ba4bc` |
| `libperipheral_client.so` | `55648` | `e92e05976d7c04c04c055f569d87c4f27feac2b1901cd5ef4c617e62a7f770e4` |
| `libqmiservices.so` | `154352` | `1a1b21935e9a264f5818cb125961f392ae12c152adcf0f24e570eb5419ae6f3e` |

## Decision

Do not retry Wi-Fi HAL, scan/connect, DHCP, or external ping yet. The next
bounded unit should prove whether `vendor.qcom.PeripheralManager` exists and is
reachable in the native vendor Binder namespace, then run only a controlled CNSS
retry if that prerequisite is positive.

## Next Gate

V685:

1. inspect Android/vendor init service definitions for the
   `vendor.qcom.PeripheralManager` provider;
2. classify whether native init already registers it;
3. if absent and bounded-safe, start only the minimal provider needed for
   `libperipheral_client.so`;
4. retry `cnss-daemon` only after service availability is proven;
5. continue blocking Wi-Fi HAL, scan/connect, DHCP, routes, and external ping.
