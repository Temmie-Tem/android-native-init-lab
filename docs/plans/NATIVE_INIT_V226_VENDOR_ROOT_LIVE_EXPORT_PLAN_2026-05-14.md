# v226 Plan: Native Vendor Root Live Export

## Summary

v226 closes the v222/v221 blocker by exporting a minimal host-visible vendor
root from the live native environment.

- baseline device: `A90 Linux init 0.9.59 (v159)`
- previous blocker: v222 `export-source-required`, v221 `vendor-root-required`
- planned tool: `scripts/revalidation/wifi_vendor_live_export.py`
- evidence output: `tmp/wifi/v226-vendor-root-live-export`
- follow-up reruns: v222 -> v221 -> v224 -> v225

This is still a read-only evidence step. It does not execute Wi-Fi daemons,
mutate ICNSS controls, change rfkill/link state, scan, connect, or collect
credentials.

## Goal

Create a private host directory that looks like a vendor root and contains:

- `bin/cnss-daemon`
- `bin/cnss_diag`
- the vendor libraries reachable through recursive ELF `DT_NEEDED` inspection

The result should be usable as:

```bash
python3 scripts/revalidation/wifi_vendor_root_evidence_export.py \
  --source-vendor-root tmp/wifi/v226-vendor-root-live-export/vendor-source \
  --out-dir tmp/wifi/v222-vendor-root-evidence-export
```

## Extraction Model

The live exporter uses the already validated v209/v210 pattern:

1. read `/sys/class/block/sda29/dev`;
2. create only a temporary block node under `/tmp/a90-v226-*`;
3. mount the vendor candidate as ext4 `ro,noload`;
4. pull allowlisted files through `toybox base64 -w 0`;
5. write host evidence with `0700` directories and `0600` files;
6. unmount the temporary mount point.

The exporter uses the current sysfs major/minor for `sda29`, not a hardcoded
value, because previous reports observed that dynamic minor numbers can change
between boots.

## Guardrails

The tool must not:

- create persistent `/dev/block/sda29` nodes;
- mount without `ro,noload`;
- write to vendor, system, sysfs, debugfs, configfs, or firmware paths;
- run `cnss-daemon`, `cnss_diag`, Wi-Fi HAL, wificond, supplicant, or hostapd;
- perform rfkill, link-up, scan, connect, DHCP, or credential workflows;
- dump a full partition;
- copy `/data/misc/wifi` or credential files;
- follow destination symlinks;
- create group/world-readable evidence output.

## Follow-up Validation

After v226 export succeeds:

```bash
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

Expected progression:

- v222 should move from `export-source-required` to `vendor-root-ready`;
- v221 should move from `vendor-root-required` to either
  `elf-evidence-ready` or a concrete unresolved-library blocker;
- v224 should move from `shim-source-required` to `shim-dryrun-ready` only if
  v222 is ready;
- v225 should remain the active exposure gate and must not approve scan/connect
  unless all prerequisites are ready.

## Acceptance

- `wifi_vendor_live_export.py` command guard passes.
- The live export produces private evidence under
  `tmp/wifi/v226-vendor-root-live-export`.
- `vendor-source/bin/cnss-daemon` and `vendor-source/bin/cnss_diag` are present.
- The temporary vendor mount is unmounted after collection.
- v222/v221/v224/v225 reruns record the new state without active Wi-Fi
  operations.

