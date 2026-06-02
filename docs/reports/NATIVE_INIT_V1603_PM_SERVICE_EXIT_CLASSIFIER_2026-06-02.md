# Native Init V1603 PM-Service Exit Classifier

## Summary

- Cycle: `V1603`
- Type: host-only PM-service startup/lifetime classifier
- Decision: `v1603-pph-gate-passed-per-mgr-exit-before-contract`
- Result: `PASS`
- Reason: V1602 closes the pm_proxy_helper fd race: /dev/subsys_modem is present before per_mgr, but pm-service exits 0 before observation and before owning /dev/subsys_modem or /dev/subsys_esoc0; the next gate must instrument pm-service startup/lifetime, not RC1/MHI/WLFW
- Evidence: `tmp/wifi/v1603-pm-service-exit-classifier`

## Inputs

| input | path |
| --- | --- |
| v1602_manifest | tmp/wifi/v1602-pm-first-late-per-proxy-pph-gate-lower-marker-handoff/manifest.json |
| v1602_summary | tmp/wifi/v1602-pm-first-late-per-proxy-pph-gate-lower-marker-handoff/summary.md |
| v1602_helper_result | tmp/wifi/v1602-pm-first-late-per-proxy-pph-gate-lower-marker-handoff/test-v1393-helper-result.stdout.txt |
| v1602_dmesg | tmp/wifi/v1602-pm-first-late-per-proxy-pph-gate-lower-marker-handoff/test-v1393-dmesg.stdout.txt |
| v1599_report | docs/reports/NATIVE_INIT_V1599_PM_FIRST_LATE_PER_PROXY_LOWER_MARKER_HANDOFF_2026-06-02.md |
| v1602_report | docs/reports/NATIVE_INIT_V1602_PM_FIRST_LATE_PER_PROXY_PPH_GATE_LOWER_MARKER_HANDOFF_2026-06-02.md |
| helper_source | stage3/linux_init/helpers/a90_android_execns_probe.c |

## Derived Checks

| check | value |
| --- | --- |
| v1602_handoff_evidence_present | True |
| pph_gate_passed | True |
| per_mgr_exited_clean_before_observable | True |
| per_mgr_never_held_subsys_modem | True |
| pm_proxy_failed_after_per_mgr | True |
| pm_service_owned_esoc0_missing | True |
| downstream_markers_absent | True |
| guardrails_preserved | True |
| source_records_required_fields | True |

## V1602 Boundary

| field | value |
| --- | --- |
| manifest_decision | v1602-test-boot-no-downstream-wifi-progress-blocked |
| helper_result | pm-service-owned-powerup-missing |
| helper_reason | pm-first-late-per-proxy-route-did-not-reach-dev-subsys-esoc0-mdm-subsys-powerup |
| pph_gate_enabled | 1 |
| pph_gate_seen | 1 |
| pph_gate_first_seen_ms | 301 |
| pph_gate_final_count | 1 |
| pm_proxy_helper_subsys_modem_fd_count | 1 |
| per_mgr_observable | 0 |
| per_mgr_exited | 1 |
| per_mgr_exit_code | 0 |
| per_mgr_subsys_modem_fd_count | -1 |
| pm_proxy_observable | 1 |
| pm_proxy_exit_code | 1 |
| pm_full_contract_seen | 0 |
| subsys_esoc0_open_attempted | 0 |
| subsys_trigger_started | 0 |
| mdm_helper_esoc0_fd_count | 1 |

## Downstream Marker State

| marker | count/value |
| --- | --- |
| dmesg __subsystem_get modem | 1 |
| dmesg pm-service __subsystem_get esoc0 | 0 |
| dmesg mdm_subsys_powerup | 0 |
| dmesg RC1 | 0 |
| dmesg WLFW | 0 |
| dmesg wlan0 | 0 |
| scan/connect guard | 0 |
| credentials guard | 0 |
| DHCP/routes guard | 0 |
| external ping guard | 0 |

## Stderr Triage

| field | value |
| --- | --- |
| stderr_bytes | 893 |
| old_property_service_warning | True |
| kmsg_permission_denied | True |
| shell_quote_error | True |
| pm_service_specific_text | False |

## Interpretation

V1602 proves the PPH fd race is closed: the route waits until `pm_proxy_helper` holds `/dev/subsys_modem` before starting `per_mgr`.  The failure still occurs above the SDX50M/eSoC/RC1 layer: `/vendor/bin/pm-service` exits with code `0` before it is observable in the sampling window and before it owns `/dev/subsys_modem`.  Consequently `pm-proxy` exits `1`, `pm_full_contract_seen` remains `0`, and no PM-service-owned `/dev/subsys_esoc0` or `mdm_subsys_powerup` marker exists.

The current next step is therefore not another RC1/PERST/refclk or firmware/MHI/WLFW deep dive.  Those paths remain downstream until the Android-style PM-service contract survives long enough to trigger `/dev/subsys_esoc0`.

## Next Gate

- Recommended cycle: `V1604`
- Type: source/build-only focused pm-service startup diagnostic
- Focus: extend a90_android_execns_probe with a tight per_mgr startup sampler after the proven PPH modem-fd gate

### Success Markers

- sample per_mgr at 10-20ms cadence from spawn until exit or one second
- record first observable time, exit time, exit code, signal, cwd, cmdline, wchan, and fd links if alive
- record whether per_mgr ever opens /dev/subsys_modem, /dev/vndbinder, /dev/hwbinder, binder sockets, or service-manager sockets
- capture per_mgr stdout/stderr byte counts and last diagnostic lines
- preserve the existing PPH fd gate and all scan/connect/credential/DHCP/external-ping guardrails

### Live Follow-Up Constraint

- V1605 artifact sanity, then V1606 rollbackable live handoff only if the diagnostic image excludes Wi-Fi HAL, scan/connect, DHCP/routes, external ping, direct PMIC/GPIO/GDSC writes, blind eSoC notify/BOOT_DONE, global PCI rescan, and platform bind/unbind.

## Safety Scope

This classifier is host-only. It performs no device command, flash, reboot, partition write, daemon start, Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC write, blind eSoC notify/`BOOT_DONE` spoof, pci-msm debugfs write, global PCI rescan, or platform bind/unbind.
