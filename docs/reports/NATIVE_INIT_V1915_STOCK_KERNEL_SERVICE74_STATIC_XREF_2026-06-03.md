# Native Init V1915 Stock Kernel Service74 Static Xref

## Summary

- Cycle: `V1915`
- Type: host-only bounded stock-kernel/source xref preflight for service-notifier instance74
- Decision: `v1915-stock-kernel-static-xref-no-service74-caller-host-pass`
- Label: `stock-kernel-static-xref-no-service74-caller`
- Result: `PASS`
- Reason: stock and v724 kernels are identical and expose service-notifier strings, but bounded strings/source xref has no literal instance74 caller beyond the ICNSS domain-list path; static host evidence cannot identify the runtime service74 publisher
- Evidence: `tmp/wifi/v1915-stock-kernel-service74-static-xref`

## Gate Results

| gate | pass |
| --- | --- |
| stock_and_v724_kernel_identical | True |
| stock_strings_have_relevant_symbols | True |
| stock_strings_have_no_literal_service74 | True |
| osrc_register_caller_boundary | True |
| no_local_vmlinux_or_system_map | True |

## Boot Kernel

| field | value |
| --- | --- |
| stock boot/kernel/sha | backups/baseline_a_20260423_030309/boot.img / tmp/wifi/v1915-stock-kernel-service74-static-xref/stock/kernel / 9f4fc72c15ce9f96694023cf8f3f0340651d073acd584853941764cf9756b85a |
| v724 boot/kernel/sha | stage3/boot_linux_v724.img / tmp/wifi/v1915-stock-kernel-service74-static-xref/native/kernel / 9f4fc72c15ce9f96694023cf8f3f0340651d073acd584853941764cf9756b85a |
| kernel sizes | 49827613 / 49827613 |
| unpack rc | 0 / 0 |

## Focused Strings

| term | count | first offsets |
| --- | --- | --- |
| service_notif_register_notifier | 1 | 39021342 |
| service_notifier_new_server | 1 | 35173485 |
| qmi_add_lookup | 4 | 35139560, 35141038, 35827096, 39019193 |
| SERVREG_NOTIF_SERVICE_ID | 0 |  |
| servreg_notif | 0 |  |
| wlan/fw | 1 | 35161223 |
| wlan_pd | 15 | 35267244, 36016656, 36631397, 36632687 |
| msm/modem/wlan_pd | 0 |  |
| wlfw | 22 | 34276929, 34276997, 34277022, 34277046 |
| icnss_get_service_location | 0 |  |
| service_locator | 5 | 28254820, 35174191, 35174499, 35174579 |
| restart_pd | 0 |  |
| 74 service | 0 |  |
| service 74 | 0 |  |
| instance 74 | 0 |  |

## Source Xref

| field | value |
| --- | --- |
| source files scanned | 286 |
| register callers | ["kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/icnss.c:2006: service_notif_register_notifier(pd->domain_list[i].name,"] |
| new-server print | ["kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/service-notifier.c:337: pr_info(\"Connection established between QMI handle and %d service\\n\","] |
| service74 literal line count | 0 |
| SERVREG service-id lines | ["kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/service-notifier-private.h:18: #define SERVREG_NOTIF_SERVICE_ID_V01 0x42", "kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/service-notifier.c:34: #define SERVREG_NOTIF_SERVICE_ID\tSERVREG_NOTIF_SERVICE_ID_V01", "kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/service-notifier.c:546: SERVREG_NOTIF_SERVICE_ID,"] |
| qmi_add_lookup lines | ["kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/net/wireless/cnss2/qmi.c:1734: ret = qmi_add_lookup(&plat_priv->qmi_wlfw, WLFW_SERVICE_ID_V01,", "kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/net/wireless/cnss2/qmi.c:1738: ret = qmi_add_lookup(&plat_priv->qmi_wlfw, WLFW_SERVICE_ID_V01,", "kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/adsp_vote_qmi.c:190: ret = qmi_add_lookup(dev, PGS_SERVICE_ID_V01,", "kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/dfc_qmi.c:1478: rc = qmi_add_lookup(&data->handle, DFC_SERVICE_ID_V01,", "kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/icnss_qmi.c:1275: ret = qmi_add_lookup(&priv->qmi, WLFW_SERVICE_ID_V01,", "kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/qmi_interface.c:208: * qmi_add_lookup() - register a new lookup with the name service", "kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/qmi_interface.c:219: int qmi_add_lookup(struct qmi_handle *qmi, unsigned int service,", "kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/service-locator.c:277: qmi_add_lookup(&service_locator.clnt_handle,", "kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/service-notifier.c:545: qmi_add_lookup(&qmi_data->clnt_handle,", "kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/sysmon-qmi.c:660: qmi_add_lookup(&data->clnt_handle, SSCTL_SERVICE_ID,", "kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/wda_qmi.c:433: rc = qmi_add_lookup(&data->handle, WDA_SERVICE_ID_V01,"] |

## Symbol Artifact Limit

| field | value |
| --- | --- |
| search root | kernel_build/SM-A908N_KOR_12_Opensource |
| symbol artifact count | 0 |
| has vmlinux/System.map | False |
| artifact excerpt | [] |

## Selected Diff

- Label: `stock-kernel-static-xref-no-service74-caller`.
- Source confirms the dmesg text `74 service` is `data->instance_id`, not the fixed SERVREG notifier service id.
- Source also confirms the QMI lookup is `SERVREG_NOTIF_SERVICE_ID` with runtime `instance_id`; the visible OSRC caller passes ICNSS service-locator domain-list values.
- Stock kernel strings retain relevant symbol names but no literal service74/instance74 caller clue, and no local `vmlinux`/`System.map` is available for bounded callgraph xref.
- Do not repeat broad kallsyms/disasm brute force; the next useful step is a read-only live observer around service74 lookup/publication or a fuller Android kallsyms-symbol capture.

## Safety Scope

V1915 is host-only. It unpacks local boot images into ignored tmp evidence and scans local kernel/source text. It executes no live device command, reboot, flash, tracefs write, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, PMIC/GPIO/GDSC/regulator write, forced RC1/case write, `/dev/subsys_esoc0` open, fake ONLINE state, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, firmware write, boot write, partition write, or restart-PD request.

## Next

- Next live gate: Android-good handoff that captures broader read-only `/proc/kallsyms` names and tracefs availability around service-notifier/qmi/service-locator before service74, then rollback to v724.
- Native connect/ping remains gated until native proves WLFW service69 and `wlan0`.
