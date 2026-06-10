# Native Init V2144 QCACLD Firmware Class Clean Recapture

## Summary

- Cycle: `V2144`
- Decision: `v2144-clean-fwclass-wlan0-helper-intact-fwready-consistent-rollback-pass`
- Label: `clean-fwclass-wlan0-helper-intact-fwready-consistent`
- Pass: `True`
- Reason: late recapture preserved wlan0 and helper/ICNSS state shows FW READY
- Evidence: `tmp/wifi/v2144-qcacld-fwclass-clean-recapture-handoff`

## Gate Results

- `wlan0_present`: `True` address `xx:7f:3a` (`mac_raw_redacted=1`)
- `helper_intact`: `True` missing `False` summary_armed `False`
- `icnss_state_line`: `State: 0xd8d(FW CONN | FW READY | DRIVER PROBED | SSR REGISTERED | PDR REGISTERED | MSA0 ASSIGNED | WLAN FW EXISTS)`
- `icnss_fw_ready_processed`: `1`
- `icnss_register_driver_processed`: `1`
- `fw_ready_dmesg`: `True`
- `assigning_mac`: `False`
- `set_features_fail`: `True`
- `swlan0_fail`: `True`
- `requested_wlanmdsp`: `False`

## Reframe

- This recaptures the V2137 route with a late collection window so `helper.result` and helper-embedded `/sys/kernel/debug/icnss/stats` counters are available.
- If `wlan0` and FW_READY persist while `requested_wlanmdsp` remains false, this firmware_class path is independent of the modem tftp `wlanmdsp.mbn` branch for native bring-up.
- Connectivity, scans, credentials, DHCP/routes, and external ping remain blocked until MAC assignment and degraded-interface errors are resolved.

## Steps

- `pre-status` rc `0` ok `True` evidence `pre-status.stdout.txt`
- `pre-selftest` rc `0` ok `True` evidence `pre-selftest.stdout.txt`
- `set-sibling-fwssctl-flag` rc `0` ok `True` evidence `set-sibling-fwssctl-flag.stdout.txt`
- `test-flash-from-native` rc `0` ok `True` evidence `test-flash-from-native.stdout.txt`
- `test-helper-wait-polls` rc `1` ok `False` evidence `test-helper-wait-polls.txt`
- `test-version` rc `0` ok `True` evidence `test-version.stdout.txt`
- `test-status` rc `0` ok `True` evidence `test-status.stdout.txt`
- `test-selftest` rc `0` ok `True` evidence `test-selftest.stdout.txt`
- `test-bootstatus` rc `0` ok `True` evidence `test-bootstatus.stdout.txt`
- `test-v2137-log-hide-on-busy` rc `0` ok `True` evidence `test-v2137-log-hide-on-busy.stdout.txt`
- `test-v2137-log` rc `0` ok `True` evidence `test-v2137-log.stdout.txt`
- `test-v2137-summary` rc `0` ok `True` evidence `test-v2137-summary.stdout.txt`
- `test-v2137-helper-result` rc `0` ok `True` evidence `test-v2137-helper-result.stdout.txt`
- `test-dmesg-full` rc `0` ok `True` evidence `test-dmesg-full.stdout.txt`
- `test-dmesg-wifi-filter` rc `0` ok `True` evidence `test-dmesg-wifi-filter.stdout.txt`
- `test-icnss-stats` rc `1` ok `False` evidence `test-icnss-stats.stdout.txt`
- `test-icnss-debugfs-ls` rc `1` ok `False` evidence `test-icnss-debugfs-ls.stdout.txt`
- `test-wlan0-state` rc `0` ok `True` evidence `test-wlan0-state.stdout.txt`
- `test-wlan0-ifconfig` rc `0` ok `True` evidence `test-wlan0-ifconfig.stdout.txt`
- `test-sys-wifi-mac-node` rc `0` ok `True` evidence `test-sys-wifi-mac-node.stdout.txt`
- `rollback-from-native` rc `0` ok `True` evidence `rollback-from-native.stdout.txt`
- `rollback-status` rc `0` ok `True` evidence `rollback-status.stdout.txt`
- `rollback-selftest` rc `0` ok `True` evidence `rollback-selftest.stdout.txt`

## Safety

- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping was used.
- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.
- Mutation scope: `/cache` one-shot clean-DSP flag, V2137 rollbackable test boot, bounded firmware_class fallback sysfs writes from the V2137 contract, and rollback to `stage3/boot_linux_v724.img` with selftest verification.
