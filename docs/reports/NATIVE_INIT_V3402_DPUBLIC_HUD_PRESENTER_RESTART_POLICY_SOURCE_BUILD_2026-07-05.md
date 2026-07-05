# Native Init V3402 D-public HUD Presenter Restart Policy Source Build

- Cycle: `V3402`
- Decision: `v3402-dpublic-hud-presenter-restart-policy-source-build`
- Init: `A90 Linux init 0.11.158 (v3402-dpublic-hud-presenter-restart-policy)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3402_dpublic_hud_presenter_restart_policy.img`
- Boot SHA256: `57821e94857cb58b397c737a73d5f85381329f5e9ec8a6b55dc7d5dbb6a7d3f1`
- Helper SHA256: `fa395d3ecb6944a57487f3966948a634596157e4de3fdc39575a2fc502d1ceef`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3401_dpublic_hud_shared_run_bind.img`

## Change

- Keeps the V3401 shared run-dir bind and stale-intent dedupe.
- Adds `dpublic-hud-presenter-service restart` as stop-then-start.
- Fails closed if the stop phase cannot release the old DRM owner.
- Cleans stale pidfiles before a new start and records `stale-cleaned` status.
- Adds live-visible marker `A90WSTA146 restart-stop-start-stale-pid-cleanup`.

## Validation

- Build: AArch64 helper/native-init compile, required-string audit, preserved-ramdisk overlay, boot image pack, and SHA256 capture.
- Static source checks: WSTA146 source/build tests.
- No association, DHCP, ping, public exposure, userdata format/populate, switch-root, or live display action was performed by this source build.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: ``
- Candidate type: `dpublic-hud-presenter-restart-policy`.
