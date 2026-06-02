# Native Init V1701 WLAN-PD cnss-daemon Tracefs Target-path Source Build

## Summary

- Cycle: `V1701`
- Type: source/build-only rollbackable WLAN-PD cnss-daemon tracefs target-path test boot artifact
- Decision: `v1701-wlan-pd-cnss-tracefs-target-path-source-build-pass`
- Result: PASS
- Reason: repairs the V1700 uprobe target-path contract without adding new runtime actors
- Manifest: `tmp/wifi/v1701-wlan-pd-cnss-tracefs-target-path-test-boot/manifest.json`
- Boot image: `tmp/wifi/v1701-wlan-pd-cnss-tracefs-target-path-test-boot/boot_linux_v1701_wlan_pd_cnss_tracefs_target_path.img`
- Boot SHA256: `42145b7a7bbe7ba55b887fea983767892bce8437d8f56f62e634649bb0241cf8`
- Init: `A90 Linux init 0.9.128 (v1701-wlan-pd-cnss-tracefs-target-path)`
- Helper marker: `a90_android_execns_probe v314`
- Helper SHA256: `8317fcdf1d7ea879d084dead104bfb120c13470ec0473a338d5756a45ef587c6`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-cnss-output-visibility-start-only`
- Property root: `/mnt/sdext/a90/private-property-v317/v1701/dev/__properties__`
- Actors: `qrtr-ns`, `pd-mapper`, `rmt_storage`, `tftp_server`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`
- Evidence prefix: `wlan_pd_cnss_nonlog_control_flow.*`.
- The helper attempts one bounded tracefs uprobe for `cnss-daemon+0xec00` and falls back to `/proc` evidence only if registration remains unavailable.
- No service-manager, PM trio, `boot_wlan`, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.

## Target-path Contract

- V1700 failed with `uprobe.register_rc=-2` while tracefs itself was available.
- V1701 selects the uprobe target from the helper's private namespace vendor mount first: `{temp_root}/vendor/bin/cnss-daemon`.
- It records target candidate `access/stat` evidence for private vendor, `/mnt/vendor/bin/cnss-daemon`, and `/vendor/bin/cnss-daemon`.
- Existing successful tracefs collectors used global mounted paths such as `/mnt/vendor/bin/pm-service`; this build avoids relying on the chroot-visible `/vendor/bin/cnss-daemon` path.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `4` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Live Labels

- `cnss-process-exited-before-wlfw`
- `cnss-wlfw-entry-hit-downstream-wait`
- `cnss-wlfw-entry-not-hit-init-stall`
- `cnss-uprobe-unavailable-fallback-needed`

## Safety Scope

This build script performed host-side source/build work only. It did not issue device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
