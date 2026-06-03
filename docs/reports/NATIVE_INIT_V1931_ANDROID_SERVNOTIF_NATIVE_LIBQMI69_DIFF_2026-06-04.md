# Native Init V1931 Android Servnotif vs Native Libqmi69 Diff

## Summary

- Cycle: `V1931`
- Decision: `v1931-android-servnotif-stateup-native-libqmi69-publication-missing-host-pass`
- Label: `android-servnotif-stateup-native-libqmi69-publication-missing`
- Pass: `True`
- Reason: Android normal publishes service-notifier 180/74 and reaches WLAN-PD, while native reaches service69 lookup but never gets service69/QRTR69 publication
- Evidence: `tmp/wifi/v1931-android-servnotif-native-libqmi69-diff`

## Matrix

| area | value | detail |
| --- | --- | --- |
| label | android-servnotif-stateup-native-libqmi69-publication-missing | Android normal publishes service-notifier 180/74 and reaches WLAN-PD, while native reaches service69 lookup but never gets service69/QRTR69 publication |
| android_stateup | True | service180=1 service74=1 wlan_pd=2 wlanmdsp=10 |
| android_servloc | True | instances=[180] names=['msm/modem/wlan_pd'] degraded=False pcie_mhi_before_wlan0=0 |
| native_lookup | True | service74=True service180=True servloc=domain-list-response-success:180 lookup_ids=['0x2', '0x45'] |
| native_publication | False | new_server_ids=['0x3'] new69=False qrtr69=0,0 wlan_pd=False wlanmdsp=False wlan0=False |

## Android Normal Edge

- Service-notifier 180: `[    7.373758]  [5: kworker/u16:10:  342] service-notifier: service_notifier_new_server: Connection established between QMI handle and 180 service`
- Service-notifier 74: `[    7.374392]  [5: kworker/u16:10:  342] service-notifier: service_notifier_new_server: Connection established between QMI handle and 74 service`
- WLAN-PD indication: `[    9.714467]  [5: kworker/u16:11:  343] service-notifier: root_service_service_ind_cb: Indication received from msm/modem/wlan_pd, state: 0x1fffffff, trans-id: 1`
- First wlanmdsp: `06-03 22:10:16.531   952  1449 I tftp_server: pid=952 tid=1449 tftp-server : INF :[tftp_server_utils.c, 113] file [readonly/vendor/firmware_mnt/image/wlanmdsp.mbn] : [/vendor/rfs/msm/mpss/readonly/vendor`
- `service_notif_register_notifier` owner: `builtin`

## Native Missing Edge

- First service69 lookup: `cnss-daemon-637   [003] ....     6.783727: libqmi_get_service_list_lookup_call: (0x7fa9f6deec) xport=0x0 xport_id=0x0 svc_id=0x45 idl_version=0x1 capacity_ptr=0x7f1f4e199c list_ptr=0x7f1f4e1ae0 lookup_fn=0x7fa9f71a30`
- First non-WLFW new-server: `cnss-daemon-630   [003] ....     7.694030: libqmi_xport_new_server_service: (0x7fa9f6c910) xport=0xb400007fa6283c00 svc_id=3 state=0 addr=548315802464 notifier=545987088432`
- Native service IDs: lookup `['0x2', '0x45']`, new-server `['0x3']`
- Native servnotif state/indication: `uninit` / `0`

## Decision

- This closes the retained-host comparison: Android normal has the built-in service-notifier publication path; native reaches the WLFW service69 lookup but lacks the corresponding service69/QRTR69 publication.
- The next useful unit is a read-only source/caller observer for who emits the Android service-notifier 180 -> WLAN-PD publication edge, not another pm-service/msg22 or eSoC/PCIe/GDSC path.
- Do not attempt Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping until native exposes service69/WLAN-PD and `wlan0`.

## Safety

- Host-only reparse of retained Android and native manifests; no boot, flash, device write, Wi-Fi HAL, scan/connect, credential handling, DHCP/routes, external ping, `/dev/subsys_esoc0`, PCIe/MHI/eSoC, PMIC/GPIO/GDSC/regulator action, forced RC1/case, or platform bind/unbind was used.
