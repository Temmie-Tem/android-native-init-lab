# Native Init V1062 PM Contract Gap Classifier Plan

Date: `2026-05-27`

## Goal

Classify the V1061 PM full-contract gap without another live retry.

V1061 proved global firmware visibility and the helper modem pre-holder are now
fixed, but `pm-service`/`per_mgr` did not hold `/dev/subsys_modem`.  It also
produced an eSoC reference-count warning during cleanup.  V1062 compares V1024
Android-positive PM fd evidence with V1061 native evidence to select the next
safe gate.

## Method

1. Read V1024 Android PM fd contract manifest.
2. Read V1061 live manifest, helper transcript, and dmesg delta.
3. Compare:
   - Android `pm_proxy_helper`, `pm-service`, and `mdm_helper` fd evidence;
   - native V1061 `pm_proxy_helper`, `per_mgr`, `pm-proxy`, and `mdm_helper` fd evidence;
   - V1061 property-service shim and binder/vndbinder surface;
   - V1061 eSoC reference-count warning.
4. Emit a host-only route decision.

## Hard Gates

- Host-only; no device commands.
- No live retry, daemon start, service-manager start, Wi-Fi HAL start, scan/connect, credentials, DHCP/routes, external ping, eSoC open/ioctl, sysfs/debugfs write, boot image write, partition write, firmware mutation, or Android handoff.

## Validation

```bash
python3 -m py_compile scripts/revalidation/native_wifi_pm_contract_gap_classifier_v1062.py
python3 scripts/revalidation/native_wifi_pm_contract_gap_classifier_v1062.py run
```
