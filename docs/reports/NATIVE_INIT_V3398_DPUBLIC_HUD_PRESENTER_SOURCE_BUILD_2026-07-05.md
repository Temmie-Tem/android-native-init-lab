# Native Init V3398 D-public HUD Presenter Source Build

- Cycle: `V3398`
- Decision: `v3398-dpublic-hud-presenter-source-build`
- Init: `A90 Linux init 0.11.154 (v3398-dpublic-hud-presenter)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3398_dpublic_hud_presenter.img`
- Boot SHA256: `b18be6a39eb41fb71a5256db3b23d5c648631fb164061b98b35a35ffba9f3a0c`
- Helper SHA256: `fa395d3ecb6944a57487f3966948a634596157e4de3fdc39575a2fc502d1ceef`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3397_wsta_execute_gate_screen.img`

## Change

- Adds native-init command `dpublic-hud-presenter [validate|present] [intent-path]`.
- Reads a bounded `a90-dpublic-hud-intent-v1` JSON intent file.
- Rejects stale intent, forbidden fields, and unknown top-level fields.
- Presents a minimal native/root-owned KMS HUD; Debian remains an intent producer and does not own direct KMS.
- Does not add Wi-Fi connect, DHCP, public tunnel, native reboot, flash behavior, or Debian direct DRM ownership.

## Validation

- Build: AArch64 helper/native-init compile, required-string audit, preserved-ramdisk overlay, boot image pack, and SHA256 capture.
- Static source checks: `tests.test_dpublic_smoke_helpers` and WSTA136 source proof.
- No association, DHCP, ping, public exposure, userdata mutation, switch-root, or live display action was performed by this source build.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: ``
- Candidate type: `dpublic-hud-presenter`.
