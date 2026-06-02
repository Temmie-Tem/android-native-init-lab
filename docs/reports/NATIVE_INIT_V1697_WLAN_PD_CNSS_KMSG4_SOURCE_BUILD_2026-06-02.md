# Native Init V1697 WLAN-PD cnss-daemon Kmsg4 Output-visibility Source Build

## Summary

- Cycle: `V1697`
- Type: source/build-only rollbackable WLAN-PD cnss-daemon kmsg4 output-visibility test boot artifact
- Decision: `v1697-wlan-pd-cnss-kmsg4-source-build-pass`
- Result: PASS
- Reason: preserves the V1680/V1691 internal-modem route and adds read-only `/proc` non-log cnss-daemon control-flow fallback fields
- Manifest: `tmp/wifi/v1697-wlan-pd-cnss-kmsg4-output-visibility-test-boot/manifest.json`
- Boot image: `tmp/wifi/v1697-wlan-pd-cnss-kmsg4-output-visibility-test-boot/boot_linux_v1697_wlan_pd_cnss_kmsg4_output_visibility.img`
- Boot SHA256: `d0c3e12bdc2101c830e2da2bbe7923b85ced95ab134ea1bb6f7a9d67d8603f5b`
- Init: `A90 Linux init 0.9.126 (v1697-wlan-pd-cnss-kmsg4-output-visibility)`
- Helper marker: `a90_android_execns_probe v312`
- Helper SHA256: `93e7d24ef99f0877cfe55e283359ddd056bbf89f22961341a9932056282c331a`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-cnss-output-visibility-start-only`
- Property root: `/mnt/sdext/a90/private-property-v317/v1697/dev/__properties__`
- Actors: `qrtr-ns`, `pd-mapper`, `rmt_storage`, `tftp_server`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`
- New evidence prefix: `wlan_pd_cnss_nonlog_control_flow.*`.
- The new fallback does not write tracefs and does not arm uprobes; it records PID, maps load-bias, computed `wlfw_start` runtime PC, fd/socket counts, task state, and MHI/ks absence.
- No service-manager, PM trio, `boot_wlan`, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `4` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Live Labels

- `cnss-process-exited-before-wlfw`
- `cnss-uprobe-unavailable-fallback-needed`
- Existing output labels remain captured through `wlan_pd_cnss_output_visibility.label`.

## Safety Scope

This build script performed host-side source/build work only. It did not issue device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.

## V1697 Delta

- Raises `persist.vendor.cnss-daemon.kmsg_logging` from `1` to `4` so `wlfw_start` severity-2 messages are kmsg-visible.
- Keeps `persist.vendor.cnss-daemon.debug_level=4`.
- Keeps the V1680 internal modem firmware-serve route and does not add PM/service-window actors or `boot_wlan`.
