# Native Init V3342 SoftAP S3 Firmware Source IfType Probe Source Build

- Cycle: `V3342`
- Decision: `v3342-softap-s3-fwsource-iftype-probe-source-build-pass`
- Init: `A90 Linux init 0.11.106 (v3342-softap-s3-fwsource-iftype-probe)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3342_softap_s3_fwsource_iftype_probe.img`
- Boot SHA256: `836f76249d578ef42e25a2d0c7b43cc3ef1d8db9efe5dabc6ee5ce13b10e5502`
- Helper SHA256: `fa395d3ecb6944a57487f3966948a634596157e4de3fdc39575a2fc502d1ceef`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3335_gpu_z3_primary_setcrtc.img`

## Change

- Keeps the V3341 `wifi softap iftype-probe [timeout_ms]` AP-iftype add/delete proof.
- Fixes the pre-iftype `wlan0` blocker by letting the QCACLD firmware_class feeder read from the helper's already mounted read-only vendor firmware tree before falling back to global `/vendor/firmware` paths.
- Adds helper source policy marker `qcacld-fwsource-mounted-vendor-first`.
- Keeps AP service below start: no generated SSID/PSK config, no `wpa_supplicant mode=2`, no `udhcpd`, no listener, no AP address, no route/NAT.

## Validation Contract

- PASS requires post-flash `selftest fail=0`, helper-window `wlan0_present=1`, firmware_class feed `source_rc=0`, `decision=softap-iftype-probe-pass`, `ap_iftype_add_rc=0`, `ap_iftype_iface_created=1`, and `ap_iftype_cleanup_ok=1`.
- Public output remains metadata-only and must not contain SSID, PSK, BSSID, MAC, client identifiers, concrete peer addresses, DHCP leases, or transfer payloads.

## Static Validation

- `py_compile`: V3342 builder and focused source tests.
- Unit tests: V3342 firmware-source feeder source/build contract plus retained V3341 SoftAP iftype contract.
- Build: AArch64 helper/native-init compile, preserved-ramdisk overlay, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V3342 identity, SoftAP v2, no-start fields, and the mounted-vendor-first firmware source policy marker.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: ``
- Candidate type: `softap-s3-fwsource-iftype-probe-candidate`.
