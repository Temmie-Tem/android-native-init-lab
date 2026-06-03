# Native Init V1824 QIPCRTR Socket-State Source Build

## Summary

- Cycle: `V1824`
- Type: source/build-only rollbackable passive QIPCRTR socket-state observer test boot artifact
- Decision: `v1824-qipcrtr-socket-state-source-build-pass`
- Result: PASS
- Reason: helper v349 keeps the bounded lower publication route and adds one passive AF_QIPCRTR socket-state snapshot at `net_window`.
- Manifest: `tmp/wifi/v1824-qipcrtr-socket-state-test-boot/manifest.json`
- Boot image: `tmp/wifi/v1824-qipcrtr-socket-state-test-boot/boot_linux_v1824_qipcrtr_socket_state.img`
- Boot SHA256: `3512feca5f5d8180123e64c0e3397b7528b3528e1db741dc447ba552f907758f`
- Init: `A90 Linux init 0.9.158 (v1824-qipcrtr-socket-state)`
- Helper marker: `a90_android_execns_probe v349`
- Helper SHA256: `9b014cb3d9d919f7731a41a2a8029a71c6996cbc2477907653c6cb845eef4f16`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Property root: `/mnt/sdext/a90/private-property-v317/v1824/dev/__properties__`
- Base route remains the bounded lower handoff observer: PM-client return fetchargs, lower-state samples, service-notifier listener state, raw service-notifier 180/74 samples, lower precondition klog samples, publication text samples, and QRTR registry file summaries.
- Added socket-state prefix: `wlan_pd_qipcrtr_socket_state.net_window.*`.
- Added passive operations: protocol summary before open, AF_QIPCRTR/SOCK_DGRAM open, `getsockname`, protocol summary while open, close, and protocol summary after close.
- Explicit non-actions: `no_bind=1`, `no_connect=1`, `no_send=1`, `no_qrtr_lookup_send=1`, `no_qrtr_control_payload=1`, and `no_service_start=1`.
- Still excluded: direct `/dev/subsys_esoc0` open, fake-ONLINE, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC writes, `boot_wlan`, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.

## Expected Live Discriminator

- V1825 should run one rollbackable live gate with this artifact only if the passive socket-state snapshot is accepted as the next bounded surface.
- `qipcrtr-socket-open-getname-close-passive`: AF_QIPCRTR opens, `getsockname` succeeds, socket count rises only while the local fd is open, and service74/wlan_pd still remain absent.
- `qipcrtr-socket-open-fails`: AF_QIPCRTR protocol is listed but opening the passive socket fails; capture errno and stop.
- `lower-publication-progress`: service 74, wlan_pd, WLFW service 69, MHI, or `wlan0` appears; stop before Wi-Fi HAL/scan/connect.
- `safety-regression`: any forbidden side effect appears; stop and roll back.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Safety Scope

This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
