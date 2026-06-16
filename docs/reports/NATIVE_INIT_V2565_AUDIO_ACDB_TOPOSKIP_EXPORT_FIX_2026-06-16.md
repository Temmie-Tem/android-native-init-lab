# NATIVE_INIT V2565 — ACDB topology-skip dynamic export fix

Date: 2026-06-16

## Scope

Host-only fix for the V2564 topology-skip failure. V2564 proved the live handoff rolled back safely, but the intended `acdb_loader_send_common_custom_topology()` interposer never ran because the V2561 preload exported that symbol as `LOCAL HIDDEN` only.

## Change

- Added explicit default symbol visibility to `libacdb_topology_skip_v2561.c` for `acdb_loader_send_common_custom_topology()`.
- Hardened `build_android_acdb_toposkip_per_device_manifest_v2561.py` so `exports_common_topology_skip` requires a `GLOBAL DEFAULT` symbol, not just any symtab occurrence.
- Added test coverage for the default-visibility source marker and the non-hidden dynamic export check.

## Validation

Commands run:

```bash
python3 -m py_compile \
  workspace/public/src/scripts/revalidation/build_android_acdb_toposkip_per_device_manifest_v2561.py \
  tests/test_build_android_acdb_toposkip_per_device_manifest_v2561.py
PYTHONPATH=tests python3 -m unittest tests.test_build_android_acdb_toposkip_per_device_manifest_v2561 -v
python3 workspace/public/src/scripts/revalidation/build_android_acdb_toposkip_per_device_manifest_v2561.py --build > /tmp/v2565-toposkip-build.json
readelf -Ws workspace/private/builds/audio/v2561-acdb-toposkip-per-device-capture-host-only/bin/liba90_acdb_toposkip_per_device_preload_v2561.so | rg 'acdb_loader_send_common_custom_topology|acdb_ioctl|a90_arm_capture|ioctl'
```

Result:

- focused tests: `3` passed.
- private build manifest: `ok=true`.
- fixed preload SHA-256: `7a37cebb38fae83d9cd0882861aacba77dfd490ce28d2cc1254cab75323259ae`.
- `readelf` now shows `acdb_loader_send_common_custom_topology` as `GLOBAL DEFAULT` in the dynamic symbol table.

Relevant `readelf` proof:

```text
8: 000032b0   236 FUNC    GLOBAL DEFAULT    8 acdb_loader_send_common_custom_topology
66: 000032b0   236 FUNC    GLOBAL DEFAULT    8 acdb_loader_send_common_custom_topology
```

## Boundary

No device action, no Android boot, no native calibration ioctl, no speaker write, no raw ACDB payload committed.

## Decision

`v2565-toposkip-dynamic-export-fixed-host-only` is complete. The next bounded unit is to rerun the V2564 topology-skip per-device live handoff with the rebuilt preload and require the topology-skip marker before accepting any per-device capture.
