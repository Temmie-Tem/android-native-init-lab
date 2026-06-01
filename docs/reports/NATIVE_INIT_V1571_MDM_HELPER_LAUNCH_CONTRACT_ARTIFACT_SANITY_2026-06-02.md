# Native Init V1571 MDM Helper Launch Contract Artifact Sanity

## Summary

- Cycle: `V1571`
- Type: local-only artifact sanity verifier
- Decision: `v1571-mdm-helper-launch-contract-artifact-sanity-pass`
- Result: PASS
- V1571 manifest: `tmp/wifi/v1571-mdm-helper-launch-contract-test-boot/manifest.json`
- V1571 boot image: `tmp/wifi/v1571-mdm-helper-launch-contract-test-boot/boot_linux_v1393_wifi_test.img`

## Checks

- manifest decision: `True`
- init static: `True`
- helper static: `True`
- ramdisk entries: `True`
- boot markers: `True`
- helper launch-contract markers: `True`
- init trigger route: `True`
- route contract: `True`
- header parity: `True`
- kernel parity: `True`
- forbidden credential-like bytes absent: `True`
- private modes: `True`

## Artifact

- boot image: `tmp/wifi/v1571-mdm-helper-launch-contract-test-boot/boot_linux_v1393_wifi_test.img`
- boot sha256: `d5fc21430720868d3836f6bb6b7b811348cfadb3596bdc3274a7aef84f0b6392`
- ramdisk sha256: `b349a927e3415b0a1fe12e42ee5624915dc0ee1397b525e2e766fb9c80e02bf4`
- init sha256: `9c5ed599d56b7f33569aa0357c1dda431ec21667ca1cc7b3d85bca718808b467`
- helper sha256: `264d3ba7215330ea08a080ade27f0b19c3b888e74ee783dda08a5a22a2aa463a`
- helper marker: `a90_android_execns_probe v289`
- helper runtime mode: `wifi-companion-android-wifi-service-window-subsys-trigger-capture`

## Verified Test Scope

- The test image selects `wifi-companion-android-wifi-service-window-subsys-trigger-capture`.
- The helper contains `android_wifi_service_window.mdm_helper_launch_contract` planned and post-spawn diagnostics.
- The helper records argv/env/identity/SELinux/dev-node/fd comparisons without changing service-window actor order.
- The PID1 argv excludes post-PM observer, forced RC1 enumerate, direct scan/connect flags, credentials, DHCP/routes, and external ping flags.

## Safety Scope

No device command, flash, reboot, boot partition write, partition write, Wi-Fi
scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC
direct write, blind eSoC notify/`BOOT_DONE` spoof, global PCI rescan, or
platform bind/unbind was performed by this verifier.

## Next

A later V1572 rollbackable live handoff may flash only this V1571 test image,
collect the helper result file, classify the service-window `mdm_helper`
launch-contract delta, and roll back to `stage3/boot_linux_v724.img`.
No credentials, scan/connect, DHCP/routes, or external ping.
