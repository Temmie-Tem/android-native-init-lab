# Native Init V1707 CNSS WLFW Start Branch Uprobe Source Build

## Summary

- Cycle: `V1707`
- Type: source/build-only rollbackable CNSS WLFW start-branch uprobe test boot artifact
- Decision: `v1707-cnss-wlfw-start-branch-uprobe-source-build-pass`
- Result: PASS
- Reason: extends the V1705 non-log proof from `wlfw_start` to bounded in-function branch tracepoints around DMS init and pthread_create
- Manifest: `tmp/wifi/v1707-cnss-wlfw-start-branch-uprobe-test-boot/manifest.json`
- Boot image: `tmp/wifi/v1707-cnss-wlfw-start-branch-uprobe-test-boot/boot_linux_v1707_cnss_wlfw_start_branch_uprobe.img`
- Boot SHA256: `5ebb8629f9bd0b96ccea4c44b040739b18a18d4385c52da3855770922d124b89`
- Init: `A90 Linux init 0.9.130 (v1707-cnss-wlfw-start-branch-uprobe)`
- Helper marker: `a90_android_execns_probe v316`
- Helper SHA256: `7c2c3a2661896aa4c557eb08a0353b8ab6815862d63bbfc343d8aedab73fdab2`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-cnss-output-visibility-start-only`
- Property root: `/mnt/sdext/a90/private-property-v317/v1707/dev/__properties__`
- Actors: `qrtr-ns`, `pd-mapper`, `rmt_storage`, `tftp_server`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`.
- No service-manager, PM trio, `boot_wlan`, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.

## Trace Targets

- `cnss-daemon+0xec00`: `wlfw_start` continuity target from V1705.
- `cnss-daemon+0xecd4`: DMS initialization call.
- `cnss-daemon+0xecd8`: DMS initialization return-code branch.
- `cnss-daemon+0xecf0`: WLFW worker `pthread_create` call.
- `cnss-daemon+0xecf8`: WLFW worker `pthread_create` failure path.
- `cnss-daemon+0xeda0`: WLFW worker `pthread_create` success path.

## Live Labels

- `wlfw-start-dms-init-blocked-before-worker`
- `wlfw-start-dms-init-failed-before-worker`
- `wlfw-start-pthread-create-not-reached`
- `wlfw-start-pthread-create-failed`
- `wlfw-start-pthread-create-call-no-return`
- `wlfw-start-pthread-create-success-worker-missing`
- `wlfw-start-worker-entry-reached`
- `wlfw-worker-thread-started-waiting-for-qmi-service`
- `wlfw-worker-thread-started-qmi-ind-register-sent`
- `wlfw-worker-thread-started-qmi-cap-sent`
- `cnss-target-unavailable`

## Safety Scope

This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
