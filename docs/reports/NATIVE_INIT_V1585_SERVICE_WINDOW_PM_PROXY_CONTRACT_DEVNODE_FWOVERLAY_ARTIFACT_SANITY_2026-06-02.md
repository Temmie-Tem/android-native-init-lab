# Native Init V1585 Service-window PM Proxy Contract Devnode Firmware Overlay Artifact Sanity

## Summary

- Cycle: `V1585`
- Type: local-only artifact sanity verifier
- Decision: `v1585-service-window-pm-proxy-contract-devnode-fwoverlay-artifact-sanity-pass`
- Result: PASS
- V1585 manifest: `tmp/wifi/v1585-service-window-pm-proxy-contract-devnode-fwoverlay-test-boot/manifest.json`
- V1585 boot image: `tmp/wifi/v1585-service-window-pm-proxy-contract-devnode-fwoverlay-test-boot/boot_linux_v1393_wifi_test.img`

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

- boot image: `tmp/wifi/v1585-service-window-pm-proxy-contract-devnode-fwoverlay-test-boot/boot_linux_v1393_wifi_test.img`
- boot sha256: `615134bcfe759f9eae7b8851087bab5e5733f16256d31d8b6748f0bb18905191`
- ramdisk sha256: `1bcca5a0f183c93e7f76b84f166bbb779c0b15de1294a775f62b5b6b2be399c9`
- init sha256: `55afa0e737a7e907e35d4e47dc7a59422caaeee25d22c9c3c0725fedd7a94108`
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

A later V1576 rollbackable live handoff may flash only this V1585 PM proxy contract devnode test image,
collect the helper result file, classify the service-window `mdm_helper`
launch-contract delta, and roll back to `stage3/boot_linux_v724.img`.
No credentials, scan/connect, DHCP/routes, or external ping.
