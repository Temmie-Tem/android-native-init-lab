# Native Init V1749 WLAN-PD Tracefs Mount Restore Source Build

## Summary

- Cycle: `V1749`
- Type: source/build-only rollbackable pure-route tracefs mount-restore test boot artifact
- Decision: `v1749-wlan-pd-tracefs-mount-restore-source-build-pass`
- Result: PASS
- Reason: restores the V1701 `--wifi-test-mount-debugfs` contract on the V1745 private tracefs path repair artifact.
- Manifest: `tmp/wifi/v1749-wlan-pd-tracefs-mount-restore-test-boot/manifest.json`
- Boot image: `tmp/wifi/v1749-wlan-pd-tracefs-mount-restore-test-boot/boot_linux_v1749_wlan_pd_tracefs_mount_restore.img`
- Boot SHA256: `eedc25769b696f95be9693667e9ff56723d0e8959f7595b1ef71302d9a7f46c9`
- Init: `A90 Linux init 0.9.143 (v1749-wlan-pd-tracefs-mount-restore)`
- Helper marker: `a90_android_execns_probe v329`
- Helper SHA256: `c57f57aa1b285861655ce4a4cbcea65185c17862c4c2f5a5f6cde220f145fcbe`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-cnss-output-visibility-start-only`
- Property root: `/mnt/sdext/a90/private-property-v317/v1749/dev/__properties__`
- Debugfs mount enabled: `True`
- Actors: `qrtr-ns`, `pd-mapper`, `rmt_storage`, `tftp_server`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`.
- Tracefs contract: mount debugfs/tracefs before helper uprobe arming, then let helper bind/search private tracefs paths first.
- No service-manager, PM trio, `boot_wlan`, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Expected Live Discriminator

- If tracefs becomes available, classify pure-route non-log `wlfw_start` entry vs no-entry.
- If `wlfw_start` appears, keep actor expansion stopped and classify the blocker as downstream WLAN-PD/WLFW publication.
- If tracefs still reports unavailable, inspect the PID1 debugfs mount helper path rather than adding actors.

## Safety Scope

This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
