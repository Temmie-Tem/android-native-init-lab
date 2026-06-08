# Native Init V2174 Wi-Fi Urandom Connect Source Build

## Summary

- Candidate tag: `v2174-wifi-urandom-connect`
- Parent baseline: `v2169-transport-contract`
- Type: source/build-only test boot candidate.
- Decision: `v2174-wifi-urandom-connect-source-build-pass`
- Result: PASS
- Reason: V2174 keeps the V2169 transport contract, adds native-init `wifi connect [profile]`, and ensures `/dev/random` + `/dev/urandom` are present for WPA key negotiation.
- Manifest: `workspace/private/builds/native-init/v2174-wifi-urandom-connect-test-boot/manifest.json`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v725_fasttransport.img`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v2174_wifi_urandom_connect.img`
- Boot SHA256: `cda957e4302d66e407fc97a95932501f0ef2ac655ee264c94519111fece0b3ba`
- Boot SHA verification: source/build output only; live flash/readback/selftest must be recorded separately before promotion.
- Init: `A90 Linux init 0.9.251 (v2174-wifi-urandom-connect)`
- Helper marker: `a90_android_execns_probe helper-v427` (binary marker string: `a90_android_execns_probe v427`)
- Helper SHA256: `99bdd67f0cd2fcaf6557478a97f85d405a0de3d6b0858ea17b4d46d7ce162ca1`

## Included Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v726/dev/__properties__`
- Preserved from V2172: `wifi status`, bounded credential-free `wifi scan [delay_ms]`, V726 Wi-Fi lifecycle route, and `transport.contract=1` status fields.
- Added: `wifi connect [profile]` waits for `wlan0`, prepares the redacted supplicant config, starts or reuses standalone `wpa_supplicant`, sends redacted ctrl commands, and waits for carrier.
- Added: base `/dev` bootstrap creates `/dev/random` (1:8) and `/dev/urandom` (1:9), both mode `0666`, so `wpa_supplicant` can generate SNonce during the 4-way handshake.
- Not added: DHCP, route installation, external ping, boot autoconnect, or raw credential logging.

## Safety Scope

- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, platform bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE path is included.
- The live validation must remain credential-redacted and rollbackable to `workspace/private/inputs/boot_images/boot_linux_v2169_transport_contract.img`.
