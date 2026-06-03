# Native Init V1932 Servnotif/ICNSS Source Gap

## Summary

- Cycle: `V1932`
- Decision: `v1932-servnotif-icnss-domainlist-to-wlfw69-publication-gap-host-pass`
- Label: `servnotif-icnss-domainlist-to-wlfw69-publication-gap`
- Pass: `True`
- Reason: source maps the ICNSS service-locator -> service-notifier -> SERVREG state-up -> WLFW69 path; Android normal proves the edge, but Android kernel kprobes are unavailable and native reaches A1+WLFW lookup while service69/WLAN-PD publication stays absent
- Evidence: `tmp/wifi/v1932-servnotif-icnss-source-gap`

## Source Chain

| anchor | present | line | meaning |
| --- | --- | --- | --- |
| icnss_register_callback | True | kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/icnss.c:1998 | ICNSS installs the callback used for WLAN-PD service state notifications |
| icnss_register_notifier | True | kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/icnss.c:2006 | ICNSS registers each service-locator domain name/instance with service-notifier |
| icnss_state_up_callback | True | kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/icnss.c:1962 | ICNSS observes SERVREG UP by clearing FW_DOWN in the notifier callback |
| servnotif_public_api | True | kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/service-notifier.c:678 | Kernel clients enter the service-notifier path through service_notif_register_notifier |
| servnotif_new_server | True | kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/service-notifier.c:327 | QMI name-service arrival for SERVREG notifier instance queues listener registration |
| servnotif_new_server_print | True | kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/service-notifier.c:337 | The Android/native 180 and 74 dmesg lines print runtime instance_id here |
| servnotif_root_indication | True | kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/service-notifier.c:224 | Remote SERVREG state-up indications enter HLOS through root_service_service_ind_cb |
| servnotif_indication_print | True | kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/service-notifier.c:237 | The Android WLAN-PD state-up dmesg line is emitted here |
| servnotif_servreg_lookup | True | kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/service-notifier.c:545 | service-notifier asks QRTR for SERVREG notifier service 0x42 with runtime instance |
| servreg_service_id | True | kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/service-notifier-private.h:18 | The service-notifier lookup service id is fixed 0x42; 180/74 are runtime instances |
| cnss_wlfw_new_server | True | kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/net/wireless/cnss2/qmi.c:1678 | CNSS handles WLFW service 69 publication in wlfw_new_server |
| cnss_wlfw_lookup | True | kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/net/wireless/cnss2/qmi.c:1734 | CNSS waits for WLFW service 0x45/69 after the userspace worker starts |

## Retained Evidence

| area | pass | detail |
| --- | --- | --- |
| Android trace | True | 180=1 74=1 wlan_pd=2 wlanmdsp=10 pcie_mhi_before_wlan0=0 |
| Android tracefs | True | kprobe_events=0 uprobe_events=1 available_filter_functions=0 |
| Native A1 wait | True | service74=True pm_open=True holder=True worker=1 ind=0 cap=0 |
| Native publication | True | lookup69=True new69=False servnotif=uninit/0 servloc=msm/modem/wlan_pd:180 |

## Decision

- The Android state-up edge is not a pm-service/msg22/eSoC/PCIe/GDSC path. Source maps it to ICNSS registering the `msm/modem/wlan_pd` service-locator domain with service-notifier, then receiving a SERVREG state-up indication.
- Native already reaches the A1 surface: clean-DSP/sibling-sysmon service74/service180, PM `/dev/subsys_modem` open, modem holder, DMS request, and CNSS WLFW worker/service69 lookup.
- The missing transition is remote publication/state-up: no `root_service_service_ind_cb` WLAN-PD indication and no WLFW service69 `new_server` before the worker can send indication/capability QMI.
- Android kernel kprobe observation is not available from retained tracefs (`kprobe_events=0`), so the next live unit should be native-side and source-aligned.

## Next Read-Only Unit

- Prefer native helper-mounted tracefs if available: observe `service_notif_register_notifier`, `service_notifier_new_server`, `root_service_service_ind_cb`, `qmi_add_lookup` for SERVREG 0x42/instance 180, and `wlfw_new_server`/WLFW 0x45.
- If kernel kprobes are unavailable, fall back to native dmesg/QRTR/libqmi wait snapshots around the same A1 boot window.
- Stop before Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping until native exposes WLFW69/WLAN-PD and `wlan0`.

## Safety Scope

Host-only. This classifier reads retained manifests and local source text only. It does not issue live device commands, flash, reboot, stage properties, write firmware/partitions, remount-write, open `/dev/subsys_esoc0`, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, external ping, force RC1/case, touch PMIC/GPIO/GDSC/regulators, rescan PCI, bind/unbind platforms, fake ONLINE, or send eSoC notify/BOOT_DONE.
