# Native Init V1573 MDM Helper Launch Contract Crashfix Artifact Sanity

## Summary

- Cycle: `V1573`
- Type: local-only artifact sanity verifier
- Decision: `v1573-mdm-helper-launch-contract-crashfix-artifact-sanity-pass`
- Result: PASS
- V1573 manifest: `tmp/wifi/v1573-mdm-helper-launch-contract-crashfix-test-boot/manifest.json`
- V1573 boot image: `tmp/wifi/v1573-mdm-helper-launch-contract-crashfix-test-boot/boot_linux_v1393_wifi_test.img`

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

- boot image: `tmp/wifi/v1573-mdm-helper-launch-contract-crashfix-test-boot/boot_linux_v1393_wifi_test.img`
- boot sha256: `ea028a2c0c96241a9e1a558cfa39af631924ee428672004f410218b8e15c893a`
- ramdisk sha256: `61f824051ec3910d6ff5ea46c6348524a3daf260b5fb4ede8e637924baa89afd`
- init sha256: `49796e33be9b9965e338c7ad85ea1ae87970bcfba86c40921a66326e0fb40bd7`
- helper sha256: `ecc9b3ad1fd5a3644e8fed1a54e57befb92641c33ff1f2c2c6d77a4087109518`
- helper marker: `a90_android_execns_probe v290`
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

A later V1574 rollbackable live handoff may flash only this V1573 crashfix test image,
collect the helper result file, classify the service-window `mdm_helper`
launch-contract delta, and roll back to `stage3/boot_linux_v724.img`.
No credentials, scan/connect, DHCP/routes, or external ping.
