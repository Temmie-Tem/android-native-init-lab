# Native Init V1739 WLAN-PD cnss-daemon Output-source Visibility Source Build

## Summary

- Cycle: `V1739`
- Type: source/build-only rollbackable WLAN-PD cnss-daemon output-source visibility test boot artifact
- Decision: `v1739-wlan-pd-cnss-output-source-source-build-pass`
- Result: PASS
- Reason: preserves the V1680 internal-modem firmware-serve route and separates cnss-daemon stdout/stderr/kmsg marker sources.
- Manifest: `tmp/wifi/v1739-wlan-pd-cnss-output-source-test-boot/manifest.json`
- Boot image: `tmp/wifi/v1739-wlan-pd-cnss-output-source-test-boot/boot_linux_v1739_wlan_pd_cnss_output_source.img`
- Boot SHA256: `2b31e64ab017436938142b778081b0e7eb62a39e5ff15c18e09a320e5548c4f1`
- Init: `A90 Linux init 0.9.140 (v1739-wlan-pd-cnss-output-source)`
- Helper marker: `a90_android_execns_probe v327`
- Helper SHA256: `47c9afbddb97736b16345956f34d89e213f4cec16ba94c2f7c107e52da540713`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-cnss-output-visibility-start-only`
- Property root: `/mnt/sdext/a90/private-property-v317/v1739/dev/__properties__`
- Actors: `qrtr-ns`, `pd-mapper`, `rmt_storage`, `tftp_server`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`.
- No service-manager, PM trio, `boot_wlan`, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Output-source Evidence

- New fields: `wlan_pd_cnss_output_visibility.stdout_bytes` and `stderr_bytes`.
- New fields: `wlan_pd_cnss_output_visibility.wlfw_start.{source,stdout_count,stderr_count,kmsg_count}`.
- New fields: per-failure `stdout_count`, `stderr_count`, and `kmsg_count` for all eight pre-WLFW init failure strings.

## Live Labels

- `wlfw-start-reached-downstream-block`
- `cnss-init-step-failed-<name>`
- `cnss-output-still-invisible`

## Safety Scope

This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
