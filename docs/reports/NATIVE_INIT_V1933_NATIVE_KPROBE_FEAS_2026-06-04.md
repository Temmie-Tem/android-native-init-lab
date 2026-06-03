# Native Init V1933 Native Kprobe Feasibility

## Summary

- Cycle: `V1933`
- Decision: `v1933-native-kprobe-unavailable-uprobe-only-fallback-pass`
- Label: `native-kprobe-unavailable-uprobe-only-fallback`
- Pass: `True`
- Reason: native v724 exposes target symbol names but has CONFIG_KPROBES/KPROBE_EVENTS disabled, so service-notifier kernel callbacks cannot be kprobed; continue with userland uprobes/QRTR/dmesg fallback
- Evidence: `tmp/wifi/v1933-native-kprobe-feas`

## Matrix

| area | value | detail |
| --- | --- | --- |
| version/selftest | True | version_ok=True selftest_ok=True |
| kernel kprobe | False | CONFIG_KPROBES=not set CONFIG_KPROBE_EVENTS=None |
| user uprobe | True | CONFIG_UPROBE_EVENTS=y |
| kallsyms targets | True | targets=['__kstrtab_qmi_add_lookup', '__kstrtab_service_notif_register_notifier', '__ksymtab_qmi_add_lookup', '__ksymtab_service_notif_register_notifier', 'icnss_service_notifier_notify', 'qmi_add_lookup', 'root_service_service_ind_cb', 'service_notif_register_notifier', 'service_notifier_new_server', 'wlfw_new_server'] all_zero_addresses=True |
| tracefs fs | True | dir_exists=True |

## Kallsyms Sample

- `0000000000000000 T qmi_add_lookup`
- `0000000000000000 t icnss_service_notifier_notify`
- `0000000000000000 t wlfw_new_server`
- `0000000000000000 T service_notif_register_notifier`
- `0000000000000000 t service_notifier_new_server`
- `0000000000000000 t root_service_service_ind_cb`
- `0000000000000000 r __ksymtab_qmi_add_lookup`
- `0000000000000000 r __ksymtab_service_notif_register_notifier`
- `0000000000000000 r __kstrtab_qmi_add_lookup`
- `0000000000000000 r __kstrtab_service_notif_register_notifier`

## Decision

- Do not implement a native kernel kprobe observer for `root_service_service_ind_cb`, `service_notifier_new_server`, or `wlfw_new_server`: current native config has `CONFIG_KPROBES` disabled.
- Continue with the already-proven userland observer class: `libqmi_cci.so`/CNSS uprobes, QRTR service snapshots, and dmesg state lines around the A1 window.
- Stop before Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping until native exposes WLFW69/WLAN-PD and `wlan0`.

## Safety Scope

Read-only native preflight. This script reads `/proc/filesystems`, `/proc/config.gz`, `/proc/kallsyms`, `/sys/kernel/tracing` directory metadata, version, and selftest only. It does not mount tracefs, write tracefs, flash, reboot, stage properties, write firmware/partitions, remount-write, open `/dev/subsys_esoc0`, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, external ping, force RC1/case, touch PMIC/GPIO/GDSC/regulators, rescan PCI, bind/unbind platforms, fake ONLINE, or send eSoC notify/BOOT_DONE.
