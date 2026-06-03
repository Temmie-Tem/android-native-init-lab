# Native Init V1888 PM Msg-id Capture Diff Classifier

## Summary

- Cycle: `V1888`
- Type: host-only parser/classifier for normal-Android PM msg-id capture versus native post-open evidence
- Decision: `v1888-android-stateup-msg22-observability-gap-host-pass`
- Label: `android-stateup-without-msg22-log-observability-gap`
- Result: PASS
- Reason: Android normal state-up is present but retained capture has zero pm-service msg22 observability; native post-open still lacks msg22/WLFW/wlanmdsp
- Evidence: `tmp/wifi/v1888-pm-msgid-capture-diff-classifier-v1909`

## Android Capture Parse

- Evidence dir: `tmp/wifi/v1909-android-servloc-domain-handoff-live-20260603-213346/android-postfs-evidence/a90-v1909-servloc-domain`
- logcat/dmesg/request lines: `1675` / `118` / `0`
- PM register/vote count/time: `2` / `2` / `21:35:56.689`
- WLFW request count/time: `1` / `21:35:56.718`
- wlan_pd indication/ack/time: `2` / `1` / `9.558609`
- wlanmdsp count/time: `10` / `21:35:57.365`
- wlan0 time and contamination counts: `14.904181` / PCIe-MHI `0` / esoc-boot-failed `0` / degraded257 `False`
- pm msg20/msg21/msg22 hits: `0` / `0` / `0`
- first msg22 line: ``
- first wlan_pd line: `[    9.558609]  [5:  kworker/u16:1:   75] service-notifier: root_service_service_ind_cb: Indication received from msm/modem/wlan_pd, state: 0x1fffffff, trans-id: 1`
- first wlanmdsp line: `06-03 21:35:57.365   968  1454 I tftp_server: pid=968 tid=1454 tftp-server : INF :[tftp_server_utils.c, 113] file [readonly/vendor/firmware_mnt/image/wlanmdsp.mbn] : [/vendor/rfs/msm/mpss/readonly/vendor`

## Native Post-open Parse

- Manifest decision/label/pass: `v1885-internal-pm-qmi-servreg-trigger-source-diff-host-pass` / `pm-msg22-servreg-trigger-trace-gap` / `True`
- PM register/connect/open: `0` / `0` / `/dev/subsys_modem` fd `0x7` state `0x2`
- post-ack open/msg22 hits: `1` / `0`
- WLFW request/ind-register/cap hits: `1` / `0` / `0`
- wlanmdsp/WLFW69/wlan0/states: `0` / `0` / `0` / `uninit` -> `uninit`

## Contract

- Contract decision/label/pass: `v1887-normal-android-pm-msgid-capture-contract-host-pass` / `normal-android-pm-msgid-capture-contract-ready` / `True`
- Fixed labels: `["android-msg22-stateup-observed-native-absent", "android-stateup-without-msg22-log-observability-gap", "android-normal-capture-contaminated", "native-post-open-msg22-still-absent", "capture-incomplete"]`

## Selected Diff

- Label: `android-stateup-without-msg22-log-observability-gap`.
- The retained normal Android sample proves PM vote, WLAN-PD state indication, `wlanmdsp.mbn`, and `wlan0` with zero PCIe/MHI contamination.
- The same retained sample has zero pm-service msg22 observability, so it cannot prove or disprove msg22 as the Android trigger.
- Native post-open still proves the missing edge: `/dev/subsys_modem` open succeeds, but msg22 indication, WLFW service 69, `wlanmdsp.mbn`, and `wlan0` stay absent.

## Safety Scope

V1888 is host-only. It parses retained files/manifests and writes local classifier artifacts only. It performs no device command, flash, reboot, property staging, tracefs write, service start, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, PMIC/GPIO/GDSC write, forced RC1/case write, `/dev/subsys_esoc0` open, fake ONLINE state, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, firmware write, boot write, or device partition write.

## Next

- Feed this parser a fresh normal-Android capture with pm-service msg-id visibility; the expected stronger label is `android-msg22-stateup-observed-native-absent` if msg22 appears before `wlanmdsp.mbn`.
- Reject degraded 257s boots or any capture with PCIe/MHI before `wlan0`.
- Do not attempt Wi-Fi connect or ping until native init proves WLFW service 69 and `wlan0` are both present.
