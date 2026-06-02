# Native Init V1743 WLAN-PD Pure-route Non-log Parity Source Build

## Summary

- Cycle: `V1743`
- Type: source/build-only rollbackable pure-route non-log parity test boot artifact
- Decision: `v1743-wlan-pd-pure-nonlog-parity-source-build-pass`
- Result: PASS
- Reason: keeps the V1740 pure internal-modem route but adds private tracefs materialization so the same CNSS non-log uprobe observer can run without service-manager actors.
- Manifest: `tmp/wifi/v1743-wlan-pd-pure-nonlog-parity-test-boot/manifest.json`
- Boot image: `tmp/wifi/v1743-wlan-pd-pure-nonlog-parity-test-boot/boot_linux_v1743_wlan_pd_pure_nonlog_parity.img`
- Boot SHA256: `f6beb03212533fca872252b27a509f29a84ead32243b57b9b6bfff26083d8d24`
- Init: `A90 Linux init 0.9.141 (v1743-wlan-pd-pure-nonlog-parity)`
- Helper marker: `a90_android_execns_probe v328`
- Helper SHA256: `59396002cf8fd7b5886d8a04a2bd4c181797f9c0b8c768d59ac2fddd59c05a75`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-cnss-output-visibility-start-only`
- Property root: `/mnt/sdext/a90/private-property-v317/v1743/dev/__properties__`
- Actors: `qrtr-ns`, `pd-mapper`, `rmt_storage`, `tftp_server`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`.
- New source change: materialize private tracefs for output-visibility mode before CNSS uprobe arming.
- No service-manager, PM trio, `boot_wlan`, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Expected Live Discriminator

- If tracefs becomes available and `wlfw_start` remains absent, V1740's pure-route no-entry result is confirmed without the old non-log measurement gap.
- If tracefs becomes available and `wlfw_start` appears, V1740 was only a tracefs visibility gap and the blocker returns to downstream WLAN-PD/WLFW publication.
- If tracefs is still unavailable, classify the live result as a tracefs-surface failure before adding any actors.

## Safety Scope

This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
