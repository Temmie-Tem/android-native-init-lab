# Native Init V1616 pm-service Launch Contract Classifier

## Summary

- Cycle: `V1616`
- Type: host-only classifier over V1614/V1615, V862, V1073, V1081, and Android-good property evidence
- Decision: `v1616-pm-service-clean-exit-is-offline-system-info-contract-gap`
- Result: `PASS`
- Reason: Current native pm-service reaches only the offline property publication path and exits cleanly before binder/QMI/PM fd setup, while Android-good keeps per_mgr/per_proxy running with SDX50M/modem ONLINE; the next gap is the mdmdetect/get_system_info input contract, not lower RC1/MHI
- Evidence: `tmp/wifi/v1616-pm-service-launch-contract-classifier`

## Inputs

| input | path |
| --- | --- |
| v1614_manifest | tmp/wifi/v1614-per-mgr-nonstop-context-handoff/manifest.json |
| v1614_helper | tmp/wifi/v1614-per-mgr-nonstop-context-handoff/test-v1393-helper-result.stdout.txt |
| v1615_report | docs/reports/NATIVE_INIT_V1615_PER_MGR_NONSTOP_CONTEXT_CLASSIFIER_2026-06-02.md |
| v862_manifest | tmp/wifi/v862-android-init-service-contract/manifest.json |
| v1073_extract | tmp/wifi/v1073-host-only/vendor-extract/files |
| v1073_analysis | tmp/wifi/v1073-host-only/analysis |
| v1081_manifest | tmp/wifi/v1081-pm-service-early-path-classifier/manifest.json |
| android_good_props | tmp/wifi/v431-android-runtime-gap-handoff-live-su-quote-20260520-152315/v431-android-runtime-gap-run/commands/wifi-props-filtered.txt |

## Checks

| check | value |
| --- | --- |
| v1615_current_boundary_valid | True |
| pm_service_natural_clean_exit | True |
| pm_service_exits_before_ipc_or_pm_fd | True |
| current_runtime_only_publishes_offline | True |
| binary_has_persistent_server_stack | True |
| android_init_contract_known | True |
| current_source_models_old_init_gaps | True |
| android_good_keeps_peripheral_online | True |
| prior_get_system_info_boundary_relevant | True |
| downstream_wifi_still_absent | True |

## Current Native Runtime

| field | value |
| --- | --- |
| handoff_pass | True |
| rollback_ok | True |
| nonstop_context_trace | 1 |
| child_traced | 0 |
| startup_exit_code | 0 |
| startup_signal | 0 |
| last_alive_ms | 20 |
| first_gone_ms | 41 |
| max_subsys_modem_fd | 0 |
| max_subsys_esoc0_fd | 0 |
| max_vndbinder_fd | 0 |
| max_socket_fd | 0 |
| property_request_count | 3 |
| provider_trigger | False |
| wlan0_present | False |

## Property Requests

| index | name | value | allowed | result |
| --- | --- | --- | --- | --- |
| 1 | hwservicemanager.ready | true | 1 | 0x00000000 |
| 2 | vendor.peripheral.SDX50M.state | OFFLINE | 1 | 0x00000000 |
| 3 | vendor.peripheral.modem.state | OFFLINE | 1 | 0x00000000 |

## Android-good Contrast

| field | value |
| --- | --- |
| source | tmp/wifi/v431-android-runtime-gap-handoff-live-su-quote-20260520-152315/v431-android-runtime-gap-run/commands/wifi-props-filtered.txt |
| init.svc.vendor.per_mgr | True |
| init.svc.vendor.per_proxy | True |
| init.svc.vendor.per_proxy_helper | stopped |
| vendor.peripheral.SDX50M.state | ONLINE |
| vendor.peripheral.modem.state | ONLINE |
| vendor.peripheral.shutdown_critical_list | SDX50M modem  |

## Binary and Init Contract

| surface | value |
| --- | --- |
| pm-service NEEDED | libcutils.so, libutils.so, liblog.so, libbinder.so, libqmi_cci.so, libqmi_common_so.so, libqmi_encdec.so, libqmi_csi.so, libmdmdetect.so, libperipheral_client.so, libc++.so, libc.so, libm.so, libdl.so |
| persistent server symbols | True |
| mdmdetect sysfs inputs | True |
| service literal | True |
| per_mgr rc path | /vendor/bin/pm-service |
| per_mgr ioprio | rt 4 |
| per_proxy start action | start vendor.per_proxy |
| pm_proxy_helper post-fs-data | True |

## Current Helper Coverage

| contract | modelled |
| --- | --- |
| has_ioprio_rt4 | True |
| has_per_proxy_helper | True |
| has_init_svc_per_mgr_running_gate | True |
| has_shutdown_critical_list_allow | True |
| has_property_offline_allow | True |
| wrapper_can_enable_nonstop_context | True |

## Interpretation

V1616 keeps the V1615 runtime boundary but adds static and Android-good context.  `pm-service` is capable of a persistent Binder/QMI server path: the binary imports Binder, QMI CSI/CCI, `libmdmdetect`, `libperipheral_client`, `get_system_info`, `property_set`, and `qmi_csi_register`.  The current native run does not reach that path.  It publishes only `hwservicemanager.ready=true`, `vendor.peripheral.SDX50M.state=OFFLINE`, and `vendor.peripheral.modem.state=OFFLINE`, then exits cleanly before any `/dev/vndbinder`, socket, `/dev/subsys_modem`, or `/dev/subsys_esoc0` fd.  Android-good evidence instead keeps `vendor.per_mgr` and `vendor.per_proxy` running and reports SDX50M/modem `ONLINE` plus `vendor.peripheral.shutdown_critical_list=SDX50M modem `.  Therefore the active blocker is the system-info/peripheral-state input contract that makes `pm-service` decide both peripherals are OFFLINE, not RC1/MHI/WLFW.

Prior V1081 remains relevant: it proved the early stripped-binary boundary `v1081-pm-service-early-exit-path-classified` where `get_system_info` prevents Binder/QMI setup.  The current path has advanced from hard failure to OFFLINE-only publication, but still needs the exact `libmdmdetect` input surface classified.

## Next Gate

- Recommended cycle: `V1617`
- Type: source/build-only non-ptrace pm-service system-info surface capture
- Focus: capture exact libmdmdetect/get_system_info input surfaces around pm-service startup without ptrace: /sys/bus/msm_subsys/devices, /sys/bus/esoc/devices, /sys/class/esoc-dev, /dev/subsys_*, /dev/esoc-*, /dev/vndbinder, private property root and service-manager sockets
- Rationale: V1616 proves property coverage and old init-contract gaps are not the active blocker; pm-service is making an OFFLINE-only decision before it reaches its persistent Binder/QMI server path

### Hard Gates

- no pm-service syscall ptrace
- no mdm_helper ptrace
- no direct /dev/subsys_esoc0 open
- no Wi-Fi HAL start
- no scan/connect/credentials
- no DHCP/routes/external ping
- no PMIC/GPIO/GDSC direct write
- no blind eSoC notify/BOOT_DONE spoof
- no global PCI rescan
- no platform bind/unbind

## Safety Scope

This classifier is host-only. It performs no device command, flash, reboot, partition write, daemon start, Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC write, blind eSoC notify/`BOOT_DONE` spoof, pci-msm debugfs write, global PCI rescan, or platform bind/unbind.
