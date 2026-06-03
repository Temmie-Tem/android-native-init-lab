# Native Init V1827 QIPCRTR Auto-Bind Source Build

## Summary

- Cycle: `V1827`
- Type: source/build-only rollbackable passive QIPCRTR local auto-bind observer test boot artifact
- Decision: `v1827-qipcrtr-autobind-source-build-pass`
- Result: PASS
- Reason: helper v350 keeps the bounded lower publication route and adds one local auto-bind AF_QIPCRTR socket-state snapshot at `net_window`.
- Manifest: `tmp/wifi/v1827-qipcrtr-autobind-test-boot/manifest.json`
- Boot image: `tmp/wifi/v1827-qipcrtr-autobind-test-boot/boot_linux_v1827_qipcrtr_autobind.img`
- Boot SHA256: `d33c717024f0337bd519878f776c76e56b817bcb339a92b431ff31b4461dd6f6`
- Init: `A90 Linux init 0.9.159 (v1827-qipcrtr-autobind)`
- Helper marker: `a90_android_execns_probe v350`
- Helper SHA256: `3c081c9b1c83d910f42010c428cf0983b1e530a14eacb9e92f80e03d8672364a`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Property root: `/mnt/sdext/a90/private-property-v317/v1827/dev/__properties__`
- Base route remains the bounded lower handoff observer and retains the V1824 passive unbound socket snapshot.
- Added auto-bind prefix: `wlan_pd_qipcrtr_autobind_state.net_window.*`.
- Added local auto-bind operations: protocol summary before open, AF_QIPCRTR/SOCK_DGRAM open, `getsockname` before bind, `bind` with node/port `0/0`, `getsockname` after bind, protocol summary while bound, close, and protocol summary after close.
- Explicit non-actions: `no_connect=1`, `no_send=1`, `no_qrtr_lookup_send=1`, `no_qrtr_control_payload=1`, and `no_service_start=1`.
- Still excluded: direct `/dev/subsys_esoc0` open, fake-ONLINE, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC writes, `boot_wlan`, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.

## Expected Live Discriminator

- V1828 should run one rollbackable live gate with this artifact only if the local auto-bind socket-state snapshot is accepted as the next bounded surface.
- `qipcrtr-autobind-gets-local-port-passive`: AF_QIPCRTR opens, local auto-bind succeeds, `getsockname` returns a non-zero local port, and service74/wlan_pd still remain absent.
- `qipcrtr-autobind-fails`: open succeeds but local auto-bind fails; capture errno and stop.
- `lower-publication-progress`: service 74, wlan_pd, WLFW service 69, MHI, or `wlan0` appears; stop before Wi-Fi HAL/scan/connect.
- `safety-regression`: any forbidden side effect appears; stop and roll back.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Safety Scope

This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
