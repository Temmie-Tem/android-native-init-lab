# Native Init V1924 WLFW Client-wait Observer Source Build

## Summary

- Cycle: `V1924`
- Type: source/build-only rollbackable internal-modem WLFW client-wait observer test boot artifact
- Decision: `v1924-wlfw-client-wait-observer-source-build-pass`
- Result: PASS
- Reason: V1923 localized the blocker to post-`wlfw_service_request` WLFW service availability; helper v360 adds read-only uprobes around WLFW QMI client initialization and service-instance lookup before the first indication/capability QMI send.
- Manifest: `tmp/wifi/v1924-wlfw-client-wait-observer-test-boot/manifest.json`
- Boot image: `tmp/wifi/v1924-wlfw-client-wait-observer-test-boot/boot_linux_v1924_wlfw_client_wait_observer.img`
- Boot SHA256: `5a1c43daf7eda8d40683abafbefa57a63fe31e7709902b5582a6627e78582df9`
- Init: `A90 Linux init 0.9.173 (v1924-wlfw-client-wait-observer)`
- Helper marker: `a90_android_execns_probe v360`
- Helper SHA256: `5e2ef4c3923d0efd6d52f19e7844b646bc907a18441e7efd2cb0d84bb0fcb524`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Property root: `/mnt/sdext/a90/private-property-v317/v1924/dev/__properties__`
- Base route remains the bounded internal-modem post-PM lower observer used by V1846/V1920: firmware mounts, service managers, `pm-service`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`, service-locator/domain-list, service-notifier listener, and WLFW QRTR readback.
- Added WLFW worker labels: `wlfw_client_init_instance_call`, `wlfw_client_init_instance_retcheck`, `wlfw_client_init_instance_fail_log`, `wlfw_register_error_cb_call`, `wlfw_register_error_cb_retcheck`, `wlfw_get_service_instance_call`, `wlfw_get_service_instance_retcheck`, `wlfw_get_instance_id_call`, `wlfw_get_instance_id_retcheck`, `wlfw_send_ind_register_entry`, `wlfw_fw_mem_cond_wait`.
- New label selection distinguishes blocking in `qmi_client_init_instance`, `qmi_client_get_service_instance`, instance-id lookup, ind-register entry-before-QMI, and the FW-memory condition wait.
- Stop condition: WLFW service 69, `wlan_pd`, requested `wlanmdsp`, `wlfw_ind_register_qmi`, `wlfw_cap_qmi`, or `wlan0` appears; do not proceed to HAL/scan/connect in this unit.
- Excluded by construction: private SDX50M mount, `/dev/subsys_esoc0` open, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.

## Expected Live Discriminator

- `wlfw-worker-blocked-in-qmi-client-init-instance`: worker enters `qmi_client_init_instance` and does not return while WLFW69 remains absent.
- `wlfw-worker-blocked-in-get-service-instance`: client init returns and service-instance lookup blocks while WLFW69 remains absent.
- `wlfw-worker-service-instance-returned-before-instance-id`: lookup returns but the instance-id path does not progress.
- `wlfw-worker-entered-ind-register-before-qmi-send`: `wlfw_send_ind_register_req` entry fires but the QMI send at `0xf32c` does not.
- `wlfw-worker-thread-started-qmi-ind-register-sent`: first WLFW QMI send progressed; stop and classify the new downstream state before BDF/HAL work.
- `safety-regression`: any hard-stop side effect appears; stop and roll back.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Safety Scope

This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
