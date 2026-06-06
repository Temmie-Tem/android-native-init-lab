# Native Init V2167 Connect DHCP Google Ping Handoff

## Summary

- Cycle: `V2167`
- Run label: `qa-hold-v25-2g`
- Decision: `v2167-connect-dhcp-ping-hold-failed`
- Label: `connect-dhcp-ping-hold-failed`
- Pass: `False`
- Reason: native wlan0 associated, DHCP and google.com ping succeeded, but hold failed: ip-ping-failed
- Evidence: `tmp/wifi/v2167-connect-dhcp-google-ping-handoff-qa-hold-v25-2g`
- QA hold config: sec `120` interval `30` reconnect_on_drop `True`
- Result source: `serial-cat` serial_attempts `1` result_left_on_device `False`
- Fast upload: ok `False` reason `device-to-host-ncm-probe-failed-after-nm-repair` elapsed `0.0`
- Fast upload archive: `` bytes `0` receiver_bytes `0` entries `0` secret_hits `[]` forbidden_entries `[]`

## Phase Timers

- `host_property_build` elapsed `0.029` ok `True` detail ``
- `host_property_archive` elapsed `0.019` ok `True` detail ``
- `host_standalone_wpa_bundle` elapsed `3.193` ok `True` detail ``
- `property_stage` elapsed `2.338` ok `True` detail ``
- `host_helper_build` elapsed `8.055` ok `True` detail ``
- `helper_stage` elapsed `2.281` ok `True` detail ``
- `strace_stage` elapsed `1.085` ok `True` detail ``
- `standalone_wpa_stage` elapsed `2.908` ok `True` detail ``
- `fast_transfer_close` elapsed `0.0` ok `True` detail ``
- `prestage_total` elapsed `16.668` ok `True` detail ``
- `connect_config_stage` elapsed `2.76` ok `True` detail ``
- `connect_window` elapsed `219.248` ok `True` detail ``
- `handoff_flash_test_rollback_total` elapsed `358.581` ok `True` detail ``
- `post_rollback_artifact_upload` elapsed `25.095` ok `True` detail ``

## Step Phase Summary

- `preflight_device` elapsed `1.559` steps `3` slow `set-sibling-fwssctl-flag:0.65s, pre-status:0.467s, pre-selftest:0.442s`
- `helper_stage` elapsed `11.902` steps `10` slow `host-build-execns-helper:7.96s, property-runtime-stage-extract:0.656s, property-runtime-fast-wget:0.552s`
- `connect_config_stage` elapsed `2.207` steps `5` slow `connect-config-mkdir:0.56s, connect-config-decode-redacted:0.554s, connect-config-touch-b64:0.55s`
- `flash_total` elapsed `64.813` steps `1` slow `test-flash-from-native:64.813s`
- `connect_window` elapsed `218.247` steps `35` slow `connect-result-wait-polls:152.511s, connect-script-line-00:45.177s, connect-script-touch:3.312s`
- `artifact_upload` elapsed `1.817` steps `16` slow `test-fast-evidence-device-stream:0.743s, test-fast-evidence-collector-fast-wget:0.557s, post-rollback-connect-ping-result:0.516s`
- `rollback_flash_total` elapsed `63.752` steps `1` slow `rollback-from-native:63.752s`
- `rollback_status` elapsed `0.476` steps `1` slow `rollback-status:0.476s`
- `selftest` elapsed `0.878` steps `2` slow `rollback-selftest:0.443s, test-selftest:0.435s`
- `other` elapsed `28.203` steps `30` slow `fast-transfer-device-host-probe-after-nm-repair:10.214s, fast-transfer-device-host-probe:10.121s, test-status:1.131s`

## Native Flash Subphases

- `test-flash-from-native.inspect_local_image` elapsed `0.057` ok `True`
- `test-flash-from-native.native_to_recovery` elapsed `0.302` ok `True`
- `test-flash-from-native.wait_recovery_adb` elapsed `28.123` ok `True`
- `test-flash-from-native.adb_push` elapsed `0.839` ok `True`
- `test-flash-from-native.remote_sha256` elapsed `0.107` ok `True`
- `test-flash-from-native.boot_dd_write` elapsed `0.442` ok `True`
- `test-flash-from-native.boot_readback_sha256` elapsed `0.346` ok `True`
- `test-flash-from-native.flash_boot_image` elapsed `1.734` ok `True`
- `test-flash-from-native.reboot_twrp_to_system` elapsed `2.619` ok `True`
- `test-flash-from-native.verify_native_init` elapsed `31.934` ok `True`
- `test-flash-from-native.total` elapsed `64.77` ok `True`
- `rollback-from-native.inspect_local_image` elapsed `0.056` ok `True`
- `rollback-from-native.native_to_recovery` elapsed `0.303` ok `True`
- `rollback-from-native.wait_recovery_adb` elapsed `28.121` ok `True`
- `rollback-from-native.adb_push` elapsed `0.822` ok `True`
- `rollback-from-native.remote_sha256` elapsed `0.099` ok `True`
- `rollback-from-native.boot_dd_write` elapsed `0.418` ok `True`
- `rollback-from-native.boot_readback_sha256` elapsed `0.341` ok `True`
- `rollback-from-native.flash_boot_image` elapsed `1.681` ok `True`
- `rollback-from-native.reboot_twrp_to_system` elapsed `2.116` ok `True`
- `rollback-from-native.verify_native_init` elapsed `31.431` ok `True`
- `rollback-from-native.total` elapsed `63.708` ok `True`

## Slowest Steps

- `connect-result-wait-polls` elapsed `152.511` ok `True` timeout `False`
- `test-flash-from-native` elapsed `64.813` ok `True` timeout `False`
- `rollback-from-native` elapsed `63.752` ok `True` timeout `False`
- `connect-script-line-00` elapsed `45.177` ok `False` timeout `False`
- `fast-transfer-device-host-probe-after-nm-repair` elapsed `10.214` ok `False` timeout `False`
- `fast-transfer-device-host-probe` elapsed `10.121` ok `False` timeout `False`
- `host-build-execns-helper` elapsed `7.96` ok `True` timeout `False`
- `connect-script-touch` elapsed `3.312` ok `True` timeout `False`
- `test-status` elapsed `1.131` ok `True` timeout `False`
- `standalone-wpa-stage-extract-verify` elapsed `0.754` ok `True` timeout `False`
- `test-fast-evidence-device-stream` elapsed `0.743` ok `True` timeout `False`
- `standalone-wpa-fast-wget` elapsed `0.658` ok `True` timeout `False`

## Gate Results

- `wlan0_seen`: `True` helper_invoked `True` helper_rc `0`
- `executor_result`: `connect-dhcp-ping-failed`
- `association_carrier`: `True` errno `0`
- `country`: `KR` driver_ioctl_rc `0` errno `0` readback `US` get_rc `0`
- `wpa_ctrl`: ready `True` surface `interface` global_path `/tmp/a90-v231-710/root/dev/socket/wpa_wlan0` abstract `False` preclean `none` preclean_errno `0` ping `pong` interface_add_rc `0` interface_add `` after_add_ready `False` after_add_surface `` after_add_global `` after_add_ping `` country_rc `0` reply `unknown` enable `ok` reassociate `ok`
- `wpa_ctrl_path`: dir `/cache/a90-wifi/sockets` interface `/cache/a90-wifi/sockets/wlan0`
- `supplicant`: launch `native-direct-interface-config` driver `nl80211` global_ctrl `none` direct_iface `True` strace `False` strace_output `` android_socket_mode `disabled-native-global-ctrl` android_socket_fd `-2` android_socket_errno `0` alive_start `True` state_start `S` zombie_after_ctrl `False` alive_after_carrier_wait `True` state_after_carrier_wait `S`
- `supplicant_preexec`: path `/cache/a90-wifi/wpa-standalone/wpa_supplicant-a90.sh` path_x `True` path_errno `0` loader_x `True` loader_errno `0` binary_x `True` binary_errno `0` busybox_x `True` busybox_errno `0` urandom_r `True` urandom_errno `0` urandom_mode `666` urandom_rdev `1:9`
- `standalone_wpa`: enabled `1` staged `True` reason `ok` wrapper `/cache/a90-wifi/wpa-standalone/wpa_supplicant-a90.sh` packages `17` version_rc `0` version `Could_not_open_/dev/urandom.`
- `supplicant_hidl`: hwservicemanager_started `False` mode `not-needed` pid `-1` add_rc `0` service_found `False` descriptor `` instance `` transaction_ok `False` status `` iface_handle `False` result `skipped` reason `manual-hidl-add-disabled-for-direct-interface-route` after_add_fd `4` after_add_netlink `0` after_add_genl `0`
- `supplicant_hidl_vendor`: service_found `False` descriptor `` instance ``
- `supplicant_proc_start`: comm `a90_strace_v216` exe `a90_strace_v2167` has_wpa `True` has_helper `False` has_config `True`
- `supplicant_proc_start_runtime`: uid `0?0?0?0` gid `0?0?0?0` groups `` wchan `do_wait` syscall `260 0xffffffffffffffff 0x7fecf250d4 0x40000000 0x0 0x0 0x0 0x7fecf25080 0x4e5688` stack `[<0000000000000000>] __switch_to+0x10c/0x120` fd_count `4` socket_fds `0` netlink_fds `0` generic_netlink_fds `0` netlink_miss `0` wpa_socket_fds `0` stdio_fds `1`
- `supplicant_proc_after_wait`: comm `a90_strace_v216` exe `a90_strace_v2167` has_wpa `True` has_helper `False` has_config `True`
- `supplicant_proc_after_wait_runtime`: uid `0?0?0?0` gid `0?0?0?0` groups `` wchan `do_wait` syscall `260 0xffffffffffffffff 0x7fecf250d4 0x40000000 0x0 0x0 0x0 0x7fecf25080 0x4e5688` stack `[<0000000000000000>] __switch_to+0x10c/0x120` fd_count `4` socket_fds `0` netlink_fds `0` generic_netlink_fds `0` netlink_miss `0` wpa_socket_fds `0` stdio_fds `1`
- `supplicant_log`: present `False` size `0` lines `0` ctrl `0` ctrl_err `0` nl80211 `0` scan `0` auth `0` assoc `0` connected `0` disconnected `0` fail `0` permission `0` avc `0` samples `0` tail_samples `0` nonproperty_samples `0` sensitive_skipped `0`
- `supplicant_stdio`: present `True` size `70707` lines `876` ctrl `8` ctrl_err `0` config_err `1` nl80211 `296` scan `40` auth `17` assoc `22` connected `4` disconnected `3` fail `2` usage `0` interface `16` socket `9` terminate `0` permission `0` avc `0` samples `24` tail_samples `24` nonproperty_samples `24` sensitive_skipped `83`
- `logdw_sink`: started `True` errno `0` datagrams `22` bytes `1744` wpa `0` supplicant `0` nl80211 `6` ctrl `0` interface `0` fail `8` permission `0` hidl `0` service_manager `0` samples `14` sensitive_skipped `0` drain_errno `0`
- `kmsg_stream`: started `True` start_errno `0` present `True` size `96294` lines `1251` permission `0` avc `0` nl80211 `0` auth `3` assoc `6` fail `328` sensitive_skipped `19` cleanup_exit `-1` signal `15` timeout `False`
- `dhcp_executed`: `True` dhcp_rc `0` resolv_present `True` resolv_errno `0` resolv_size `48` nameservers `2`
- `external_ping_executed`: `True` target `google.com` rc `0` classifier `icmp-reply` output_present `True` output_errno `0` bytes_from `True` bad_address `False` unknown_host `False` net_unreach `False` sendto `False` zero_recv `False` loss100 `False`
- `hold`: enabled `True` executed `True` requested_sec `120` interval_sec `30` pass `False` reason `ip-ping-failed` samples `4` carrier_up `4` carrier_down `0` host_ping_success `1` host_ping_fail `3` ip_ping_success `1` ip_ping_fail `3` reconnect_on_drop `True` reconnect_attempts `0` reconnect_success `0` first_fail_sample `1` first_fail_errno `0` first_fail_ping_rc `1`
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

- `tail_00`: `1518764817.715896: nl80211: Operating frequency for the associated BSS from scan results: 2412 MHz`
- `tail_01`: `1518764817.718109: nl80211: Associated on 2412 MHz`
- `tail_02`: `1518764817.723402: nl80211: Set wlan0 operstate 0->0 (DORMANT)`
- `tail_03`: `1518764817.731234: WPA: Update cipher suite selection based on IEs in driver-generated WPA/RSNE in AssocReq - hexdump(len=73): 30 16 01 00 00 0f ac 04 01 00 00 0f ac 04 01 00 00 0f ac 02 0c 00 00 00 32 04 30 48 60 6c 3b 16 53 51 53 54 73 74 75 76 77 78 79`
- `tail_04`: `1518764817.738959: EAPOL: SUPP_PAE entering state CONNECTING`
- `tail_05`: `1518764817.740808: wlan0: CTRL-EVENT-SUBNET-STATUS-UPDATE status=0`
- `tail_06`: `1518764817.776217: wlan0: WPA: Installing PTK to the driver`
- `tail_07`: `1518764817.777487: nl80211: NEW_KEY`
- `tail_08`: `1518764817.777660: nl80211: KEY_DATA - hexdump(len=16): [REMOVED]`
- `tail_09`: `1518764817.777868: nl80211: KEY_SEQ - hexdump(len=6): 00 00 00 00 00 00`
- `tail_10`: `1518764817.789993: wlan0: WPA: Installing GTK to the driver (keyidx=1 tx=0 len=16)`
- `tail_11`: `1518764817.792713: nl80211: NEW_KEY`
- `tail_12`: `1518764817.792895: nl80211: KEY_DATA - hexdump(len=16): [REMOVED]`
- `tail_13`: `1518764817.793075: nl80211: KEY_SEQ - hexdump(len=6): 06 00 00 00 00 00`
- `tail_14`: `1518764817.799623: wlan0: Radio work 'connect'@0x557a690610 done in 0.380675 seconds`
- `tail_15`: `1518764817.800069: wlan0: radio_work_free('connect'@0x557a690610): num_active_works --> 0`
- `tail_16`: `1518764817.800995: nl80211: Set wlan0 operstate 0->1 (UP)`
- `tail_17`: `1518764817.812338: nl80211: Set rekey offload`
- `tail_18`: `1518764817.814834: nl80211: Set IF_OPER_UP again based on ifi_flags and expected operstate`
- `tail_19`: `1518764817.816769: nl80211: Event message available`
- `tail_20`: `1518764817.821104: nl80211: Drv Event 103 (NL80211_CMD_VENDOR) received for wlan0`
- `tail_21`: `1518764817.821298: nl80211: Vendor event: wiphy=0 vendor_id=0x1374 subcmd=165`
- `tail_22`: `1518764817.821477: nl80211: Vendor data - hexdump(len=48): 30 00 01 00 2c 00 00 00 08 00 01 00 00 00 00 00 08 00 02 00 01 00 00 00 18 00 03 00 14 00 00 00 08 00 01 00 09 00 00 00 08 00 02 00 6c 09 00 00`
- `tail_23`: `1518764817.824288: nl80211: Ignore unsupported QCA vendor event 165`

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

- `logdw_sample_00`: `ZLT cnss-daemon nl80211 response handler invoked`
- `logdw_sample_01`: `Z;w cnss-daemon nl80211_response_handler: cmd 103, vendorID 4980, subcmd 106  received`
- `logdw_sample_02`: `Z X CNSS failed to open file a+ mode or file size 0 is less than max_file_size 31457280`
- `logdw_sample_03`: `Z Y CNSS Failed to open file /data/vendor/log/wifi/host_driver_logs_current.txt: 2`
- `logdw_sample_04`: `Z cnss-daemon nl80211 response handler invoked`
- `logdw_sample_05`: `Z a cnss-daemon nl80211_response_handler: cmd 103, vendorID 4980, subcmd 107  received`
- `logdw_sample_06`: `Z t. cnss-daemon nl80211 response handler invoked`
- `logdw_sample_07`: `Z .u. cnss-daemon nl80211_response_handler: cmd 103, vendorID 4980, subcmd 165  received`
- `logdw_sample_08`: `ZV \ CNSS failed to open file a+ mode or file size 0 is less than max_file_size 31457280`
- `logdw_sample_09`: `Zf=\ CNSS Failed to open file /data/vendor/log/wifi/host_driver_logs_current.txt: 2`
- `logdw_sample_10`: `Z O_ CNSS failed to open file a+ mode or file size 0 is less than max_file_size 31457280`
- `logdw_sample_11`: `Z w_ CNSS Failed to open file /data/vendor/log/wifi/host_driver_logs_current.txt: 2`
- `logdw_sample_12`: `Z rb CNSS failed to open file a+ mode or file size 0 is less than max_file_size 31457280`
- `logdw_sample_13`: `Z b CNSS Failed to open file /data/vendor/log/wifi/host_driver_logs_current.txt: 2`
- `kmsg_sample_00`: `4,4357,90456459,-; scheduler_thread+0x1b4/0x5a8`
- `kmsg_sample_01`: `4,4358,90456471,-; kthread+0x120/0x138`
- `kmsg_sample_02`: `4,4425,90457346,-; scheduler_thread+0x1b4/0x5a8`
- `kmsg_sample_03`: `4,4426,90457357,-; kthread+0x120/0x138`
- `kmsg_sample_04`: `4,4437,90457589,-;WARNING: CPU: 0 PID: 656 at drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0/components/ipa/core/src/wlan_ipa_core.c:1493 wlan_ipa_cleanup_iface+0x2e8/0x4a8`
- `kmsg_sample_05`: `4,4493,90458308,-; scheduler_thread+0x1b4/0x5a8`
- `kmsg_sample_06`: `4,4494,90458319,-; kthread+0x120/0x138`
- `kmsg_sample_07`: `3,4497,90458410,-;[schedu][0x7c6ca821][07:06:57.705959] wlan: [656:E:IPA] __wlan_ipa_wlan_evt: 2236: wlan_ipa_setup_iface failed 4294967282`
- `kmsg_sample_08`: `6,4520,90553887,-;IPv6: ADDRCONF(NETDEV_CHANGE): wlan0: link becomes ready`
- `kmsg_sample_09`: `6,4525,91530078,-;max77705_fg_periodic_read: skip old(1) current(91)`
- `kmsg_sample_10`: `6,4526,91531455,-;max77705_fg_read_qh : QH(4777000)`
- `kmsg_sample_11`: `7,4528,91531711,-;max77705_fg_read_current: current=0mA`
- `kmsg_sample_12`: `7,4529,91532172,-;max77705_fg_read_avg_current: avg_current=0mA`
- `kmsg_sample_13`: `6,4530,91532409,-;max77705_fg_read_isys_avg: isys_avg_current=625mA`
- `kmsg_sample_14`: `6,4531,91532649,-;max77705_fg_read_isys: isys_current=906mA`
- `kmsg_sample_15`: `6,4533,91548107,-;max77705_fg_read_vcell: VCELL(4328)mV, data(0xd86a)`
- `kmsg_sample_16`: `7,4534,91548571,-;max77705_fg_read_avg_current: avg_current=0mA`
- `kmsg_sample_17`: `6,4551,91553423,-;sec_bat_get_property: input current(1500mA), cable type(5), slow-charging mode(1)`
- `kmsg_sample_18`: `6,4552,91553441,-;sec_bat_get_property cable type = 5 sleep_mode = 0`
- `kmsg_sample_19`: `7,4553,91553689,-;max77705_fg_read_current: current=0mA`
- `kmsg_sample_20`: `7,4554,91554205,-;max77705_fg_read_avg_current: avg_current=0mA`
- `kmsg_sample_21`: `14,4586,97062233,-;rmt_storage:INFO:rmt_storage_client_thread: Calling Write [offset=0, size=2097152, req_h 0x9, wr_count 1] for /boot/modem_fs2!`
- `kmsg_sample_22`: `14,4587,97110333,-;rmt_storage:INFO:rmt_storage_client_thread: Done Write (bytes = 2097152, req_h 0x9, wr_count 1) for /boot/modem_fs2!`
- `kmsg_sample_23`: `6,4633,121554527,-;max77705_fg_periodic_read: skip old(1) current(121)`
- `kmsg_tail_00`: `6,5402,221514275,-;failed to send QMI message -104`
- `kmsg_tail_01`: `3,5403,221514289,-;qmi_sensors:qmi_ts_request qmi txn send failed for pa_1 ret:-104`
- `kmsg_tail_02`: `6,5404,221616011,-;failed to send QMI message -104`
- `kmsg_tail_03`: `3,5405,221616024,-;qmi_sensors:qmi_ts_request qmi txn send failed for pa ret:-104`
- `kmsg_tail_04`: `6,5406,221713316,-;failed to send QMI message -104`
- `kmsg_tail_05`: `3,5407,221713329,-;qmi_sensors:qmi_ts_request qmi txn send failed for pa_1 ret:-104`
- `kmsg_tail_06`: `6,5408,221815558,-;failed to send QMI message -104`
- `kmsg_tail_07`: `3,5409,221815571,-;qmi_sensors:qmi_ts_request qmi txn send failed for pa ret:-104`
- `kmsg_tail_08`: `6,5413,223923930,-;failed to send QMI message -104`
- `kmsg_tail_09`: `3,5414,223923944,-;qmi_sensors:qmi_ts_request qmi txn send failed for pa_1 ret:-104`
- `kmsg_tail_10`: `6,5415,224025599,-;failed to send QMI message -104`
- `kmsg_tail_11`: `3,5416,224025612,-;qmi_sensors:qmi_ts_request qmi txn send failed for pa ret:-104`
- `kmsg_tail_12`: `6,5417,224123078,-;failed to send QMI message -104`
- `kmsg_tail_13`: `3,5418,224123091,-;qmi_sensors:qmi_ts_request qmi txn send failed for pa_1 ret:-104`
- `kmsg_tail_14`: `6,5419,224225552,-;failed to send QMI message -104`
- `kmsg_tail_15`: `3,5420,224225565,-;qmi_sensors:qmi_ts_request qmi txn send failed for pa ret:-104`
- `kmsg_tail_16`: `6,5424,226333917,-;failed to send QMI message -104`
- `kmsg_tail_17`: `3,5425,226333931,-;qmi_sensors:qmi_ts_request qmi txn send failed for pa_1 ret:-104`
- `kmsg_tail_18`: `6,5426,226435850,-;failed to send QMI message -104`
- `kmsg_tail_19`: `3,5427,226435863,-;qmi_sensors:qmi_ts_request qmi txn send failed for pa ret:-104`
- `kmsg_tail_20`: `6,5428,226533249,-;failed to send QMI message -104`
- `kmsg_tail_21`: `3,5429,226533262,-;qmi_sensors:qmi_ts_request qmi txn send failed for pa_1 ret:-104`
- `kmsg_tail_22`: `6,5430,226635559,-;failed to send QMI message -104`
- `kmsg_tail_23`: `3,5431,226635572,-;qmi_sensors:qmi_ts_request qmi txn send failed for pa ret:-104`

## Supplicant FD Samples

- `start_fd_00`: `2:/cache/a90-wifi/a90_supplicant_execns_stdio.log`
- `wait_fd_00`: `2:/cache/a90-wifi/a90_supplicant_execns_stdio.log`

## Staging

- `property_archive`: `tmp/wifi/v2167-connect-dhcp-google-ping-handoff-qa-hold-v25-2g/property-runtime-v2167.tgz` bytes `12724` chunks `12` staged `1` method `ncm-wget` fast `1` elapsed `1.125`
- `helper_sha256`: `1f9fa01681c9ceb630d194fbf0fd371b02b10c5234108e2f97561172674194e9` gzip_len `609234` chunks `529` method `ncm-wget` fast `1` elapsed `0.552`
- `strace_stage`: ok `1` reason `already-present` fast `` elapsed ``
- `standalone_wpa_archive`: ok `True` bytes `8179676` sha `48afc387ecaf342c775e0c9e2484d773b2659a23b7e489b5462a133d19942b42` packages `17` staged `1` fast `1` elapsed `0.659`
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
- `connect-script-line-25` rc `0` ok `True` evidence `connect-script-line-25.stdout.txt`
- `connect-script-line-26` rc `0` ok `True` evidence `connect-script-line-26.stdout.txt`
- `connect-script-line-27` rc `0` ok `True` evidence `connect-script-line-27.stdout.txt`
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
