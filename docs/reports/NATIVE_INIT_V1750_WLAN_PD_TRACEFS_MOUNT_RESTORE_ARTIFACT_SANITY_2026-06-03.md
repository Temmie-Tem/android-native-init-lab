# Native Init V1750 WLAN-PD Tracefs Mount Restore Artifact Sanity

## Summary

- Cycle: `V1750`
- Type: local-only artifact sanity verifier
- Decision: `v1750-wlan-pd-tracefs-mount-restore-artifact-sanity-pass`
- Result: PASS
- V1749 manifest: `tmp/wifi/v1749-wlan-pd-tracefs-mount-restore-test-boot/manifest.json`
- V1749 boot image: `tmp/wifi/v1749-wlan-pd-tracefs-mount-restore-test-boot/boot_linux_v1749_wlan_pd_tracefs_mount_restore.img`

## Checks

- manifest decision: `True`
- base boot exists: `True`
- init static: `True`
- helper static: `True`
- ramdisk entries: `True`
- boot markers: `True`
- route contract: `True`
- property runtime: `True`
- mount_debugfs enabled: `True`
- header parity: `True`
- kernel parity: `True`
- forbidden credential-like bytes absent: `True`
- private modes: `True`

## Artifact

- boot image: `tmp/wifi/v1749-wlan-pd-tracefs-mount-restore-test-boot/boot_linux_v1749_wlan_pd_tracefs_mount_restore.img`
- boot sha256: `eedc25769b696f95be9693667e9ff56723d0e8959f7595b1ef71302d9a7f46c9`
- ramdisk sha256: `d59aa1b43ad41e88ca545ac3c08dc8140e2a5b40158bb124ac0456d5a41a94ca`
- init sha256: `6dd8b9691a18383cc246f04450072631b5a925e68c4ef3d1d1fa9ec12995f693`
- helper sha256: `c57f57aa1b285861655ce4a4cbcea65185c17862c4c2f5a5f6cde220f145fcbe`
- helper marker: `a90_android_execns_probe v329`
- helper runtime mode: `wifi-companion-wlan-pd-cnss-output-visibility-start-only`
- helper result path: `/cache/native-init-wifi-test-boot-v1749-helper.result`

## Verified Scope

- The test image selects `wifi-companion-wlan-pd-cnss-output-visibility-start-only`.
- The manifest route restores `mount_debugfs=true` and excludes service-manager, PM trio, `boot_wlan`, eSoC/subsys_esoc0, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.
- The boot image contains the v329 helper marker and private tracefs/uProbe result fields.

## Safety Scope

No device command, flash, reboot, boot partition write, partition write, Wi-Fi scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC direct write, blind eSoC notify/`BOOT_DONE` spoof, global PCI rescan, or platform bind/unbind was performed by this verifier.

## Next

V1751 may be a separate one-run rollbackable live handoff for only this V1749 image, expecting `A90 Linux init 0.9.143 (v1749-wlan-pd-tracefs-mount-restore)`, collecting the helper result, then rolling back to `stage3/boot_linux_v724.img`.
