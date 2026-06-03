# Native Init V1896 Normal Android Trigger Capture Chain

## Summary

- Cycle: `V1896`
- Type: host-only chain gate for normal-Android trigger capture parsing
- Decision: `v1896-normal-android-trigger-capture-chain-host-pass`
- Label: `normal-android-trigger-capture-chain-ready`
- Result: PASS
- Reason: fresh normal-Android capture handoff is ready for V1894 pending-client parsing and V1888 msg-id diffing
- Evidence: `tmp/wifi/v1896-normal-android-trigger-capture-chain`

## Chain Checks

- V1890/V1894/V1888 ready: `True` / `True` / `True`
- V1895 QMI-client filter ready: `True`
- scripts present: `True`
- required outputs/filter terms: `True` / `True`
- forbidden command surface absent: `True`
- required Android outputs: `["android/logcat-filtered.txt", "android/dmesg-filtered.txt", "android/request-lines.txt"]`
- required filter terms: `["PerMgrSrv", "QMI client", "QMI service", "peripheral restart", "wlanmdsp", "wlan_pd", "wlfw_service_request"]`

## Future Chain

- Capture output dir: `tmp/wifi/v1896-normal-android-trigger-capture`
- Pending-client diff dir: `tmp/wifi/v1896-normal-android-pending-client-diff`
- Msg-id diff dir: `tmp/wifi/v1896-normal-android-msgid-diff`
- Capture command: `python3 scripts/revalidation/native_wifi_android_pm_msgid_log_capture_runner_v1890.py --execute --out-dir tmp/wifi/v1896-normal-android-trigger-capture`
- Pending-client parser: `python3 scripts/revalidation/native_wifi_android_pending_client_msg22_parser_v1894.py --android-dir tmp/wifi/v1896-normal-android-trigger-capture/android --out-dir tmp/wifi/v1896-normal-android-pending-client-diff`
- Msg-id parser: `python3 scripts/revalidation/native_wifi_pm_msgid_capture_diff_classifier_v1888.py --android-dir tmp/wifi/v1896-normal-android-trigger-capture/android --out-dir tmp/wifi/v1896-normal-android-msgid-diff`

## Selected Diff

- Label: `normal-android-trigger-capture-chain-ready`.
- The next useful live evidence is a normal Android ADB/root capture across PM vote to first `wlanmdsp.mbn`.
- V1894 now tests the narrowed V1893 pending-client/msg22 edge; V1888 tests the broader pm-service msg-id/servreg transition.
- A capture promotes only if pending-client/msg22, servreg, or SSCTL evidence appears before `wlanmdsp.mbn` on a normal non-PCIe/MHI boot.

## Safety Scope

- host-only/device-contact/live-capture: `True` / `False` / `False`
- Wi-Fi HAL/scan-connect/credential/DHCP/routes/ping: `False` / `False` / `False` / `False` / `False`
- PMIC-GPIO-GDSC/forced-RC1/subsys-esoc0/eSoC notify/PCI rescan/platform bind: `False` / `False` / `False` / `False` / `False` / `False`

## Next

- Run the capture command only on normal Android with ADB/root available; reject degraded 257s captures and any pre-wlan0 PCIe/MHI path.
- Parse the captured `android/` directory with both listed parsers before any native trigger replay.
- Do not attempt Wi-Fi connect or ping until native init proves WLFW service 69 and `wlan0` are both present.
