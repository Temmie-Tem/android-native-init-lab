# Native Init V1557 Endpoint Signal Long-Hold Handoff

## Summary

- Cycle: `V1557`
- Type: rollbackable native Wi-Fi test-boot long hold
- Decision: `v1557-native-long-hold-endpoint-still-silent-no-l0-rollback-pass`
- Result: `PASS`
- Reason: native long hold still has RC1 link failure and no wake/status endpoint signal; rollback verified
- Evidence: `tmp/wifi/v1557-native-endpoint-long-hold-handoff`
- Hold seconds: `280.0`

## Progress

| field | value |
| --- | --- |
| provider/modem | True/True |
| RC1 progress/L0/link_failed | True/False/True |
| MHI/WLFW/BDF/FW-ready/wlan0 | False/False/False/False/False |
| endpoint_positive | False |
| IRQ wake/status/errfatal | 0/0/0 |
| GPIO104/GPIO142/GPIO135 high | False/False/False |
| rc1_window_sample_count | 5 |

## Safety

The only device mutation is the declared test boot flash and rollback to native v724. The runner performs no Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, direct PMIC/GPIO/GDSC write, eSoC notify/BOOT_DONE spoof, global PCI rescan, or platform bind/unbind.

## Next

- If endpoint signals remain absent, compare the provider-driven native path against Android's pre-IRQ state and avoid more long-hold retries.
- If endpoint signals appear, move to the earliest missing stage after wake/status: L0, PCI enumeration, MHI, WLFW/BDF, then `wlan0`.
