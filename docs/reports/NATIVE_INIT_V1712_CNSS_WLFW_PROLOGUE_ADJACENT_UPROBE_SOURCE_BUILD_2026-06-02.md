# Native Init V1712 CNSS WLFW Prologue Adjacent Uprobe Source Build

## Summary

- Cycle: `V1712`
- Type: source/build-only rollbackable CNSS `wlfw_start` prologue-adjacent uprobe test boot artifact
- Decision: `v1712-cnss-wlfw-prologue-adjacent-uprobe-source-build-pass`
- Result: PASS
- Reason: extends V1710/V1711 to adjacent targets between `wlfw_start@0xec00` and first `pthread_mutex_init@0xec58`
- Manifest: `tmp/wifi/v1712-cnss-wlfw-prologue-adjacent-uprobe-test-boot/manifest.json`
- Boot image: `tmp/wifi/v1712-cnss-wlfw-prologue-adjacent-uprobe-test-boot/boot_linux_v1712_cnss_wlfw_prologue_adjacent_uprobe.img`
- Boot SHA256: `e654cf3ebb56cf54cd992af2d38c09084e538c80598e56df17a5386f251d26be`
- Init: `A90 Linux init 0.9.132 (v1712-cnss-wlfw-prologue-adjacent-uprobe)`
- Helper marker: `a90_android_execns_probe v318`
- Helper SHA256: `57d2944b8a04c1d4b1db175a1c904498a2a0ed385998dbe63027222821b6a845`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-cnss-output-visibility-start-only`
- Property root: `/mnt/sdext/a90/private-property-v317/v1712/dev/__properties__`
- Actors: `qrtr-ns`, `pd-mapper`, `rmt_storage`, `tftp_server`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`.
- No service-manager, PM trio, `boot_wlan`, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.

## New Trace Targets

- `cnss-daemon+0xec20`: log severity setup immediately before unconditional log call.
- `cnss-daemon+0xec24`: unconditional log wrapper call.
- `cnss-daemon+0xec28`: first post-log instruction.
- `cnss-daemon+0xec34` / `0xec44`: optional setup calls on the zero-argument path.
- `cnss-daemon+0xec48`: common path after log/optional setup.
- `cnss-daemon+0xec50` / `0xec54` / `0xec58`: first pthread init edge.

## Safety Scope

This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
