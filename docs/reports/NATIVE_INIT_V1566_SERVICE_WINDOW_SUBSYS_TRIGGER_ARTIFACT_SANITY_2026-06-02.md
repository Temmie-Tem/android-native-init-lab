# Native Init V1566 Service-Window Subsys Trigger Artifact Sanity

## Summary

- Cycle: `V1566`
- Type: local-only artifact sanity verifier
- Decision: `v1566-service-window-subsys-trigger-artifact-sanity-pass`
- Result: PASS
- V1566 manifest: `tmp/wifi/v1566-android-wifi-service-window-subsys-trigger-test-boot/manifest.json`
- V1566 boot image: `tmp/wifi/v1566-android-wifi-service-window-subsys-trigger-test-boot/boot_linux_v1393_wifi_test.img`

## Checks

- manifest decision: `True`
- base boot exists: `True`
- init static: `True`
- helper static: `True`
- ramdisk entries: `True`
- boot markers: `True`
- init trigger route: `True`
- trigger contract: `True`
- header parity: `True`
- kernel parity: `True`
- forbidden credential-like bytes absent: `True`
- private modes: `True`

## Artifact

- boot image: `tmp/wifi/v1566-android-wifi-service-window-subsys-trigger-test-boot/boot_linux_v1393_wifi_test.img`
- boot sha256: `4b2cd6b0fe07c5826c0c3865b5fd60fff37a3d3a9437f5998312b7103cc11a65`
- ramdisk sha256: `82bf31af60721d6fdd5ec78ce4e93cb1f086e7b16028eedb93b5a1c988320a02`
- init sha256: `f64b88079291d2bea5bf1ce4ccaaf36dadfab0ca25ffee244fafccad180b6b1b`
- helper sha256: `660d88fc9e0ebdf6c95e495d9dd659c09321feb407fe6a7f77213f3b5c2bb411`
- helper marker: `a90_android_execns_probe v287`
- helper runtime mode: `wifi-companion-android-wifi-service-window-subsys-trigger-capture`
- supervisor timeout: `75` seconds

## Verified Test Scope

- The test image selects `wifi-companion-android-wifi-service-window-subsys-trigger-capture`.
- The PID1 argv contains both Android service-window allow flags.
- The PID1 argv excludes the start-only route, post-PM observer route, forced RC1 enumerate, private patched CNSS daemon path, direct scan/connect flags, and external ping flags.
- The generated manifest records no credential, scan/connect, DHCP/route, external ping, flash, or partition write action for the source/build step.
- The boot image contains `cnss_before_esoc`/subsys-trigger evidence markers for the next live classifier.

## Safety Scope

No device command, flash, reboot, boot partition write, partition write,
Wi-Fi scan/connect, credential handling, DHCP/routes, external ping,
PMIC/GPIO/GDSC direct write, blind eSoC notify/`BOOT_DONE` spoof, global
PCI rescan, or platform bind/unbind was performed by this verifier.

## Next

A later V1567 rollbackable live handoff may flash only this V1566 test
image, expect `A90 Linux init 0.9.69 (v1566-service-window-subsys-trigger)`,
collect the service-window log, summary, focused dmesg, and `wlan0` state,
then roll back to `stage3/boot_linux_v724.img`. The live target remains
WLFW/BDF/FW-ready/`wlan0` progress and trigger-window classification;
no credentials, scan/connect, DHCP/routes, or external ping.
