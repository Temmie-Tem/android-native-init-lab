# Native Init V2152 Connect DHCP Google Ping Handoff

## Summary

- Cycle: `V2152`
- Run label: `2g-kr-country`
- Decision: `v2152-connect-dhcp-ping-association-failed-rollback-blocked`
- Label: `connect-dhcp-ping-association-failed`
- Pass: `False`
- Reason: supplicant did not establish carrier; result=connect-dhcp-ping-failed helper_rc=0
- Evidence: `tmp/wifi/v2152-connect-dhcp-google-ping-handoff-2g-kr-country`

## Gate Results

- `wlan0_seen`: `True` helper_invoked `True` helper_rc `0`
- `executor_result`: `connect-dhcp-ping-failed`
- `association_carrier`: `False` errno `110`
- `country`: `KR` driver_ioctl_rc `0` errno `0` readback `US` get_rc `0`
- `wpa_ctrl`: ready `False` surface `none` ping `none` country_rc `0` reply `` enable `` reassociate ``
- `dhcp_executed`: `False` dhcp_rc `-1`
- `external_ping_executed`: `False` target `google.com` rc `-1`
- `pre_state`: operstate `down` carrier `unreadable` flags `0x1002`
- `post_state`: operstate `down` carrier `unreadable` flags `0x1002`
- `helper_stage_ok`: `True` config_ok `True` script_ok `True` wait_complete `True`
- `no_raw`: `True` secret_values_logged `0`

## Staging

- `helper_sha256`: `f08c03a49104adb454ce9717f023a8c540bc2faec1eab1fd8e0dd547650659aa` gzip_len `593924` chunks `1547`
- `connect_config`: path `/cache/a90-wifi/v2152.conf` size `238` mode `600` security `wpa-psk` disabled_initially `0` raw_values_logged `0`

## Scope

- This is the first bounded native active connect unit after V2151 scan success.
- Allowed actions: start private Wi-Fi active-session surface, start `wpa_supplicant`, run DHCP, set temporary route/DNS, and ping `google.com`.
- Outputs are redacted: no SSID, PSK, BSSID, raw MAC, assigned IP, route, DNS, DHCP lease, or ping transcript is recorded in the report.
- Cleanup removes staged config/result/script artifacts and rollback returns to `v724`.

## Steps

- `pre-status` rc `0` ok `True` evidence `pre-status.stdout.txt`
- `pre-selftest` rc `0` ok `True` evidence `pre-selftest.stdout.txt`
- `set-sibling-fwssctl-flag` rc `0` ok `True` evidence `set-sibling-fwssctl-flag.stdout.txt`
- `test-flash-from-native` rc `0` ok `True` evidence `test-flash-from-native.stdout.txt`
- `host-build-execns-helper` rc `0` ok `True` evidence `host-build-execns-helper.stdout.txt`
- `execns-helper-verify-existing` rc `0` ok `True` evidence `execns-helper-verify-existing.stdout.txt`
- `connect-config-mkdir` rc `0` ok `True` evidence `connect-config-mkdir.stdout.txt`
- `connect-config-clean` rc `0` ok `True` evidence `connect-config-clean.stdout.txt`
- `connect-config-touch-b64` rc `0` ok `True` evidence `connect-config-touch-b64.stdout.txt`
- `connect-config-write-redacted` rc `0` ok `True` evidence `connect-config-write-redacted.stdout.txt`
- `connect-config-decode-redacted` rc `0` ok `True` evidence `connect-config-decode-redacted.stdout.txt`
- `connect-script-clean-hide-on-busy` rc `0` ok `True` evidence `connect-script-clean-hide-on-busy.stdout.txt`
- `connect-script-clean` rc `0` ok `True` evidence `connect-script-clean.stdout.txt`
- `connect-script-touch` rc `0` ok `True` evidence `connect-script-touch.stdout.txt`
- `connect-script-line-00` rc `0` ok `True` evidence `connect-script-line-00.stdout.txt`
- `connect-script-line-01` rc `0` ok `True` evidence `connect-script-line-01.stdout.txt`
- `connect-script-line-02` rc `0` ok `True` evidence `connect-script-line-02.stdout.txt`
- `connect-script-line-03` rc `0` ok `True` evidence `connect-script-line-03.stdout.txt`
- `connect-script-line-04` rc `0` ok `True` evidence `connect-script-line-04.stdout.txt`
- `connect-script-line-05` rc `0` ok `True` evidence `connect-script-line-05.stdout.txt`
- `connect-script-line-06` rc `0` ok `True` evidence `connect-script-line-06.stdout.txt`
- `connect-script-line-07` rc `0` ok `True` evidence `connect-script-line-07.stdout.txt`
- `connect-script-line-08` rc `0` ok `True` evidence `connect-script-line-08.stdout.txt`
- `connect-script-line-09` rc `0` ok `True` evidence `connect-script-line-09.stdout.txt`
- `connect-script-line-10` rc `0` ok `True` evidence `connect-script-line-10.stdout.txt`
- `connect-script-line-11` rc `0` ok `True` evidence `connect-script-line-11.stdout.txt`
- `connect-script-line-12` rc `0` ok `True` evidence `connect-script-line-12.stdout.txt`
- `connect-script-line-13` rc `0` ok `True` evidence `connect-script-line-13.stdout.txt`
- `connect-script-line-14` rc `0` ok `True` evidence `connect-script-line-14.stdout.txt`
- `connect-script-line-15` rc `0` ok `True` evidence `connect-script-line-15.stdout.txt`
- `connect-script-line-16` rc `0` ok `True` evidence `connect-script-line-16.stdout.txt`
- `connect-script-line-17` rc `0` ok `True` evidence `connect-script-line-17.stdout.txt`
- `connect-script-line-18` rc `0` ok `True` evidence `connect-script-line-18.stdout.txt`
- `connect-script-line-19` rc `0` ok `True` evidence `connect-script-line-19.stdout.txt`
- `connect-script-line-20` rc `0` ok `True` evidence `connect-script-line-20.stdout.txt`
- `connect-script-line-21` rc `0` ok `True` evidence `connect-script-line-21.stdout.txt`
- `connect-script-line-22` rc `0` ok `True` evidence `connect-script-line-22.stdout.txt`
- `connect-script-line-23` rc `0` ok `True` evidence `connect-script-line-23.stdout.txt`
- `connect-script-line-24` rc `0` ok `True` evidence `connect-script-line-24.stdout.txt`
- `connect-script-chmod` rc `0` ok `True` evidence `connect-script-chmod.stdout.txt`
- `connect-script-start` rc `0` ok `True` evidence `connect-script-start.stdout.txt`
- `connect-result-wait-polls` rc `0` ok `True` evidence `connect-result-wait-polls.txt`
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
- `post-rollback-connect-ping-result-hide-on-busy` rc `0` ok `True` evidence `post-rollback-connect-ping-result-hide-on-busy.stdout.txt`
- `post-rollback-connect-ping-result` rc `0` ok `True` evidence `post-rollback-connect-ping-result.stdout.txt`
- `post-rollback-connect-ping-cleanup` rc `0` ok `True` evidence `post-rollback-connect-ping-cleanup.stdout.txt`

## Cleanup

- `cache_artifacts_removed`: `True`

## Safety

- Wi-Fi credentials are read only from environment variables and are not committed.
- Raw supplicant, DHCP, and ping stdout/stderr are redirected to `/dev/null` by the helper.
- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action is used.
