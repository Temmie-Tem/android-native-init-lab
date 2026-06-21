# Native Init V3027 DOOMGENERIC Runtime WAD Preflight

## Summary

- Cycle: `V3027`
- Track: active Video playback / DOOM capstone.
- Decision: `v3027-doomgeneric-runtime-wad-staging-contract-ready`
- Device action: `none` in this host-only unit.
- Preflight OK: `1`
- Live asset ready: `1`
- Public WAD files committed/present: `0`
- Private WAD root exists: `1`
- Private WAD/IWAD candidate count: `1`
- Private WAD candidates within size cap: `1`
- Private WAD candidates magic ok: `1`
- Private WAD candidate ambiguous: `0`

## Prior Evidence Gates

- V3023 policy ready: `1`
- V3023 private WAD root pinned: `1`
- V3023 WAD size cap pinned: `1`
- V3025 command bridge ready: `1`
- V3025 ramdisk WAD count zero: `1`
- V3026 command bridge live pass: `1`
- V3026 no OTG required: `1`
- V3026 WAD not staged: `1`

## Runtime WAD Contract

- Private WAD root: `workspace/private/demo-assets/doom/wads/`
- Runtime staging root: `/cache/a90-runtime/pkg/doom/v3024/`
- Runtime WAD path: `/cache/a90-runtime/pkg/doom/v3024/DOOM1.WAD`
- Runtime WAD max bytes: `67108864`
- Selected WAD bytes: `4196020`
- Selected WAD SHA256: `1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771`
- Selected WAD magic: `IWAD`
- Stage at live time only; do not copy WAD data during this host-only unit.
- Verify the selected SHA256 before any future WAD-backed DOOM command.
- Clean up the runtime WAD after any future bounded smoke.
- WAD/IWAD bytes must stay out of public, ramdisk, and boot image.

## Command Contract

- Status command: `video demo doom status`
- Future verify command: `video demo doom verify --wad runtime-private --sha256 EXPECTED`
- Future play command: `video demo doom play [frames] --wad runtime-private --sha256 EXPECTED`
- Default smoke frames: `300`
- Max smoke frames: `5400`
- Input path: `serial-doompad-to-DG_GetKey`
- OTG required: `0`
- Sound: `disabled-nosound-nomusic`
- Next requires command implementation: `1`

## Interpretation

- V3027 is host-only and does not stage, copy, or embed WAD bytes.
- Current state has exactly one private WAD/IWAD candidate with a pinned hash/size contract, so the next bounded unit is command implementation, not immediate live gameplay.

## Safety

- Host-only preflight; no flash, serial command, WAD copy, Wi-Fi action, sysfs write, boot image write, ramdisk write, PMIC, backlight, GPIO, regulator, GDSC, or forbidden partition path is touched.
- Public output records no WAD bytes and no private WAD filename.

## Host Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_doomgeneric_runtime_wad_preflight_v3027.py tests/test_native_doomgeneric_runtime_wad_preflight_v3027.py`: PASS
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 -m unittest tests.test_native_doomgeneric_runtime_wad_preflight_v3027`: PASS
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 -m unittest tests.test_native_init_frontier_select`: PASS
- `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 workspace/public/src/scripts/revalidation/native_init_frontier_select.py --json`: PASS
- `git diff --check`: PASS

## Next Unit

- Run ID: `V3028`
- Type: `host-only WAD-backed doomgeneric command implementation`
- Summary: Wire bounded runtime-private WAD verify/play command handling around the selected private WAD hash, still keeping WAD bytes out of public, ramdisk, and boot image.
