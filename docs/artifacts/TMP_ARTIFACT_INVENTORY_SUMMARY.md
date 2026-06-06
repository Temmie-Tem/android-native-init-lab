# Tmp Artifact Inventory Summary

- Generated: `2026-06-07 04:45:09 +0900`
- Root: `tmp`
- Tmp entries: `262`
- Wifi entries: `5412`
- Tmp total: `11485.872 MiB`

## Classification Taxonomy

| Axis | Meaning | Default action |
| --- | --- | --- |
| `wifi-connect-evidence` / `wifi-run-evidence` / `wifi-host-analysis` | Evidence and run records | preserve |
| `wifi-probe-evidence` / `wifi-static-analysis` | Small probe outputs, disassembly, marker/status files | preserve |
| `wifi-private-local-config` | Local-only secret/config marker paths | preserve locally; do not copy contents |
| `wifi-test-boot-evidence` | Mixed test-boot dirs; logs preserved, generated binaries pruneable | prune build products only |
| `wifi-unpacked-build-product` | Reproducible unpacked kernel/ramdisk products | prune after explicit review |
| `wifi-build-cache` | Build/extract/cache dirs | prune build products or cache after review |
| `wifi-benchmark` | Transfer benchmark payloads | prune dummy payloads after summary |
| `root-structured-log-root` | New top-level structured logs under `tmp/logs/` | preserve |
| `root-tool-evidence` | Older tool outputs referenced by docs/scripts | preserve until indexed |
| `root-bridge-log` | Large host bridge logs | compress or rotate |
| `root-bridge-log-compressed` | Compressed host bridge logs | preserve |
| `root-legacy-run-evidence` | Older root-level run records | preserve until indexed |

## By Recommended Action

| Action | Count | MiB |
| --- | ---: | ---: |
| `compress-or-rotate` | 7 | 0.0 |
| `preserve` | 5122 | 8431.312 |
| `prune-build-products` | 544 | 3035.926 |

## Top Tmp Entries

| Path | Category | Action | MiB |
| --- | --- | --- | ---: |
| `tmp/wifi` | `wifi-artifact-root` | `preserve` | 11335.23 |
| `tmp/bridge-v1111-identity.log.gz` | `root-bridge-log-compressed` | `preserve` | 134.629 |
| `tmp/inspect-v1571-ramdisk` | `root-build-inspection` | `prune-build-products` | 5.84 |
| `tmp/logs` | `root-structured-log-root` | `preserve` | 1.578 |
| `tmp/validation` | `root-legacy-run-evidence` | `preserve` | 1.271 |
| `tmp/current-native-dmesg-after-v464.txt` | `root-legacy-run-evidence` | `preserve` | 1.043 |
| `tmp/xfer-http-test` | `root-benchmark` | `prune-build-products` | 1.0 |
| `tmp/verify` | `root-legacy-run-evidence` | `preserve` | 0.883 |
| `tmp/worktree-cleanup` | `root-tool-evidence` | `preserve` | 0.647 |
| `tmp/v214-after-rebind-retry-dmesg.txt` | `root-legacy-run-evidence` | `preserve` | 0.44 |
| `tmp/v214-current-dmesg.txt` | `root-legacy-run-evidence` | `preserve` | 0.435 |
| `tmp/source` | `root-tool-evidence` | `preserve` | 0.36 |
| `tmp/diag-src` | `root-build-inspection` | `prune-build-products` | 0.204 |
| `tmp/a90-v190-live-20260511-212826` | `root-legacy-run-evidence` | `preserve` | 0.141 |
| `tmp/a90-v190-live-fixed-20260511-212947` | `root-legacy-run-evidence` | `preserve` | 0.14 |
| `tmp/diag` | `root-tool-evidence` | `preserve` | 0.097 |
| `tmp/kernelinv` | `root-tool-evidence` | `preserve` | 0.084 |
| `tmp/security` | `root-tool-evidence` | `preserve` | 0.081 |
| `tmp/a90-h2-soak-suite-dry` | `root-legacy-run-evidence` | `preserve` | 0.079 |
| `tmp/a90-h2-soak-suite-dry-2` | `root-legacy-run-evidence` | `preserve` | 0.078 |

## Top Wifi Entries

| Path | Category | Action | MiB |
| --- | --- | --- | ---: |
| `tmp/wifi/v1073-host-only` | `wifi-host-analysis` | `preserve` | 2844.133 |
| `tmp/wifi/v766-icnss-qcacld-patch-apply-build` | `wifi-build-cache` | `prune-build-products` | 1201.845 |
| `tmp/wifi/v1331-esoc-disasm` | `wifi-run-evidence` | `preserve` | 240.684 |
| `tmp/wifi/v773-stock-dtb-tail-repack` | `wifi-run-evidence` | `preserve` | 150.472 |
| `tmp/wifi/v775-boot-incompat-postmortem` | `wifi-run-evidence` | `preserve` | 102.957 |
| `tmp/wifi/v775-boot-incompat-postmortem-refresh` | `wifi-run-evidence` | `preserve` | 102.957 |
| `tmp/wifi/v770-instrumented-diagnostic-boot-staging` | `wifi-run-evidence` | `preserve` | 102.361 |
| `tmp/wifi/v1915-stock-kernel-service74-static-xref` | `wifi-run-evidence` | `preserve` | 99.993 |
| `tmp/wifi/v1915-kernel-static-preflight` | `wifi-host-analysis` | `preserve` | 99.973 |
| `tmp/wifi/unpack-v724-test` | `wifi-unpacked-build-product` | `prune-build-products` | 52.035 |
| `tmp/wifi/v770-probe-unpack` | `wifi-run-evidence` | `preserve` | 51.465 |
| `tmp/wifi/v2167-connect-dhcp-google-ping-handoff-v726-5g-fwready-wait-5min-no-helper-holder` | `wifi-connect-evidence` | `preserve` | 37.05 |
| `tmp/wifi/v2167-connect-dhcp-google-ping-handoff-v726-final-sha-smoke` | `wifi-connect-evidence` | `preserve` | 35.371 |
| `tmp/wifi/v2167-connect-dhcp-google-ping-handoff-v726-5g-fwready-wait-smoke-no-helper-holder` | `wifi-connect-evidence` | `preserve` | 35.363 |
| `tmp/wifi/v2167-connect-dhcp-google-ping-handoff-hold-diag-v30-2g-modem-holder` | `wifi-connect-evidence` | `preserve` | 35.002 |
| `tmp/wifi/v2167-connect-dhcp-google-ping-handoff-hold-diag-v28-2g-power-on` | `wifi-connect-evidence` | `preserve` | 35.0 |
| `tmp/wifi/v2167-connect-dhcp-google-ping-handoff-hold-diag-v32-5g-lifecycle-owner` | `wifi-connect-evidence` | `preserve` | 34.903 |
| `tmp/wifi/v2167-connect-dhcp-google-ping-handoff-hold-diag-v29-2g-lifetime` | `wifi-connect-evidence` | `preserve` | 34.854 |
| `tmp/wifi/v2167-connect-dhcp-google-ping-handoff-hold-diag-v26-2g` | `wifi-connect-evidence` | `preserve` | 34.854 |
| `tmp/wifi/v2167-connect-dhcp-google-ping-handoff-standalone-wpa-v22` | `wifi-connect-evidence` | `preserve` | 34.847 |

## Top Review Entries

| Path | Category | Action | MiB |
| --- | --- | --- | ---: |

## Notes

- This is a metadata-only public summary; it does not copy raw logs, firmware, boot images, credentials, or private payloads.
- Cleanup remains separate and dry-run first. This inventory is for classification and review.
