# Native Init V1568 Service-Window Subsys Trigger Result Artifact Sanity

## Summary

- Cycle: `V1568`
- Type: local-only artifact sanity verifier
- Decision: `v1568-service-window-subsys-trigger-result-artifact-sanity-pass`
- Result: PASS
- V1568 manifest: `tmp/wifi/v1568-service-window-subsys-trigger-result-test-boot/manifest.json`
- V1568 boot image: `tmp/wifi/v1568-service-window-subsys-trigger-result-test-boot/boot_linux_v1393_wifi_test.img`

## Checks

- manifest decision: `True`
- base boot exists: `True`
- init static: `True`
- helper static: `True`
- ramdisk entries: `True`
- boot markers: `True`
- init trigger route: `True`
- trigger/result contract: `True`
- header parity: `True`
- kernel parity: `True`
- forbidden credential-like bytes absent: `True`
- private modes: `True`

## Artifact

- boot image: `tmp/wifi/v1568-service-window-subsys-trigger-result-test-boot/boot_linux_v1393_wifi_test.img`
- boot sha256: `0bf402cf31ce53e4e6a8d365d4b105cb31ec8e58b484c9a681872c62c87279a4`
- ramdisk sha256: `5ef0bfa56cec60733fd960279fbbf9258be709f92aed37bb67278e66ede4176b`
- init sha256: `9e629d6436360aef2367249c19c1f8b6f21ce0c212d513de51fa478b57d4c975`
- helper sha256: `ecc889253d8de7b8afdc09721ca780ea28d839fec00b5cb16380c6b7fd419c5b`
- helper marker: `a90_android_execns_probe v288`
- helper runtime mode: `wifi-companion-android-wifi-service-window-subsys-trigger-capture`
- helper result path: `/cache/native-init-wifi-test-boot-v1393-helper.result`
- supervisor timeout: `75` seconds

## Verified Test Scope

- The test image selects `wifi-companion-android-wifi-service-window-subsys-trigger-capture`.
- The PID1 argv contains both Android service-window allow flags.
- The PID1 argv excludes the start-only route, post-PM observer route, forced RC1 enumerate, private patched CNSS daemon path, direct scan/connect flags, and external ping flags.
- The generated manifest records no credential, scan/connect, DHCP/route, external ping, flash, or partition write action for the source/build step.
- The boot image contains `cnss_before_esoc`/subsys-trigger evidence markers and passes `--result-output-path` so the helper writes a private result artifact for the next live classifier.

## Safety Scope

No device command, flash, reboot, boot partition write, partition write,
Wi-Fi scan/connect, credential handling, DHCP/routes, external ping,
PMIC/GPIO/GDSC direct write, blind eSoC notify/`BOOT_DONE` spoof, global
PCI rescan, or platform bind/unbind was performed by this verifier.

## Next

A later V1569 rollbackable live handoff may flash only this V1568 test
image, expect `A90 Linux init 0.9.69 (v1568-service-window-subsys-trigger-result)`,
collect the service-window log, summary, focused dmesg, and `wlan0` state,
then roll back to `stage3/boot_linux_v724.img`. The live target remains
WLFW/BDF/FW-ready/`wlan0` progress and trigger-window classification;
no credentials, scan/connect, DHCP/routes, or external ping.
