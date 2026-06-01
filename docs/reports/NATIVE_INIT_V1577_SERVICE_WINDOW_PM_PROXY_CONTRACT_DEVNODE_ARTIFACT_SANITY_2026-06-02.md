# Native Init V1577 Service-window PM Proxy Contract Devnode Artifact Sanity

## Summary

- Cycle: `V1577`
- Type: local-only artifact sanity verifier
- Decision: `v1577-service-window-pm-proxy-contract-devnode-artifact-sanity-pass`
- Result: PASS
- V1577 manifest: `tmp/wifi/v1577-service-window-pm-proxy-contract-devnode-test-boot/manifest.json`
- V1577 boot image: `tmp/wifi/v1577-service-window-pm-proxy-contract-devnode-test-boot/boot_linux_v1393_wifi_test.img`

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

- boot image: `tmp/wifi/v1577-service-window-pm-proxy-contract-devnode-test-boot/boot_linux_v1393_wifi_test.img`
- boot sha256: `4305b595fdaf307e55cff154362616e8404af59c015719f273c6ccdb836b1600`
- ramdisk sha256: `f35c85431a05643f64b5a496ba5cacaa3f6931ae3af93afc6f8ea0a570709782`
- init sha256: `f198c6ff5acba5e63646da6d9ba4a12879d0ab808aaf4d5c89357a438585fb64`
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

A later V1576 rollbackable live handoff may flash only this V1577 PM proxy contract devnode test image,
collect the helper result file, classify the service-window `mdm_helper`
launch-contract delta, and roll back to `stage3/boot_linux_v724.img`.
No credentials, scan/connect, DHCP/routes, or external ping.
