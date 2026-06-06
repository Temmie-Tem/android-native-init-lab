# Native Init V2167 Connect DHCP Google Ping Handoff

## Summary

- Cycle: `V2167`
- Run label: `v726-final-sha-smoke`
- Decision: `v2167-connect-dhcp-google-ping-hold-pass`
- Label: `connect-dhcp-google-ping-hold-pass`
- Pass: `True`
- Reason: native wlan0 associated, DHCP succeeded, google.com ping returned success, and hold stayed stable
- Evidence: `tmp/wifi/v2167-connect-dhcp-google-ping-handoff-v726-final-sha-smoke`
- QA hold config: sec `60` interval `30` reconnect_on_drop `True` force_power_on `False`
- Result source: `fast-upload` serial_attempts `0` result_left_on_device `False`
- Fast upload: ok `False` reason `upload-or-validation-failed` elapsed `66.176`
- Fast upload archive: `tmp/wifi/v2167-connect-dhcp-google-ping-handoff-v726-final-sha-smoke/fast-upload-v2167-1780765461.tgz` bytes `145225` receiver_bytes `145225` entries `7` secret_hits `[]` forbidden_entries `[]`

## Phase Timers

- `host_property_build` elapsed `0.028` ok `True` detail ``
- `host_property_archive` elapsed `0.016` ok `True` detail ``
- `host_standalone_wpa_bundle` elapsed `3.242` ok `True` detail ``
- `property_stage` elapsed `5.555` ok `True` detail ``
- `host_helper_build` elapsed `8.678` ok `True` detail ``
- `helper_stage` elapsed `0.545` ok `True` detail ``
- `strace_stage` elapsed `1.099` ok `True` detail ``
- `standalone_wpa_stage` elapsed `3.029` ok `True` detail ``
- `fast_transfer_close` elapsed `0.0` ok `True` detail ``
- `prestage_total` elapsed `18.906` ok `True` detail ``
- `connect_config_stage` elapsed `2.761` ok `True` detail ``
- `connect_window` elapsed `206.388` ok `True` detail ``
- `handoff_flash_test_rollback_total` elapsed `346.34` ok `True` detail ``
- `post_rollback_artifact_upload` elapsed `66.732` ok `True` detail ``

## Step Phase Summary

- `preflight_device` elapsed `1.57` steps `3` slow `set-sibling-fwssctl-flag:0.649s, pre-status:0.478s, pre-selftest:0.443s`
- `helper_stage` elapsed `10.801` steps `6` slow `host-build-execns-helper:8.581s, property-runtime-stage-extract:0.569s, property-runtime-fast-wget:0.558s`
- `connect_config_stage` elapsed `2.187` steps `5` slow `connect-config-clean:0.553s, connect-config-decode-redacted:0.549s, connect-config-mkdir:0.543s`
- `flash_total` elapsed `63.44` steps `1` slow `test-flash-from-native:63.44s`
- `connect_window` elapsed `205.374` steps `36` slow `connect-result-wait-polls:141.959s, connect-script-line-00:45.113s, connect-script-line-19:0.582s`
- `artifact_upload` elapsed `66.422` steps `14` slow `fast-upload-v2167-device-stream:65.216s, test-fast-evidence-device-stream:0.644s, test-fast-evidence-collector-fast-wget:0.562s`
- `rollback_flash_total` elapsed `64.419` steps `1` slow `rollback-from-native:64.419s`
- `rollback_status` elapsed `0.477` steps `1` slow `rollback-status:0.477s`
- `selftest` elapsed `0.914` steps `2` slow `test-selftest:0.476s, rollback-selftest:0.438s`
- `other` elapsed `9.041` steps `30` slow `standalone-wpa-stage-extract-verify:0.856s, standalone-wpa-fast-wget:0.666s, standalone-wpa-verify-existing:0.556s`

## Native Flash Subphases

- `test-flash-from-native.inspect_local_image` elapsed `0.068` ok `True`
- `test-flash-from-native.native_to_recovery` elapsed `0.303` ok `True`
- `test-flash-from-native.wait_recovery_adb` elapsed `27.131` ok `True`
- `test-flash-from-native.adb_push` elapsed `0.839` ok `True`
- `test-flash-from-native.remote_sha256` elapsed `0.099` ok `True`
- `test-flash-from-native.boot_dd_write` elapsed `0.436` ok `True`
- `test-flash-from-native.boot_readback_sha256` elapsed `0.35` ok `True`
- `test-flash-from-native.flash_boot_image` elapsed `1.724` ok `True`
- `test-flash-from-native.reboot_twrp_to_system` elapsed `2.733` ok `True`
- `test-flash-from-native.verify_native_init` elapsed `31.432` ok `True`
- `test-flash-from-native.total` elapsed `63.39` ok `True`
- `rollback-from-native.inspect_local_image` elapsed `0.061` ok `True`
- `rollback-from-native.native_to_recovery` elapsed `0.303` ok `True`
- `rollback-from-native.wait_recovery_adb` elapsed `28.13` ok `True`
- `rollback-from-native.adb_push` elapsed `0.838` ok `True`
- `rollback-from-native.remote_sha256` elapsed `0.099` ok `True`
- `rollback-from-native.boot_dd_write` elapsed `0.429` ok `True`
- `rollback-from-native.boot_readback_sha256` elapsed `0.226` ok `True`
- `rollback-from-native.flash_boot_image` elapsed `1.592` ok `True`
- `rollback-from-native.reboot_twrp_to_system` elapsed `2.847` ok `True`
- `rollback-from-native.verify_native_init` elapsed `31.435` ok `True`
- `rollback-from-native.total` elapsed `64.369` ok `True`

## Slowest Steps

- `connect-result-wait-polls` elapsed `141.959` ok `True` timeout `False`
- `fast-upload-v2167-device-stream` elapsed `65.216` ok `False` timeout `False`
- `rollback-from-native` elapsed `64.419` ok `True` timeout `False`
- `test-flash-from-native` elapsed `63.44` ok `True` timeout `False`
- `connect-script-line-00` elapsed `45.113` ok `False` timeout `False`
- `host-build-execns-helper` elapsed `8.581` ok `True` timeout `False`
- `standalone-wpa-stage-extract-verify` elapsed `0.856` ok `True` timeout `False`
- `standalone-wpa-fast-wget` elapsed `0.666` ok `True` timeout `False`
- `set-sibling-fwssctl-flag` elapsed `0.649` ok `True` timeout `False`
- `test-fast-evidence-device-stream` elapsed `0.644` ok `True` timeout `False`
- `connect-script-line-19` elapsed `0.582` ok `True` timeout `False`
- `property-runtime-stage-extract` elapsed `0.569` ok `True` timeout `False`

## Gate Results

- `wlan0_seen`: `True` helper_invoked `True` helper_rc `0`
- `executor_result`: `connect-dhcp-ping-pass`
- `association_carrier`: `True` errno `0`
- `country`: `KR` driver_ioctl_rc `0` errno `0` readback `US` get_rc `0`
- `wpa_ctrl`: ready `True` surface `interface` global_path `/tmp/a90-v231-781/root/dev/socket/wpa_wlan0` abstract `False` preclean `none` preclean_errno `0` ping `pong` interface_add_rc `0` interface_add `` after_add_ready `False` after_add_surface `` after_add_global `` after_add_ping `` country_rc `0` reply `unknown` enable `ok` reassociate `ok`
- `wpa_ctrl_path`: dir `/cache/a90-wifi/sockets` interface `/cache/a90-wifi/sockets/wlan0`
- `supplicant`: launch `native-direct-interface-config` driver `nl80211` global_ctrl `none` direct_iface `True` strace `False` strace_output `` android_socket_mode `disabled-native-global-ctrl` android_socket_fd `-2` android_socket_errno `0` alive_start `True` state_start `S` zombie_after_ctrl `False` alive_after_carrier_wait `True` state_after_carrier_wait `R`
- `supplicant_preexec`: path `/cache/a90-wifi/wpa-standalone/wpa_supplicant-a90.sh` path_x `True` path_errno `0` loader_x `True` loader_errno `0` binary_x `True` binary_errno `0` busybox_x `True` busybox_errno `0` urandom_r `True` urandom_errno `0` urandom_mode `666` urandom_rdev `1:9`
- `standalone_wpa`: enabled `1` staged `True` reason `ok` wrapper `/cache/a90-wifi/wpa-standalone/wpa_supplicant-a90.sh` packages `17` version_rc `0` version `Could_not_open_/dev/urandom.`
- `supplicant_hidl`: hwservicemanager_started `False` mode `not-needed` pid `-1` add_rc `0` service_found `False` descriptor `` instance `` transaction_ok `False` status `` iface_handle `False` result `skipped` reason `manual-hidl-add-disabled-for-direct-interface-route` after_add_fd `4` after_add_netlink `0` after_add_genl `0`
- `supplicant_hidl_vendor`: service_found `False` descriptor `` instance ``
- `supplicant_proc_start`: comm `a90_strace_v216` exe `a90_strace_v2167` has_wpa `True` has_helper `False` has_config `True`
- `supplicant_proc_start_runtime`: uid `0?0?0?0` gid `0?0?0?0` groups `` wchan `do_wait` syscall `260 0xffffffffffffffff 0x7fedac6df4 0x40000000 0x0 0x0 0x0 0x7fedac6da0 0x4e5688` stack `[<0000000000000000>] __switch_to+0x10c/0x120` fd_count `4` socket_fds `0` netlink_fds `0` generic_netlink_fds `0` netlink_miss `0` wpa_socket_fds `0` stdio_fds `1`
- `supplicant_proc_after_wait`: comm `a90_strace_v216` exe `a90_strace_v2167` has_wpa `True` has_helper `False` has_config `True`
- `supplicant_proc_after_wait_runtime`: uid `0?0?0?0` gid `0?0?0?0` groups `` wchan `0` syscall `running` stack `[<0000000000000000>] __switch_to+0x10c/0x120` fd_count `4` socket_fds `0` netlink_fds `0` generic_netlink_fds `0` netlink_miss `0` wpa_socket_fds `0` stdio_fds `1`
- `supplicant_log`: present `False` size `0` lines `0` ctrl `0` ctrl_err `0` nl80211 `0` scan `0` auth `0` assoc `0` connected `0` disconnected `0` fail `0` permission `0` avc `0` samples `0` tail_samples `0` nonproperty_samples `0` sensitive_skipped `0`
- `supplicant_stdio`: present `True` size `73030` lines `901` ctrl `16` ctrl_err `0` config_err `1` nl80211 `295` scan `40` auth `17` assoc `22` connected `4` disconnected `3` fail `2` usage `0` interface `24` socket `15` terminate `0` permission `0` avc `0` samples `24` tail_samples `24` nonproperty_samples `24` sensitive_skipped `90`
- `logdw_sink`: started `True` errno `0` datagrams `20` bytes `1555` wpa `0` supplicant `0` nl80211 `6` ctrl `0` interface `0` fail `6` permission `0` hidl `0` service_manager `0` samples `12` sensitive_skipped `0` drain_errno `0`
- `kmsg_stream`: started `True` start_errno `0` present `True` size `49702` lines `585` permission `0` avc `0` nl80211 `0` auth `3` assoc `6` fail `11` sensitive_skipped `18` cleanup_exit `-1` signal `15` timeout `False`
- `dhcp_executed`: `True` dhcp_rc `0` resolv_present `True` resolv_errno `0` resolv_size `48` nameservers `2`
- `external_ping_executed`: `True` target `google.com` rc `0` classifier `icmp-reply` output_present `True` output_errno `0` bytes_from `True` bad_address `False` unknown_host `False` net_unreach `False` sendto `False` zero_recv `False` loss100 `False`
- `force_power_on`: enabled `False` executed `False` reason `disabled` class `->` class_rc `0` class_errno `0` device `->` device_rc `0` device_errno `0`
- `modem_holder`: requested `False` enabled `False` started `False` start_attempted `False` opened `False` open_errno `0` pid `0` stop_attempted `False` reaped `False` postflight_safe `False` esoc0_attempt `False` esoc_attempt `False` forced_rc1 `False`
- `hold`: enabled `True` executed `True` requested_sec `60` interval_sec `30` pass `True` reason `hold-carrier-and-ping-stable` samples `2` carrier_up `2` carrier_down `0` host_ping_success `2` host_ping_fail `0` ip_ping_success `2` ip_ping_fail `0` reconnect_on_drop `True` reconnect_attempts `0` reconnect_success `0` first_fail_sample `-1` first_fail_errno `0` first_fail_ping_rc `0`
- `hold_path_diag`: gateway_ping `2/2` gateway_fail `0` route_default `2` route_gateway `2` arp_before `2/2` arp_after `2/2`

## Hold Sample Diagnostics

- `hold_sample_00` t_ms `30000` carrier `True` route `True/True` err `0` arp `True:True->True:True` gw `icmp-reply` ip `icmp-reply` host `icmp-reply` stats `True/True` pkt_delta rx/tx `5/5` err_drop `0/0/0/0` wpa `COMPLETED` rc `0` freq `5745` sig `-49/866` rc `0` power `auto/auto/unsupported` owners cnss/pm/per/wifi/ipacm `2/1/0/1/0` fds ipa/subsys_modem `0/3` icnss `unsupported/unsupported` wlanpd `False:missing:missing` modem `True:ONLINE`
- `hold_sample_01` t_ms `60411` carrier `True` route `True/True` err `0` arp `True:True->True:True` gw `icmp-reply` ip `icmp-reply` host `icmp-reply` stats `True/True` pkt_delta rx/tx `5/5` err_drop `0/0/0/0` wpa `COMPLETED` rc `0` freq `5745` sig `-56/780` rc `0` power `auto/auto/unsupported` owners cnss/pm/per/wifi/ipacm `2/1/0/1/0` fds ipa/subsys_modem `0/3` icnss `unsupported/unsupported` wlanpd `False:missing:missing` modem `True:ONLINE`

## Interface State

- `pre_state`: operstate `down` carrier `unreadable` flags `0x1002`
- `post_state`: operstate `down` carrier `unreadable` flags `0x1002`
- `staging`: property `True` helper `True` standalone_wpa `True` config `True` script `True` wait_complete `True`
- `property_root`: remote `/cache/a90-wifi-property-v2167/dev/__properties__` decision `v2167-wpa-supplicant-private-property-runtime-ready` files `22` property_info_size `7620`
- `no_raw`: `True` secret_values_logged `0`

## Redacted Supplicant Samples

- `supplicant_log`: `none`

## Redacted Supplicant Stdio Samples

- `sample_00`: `wifi_connect_ping.supplicant_preexec.path=/cache/a90-wifi/wpa-standalone/wpa_supplicant-a90.sh`
- `sample_01`: `wifi_connect_ping.supplicant_preexec.path_access_x=1`
- `sample_02`: `wifi_connect_ping.supplicant_preexec.path_access_errno=0`
- `sample_03`: `wifi_connect_ping.supplicant_preexec.loader_access_x=1`
- `sample_04`: `wifi_connect_ping.supplicant_preexec.loader_access_errno=0`
- `sample_05`: `wifi_connect_ping.supplicant_preexec.binary_access_x=1`
- `sample_06`: `wifi_connect_ping.supplicant_preexec.binary_access_errno=0`
- `sample_07`: `wifi_connect_ping.supplicant_preexec.busybox_access_x=1`
- `sample_08`: `wifi_connect_ping.supplicant_preexec.busybox_access_errno=0`
- `sample_09`: `wifi_connect_ping.supplicant_preexec.dev_urandom_access_r=1`
- `sample_10`: `wifi_connect_ping.supplicant_preexec.dev_urandom_access_errno=0`
- `sample_11`: `wifi_connect_ping.supplicant_preexec.dev_urandom.mode=666`
- `sample_12`: `wifi_connect_ping.supplicant_preexec.dev_urandom.rdev_major=1`
- `sample_13`: `wifi_connect_ping.supplicant_preexec.dev_urandom.rdev_minor=9`
- `sample_14`: `wifi_connect_ping.supplicant_identity.start_uid=0`
- `sample_15`: `wifi_connect_ping.supplicant_identity.start_gid=0`
- `sample_16`: `wifi_connect_ping.supplicant_identity.android_init_parity=root-start-direct-interface-self-drop`
- `sample_17`: `wifi_connect_ping.supplicant_strace.enabled=1`
- `sample_18`: `wifi_connect_ping.supplicant_strace.path=/cache/a90-wifi/a90_strace_v2167`
- `sample_19`: `wifi_connect_ping.supplicant_strace.output=/cache/a90-wifi/a90_supplicant_strace`
- `sample_20`: `context.proc_self_exe.readlink=/cache/bin/a90_android_execns_probe_v2167`
- `sample_21`: `wifi_connect_ping.supplicant.selinux_context_mode=auto`
- `sample_22`: `wifi_connect_ping.supplicant.selinux_exec.target_context=u:r:hal_wifi_supplicant_default:s0`
- `sample_23`: `wifi_connect_ping.supplicant.selinux_exec.ok=1`

## Redacted Supplicant Tail Samples

- `tail_00`: `1518777826.058664: nl80211: KEY_SEQ - hexdump(len=6): d9 03 09 00 00 00`
- `tail_01`: `1518777826.062337: wlan0: Radio work 'connect'@0x5570a55610 done in 0.199716 seconds`
- `tail_02`: `1518777826.062776: wlan0: radio_work_free('connect'@0x5570a55610): num_active_works --> 0`
- `tail_03`: `1518777826.063666: nl80211: Set wlan0 operstate 0->1 (UP)`
- `tail_04`: `1518777826.075633: nl80211: Set rekey offload`
- `tail_05`: `1518777826.078986: nl80211: Event message available`
- `tail_06`: `1518777826.083052: nl80211: Drv Event 103 (NL80211_CMD_VENDOR) received for wlan0`
- `tail_07`: `1518777826.083242: nl80211: Vendor event: wiphy=0 vendor_id=0x1374 subcmd=165`
- `tail_08`: `1518777826.083421: nl80211: Vendor data - hexdump(len=48): 30 00 01 00 2c 00 00 00 08 00 01 00 00 00 00 00 08 00 02 00 02 00 00 00 18 00 03 00 14 00 00 00 08 00 01 00 09 00 00 00 08 00 02 00 71 16 00 00`
- `tail_09`: `1518777826.086197: nl80211: Ignore unsupported QCA vendor event 165`
- `tail_10`: `1518777861.488253: CTRL-DEBUG: ctrl_sock-sendto: sock=12 sndbuf=229376 outq=0 send_len=304`
- `tail_11`: `1518777861.489129: Control interface recv command from: \x00a90-wpa-781-182221`
- `tail_12`: `1518777861.489330: wlan0: Control interface command 'SIGNAL_POLL'`
- `tail_13`: `1518777861.512129: CTRL-DEBUG: ctrl_sock-sendto: sock=12 sndbuf=229376 outq=0 send_len=62`
- `tail_14`: `1518777861.513569: Control interface recv command from: \x00a90-wpa-781-182245`
- `tail_15`: `1518777861.513731: wlan0: Control interface command 'DRIVER GETPOWER'`
- `tail_16`: `1518777861.514345: CTRL-DEBUG: ctrl_sock-sendto: sock=12 sndbuf=229376 outq=0 send_len=16`
- `tail_17`: `1518777891.898662: CTRL-DEBUG: ctrl_sock-sendto: sock=12 sndbuf=229376 outq=0 send_len=304`
- `tail_18`: `1518777891.899506: Control interface recv command from: \x00a90-wpa-781-212631`
- `tail_19`: `1518777891.899712: wlan0: Control interface command 'SIGNAL_POLL'`
- `tail_20`: `1518777891.929745: CTRL-DEBUG: ctrl_sock-sendto: sock=12 sndbuf=229376 outq=0 send_len=62`
- `tail_21`: `1518777891.930587: Control interface recv command from: \x00a90-wpa-781-212662`
- `tail_22`: `1518777891.930747: wlan0: Control interface command 'DRIVER GETPOWER'`
- `tail_23`: `1518777891.931354: CTRL-DEBUG: ctrl_sock-sendto: sock=12 sndbuf=229376 outq=0 send_len=16`

## Redacted Supplicant Non-Property Samples

- `nonproperty_00`: `wifi_connect_ping.supplicant_preexec.path=/cache/a90-wifi/wpa-standalone/wpa_supplicant-a90.sh`
- `nonproperty_01`: `wifi_connect_ping.supplicant_preexec.path_access_x=1`
- `nonproperty_02`: `wifi_connect_ping.supplicant_preexec.path_access_errno=0`
- `nonproperty_03`: `wifi_connect_ping.supplicant_preexec.loader_access_x=1`
- `nonproperty_04`: `wifi_connect_ping.supplicant_preexec.loader_access_errno=0`
- `nonproperty_05`: `wifi_connect_ping.supplicant_preexec.binary_access_x=1`
- `nonproperty_06`: `wifi_connect_ping.supplicant_preexec.binary_access_errno=0`
- `nonproperty_07`: `wifi_connect_ping.supplicant_preexec.busybox_access_x=1`
- `nonproperty_08`: `wifi_connect_ping.supplicant_preexec.busybox_access_errno=0`
- `nonproperty_09`: `wifi_connect_ping.supplicant_preexec.dev_urandom_access_r=1`
- `nonproperty_10`: `wifi_connect_ping.supplicant_preexec.dev_urandom_access_errno=0`
- `nonproperty_11`: `wifi_connect_ping.supplicant_preexec.dev_urandom.mode=666`
- `nonproperty_12`: `wifi_connect_ping.supplicant_preexec.dev_urandom.rdev_major=1`
- `nonproperty_13`: `wifi_connect_ping.supplicant_preexec.dev_urandom.rdev_minor=9`
- `nonproperty_14`: `wifi_connect_ping.supplicant_identity.start_uid=0`
- `nonproperty_15`: `wifi_connect_ping.supplicant_identity.start_gid=0`
- `nonproperty_16`: `wifi_connect_ping.supplicant_identity.android_init_parity=root-start-direct-interface-self-drop`
- `nonproperty_17`: `wifi_connect_ping.supplicant_strace.enabled=1`
- `nonproperty_18`: `wifi_connect_ping.supplicant_strace.path=/cache/a90-wifi/a90_strace_v2167`
- `nonproperty_19`: `wifi_connect_ping.supplicant_strace.output=/cache/a90-wifi/a90_supplicant_strace`
- `nonproperty_20`: `context.proc_self_exe.readlink=/cache/bin/a90_android_execns_probe_v2167`
- `nonproperty_21`: `wifi_connect_ping.supplicant.selinux_context_mode=auto`
- `nonproperty_22`: `wifi_connect_ping.supplicant.selinux_exec.target_context=u:r:hal_wifi_supplicant_default:s0`
- `nonproperty_23`: `wifi_connect_ping.supplicant.selinux_exec.ok=1`

## Redacted Kernel Stream Samples

- `logdw_sample_00`: `Z 5 cnss-daemon nl80211 response handler invoked`
- `logdw_sample_01`: `ZM 5 cnss-daemon nl80211_response_handler: cmd 103, vendorID 4980, subcmd 106  received`
- `logdw_sample_02`: `Z [ CNSS failed to open file a+ mode or file size 0 is less than max_file_size 31457280`
- `logdw_sample_03`: `Zs CNSS Failed to open file /data/vendor/log/wifi/host_driver_logs_current.txt: 2`
- `logdw_sample_04`: `Zp 11 cnss-daemon nl80211 response handler invoked`
- `logdw_sample_05`: `Z% 11 cnss-daemon nl80211_response_handler: cmd 103, vendorID 4980, subcmd 107  received`
- `logdw_sample_06`: `Z cnss-daemon nl80211 response handler invoked`
- `logdw_sample_07`: `Z@! cnss-daemon nl80211_response_handler: cmd 103, vendorID 4980, subcmd 165  received`
- `logdw_sample_08`: `Z CNSS failed to open file a+ mode or file size 0 is less than max_file_size 31457280`
- `logdw_sample_09`: `Z CNSS Failed to open file /data/vendor/log/wifi/host_driver_logs_current.txt: 2`
- `logdw_sample_10`: `Z{ CNSS failed to open file a+ mode or file size 0 is less than max_file_size 31457280`
- `logdw_sample_11`: `Z, CNSS Failed to open file /data/vendor/log/wifi/host_driver_logs_current.txt: 2`
- `kmsg_sample_00`: `4,4437,146706020,-; scheduler_thread+0x1b4/0x5a8`
- `kmsg_sample_01`: `4,4438,146706032,-; kthread+0x120/0x138`
- `kmsg_sample_02`: `4,4505,146706833,-; scheduler_thread+0x1b4/0x5a8`
- `kmsg_sample_03`: `4,4506,146706843,-; kthread+0x120/0x138`
- `kmsg_sample_04`: `4,4517,146707014,-;WARNING: CPU: 1 PID: 706 at drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0/components/ipa/core/src/wlan_ipa_core.c:1493 wlan_ipa_cleanup_iface+0x2e8/0x4a8`
- `kmsg_sample_05`: `4,4573,146707734,-; scheduler_thread+0x1b4/0x5a8`
- `kmsg_sample_06`: `4,4574,146707745,-; kthread+0x120/0x138`
- `kmsg_sample_07`: `3,4577,146707788,-;[schedu][0xbccd71a0][10:43:45.975337] wlan: [706:E:IPA] __wlan_ipa_wlan_evt: 2236: wlan_ipa_setup_iface failed 4294967282`
- `kmsg_sample_08`: `6,4599,146796557,-;IPv6: ADDRCONF(NETDEV_CHANGE): wlan0: link becomes ready`
- `kmsg_sample_09`: `6,4618,151614022,-;max77705_fg_periodic_read: skip old(1) current(151)`
- `kmsg_sample_10`: `6,4619,151615403,-;max77705_fg_read_qh : QH(4779000)`
- `kmsg_sample_11`: `7,4621,151615659,-;max77705_fg_read_current: current=0mA`
- `kmsg_sample_12`: `7,4622,151616122,-;max77705_fg_read_avg_current: avg_current=0mA`
- `kmsg_sample_13`: `6,4623,151616358,-;max77705_fg_read_isys_avg: isys_avg_current=721mA`
- `kmsg_sample_14`: `6,4624,151616599,-;max77705_fg_read_isys: isys_current=936mA`
- `kmsg_sample_15`: `6,4626,151632072,-;max77705_fg_read_vcell: VCELL(4326)mV, data(0xd84e)`
- `kmsg_sample_16`: `7,4627,151632536,-;max77705_fg_read_avg_current: avg_current=0mA`
- `kmsg_sample_17`: `6,4644,151637311,-;sec_bat_get_property: input current(1500mA), cable type(5), slow-charging mode(1)`
- `kmsg_sample_18`: `6,4645,151637329,-;sec_bat_get_property cable type = 5 sleep_mode = 0`
- `kmsg_sample_19`: `7,4646,151637575,-;max77705_fg_read_current: current=0mA`
- `kmsg_sample_20`: `7,4647,151638035,-;max77705_fg_read_avg_current: avg_current=0mA`
- `kmsg_sample_21`: `14,4662,155288993,-;rmt_storage:INFO:rmt_storage_client_thread: Calling Write [offset=0, size=2097152, req_h 0x9, wr_count 1] for /boot/modem_fs2!`
- `kmsg_sample_22`: `14,4663,155336566,-;rmt_storage:INFO:rmt_storage_client_thread: Done Write (bytes = 2097152, req_h 0x9, wr_count 1) for /boot/modem_fs2!`
- `kmsg_sample_23`: `3,4679,162560063,-;sec_debug_partition:debug_partition_operation() filp_open failed: -2[81]`
- `kmsg_tail_00`: `3,4679,162560063,-;sec_debug_partition:debug_partition_operation() filp_open failed: -2[81]`
- `kmsg_tail_01`: `6,4713,181638407,-;max77705_fg_periodic_read: skip old(1) current(181)`
- `kmsg_tail_02`: `6,4714,181639782,-;max77705_fg_read_qh : QH(4779000)`
- `kmsg_tail_03`: `7,4716,181640077,-;max77705_fg_read_current: current=-9mA`
- `kmsg_tail_04`: `7,4717,181640560,-;max77705_fg_read_avg_current: avg_current=0mA`
- `kmsg_tail_05`: `7,4719,181657729,-;max77705_fg_read_avg_current: avg_current=0mA`
- `kmsg_tail_06`: `6,4736,181662502,-;sec_bat_get_property: input current(1500mA), cable type(5), slow-charging mode(1)`
- `kmsg_tail_07`: `6,4737,181662520,-;sec_bat_get_property cable type = 5 sleep_mode = 0`
- `kmsg_tail_08`: `7,4738,181662765,-;max77705_fg_read_current: current=-9mA`
- `kmsg_tail_09`: `7,4739,181663225,-;max77705_fg_read_avg_current: avg_current=0mA`
- `kmsg_tail_10`: `3,4754,182377520,-;EXT4-fs (sda29): errors=remount-ro for active namespaces on umount 2`
- `kmsg_tail_11`: `6,4787,197601833,-;max77705_muic_print_reg_log fail to read uiadc(0), chgtyp(0), spr(0), dcdtmo(0), vbadc(0), vbusdet(0), unknown(0)`
- `kmsg_tail_12`: `3,4801,202560056,-;sec_debug_partition:debug_partition_operation() filp_open failed: -2[101]`
- `kmsg_tail_13`: `6,4815,211931454,-;max77705_fg_read_qh : QH(4779000)`
- `kmsg_tail_14`: `7,4817,211931710,-;max77705_fg_read_current: current=-8mA`
- `kmsg_tail_15`: `7,4818,211932170,-;max77705_fg_read_avg_current: avg_current=0mA`
- `kmsg_tail_16`: `6,4819,211932406,-;max77705_fg_read_isys_avg: isys_avg_current=892mA`
- `kmsg_tail_17`: `6,4820,211932645,-;max77705_fg_read_isys: isys_current=915mA`
- `kmsg_tail_18`: `6,4822,211947735,-;max77705_fg_read_vcell: VCELL(4328)mV, data(0xd86a)`
- `kmsg_tail_19`: `7,4823,211948199,-;max77705_fg_read_avg_current: avg_current=0mA`
- `kmsg_tail_20`: `6,4840,211952932,-;sec_bat_get_property: input current(1500mA), cable type(5), slow-charging mode(1)`
- `kmsg_tail_21`: `6,4841,211952951,-;sec_bat_get_property cable type = 5 sleep_mode = 0`
- `kmsg_tail_22`: `7,4842,211953197,-;max77705_fg_read_current: current=-8mA`
- `kmsg_tail_23`: `7,4843,211953654,-;max77705_fg_read_avg_current: avg_current=0mA`

## Supplicant FD Samples

- `start_fd_00`: `2:/cache/a90-wifi/a90_supplicant_execns_stdio.log`
- `wait_fd_00`: `2:/cache/a90-wifi/a90_supplicant_execns_stdio.log`

## Staging

- `property_archive`: `tmp/wifi/v2167-connect-dhcp-google-ping-handoff-v726-final-sha-smoke/property-runtime-v2167.tgz` bytes `12741` chunks `12` staged `1` method `ncm-wget` fast `1` elapsed `4.431`
- `helper_sha256`: `fc538747af01f1b572211594bc501deacfe36fd9446bb6c70ba2be51cb9ddd02` gzip_len `616652` chunks `536` method `` fast `` elapsed ``
- `strace_stage`: ok `1` reason `already-present` fast `` elapsed ``
- `standalone_wpa_archive`: ok `True` bytes `8179705` sha `71e4a9d74b7cdaef0d8d71bb56ab8d9c5c4ff490a1a3f603a8775648f8791d81` packages `17` staged `1` fast `1` elapsed `0.667`
- `connect_config`: path `/cache/a90-wifi/v2167.conf` size `232` mode `600` security `wpa-psk` disabled_initially `0` raw_values_logged `0`

## Scope

- This V2167 unit stages a generated private property root at `/cache/a90-wifi-property-v2167/dev/__properties__` with the wpa_supplicant loader/log lookup keys, adds private `/dev/random` and `/dev/urandom`, creates `/dev/socket/logdw`, launches `wpa_supplicant` direct as `-dd -i wlan0 -D nl80211 -c <config> -O /cache/a90-wifi/sockets -t`, and observes carrier/DHCP/ping. It records redacted supplicant/logdw/kmsg samples plus `/proc` fd/netlink/syscall counters. This target supplicant does not support `-f`, so stdout/stderr plus logdw are the diagnostic logs.
- Allowed actions: start private Wi-Fi active-session surface, start `wpa_supplicant`, run DHCP, set temporary route/DNS, and run bounded gateway/IP/hostname ping probes.
- Outputs are redacted: no SSID, PSK, BSSID, raw MAC, assigned IP, route, DNS, DHCP lease, or ping transcript is recorded in the report.
- Cleanup removes staged config/result/script artifacts and rollback returns to `v725-fasttransport`.

## Steps

- `pre-status` rc `0` ok `True` evidence `pre-status.stdout.txt`
- `pre-selftest` rc `0` ok `True` evidence `pre-selftest.stdout.txt`
- `set-sibling-fwssctl-flag` rc `0` ok `True` evidence `set-sibling-fwssctl-flag.stdout.txt`
- `test-flash-from-native` rc `0` ok `True` evidence `test-flash-from-native.stdout.txt`
- `standalone-wpa-host-bundle` rc `0` ok `True` evidence `standalone-wpa-host-bundle.stdout.txt`
- `property-runtime-stage-clean` rc `0` ok `True` evidence `property-runtime-stage-clean.stdout.txt`
- `fast-transfer-host-net-before` rc `0` ok `True` evidence `fast-transfer-host-net-before.stdout.txt`
- `fast-transfer-host-nm-linklocal-repair` rc `0` ok `True` evidence `fast-transfer-host-nm-linklocal-repair.stdout.txt`
- `fast-transfer-device-host-probe` rc `0` ok `True` evidence `fast-transfer-device-host-probe.stdout.txt`
- `fast-transfer-device-host-probe-result` rc `0` ok `True` evidence `fast-transfer-device-host-probe-result.stdout.txt`
- `property-runtime-fast-wget` rc `0` ok `True` evidence `property-runtime-fast-wget.stdout.txt`
- `property-runtime-fast-wget-result` rc `0` ok `True` evidence `property-runtime-fast-wget-result.stdout.txt`
- `property-runtime-stage-extract` rc `0` ok `True` evidence `property-runtime-stage-extract.stdout.txt`
- `host-build-execns-helper` rc `0` ok `True` evidence `host-build-execns-helper.stdout.txt`
- `execns-helper-verify-existing` rc `0` ok `True` evidence `execns-helper-verify-existing.stdout.txt`
- `strace-helper-prepare-cache-dir` rc `0` ok `True` evidence `strace-helper-prepare-cache-dir.stdout.txt`
- `strace-helper-verify-existing` rc `0` ok `True` evidence `strace-helper-verify-existing.stdout.txt`
- `standalone-wpa-prepare-cache-dir` rc `0` ok `True` evidence `standalone-wpa-prepare-cache-dir.stdout.txt`
- `standalone-wpa-verify-existing` rc `0` ok `True` evidence `standalone-wpa-verify-existing.stdout.txt`
- `standalone-wpa-fast-wget` rc `0` ok `True` evidence `standalone-wpa-fast-wget.stdout.txt`
- `standalone-wpa-fast-wget-result` rc `0` ok `True` evidence `standalone-wpa-fast-wget-result.stdout.txt`
- `standalone-wpa-stage-extract-verify` rc `0` ok `True` evidence `standalone-wpa-stage-extract-verify.stdout.txt`
- `connect-config-mkdir` rc `0` ok `True` evidence `connect-config-mkdir.stdout.txt`
- `connect-config-clean` rc `0` ok `True` evidence `connect-config-clean.stdout.txt`
- `connect-config-touch-b64` rc `0` ok `True` evidence `connect-config-touch-b64.stdout.txt`
- `connect-config-write-redacted` rc `0` ok `True` evidence `connect-config-write-redacted.stdout.txt`
- `connect-config-decode-redacted` rc `0` ok `True` evidence `connect-config-decode-redacted.stdout.txt`
- `connect-script-clean-hide-on-busy` rc `0` ok `True` evidence `connect-script-clean-hide-on-busy.stdout.txt`
- `connect-script-clean` rc `0` ok `True` evidence `connect-script-clean.stdout.txt`
- `connect-script-touch` rc `0` ok `True` evidence `connect-script-touch.stdout.txt`
- `connect-script-line-00` rc `1` ok `False` evidence `connect-script-line-00.stdout.txt`
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
- `connect-script-line-25` rc `0` ok `True` evidence `connect-script-line-25.stdout.txt`
- `connect-script-line-26` rc `0` ok `True` evidence `connect-script-line-26.stdout.txt`
- `connect-script-line-27` rc `0` ok `True` evidence `connect-script-line-27.stdout.txt`
- `connect-script-line-28` rc `0` ok `True` evidence `connect-script-line-28.stdout.txt`
- `connect-script-validate` rc `0` ok `True` evidence `connect-script-validate.stdout.txt`
- `connect-script-chmod` rc `0` ok `True` evidence `connect-script-chmod.stdout.txt`
- `connect-script-start` rc `0` ok `True` evidence `connect-script-start.stdout.txt`
- `connect-result-wait-polls` rc `0` ok `True` evidence `connect-result-wait-polls.txt`
- `test-helper-wait-polls` rc `0` ok `True` evidence `test-helper-wait-polls.txt`
- `fast-transfer-host-net-before` rc `0` ok `True` evidence `fast-transfer-host-net-before.stdout.txt`
- `fast-transfer-host-nm-linklocal-repair` rc `0` ok `True` evidence `fast-transfer-host-nm-linklocal-repair.stdout.txt`
- `fast-transfer-device-host-probe` rc `0` ok `True` evidence `fast-transfer-device-host-probe.stdout.txt`
- `fast-transfer-device-host-probe-result` rc `0` ok `True` evidence `fast-transfer-device-host-probe-result.stdout.txt`
- `test-fast-evidence-collector-fast-wget` rc `0` ok `True` evidence `test-fast-evidence-collector-fast-wget.stdout.txt`
- `test-fast-evidence-collector-fast-wget-result` rc `0` ok `True` evidence `test-fast-evidence-collector-fast-wget-result.stdout.txt`
- `test-fast-evidence-device-stream` rc `0` ok `True` evidence `test-fast-evidence-device-stream.stdout.txt`
- `test-sys-wifi-mac-node` rc `0` ok `True` evidence `test-sys-wifi-mac-node.stdout.txt`
- `test-dmesg-full` rc `0` ok `True` evidence `test-dmesg-full.stdout.txt`
- `test-supplicant-strace` rc `0` ok `True` evidence `test-supplicant-strace.stdout.txt`
- `test-icnss-stats` rc `0` ok `True` evidence `test-icnss-stats.stdout.txt`
- `test-dmesg-wifi-filter` rc `0` ok `True` evidence `test-dmesg-wifi-filter.stdout.txt`
- `test-wlan0-ifconfig` rc `0` ok `True` evidence `test-wlan0-ifconfig.stdout.txt`
- `test-icnss-debugfs-ls` rc `0` ok `True` evidence `test-icnss-debugfs-ls.stdout.txt`
- `test-wlan0-state` rc `0` ok `True` evidence `test-wlan0-state.stdout.txt`
- `test-fast-evidence-upload-result` rc `0` ok `True` evidence `test-fast-evidence-upload-result.stdout.txt`
- `test-version` rc `0` ok `True` evidence `test-version.stdout.txt`
- `test-status` rc `0` ok `True` evidence `test-status.stdout.txt`
- `test-selftest` rc `0` ok `True` evidence `test-selftest.stdout.txt`
- `test-bootstatus` rc `0` ok `True` evidence `test-bootstatus.stdout.txt`
- `test-v726-log` rc `0` ok `True` evidence `test-v726-log.stdout.txt`
- `test-v726-summary` rc `0` ok `True` evidence `test-v726-summary.stdout.txt`
- `test-v726-helper-result` rc `1` ok `False` evidence `test-v726-helper-result.stdout.txt`
- `rollback-from-native` rc `0` ok `True` evidence `rollback-from-native.stdout.txt`
- `rollback-status` rc `0` ok `True` evidence `rollback-status.stdout.txt`
- `rollback-selftest` rc `0` ok `True` evidence `rollback-selftest.stdout.txt`
- `fast-transfer-host-net-before` rc `0` ok `True` evidence `fast-transfer-host-net-before.stdout.txt`
- `fast-transfer-host-net-existing` rc `0` ok `True` evidence `fast-transfer-host-net-existing.stdout.txt`
- `fast-transfer-device-host-probe-hide-on-busy` rc `0` ok `True` evidence `fast-transfer-device-host-probe-hide-on-busy.stdout.txt`
- `fast-transfer-device-host-probe` rc `0` ok `True` evidence `fast-transfer-device-host-probe.stdout.txt`
- `fast-transfer-device-host-probe-result` rc `0` ok `True` evidence `fast-transfer-device-host-probe-result.stdout.txt`
- `fast-upload-v2167-device-stream` rc `1` ok `False` evidence `fast-upload-v2167-device-stream.stdout.txt`
- `fast-upload-v2167-result` rc `1` ok `False` evidence `fast-upload-v2167-result.stdout.txt`
- `post-rollback-connect-ping-result-fast-upload` rc `0` ok `True` evidence `post-rollback-connect-ping-result-fast-upload.stdout.txt`
- `post-rollback-connect-ping-cleanup` rc `0` ok `True` evidence `post-rollback-connect-ping-cleanup.stdout.txt`

## Cleanup

- `cache_artifacts_removed`: `True`
- `cleanup_skipped_reason`: ``

## Safety

- Wi-Fi credentials are read only from environment variables and are not committed.
- Raw supplicant, kmsg, DHCP, and ping stdout/stderr are summarized with redacted samples; raw supplicant/kmsg files are removed during helper cleanup.
- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action is used.
