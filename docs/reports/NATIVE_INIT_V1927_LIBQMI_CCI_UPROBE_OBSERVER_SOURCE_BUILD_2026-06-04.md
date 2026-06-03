# Native Init V1927 Libqmi CCI Uprobe Observer Source Build

## Summary

- Cycle: `V1927`
- Type: source/build-only rollbackable internal-modem libqmi CCI observer test boot artifact
- Decision: `v1927-libqmi-cci-uprobe-observer-source-build-pass`
- Result: PASS
- Reason: V1925 localized the live stall inside `qmi_client_init_instance`; V1926 mapped the libqmi wait loop; helper v361 adds a separate read-only `libqmi_cci.so` uprobe target group.
- Manifest: `tmp/wifi/v1927-libqmi-cci-uprobe-observer-test-boot/manifest.json`
- Boot image: `tmp/wifi/v1927-libqmi-cci-uprobe-observer-test-boot/boot_linux_v1927_libqmi_cci_uprobe_observer.img`
- Boot SHA256: `b21bbb21b3493dba49e23d491e30c7007d57ef56a5f5d29fa00ede57fb226669`
- Init: `A90 Linux init 0.9.174 (v1927-libqmi-cci-uprobe-observer)`
- Helper marker: `a90_android_execns_probe v361`
- Helper SHA256: `619c900346b83bcbf3f9588990812d9e62f7df7bdea85bb4ca0ab788bf7e37a6`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Property root: `/mnt/sdext/a90/private-property-v317/v1927/dev/__properties__`
- Base route remains the bounded internal-modem post-PM lower observer: clean firmware mounts, service managers, `pm-service`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`, service-locator/domain-list, service-notifier listener, and WLFW QRTR readback.
- Added libqmi labels: `libqmi_client_init_instance_entry`, `libqmi_initial_get_service_instance_ret`, `libqmi_initial_client_init_ret`, `libqmi_notifier_init_call`, `libqmi_notifier_init_ret`, `libqmi_wait_call`, `libqmi_wait_return`, `libqmi_loop_get_service_instance_ret`, `libqmi_loop_client_init_ret`, `libqmi_init_timeout_path`, `libqmi_init_return`, `libqmi_signal_wait_entry`, `libqmi_signal_wait_timedwait`, `libqmi_signal_wait_timeout_store`, `libqmi_xport_new_server_entry`, `libqmi_xport_new_server_signal`.
- New discriminator separates wait-loop entry, notifier setup, service-list retry, timeout return, and transport new-server wake edges.
- Stop condition: WLFW service 69, `wlan_pd`, requested `wlanmdsp`, `wlfw_ind_register_qmi`, `wlfw_cap_qmi`, or `wlan0` appears; do not proceed to HAL/scan/connect in this unit.
- Excluded by construction: private SDX50M mount, `/dev/subsys_esoc0` open, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.

## Expected Live Discriminator

- `qmi-client-init-instance-waiting-no-new-server`: WLFW worker is blocked in libqmi wait and no libqmi new-server edge arrived.
- `qmi-client-init-instance-new-server-no-wake`: libqmi saw a new-server edge but the wait loop did not wake/progress.
- `qmi-client-init-instance-timeout`: timeout path at `libqmi_cci.so+0x7954` hit.
- `qmi-client-init-instance-returned`: libqmi returned; classify the caller/downstream state before any HAL work.
- `safety-regression`: any hard-stop side effect appears; stop and roll back.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Safety Scope

This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
