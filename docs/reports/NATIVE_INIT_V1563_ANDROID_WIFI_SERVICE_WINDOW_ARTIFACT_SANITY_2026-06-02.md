# Native Init V1563 Android Wi-Fi Service-Window Artifact Sanity

## Summary

- Cycle: `V1563`
- Type: local-only artifact sanity verifier
- Decision: `v1563-android-wifi-service-window-artifact-sanity-pass`
- Result: PASS
- V1562 manifest: `tmp/wifi/v1562-android-wifi-service-window-test-boot/manifest.json`
- V1562 boot image: `tmp/wifi/v1562-android-wifi-service-window-test-boot/boot_linux_v1393_wifi_test.img`

## Checks

- manifest decision: `True`
- base boot exists: `True`
- init static: `True`
- helper static: `True`
- ramdisk entries: `True`
- boot markers: `True`
- init service-window route: `True`
- service-window contract: `True`
- header parity: `True`
- kernel parity: `True`
- forbidden credential-like bytes absent: `True`
- private modes: `True`

## Artifact

- boot image: `tmp/wifi/v1562-android-wifi-service-window-test-boot/boot_linux_v1393_wifi_test.img`
- boot sha256: `3b927f60b81caaf60f01ea5fcf23cccc56d68cbc58edaf5db6e7993f5cad262d`
- ramdisk sha256: `6458f17cdd301f9f70be9c508b05a152aac27b29ee485a37bdb3f8c8b291fc4b`
- init sha256: `5638f696643bc1df74eea413c1aeb97b9939cd36666897bb8d23c854e1b15ace`
- helper sha256: `660d88fc9e0ebdf6c95e495d9dd659c09321feb407fe6a7f77213f3b5c2bb411`
- helper marker: `a90_android_execns_probe v287`
- helper runtime mode: `wifi-companion-android-wifi-service-window-start-only`

## Verified Test Scope

- The test image selects the Android Wi-Fi service-window route.
- The PID1 argv contains `--allow-android-wifi-service-window`.
- The PID1 argv excludes post-PM observer, forced RC1 enumerate, private patched CNSS daemon, and direct PM observer flags.
- The generated manifest records no credential, scan/connect, DHCP/route, external ping, flash, or partition write action for the source/build step.

## Safety Scope

No device command, flash, reboot, boot partition write, partition write,
Wi-Fi scan/connect, credential handling, DHCP/routes, external ping,
PMIC/GPIO/GDSC direct write, blind eSoC notify/`BOOT_DONE` spoof, global
PCI rescan, or platform bind/unbind was performed by this verifier.

## Next

V1564 may perform a rollbackable live handoff for only the V1562 test
image, expect `A90 Linux init 0.9.69 (v1562-service-window)`, collect
the service-window log, summary, focused dmesg, and `wlan0` state, then
roll back to `stage3/boot_linux_v724.img`. The live target remains only
`cnss-daemon wlfw_start`/`wlfw_service_request`; no credentials,
scan/connect, DHCP/routes, or external ping.
