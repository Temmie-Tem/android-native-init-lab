# Native Init V1579 Service-window PM Proxy Contract Devnode Firmware Artifact Sanity

## Summary

- Cycle: `V1579`
- Type: local-only artifact sanity verifier
- Decision: `v1579-service-window-pm-proxy-contract-devnode-fw-artifact-sanity-pass`
- Result: PASS
- V1579 manifest: `tmp/wifi/v1579-service-window-pm-proxy-contract-devnode-fw-test-boot/manifest.json`
- V1579 boot image: `tmp/wifi/v1579-service-window-pm-proxy-contract-devnode-fw-test-boot/boot_linux_v1393_wifi_test.img`

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

- boot image: `tmp/wifi/v1579-service-window-pm-proxy-contract-devnode-fw-test-boot/boot_linux_v1393_wifi_test.img`
- boot sha256: `4467782121ca64cd7b2df58b53715c681e7925a9a9d10f70f80f55ab35d728b6`
- ramdisk sha256: `0207b105e30dc1541df6a27ff53b6e64085cd15e2c4b1efc7ecd9b203358a228`
- init sha256: `745b72c662101a8d29d61d92b28738f5fe08b3bf9f951bd248cdc49f734a0a5c`
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

A later V1576 rollbackable live handoff may flash only this V1579 PM proxy contract devnode test image,
collect the helper result file, classify the service-window `mdm_helper`
launch-contract delta, and roll back to `stage3/boot_linux_v724.img`.
No credentials, scan/connect, DHCP/routes, or external ping.
