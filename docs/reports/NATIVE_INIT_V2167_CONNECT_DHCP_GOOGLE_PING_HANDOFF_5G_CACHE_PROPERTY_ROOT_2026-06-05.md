# Native Init V2167 Connect DHCP Google Ping Handoff

## Summary

- Cycle: `V2167`
- Run label: `5g-cache-property-root`
- Decision: `v2167-connect-dhcp-ping-association-failed`
- Label: `connect-dhcp-ping-association-failed`
- Pass: `False`
- Reason: supplicant did not establish carrier; result=connect-dhcp-ping-failed helper_rc=0
- Evidence: `tmp/wifi/v2167-connect-dhcp-google-ping-handoff-5g-cache-property-root`

## Gate Results

- `wlan0_seen`: `True` helper_invoked `True` helper_rc `0`
- `executor_result`: `connect-dhcp-ping-failed`
- `association_carrier`: `False` errno `110`
- `country`: `KR` driver_ioctl_rc `0` errno `0` readback `US` get_rc `0`
- `wpa_ctrl`: ready `False` surface `none` global_path `/tmp/a90-v231-746/root/dev/socket/wpa_wlan0` abstract `False` ping `none` interface_add_rc `0` interface_add `` after_add_ready `False` after_add_surface `` after_add_global `` after_add_ping `` country_rc `0` reply `` enable `` reassociate ``
- `wpa_ctrl_path`: dir `/cache/a90-wifi/sockets` interface `/cache/a90-wifi/sockets/wlan0`
- `supplicant`: launch `direct-interface-cache-ctrl` driver `nl80211` global_ctrl `none` alive_start `True` state_start `R` alive_after_carrier_wait `True` state_after_carrier_wait `R`
- `supplicant_proc_start`: comm `wpa_supplicant` exe `wpa_supplicant` has_wpa `True` has_helper `False` has_config `True`
- `supplicant_proc_start_runtime`: uid `1010?1010?1010?1010` gid `1010?1010?1010?1010` groups `1007 1010 1017 3003` wchan `0` fd_count `5` socket_fds `1` wpa_socket_fds `0` stdio_fds `2`
- `supplicant_proc_after_wait`: comm `wpa_supplicant` exe `wpa_supplicant` has_wpa `True` has_helper `False` has_config `True`
- `supplicant_proc_after_wait_runtime`: uid `1010?1010?1010?1010` gid `1010?1010?1010?1010` groups `1007 1010 1017 3003` wchan `0` fd_count `5` socket_fds `1` wpa_socket_fds `0` stdio_fds `2`
- `supplicant_log`: present `False` size `0` lines `0` ctrl `0` ctrl_err `0` nl80211 `0` scan `0` auth `0` assoc `0` connected `0` disconnected `0` fail `0`
- `supplicant_stdio`: present `True` size `0` lines `0` ctrl `0` ctrl_err `0` config_err `0` nl80211 `0` scan `0` auth `0` assoc `0` connected `0` disconnected `0` fail `0` usage `0` interface `0` socket `0` terminate `0` permission `0` samples `0` tail_samples `0` nonproperty_samples `0` sensitive_skipped `0`
- `dhcp_executed`: `False` dhcp_rc `-1`
- `external_ping_executed`: `False` target `google.com` rc `-1`
- `pre_state`: operstate `down` carrier `unreadable` flags `0x1002`
- `post_state`: operstate `down` carrier `unreadable` flags `0x1002`
- `staging`: property `True` helper `True` config `True` script `True` wait_complete `True`
- `property_root`: remote `/cache/a90-wifi-property-v2167/dev/__properties__` decision `v2167-wpa-supplicant-private-property-runtime-ready` files `22` property_info_size `7620`
- `no_raw`: `True` secret_values_logged `0`

## Redacted Supplicant Samples

- `none`

## Redacted Supplicant Tail Samples

- `none`

## Redacted Supplicant Non-Property Samples

- `none`

## Supplicant FD Samples

- `start_fd_00`: `0:/dev/null`
- `start_fd_01`: `1:/cache/a90-wifi/a90_supplicant_execns_stdio.log`
- `start_fd_02`: `2:/cache/a90-wifi/a90_supplicant_execns_stdio.log`
- `start_fd_03`: `3:socket:[29088]`
- `start_fd_04`: `4:/tmp/a90-v231-746/root/dev/hwbinder`
- `wait_fd_00`: `0:/dev/null`
- `wait_fd_01`: `1:/cache/a90-wifi/a90_supplicant_execns_stdio.log`
- `wait_fd_02`: `2:/cache/a90-wifi/a90_supplicant_execns_stdio.log`
- `wait_fd_03`: `3:socket:[29088]`
- `wait_fd_04`: `4:/tmp/a90-v231-746/root/dev/hwbinder`

## Staging

- `property_archive`: `tmp/wifi/v2167-connect-dhcp-google-ping-handoff-5g-cache-property-root/property-runtime-v2167.tgz` bytes `12721` chunks `12` staged `1`
- `helper_sha256`: `ef5706ff2ce3d25fbfbd8a0dbe3db99abbbf3c6c4746b80a8568a314ee9df69b` gzip_len `599560` chunks `521`
- `connect_config`: path `/cache/a90-wifi/v2167.conf` size `232` mode `600` security `wpa-psk` disabled_initially `0` raw_values_logged `0`

## Scope

- This V2167 unit stages a generated private property root at `/cache/a90-wifi-property-v2167/dev/__properties__` with the wpa_supplicant loader/log lookup keys, adds private `/dev/random` and `/dev/urandom`, launches `wpa_supplicant` root-start direct `-i wlan0 -D nl80211 -c <private-config> -O /cache/a90-wifi/sockets`, and records redacted first/tail/non-property stdio samples plus `/proc` exec-state counters.
- Allowed actions: start private Wi-Fi active-session surface, start `wpa_supplicant`, run DHCP, set temporary route/DNS, and ping `google.com`.
- Outputs are redacted: no SSID, PSK, BSSID, raw MAC, assigned IP, route, DNS, DHCP lease, or ping transcript is recorded in the report.
- Cleanup removes staged config/result/script artifacts and rollback returns to `v724`.

## Steps

- `pre-status` rc `0` ok `True` evidence `pre-status.stdout.txt`
- `pre-selftest` rc `0` ok `True` evidence `pre-selftest.stdout.txt`
- `set-sibling-fwssctl-flag` rc `0` ok `True` evidence `set-sibling-fwssctl-flag.stdout.txt`
- `test-flash-from-native` rc `0` ok `True` evidence `test-flash-from-native.stdout.txt`
- `property-runtime-stage-clean` rc `0` ok `True` evidence `property-runtime-stage-clean.stdout.txt`
- `property-runtime-stage-touch-b64` rc `0` ok `True` evidence `property-runtime-stage-touch-b64.stdout.txt`
- `property-runtime-stage-b64-chunks` rc `0` ok `True` evidence `property-runtime-stage-b64-chunks.stdout.txt`
- `property-runtime-stage-extract` rc `0` ok `True` evidence `property-runtime-stage-extract.stdout.txt`
- `host-build-execns-helper` rc `0` ok `True` evidence `host-build-execns-helper.stdout.txt`
- `execns-helper-verify-existing` rc `0` ok `True` evidence `execns-helper-verify-existing.stdout.txt`
- `execns-helper-stage-clean` rc `0` ok `True` evidence `execns-helper-stage-clean.stdout.txt`
- `execns-helper-stage-touch` rc `0` ok `True` evidence `execns-helper-stage-touch.stdout.txt`
- `execns-helper-stage-b64-chunks` rc `0` ok `True` evidence `execns-helper-stage-b64-chunks.stdout.txt`
- `execns-helper-stage-decode` rc `0` ok `True` evidence `execns-helper-stage-decode.stdout.txt`
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
- `post-rollback-connect-ping-cleanup` rc `1` ok `False` evidence `post-rollback-connect-ping-cleanup.stdout.txt`

## Cleanup

- `cache_artifacts_removed`: `False`
- Post-run manual cleanup removed `/cache/a90-wifi-property-v2167`; rollback baseline was re-verified as `v724` with selftest `fail=0`.
- Runner fix after this capture changes property-root cleanup from `rm -f` to `rm -rf` for the staged `/cache` directory.

## Safety

- Wi-Fi credentials are read only from environment variables and are not committed.
- Raw supplicant, DHCP, and ping stdout/stderr are redirected to `/dev/null` by the helper.
- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action is used.
