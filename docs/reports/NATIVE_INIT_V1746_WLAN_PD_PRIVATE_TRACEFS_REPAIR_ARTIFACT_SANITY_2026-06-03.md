# Native Init V1746 WLAN-PD Private Tracefs Repair Artifact Sanity

## Summary

- Cycle: `V1746`
- Type: local-only artifact sanity verifier
- Decision: `v1746-wlan-pd-private-tracefs-repair-artifact-sanity-pass`
- Result: PASS
- V1745 manifest: `tmp/wifi/v1745-wlan-pd-private-tracefs-repair-test-boot/manifest.json`
- V1745 boot image: `tmp/wifi/v1745-wlan-pd-private-tracefs-repair-test-boot/boot_linux_v1745_wlan_pd_private_tracefs_repair.img`

## Checks

- manifest decision: `True`
- base boot exists: `True`
- init static: `True`
- helper static: `True`
- ramdisk entries: `True`
- boot markers: `True`
- route contract: `True`
- property runtime: `True`
- header parity: `True`
- kernel parity: `True`
- forbidden credential-like bytes absent: `True`
- private modes: `True`

## Artifact

- boot image: `tmp/wifi/v1745-wlan-pd-private-tracefs-repair-test-boot/boot_linux_v1745_wlan_pd_private_tracefs_repair.img`
- boot sha256: `5b86d481d79d39351d1410501b729a2d46e8680277381a54e4b0d088612289dc`
- ramdisk sha256: `35a9949c60be5a39b680772faf34de42b04c7e00da50ffd27090d6fdfcc1827d`
- init sha256: `1b7e754dc3577a7b600edb78100cb8bceb0b709da097259ee562dcec45d93ac1`
- helper sha256: `c57f57aa1b285861655ce4a4cbcea65185c17862c4c2f5a5f6cde220f145fcbe`
- helper marker: `a90_android_execns_probe v329`
- helper runtime mode: `wifi-companion-wlan-pd-cnss-output-visibility-start-only`
- helper result path: `/cache/native-init-wifi-test-boot-v1745-helper.result`

## Verified Scope

- The test image selects `wifi-companion-wlan-pd-cnss-output-visibility-start-only`.
- The manifest route excludes service-manager, PM trio, `boot_wlan`, eSoC/subsys_esoc0, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.
- The boot image contains the v329 helper marker and private tracefs/uProbe result fields.

## Safety Scope

No device command, flash, reboot, boot partition write, partition write, Wi-Fi scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC direct write, blind eSoC notify/`BOOT_DONE` spoof, global PCI rescan, or platform bind/unbind was performed by this verifier.

## Next

V1747 may be a separate one-run rollbackable live handoff for only this V1745 image, expecting `A90 Linux init 0.9.142 (v1745-wlan-pd-private-tracefs-repair)`, collecting the helper result, then rolling back to `stage3/boot_linux_v724.img`.
