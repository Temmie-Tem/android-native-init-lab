# Native Init V1560 Android Order vs Native Route Classifier

## Summary

- Cycle: `V1560`
- Type: host-only Android/native lower-sequence classifier
- Decision: `v1560-android-wlfw-before-ap2mdm-native-route-lacks-wlfw`
- Result: `PASS`
- Reason: Android lower sequence reaches wlfw_start before esoc0/AP2MDM/BDF, but native V1496/V1557 only reaches cnss-daemon netlink plus forced RC1 enumerate and never reaches wlfw_start/BDF/FW-ready/wlan0
- Evidence: `tmp/wifi/v1560-android-order-vs-native-route-classifier`

## Inputs

| input | path |
| --- | --- |
| android_v1555 | tmp/wifi/v1555-android-good-minimal-trace-reference/manifest.json |
| native_v1496_dmesg | tmp/wifi/v1496-wifi-rc1-window-short-hold-handoff/test-v1393-dmesg.stdout.txt |
| native_v1557 | tmp/wifi/v1557-native-endpoint-long-hold-handoff/manifest.json |
| v1559_order_classifier | tmp/wifi/v1559-android-pre-endpoint-order-classifier/manifest.json |

## Sequence Comparison

| signal | android_v1555 | native_v1496 | native_v1557 | interpretation |
| --- | --- | --- | --- | --- |
| cnss/WLFW start | 43.444373 | missing | missing | Android has explicit wlfw_start; native route does not |
| wlfw service request | 43.479557 | missing | missing | Android starts WLFW request thread before BDF |
| cnss netlink | not discriminating | 9.053124 | 9.022028 | native watcher triggers on netlink, not on wlfw_start |
| esoc0 get | 43.547935 | 9.132753 | 9.102002 | both paths reach esoc0 |
| BDF | 44.514027/44.528819 | missing | missing | Android BDF is +1.069654s after wlfw_start |
| FW-ready/wlan0 | 49.428211/49.775275 | missing/missing | missing/missing | native never reaches lower Wi-Fi readiness |
| RC1 forced enumerate | late L0=248.811581 | phy=9.185345 fail=9.294307 | phy=9.151651 fail=9.260647 | native forced RC1 path fails before L0; Android retained L0 is late relative to wlan0 |

## Derived Checks

| check | value |
| --- | --- |
| android_order_ok | True |
| native_route_lacks_wlfw | True |
| l0_order_caveat | True |

## Interpretation

The existing Android-good evidence shows the lower sequence starts with `cnss-daemon wlfw_start`, then reaches `esoc0`, BDF, FW-ready, and `wlan0`. The current native auto-readiness route does not reproduce that contract: it sees `cnss-daemon` generic netlink traffic, then forces RC1 enumerate and fails before L0, but no `wlfw_start`, BDF, FW-ready, or `wlan0` appears.

Therefore the next useful unit is not a credentialed Wi-Fi connect attempt and not another blind RC1 enumerate retry. The immediate missing contract is the native `cnss-daemon` WLFW start/request path.

## Next Gate

- Recommended cycle: `V1561`
- Type: host-only contract comparator before live
- Focus: cnss-daemon WLFW start/request contract, not credentials or connect

### Requirements

- compare Android cnss-daemon invocation/properties/sockets/service-manager context against native test-boot cnss-daemon context
- explain why native cnss-daemon emits generic netlink traffic but not wlfw_start/wlfw_service_request
- keep forced RC1 enumerate as diagnostic only; do not use it as the primary trigger for lower Wi-Fi
- do not start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, or external ping until WLFW/BDF/FW-ready/wlan0 exist in native

## Safety Scope

This classifier is host-only. It performs no device command, flash, reboot, partition write, Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC write, eSoC notify/BOOT_DONE spoof, pci-msm debugfs write, global PCI rescan, or platform bind/unbind.
