# Native Init V1704 CNSS WLFW Downstream Uprobe Source Build

## Summary

- Cycle: `V1704`
- Type: source/build-only rollbackable CNSS WLFW downstream uprobe test boot artifact
- Decision: `v1704-cnss-wlfw-downstream-uprobe-source-build-pass`
- Result: PASS
- Reason: extends the V1702 non-log proof from `wlfw_start` to bounded downstream WLFW worker/QMI tracepoints
- Manifest: `tmp/wifi/v1704-cnss-wlfw-downstream-uprobe-test-boot/manifest.json`
- Boot image: `tmp/wifi/v1704-cnss-wlfw-downstream-uprobe-test-boot/boot_linux_v1704_cnss_wlfw_downstream_uprobe.img`
- Boot SHA256: `0db8664b0ef3f4f92cad9c80c55400599ac2af01ab2b73a4b2c83dc5ada86775`
- Init: `A90 Linux init 0.9.129 (v1704-cnss-wlfw-downstream-uprobe)`
- Helper marker: `a90_android_execns_probe v315`
- Helper SHA256: `757c3c217d0c4df95a446ce0519940bb6f782fe73515172796dc32e041ebb58f`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-cnss-output-visibility-start-only`
- Property root: `/mnt/sdext/a90/private-property-v317/v1704/dev/__properties__`
- Actors: `qrtr-ns`, `pd-mapper`, `rmt_storage`, `tftp_server`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`.
- No service-manager, PM trio, `boot_wlan`, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.

## Trace Targets

- `cnss-daemon+0xec00`: `wlfw_start` continuity target from V1702.
- `cnss-daemon+0xd9fc`: `wlfw_service_request` worker thread entry.
- `cnss-daemon+0xf32c`: first concrete WLFW indication-register QMI sync call.
- `cnss-daemon+0xf460`: WLFW capability QMI sync call.
- `cnss-daemon+0xe808`: secondary DMS service-request thread entry.

## Live Labels

- `wlfw-worker-thread-started-waiting-for-qmi-service`
- `wlfw-worker-thread-started-qmi-ind-register-sent`
- `wlfw-worker-thread-started-qmi-cap-sent`
- `wlfw-worker-thread-missing-after-wlfw-start`
- `cnss-target-unavailable`

## Safety Scope

This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
