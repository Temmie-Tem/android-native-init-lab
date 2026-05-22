# Native Init V621 MDM Helper Contract Classifier Plan

- date: `2026-05-23 KST`
- cycle: `v621`
- scope: host-only classifier
- target: classify whether Android's `vendor.mdm_helper`/`vendor.mdm_launcher`
  contract is the next safe gate for the native modem/QMI publication gap

## Background

V620 refined the `sysmon_esoc0` hypothesis. Android publishes
`service-notifier 180/74` before `sysmon_esoc0`, so missing native
`sysmon_esoc0` is a later state delta rather than a proven first-notifier
precondition.

V619 also showed that repeating direct ADSP/CDSP/SLPI boot-node writes is not
acceptable: the Android-order companion replay did not publish
`service-notifier`, and it reproduced `pm_qos` kernel warnings.

The remaining host-only question is whether Android reaches the missing lower
QMI publication state through `vendor.mdm_helper`, its `vendor.mdm_launcher`
wrapper, or another init property/ioctl path before CNSS/HAL.

## Guardrails

V621 must not:

- contact the device;
- write sysfs, `boot_wlan`, `qcwlanstate`, or DSP boot nodes;
- start `mdm_helper`, companion daemons, CNSS, service-manager, Wi-Fi HAL,
  `wificond`, supplicant, or hostapd;
- scan/connect/link-up, use credentials, run DHCP, change routes, or ping
  externally.

## Inputs

- V620 refined classifier:
  `tmp/wifi/v620-dsp-mdm3-safety-classifier-refined/manifest.json`
- V614 vendor init snapshot:
  `tmp/wifi/v614-mdm3-trigger-path-classifier/native/vendor-init-readonly-snapshot.txt`
- Android V611 lower-surface dmesg/timing manifest:
  `tmp/wifi/v612-android-lower-surface-handoff-20260523-011739/v611-android-lower-surface-recapture-run/manifest.json`
- Android V431 property evidence:
  `tmp/wifi/v431-android-runtime-gap-handoff-live-su-quote-20260520-152315/v431-android-runtime-gap-run/commands/wifi-props-filtered.txt`
- Android V297 fallback property evidence:
  `tmp/wifi/v297-android-property-capture-android/commands/wifi-property-filter.txt`

External Qualcomm/postmarketOS references remain supporting context only:
SDM845 work documents `rmtfs`, `pd-mapper`, and `tqftpserv` as QRTR/firmware
companions, but it does not provide a Samsung vendor-kernel `mdm_helper`
contract for this device.

## Checks

1. Parse the V614 vendor init snapshot for:
   - `service vendor.mdm_helper /vendor/bin/mdm_helper`
   - `service vendor.mdm_launcher /vendor/bin/sh /vendor/bin/init.mdm.sh`
   - `init.mdm.sh` `ro.baseband` gate
   - `start vendor.mdm_helper`
   - `start wcnss-service`
2. Compare Android properties for:
   - `ro.baseband` / `ro.boot.baseband`
   - `init.svc.vendor.mdm_helper`
   - `init.svc.vendor.mdm_launcher`
   - `persist.vendor.mdm_helper.fail_action`
   - `ro.boottime.vendor.mdm_launcher`
   - `ro.boottime.vendor.mdm_helper`
3. Detect whether the property evidence and service-notifier dmesg are from the
   same Android boot.
4. Classify `vendor.mdm_helper`, `vendor.mdm_launcher`, and `wcnss-service` as
   live candidates or non-candidates.
5. Produce a next gate only if it avoids direct DSP boot-node writes and avoids
   CNSS/HAL/scan/connect.

## Success Criteria

V621 passes if it selects one of these outcomes using existing evidence:

- `v621-mdm-helper-contract-same-boot-recapture-required`
- `v621-mdm-helper-start-only-ready`
- `v621-mdm-helper-not-causal`
- `v621-mdm-helper-contract-evidence-gap`

Passing V621 does not authorize Wi-Fi bring-up. If timing remains cross-boot,
the next action is Android same-boot read-only recapture, not native live
daemon start.
