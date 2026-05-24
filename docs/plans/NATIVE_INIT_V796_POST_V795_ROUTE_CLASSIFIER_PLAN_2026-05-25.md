# Native Init V796 Post-V795 Route Classifier Plan

## Goal

Reconcile V795 with the latest CNSS, BPF, memshare, and mdm_helper evidence to
select the next smallest gate toward native Wi-Fi readiness.

## Scope

- Host-only classifier.
- Read V795, V792, V782, V785, V764, and V768 manifests.
- Read V777/V781 reports to confirm PIL tracepoint payload fields and stock
  kernel attach feasibility.
- Decide whether to repeat an existing trigger, return to custom-kernel
  instrumentation, or capture missing PIL payload details.

## Hard Gates

- No device command.
- No trace control write, mount, reboot, daemon start, service-manager, Wi-Fi
  HAL, `boot_wlan`, scan/connect, credentials, DHCP/routes, or external ping.
- No raw `esoc0`, module bind/unbind, boot image write, partition write, or
  custom kernel flash.
- No Wi-Fi secret material in tracked output.

## Validation

```bash
python3 -m py_compile scripts/revalidation/native_wifi_post_v795_route_classifier_v796.py
python3 scripts/revalidation/native_wifi_post_v795_route_classifier_v796.py --out-dir tmp/wifi/v796-static-plan-check plan
python3 scripts/revalidation/native_wifi_post_v795_route_classifier_v796.py run
git diff --check
```

## Expected Routing

- If input evidence is missing, block and restore the exact prior manifests.
- If V782 counted PIL events but did not capture `event_name`, `code`, and
  `fw_name`, select a payload-capture gate.
- Do not widen to HAL, scan/connect, DHCP, external ping, custom kernel, or raw
  `esoc0` until the mdm3/WLFW publication gap is sharper.
