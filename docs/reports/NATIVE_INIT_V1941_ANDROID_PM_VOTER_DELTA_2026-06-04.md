# Native Init V1941 Android PM Voter Delta

## Summary

- Cycle: `V1941`
- Type: host-only classifier over normal Android PerMgrSrv logcat and native V1937 cnss PM uprobes
- Decision: `v1941-android-qcril-vote-visible-native-absent-sdx50m-coupled-host-pass`
- Label: `android-qcril-vote-visible-native-absent-sdx50m-coupled`
- Pass: `True`
- Reason: native already proves cnss-daemon PM client register/connect success and /dev/subsys_modem open, while normal Android shows an additional QCRIL modem vote before wlanmdsp; that vote is coupled to SDX50M in the same normal log, so it is a read-only source/diff lead, not a permissible direct trigger
- Evidence: `tmp/wifi/v1941-android-pm-voter-delta`

## Matrix

| area | value | detail |
| --- | --- | --- |
| label | android-qcril-vote-visible-native-absent-sdx50m-coupled | native already proves cnss-daemon PM client register/connect success and /dev/subsys_modem open, while normal Android shows an additional QCRIL modem vote before wlanmdsp; that vote is coupled to SDX50M in the same normal log, so it is a read-only source/diff lead, not a permissible direct trigger |
| Android cnss PM vote | True | PM-PROXY online, cnss-daemon registered/voted before wlanmdsp |
| Native cnss PM success | True | pm_client_register/connect/return rc=0 plus /dev/subsys_modem holder |
| Android QCRIL delta | True | QCRIL modem vote appears before wlanmdsp |
| QCRIL SDX50M coupling | True | same Android window also votes SDX50M; direct execution is forbidden |
| Native QCRIL absent | True | no QCRIL/PM-PROXY/voting text in native helper evidence |
| Native downstream absent | True | wlfw69=False wlan0=False |
| Post-180 gap | True | post180-remote-servreg-stateup-producer-missing |

## Marker Rows

| marker | count | time | first line |
| --- | --- | --- | --- |
| android_pm_proxy_vote | 1 | 06-04 02:03:50.337 | 06-04 02:03:50.337   926   964 D PerMgrSrv: PM-PROXY-THREAD voting for modem |
| android_cnss_vote | 2 | 06-04 02:03:50.798 | 06-04 02:03:50.798  1184  1184 D PerMgrLib: cnss-daemon voting for modem |
| android_qcril_modem_vote | 1 | 06-04 02:03:50.850 | 06-04 02:03:50.850   926   964 D PerMgrSrv: QCRIL voting for modem |
| android_qcril_sdx50m_vote | 1 | 06-04 02:03:50.850 | 06-04 02:03:50.850   926   964 D PerMgrSrv: QCRIL voting for SDX50M |
| android_wlanmdsp | 10 | 06-04 02:03:51.389 | 06-04 02:03:51.389   965  1419 I tftp_server: pid=965 tid=1419 tftp-server : INF :[tftp_server_utils.c, 113] file [readonly/vendor/firmware_mnt/image/wlanmdsp.mbn] : [/vendor/rfs/msm/mpss/readonly/vendor |
| native_pm_register_ret0 | 1 |  | wlan_pd_cnss_nonlog_control_flow.uprobe.pm_init_pm_client_register_retcheck.first_hit_line=     cnss-daemon-623   [002] ....     6.679141: pm_init_pm_client_register_retcheck: (0x558f2af628) rc=0x0 |
| native_pm_connect_ret0 | 1 |  | wlan_pd_cnss_nonlog_control_flow.uprobe.pm_init_pm_client_connect_retcheck.first_hit_line=     cnss-daemon-623   [002] ....     6.680123: pm_init_pm_client_connect_retcheck: (0x558f2af654) rc=0x0 |
| native_pm_return0 | 1 |  | wlan_pd_cnss_nonlog_control_flow.uprobe.pm_init_return_path.first_hit_line=     cnss-daemon-623   [002] ....     6.680130: pm_init_return_path: (0x558f2af554) rc=0x0 |
| native_qcril_text | 0 |  | missing |

## Interpretation

- This does not make QCRIL a permitted direct trigger. The normal Android line that votes QCRIL for modem is immediately coupled to a QCRIL vote for SDX50M.
- The useful result is narrower: native already matches the cnss-daemon PM-client success path, so the next host/source comparison should extract what QCRIL contributes to internal-modem WLAN-PD state-up without starting QCRIL on native.
- Any live follow-up must stay read-only and must not open `/dev/subsys_esoc0`, start SDX50M/eSoC/PCIe paths, invoke Wi-Fi HAL, scan/connect, use credentials, DHCP/routes, external ping, or call restart-PD.

## Inputs

- Android logcat: `tmp/wifi/v1934-android-libqmi-service69-positive-control-live-20260603-170139/android-postfs-evidence/a90-v1934-libqmi69/logcat-filtered.txt`
- Native helper: `tmp/wifi/v1937-icnss-ipc-service69-integration/v1936-handoff/test-v1393-helper-result.stdout.txt`
- Native manifest: `tmp/wifi/v1937-icnss-ipc-service69-integration/manifest.json`
- V1940 manifest: `tmp/wifi/v1940-post180-servreg-producer-gap/manifest.json`

## Safety Scope

Host-only parser. No live device command, flash, reboot, QCRIL start, firmware/partition write, remount-write, `/dev/subsys_esoc0`, eSoC/PCIe/GDSC/PMIC/GPIO/regulator action, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, or restart-PD request was used.
