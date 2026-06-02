# Native Init V1760 WLAN-PD Request-trigger Surface Classifier

## Summary

- Cycle: `V1760`
- Type: host-only request-trigger/served-path classifier
- Decision: `v1760-android-good-serves-wlanmdsp-native-never-requests-host-pass`
- Label: `request-generation-gap-before-firmware-serving`
- Result: PASS
- Reason: Android-good requests wlanmdsp after the WLFW worker and serves it via vendor/firmware fallback; native reaches the same WLFW worker with tftp_server running but never requests wlanmdsp
- Evidence: `tmp/wifi/v1760-wlan-pd-request-trigger-surface-classifier`

## Android-good Timeline

| event | time | delta |
| --- | --- | --- |
| rmt_storage_ready | 15449.309 | -2.071s |
| tftp_server_started | 15449.322 | -2.058s |
| cnss_daemon_started | 15450.592 | -0.788s |
| wlfw_start | 15450.687 | -0.693s |
| per_mgr_register | 15450.688 | -0.692s |
| per_mgr_vote | 15450.688 | -0.692s |
| ro_baseband_mdm | 15450.724 | -0.656s |
| wlfw_service_request | 15450.756 | -0.624s |
| wlanmdsp_request | 15451.380 | +0.000s |
| bdf_regdb | 15451.805 | +0.425s |

## Android Served-path Fallback

- firmware_mnt attempt seen: `True`
- vendor/firmware attempt seen: `True`
- vendor/firmware OACK size seen: `True`
- snapshot has `/vendor/firmware/wlanmdsp.mbn`: `True`
- snapshot has `/vendor/firmware_mnt/image/wlanmdsp.mbn`: `False`

```text
06-03 04:17:31.380  1684  2518 I tftp_server: pid=1684 tid=2518 tftp-server : INF :[tftp_server_utils.c, 113] file [readonly/vendor/firmware_mnt/image/wlanmdsp.mbn] : [/vendor/rfs/msm/mpss/readonly/vendor
06-03 04:17:31.409  1684  2523 I tftp_server: pid=1684 tid=2523 tftp-server : INF :[tftp_server_utils.c, 113] file [readonly/vendor/firmware/wlanmdsp.mbn] : [/vendor/rfs/msm/mpss/readonly/vendor/firmware/
06-03 04:17:31.409  1684  2523 I tftp_server: pid=1684 tid=2523 tftp-server : INF :[tftp_server.c, 1203] OACK options [port: 87] : [7680, 200, 4251884, 10, 0, 0, 0, 0]
```

## Native SM-route Baseline

- Manifest: `tmp/wifi/v1736-wlan-pd-timestamped-observer-handoff/manifest.json`
- Decision/pass: `v1736-wlfw-start-reached-downstream-block-rollback-pass` / `True`
- Order: `servicemanager,hwservicemanager,vndservicemanager,qrtr_ns,pd_mapper,rmt_storage,tftp_server,subsys_modem_holder,cnss_diag,cnss_daemon,service-window-trigger-summary`
- service-manager / tftp running: `1` / `1`
- WLFW start/request/worker hits: `1` / `1` / `1`
- requested `wlanmdsp`: `0`
- WLFW service 69: `0`
- WLAN-PD uninit evidence: `True`

## Interpretation

- Android-good proves the modem-side request happens after `wlfw_service_request` and before WLAN-PD/ICNSS progress.
- Android-good also proves the first `firmware_mnt` lookup can fail and still recover through `/vendor/firmware/wlanmdsp.mbn`; therefore a native fix cannot be scoped as served-path repair while native has no request.
- Native V1736 reaches the WLFW worker and has `tftp_server` running, but `wlanmdsp.mbn` is never requested and WLAN-PD remains `UNINIT`.
- The active blocker is request generation/autoload trigger before firmware serving.  Do not add PM actors, QCACLD, eSoC/RC1, restart-PD, Wi-Fi HAL, scan/connect, DHCP/routes, credentials, or external ping in this unit.

## Next

- V1761 should remain host/source-only first: inspect the modem-side WLAN-PD autoload trigger contract around Android-good `wlfw_service_request -> wlanmdsp request` without adding actors.
- A later live gate is justified only if it observes or repairs a single identified request-trigger condition and still measures `requested_wlanmdsp`, WLFW service 69, and `wlan0` before any connection attempt.

## Safety Scope

This classifier is host-only. It performs no device contact, flash, reboot, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, PMIC/GPIO/GDSC write, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, firmware/partition write, or actor start.
