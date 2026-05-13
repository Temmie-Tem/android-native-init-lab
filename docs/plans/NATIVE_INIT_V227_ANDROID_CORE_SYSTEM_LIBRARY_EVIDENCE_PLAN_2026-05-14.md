# v227 Plan: Android Core/System Library Evidence Export

## Summary

v227 closes the narrowed v221 blocker after v226. v226 exported the live native
vendor source and v222 produced a usable host `vendor-root`, but v221 still
returns `daemon-native-blocked` because `cnss-daemon` / `cnss_diag` reference
Android system runtime libraries that are not part of vendor:

- `libcutils.so`
- `libnl.so`
- `libhardware_legacy.so`

v227 therefore exports only the minimal `/mnt/system/system/lib*` library
candidates required by v221 and extends v221 ELF closure to accept a separate
`--system-root` evidence tree.

## Scope

- Add `scripts/revalidation/wifi_android_core_library_export.py`.
- Extend `scripts/revalidation/wifi_vendor_elf_library_closure.py` with
  `--system-root`.
- Keep the work evidence-only and read-only.
- Do not execute CNSS daemons.
- Do not start Android services.
- Do not bring up Wi-Fi, run scans, connect, write credentials, or write sysfs.

## Evidence Model

Output directory:

```text
tmp/wifi/v227-android-core-system-library-evidence/
├── manifest.json
├── summary.md
├── native/commands/*.txt
└── system-root/
    └── system/
        ├── lib64/*.so
        └── lib/*.so
```

The exporter reads current v221 unresolved libraries, mounts system read-only
through `mountsystem ro`, then copies only safe candidates from:

- `/mnt/system/system/lib64/<library>`
- `/mnt/system/system/lib/<library>`

Missing ABI variants are recorded as missing candidates, not automatically fatal,
as long as each requested library name has at least one copied evidence file.

## v221 Resolver Change

v221 remains a host-side ELF/library closure tool. With v227 it can resolve
libraries in this order:

1. `--vendor-root` library search paths;
2. `--system-root/system/lib64`, `--system-root/system/lib`, and related system
   library directories;
3. built-in Android core runtime allowlist.

Resolved system libraries are classified as `android-system-resolved` in
`elf-dependencies.json`.

## Validation Commands

```bash
python3 scripts/revalidation/wifi_android_core_library_export.py \
  --out-dir tmp/wifi/v227-android-core-system-library-evidence

python3 scripts/revalidation/wifi_vendor_elf_library_closure.py \
  --vendor-root tmp/wifi/v222-vendor-root-evidence-export/vendor-root \
  --system-root tmp/wifi/v227-android-core-system-library-evidence/system-root \
  --out-dir tmp/wifi/v221-host-vendor-elf-library-evidence

python3 scripts/revalidation/wifi_android_env_shim_materialize.py \
  --vendor-root tmp/wifi/v222-vendor-root-evidence-export/vendor-root \
  --out-dir tmp/wifi/v224-android-env-shim-materialize

python3 scripts/revalidation/wifi_exposure_security_gate_v3.py \
  --out-dir tmp/wifi/v225-exposure-security-gate-v3
```

## Expected Decisions

- v227: `system-root-ready`
- v221: `elf-evidence-ready` if all CNSS ELF dependencies resolve
- v224: remains `shim-dryrun-ready`
- v225: may advance from `still-no-go` to the next approved planning state only
  if v221 and v224 both pass and security gate inputs remain clean

Even if v225 advances, v227 does not approve active Wi-Fi scan/connect. The next
step must still be a separate controlled CNSS start plan.

## Guardrails

- `mountsystem ro` only; no rw/remount/init path.
- `stat` and `toybox base64 -w 0` only for `/mnt/system/system/lib*/*.so`.
- Private evidence output through no-follow/0600 helpers.
- No credential paths.
- No `/sys` writes.
- No daemon execution.
- No network changes.

## Acceptance

- v227 exporter produces private `system-root` evidence.
- v221 rerun shows unresolved CNSS library list closed or narrowed with exact
  remaining names.
- v225 is rerun from updated v221/v224 evidence.
- Report documents whether active Wi-Fi remains blocked or whether the next step
  can become controlled CNSS start planning.
