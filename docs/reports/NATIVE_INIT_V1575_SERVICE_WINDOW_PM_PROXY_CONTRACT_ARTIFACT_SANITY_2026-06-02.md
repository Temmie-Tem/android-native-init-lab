# Native Init V1575 Service-window PM Proxy Contract Artifact Sanity

## Summary

- Cycle: `V1575`
- Type: local-only artifact sanity verifier
- Decision: `v1575-service-window-pm-proxy-contract-artifact-sanity-pass`
- Result: PASS
- V1575 manifest: `tmp/wifi/v1575-service-window-pm-proxy-contract-test-boot/manifest.json`
- V1575 boot image: `tmp/wifi/v1575-service-window-pm-proxy-contract-test-boot/boot_linux_v1393_wifi_test.img`

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

- boot image: `tmp/wifi/v1575-service-window-pm-proxy-contract-test-boot/boot_linux_v1393_wifi_test.img`
- boot sha256: `c10ee64d49e548c01963221cfad6ac06c7c0013cfeb025579308f1f04af75759`
- ramdisk sha256: `c54276096ce09e94102e3f194343062646e2e8c722aed567cac599745230ed06`
- init sha256: `23cb7320af08d9ed0f4306287b81ae1d5ee7bd5acd0f75089ebc65c6a8e2ca7e`
- helper sha256: `1bf13ba694dd7a60b038d5bc9960b10e268ae9d95cdfc5f20e20428e27010d5c`
- helper marker: `a90_android_execns_probe v291`
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

A later V1576 rollbackable live handoff may flash only this V1575 PM proxy contract test image,
collect the helper result file, classify the service-window `mdm_helper`
launch-contract delta, and roll back to `stage3/boot_linux_v724.img`.
No credentials, scan/connect, DHCP/routes, or external ping.
