# Native Init V2146 QCACLD Firmware Class Global MAC Assign Handoff

## Summary

- Cycle: `V2146`
- Decision: `v2146-global-mac-assign-kernel-proof-wlan0-still-degraded-rollback-pass`
- Label: `global-mac-assign-kernel-proof-wlan0-still-degraded`
- Pass: `True`
- Reason: pre-HDD MAC assignment reached the kernel store path and wlan0, but degraded-interface errors remain
- Evidence: `tmp/wifi/v2146-qcacld-fwclass-global-mac-assign-handoff`

## MAC Gate

- `source_ok`: `True` shape `colon_hex` exists `1` bytes `17` raw_logged `0`
- `target_exists`: `1` writable `True`
- `write_ok`: `False` rc `1` len `17`
- `assigning_mac`: `True` kernel_store_ok `True`

## Interface State

- `wlan0_present`: `True` address `xx:7f:3a` (`mac_raw_redacted=1`)
- `set_features_fail`: `True`
- `swlan0_fail`: `True`
- `icnss_state_line`: `State: 0xd8d(FW CONN | FW READY | DRIVER PROBED | SSR REGISTERED | PDR REGISTERED | MSA0 ASSIGNED | WLAN FW EXISTS)`
- `requested_wlanmdsp`: `False`

## Reframe

- V2146 keeps the proven V2137 `boot_wlan + firmware_class` route and adds a host-side pre-HDD MAC write immediately after test-boot verification.
- The EFS mount is read-only and only supplies `.mac.info`; the only write is the bounded ICNSS `/sys/wifi/mac_addr` sysfs assignment.
- If FW_READY/wlan0 still occur with no live dmesg `wlanmdsp.mbn`, the modem tftp branch remains moot for this native path.

## Steps

- `pre-status` rc `0` ok `True` evidence `pre-status.stdout.txt`
- `pre-selftest` rc `0` ok `True` evidence `pre-selftest.stdout.txt`
- `set-sibling-fwssctl-flag-hide-on-busy` rc `0` ok `True` evidence `set-sibling-fwssctl-flag-hide-on-busy.stdout.txt`
- `set-sibling-fwssctl-flag` rc `0` ok `True` evidence `set-sibling-fwssctl-flag.stdout.txt`
- `test-flash-from-native` rc `0` ok `True` evidence `test-flash-from-native.stdout.txt`
- `mac-assign-begin-hide-on-busy` rc `0` ok `True` evidence `mac-assign-begin-hide-on-busy.stdout.txt`
- `mac-assign-begin` rc `0` ok `True` evidence `mac-assign-begin.stdout.txt`
- `mac-assign-mkdir-dev-block` rc `0` ok `True` evidence `mac-assign-mkdir-dev-block.stdout.txt`
- `mac-assign-mkdir-efs` rc `0` ok `True` evidence `mac-assign-mkdir-efs.stdout.txt`
- `mac-assign-efs-uevent` rc `1` ok `False` evidence `mac-assign-efs-uevent.stdout.txt`
- `mac-assign-efs-block-rm` rc `0` ok `True` evidence `mac-assign-efs-block-rm.stdout.txt`
- `mac-assign-efs-block-mknod` rc `0` ok `True` evidence `mac-assign-efs-block-mknod.stdout.txt`
- `mac-assign-efs-ro-mount` rc `0` ok `True` evidence `mac-assign-efs-ro-mount.stdout.txt`
- `mac-assign-efs-mounted-check` rc `0` ok `True` evidence `mac-assign-efs-mounted-check.stdout.txt`
- `mac-assign-source-readable-test` rc `0` ok `True` evidence `mac-assign-source-readable-test.stdout.txt`
- `mac-assign-source-wc` rc `0` ok `True` evidence `mac-assign-source-wc.stdout.txt`
- `mac-assign-target-exists-test` rc `0` ok `True` evidence `mac-assign-target-exists-test.stdout.txt`
- `mac-assign-target-writable-test` rc `0` ok `True` evidence `mac-assign-target-writable-test.stdout.txt`
- `mac-assign-target-stat` rc `0` ok `True` evidence `mac-assign-target-stat.stdout.txt`
- `mac-assign-write-sysfs` rc `1` ok `False` evidence `mac-assign-write-sysfs.stdout.txt`
- `mac-assign-dmesg-proof` rc `0` ok `True` evidence `mac-assign-dmesg-proof.stdout.txt`
- `test-helper-wait-polls` rc `0` ok `True` evidence `test-helper-wait-polls.txt`
- `test-version` rc `0` ok `True` evidence `test-version.stdout.txt`
- `test-status` rc `0` ok `True` evidence `test-status.stdout.txt`
- `test-selftest` rc `0` ok `True` evidence `test-selftest.stdout.txt`
- `test-bootstatus` rc `0` ok `True` evidence `test-bootstatus.stdout.txt`
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
- No EFS/persist/file/partition write was used; EFS was mounted read-only and `.mac.info` was read-only.
- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.
