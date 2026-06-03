# Native Init V1907 Service-locator Domain Service74 Gap Classifier

## Summary

- Cycle: `V1907`
- Type: host/source classifier over service-locator, ICNSS, service-notifier source and V1904/V1905/V1906 evidence
- Decision: `v1907-servloc-domain-list-missing-service74-host-pass`
- Label: `servloc-domain-list-missing-service74`
- Result: PASS
- Reason: native service-locator returns only msm/modem/wlan_pd instance 180, while Android normal reaches service-notifier 74+180; source shows ICNSS is the only real service-notifier register caller and consumes service-locator domain_list entries
- Evidence: `tmp/wifi/v1907-servloc-domain-service74-gap-classifier`

## Evidence Edge

- V1906 decision/label/pass: `v1906-service74-root-service-publication-edge-host-pass` / `service74-root-service-publication-edge` / `True`
- Android service74/service180/wlan_pd/wlan0: `1` / `1` / `2` / `15.001322`
- Android contamination pre-wlan0 PCIe-MHI/degraded257: `0` / `False`
- Native service180/service74/wlan_pd: `1,1,1` / `0,0,0` / `0,0,0`
- Native service-locator domain count/name/instance/result: `1` / `msm/modem/wlan_pd` / `180` / `domain-list-response-success`
- Native lower gates WLFW69/wlan0: `0` / `0`

## Source Edge

- service-locator sends get-domain-list QMI and copies response entries into `pd->domain_list`: `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/service-locator.c:306`, `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/service-locator.c:135`, `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/service-locator.c:95`, `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/service-locator.c:102`, `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/service-locator.c:104`
- service-locator delivers `LOCATOR_UP` with that domain list to ICNSS: `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/service-locator.c:373`, `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/icnss.c:2060`, `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/icnss.c:1967`
- ICNSS loops over each domain and calls service-notifier with `name` and `instance_id`: `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/icnss.c:2000`, `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/icnss.c:2006`
- service-notifier new-server log exposes the same instance id: `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/service-notifier.c:337`
- real service-notifier register callers: `["kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/icnss.c:2006:\t\t\tservice_notif_register_notifier(pd->domain_list[i].name,"]`

## Selected Diff

- Label: `servloc-domain-list-missing-service74`.
- Native is missing service-locator domain-list entry/instance 74 before service-notifier lookup, listener msg20, wlan_pd state-up msg22, WLFW69, and wlan0.
- Android normal proves that the internal modem can publish both service-notifier instances 74 and 180 before wlan_pd and wlan0 without PCIe/MHI or pm-service msg22.
- The next useful live unit is a read-only internal-modem observer for the service-locator get-domain-list response and ICNSS domain registration arguments.

## Safety Scope

V1907 is host-only. It reads retained manifests and local kernel source only, and writes local evidence/report artifacts. It performs no device command, flash, reboot, tracefs write, service start, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, PMIC/GPIO/GDSC/regulator write, forced RC1/case write, `/dev/subsys_esoc0` open, fake ONLINE state, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, firmware write, boot write, partition write, or restart-PD request.

## Next

- Build the next rollbackable native observer to capture service-locator response domain entries and ICNSS `service_notif_register_notifier` arguments before any functional Wi-Fi bring-up attempt.
- Do not attempt Wi-Fi connect/ping until native init proves WLFW service69 and `wlan0`.
