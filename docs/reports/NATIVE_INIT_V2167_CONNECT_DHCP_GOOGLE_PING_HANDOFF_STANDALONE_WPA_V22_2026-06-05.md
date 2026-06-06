# Native Init V2167 Connect DHCP Google Ping Handoff

## Summary

- Cycle: `V2167`
- Run label: `standalone-wpa-v22`
- Decision: `v2167-connect-dhcp-google-ping-pass`
- Label: `connect-dhcp-google-ping-pass`
- Pass: `True`
- Reason: native wlan0 associated, DHCP succeeded, and google.com ping returned success
- Evidence: `tmp/wifi/v2167-connect-dhcp-google-ping-handoff-standalone-wpa-v22`
- Result source: `fast-upload` serial_attempts `0` result_left_on_device `False`
- Fast upload: ok `True` reason `ok` elapsed `14.837`
- Fast upload archive: `tmp/wifi/v2167-connect-dhcp-google-ping-handoff-standalone-wpa-v22/fast-upload-v2167-1780726505.tgz` bytes `137822` receiver_bytes `137822` entries `6` secret_hits `[]` forbidden_entries `[]`

## Phase Timers

- `host_property_build` elapsed `0.027` ok `True` detail ``
- `host_property_archive` elapsed `0.018` ok `True` detail ``
- `host_standalone_wpa_bundle` elapsed `2.971` ok `True` detail ``
- `property_stage` elapsed `4.894` ok `True` detail ``
- `host_helper_build` elapsed `7.275` ok `True` detail ``
- `helper_stage` elapsed `2.275` ok `True` detail ``
- `strace_stage` elapsed `1.084` ok `True` detail ``
- `standalone_wpa_stage` elapsed `2.91` ok `True` detail ``
- `fast_transfer_close` elapsed `0.0` ok `True` detail ``
- `prestage_total` elapsed `18.438` ok `True` detail ``
- `connect_config_stage` elapsed `2.714` ok `True` detail ``
- `connect_window` elapsed `90.281` ok `True` detail ``
- `handoff_flash_test_rollback_total` elapsed `255.201` ok `True` detail ``
- `post_rollback_artifact_upload` elapsed `74.921` ok `True` detail ``

## Step Phase Summary

- `preflight_device` elapsed `1.55` steps `3` slow `set-sibling-fwssctl-flag:0.645s, pre-status:0.466s, pre-selftest:0.438s`
- `helper_stage` elapsed `11.009` steps `10` slow `host-build-execns-helper:7.18s, property-runtime-stage-extract:0.555s, execns-helper-fast-wget:0.553s`
- `connect_config_stage` elapsed `2.169` steps `5` slow `connect-config-mkdir:0.544s, connect-config-decode-redacted:0.544s, connect-config-clean:0.541s`
- `flash_total` elapsed `62.571` steps `1` slow `test-flash-from-native:62.571s`
- `connect_window` elapsed `89.292` steps `32` slow `connect-script-line-00:45.078s, connect-result-wait-polls:28.357s, connect-script-validate:0.552s`
- `artifact_upload` elapsed `1.845` steps `17` slow `fast-upload-v2167-device-stream:0.65s, test-fast-evidence-device-stream:0.642s, test-fast-evidence-collector-fast-wget:0.553s`
- `rollback_flash_total` elapsed `62.358` steps `1` slow `rollback-from-native:62.358s`
- `rollback_status` elapsed `0.468` steps `1` slow `rollback-status:0.468s`
- `selftest` elapsed `0.873` steps `2` slow `rollback-selftest:0.438s, test-selftest:0.435s`
- `other` elapsed `110.447` steps `30` slow `post-rollback-connect-ping-cleanup:60.076s, test-helper-wait-polls:33.336s, fast-transfer-device-host-probe:10.277s`

## Native Flash Subphases

- `test-flash-from-native.inspect_local_image` elapsed `0.054` ok `True`
- `test-flash-from-native.native_to_recovery` elapsed `0.302` ok `True`
- `test-flash-from-native.wait_recovery_adb` elapsed `27.119` ok `True`
- `test-flash-from-native.adb_push` elapsed `0.844` ok `True`
- `test-flash-from-native.remote_sha256` elapsed `0.107` ok `True`
- `test-flash-from-native.boot_dd_write` elapsed `0.452` ok `True`
- `test-flash-from-native.boot_readback_sha256` elapsed `0.359` ok `True`
- `test-flash-from-native.flash_boot_image` elapsed `1.763` ok `True`
- `test-flash-from-native.reboot_twrp_to_system` elapsed `1.851` ok `True`
- `test-flash-from-native.verify_native_init` elapsed `31.44` ok `True`
- `test-flash-from-native.total` elapsed `62.529` ok `True`
- `rollback-from-native.inspect_local_image` elapsed `0.053` ok `True`
- `rollback-from-native.native_to_recovery` elapsed `0.303` ok `True`
- `rollback-from-native.wait_recovery_adb` elapsed `27.127` ok `True`
- `rollback-from-native.adb_push` elapsed `0.82` ok `True`
- `rollback-from-native.remote_sha256` elapsed `0.105` ok `True`
- `rollback-from-native.boot_dd_write` elapsed `0.434` ok `True`
- `rollback-from-native.boot_readback_sha256` elapsed `0.173` ok `True`
- `rollback-from-native.flash_boot_image` elapsed `1.533` ok `True`
- `rollback-from-native.reboot_twrp_to_system` elapsed `1.855` ok `True`
- `rollback-from-native.verify_native_init` elapsed `31.446` ok `True`
- `rollback-from-native.total` elapsed `62.317` ok `True`

## Slowest Steps

- `test-flash-from-native` elapsed `62.571` ok `True` timeout `False`
- `rollback-from-native` elapsed `62.358` ok `True` timeout `False`
- `post-rollback-connect-ping-cleanup` elapsed `60.076` ok `False` timeout `False`
- `connect-script-line-00` elapsed `45.078` ok `False` timeout `False`
- `test-helper-wait-polls` elapsed `33.336` ok `True` timeout `False`
- `connect-result-wait-polls` elapsed `28.357` ok `True` timeout `False`
- `fast-transfer-device-host-probe` elapsed `10.277` ok `False` timeout `False`
- `host-build-execns-helper` elapsed `7.18` ok `True` timeout `False`
- `standalone-wpa-stage-extract-verify` elapsed `0.748` ok `True` timeout `False`
- `standalone-wpa-fast-wget` elapsed `0.661` ok `True` timeout `False`
- `fast-upload-v2167-device-stream` elapsed `0.65` ok `True` timeout `False`
- `set-sibling-fwssctl-flag` elapsed `0.645` ok `True` timeout `False`

## Gate Results

- `wlan0_seen`: `True` helper_invoked `True` helper_rc `0`
- `executor_result`: `connect-dhcp-ping-pass`
- `association_carrier`: `True` errno `0`
- `country`: `KR` driver_ioctl_rc `0` errno `0` readback `US` get_rc `0`
- `wpa_ctrl`: ready `True` surface `interface` global_path `/tmp/a90-v231-718/root/dev/socket/wpa_wlan0` abstract `False` preclean `none` preclean_errno `0` ping `pong` interface_add_rc `0` interface_add `` after_add_ready `False` after_add_surface `` after_add_global `` after_add_ping `` country_rc `0` reply `unknown` enable `ok` reassociate `ok`
- `wpa_ctrl_path`: dir `/cache/a90-wifi/sockets` interface `/cache/a90-wifi/sockets/wlan0`
- `supplicant`: launch `native-direct-interface-config` driver `nl80211` global_ctrl `none` direct_iface `True` strace `False` strace_output `` android_socket_mode `disabled-native-global-ctrl` android_socket_fd `-2` android_socket_errno `0` alive_start `True` state_start `S` zombie_after_ctrl `False` alive_after_carrier_wait `True` state_after_carrier_wait `S`
- `supplicant_preexec`: path `/cache/a90-wifi/wpa-standalone/wpa_supplicant-a90.sh` path_x `True` path_errno `0` loader_x `True` loader_errno `0` binary_x `True` binary_errno `0` busybox_x `True` busybox_errno `0` urandom_r `True` urandom_errno `0` urandom_mode `666` urandom_rdev `1:9`
- `standalone_wpa`: enabled `1` staged `True` reason `ok` wrapper `/cache/a90-wifi/wpa-standalone/wpa_supplicant-a90.sh` packages `17` version_rc `0` version `Could_not_open_/dev/urandom.`
- `supplicant_hidl`: hwservicemanager_started `False` mode `not-needed` pid `-1` add_rc `0` service_found `False` descriptor `` instance `` transaction_ok `False` status `` iface_handle `False` result `skipped` reason `manual-hidl-add-disabled-for-direct-interface-route` after_add_fd `4` after_add_netlink `0` after_add_genl `0`
- `supplicant_hidl_vendor`: service_found `False` descriptor `` instance ``
- `supplicant_proc_start`: comm `a90_strace_v216` exe `a90_strace_v2167` has_wpa `True` has_helper `False` has_config `True`
- `supplicant_proc_start_runtime`: uid `0?0?0?0` gid `0?0?0?0` groups `` wchan `do_wait` syscall `260 0xffffffffffffffff 0x7fca18a164 0x40000000 0x0 0x0 0x0 0x7fca18a110 0x4e5688` stack `[<0000000000000000>] __switch_to+0x10c/0x120` fd_count `4` socket_fds `0` netlink_fds `0` generic_netlink_fds `0` netlink_miss `0` wpa_socket_fds `0` stdio_fds `1`
- `supplicant_proc_after_wait`: comm `a90_strace_v216` exe `a90_strace_v2167` has_wpa `True` has_helper `False` has_config `True`
- `supplicant_proc_after_wait_runtime`: uid `0?0?0?0` gid `0?0?0?0` groups `` wchan `do_wait` syscall `260 0xffffffffffffffff 0x7fca18a164 0x40000000 0x0 0x0 0x0 0x7fca18a110 0x4e5688` stack `[<0000000000000000>] __switch_to+0x10c/0x120` fd_count `4` socket_fds `0` netlink_fds `0` generic_netlink_fds `0` netlink_miss `0` wpa_socket_fds `0` stdio_fds `1`
- `supplicant_log`: present `False` size `0` lines `0` ctrl `0` ctrl_err `0` nl80211 `0` scan `0` auth `0` assoc `0` connected `0` disconnected `0` fail `0` permission `0` avc `0` samples `0` tail_samples `0` nonproperty_samples `0` sensitive_skipped `0`
- `supplicant_stdio`: present `True` size `71659` lines `884` ctrl `8` ctrl_err `0` config_err `1` nl80211 `299` scan `41` auth `17` assoc `25` connected `4` disconnected `3` fail `3` usage `0` interface `16` socket `9` terminate `0` permission `0` avc `0` samples `24` tail_samples `24` nonproperty_samples `24` sensitive_skipped `87`
- `logdw_sink`: started `True` errno `0` datagrams `19` bytes `1460` wpa `0` supplicant `0` nl80211 `6` ctrl `0` interface `0` fail `6` permission `0` hidl `0` service_manager `0` samples `12` sensitive_skipped `0` drain_errno `0`
- `kmsg_stream`: started `True` start_errno `0` present `True` size `29476` lines `363` permission `0` avc `0` nl80211 `0` auth `3` assoc `6` fail `7` sensitive_skipped `19` cleanup_exit `-1` signal `15` timeout `False`
- `dhcp_executed`: `True` dhcp_rc `0` resolv_present `True` resolv_errno `0` resolv_size `48` nameservers `2`
- `external_ping_executed`: `True` target `google.com` rc `0` classifier `icmp-reply` output_present `True` output_errno `0` bytes_from `True` bad_address `False` unknown_host `False` net_unreach `False` sendto `False` zero_recv `False` loss100 `False`
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

- `tail_00`: `1518738890.678383: nl80211: Associated on 5745 MHz`
- `tail_01`: `1518738890.680758: nl80211: Dump inconsistency detected, interrupted; convert to -EAGAIN`
- `tail_02`: `1518738890.683960: nl80211: Associated on 5745 MHz`
- `tail_03`: `1518738890.690959: nl80211: Set wlan0 operstate 0->0 (DORMANT)`
- `tail_04`: `1518738890.698509: WPA: Update cipher suite selection based on IEs in driver-generated WPA/RSNE in AssocReq - hexdump(len=91): 30 16 01 00 00 0f ac 04 01 00 00 0f ac 04 01 00 00 0f ac 02 0c 00 00 00 3b 16 80 51 53 54 73 74 75 76 77 78 79 7a 7b 7c 7d 7e 7f`
- `tail_05`: `1518738890.706251: EAPOL: SUPP_PAE entering state CONNECTING`
- `tail_06`: `1518738890.708570: wlan0: CTRL-EVENT-SUBNET-STATUS-UPDATE status=0`
- `tail_07`: `1518738890.737103: wlan0: WPA: Installing PTK to the driver`
- `tail_08`: `1518738890.738333: nl80211: NEW_KEY`
- `tail_09`: `1518738890.738511: nl80211: KEY_DATA - hexdump(len=16): [REMOVED]`
- `tail_10`: `1518738890.738686: nl80211: KEY_SEQ - hexdump(len=6): 00 00 00 00 00 00`
- `tail_11`: `1518738890.750041: wlan0: WPA: Installing GTK to the driver (keyidx=1 tx=0 len=16)`
- `tail_12`: `1518738890.751377: nl80211: NEW_KEY`
- `tail_13`: `1518738890.751554: nl80211: KEY_DATA - hexdump(len=16): [REMOVED]`
- `tail_14`: `1518738890.751741: nl80211: KEY_SEQ - hexdump(len=6): 6f f0 08 00 00 00`
- `tail_15`: `1518738890.755571: wlan0: Radio work 'connect'@0x55572cc610 done in 0.204090 seconds`
- `tail_16`: `1518738890.756010: wlan0: radio_work_free('connect'@0x55572cc610): num_active_works --> 0`
- `tail_17`: `1518738890.756889: nl80211: Set wlan0 operstate 0->1 (UP)`
- `tail_18`: `1518738890.769076: nl80211: Set rekey offload`
- `tail_19`: `1518738890.772178: nl80211: Event message available`
- `tail_20`: `1518738890.776269: nl80211: Drv Event 103 (NL80211_CMD_VENDOR) received for wlan0`
- `tail_21`: `1518738890.776455: nl80211: Vendor event: wiphy=0 vendor_id=0x1374 subcmd=165`
- `tail_22`: `1518738890.776632: nl80211: Vendor data - hexdump(len=48): 30 00 01 00 2c 00 00 00 08 00 01 00 00 00 00 00 08 00 02 00 02 00 00 00 18 00 03 00 14 00 00 00 08 00 01 00 09 00 00 00 08 00 02 00 71 16 00 00`
- `tail_23`: `1518738890.779602: nl80211: Ignore unsupported QCA vendor event 165`

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

- `logdw_sample_00`: `Z l # cnss-daemon nl80211 response handler invoked`
- `logdw_sample_01`: `Z: # cnss-daemon nl80211_response_handler: cmd 103, vendorID 4980, subcmd 106  received`
- `logdw_sample_02`: `Z U CNSS failed to open file a+ mode or file size 0 is less than max_file_size 31457280`
- `logdw_sample_03`: `Z= CNSS Failed to open file /data/vendor/log/wifi/host_driver_logs_current.txt: 2`
- `logdw_sample_04`: `Z> D cnss-daemon nl80211 response handler invoked`
- `logdw_sample_05`: `Z PE cnss-daemon nl80211_response_handler: cmd 103, vendorID 4980, subcmd 107  received`
- `logdw_sample_06`: `Zd , cnss-daemon nl80211 response handler invoked`
- `logdw_sample_07`: `Z&p , cnss-daemon nl80211_response_handler: cmd 103, vendorID 4980, subcmd 165  received`
- `logdw_sample_08`: `Z CNSS failed to open file a+ mode or file size 0 is less than max_file_size 31457280`
- `logdw_sample_09`: `Z CNSS Failed to open file /data/vendor/log/wifi/host_driver_logs_current.txt: 2`
- `logdw_sample_10`: `Z? CNSS failed to open file a+ mode or file size 0 is less than max_file_size 31457280`
- `logdw_sample_11`: `Ze CNSS Failed to open file /data/vendor/log/wifi/host_driver_logs_current.txt: 2`
- `kmsg_sample_00`: `4,4177,90394684,-; scheduler_thread+0x1b4/0x5a8`
- `kmsg_sample_01`: `4,4178,90394696,-; kthread+0x120/0x138`
- `kmsg_sample_02`: `4,4245,90395503,-; scheduler_thread+0x1b4/0x5a8`
- `kmsg_sample_03`: `4,4246,90395514,-; kthread+0x120/0x138`
- `kmsg_sample_04`: `4,4257,90395695,-;WARNING: CPU: 3 PID: 659 at drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0/components/ipa/core/src/wlan_ipa_core.c:1493 wlan_ipa_cleanup_iface+0x2e8/0x4a8`
- `kmsg_sample_05`: `4,4313,90396417,-; scheduler_thread+0x1b4/0x5a8`
- `kmsg_sample_06`: `4,4314,90396428,-; kthread+0x120/0x138`
- `kmsg_sample_07`: `3,4317,90396471,-;[schedu][0x7c5d89ff][23:54:50.664174] wlan: [659:E:IPA] __wlan_ipa_wlan_evt: 2236: wlan_ipa_setup_iface failed 4294967282`
- `kmsg_sample_08`: `6,4339,90489635,-;IPv6: ADDRCONF(NETDEV_CHANGE): wlan0: link becomes ready`
- `kmsg_sample_09`: `6,4345,91509643,-;max77705_fg_periodic_read: skip old(1) current(91)`
- `kmsg_sample_10`: `6,4346,91511034,-;max77705_fg_read_qh : QH(4773000)`
- `kmsg_sample_11`: `7,4348,91511291,-;max77705_fg_read_current: current=5mA`
- `kmsg_sample_12`: `7,4349,91511754,-;max77705_fg_read_avg_current: avg_current=0mA`
- `kmsg_sample_13`: `6,4350,91511992,-;max77705_fg_read_isys_avg: isys_avg_current=633mA`
- `kmsg_sample_14`: `6,4351,91512233,-;max77705_fg_read_isys: isys_current=983mA`
- `kmsg_sample_15`: `6,4353,91527721,-;max77705_fg_read_vcell: VCELL(4330)mV, data(0xd880)`
- `kmsg_sample_16`: `7,4354,91528188,-;max77705_fg_read_avg_current: avg_current=0mA`
- `kmsg_sample_17`: `6,4371,91532954,-;sec_bat_get_property: input current(1500mA), cable type(5), slow-charging mode(1)`
- `kmsg_sample_18`: `6,4372,91532971,-;sec_bat_get_property cable type = 5 sleep_mode = 0`
- `kmsg_sample_19`: `7,4373,91533218,-;max77705_fg_read_current: current=5mA`
- `kmsg_sample_20`: `7,4374,91533678,-;max77705_fg_read_avg_current: avg_current=0mA`
- `kmsg_tail_00`: `4,4177,90394684,-; scheduler_thread+0x1b4/0x5a8`
- `kmsg_tail_01`: `4,4178,90394696,-; kthread+0x120/0x138`
- `kmsg_tail_02`: `4,4245,90395503,-; scheduler_thread+0x1b4/0x5a8`
- `kmsg_tail_03`: `4,4246,90395514,-; kthread+0x120/0x138`
- `kmsg_tail_04`: `4,4257,90395695,-;WARNING: CPU: 3 PID: 659 at drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0/components/ipa/core/src/wlan_ipa_core.c:1493 wlan_ipa_cleanup_iface+0x2e8/0x4a8`
- `kmsg_tail_05`: `4,4313,90396417,-; scheduler_thread+0x1b4/0x5a8`
- `kmsg_tail_06`: `4,4314,90396428,-; kthread+0x120/0x138`
- `kmsg_tail_07`: `3,4317,90396471,-;[schedu][0x7c5d89ff][23:54:50.664174] wlan: [659:E:IPA] __wlan_ipa_wlan_evt: 2236: wlan_ipa_setup_iface failed 4294967282`
- `kmsg_tail_08`: `6,4339,90489635,-;IPv6: ADDRCONF(NETDEV_CHANGE): wlan0: link becomes ready`
- `kmsg_tail_09`: `6,4345,91509643,-;max77705_fg_periodic_read: skip old(1) current(91)`
- `kmsg_tail_10`: `6,4346,91511034,-;max77705_fg_read_qh : QH(4773000)`
- `kmsg_tail_11`: `7,4348,91511291,-;max77705_fg_read_current: current=5mA`
- `kmsg_tail_12`: `7,4349,91511754,-;max77705_fg_read_avg_current: avg_current=0mA`
- `kmsg_tail_13`: `6,4350,91511992,-;max77705_fg_read_isys_avg: isys_avg_current=633mA`
- `kmsg_tail_14`: `6,4351,91512233,-;max77705_fg_read_isys: isys_current=983mA`
- `kmsg_tail_15`: `6,4353,91527721,-;max77705_fg_read_vcell: VCELL(4330)mV, data(0xd880)`
- `kmsg_tail_16`: `7,4354,91528188,-;max77705_fg_read_avg_current: avg_current=0mA`
- `kmsg_tail_17`: `6,4371,91532954,-;sec_bat_get_property: input current(1500mA), cable type(5), slow-charging mode(1)`
- `kmsg_tail_18`: `6,4372,91532971,-;sec_bat_get_property cable type = 5 sleep_mode = 0`
- `kmsg_tail_19`: `7,4373,91533218,-;max77705_fg_read_current: current=5mA`
- `kmsg_tail_20`: `7,4374,91533678,-;max77705_fg_read_avg_current: avg_current=0mA`

## Supplicant FD Samples

- `start_fd_00`: `2:/cache/a90-wifi/a90_supplicant_execns_stdio.log`
- `wait_fd_00`: `2:/cache/a90-wifi/a90_supplicant_execns_stdio.log`

## Staging

- `property_archive`: `tmp/wifi/v2167-connect-dhcp-google-ping-handoff-standalone-wpa-v22/property-runtime-v2167.tgz` bytes `12738` chunks `12` staged `1` method `ncm-wget` fast `1` elapsed `3.785`
- `helper_sha256`: `6b655eea64ef3c12ad354e6151085c2aab60aa8c3f57945925ef03fd2789c1af` gzip_len `607578` chunks `528` method `ncm-wget` fast `1` elapsed `0.554`
- `strace_stage`: ok `1` reason `already-present` fast `` elapsed ``
- `standalone_wpa_archive`: ok `True` bytes `8179693` sha `d418c3f82d467f2c559019d55c9e9ce9ecf24fd7231c58110d8750868cbe71ba` packages `17` staged `1` fast `1` elapsed `0.662`
- `connect_config`: path `/cache/a90-wifi/v2167.conf` size `232` mode `600` security `wpa-psk` disabled_initially `0` raw_values_logged `0`

## Scope

- This V2167 unit stages a generated private property root at `/cache/a90-wifi-property-v2167/dev/__properties__` with the wpa_supplicant loader/log lookup keys, adds private `/dev/random` and `/dev/urandom`, creates `/dev/socket/logdw`, launches `wpa_supplicant` direct as `-dd -i wlan0 -D nl80211 -c <config> -O /cache/a90-wifi/sockets -t`, and observes carrier/DHCP/ping. It records redacted supplicant/logdw/kmsg samples plus `/proc` fd/netlink/syscall counters. This target supplicant does not support `-f`, so stdout/stderr plus logdw are the diagnostic logs.
- Allowed actions: start private Wi-Fi active-session surface, start `wpa_supplicant`, run DHCP, set temporary route/DNS, and ping `google.com`.
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
- `execns-helper-stage-clean` rc `0` ok `True` evidence `execns-helper-stage-clean.stdout.txt`
- `execns-helper-fast-wget` rc `0` ok `True` evidence `execns-helper-fast-wget.stdout.txt`
- `execns-helper-fast-wget-result` rc `0` ok `True` evidence `execns-helper-fast-wget-result.stdout.txt`
- `execns-helper-stage-decode` rc `0` ok `True` evidence `execns-helper-stage-decode.stdout.txt`
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
- `connect-script-validate` rc `0` ok `True` evidence `connect-script-validate.stdout.txt`
- `connect-script-chmod` rc `0` ok `True` evidence `connect-script-chmod.stdout.txt`
- `connect-script-start` rc `0` ok `True` evidence `connect-script-start.stdout.txt`
- `connect-result-wait-polls` rc `0` ok `True` evidence `connect-result-wait-polls.txt`
- `test-helper-wait-polls` rc `0` ok `True` evidence `test-helper-wait-polls.txt`
- `fast-transfer-host-net-before` rc `0` ok `True` evidence `fast-transfer-host-net-before.stdout.txt`
- `fast-transfer-host-net-existing` rc `0` ok `True` evidence `fast-transfer-host-net-existing.stdout.txt`
- `fast-transfer-device-host-probe` rc `0` ok `True` evidence `fast-transfer-device-host-probe.stdout.txt`
- `fast-transfer-device-host-probe-result` rc `0` ok `True` evidence `fast-transfer-device-host-probe-result.stdout.txt`
- `test-fast-evidence-collector-fast-wget` rc `0` ok `True` evidence `test-fast-evidence-collector-fast-wget.stdout.txt`
- `test-fast-evidence-collector-fast-wget-result` rc `0` ok `True` evidence `test-fast-evidence-collector-fast-wget-result.stdout.txt`
- `test-fast-evidence-device-stream` rc `0` ok `True` evidence `test-fast-evidence-device-stream.stdout.txt`
- `test-sys-wifi-mac-node` rc `0` ok `True` evidence `test-sys-wifi-mac-node.stdout.txt`
- `test-dmesg-full` rc `0` ok `True` evidence `test-dmesg-full.stdout.txt`
- `test-v2168-helper-result` rc `0` ok `True` evidence `test-v2168-helper-result.stdout.txt`
- `test-supplicant-strace` rc `0` ok `True` evidence `test-supplicant-strace.stdout.txt`
- `test-icnss-stats` rc `0` ok `True` evidence `test-icnss-stats.stdout.txt`
- `test-v2168-summary` rc `0` ok `True` evidence `test-v2168-summary.stdout.txt`
- `test-dmesg-wifi-filter` rc `0` ok `True` evidence `test-dmesg-wifi-filter.stdout.txt`
- `test-wlan0-ifconfig` rc `0` ok `True` evidence `test-wlan0-ifconfig.stdout.txt`
- `test-icnss-debugfs-ls` rc `0` ok `True` evidence `test-icnss-debugfs-ls.stdout.txt`
- `test-wlan0-state` rc `0` ok `True` evidence `test-wlan0-state.stdout.txt`
- `test-v2168-log` rc `0` ok `True` evidence `test-v2168-log.stdout.txt`
- `test-fast-evidence-upload-result` rc `0` ok `True` evidence `test-fast-evidence-upload-result.stdout.txt`
- `test-version` rc `0` ok `True` evidence `test-version.stdout.txt`
- `test-status` rc `0` ok `True` evidence `test-status.stdout.txt`
- `test-selftest` rc `0` ok `True` evidence `test-selftest.stdout.txt`
- `test-bootstatus` rc `0` ok `True` evidence `test-bootstatus.stdout.txt`
- `rollback-from-native` rc `0` ok `True` evidence `rollback-from-native.stdout.txt`
- `rollback-status` rc `0` ok `True` evidence `rollback-status.stdout.txt`
- `rollback-selftest` rc `0` ok `True` evidence `rollback-selftest.stdout.txt`
- `fast-transfer-host-net-before` rc `0` ok `True` evidence `fast-transfer-host-net-before.stdout.txt`
- `fast-transfer-host-net-existing` rc `0` ok `True` evidence `fast-transfer-host-net-existing.stdout.txt`
- `fast-transfer-device-host-probe-hide-on-busy` rc `0` ok `True` evidence `fast-transfer-device-host-probe-hide-on-busy.stdout.txt`
- `fast-transfer-device-host-probe` rc `1` ok `False` evidence `fast-transfer-device-host-probe.stdout.txt`
- `fast-transfer-device-host-probe-result` rc `1` ok `False` evidence `fast-transfer-device-host-probe-result.stdout.txt`
- `fast-transfer-host-nm-linklocal-repair` rc `0` ok `True` evidence `fast-transfer-host-nm-linklocal-repair.stdout.txt`
- `fast-transfer-device-host-probe-after-nm-repair` rc `0` ok `True` evidence `fast-transfer-device-host-probe-after-nm-repair.stdout.txt`
- `fast-transfer-device-host-probe-result-after-nm-repair` rc `0` ok `True` evidence `fast-transfer-device-host-probe-result-after-nm-repair.stdout.txt`
- `fast-upload-v2167-device-stream` rc `0` ok `True` evidence `fast-upload-v2167-device-stream.stdout.txt`
- `fast-upload-v2167-result` rc `0` ok `True` evidence `fast-upload-v2167-result.stdout.txt`
- `post-rollback-connect-ping-result-fast-upload` rc `0` ok `True` evidence `post-rollback-connect-ping-result-fast-upload.stdout.txt`
- `post-rollback-connect-ping-cleanup` rc `1` ok `False` evidence `post-rollback-connect-ping-cleanup.stdout.txt`

## Cleanup

- `cache_artifacts_removed`: `False`
- `cleanup_skipped_reason`: ``

## Safety

- Wi-Fi credentials are read only from environment variables and are not committed.
- Raw supplicant, kmsg, DHCP, and ping stdout/stderr are summarized with redacted samples; raw supplicant/kmsg files are removed during helper cleanup.
- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action is used.
