# Native Init V1745 WLAN-PD Private Tracefs Repair Source Build

## Summary

- Cycle: `V1745`
- Type: source/build-only rollbackable pure-route private tracefs repair test boot artifact
- Decision: `v1745-wlan-pd-private-tracefs-repair-source-build-pass`
- Result: PASS
- Reason: extends V1743/V1744 by making CNSS uprobe arming search the private tracefs bind path before global `/sys/kernel/*/tracing` roots.
- Manifest: `tmp/wifi/v1745-wlan-pd-private-tracefs-repair-test-boot/manifest.json`
- Boot image: `tmp/wifi/v1745-wlan-pd-private-tracefs-repair-test-boot/boot_linux_v1745_wlan_pd_private_tracefs_repair.img`
- Boot SHA256: `5b86d481d79d39351d1410501b729a2d46e8680277381a54e4b0d088612289dc`
- Init: `A90 Linux init 0.9.142 (v1745-wlan-pd-private-tracefs-repair)`
- Helper marker: `a90_android_execns_probe v329`
- Helper SHA256: `c57f57aa1b285861655ce4a4cbcea65185c17862c4c2f5a5f6cde220f145fcbe`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-cnss-output-visibility-start-only`
- Property root: `/mnt/sdext/a90/private-property-v317/v1745/dev/__properties__`
- Actors: `qrtr-ns`, `pd-mapper`, `rmt_storage`, `tftp_server`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`.
- Source change: CNSS and peripheral uprobe finders now try private tracefs paths materialized under the helper namespace before the global roots.
- No service-manager, PM trio, `boot_wlan`, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Expected Live Discriminator

- If tracefs becomes available, V1745 can finally classify pure-route non-log `wlfw_start` entry vs no-entry.
- If tracefs still reports unavailable, the blocker is not just path selection and the next unit should inspect whether tracefs is mounted globally before private namespace setup.
- If `wlfw_start` appears, keep actor expansion stopped and classify the blocker as downstream WLAN-PD/WLFW publication.

## Safety Scope

This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
