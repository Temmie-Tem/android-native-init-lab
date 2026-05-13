# v226 Report: Native Vendor Root Live Export

## Summary

v226 adds a live native read-only vendor-root exporter and uses it to remove the
previous v222 `export-source-required` blocker.

- tool: `scripts/revalidation/wifi_vendor_live_export.py`
- plan: `docs/plans/NATIVE_INIT_V226_VENDOR_ROOT_LIVE_EXPORT_PLAN_2026-05-14.md`
- output: `tmp/wifi/v226-vendor-root-live-export`
- baseline device: `A90 Linux init 0.9.59 (v159)`
- result: PASS
- decision: `vendor-source-exported`

The exporter mounted the live vendor candidate with ext4 `ro,noload`, pulled
allowlisted files through `toybox base64`, wrote private/no-follow host
evidence, and unmounted the temporary mount point.

## v226 Result

```text
PASS out_dir=/home/temmie/dev/A90_5G_rooting/tmp/wifi/v226-vendor-root-live-export decision=vendor-source-exported reason=live read-only vendor source is ready for v222 rerun
```

Key manifest values:

| field | value |
| --- | --- |
| decision | `vendor-source-exported` |
| pulled_files | `22` |
| pulled_total_bytes | `1405464` |
| block | `sda29` |
| dynamic major:minor | `259:32` |
| cleanup_ok | `true` |

Required files were exported:

- `vendor-source/bin/cnss-daemon`
- `vendor-source/bin/cnss_diag`

The exporter also pulled vendor-side libraries found by recursive ELF
`DT_NEEDED` inspection, including QMI, CLD80211, diag, and time-genoff vendor
libraries.

## Follow-up Rerun Results

The v226 output was passed into the existing v222/v221/v224/v225 chain.

| stage | result | decision | reason |
| --- | --- | --- | --- |
| v222 | PASS | `vendor-root-ready` | minimal vendor root evidence is ready for v221 rerun |
| v221 | FAIL | `daemon-native-blocked` | unresolved ELF/library blockers remain |
| v224 | PASS | `shim-dryrun-ready` | dry-run shim materialization is ready |
| v225 | PASS | `still-no-go` | gate has blocked prerequisites: `vendor_evidence` |

The previous `shim_materialization` blocker is closed. The remaining Wi-Fi
blocker is now narrower: v221 still needs an Android core/system runtime
library evidence closure for `libcutils.so`, `libnl.so`, and
`libhardware_legacy.so`.

## v221 Remaining Blocker

Current v221 unresolved library names:

| daemon | unresolved |
| --- | --- |
| `cnss-daemon` | `libcutils.so`, `libnl.so` |
| `cnss_diag` | `libcutils.so`, `libhardware_legacy.so`, `libnl.so` |

These are not proof that daemon execution is impossible. They mean that the
host-side vendor-only root is not enough to model the Android runtime closure.
Next work should capture or classify the matching system/core libraries without
executing daemons.

## Validation

Static validation:

```bash
python3 -m py_compile \
  scripts/revalidation/wifi_vendor_live_export.py \
  scripts/revalidation/wifi_vendor_root_evidence_export.py \
  scripts/revalidation/wifi_vendor_elf_library_closure.py \
  scripts/revalidation/wifi_android_env_shim_materialize.py \
  scripts/revalidation/wifi_exposure_security_gate_v3.py

python3 - <<'PY'
import sys
sys.path.insert(0, 'scripts/revalidation')
import wifi_vendor_live_export
wifi_vendor_live_export.validate_command_guard()
print('v226 command guard PASS')
PY

git diff --check
```

Live export and rerun commands:

```bash
python3 scripts/revalidation/wifi_vendor_live_export.py \
  --out-dir tmp/wifi/v226-vendor-root-live-export

python3 scripts/revalidation/wifi_vendor_root_evidence_export.py \
  --source-vendor-root tmp/wifi/v226-vendor-root-live-export/vendor-source \
  --out-dir tmp/wifi/v222-vendor-root-evidence-export

python3 scripts/revalidation/wifi_vendor_elf_library_closure.py \
  --vendor-root tmp/wifi/v222-vendor-root-evidence-export/vendor-root \
  --out-dir tmp/wifi/v221-host-vendor-elf-library-evidence

python3 scripts/revalidation/wifi_android_env_shim_materialize.py \
  --vendor-root tmp/wifi/v222-vendor-root-evidence-export/vendor-root \
  --out-dir tmp/wifi/v224-android-env-shim-materialize

python3 scripts/revalidation/wifi_exposure_security_gate_v3.py \
  --out-dir tmp/wifi/v225-exposure-security-gate-v3
```

## Hashes

```text
50bade8decad032988de39702892f50276e50926c581da7cbad69a022639c96c  tmp/wifi/v226-vendor-root-live-export/manifest.json
461673558520c374289d9e379fef62671a9a8d8a82d38d162173d801872c90d0  tmp/wifi/v226-vendor-root-live-export/summary.md
87de424ca8d620ab12f1e0ee097de89b0807147ed044473c737c07b4d9cbdcfa  tmp/wifi/v222-vendor-root-evidence-export/manifest.json
70a91522eb31287ab42d0d4f05a1c7308ba4cad79f063efa57f36c97611b7d81  tmp/wifi/v221-host-vendor-elf-library-evidence/manifest.json
7f5efa0520b38da781782e362813a1583f1b42584ccd4e7f63642da9f469dc90  tmp/wifi/v224-android-env-shim-materialize/manifest.json
aadda132c30427b905ced07dbc10a1d96edbf52b5383217f7d3d945db8dde7f5  tmp/wifi/v225-exposure-security-gate-v3/manifest.json
```

## Guardrails

- No vendor/system/sysfs/debugfs/configfs writes.
- No daemon execution.
- No rfkill, link-up, scan, connect, DHCP, or credential handling.
- Temporary `sda29` mount only, ext4 `ro,noload`.
- Host evidence output remains private/no-follow.

## Next Work

Plan v227 as Android core/system library evidence closure:

1. determine whether unresolved `libcutils.so`, `libnl.so`, and
   `libhardware_legacy.so` are Android core/system runtime dependencies;
2. if needed, export the minimal read-only system library subset with the same
   private/no-follow model;
3. rerun v221 and then v225;
4. keep active Wi-Fi daemon execution, scan, and connect blocked until v225 no
   longer reports `vendor_evidence`.
