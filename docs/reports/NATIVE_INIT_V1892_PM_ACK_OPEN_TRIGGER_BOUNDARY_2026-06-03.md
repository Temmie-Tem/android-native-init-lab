# Native Init V1892 PM Ack/Open Trigger Boundary

## Summary

- Cycle: `V1892`
- Type: host-only classifier for PM callback/ack and `/dev/subsys_modem` open versus WLAN guest-PD trigger
- Decision: `v1892-pm-ack-open-not-guest-pd-trigger-host-pass`
- Label: `pm-ack-open-not-guest-pd-trigger`
- Result: PASS
- Reason: PM callback/ack and /dev/subsys_modem open are both proven on native, but neither produces msg22 indication, wlan_pd state-up, WLFW service 69, wlanmdsp, or wlan0; the remaining discriminator is the normal-Android post-vote msg22/servreg/SSCTL transition
- Evidence: `tmp/wifi/v1892-pm-ack-open-trigger-boundary`

## Boundary Checks

- callback ack present/not-trigger: `True` / `True`
- modem open present/not-trigger: `True` / `True`
- msg22 source candidate: `True`
- servloc discovery not-trigger: `True`
- Android normal state-up/msgid gap: `True` / `True`
- capture handoff ready: `True`

## Native Proven Boundary

- PM callback/ack label/hits: `callback-ack-present-no-powerup` / `28`
- PM register/connect rc: `0` / `0`
- open path/fd/state: `/dev/subsys_modem` / `0x7` / `0x2`
- post-ack open/msg22 hits: `1` / `0`
- native WLFW ind/cap/wlanmdsp/WLFW69/wlan0: `0` / `0` / `0` / `0` / `0`
- native service-notifier state: `uninit` -> `uninit`

## Servloc And Android

- servloc domain/name/instance: `1` / `msm/modem/wlan_pd` / `180`
- servloc state/indication: `uninit` -> `uninit` / `0` -> `0`
- Android PM vote/WLFW request/wlan_pd/wlanmdsp/wlan0: `2` / `1` / `2` / `10` / `15.242158`
- Android contamination counts: PCIe-MHI `0` / esoc-boot-failed `0` / degraded257 `False`
- retained Android msg22 hits: `0`

## Selected Diff

- Label: `pm-ack-open-not-guest-pd-trigger`.
- The native PM callback/transact/ack path and `/dev/subsys_modem` open are sufficient to prove PM plumbing, but insufficient to start `msm/modem/wlan_pd`.
- Service-locator discovery is also insufficient: the `msm/modem/wlan_pd` domain is resolvable while the service-notifier state stays `uninit`.
- The remaining trigger evidence must come from a normal Android post-vote PM msg-id/servreg/SSCTL capture, then V1888 parsing against native post-open absence.

## Handoff Commands

- Capture command: `python3 scripts/revalidation/native_wifi_android_pm_msgid_log_capture_runner_v1890.py --execute --out-dir tmp/wifi/v1891-normal-android-capture-run`
- Parser command: `python3 scripts/revalidation/native_wifi_pm_msgid_capture_diff_classifier_v1888.py --android-dir tmp/wifi/v1891-normal-android-capture-run/android --out-dir tmp/wifi/v1891-normal-android-capture-diff`

## Safety Scope

- host-only/device-contact: `True` / `False`
- Wi-Fi HAL/scan-connect/credential/DHCP/routes/ping: `False` / `False` / `False` / `False` / `False`
- PMIC-GPIO-GDSC/forced-RC1/subsys-esoc0/eSoC notify/PCI rescan/platform bind: `False` / `False` / `False` / `False` / `False` / `False`

## Next

- Run the capture command only on normal Android with ADB/root available; reject degraded 257s captures and any pre-wlan0 PCIe/MHI path.
- Do not replay native msg22, force subsystem state, or touch eSoC/PCIe/GDSC; first prove the Android post-vote request that precedes `wlanmdsp.mbn`.
- Do not attempt Wi-Fi connect or ping until native init proves WLFW service 69 and `wlan0` are both present.
