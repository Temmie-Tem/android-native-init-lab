# Native Init V1693 WLAN-PD cnss-daemon Non-log Control-flow Source Build

## Summary

- Cycle: `V1693`
- Type: source/build-only rollbackable WLAN-PD cnss-daemon non-log control-flow test boot artifact
- Decision: `v1693-wlan-pd-cnss-nonlog-control-flow-source-build-pass`
- Result: PASS
- Reason: preserves the V1680/V1691 internal-modem route and adds read-only `/proc` non-log cnss-daemon control-flow fallback fields
- Manifest: `tmp/wifi/v1693-wlan-pd-cnss-nonlog-control-flow-test-boot/manifest.json`
- Boot image: `tmp/wifi/v1693-wlan-pd-cnss-nonlog-control-flow-test-boot/boot_linux_v1693_wlan_pd_cnss_nonlog_control_flow.img`
- Boot SHA256: `e15442d7419fb7ced989eacab912aecf800847c1fdda1ffa9283361a8cfdb106`
- Init: `A90 Linux init 0.9.125 (v1693-wlan-pd-cnss-nonlog-control-flow)`
- Helper marker: `a90_android_execns_probe v311`
- Helper SHA256: `3c381ab934b0189bd3f775964a37823036ff50a93eb5338a28a5bb1e70454b89`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-cnss-output-visibility-start-only`
- Property root: `/mnt/sdext/a90/private-property-v317/v1693/dev/__properties__`
- Actors: `qrtr-ns`, `pd-mapper`, `rmt_storage`, `tftp_server`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`
- New evidence prefix: `wlan_pd_cnss_nonlog_control_flow.*`.
- The new fallback does not write tracefs and does not arm uprobes; it records PID, maps load-bias, computed `wlfw_start` runtime PC, fd/socket counts, task state, and MHI/ks absence.
- No service-manager, PM trio, `boot_wlan`, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Live Labels

- `cnss-process-exited-before-wlfw`
- `cnss-uprobe-unavailable-fallback-needed`
- Existing output labels remain captured through `wlan_pd_cnss_output_visibility.label`.

## Safety Scope

This build script performed host-side source/build work only. It did not issue device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
