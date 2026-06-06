# Public Artifact Summaries

`docs/artifacts/` stores small, redacted, reviewable summaries derived from local
test artifacts.

## Allowed

- Result labels, pass/fail decisions, phase timers, command names, and tool versions
- Boot image SHA256 values and reproducible source/build paths
- Redacted device state such as masked MAC/IP/SSID labels
- Artifact manifests with file names, sizes, hashes, and secret-scan status
- Metadata-only tmp inventory summaries such as `TMP_ARTIFACT_INVENTORY_SUMMARY.md`

## Not Allowed

- Wi-Fi PSK, raw `wpa_supplicant.conf`, or environment files
- Full MAC, BSSID, routable IP, credentials, cookies, tokens, or private keys
- Raw EFS/NV/RFS/vendor/firmware dumps
- Samsung/Qualcomm boot images, firmware blobs, or proprietary binary payloads
- Large raw logs better kept under ignored `tmp/wifi/runs/`

## Current Summaries

- `TMP_ARTIFACT_INVENTORY_SUMMARY.md` – classifies current `tmp`/`tmp/wifi` entries by record type and cleanup posture without copying raw evidence.
- `tmp-artifact-inventory-summary.json` – machine-readable version of the same metadata-only inventory.
