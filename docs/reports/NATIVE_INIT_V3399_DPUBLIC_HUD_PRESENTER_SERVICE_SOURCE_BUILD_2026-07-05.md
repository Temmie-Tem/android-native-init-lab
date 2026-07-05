# Native Init V3399 D-public HUD Presenter Service Source Build

- Cycle: `V3399`
- Decision: `v3399-dpublic-hud-presenter-service-source-build`
- Init: `A90 Linux init 0.11.155 (v3399-dpublic-hud-presenter-service)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3399_dpublic_hud_presenter_service.img`
- Boot SHA256: `cd59b7a5eecc7dda464374c7fb412a60eeda7e2579ef7e2abe26d856277ff9dd`
- Helper SHA256: `fa395d3ecb6944a57487f3966948a634596157e4de3fdc39575a2fc502d1ceef`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3398_dpublic_hud_presenter.img`

## Change

- Adds native-init command `dpublic-hud-presenter-service [start|status|stop] [options]`.
- `start` forks a native/root child presenter that watches the bounded HUD intent file.
- `status` reports pid, intent path, status path, and whether the presenter owns a DRM fd.
- `stop` terminates the presenter, removes the pidfile, and releases DRM by process exit.
- Handoff cleanup preserves the armed durable presenter while still killing legacy unexpected native DRM holders.
- Debian remains an intent producer and does not own direct KMS.

## Validation

- Build: AArch64 helper/native-init compile, required-string audit, preserved-ramdisk overlay, boot image pack, and SHA256 capture.
- Static source checks: WSTA140 source/build tests.
- No association, DHCP, ping, public exposure, userdata mutation, switch-root, or live display action was performed by this source build.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: ``
- Candidate type: `dpublic-hud-presenter-service`.
