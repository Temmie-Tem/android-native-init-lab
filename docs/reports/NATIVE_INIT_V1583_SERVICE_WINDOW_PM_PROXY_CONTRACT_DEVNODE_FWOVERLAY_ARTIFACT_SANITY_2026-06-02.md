# Native Init V1583 Service-window PM Proxy Contract Devnode Firmware Overlay Artifact Sanity

## Summary

- Cycle: `V1583`
- Type: local-only artifact sanity verifier
- Decision: `v1583-service-window-pm-proxy-contract-devnode-fwoverlay-artifact-sanity-pass`
- Result: PASS
- V1583 manifest: `tmp/wifi/v1583-service-window-pm-proxy-contract-devnode-fwoverlay-test-boot/manifest.json`
- V1583 boot image: `tmp/wifi/v1583-service-window-pm-proxy-contract-devnode-fwoverlay-test-boot/boot_linux_v1393_wifi_test.img`

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

- boot image: `tmp/wifi/v1583-service-window-pm-proxy-contract-devnode-fwoverlay-test-boot/boot_linux_v1393_wifi_test.img`
- boot sha256: `fbc34b1185d5d35de92bdef1c993835f8376d5c403d4c8e15b4fdf4535ce1170`
- ramdisk sha256: `494341407d174d80de203f7ee0f53e81a43cd393161a4fc66333866598d87ef9`
- init sha256: `d8cbb00b8228e765989a2ecc9d6b33a864f4e75b6fb22ed52ec3641b807825d0`
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

A later V1576 rollbackable live handoff may flash only this V1583 PM proxy contract devnode test image,
collect the helper result file, classify the service-window `mdm_helper`
launch-contract delta, and roll back to `stage3/boot_linux_v724.img`.
No credentials, scan/connect, DHCP/routes, or external ping.
