# Native Init V2167 Connect DHCP Google Ping Handoff

## Summary

- Cycle: `V2167`
- Run label: `standalone-wpa-v23-2g`
- Decision: `v2167-connect-dhcp-google-ping-pass`
- Label: `connect-dhcp-google-ping-pass`
- Pass: `True`
- Reason: native wlan0 associated, DHCP succeeded, and google.com ping returned success
- Evidence: `tmp/wifi/v2167-connect-dhcp-google-ping-handoff-standalone-wpa-v23-2g`
- Result source: `serial-cat` serial_attempts `1` result_left_on_device `False`
- Fast upload: ok `False` reason `device-to-host-ncm-probe-failed-after-nm-repair` elapsed `0.0`
- Fast upload archive: `` bytes `0` receiver_bytes `0` entries `0` secret_hits `[]` forbidden_entries `[]`

## Phase Timers

- `host_property_build` elapsed `0.026` ok `True` detail ``
- `host_property_archive` elapsed `0.016` ok `True` detail ``
- `host_standalone_wpa_bundle` elapsed `2.958` ok `True` detail ``
- `property_stage` elapsed `2.223` ok `True` detail ``
- `host_helper_build` elapsed `7.274` ok `True` detail ``
- `helper_stage` elapsed `0.542` ok `True` detail ``
- `strace_stage` elapsed `1.089` ok `True` detail ``
- `standalone_wpa_stage` elapsed `2.994` ok `True` detail ``
- `fast_transfer_close` elapsed `0.0` ok `True` detail ``
- `prestage_total` elapsed `14.121` ok `True` detail ``
- `connect_config_stage` elapsed `2.725` ok `True` detail ``
- `connect_window` elapsed `86.625` ok `True` detail ``
- `handoff_flash_test_rollback_total` elapsed `256.635` ok `True` detail ``
- `post_rollback_artifact_upload` elapsed `25.237` ok `True` detail ``

## Step Phase Summary

- `preflight_device` elapsed `1.553` steps `3` slow `set-sibling-fwssctl-flag:0.645s, pre-status:0.466s, pre-selftest:0.442s`
- `helper_stage` elapsed `9.374` steps `6` slow `host-build-execns-helper:7.18s, property-runtime-fast-wget:0.556s, property-runtime-stage-extract:0.553s`
- `connect_config_stage` elapsed `2.169` steps `5` slow `connect-config-decode-redacted:0.545s, connect-config-mkdir:0.544s, connect-config-touch-b64:0.542s`
- `flash_total` elapsed `63.734` steps `1` slow `test-flash-from-native:63.734s`
- `connect_window` elapsed `85.634` steps `32` slow `connect-script-touch:45.107s, connect-result-wait-polls:24.814s, connect-script-line-19:0.549s`
- `artifact_upload` elapsed `1.667` steps `16` slow `test-fast-evidence-device-stream:0.64s, test-fast-evidence-collector-fast-wget:0.55s, post-rollback-connect-ping-result:0.477s`
- `rollback_flash_total` elapsed `66.313` steps `1` slow `rollback-from-native:66.313s`
- `rollback_status` elapsed `0.469` steps `1` slow `rollback-status:0.469s`
- `selftest` elapsed `0.871` steps `2` slow `test-selftest:0.436s, rollback-selftest:0.435s`
- `other` elapsed `60.682` steps `30` slow `test-helper-wait-polls:33.309s, fast-transfer-device-host-probe:10.28s, fast-transfer-device-host-probe-after-nm-repair:10.237s`

## Native Flash Subphases

- `test-flash-from-native.inspect_local_image` elapsed `0.055` ok `True`
- `test-flash-from-native.native_to_recovery` elapsed `0.302` ok `True`
- `test-flash-from-native.wait_recovery_adb` elapsed `28.135` ok `True`
- `test-flash-from-native.adb_push` elapsed `0.838` ok `True`
- `test-flash-from-native.remote_sha256` elapsed `0.099` ok `True`
- `test-flash-from-native.boot_dd_write` elapsed `0.424` ok `True`
- `test-flash-from-native.boot_readback_sha256` elapsed `0.346` ok `True`
- `test-flash-from-native.flash_boot_image` elapsed `1.708` ok `True`
- `test-flash-from-native.reboot_twrp_to_system` elapsed `2.046` ok `True`
- `test-flash-from-native.verify_native_init` elapsed `31.443` ok `True`
- `test-flash-from-native.total` elapsed `63.689` ok `True`
- `rollback-from-native.inspect_local_image` elapsed `0.053` ok `True`
- `rollback-from-native.native_to_recovery` elapsed `0.553` ok `True`
- `rollback-from-native.wait_recovery_adb` elapsed `30.143` ok `True`
- `rollback-from-native.adb_push` elapsed `0.815` ok `True`
- `rollback-from-native.remote_sha256` elapsed `0.096` ok `True`
- `rollback-from-native.boot_dd_write` elapsed `0.452` ok `True`
- `rollback-from-native.boot_readback_sha256` elapsed `0.218` ok `True`
- `rollback-from-native.flash_boot_image` elapsed `1.582` ok `True`
- `rollback-from-native.reboot_twrp_to_system` elapsed `2.496` ok `True`
- `rollback-from-native.verify_native_init` elapsed `31.446` ok `True`
- `rollback-from-native.total` elapsed `66.272` ok `True`

## Slowest Steps

- `rollback-from-native` elapsed `66.313` ok `True` timeout `False`
- `test-flash-from-native` elapsed `63.734` ok `True` timeout `False`
- `connect-script-touch` elapsed `45.107` ok `False` timeout `False`
- `test-helper-wait-polls` elapsed `33.309` ok `True` timeout `False`
- `connect-result-wait-polls` elapsed `24.814` ok `True` timeout `False`
- `fast-transfer-device-host-probe` elapsed `10.28` ok `False` timeout `False`
- `fast-transfer-device-host-probe-after-nm-repair` elapsed `10.237` ok `False` timeout `False`
- `host-build-execns-helper` elapsed `7.18` ok `True` timeout `False`
- `standalone-wpa-stage-extract-verify` elapsed `0.849` ok `True` timeout `False`
- `standalone-wpa-fast-wget` elapsed `0.651` ok `True` timeout `False`
- `set-sibling-fwssctl-flag` elapsed `0.645` ok `True` timeout `False`
- `test-fast-evidence-device-stream` elapsed `0.64` ok `True` timeout `False`

## Gate Results

- `wlan0_seen`: `True` helper_invoked `True` helper_rc `0`
- `executor_result`: `connect-dhcp-ping-pass`
- `association_carrier`: `True` errno `0`
- `country`: `KR` driver_ioctl_rc `0` errno `0` readback `US` get_rc `0`
- `wpa_ctrl`: ready `True` surface `interface` global_path `/tmp/a90-v231-718/root/dev/socket/wpa_wlan0` abstract `False` preclean `none` preclean_errno `0` ping `pong` interface_add_rc `0` interface_add `` after_add_ready `False` after_add_surface `` after_add_global `` after_add_ping `` country_rc `0` reply `unknown` enable `ok` reassociate `ok`
- `wpa_ctrl_path`: dir `/cache/a90-wifi/sockets` interface `/cache/a90-wifi/sockets/wlan0`
- `supplicant`: launch `native-direct-interface-config` driver `nl80211` global_ctrl `none` direct_iface `True` strace `False` strace_output `` android_socket_mode `disabled-native-global-ctrl` android_socket_fd `-2` android_socket_errno `0` alive_start `True` state_start `S` zombie_after_ctrl `False` alive_after_carrier_wait `True` state_after_carrier_wait `R`
- `supplicant_preexec`: path `/cache/a90-wifi/wpa-standalone/wpa_supplicant-a90.sh` path_x `True` path_errno `0` loader_x `True` loader_errno `0` binary_x `True` binary_errno `0` busybox_x `True` busybox_errno `0` urandom_r `True` urandom_errno `0` urandom_mode `666` urandom_rdev `1:9`
- `standalone_wpa`: enabled `1` staged `True` reason `ok` wrapper `/cache/a90-wifi/wpa-standalone/wpa_supplicant-a90.sh` packages `17` version_rc `0` version `Could_not_open_/dev/urandom.`
- `supplicant_hidl`: hwservicemanager_started `False` mode `not-needed` pid `-1` add_rc `0` service_found `False` descriptor `` instance `` transaction_ok `False` status `` iface_handle `False` result `skipped` reason `manual-hidl-add-disabled-for-direct-interface-route` after_add_fd `4` after_add_netlink `0` after_add_genl `0`
- `supplicant_hidl_vendor`: service_found `False` descriptor `` instance ``
- `supplicant_proc_start`: comm `a90_strace_v216` exe `a90_strace_v2167` has_wpa `True` has_helper `False` has_config `True`
- `supplicant_proc_start_runtime`: uid `0?0?0?0` gid `0?0?0?0` groups `` wchan `do_wait` syscall `260 0xffffffffffffffff 0x7fc6f8af54 0x40000000 0x0 0x0 0x0 0x7fc6f8af00 0x4e5688` stack `[<0000000000000000>] __switch_to+0x10c/0x120` fd_count `4` socket_fds `0` netlink_fds `0` generic_netlink_fds `0` netlink_miss `0` wpa_socket_fds `0` stdio_fds `1`
- `supplicant_proc_after_wait`: comm `a90_strace_v216` exe `a90_strace_v2167` has_wpa `True` has_helper `False` has_config `True`
- `supplicant_proc_after_wait_runtime`: uid `0?0?0?0` gid `0?0?0?0` groups `` wchan `0` syscall `running` stack `[<0000000000000000>] __switch_to+0x10c/0x120` fd_count `5` socket_fds `1` netlink_fds `1` generic_netlink_fds `0` netlink_miss `0` wpa_socket_fds `0` stdio_fds `1`
- `supplicant_log`: present `False` size `0` lines `0` ctrl `0` ctrl_err `0` nl80211 `0` scan `0` auth `0` assoc `0` connected `0` disconnected `0` fail `0` permission `0` avc `0` samples `0` tail_samples `0` nonproperty_samples `0` sensitive_skipped `0`
- `supplicant_stdio`: present `True` size `71417` lines `884` ctrl `8` ctrl_err `0` config_err `1` nl80211 `296` scan `40` auth `17` assoc `22` connected `4` disconnected `3` fail `2` usage `0` interface `16` socket `9` terminate `0` permission `0` avc `0` samples `24` tail_samples `24` nonproperty_samples `24` sensitive_skipped `91`
- `logdw_sink`: started `True` errno `0` datagrams `13` bytes `892` wpa `0` supplicant `0` nl80211 `6` ctrl `0` interface `0` fail `2` permission `0` hidl `0` service_manager `0` samples `8` sensitive_skipped `0` drain_errno `0`
- `kmsg_stream`: started `True` start_errno `0` present `True` size `29078` lines `357` permission `0` avc `0` nl80211 `0` auth `3` assoc `6` fail `7` sensitive_skipped `18` cleanup_exit `-1` signal `15` timeout `False`
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

- `tail_00`: `1518739325.716229: nl80211: Operating frequency for the associated BSS from scan results: 2412 MHz`
- `tail_01`: `1518739325.718664: nl80211: Associated on 2412 MHz`
- `tail_02`: `1518739325.724094: nl80211: Set wlan0 operstate 0->0 (DORMANT)`
- `tail_03`: `1518739325.731821: WPA: Update cipher suite selection based on IEs in driver-generated WPA/RSNE in AssocReq - hexdump(len=73): 30 16 01 00 00 0f ac 04 01 00 00 0f ac 04 01 00 00 0f ac 02 0c 00 00 00 32 04 30 48 60 6c 3b 16 53 51 53 54 73 74 75 76 77 78 79`
- `tail_04`: `1518739325.739469: EAPOL: SUPP_PAE entering state CONNECTING`
- `tail_05`: `1518739325.741266: wlan0: CTRL-EVENT-SUBNET-STATUS-UPDATE status=0`
- `tail_06`: `1518739325.772589: wlan0: WPA: Installing PTK to the driver`
- `tail_07`: `1518739325.773787: nl80211: NEW_KEY`
- `tail_08`: `1518739325.773969: nl80211: KEY_DATA - hexdump(len=16): [REMOVED]`
- `tail_09`: `1518739325.774148: nl80211: KEY_SEQ - hexdump(len=6): 00 00 00 00 00 00`
- `tail_10`: `1518739325.785803: wlan0: WPA: Installing GTK to the driver (keyidx=1 tx=0 len=16)`
- `tail_11`: `1518739325.787178: nl80211: NEW_KEY`
- `tail_12`: `1518739325.787358: nl80211: KEY_DATA - hexdump(len=16): [REMOVED]`
- `tail_13`: `1518739325.787546: nl80211: KEY_SEQ - hexdump(len=6): 00 00 00 00 00 00`
- `tail_14`: `1518739325.793153: wlan0: Radio work 'connect'@0x557e2fa610 done in 0.372096 seconds`
- `tail_15`: `1518739325.793610: wlan0: radio_work_free('connect'@0x557e2fa610): num_active_works --> 0`
- `tail_16`: `1518739325.794541: nl80211: Set wlan0 operstate 0->1 (UP)`
- `tail_17`: `1518739325.806920: nl80211: Set rekey offload`
- `tail_18`: `1518739325.809558: nl80211: Set IF_OPER_UP again based on ifi_flags and expected operstate`
- `tail_19`: `1518739325.811522: nl80211: Event message available`
- `tail_20`: `1518739325.815667: nl80211: Drv Event 103 (NL80211_CMD_VENDOR) received for wlan0`
- `tail_21`: `1518739325.815861: nl80211: Vendor event: wiphy=0 vendor_id=0x1374 subcmd=165`
- `tail_22`: `1518739325.816042: nl80211: Vendor data - hexdump(len=48): 30 00 01 00 2c 00 00 00 08 00 01 00 00 00 00 00 08 00 02 00 01 00 00 00 18 00 03 00 14 00 00 00 08 00 01 00 09 00 00 00 08 00 02 00 6c 09 00 00`
- `tail_23`: `1518739325.818902: nl80211: Ignore unsupported QCA vendor event 165`

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

- `logdw_sample_00`: `{ ZDb cnss-daemon nl80211 response handler invoked`
- `logdw_sample_01`: `{ Z cnss-daemon nl80211_response_handler: cmd 103, vendorID 4980, subcmd 106  received`
- `logdw_sample_02`: `} Za R CNSS failed to open file a+ mode or file size 0 is less than max_file_size 31457280`
- `logdw_sample_03`: `} Z> S CNSS Failed to open file /data/vendor/log/wifi/host_driver_logs_current.txt: 2`
- `logdw_sample_04`: `} Z f cnss-daemon nl80211 response handler invoked`
- `logdw_sample_05`: `} Z cnss-daemon nl80211_response_handler: cmd 103, vendorID 4980, subcmd 107  received`
- `logdw_sample_06`: `} Z ;. cnss-daemon nl80211 response handler invoked`
- `logdw_sample_07`: `} Z ;<. cnss-daemon nl80211_response_handler: cmd 103, vendorID 4980, subcmd 165  received`
- `kmsg_sample_00`: `4,4194,90436241,-; scheduler_thread+0x1b4/0x5a8`
- `kmsg_sample_01`: `4,4195,90436253,-; kthread+0x120/0x138`
- `kmsg_sample_02`: `4,4262,90437165,-; scheduler_thread+0x1b4/0x5a8`
- `kmsg_sample_03`: `4,4263,90437176,-; kthread+0x120/0x138`
- `kmsg_sample_04`: `4,4274,90437426,-;WARNING: CPU: 0 PID: 658 at drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0/components/ipa/core/src/wlan_ipa_core.c:1493 wlan_ipa_cleanup_iface+0x2e8/0x4a8`
- `kmsg_sample_05`: `4,4330,90438151,-; scheduler_thread+0x1b4/0x5a8`
- `kmsg_sample_06`: `4,4331,90438162,-; kthread+0x120/0x138`
- `kmsg_sample_07`: `3,4334,90438204,-;[schedu][0x7c6869f3][00:02:05.705947] wlan: [658:E:IPA] __wlan_ipa_wlan_evt: 2236: wlan_ipa_setup_iface failed 4294967282`
- `kmsg_sample_08`: `6,4355,90527690,-;IPv6: ADDRCONF(NETDEV_CHANGE): wlan0: link becomes ready`
- `kmsg_sample_09`: `6,4369,91509936,-;max77705_fg_periodic_read: skip old(1) current(91)`
- `kmsg_sample_10`: `6,4370,91511332,-;max77705_fg_read_qh : QH(4773000)`
- `kmsg_sample_11`: `7,4372,91511587,-;max77705_fg_read_current: current=5mA`
- `kmsg_sample_12`: `7,4373,91512050,-;max77705_fg_read_avg_current: avg_current=-1mA`
- `kmsg_sample_13`: `6,4374,91512287,-;max77705_fg_read_isys_avg: isys_avg_current=630mA`
- `kmsg_sample_14`: `6,4375,91512528,-;max77705_fg_read_isys: isys_current=890mA`
- `kmsg_sample_15`: `6,4377,91528006,-;max77705_fg_read_vcell: VCELL(4329)mV, data(0xd874)`
- `kmsg_sample_16`: `7,4378,91528474,-;max77705_fg_read_avg_current: avg_current=-1mA`
- `kmsg_sample_17`: `6,4395,91533255,-;sec_bat_get_property: input current(1500mA), cable type(5), slow-charging mode(1)`
- `kmsg_sample_18`: `6,4396,91533273,-;sec_bat_get_property cable type = 5 sleep_mode = 0`
- `kmsg_sample_19`: `7,4397,91533521,-;max77705_fg_read_current: current=5mA`
- `kmsg_sample_20`: `7,4398,91533983,-;max77705_fg_read_avg_current: avg_current=-1mA`
- `kmsg_tail_00`: `4,4194,90436241,-; scheduler_thread+0x1b4/0x5a8`
- `kmsg_tail_01`: `4,4195,90436253,-; kthread+0x120/0x138`
- `kmsg_tail_02`: `4,4262,90437165,-; scheduler_thread+0x1b4/0x5a8`
- `kmsg_tail_03`: `4,4263,90437176,-; kthread+0x120/0x138`
- `kmsg_tail_04`: `4,4274,90437426,-;WARNING: CPU: 0 PID: 658 at drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0/components/ipa/core/src/wlan_ipa_core.c:1493 wlan_ipa_cleanup_iface+0x2e8/0x4a8`
- `kmsg_tail_05`: `4,4330,90438151,-; scheduler_thread+0x1b4/0x5a8`
- `kmsg_tail_06`: `4,4331,90438162,-; kthread+0x120/0x138`
- `kmsg_tail_07`: `3,4334,90438204,-;[schedu][0x7c6869f3][00:02:05.705947] wlan: [658:E:IPA] __wlan_ipa_wlan_evt: 2236: wlan_ipa_setup_iface failed 4294967282`
- `kmsg_tail_08`: `6,4355,90527690,-;IPv6: ADDRCONF(NETDEV_CHANGE): wlan0: link becomes ready`
- `kmsg_tail_09`: `6,4369,91509936,-;max77705_fg_periodic_read: skip old(1) current(91)`
- `kmsg_tail_10`: `6,4370,91511332,-;max77705_fg_read_qh : QH(4773000)`
- `kmsg_tail_11`: `7,4372,91511587,-;max77705_fg_read_current: current=5mA`
- `kmsg_tail_12`: `7,4373,91512050,-;max77705_fg_read_avg_current: avg_current=-1mA`
- `kmsg_tail_13`: `6,4374,91512287,-;max77705_fg_read_isys_avg: isys_avg_current=630mA`
- `kmsg_tail_14`: `6,4375,91512528,-;max77705_fg_read_isys: isys_current=890mA`
- `kmsg_tail_15`: `6,4377,91528006,-;max77705_fg_read_vcell: VCELL(4329)mV, data(0xd874)`
- `kmsg_tail_16`: `7,4378,91528474,-;max77705_fg_read_avg_current: avg_current=-1mA`
- `kmsg_tail_17`: `6,4395,91533255,-;sec_bat_get_property: input current(1500mA), cable type(5), slow-charging mode(1)`
- `kmsg_tail_18`: `6,4396,91533273,-;sec_bat_get_property cable type = 5 sleep_mode = 0`
- `kmsg_tail_19`: `7,4397,91533521,-;max77705_fg_read_current: current=5mA`
- `kmsg_tail_20`: `7,4398,91533983,-;max77705_fg_read_avg_current: avg_current=-1mA`

## Supplicant FD Samples

- `start_fd_00`: `2:/cache/a90-wifi/a90_supplicant_execns_stdio.log`
- `wait_fd_00`: `2:/cache/a90-wifi/a90_supplicant_execns_stdio.log`
- `wait_fd_01`: `4:socket_inode=593 eth=4 pid=757 groups=00000000`

## Staging

- `property_archive`: `tmp/wifi/v2167-connect-dhcp-google-ping-handoff-standalone-wpa-v23-2g/property-runtime-v2167.tgz` bytes `12741` chunks `12` staged `1` method `ncm-wget` fast `1` elapsed `1.117`
- `helper_sha256`: `6b655eea64ef3c12ad354e6151085c2aab60aa8c3f57945925ef03fd2789c1af` gzip_len `607578` chunks `528` method `` fast `` elapsed ``
- `strace_stage`: ok `1` reason `already-present` fast `` elapsed ``
- `standalone_wpa_archive`: ok `True` bytes `8179702` sha `c60ca9404eb9ec102662990ff0056afdfebf81d8ac2136be2c8102a7364b8dd6` packages `17` staged `1` fast `1` elapsed `0.652`
- `connect_config`: path `/cache/a90-wifi/v2167.conf` size `236` mode `600` security `wpa-psk` disabled_initially `0` raw_values_logged `0`

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
- `fast-transfer-host-net-existing` rc `0` ok `True` evidence `fast-transfer-host-net-existing.stdout.txt`
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
- `connect-script-touch` rc `1` ok `False` evidence `connect-script-touch.stdout.txt`
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
- `fast-transfer-device-host-probe-after-nm-repair` rc `1` ok `False` evidence `fast-transfer-device-host-probe-after-nm-repair.stdout.txt`
- `fast-transfer-device-host-probe-result-after-nm-repair` rc `1` ok `False` evidence `fast-transfer-device-host-probe-result-after-nm-repair.stdout.txt`
- `fast-upload-v2167-skipped` rc `1` ok `False` evidence `fast-upload-v2167-skipped.stdout.txt`
- `post-rollback-connect-ping-result` rc `0` ok `True` evidence `post-rollback-connect-ping-result.stdout.txt`
- `post-rollback-connect-ping-cleanup` rc `0` ok `True` evidence `post-rollback-connect-ping-cleanup.stdout.txt`

## Cleanup

- `cache_artifacts_removed`: `True`
- `cleanup_skipped_reason`: ``

## Safety

- Wi-Fi credentials are read only from environment variables and are not committed.
- Raw supplicant, kmsg, DHCP, and ping stdout/stderr are summarized with redacted samples; raw supplicant/kmsg files are removed during helper cleanup.
- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action is used.
