# Native Init V1976 Lower Publication Context Handoff

## Summary

- Cycle: `V1976`
- Decision: `v1976-native-service74-dms-wlfw-no-pdmapper-domain-wlanpd-publication-rollback-pass`
- Label: `native-service74-dms-wlfw-no-pdmapper-domain-wlanpd-publication`
- Pass: `True`
- Reason: native rerun reproduced service74/180, PM open, DMS/WLFW lookup, and WLFW wait, but lower klog has no pd-mapper/domain/wlan_pd/QMI-server publication text and no WLFW69/wlanmdsp/wlan0
- Evidence: `tmp/wifi/v1976-lower-publication-context-handoff`
- V1937 manifest: `tmp/wifi/v1976-lower-publication-context-handoff/manifest-v1937.json`
- Inner handoff: `tmp/wifi/v1976-lower-publication-context-handoff/v1936-handoff/manifest.json`

## Gate

V1975 showed native is not missing DMS/WLFW libqmi service discovery. V1976 reruns the same internal-modem native combo and classifies whether the lower publication context advances into pd-mapper/domain/wlan_pd/QMI-server text before WLFW69 remains absent.

## Matrix

| area | value | detail |
| --- | --- | --- |
| label | native-service74-dms-wlfw-no-pdmapper-domain-wlanpd-publication | native rerun reproduced service74/180, PM open, DMS/WLFW lookup, and WLFW wait, but lower klog has no pd-mapper/domain/wlan_pd/QMI-server publication text and no WLFW69/wlanmdsp/wlan0 |
| combined | True | service74=True service180=True pm_open=True lookup_ids=['0x2', '0x45'] |
| publication | False | wlfw69=False wlan_pd=False wlanmdsp=False wlan0=False |
| lower-domain | False | pd_mapper=0,0,0 domain=0,0,0 qmi_server=0,0,0 |
| safety | True | no_esoc0_open/no_fake_online/no_pmic_gpio_gdsc_write stayed asserted |

## Lower Klog Samples

| phase | service text | publication text | first missing-focus line |
| --- | --- | --- | --- |
| after_holder_start | 180=1 74=1 qmi=1 | pd_mapper=0 domain=0 qmi_server=0 wlan_pd=0 | missing |
| after_early_listener | 180=1 74=1 qmi=1 | pd_mapper=0 domain=0 qmi_server=0 wlan_pd=0 | missing |
| after_post_listener_window | 180=1 74=1 qmi=1 | pd_mapper=0 domain=0 qmi_server=0 wlan_pd=0 | missing |

## Key Edges

- First DMS lookup: `cnss-daemon-631   [000] ....     6.748075: libqmi_get_service_list_lookup_call: (0x7fba192eec) xport=0x0 xport_id=0x0 svc_id=0x2 idl_version=0x1 capacity_ptr=0x7f301ccf5c list_ptr=0x7f301cd0a0 lookup_fn=0x7fba196a30`
- First WLFW lookup: `cnss-daemon-632   [002] ....     6.744271: libqmi_get_service_list_lookup_call: (0x7fba192eec) xport=0x0 xport_id=0x0 svc_id=0x45 idl_version=0x1 capacity_ptr=0x7f300d199c list_ptr=0x7f300d1ae0 lookup_fn=0x7fba196a30`
- First WLFW return: `cnss-daemon-632   [000] .n..     6.745953: libqmi_get_service_list_lookup_ret: (0x7fba192ef0) found=0x0 list=0x7f300d1ae0 capacity_ptr=0x7f300d1a14 count_ptr=0x7f300d1a10 offset=0x0 xport_index=0x0`
- First non-WLFW new-server: `cnss-daemon-625   [000] ....     7.735723: libqmi_xport_new_server_service: (0x7fba191910) xport=0xb400007fb5683c00 svc_id=3 state=0 addr=548579482464 notifier=546268041264`

## Decision

- Native rerun again reaches the internal-modem combo: service74/180, `/dev/subsys_modem` PM open, DMS lookup, and WLFW service69 wait.
- The missing edge is below that: no pd-mapper/domain/wlan_pd/QMI-server publication text appears, and WLFW69/wlanmdsp/wlan0 remain absent.
- Next live unit should pre-arm a safe native wrapper/strace around `pd-mapper` and `tftp_server` in this same combo to observe whether the modem ROOT-PD asks AP pd-mapper for wlan_pd and whether any `wlanmdsp.mbn` request is attempted. Do not revisit RIL, pm-service retries, eSoC/PCIe/MHI/GDSC, or Wi-Fi HAL/scan/connect before WLFW69 and `wlan0` exist.

## Safety

- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping was used.
- No `/dev/subsys_esoc0` open/control, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, platform bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.
- Mutation scope: `/cache` one-shot clean-DSP flag, V1936 test-boot flash-handoff, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.
