# Native Init V3023 DOOMGENERIC Integration Policy

## Summary

- Decision: `v3023-doomgeneric-private-integration-policy-ready`
- Device action: `none` in this host-only unit.
- Track: active Video playback / DOOM capstone.
- Policy choice: keep the pinned doomgeneric source private for the next build-only native-init integration step.
- Private doomgeneric source pinned: `1`
- Private source clean: `1`
- V3020 port probe pass: `1`
- V3020 AArch64 probe linked: `1`
- V3022 checkpoint live pass retained: `1`
- Public WAD files committed/present: `0`
- Runtime WAD currently staged: `0`
- Safe next host-only unit: `1`

## Source Handling

- Source URL: `https://github.com/ozkl/doomgeneric`
- Private source root: `workspace/private/demo-assets/doom/doomgeneric-v3020`
- Pinned commit: `dcb7a8dbc7a16ce3dda29382ac9aae9d77d21284`
- Current commit: `dcb7a8dbc7a16ce3dda29382ac9aae9d77d21284`
- Commit date: `2026-04-12`
- Commit subject: `boolean fix`
- Source file count: `202`
- LICENSE SHA256: `8177f97513213526df2cf6184d8ff986c675afb514d4e68a404010521b880643`
- Public vendoring is deferred until a later GPL/NOTICE review; V3024 should only integrate from the private pinned source.

## Current Native DOOM State

- Status source: `workspace/public/src/native-init/v319/30_status_hud.inc.c`
- Menu source: `workspace/public/src/native-init/v319/40_menu_apps.inc.c`
- DOOM stub marker present: `1`
- Doompad serial input marker present: `1`
- Current engine explicitly not WAD-backed: `1`
- WAD not-bundled marker present: `1`
- `video demo doom play` command present: `1`

## Asset Policy

- WAD/IWAD data must not be committed.
- WAD/IWAD data must not be embedded into a boot image or ramdisk.
- Runtime staging allowlist root: `/cache/a90-runtime/pkg/doom/v3024/`.
- Private WAD root for operator staging: `workspace/private/demo-assets/doom/wads/`.
- Runtime WAD size cap before first smoke: `67108864` bytes.
- Public reports may record WAD size and SHA256 only after a private WAD is intentionally staged.

## Build Gate For V3024

- Build type: `private-source native-init source integration without WAD`.
- Engine-only boot-image delta cap: `2097152` bytes.
- The V3024 build must report native-init binary delta and boot-image delta.
- Abort V3024 if any `.wad` data appears in the ramdisk, boot image, or public tree.
- Do not flash merely because the source integrates; first produce a host build/report and keep live validation rollback-gated.

## Runtime Command Surface

- Status command: `video demo doom status`.
- Verify command target: `video demo doom verify --wad runtime-private --sha256 EXPECTED`.
- Play command target: `video demo doom play [frames] --wad runtime-private --sha256 EXPECTED`.
- Default smoke frames: `300`.
- Hard frame cap: `5400`.
- The player must remain interruptible and restore the menu/HUD on exit.

## Port Policy

- Frame path: doomgeneric DG_DrawFrame -> existing a90_kms_present/pageflip path.
- Input path: serial doompad snapshot edges -> doomgeneric DG_GetKey queue.
- OTG keyboard and touch are not required for this path; serial doompad remains the controller bridge.
- Sound is disabled for the first native doomgeneric engine integration.

## Safety

- Host-only policy gate; no flash, serial command, WAD copy, Wi-Fi action, sysfs write, boot image write, PMIC, backlight, GPIO, regulator, GDSC, or forbidden partition path is touched.
- The current runtime WAD is not staged, so a live WAD-backed DOOM smoke remains blocked until private WAD staging and hash metadata exist.

## Host Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_doomgeneric_integration_policy_v3023.py tests/test_native_doomgeneric_integration_policy_v3023.py`: PASS
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 -m unittest tests.test_native_doomgeneric_integration_policy_v3023`: PASS
- `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 workspace/public/src/scripts/revalidation/native_doomgeneric_integration_policy_v3023.py`: PASS
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 -m unittest tests.test_native_init_frontier_select`: PASS
- `git diff --check`: PASS

## Next Unit

- Run ID: `V3024`
- Type: `private-source native-init integration build`
- Summary: Build a host-only/native-init source integration around the pinned private doomgeneric source, keeping WAD data runtime-private and absent from the boot image.
