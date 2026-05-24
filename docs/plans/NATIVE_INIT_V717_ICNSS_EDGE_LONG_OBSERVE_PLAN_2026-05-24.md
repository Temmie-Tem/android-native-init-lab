# Native Init V717 ICNSS Edge Long-Observe Plan

- date: `2026-05-24 KST`
- cycle: `V717`
- gate: bounded live long-observe
- runner: `scripts/revalidation/native_wifi_provider_first_icnss_edge_orchestrator_v712.py`

## Objective

Remove a timing-window ambiguity from the V714/V716 result. Android reference
shows service `74` to WLFW start in roughly `1.409s`; V714 used the default
helper observation window. V717 reruns the same V712 helper v121 provider-first
ICNSS edge proof with an explicit `30s` companion runtime window.

## Scope

Allowed:

- V641 clean-DSP reboot prep;
- V401 SELinuxfs mount surface;
- V490 SELinux policy-load proof;
- bounded helper v121 provider-first ICNSS edge proof;
- `30s` companion observe window;
- runner-owned cleanup and reboot;
- host-only V715/V716 reclassification of the new evidence.

Forbidden:

- QCA6390 `bind`, `unbind`, or `driver_override` writes;
- Wi-Fi HAL, `wificond`, supplicant, or hostapd start;
- scan/connect/link-up, credentials, DHCP, route changes, or external ping;
- boot image or partition writes.

## Expected Result

If WLFW/BDF/fw-ready/`wlan0` still stay at `0` after `30s`, the blocker is not
a short observation-window issue. The next target remains ICNSS-QMI/WLFW
readiness trigger analysis.

## Validation

```bash
python3 scripts/revalidation/native_wifi_provider_first_icnss_edge_orchestrator_v712.py \
  --out-dir tmp/wifi/v717-provider-first-icnss-edge-long-observe-<timestamp> \
  --arm-companion-runtime-sec 30 \
  --apply --assume-yes \
  run

python3 scripts/revalidation/native_wifi_icnss_edge_surface_classifier_v715.py \
  --source tmp/wifi/latest-v717-icnss-edge-long-observe.txt \
  --out-dir tmp/wifi/v717-icnss-edge-surface-classifier \
  run

python3 scripts/revalidation/native_wifi_qca_bind_reconciliation_v716.py \
  --v715-source tmp/wifi/latest-v717-icnss-edge-surface-classifier.txt \
  --out-dir tmp/wifi/v717-qca-bind-reconciliation \
  run
```
