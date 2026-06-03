# Native Init V1836 WLAN-PD UNINIT Transition Classifier

## Summary

- Cycle: `V1836`
- Type: host-only retained-evidence classifier over V1835 plus lower/Android-positive baselines
- Decision: `v1836-wlan-pd-uninit-lower-continuation-target-host-pass`
- Result: PASS
- Reason: PM list/register, service-object, service-locator/notifier, and QIPCRTR socket mechanics are cleared enough; native remains mdm3 OFFLINING with service-notifier uninit, no WLFW service 69, no wlanmdsp request, no MHI, and no wlan0 while Android-positive reaches mdm3 ONLINE, WLAN-PD UP, WLFW/BDF, and wlan0
- Evidence: `tmp/wifi/v1836-wlan-pd-uninit-transition-classifier`

## Source Gates

- V1835: `v1835-qipcrtr-mechanics-cleared-wlan-pd-uninit-blocker-host-pass`
- V1804: `v1804-post-pm-success-mdm3-offlining-before-wlanpd-up-host-pass`
- V1760: `v1760-android-good-serves-wlanmdsp-native-never-requests-host-pass` / `request-generation-gap-before-firmware-serving`
- V1738: `v1738-pd-trigger-is-modem-autoload-missing-pass` / `pd-trigger-is-modem-autoload-missing`
- V1244: `v1244-android-pmic-pcie-delta-classified`

## Current Cleared Mechanics

- PM projection/list/init-fail: `list-commit-progress` / `2` / `0`
- PM provider/asInterface/register TX: `1` / `1` / `1`
- PM client register/connect/return rc: `0` / `0` / `0`
- QIPCRTR label/poll/reason: `qipcrtr-bound-recv-poll-timeout-passive` / `250ms timeout=1` / `poll-timeout`
- QRTR/service-locator/service-notifier labels: `wlfw-readback-empty` / `servloc-domain-wlan-pd-instance180` / `service-notifier-uninit`
- bound observer no connect/send/lookup/control/service-start: `1` / `1` / `1` / `1` / `1`

## Current Blocker Shape

- service-notifier early/late state: `uninit` / `uninit`
- service-notifier early/late indications: `0` / `0`
- raw service180/service74/wlan_pd: `1,1,1` / `0,0,0` / `0,0,0`
- lower state/mdm3/MHI: `stable-mdm3-offlining` / `OFFLINING` / `False`
- requested wlanmdsp / WLFW service69 / wlan0: `0` / `0` / `0`
- V1760 native WLFW start/request/worker/requested: `1` / `1` / `1` / `0`

## Android-Positive Contrast

- V1804 Android mss/mdm3: `ONLINE` / `ONLINE`
- V739 service-notifier74/wlan_pd/qmi/wlan0 counts: `1` / `2` / `1` / `3`
- V852 mdm3 and hints wlan_pd/WLFW/wlan0: `ONLINE` / `True` / `True` / `True`
- V1760 Android requested/fallback/OACK: `True` / `True` / `True`
- V1738 Android companion/no-restart/WLAN-PD+wlan0: `True` / `True` / `True`
- V1244 Android PCIe RC1 reference: `| PCIe RC1 link initialized | 8.820s |`

## Source Surface

- ICNSS WLFW lookup passive: `True`
- service-notifier listener is state query: `True`
- restart-PD API explicit recovery only: `True`
- source lines listener/restart/lookup: `319` / `648` / `1275`

## Legacy Power-Gap Context

- V1244 native decision: `v1243-pm-esoc0-trigger-sampled-mdm2ap-silent-reboot-required`
- V1244 native first mdm3/MHI/wlan0: `OFFLINING` / `0` / `0`
- V1244 native PCIe1 GDSC: `pcie_1_gdsc                      0    2      0     0mV     0mA     0mV     0mV`
- V1244 native PMIC soft-reset line: `pin 7 (gpio9): (MUX UNCLAIMED) c440000.qcom,spmi:qcom,pm8150l@4:pinctrl@c000:1270`

## Interpretation

- V1835 rules out another QRTR socket-mechanics unit: bound local port allocation, passive poll/timeout, service-locator domain-list QMI, and service-notifier listener QMI are all classified.
- The PM-service list/devnode and client register/connect blockers are also past the immediate boundary for this route.
- The remaining fixed blocker is the WLAN-PD UNINIT transition below the PM vote boundary: native does not move mdm3 toward ONLINE/MHI, does not publish WLFW service 69, and never requests `wlanmdsp.mbn`.
- The next unit should be host/source-only first and define a no-write lower-continuation observer/target around mdm3/ext-SDX50M state transition prerequisites; it should not add QRTR probes, PM actors, restart-PD, eSoC/RC1 actions, Wi-Fi HAL, or scan/connect.

## Safety Scope

Host-only. This classifier did not issue live device commands, flash, reboot, stage properties, start actors, open `/dev/subsys_esoc0`, start `boot_wlan`, issue restart-PD request, force RC1, fake ONLINE state, write PMIC/GPIO/GDSC controls, perform eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, or external ping.
