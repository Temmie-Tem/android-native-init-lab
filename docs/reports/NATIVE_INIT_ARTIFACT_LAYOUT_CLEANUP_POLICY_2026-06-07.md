# Native Init Artifact Layout Cleanup Policy

## Summary

- Date: `2026-06-07`
- Scope: host-side repository artifact layout, no device command, no flash, no cleanup execution.
- Decision: use structured `tmp/wifi` artifact roots for new work, keep legacy flat paths readable, and prune only through dry-run cleanup tools.

## Current Scan

- `tmp`: about `31G`, dominated by `tmp/wifi`.
- `stage3`: about `968M`, with about `933M` ignored/generated artifacts.
- `tmp/wifi` currently mixes live runs, build caches, vendor extracts, test-boot images, NCM benchmarks, and scratch data in one flat namespace.
- `stage3/linux_init` is source-bearing and must not be treated like disposable output.
- Version axes: `v726` is the current boot/init baseline tag; helper markers such as `helper-v427` and validation reports such as `V2167`/`V2168` are separate numbering streams.

## New Layout

| Path | Purpose | Default retention |
| --- | --- | --- |
| `tmp/logs/bridge/` | Host bridge logs and compressed bridge log outputs | compress/rotate large logs |
| `tmp/logs/host/` | Host command stdout/stderr and harness logs for non-run-scoped work | keep by default |
| `tmp/logs/device/` | Pulled device userspace logs when not tied to a single run | keep by default |
| `tmp/logs/kernel/` | Pulled/streamed kernel logs when not tied to a single run | keep by default |
| `tmp/logs/supplicant/` | Supplicant-specific logs when not tied to a single run | keep by default |
| `tmp/logs/net/` | Network/NCM/transport logs when not tied to a single run | keep by default |
| `tmp/logs/archive/` | Compressed log bundles | prune only when explicit |
| `tmp/wifi/runs/` | Live run evidence and result bundles | keep by default |
| `tmp/wifi/builds/` | Reproducible build outputs and logs | prune old entries |
| `tmp/wifi/cache/` | Vendor/kernel/userland extraction caches | prune only when explicit |
| `tmp/wifi/bench/` | NCM/file-transfer benchmark artifacts | prune old entries |
| `tmp/wifi/scratch/` | Disposable temporary work | prune aggressively |
| `tmp/wifi/archive/` | Compressed local evidence bundles | prune only when explicit |
| `docs/artifacts/` | Public, redacted JSON/manifest summaries | tracked |

## Record Classification

- `scripts/revalidation/inventory_tmp_artifacts.py` generates a metadata-only inventory without moving or deleting local evidence.
- Public summaries are written to `docs/artifacts/TMP_ARTIFACT_INVENTORY_SUMMARY.md` and `docs/artifacts/tmp-artifact-inventory-summary.json`.
- Current inventory groups records into preserve, prune-build-products, compress-or-rotate, and review buckets so cleanup decisions are made from classified records rather than raw directory names.
- Full local folder catalog can be regenerated with `inventory_tmp_artifacts.py --write-full-private`; the default private output is `tmp/logs/archive/tmp-artifact-folder-catalog-full.json`.

## Migration Rule

- New scripts should use `scripts/revalidation/a90harness/evidence.py` helpers:
  - `wifi_artifact_dir("runs", label)`
  - `wifi_artifact_dir("builds", label)`
  - `wifi_artifact_dir("bench", label, timestamp=True)`
  - `tmp_log_dir("host", label, timestamp=True)`
  - `EvidenceStore.write_log("host", "...", text)` for run-scoped stdout/stderr
  - `docs_artifact_path(label)`
- Existing `tmp/wifi/v...` paths remain legacy-readable because many historical reports and classifiers still reference them.
- Do not bulk-move legacy evidence unless a compatibility mapping is also added.
- Existing legacy logs are not moved by default; new active scripts write command stdout/stderr under per-run `logs/host/`.

## Cleanup Policy

- `scripts/revalidation/cleanup_stage3_artifacts.py` now defaults to keeping `v48`, `v724`, `v725`, and `v726`.
- `scripts/revalidation/cleanup_tmp_wifi_artifacts.py` is dry-run by default.
- Legacy flat `tmp/wifi/*` entries are protected unless `--include-legacy-flat --legacy-days N` is provided.
- Legacy flat build products can be pruned without removing logs/evidence directories by using `--legacy-build-products-only`.
- The build-product-only matcher is intentionally narrow: `boot_linux*.img`, `ramdisk*.cpio`, compiled `init_v*`, and extensionless compiled `a90_*_v*` helper binaries.
- Validation dry-run on 2026-06-07: `cleanup_tmp_wifi_artifacts.py --json` removed `0` entries by default and protected `5409` legacy entries totaling `32126885005` bytes.
- Validation dry-run on 2026-06-07: `cleanup_stage3_artifacts.py` kept `15` current artifacts and listed `287` reproducible generated artifacts for optional removal.
- The first cleanup pass should be:

```bash
python3 scripts/revalidation/cleanup_tmp_wifi_artifacts.py --init-layout
python3 scripts/revalidation/cleanup_tmp_wifi_artifacts.py
python3 scripts/revalidation/cleanup_stage3_artifacts.py
```

## Executed Local Cleanup

- Date: `2026-06-07`
- Command class: `cleanup_tmp_wifi_artifacts.py --legacy-build-products-only --legacy-build-product-days 3 --execute`
- Scope: file-level generated build products only; legacy evidence directories, logs, JSON, text, zip, trace, and report files were not selected.
- Delete manifest: `tmp/wifi/archive/cleanup-tmp-wifi-delete-manifest-20260607-035939.json` (ignored local artifact, mode `0600`)
- Removed: `550` files, planned bytes `8496667888`, measured freed bytes `8496509749`
- `tmp/wifi` size changed from `32075777741` bytes to `23579267992` bytes.
- Post-cleanup dry-run: `--legacy-build-product-days 3` reports `0` remaining candidates.
- A later explicit build-product cleanup removed the remaining day-0 generated files while preserving logs, manifests, JSON, text, zip, trace, and report files.

## Executed Classified Tmp Cleanup

- Date: `2026-06-07`
- Command class: `cleanup_tmp_classified_artifacts.py --all-safe --execute`
- Scope: known generated kernel build output (`v766/source/out`), NCM benchmark dummy `.bin` payloads, root-level ELF helper build products, and compression of large bridge logs.
- Preserved: run directories, logs/JSON/TXT/ZIP/trace evidence, `v1073-host-only` vendor extract, and all classified evidence records.
- Delete/compress manifest: `tmp/wifi/archive/cleanup-tmp-classified-manifest-20260607-041202.json` (ignored local artifact, mode `0600`)
- Removed: `121` planned actions; planned remove bytes `7040219680`, compressed input bytes `805910745`.
- Bridge log compression: `tmp/bridge-v1111-identity.log` `805910745` bytes -> `tmp/bridge-v1111-identity.log.gz` `141169159` bytes.
- Measured `tmp` size changed from `24420769020` bytes to `16726523108` bytes; measured freed bytes `7694245912`.
- Post-cleanup classified dry-run reports `0` remaining `--all-safe` actions.
- Regenerated inventory reports `tmp_total_mib=16025.807`, with `preserve=8542.966 MiB`, `prune-build-products=7464.208 MiB`, `review=0.0 MiB`, and no large uncompressed bridge log remaining before the day-0 build-product cleanup.

## Executed Day-0 Legacy Build Product Cleanup

- Date: `2026-06-07`
- Command class: `cleanup_tmp_wifi_artifacts.py --legacy-build-products-only --legacy-build-product-days 0 --execute`
- Scope: generated legacy flat build products only; `boot_linux*.img`, `ramdisk*.cpio`, compiled `init_v*`, and compiled `a90_*_v*` helper binaries.
- Preserved: directories, logs, manifests, JSON, text, zip, trace, report files, source/cache directories, and all evidence records.
- Delete manifest: `tmp/wifi/archive/cleanup-tmp-wifi-delete-manifest-20260607-044455.json` (ignored local artifact, mode `0600`)
- Removed: `367` files, planned bytes `4760577424`.
- Regenerated inventory reports `tmp_total_mib=11485.872`, with `preserve=8431.312 MiB`, `prune-build-products=3035.926 MiB`, `review=0.0 MiB`, and no large uncompressed bridge log remaining.

## Folder Classification Review

- Date: `2026-06-07`
- Command class: `inventory_tmp_artifacts.py --write-public --write-full-private`
- Full private catalog: `tmp/logs/archive/tmp-artifact-folder-catalog-full.json` (metadata only, mode `0600`)
- Current top-level state: `tmp_total_mib=11485.872`, `tmp_entries=262`, `wifi_entries=5413`.
- Classified totals: `preserve=8431.312 MiB`, `prune-build-products=3035.926 MiB`, `review=0.0 MiB`, `compress-or-rotate=0.0 MiB`.
- Largest preserve candidate: `tmp/wifi/v1073-host-only` (`2844.133 MiB`), kept because it contains vendor extract / host-only evidence and should not be deleted without separate provenance review.
- Largest prune candidate: `tmp/wifi/v766-icnss-qcacld-patch-apply-build` (`1201.845 MiB` after `source/out` removal), now mostly kernel source/toolchain/logs; keep or remove requires source provenance decision, not automatic cleanup.
- Largest formerly ambiguous candidate `tmp/wifi/unpack-v724-test` (`52.035 MiB`) is now classified as `wifi-unpacked-build-product`; it contains reproducible unpacked `kernel` and `ramdisk` products.
- Root tool evidence directories (`tmp/diag`, `tmp/kernelinv`, `tmp/netfilter`, `tmp/wifiinv`, `tmp/kernel-config`, `tmp/cgroup-psi`, `tmp/debug-observability`) are now preserve-classified because docs or scripts reference them.
- Static Wi-Fi analysis files (`*.objdump.txt`, `cnss_*`, driver-surface captures, and marker/status files) are now preserve-classified rather than review noise.
- Local secret/config markers such as `tmp/wifi/.wifi-test.env` are classified as local-only private config; contents must never be copied to public artifacts.
- The only remaining review candidate, `tmp/wifi/scratch-untracked-esoc-static-20260531` (`0.065 MiB`), was deleted after explicit human confirmation; manifest: `tmp/wifi/archive/manual-delete-manifest-20260607-044204-scratch-untracked-esoc-static.json`.

## Existing Document Migration Boundary

- The repository still has thousands of historical `tmp/...` references because old plans/reports cite exact local evidence paths from the run that produced them.
- Those historical reports must not be bulk-rewritten: changing paths without moving the raw evidence and recording a compatibility map would weaken provenance.
- Current operational docs are the migration target; new work should point at `tmp/wifi/{runs,builds,cache,bench,scratch,archive}`, `tmp/logs/*`, and public summaries under `docs/artifacts/`.
- Absolute runtime temp paths such as `/tmp/a90-*` are not repository artifact paths; they are runtime scratch paths and are outside the `tmp/` artifact seal.
- Legacy flat `tmp/wifi/v...` paths remain readable as historical evidence paths, but new active scripts should not create additional flat legacy roots.
- If a legacy historical artifact is moved later, add a public redacted manifest in `docs/artifacts/` and a private full manifest under `tmp/logs/archive/` before deleting or relocating the original.

## Tmp Seal Criteria

- Review bucket is empty: current inventory reports `review=0.0 MiB`.
- Safe automatic cleanup is exhausted: day-0 legacy build-product dry-run reports `remove_count=0`.
- New artifact writers use `a90harness.evidence` structured roots instead of ad-hoc flat `tmp/wifi/v...` paths.
- Public state is represented by metadata summaries in `docs/artifacts/`; raw logs, firmware, boot images, credentials, and private captures remain ignored local artifacts.
- Historical `tmp` references in old reports are treated as immutable provenance, not as active output destinations.
- `tmp` should be sealed logically by policy and tooling, not by making the whole directory read-only; test harnesses still need writable structured run/log/cache directories.

## Safety

- No proprietary boot image or firmware should be committed.
- Raw logs and archives stay under ignored `tmp/wifi`.
- Public summaries must redact credentials, full MAC/BSSID/IP, SSID where sensitive, and generated supplicant configs.
- Deletion should be executed only after reviewing dry-run output.

## Build Reproducibility Fix

- The audit found that `cpio -o -H newc` preserved inode/device metadata, so moving an otherwise identical ramdisk tree from legacy `tmp/wifi/v...` to `tmp/wifi/builds/...` changed `ramdisk_sha256` and `boot_sha256`.
- Native-init boot builders now use `cpio --reproducible -o -H newc`.
- V726 build-only verification after the fix produced identical results across two consecutive builds:
  - `ramdisk_sha256=370f0fcdb8852d9f31dadbdd4700de08bcb218d176d1259069a680b8f375db50`
  - `boot_sha256=6b34aac93d4fa6d5b40355b9e13b2c1ae847c24a3685d84b0d1cd78751351d40`
- This SHA is now the flashed V726 baseline after native flash handoff, boot readback SHA verification, and `selftest fail=0`.
