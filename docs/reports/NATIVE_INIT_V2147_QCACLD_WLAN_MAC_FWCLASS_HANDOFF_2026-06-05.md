# Native Init V2147 QCACLD wlan_mac.bin Firmware Class Handoff

## Summary

- Cycle: `V2147`
- Decision: `v2147-platform-mac-swlan0-created-set-features-blocker-rollback-pass`
- Label: `platform-mac-swlan0-created-set-features-blocker`
- Pass: `True`
- Reason: pre-HDD platform MAC was consumed and swlan0 generation succeeded; remaining blocker is set_features/debugfs
- Evidence: `tmp/wifi/v2147-qcacld-wlan-mac-fwclass-handoff`

## Gate Results

- `source_ok`: `True` hex_digits `12` raw_mac_logged `0`
- `payload_write_ok`: `True` len `120` raw_payload_logged `0`
- `feeder_seen`: `False` fed `False` write_ok `True`
- `dmesg_requested_wlan_mac`: `False`
- `dmesg_uses_wlan_mac`: `False` default_mac `False`
- `dmesg_provisioned_platform_mac`: `True`
- `dmesg_uses_platform_mac`: `True`

## Interface State

- `wlan0_present`: `True` address_logged `0`
- `set_features_fail`: `True`
- `swlan0_present`: `True`
- `swlan0_generation_fail`: `False`
- `wow_debugfs_fail`: `True`
- `legacy_swlan0_fail_counter`: `False`
- `icnss_state_line`: `State: 0xd8d(FW CONN | FW READY | DRIVER PROBED | SSR REGISTERED | PDR REGISTERED | MSA0 ASSIGNED | WLAN FW EXISTS)`
- `requested_wlanmdsp`: `False`

## Reframe

- V2146 proved `/sys/wifi/mac_addr` reaches the kernel store path, but V2146 dmesg still showed `wlan_mac.bin` firmware_class timeout followed by default MAC selection.
- V2147 feeds only the observed `wlan/qca_cld/wlan_mac.bin` firmware_class node using a redacted payload generated from read-only EFS `.mac.info`.
- The current V2147 capture shows HDD consumed the platform-driver MAC before interface creation, skipped the default-MAC path, and created `swlan0`; therefore the MAC/swlan0-generation gate is solved for this route.
- The remaining degraded-interface blocker is `set_features() failed (-11)` plus `wow debug_fs init failed` on secondary adapters.
- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping is used in this gate; connectivity remains downstream of a clean wlan0.

## Steps

- `pre-status` rc `0` ok `True` evidence `pre-status.stdout.txt`
- `pre-selftest` rc `0` ok `True` evidence `pre-selftest.stdout.txt`
- `set-sibling-fwssctl-flag` rc `0` ok `True` evidence `set-sibling-fwssctl-flag.stdout.txt`
- `test-flash-from-native` rc `0` ok `True` evidence `test-flash-from-native.stdout.txt`
- `mac-assign-begin-hide-on-busy` rc `0` ok `True` evidence `mac-assign-begin-hide-on-busy.stdout.txt`
- `mac-assign-begin` rc `0` ok `True` evidence `mac-assign-begin.stdout.txt`
- `mac-assign-mkdir-dev-block` rc `0` ok `True` evidence `mac-assign-mkdir-dev-block.stdout.txt`
- `mac-assign-mkdir-efs` rc `0` ok `True` evidence `mac-assign-mkdir-efs.stdout.txt`
- `mac-assign-efs-uevent` rc `0` ok `True` evidence `mac-assign-efs-uevent.stdout.txt`
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
- `wlan-mac-payload-touch` rc `0` ok `True` evidence `wlan-mac-payload-touch.stdout.txt`
- `wlan-mac-payload-write` rc `0` ok `True` evidence `wlan-mac-payload-write.stdout.txt`
- `wlan-mac-feeder-script-rm` rc `0` ok `True` evidence `wlan-mac-feeder-script-rm.stdout.txt`
- `wlan-mac-feeder-script-touch` rc `0` ok `True` evidence `wlan-mac-feeder-script-touch.stdout.txt`
- `wlan-mac-feeder-script-line-00` rc `0` ok `True` evidence `wlan-mac-feeder-script-line-00.stdout.txt`
- `wlan-mac-feeder-script-line-01` rc `0` ok `True` evidence `wlan-mac-feeder-script-line-01.stdout.txt`
- `wlan-mac-feeder-script-line-02` rc `0` ok `True` evidence `wlan-mac-feeder-script-line-02.stdout.txt`
- `wlan-mac-feeder-script-line-03` rc `0` ok `True` evidence `wlan-mac-feeder-script-line-03.stdout.txt`
- `wlan-mac-feeder-script-line-04` rc `0` ok `True` evidence `wlan-mac-feeder-script-line-04.stdout.txt`
- `wlan-mac-feeder-script-line-05` rc `0` ok `True` evidence `wlan-mac-feeder-script-line-05.stdout.txt`
- `wlan-mac-feeder-script-line-06` rc `0` ok `True` evidence `wlan-mac-feeder-script-line-06.stdout.txt`
- `wlan-mac-feeder-script-line-07` rc `0` ok `True` evidence `wlan-mac-feeder-script-line-07.stdout.txt`
- `wlan-mac-feeder-script-line-08` rc `0` ok `True` evidence `wlan-mac-feeder-script-line-08.stdout.txt`
- `wlan-mac-feeder-script-line-09` rc `0` ok `True` evidence `wlan-mac-feeder-script-line-09.stdout.txt`
- `wlan-mac-feeder-script-line-10` rc `0` ok `True` evidence `wlan-mac-feeder-script-line-10.stdout.txt`
- `wlan-mac-feeder-script-line-11` rc `0` ok `True` evidence `wlan-mac-feeder-script-line-11.stdout.txt`
- `wlan-mac-feeder-script-line-12` rc `0` ok `True` evidence `wlan-mac-feeder-script-line-12.stdout.txt`
- `wlan-mac-feeder-script-line-13` rc `0` ok `True` evidence `wlan-mac-feeder-script-line-13.stdout.txt`
- `wlan-mac-feeder-script-line-14` rc `0` ok `True` evidence `wlan-mac-feeder-script-line-14.stdout.txt`
- `wlan-mac-feeder-script-line-15` rc `0` ok `True` evidence `wlan-mac-feeder-script-line-15.stdout.txt`
- `wlan-mac-feeder-script-line-16` rc `0` ok `True` evidence `wlan-mac-feeder-script-line-16.stdout.txt`
- `wlan-mac-feeder-script-line-17` rc `0` ok `True` evidence `wlan-mac-feeder-script-line-17.stdout.txt`
- `wlan-mac-feeder-script-line-18` rc `0` ok `True` evidence `wlan-mac-feeder-script-line-18.stdout.txt`
- `wlan-mac-feeder-script-line-19` rc `0` ok `True` evidence `wlan-mac-feeder-script-line-19.stdout.txt`
- `wlan-mac-feeder-script-line-20` rc `0` ok `True` evidence `wlan-mac-feeder-script-line-20.stdout.txt`
- `wlan-mac-feeder-script-line-21` rc `0` ok `True` evidence `wlan-mac-feeder-script-line-21.stdout.txt`
- `wlan-mac-feeder-script-line-22` rc `0` ok `True` evidence `wlan-mac-feeder-script-line-22.stdout.txt`
- `wlan-mac-feeder-script-line-23` rc `0` ok `True` evidence `wlan-mac-feeder-script-line-23.stdout.txt`
- `wlan-mac-feeder-script-chmod` rc `0` ok `True` evidence `wlan-mac-feeder-script-chmod.stdout.txt`
- `wlan-mac-feeder-start` rc `0` ok `True` evidence `wlan-mac-feeder-start.stdout.txt`
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
- `post-rollback-wlan-mac-feeder-result-hide-on-busy` rc `0` ok `True` evidence `post-rollback-wlan-mac-feeder-result-hide-on-busy.stdout.txt`
- `post-rollback-wlan-mac-feeder-result` rc `0` ok `True` evidence `post-rollback-wlan-mac-feeder-result.stdout.txt`
- `post-rollback-wlan-mac-feeder-cleanup` rc `0` ok `True` evidence `post-rollback-wlan-mac-feeder-cleanup.stdout.txt`

## Cleanup

- `cache_artifacts_removed`: `True`

## Safety

- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping was used.
- EFS was mounted read-only; no EFS, persist, firmware, boot, or partition file was written.
- The only functional write in the test boot was bounded firmware_class userspace fallback data for the observed `wlan_mac.bin` request.
- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.
