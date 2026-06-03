# Native Init V1893 PM Msg22 Pending Client Gate

## Summary

- Cycle: `V1893`
- Type: host-only pm-service source classifier for msg22 pending-client gate
- Decision: `v1893-pm-msg22-pending-client-gate-source-pass`
- Label: `pm-msg22-pending-client-gate`
- Result: PASS
- Reason: pm-service source shows post-ack msg22 indication is gated by a pending QMI client slot; native reaches PM ack/open but the pending-client msg22 edge never fires, so the next proof must come from a normal Android PM msg22/servreg/SSCTL capture
- Evidence: `tmp/wifi/v1893-pm-msg22-pending-client-gate`

## Source Gate

- post-ack pending-client load/null-skip: `True` / `True`
- post-ack msg22 indication/uses-pending-client: `True` / `True`
- msg22 request handler string/helper/error-response: `True` / `True` / `True`
- pending helper stores/rejects-existing/transitions: `True` / `True` / `True`
- restart-indication log strings: `True`

## Native Boundary

- PM register/connect/open: `0` / `0` / `/dev/subsys_modem` fd `0x7`
- post-ack open/msg22 hits: `1` / `0`
- native wlanmdsp/WLFW69/wlan0: `0` / `0` / `0`
- native service-notifier state: `uninit` -> `uninit`

## Classifier Checks

- pm-service binary present: `True`
- source pending-client gate: `True`
- source msg22 request handler: `True`
- native open without pending msg22: `True`
- Android capture handoff ready: `True`

## Selected Diff

- Label: `pm-msg22-pending-client-gate`.
- `/dev/subsys_modem` open is below the PM ack path but above the missing guest-PD load; it does not populate the pm-service pending QMI client slot by itself.
- The source candidate is now narrower: prove whether normal Android creates the msg22 pending-client edge before `wlanmdsp.mbn`, or whether a different servreg/SSCTL request causes the modem-side WLAN-PD load.
- Native still lacks the post-ack msg22 indication, WLFW service 69, `wlanmdsp.mbn`, and `wlan0`.

## Handoff Commands

- Capture command: `python3 scripts/revalidation/native_wifi_android_pm_msgid_log_capture_runner_v1890.py --execute --out-dir tmp/wifi/v1891-normal-android-capture-run`
- Parser command: `python3 scripts/revalidation/native_wifi_pm_msgid_capture_diff_classifier_v1888.py --android-dir tmp/wifi/v1891-normal-android-capture-run/android --out-dir tmp/wifi/v1891-normal-android-capture-diff`

## Safety Scope

- host-only/device-contact: `True` / `False`
- Wi-Fi HAL/scan-connect/credential/DHCP/routes/ping: `False` / `False` / `False` / `False` / `False`
- PMIC-GPIO-GDSC/forced-RC1/subsys-esoc0/eSoC notify/PCI rescan/platform bind: `False` / `False` / `False` / `False` / `False` / `False`

## Next

- Run the normal Android capture only when ADB/root is available; reject degraded 257s captures or any pre-wlan0 PCIe/MHI path.
- Diff for pm-service msg22 pending-client creation, servreg state-up, SSCTL, and first `wlanmdsp.mbn` request.
- Do not attempt Wi-Fi connect or ping until native init proves WLFW service 69 and `wlan0` are both present.
