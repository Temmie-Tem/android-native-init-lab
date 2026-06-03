# Native Init V1911 Service74 Caller Boundary Classifier

## Summary

- Cycle: `V1911`
- Type: host-only source/evidence classifier for service-notifier instance 74 caller boundary
- Decision: `v1911-service74-pre-wlanpd-caller-boundary-host-pass`
- Label: `service74-pre-wlanpd-caller-boundary`
- Result: `PASS`
- Reason: service74 publishes before wlan_pd while early wlan/fw locator response is 180-only; OSRC exposes only the ICNSS domain-list caller plus an exported notifier API, and stock kernel tracing cannot capture a kernel caller stack
- Evidence: `tmp/wifi/v1911-service74-caller-boundary-classifier`

## Android-good Edge

| field | value |
| --- | --- |
| manifest | tmp/wifi/v1910-android-early-servloc-domain-handoff-live-20260603-214749/manifest.json |
| decision/pass/label | v1910-android-early-servloc-180-only-after-service74-before-wlanpd-pass/True/android-early-servloc-180-only-after-service74-before-wlanpd |
| early query instances/domain74/domain180 | [180]/False/True |
| time service180/service74/query/wlan_pd/wlan0 | 7.209919/7.211039/7.213/9.567936/15.02341 |
| contamination pcie-mhi/esoc/degraded257 | 0/0/False |

## Native Baseline

| field | value |
| --- | --- |
| manifest | tmp/wifi/v1908-servloc-domain-list-live-handoff/manifest.json |
| decision/pass/label | v1908-servloc-domain-list-180-only-service74-missing-rollback-pass/True/servloc-domain-list-180-only-service74-missing |
| servloc instance/service74/wlan_pd | 180/0,0,0/0,0,0 |

## Source Boundary

| field | value |
| --- | --- |
| icnss notify/register | kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/icnss.c:1967 / kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/icnss.c:2006 |
| service-notifier lookup/new-server | kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/service-notifier.c:545 / kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/service-notifier.c:327 |
| export/header | kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/service-notifier.c:707 / kernel_build/SM-A908N_KOR_12_Opensource/Kernel/include/soc/qcom/service-notifier.h:38 |
| non-header callers | ["kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/icnss.c:2006"] |
| exported symbol | True |

## Trace Capability

| field | value |
| --- | --- |
| defconfig | kernel_build/SM-A908N_KOR_12_Opensource/Kernel/arch/arm64/configs/r3q_kor_single_defconfig |
| kprobes/kprobe-events | False/False |
| function/function-graph | False/False |
| uprobes/kallsyms | True/True |

## Selected Diff

- Label: `service74-pre-wlanpd-caller-boundary`.
- V1910 corrects the service-locator hypothesis: the earliest successful Android user-space `wlan/fw` query is 180-only, and it occurs before `wlan_pd` state-up but just after service74 publication.
- Android service74 is before `cnss-daemon` WLFW start and before `wlan_pd`; native V1908 remains service74=0 with the same 180-only locator baseline.
- OSRC has only the ICNSS domain-list caller, but the notifier API is exported; a closed/binary caller or transient in-kernel registration cannot be ruled out from source alone.
- Stock-kernel kprobe/function-tracer caller-stack capture is unavailable, so do not spend another live run on kprobe/function ftrace for this edge.

## Safety Scope

V1911 is host-only. It reads retained manifests, local source, and defconfig text. It performs no live device command, flash, reboot, tracefs write, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, PMIC/GPIO/GDSC/regulator write, forced RC1/case write, `/dev/subsys_esoc0` open, fake ONLINE state, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, firmware write, boot write, partition write, or restart-PD request.

## Next

- Next useful action should avoid SDX50M/PCIe/GDSC and either collect read-only Android `/proc/kallsyms` plus module ownership for `service_notif_register_notifier`, or build a native service66/instance18945 readback gate if the goal is to test whether instance74 is externally visible without sending restart-PD.
- Do not attempt Wi-Fi credentials/connect/ping until native proves WLFW service69 and `wlan0`.
