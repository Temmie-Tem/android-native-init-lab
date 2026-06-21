# Native Init V3019 DOOMGENERIC Feasibility Audit

## Summary

- Decision: `v3019-doomgeneric-feasibility-host-pass`
- Device action: `none` in this host-only unit.
- Track: active Video playback / DOOM capstone.
- V3017 doompad loop proven: `1`
- GOAL frontier current: `1`
- Current native status is not WAD-backed: `1`
- Doompad consumer source present: `1`
- Existing doomgeneric source vendored: `0`
- Public WAD files committed/present: `0`
- Private WAD files currently present: `0`
- Safe next unit: `1`

## Source Provenance

- id Software DOOM source: `https://github.com/id-Software/DOOM` (GPL-2.0 source release; game data is separate).
- doomgeneric candidate port: `https://github.com/ozkl/doomgeneric` (small platform API: `DG_Init`, `DG_DrawFrame`, `DG_GetKey`, timing/sleep hooks).
- V3019 does not vendor or download source into public paths; it pins the next unit's provenance boundary only.

## Asset Policy

- WAD/IWAD data must not be committed.
- WAD/IWAD data should not be embedded into the boot image for the first real engine unit.
- Runtime staging root: `/cache/a90-runtime/pkg/doom/v3020/`.
- Private host source/asset root: `workspace/private/demo-assets/doom/`.
- First WAD-backed validation should use a private/runtime-staged WAD with hash-only public metadata.

## Current Size Baseline

- V2321 rollback image bytes: `60882944`
- V3016 doompad-loop image bytes: `61046784`
- V3016 delta vs rollback bytes: `163840`
- V3016 init bytes: `1330256`
- V3016 ramdisk cpio bytes: `11213824`

## Next Unit

- Run ID: `V3020`
- Type: `host-only-source-vendor-build-probe`
- Summary: Fetch/pin doomgeneric source privately or vendor with license notice, build a native-init adapter against KMS doompad shims, and keep WAD data private/runtime-staged.

## Safety

- Host-only audit; no flash, serial command, evdev open, input injection, sysfs write, Wi-Fi action, audio/video playback, PMIC, backlight, GPIO, regulator, GDSC, WAD copy, or forbidden partition path is touched.
- The next live WAD-backed step remains blocked until source provenance, license/NOTICE handling, runtime WAD hash policy, build size, bounded command surface, and rollback validation are pinned.

## Host Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_doomgeneric_feasibility_v3019.py tests/test_native_doomgeneric_feasibility_v3019.py`: PASS
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 -m unittest tests.test_native_doomgeneric_feasibility_v3019`: PASS
- `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 workspace/public/src/scripts/revalidation/native_doomgeneric_feasibility_v3019.py`: PASS
- `git diff --check`: PASS
