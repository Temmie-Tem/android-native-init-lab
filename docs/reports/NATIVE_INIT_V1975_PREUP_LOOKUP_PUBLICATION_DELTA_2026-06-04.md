# Native Init V1975 Pre-UP Lookup / WLFW69 Publication Delta

## Summary

- Cycle: `V1975`
- Decision: `v1975-native-dms-wlfw-lookup-present-wlfw69-publication-missing-host-pass`
- Label: `native-dms-wlfw-lookup-present-wlfw69-publication-missing`
- Pass: `True`
- Reason: V1974 Android-good shows pre-UP DMS and WLFW lookups before WLAN-PD UP; V1937 native already reaches DMS and WLFW lookup/wait, but only non-WLFW service publication arrives and WLFW69 never publishes
- Evidence: `tmp/wifi/v1975-preup-lookup-publication-delta`

## Gate

V1974 was the new producer-side measurement requested by the ledger: a normal Android handoff with pre-armed libqmi uprobes. This V1975 reducer uses that new measurement to decide whether native still needs to reproduce the pre-UP DMS/WLFW lookup edge, or whether the remaining delta is specifically WLFW69 publication from the internal modem.

## Matrix

| area | ok | detail |
| --- | --- | --- |
| Android normal | True | wlan_pd=9.587781 wlan0=15.214171 clean=True |
| Android pre-UP DMS | True | lookup=5 found=3 wait_return=1 |
| Android WLFW69 edge | True | pre_lookup=2 wait_return=1 found=4 init_ok=1 |
| Native lookup | True | ids=['0x2', '0x45'] service74=True service180=True pm_open=True |
| Native publication | False | new_ids=['0x3'] wlfw_wait_return=False wlfw69=False wlan_pd=False |

## Android V1974 Edge

- First DMS lookup before `wlan_pd` UP: `<...>-1272  [006] ....     8.830730: libqmi_get_service_list_lookup_call: (0x7633622eec) xport=0x0 xport_id=0x0 svc_id=0x2 idl_version=0x1 capacity_ptr=0x75abcfef5c list_ptr=0x75abcff0a0 lookup_fn=0x7633626a30`
- First DMS found before `wlan_pd` UP: `<...>-1272  [006] ....     9.315096: libqmi_get_service_list_lookup_ret: (0x7633622ef0) found=0x1 list=0x75abcff0a0 capacity_ptr=0x75abcfefd4 count_ptr=0x75abcfefd0 offset=0x0 xport_index=0x0`
- First WLFW lookup before `wlan_pd` UP: `<...>-1273  [006] ....     8.842774: libqmi_get_service_list_lookup_call: (0x7633622eec) xport=0x0 xport_id=0x0 svc_id=0x45 idl_version=0x1 capacity_ptr=0x75abc0399c list_ptr=0x75abc03ae0 lookup_fn=0x7633626a30`
- First WLFW wait return: `<...>-1273  [005] ....     9.589394: libqmi_wait_return: (0x7633624908)`
- First WLFW found: `<...>-1273  [005] ....     9.589619: libqmi_get_service_list_lookup_ret: (0x7633622ef0) found=0x1 list=0x75abc03ae0 capacity_ptr=0x75abc03a14 count_ptr=0x75abc03a10 offset=0x0 xport_index=0x0`
- Explicit `rild` pre-UP lead lookups/sends: `0` / `0`

## Native V1937 Edge

- First DMS lookup: `cnss-daemon-633   [002] ....     6.686065: libqmi_get_service_list_lookup_call: (0x7fa4aaceec) xport=0x0 xport_id=0x0 svc_id=0x2 idl_version=0x1 capacity_ptr=0x7f1bb40f5c list_ptr=0x7f1bb410a0 lookup_fn=0x7fa4ab0a30`
- First WLFW lookup: `cnss-daemon-634   [002] ....     6.681533: libqmi_get_service_list_lookup_call: (0x7fa4aaceec) xport=0x0 xport_id=0x0 svc_id=0x45 idl_version=0x1 capacity_ptr=0x7f1ba4599c list_ptr=0x7f1ba45ae0 lookup_fn=0x7fa4ab0a30`
- First WLFW lookup return: `cnss-daemon-634   [002] ....     6.682540: libqmi_get_service_list_lookup_ret: (0x7fa4aacef0) found=0x0 list=0x7f1ba45ae0 capacity_ptr=0x7f1ba45a14 count_ptr=0x7f1ba45a10 offset=0x0 xport_index=0x0`
- First native wait return: `cnss-daemon-633   [003] ....     7.738428: libqmi_wait_return: (0x7fa4aae908)`
- First native new-server: `cnss-daemon-627   [002] ....     7.738365: libqmi_xport_new_server_service: (0x7fa4aab910) xport=0xb400007fa1083c00 svc_id=3 state=0 addr=548220341088 notifier=545925632048`

## Decision

- Native is not missing the DMS/WLFW libqmi lookup edge; it already reaches `svc_id=0x2` and `svc_id=0x45` with the clean-DSP/service74, PM-open, holder, and cnss-worker stack.
- The retained delta is narrower: Android's WLFW wait returns and finds service `0x45` immediately after `wlan_pd` UP, while native only sees a non-WLFW service arrival and the WLFW worker remains outstanding.
- The next live unit should therefore measure with no AP-side mutation: observe why the internal modem does not publish WLFW69/start `msm/modem/wlan_pd` under the native combo, not another RIL/pm-service/eSoC/PCIe/GDSC path.

## Safety

Host-only reducer. No device command, boot flash, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, `/dev/subsys_esoc0`, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, PMIC/GPIO/GDSC/regulator write, fake ONLINE state, forced RC1/case write, partition write, or sda29 remount-write was performed.
