# Native Init V1581 Service-window PM Proxy Contract Devnode Firmware Target Artifact Sanity

## Summary

- Cycle: `V1581`
- Type: local-only artifact sanity verifier
- Decision: `v1581-service-window-pm-proxy-contract-devnode-fwtarget-artifact-sanity-pass`
- Result: PASS
- V1581 manifest: `tmp/wifi/v1581-service-window-pm-proxy-contract-devnode-fwtarget-test-boot/manifest.json`
- V1581 boot image: `tmp/wifi/v1581-service-window-pm-proxy-contract-devnode-fwtarget-test-boot/boot_linux_v1393_wifi_test.img`

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

- boot image: `tmp/wifi/v1581-service-window-pm-proxy-contract-devnode-fwtarget-test-boot/boot_linux_v1393_wifi_test.img`
- boot sha256: `b660caa9ad3fac57a01cb7b7d664de3970f742e3a556a16430a2341442f4d952`
- ramdisk sha256: `dfad505c154fa28ad76c870d7564cae4cee8a6bab12a79b47377e7d880cd275c`
- init sha256: `cffa39c5adc168e3ceae0feba339f9f15a6e2291cd38d294772ba3fdacc34863`
- helper sha256: `922654100570c2f7c898c11053775418c0c4881e714e5fdb22e9a274acbbde8c`
- helper marker: `a90_android_execns_probe v292`
- helper runtime mode: `wifi-companion-android-wifi-service-window-subsys-trigger-capture`

## Verified Test Scope

- The test image selects `wifi-companion-android-wifi-service-window-subsys-trigger-capture`.
- The helper contains `android_wifi_service_window.mdm_helper_launch_contract` planned and post-spawn diagnostics.
- The helper records argv/env/identity/SELinux/dev-node/fd comparisons after adding the Android-good PM proxy contract.
- The PID1 argv excludes post-PM observer, forced RC1 enumerate, direct scan/connect flags, credentials, DHCP/routes, and external ping flags.

## Safety Scope

No device command, flash, reboot, boot partition write, partition write, Wi-Fi
scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC
direct write, blind eSoC notify/`BOOT_DONE` spoof, global PCI rescan, or
platform bind/unbind was performed by this verifier.

## Next

A later V1576 rollbackable live handoff may flash only this V1581 PM proxy contract devnode test image,
collect the helper result file, classify the service-window `mdm_helper`
launch-contract delta, and roll back to `stage3/boot_linux_v724.img`.
No credentials, scan/connect, DHCP/routes, or external ping.
