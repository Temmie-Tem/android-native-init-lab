# v227 Report: Android Core/System Library Evidence Export

## Summary

v227 exported the Android system runtime libraries needed by v221 CNSS ELF
closure and extended v221 to accept a separate `--system-root`. This closes the
post-v226 daemon ELF/library blocker without executing CNSS daemons or performing
any active Wi-Fi operation.

Final result:

- v227: PASS, decision `system-root-ready`
- v221 rerun: PASS, decision `elf-evidence-ready`
- v224 rerun: PASS, decision `shim-dryrun-ready`
- v225 rerun: PASS, decision `cnss-start-plan-approved`

This approval is limited to writing a later controlled CNSS start plan. It is
not approval to scan/connect in this step.

## Implemented

- Added `scripts/revalidation/wifi_android_core_library_export.py`.
- Extended `scripts/revalidation/wifi_vendor_elf_library_closure.py` with
  `--system-root` and `android-system-resolved` dependency classification.
- Added plan:
  `docs/plans/NATIVE_INIT_V227_ANDROID_CORE_SYSTEM_LIBRARY_EVIDENCE_PLAN_2026-05-14.md`.

## v227 Live Export

Command:

```bash
python3 scripts/revalidation/wifi_android_core_library_export.py \
  --out-dir tmp/wifi/v227-android-core-system-library-evidence \
  --library 'android.system.suspend@1.0.so'
```

Result:

```text
PASS out_dir=/home/temmie/dev/A90_5G_rooting/tmp/wifi/v227-android-core-system-library-evidence decision=system-root-ready reason=Android core/system library evidence is ready for v221 rerun
```

Copied files:

| path | size | sha256 |
| --- | ---: | --- |
| `system/lib64/android.system.suspend@1.0.so` | 112528 | `136afad2c95ddd45d891535c1b8c0b795db6f8d3e0872e557851564c1c38219a` |
| `system/lib/android.system.suspend@1.0.so` | 78260 | `d16a78c1e76c437545faea195b4e03a214d01d61b3d579502ed4bd40ef30c795` |
| `system/lib64/libcutils.so` | 74224 | `06440a6a73708d40b14c3ece45b9ce952521903965cbc1bbdac2594b5030d355` |
| `system/lib/libcutils.so` | 50380 | `0503db85de6265b2e4d40facdbd7d11739e2c0eab770d5ea00deb194f7fd3853` |
| `system/lib64/libhardware_legacy.so` | 28144 | `e0b790c7bd159a8d61c6f43e55e8fde00f4488a413664017a6a356f8dc3f0a9f` |
| `system/lib/libhardware_legacy.so` | 15896 | `e7da221166d5dd4026554f8b409624d84a1410409f66a73b36f24a13166b982f` |
| `system/lib64/libnl.so` | 146896 | `f9d966fa384c93bf76e0f803591af7f96afdb5c43931c377a722ceccdedaf26a` |

Missing candidate:

- `system/lib/libnl.so`: `stat-failed`

This is not fatal because each requested library name has at least one exported
candidate and the 64-bit CNSS dependency chain resolves.

## Rerun Results

```bash
python3 scripts/revalidation/wifi_vendor_elf_library_closure.py \
  --vendor-root tmp/wifi/v222-vendor-root-evidence-export/vendor-root \
  --system-root tmp/wifi/v227-android-core-system-library-evidence/system-root \
  --out-dir tmp/wifi/v221-host-vendor-elf-library-evidence
```

```text
PASS out_dir=/home/temmie/dev/A90_5G_rooting/tmp/wifi/v221-host-vendor-elf-library-evidence decision=elf-evidence-ready reason=CNSS daemon ELF and direct library evidence captured
cnss-daemon ok []
cnss_diag ok []
```

```bash
python3 scripts/revalidation/wifi_android_env_shim_materialize.py \
  --vendor-root tmp/wifi/v222-vendor-root-evidence-export/vendor-root \
  --out-dir tmp/wifi/v224-android-env-shim-materialize

python3 scripts/revalidation/wifi_exposure_security_gate_v3.py \
  --out-dir tmp/wifi/v225-exposure-security-gate-v3
```

```text
PASS out_dir=/home/temmie/dev/A90_5G_rooting/tmp/wifi/v224-android-env-shim-materialize decision=shim-dryrun-ready reason=dry-run shim materialization is ready for v225 gate integration
PASS out_dir=/home/temmie/dev/A90_5G_rooting/tmp/wifi/v225-exposure-security-gate-v3 decision=cnss-start-plan-approved reason=all prerequisite and exposure gates passed for writing a later start plan
```

## Guardrails Verified

- `mountsystem ro` only.
- No daemon execution.
- No Android service start.
- No rfkill write, link-up, scan, or connect.
- No credential collection.
- No system/vendor write.
- Private evidence output uses the shared no-follow/private output helpers.

## Artifact Hashes

```text
62608e2e1634714c6b7c000aaace32ed157f10957e27a375a8f289dbae4eaf67  tmp/wifi/v227-android-core-system-library-evidence/manifest.json
9c3353d9dd16212fd1b1f13d6f5c7c8dac27f505e4d852d59073dc748ad50cae  tmp/wifi/v227-android-core-system-library-evidence/summary.md
a59126feebb52352e6d8427fc36fe3018e895cc73268a34556908e0752965584  tmp/wifi/v221-host-vendor-elf-library-evidence/manifest.json
a860f113e6a84877b0b9f208a9a6a0c85d4c62f6fa56a5421254f605ef0a141b  tmp/wifi/v221-host-vendor-elf-library-evidence/elf-dependencies.json
e7fdd2ae7f498d52157a36cb5038f7c55613605ccfa9c2de0215a283cee712d8  tmp/wifi/v224-android-env-shim-materialize/manifest.json
306058786372ca0951dcb25d2ad6cceccaaa25cff06d4ec080b6c3581c4dd685  tmp/wifi/v225-exposure-security-gate-v3/manifest.json
```

## Next Step

v225 now allows the next item to be a controlled CNSS start plan. That next plan
must still be separate and must define:

- exact command surface;
- recovery path;
- timeout/rollback policy;
- exposure boundaries;
- no credential collection;
- no scan/connect until the start-only experiment is proven safe.
