# Native Init V1771 WLAN-PD Service-object Visible Source Build

## Summary

- Cycle: `V1771`
- Type: source/build-only rollbackable WLAN-PD service-object-visible test boot artifact
- Decision: `v1771-wlan-pd-service-object-visible-source-build-pass`
- Result: PASS
- Reason: carries the approved one-run V1764 dormant helper gate into a rollbackable test boot with late listener evidence.
- Manifest: `tmp/wifi/v1771-wlan-pd-service-object-visible-test-boot/manifest.json`
- Boot image: `tmp/wifi/v1771-wlan-pd-service-object-visible-test-boot/boot_linux_v1771_wlan_pd_service_object_visible.img`
- Boot SHA256: `5b1b58652ecf07cce27587a4d08d4459df61c158f699b011d5b2dc1d49c3b0d5`
- Init: `A90 Linux init 0.9.140 (v1771-wlan-pd-service-object-visible)`
- Helper marker: `a90_android_execns_probe v331`
- Helper SHA256: `0f2d69082088e021d5c42035154ad70de1264826b2df0c8708147ec415b9cfe3`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-service-object-visible-trigger-start-only`
- Property root: `/mnt/sdext/a90/private-property-v317/v1771/dev/__properties__`
- Actors: `servicemanager`, `hwservicemanager`, VND service-manager fallback, `qrtr-ns`, `pd-mapper`, `rmt_storage`, `tftp_server`, `pm_proxy_helper`, `pm-service`, `/dev/subsys_modem` holder, `cnss_diag`, and stock `cnss-daemon`.
- Added evidence: service-object visibility summary, CNSS peripheral uprobes, WLFW/readback fields, and late WLAN-PD service-notifier listener state.
- No full `pm-proxy`, `boot_wlan`, restart-PD request, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Live Labels

- `service-object-nonnull-vote-sent-wlanmdsp-requested`
- `service-object-nonnull-vote-sent-no-request`
- `service-object-nonnull-no-vote`
- `service-object-still-null`

## Safety Scope

This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
