# Native Init V1839 Lower-Continuation Gap Classifier

## Summary

- Cycle: `V1839`
- Type: host-only classifier over V1838 live evidence and retained Android-positive references
- Decision: `v1839-pm-connect-return-without-powerup-trigger-host-pass`
- Label: `pm-connect-return-without-powerup-trigger`
- Result: PASS
- Reason: V1838 proves PM list/register success and static PMIC/GDSC lower state with no mdm_subsys_powerup thread or inferred subsys_esoc0 open
- Evidence: `tmp/wifi/v1839-lower-continuation-gap-classifier`

## Inputs

- V1838: `v1838-lower-continuation-static-gap-rollback-pass` / pass `True`
- V1836: `v1836-wlan-pd-uninit-lower-continuation-target-host-pass` / pass `True`
- V1760: `v1760-android-good-serves-wlanmdsp-native-never-requests-host-pass` / pass `True`
- V1738: `v1738-pd-trigger-is-modem-autoload-missing-pass` / pass `True`
- V1244: `v1244-android-pmic-pcie-delta-classified` / pass `True`

## V1838 Current State

- handoff/rollback/post-version/post-selftest: `True` / `True` / `True` / `True`
- lower-continuation label: `lower-continuation-static-gap`
- PM focus contract/safety/change/delta: `True` / `True` / `[]` / `0`
- PM-service count/names/devnodes/list-commit/init-fail: `2` / `SDX50M,modem` / `/dev/subsys_esoc0,/dev/subsys_modem` / `2` / `0`
- PM-server/provider/asInterface/registerTX/success: `pm-server-register-success-return` / `1` / `1` / `1` / `1`
- powerup threads / inferred esoc0 opens: `['0', '0']` / `['0', '0']`
- mdm3/status counts: `['OFFLINING', 'OFFLINING']` / `['0', '0']`
- pcie1/pcie0 GDSC: `['pcie_1_gdsc                      0    2      0     0mV     0mA     0mV     0mV', 'pcie_1_gdsc                      0    2      0     0mV     0mA     0mV     0mV']` / `['pcie_0_gdsc                      0    1      0     0mV     0mA     0mV     0mV', 'pcie_0_gdsc                      0    1      0     0mV     0mA     0mV     0mV']`
- PMIC soft-reset: `['pin 7 (gpio9): (MUX UNCLAIMED) c440000.qcom,spmi:qcom,pm8150l@4:pinctrl@c000:1270', 'pin 7 (gpio9): (MUX UNCLAIMED) c440000.qcom,spmi:qcom,pm8150l@4:pinctrl@c000:1270']`
- MHI/wlan0 samples: bus `['0', '0']` pipe `['0', '0']` wlan0 `['0', '0']`
- service-notifier / QRTR bound labels: `service-notifier-uninit` / `qipcrtr-bound-recv-poll-timeout-passive`
- lower mdm3/MHI/WLFW69/wlan0/requested-wlanmdsp: `OFFLINING` / `False` / `False` / `False` / `0`

## Android-Positive Contrast

- V1760 Android requested wlanmdsp/vendor fallback: `True` / `True`
- V1760 native requested wlanmdsp: `0`
- V1738 Android companion/WLAN-PD+wlan0/no-restart-PD: `True` / `True` / `True`
- V1244 Android PCIe RC1: `| PCIe RC1 link initialized | 8.820s |`
- V1244 native first mdm3/pcie1/PMIC: `OFFLINING` / `pcie_1_gdsc                      0    2      0     0mV     0mA     0mV     0mV` / `pin 7 (gpio9): (MUX UNCLAIMED) c440000.qcom,spmi:qcom,pm8150l@4:pinctrl@c000:1270`

## Interpretation

- V1838 moves the immediate boundary below PM-service list population and PM-server register success: both SDX50M and modem records are present and list commits succeed.
- The same V1838 route does not enter the lower powerup window: powerup-thread count is zero, inferred `/dev/subsys_esoc0` open is zero, mdm-status count stays zero, PMIC/GDSC text is unchanged, MHI/WLFW/`wlan0` remain absent, and service-notifier stays `uninit`.
- V1244 remains useful as downstream power-surface context, but V1838 shows the immediate current-route target is earlier: PM-client/register-success to PM-service `mdm_subsys_powerup` trigger generation.
- The next unit should be source/build-only first and instrument or classify the read-only PM-client callback/vote-to-powerup transition. It should not add actors, direct eSoC opens, restart-PD, PMIC/GPIO/GDSC writes, Wi-Fi HAL, scan/connect, DHCP/routes, credentials, or external ping.

## Safety Scope

Host-only. This classifier did not issue live device commands, flash, reboot, stage properties, start actors, open `/dev/subsys_esoc0`, start `boot_wlan`, issue restart-PD request, force RC1, fake ONLINE state, write PMIC/GPIO/GDSC controls, perform eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, or external ping.
