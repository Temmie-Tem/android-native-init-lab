# Native Init V759 Source Acquisition Plan

- date: `2026-05-24 KST`
- runner: `scripts/revalidation/native_wifi_source_acquisition_v759.py`
- scope: host-only Samsung OSRC source acquisition/staging gate

## Goal

V758 proved that rollback-safe kernel log instrumentation is not actionable
until exact kernel/QCACLD/CNSS source is available locally. V759 identifies the
official Samsung Open Source Release Center package for the live kernel build,
records any download gate, and checks whether the archive or extracted source is
already staged.

## Basis Evidence

- `docs/reports/NATIVE_INIT_V758_KERNEL_INSTRUMENTATION_FEASIBILITY_2026-05-24.md`
- `tmp/wifi/v758-kernel-instrumentation-feasibility/manifest.json`
- Samsung Open Source Release Center exact search:
  <https://opensource.samsung.com/uploadSearch?searchValue=A908NKSU5EWA3>
- local OSRC browser/probe evidence:
  - `tmp/source/v759-osrc-probe/A908NKSU5EWA3.html`
  - `tmp/source/v759-osrc-browser/page-meta2.json`
  - `tmp/source/v759-osrc-browser/modal-result2.json`

## Work Items

1. Validate V758 as input.
2. Parse the exact OSRC search result for model, version, source filename, source
   upload id, and announcement id.
3. Detect whether the source download is gated by human verification.
4. Check ignored local staging locations for the official archive or extracted
   source tree.
5. Verify whether target QCACLD/CNSS files are visible before any kernel patch
   planning.
6. Select V760 route.

## Forbidden

- no device command
- no boot image or partition write
- no kernel source patch
- no firmware download bypass
- no hCaptcha bypass attempt
- no tracefs/debugfs mount
- no `boot_wlan`, `qcwlanstate`, bind/unbind, module, or subsystem write
- no service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or
  external ping

## Success Criteria

- Produce `manifest.json` and `summary.md`.
- Prove whether the exact OSRC package is identified.
- Prove whether source download is manual-gated.
- Prove whether the archive/source is staged locally.
- Prove whether target QCACLD/CNSS files are visible.
- Select the next source verification or manual staging gate without patching or
  flashing.
