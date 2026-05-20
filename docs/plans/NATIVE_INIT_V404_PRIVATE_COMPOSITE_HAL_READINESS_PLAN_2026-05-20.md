# Native Init v404 Private-Composite Wi-Fi HAL Readiness Plan

## Goal

Create a non-mutating readiness packet for the next Wi-Fi HAL boundary after V403 proved that `servicemanager` and `hwservicemanager` can run in the helper-owned private runtime.

V404 does not start Wi-Fi HAL, `wificond`, supplicant, hostapd, CNSS/diag, scan/connect/link-up, credentials, DHCP, routing, rfkill, firmware mutation, Android partition writes, or persistent daemons.

## Starting Evidence

- V402 private SELinux proof: `docs/reports/NATIVE_INIT_V402_PRIVATE_SELINUX_SURFACE_PROOF_LIVE_2026-05-20.md`
- V403 service-manager start-only live result: `docs/reports/NATIVE_INIT_V403_SERVICE_MANAGER_START_ONLY_RETRY_LIVE_2026-05-20.md`
- V210 vendor asset classifier: `tmp/wifi/v210-vendor-asset-classifier/manifest.json`
- V216 service replay model: `tmp/wifi/v216-service-replay-model/manifest.json`
- V287 Wi-Fi service-order replay model: `tmp/wifi/v287-wifi-service-order-replay-model/manifest.json`
- V403 supplemental old HAL gate refresh: `tmp/wifi/v403-post-service-manager-hal-readiness-refresh-20260520-085835/manifest.json`

V403 proved:

```text
decision: service-manager-start-only-live-pass
system-servicemanager: start-only-pass
system-hwservicemanager: start-only-pass
postflight_clean: True
wifi_bringup_executed: False
```

The V403 supplemental V364 gate still reports old global/current runtime blockers. That is context only. The next stage must use the V403-proven helper-owned private runtime rather than assume global `/mnt/system/vendor` visibility.

## Implementation

Add `scripts/revalidation/wifi_private_composite_hal_readiness_packet.py`.

The packet:

- validates V402, V403, V210, V216, and V287 prerequisite manifests.
- refreshes current native health, process cleanliness, Wi-Fi link cleanliness, helper v22 hash, and core manager binary visibility with read-only commands.
- treats V210 vendor-root classification as the authority for vendor HAL binary, init rc, and VINTF availability.
- records global `/mnt/system/vendor` stat failures as detail, not blockers, because the helper private namespace performs temporary vendor mounting.
- selects `vendor.wifi_hal_ext` as the first HAL candidate and keeps `vendor.wifi_hal_legacy` as sibling fallback.
- emits `composite-helper-needed` as the next action: current helper starts one target per invocation, but HAL start-only needs one helper-owned namespace supervising `servicemanager`, `hwservicemanager`, and one HAL candidate together.

## Validation Plan

Static checks:

```text
python3 -m py_compile scripts/revalidation/wifi_private_composite_hal_readiness_packet.py
git diff --check
```

Packet run:

```text
python3 scripts/revalidation/wifi_private_composite_hal_readiness_packet.py \
  --out-dir tmp/wifi/v404-private-composite-hal-readiness-packet-$(date +%Y%m%d-%H%M%S) \
  run
```

Expected:

```text
decision: v404-private-composite-hal-readiness-packet-ready
pass: True
first_hal_candidate: vendor.wifi_hal_ext
live_execution_approved: False
device_mutations: False
daemon_start_executed: False
wifi_bringup_executed: False
```

Allowed non-pass action:

```text
composite-helper-needed: needed/action
```

This action is not a blocker. It defines V405.

## Next Step

Proceed to V405 only as a separate implementation/approval packet. V405 should build the composite helper or runner contract for one bounded namespace that supervises `servicemanager`, `hwservicemanager`, and the first HAL candidate. Even then, Wi-Fi scan/connect/link-up and credentials remain out of scope.
