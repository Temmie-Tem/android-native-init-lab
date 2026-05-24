# Native Init V761 Source Download Handoff Plan

- date: `2026-05-24 KST`
- runner: `scripts/revalidation/native_wifi_source_handoff_v761.py`
- scope: host-only operator handoff for manual OSRC source download/staging

## Goal

V760 provides the source staging verifier, but the official Samsung OSRC source
download still requires manual browser human-verification. V761 creates a
handoff packet and local shell helper so the manual download can be staged and
V760 rerun without retyping paths or touching the device.

## Basis Evidence

- `docs/reports/NATIVE_INIT_V759_SOURCE_ACQUISITION_2026-05-24.md`
- `docs/reports/NATIVE_INIT_V760_SOURCE_STAGING_2026-05-24.md`
- `tmp/wifi/v759-source-acquisition/manifest.json`
- `tmp/wifi/v760-source-staging/manifest.json`
- staging guide: `kernel_build/README.md`

## Work Items

1. Validate V759 exact source identification.
2. Validate V760 staging verifier status.
3. Generate `handoff.md`.
4. Generate `run-v761-source-download-handoff.sh` with `0700` permissions.
5. Keep browser opening opt-in only through `V761_OPEN_BROWSER=1`.
6. Ensure the helper only copies an already downloaded official archive into
   ignored `kernel_build/` and reruns V760.

## Forbidden

- no hCaptcha bypass
- no automatic browser open unless the operator explicitly sets
  `V761_OPEN_BROWSER=1`
- no source patch
- no source extraction
- no kernel build
- no boot image or partition write
- no device command
- no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping

## Success Criteria

- Produce `manifest.json`, `summary.md`, `handoff.md`, and executable handoff
  script.
- Prove no browser open, file copy, device command, or boot image write was
  executed by the generator.
- Make the next human action exact and repeatable.
