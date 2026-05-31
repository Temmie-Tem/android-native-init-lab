# Native Init V1336 Android Pre-CNSS Provider Classifier

## Summary

- Cycle: `V1336`
- Type: host-only classifier
- Decision: `v1336-pre-cnss-provider-order-gap`
- Result: PASS
- Evidence:
  - `tmp/wifi/v1336-android-pre-cnss-provider-classifier/manifest.json`
  - `tmp/wifi/v1336-android-pre-cnss-provider-classifier/summary.md`
- Script: `scripts/revalidation/native_wifi_android_pre_cnss_provider_classifier_v1336.py`

V1336 reconciles the Android-positive V1331 timing, the full native V1328
late-`per_proxy` window, and the V1335 observe-only early-CNSS result. It ranks
the missing input as the Android pre-CNSS PM/provider chain rather than another
late eSoC or late `per_proxy` retry.

## Key Evidence

| item | value |
| --- | --- |
| android_pre_cnss_provider_chain | `true` |
| native_observe_only_no_wlfw | `true` |
| native_missing_pre_cnss_provider_chain | `true` |
| late_per_proxy_not_sufficient | `true` |
| ranked_missing_input | `pre-CNSS PM/provider chain` |

Android V1331 starts `pm_proxy_helper`, QRTR/RFS/pd-mapper companions,
`per_mgr`, `per_proxy`, and `cnss_diag` before `cnss-daemon`; `wlfw_start`
then appears before the captured `__subsystem_get(esoc0)` marker. V1335
successfully starts `mdm_helper`, `cnss_diag`, and `cnss-daemon` in observe-only
mode, but omits `pm_proxy_helper` and `per_proxy`, keeps `/dev/subsys_esoc0`
closed, and still sees no WLFW precondition. V1328 confirms that a late
`per_proxy` after CNSS/eSoC observation is not sufficient.

## Android Boottime Order

| property | seconds |
| --- | --- |
| `ro.boottime.vendor.per_proxy_helper` | `5.813594` |
| `ro.boottime.vendor.qrtr-ns` | `6.942195` |
| `ro.boottime.vendor.pd_mapper` | `6.978435` |
| `ro.boottime.vendor.per_mgr` | `6.987725` |
| `ro.boottime.vendor.rmt_storage` | `7.061588` |
| `ro.boottime.vendor.tftp_server` | `7.064970` |
| `ro.boottime.vendor.per_proxy` | `7.848075` |
| `ro.boottime.cnss_diag` | `7.975236` |
| `ro.boottime.vendor.mdm_helper` | `8.218118` |
| `ro.boottime.cnss-daemon` | `8.222635` |

## Decision

The next useful gate is not another direct eSoC trigger, and not another late
`per_proxy` retry. V1337 should add a bounded Android-order pre-CNSS provider
observe-only gate:

1. start the service-manager/provider surface if required,
2. start `pm_proxy_helper`, `pm-service`, `pm-proxy`, and QRTR/RFS/pd-mapper
   companion services before CNSS,
3. then start `mdm_helper`, `cnss_diag`, and `cnss-daemon -n -l`,
4. keep `/dev/subsys_esoc0` closed,
5. continue forbidding Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and
   external ping.

## Safety

Host-only classifier. No device command, helper deploy, actor start, tracefs
write, live eSoC open/ioctl/notify, PMIC/GPIO write, Wi-Fi HAL start,
scan/connect, credential use, DHCP/routes, external ping, flash, boot image
write, or partition write occurred.
