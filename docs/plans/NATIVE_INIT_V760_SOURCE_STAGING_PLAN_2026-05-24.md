# Native Init V760 Source Staging Plan

- date: `2026-05-24 KST`
- runner: `scripts/revalidation/native_wifi_source_staging_v760.py`
- scope: host-only Samsung source staging verifier

## Goal

V759 identified the exact Samsung OSRC source package but confirmed that the
download is manual-gated. V760 makes the next gate repeatable: after the
official archive or extracted tree is staged locally, verify archive readability
and the required QCACLD/CNSS target source files without extracting large
archives or loading them into memory.

## Basis Evidence

- `docs/reports/NATIVE_INIT_V759_SOURCE_ACQUISITION_2026-05-24.md`
- `tmp/wifi/v759-source-acquisition/manifest.json`
- staging guide: `kernel_build/README.md`

## Work Items

1. Validate V759 as input.
2. Check ignored staging paths for the official source archive.
3. Check ignored staging paths for an extracted source tree.
4. Read archive member lists without extraction when an archive is present.
5. Verify required target files:
   - `drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_main.c`
   - `drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_driver_ops.c`
   - `drivers/net/wireless/cnss2/main.c`
   - `drivers/net/wireless/cnss2/qmi.c`
6. Select whether V761 can plan kernel instrumentation.

## Forbidden

- no device command
- no boot image or partition write
- no kernel source patch
- no source extraction by default
- no full archive hash by default
- no firmware download bypass
- no hCaptcha bypass attempt
- no `boot_wlan`, `qcwlanstate`, bind/unbind, module, or subsystem write
- no service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or
  external ping

## Success Criteria

- Produce `manifest.json` and `summary.md`.
- Prove whether official source is staged.
- Prove whether a staged archive is readable.
- Prove whether target QCACLD/CNSS source files are visible.
- Keep kernel patch planning blocked until target files are verified.
