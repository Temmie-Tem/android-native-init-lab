# Native Init V3385 Wi-Fi Service Boundary Source Build

- Cycle: `V3385`
- Decision: `v3385-wifi-service-boundary-source-build`
- Init: `A90 Linux init 0.11.141 (v3385-wifi-service-boundary)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3385_wifi_service_boundary.img`
- Boot SHA256: `33fabe5b90cab57c9e538236e2ad8abef28822807de4051cd8b7027053218710`
- Helper SHA256: `fa395d3ecb6944a57487f3966948a634596157e4de3fdc39575a2fc502d1ceef`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3384_server_distro_hardware_contract.img`

## Change

- Carries forward the V3384 server-distro hardware contract surface.
- Adds a native-owned `wifi service [status|start|stop|once] <dir>` command surface.
- The service watches a shared request file and writes a redacted response file so a Debian chroot can request native-owned `status` and `scan` without taking raw WLAN ownership.
- This rung intentionally excludes connect, DHCP, ping, DNS, API probing, and public tunnel exposure.
- The builder drops the immediate previous `v3384` DOOM engine from the preserved ramdisk overlay so the V3385 image stays within the 64 MiB boot-partition limit.
- This is source/build only; live validation is a separate checked-helper flash gate.

## Validation

- Build: AArch64 helper/native-init compile, required-string audit, preserved-ramdisk overlay, boot image pack, and SHA256 capture.
- Static source checks: `tests.test_native_wifi_service_boundary_source`.
- Builder regression: `tests.test_build_native_init_boot_v3385_wifi_service_boundary`.
- No device action was performed in this source unit.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: ``
- Candidate type: `wifi-service-boundary`.
