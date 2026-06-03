# Native Init V1869 SDX50M Private Mount Summary Source Build

## Summary

- Cycle: `V1869`
- Type: source/build-only rollbackable v356 lower-state observer with private SDX50M cnss-daemon bind-mount evidence emitted through the helper result buffer
- Decision: `v1869-sdx50m-private-mount-summary-source-build-pass`
- Result: PASS
- Reason: V1864, V1866, and V1868 rolled back safely but the handoff parser only collected helper result stdout; V1869 keeps the private-mount argv fixes and emits `private_cnss_daemon.*` materialization fields into that collected stdout buffer.
- Manifest: `tmp/wifi/v1869-sdx50m-private-mount-summary-test-boot/manifest.json`
- Boot image: `tmp/wifi/v1869-sdx50m-private-mount-summary-test-boot/boot_linux_v1869_sdx50m_private_mount_summary.img`
- Boot SHA256: `5bf7ce6de064016d3f5c4201b685aa09d205f7fbb65f1b42bb8ea06df19a3e28`
- Init: `A90 Linux init 0.9.169 (v1869-sdx50m-private-mount-summary)`
- Helper marker: `a90_android_execns_probe v356`
- Helper SHA256: `7474c92a530bda845396bd13eda1675db70292fc37ec36c8df7b3e2c1b4ca492`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Property root: `/mnt/sdext/a90/private-property-v317/v1869/dev/__properties__`
- Private CNSS mount: `True` path `/cache/bin/cnss-daemon.sdx50m`
- PID1 carries the private mount arguments in both the active service-object branch and the common helper argv tail for this macro-enabled build.
- The helper now records source path, target path, post-materialization target size, bind status, and expected `SDX50M` discriminator in the child stdout buffer collected by the handoff.
- The private mount remains namespace-local; it does not write `/vendor` and depends on the remote cache artifact already verified by V1862.
- PM-service open-context labels retained: `pm_service_post_ack_power_state_loaded`, `pm_service_post_ack_open_context`, `pm_service_post_ack_open_path_loaded`, `pm_service_post_ack_open_fd_store`, `pm_service_post_ack_open_fd_compare`, `pm_service_post_ack_open_success_counter`.
- Lower-state observer guardrails remain: no direct `/dev/subsys_esoc0` open, no fake ONLINE, no eSoC notify/BOOT_DONE, no forced RC1, no PCI rescan/bind, no PMIC/GPIO/GDSC writes, no Wi-Fi HAL, no scan/connect, no credentials, no DHCP/routes, and no external ping.

## Expected Live Discriminator

- `private-mount-bind-failed`: active argv or source artifact still failed to materialize the namespace-local bind mount; stop before live bridge interpretation.
- `private-mount-sdx50m-selected`: SDX50M private daemon path executed and changed PM selection; inspect lower publication before connect.
- `private-mount-lower-publication-progress`: WLFW service 69, BDF, MHI, or `wlan0` appears; stop before Wi-Fi HAL/scan/connect.
- `private-mount-pre-wifi-gap`: private mount works but WLFW service 69 and `wlan0` still remain absent.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Safety Scope

This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
