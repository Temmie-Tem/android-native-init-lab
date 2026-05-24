# Native Init V789 V788 Warning Classifier Plan

## Goal

Classify the V788 `pm_qos_add_request` warning without touching the device.

## Scope

- Read only existing evidence:
  - V788 manifest and dmesg delta;
  - V733 lower-only historical manifest;
  - V735 CNSS-only historical manifest;
  - V787 clean-DSP arm-only manifest.
- Compare warning, service-notifier, sysmon, WLFW, and `wlan0` markers.
- Extract the first warning context from V788 dmesg.
- Select the narrowest safe next live gate.

## Hard Gates

- No device command.
- No reboot.
- No mount/unmount.
- No daemon start.
- No Wi-Fi HAL, scan/connect, credential use, DHCP/routes, or external ping.
- No boot image or partition write.
- No custom kernel flash.

## Validation

```bash
python3 -m py_compile scripts/revalidation/native_wifi_v788_warning_classifier_v789.py
python3 scripts/revalidation/native_wifi_v788_warning_classifier_v789.py plan
python3 scripts/revalidation/native_wifi_v788_warning_classifier_v789.py run
```

## Expected Routing

If V788 is the only run with the `pm_qos` warning, the next live gate should be
narrower than V788. The preferred candidate is a clean-DSP lower-only readback:
repeat the clean-DSP plus current V401/V490 prep path, but omit
`cnss_diag`/`cnss-daemon`, HAL, scan/connect, credentials, DHCP/routes, and
external ping.
