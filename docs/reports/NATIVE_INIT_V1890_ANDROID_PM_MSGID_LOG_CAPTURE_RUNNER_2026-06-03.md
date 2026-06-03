# Native Init V1890 Android PM Msg-id Log Capture Runner

## Summary

- Cycle: `V1890`
- Type: dry-run/read-only Android normal-boot PM msg-id log capture runner
- Decision: `v1890-android-pm-msgid-log-capture-runner-dry-run-pass`
- Label: `android-pm-msgid-log-capture-runner-ready`
- Result: PASS
- Reason: dry-run generated a read-only normal-Android PM msg-id capture runner without contacting the device
- Evidence: `tmp/wifi/v1890-android-pm-msgid-log-capture-runner`

## Runner

- execute mode: `False`
- use su: `True`
- command count: `7`
- generated shell script: `tmp/wifi/v1890-android-pm-msgid-log-capture-runner/host/android-pm-msgid-log-capture.sh`
- parser: `scripts/revalidation/native_wifi_pm_msgid_capture_diff_classifier_v1888.py`
- contract decision/label/pass: `v1887-normal-android-pm-msgid-capture-contract-host-pass` / `normal-android-pm-msgid-capture-contract-ready` / `True`

## Command Targets

- Captures read-only identity props, target processes, init service props, `/proc/net/qrtr`, filtered `dmesg`, filtered `logcat -b all`, and a composed `request-lines.txt`.
- Filters include `PerMgrSrv`, `PerMgrLib`, `QMI service`, `QMI client`, `peripheral restart`, `cnss-daemon`, `service-notifier`, `servloc`, `sysmon-qmi`, `wlanmdsp`, `wlan_pd`, `wlan0`, PCIe/MHI contamination terms, and degraded-boot terms.
- Output names match V1888 parser inputs: `android/logcat-filtered.txt`, `android/dmesg-filtered.txt`, and `android/request-lines.txt`.

## Selected Diff

- Label: `android-pm-msgid-log-capture-runner-ready`.
- Current state still lacks Android ADB, so no live Android capture was attempted.
- The runner is ready to collect a fresh normal Android boot log surface with broader pm-service msg-id visibility than the retained V1753 filtered sample.
- V1888 should be run against the collected `android/` directory; promote only if msg `0x22` appears before `wlanmdsp.mbn` on a normal non-PCIe/MHI boot.

## Safety Scope

V1890 dry-run is host-only. In execute mode it runs only read-only Android ADB shell commands and writes host evidence files. It performs no flash, reboot, property staging, tracefs write, service start, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, PMIC/GPIO/GDSC write, forced RC1/case write, `/dev/subsys_esoc0` open, fake ONLINE state, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, firmware write, boot write, or device partition write.

## Next

- Use execute mode only after booting normal Android with ADB/root available; reject degraded 257s or pre-wlan0 PCIe/MHI captures.
- Keep native init at v724/selftest fail=0 until a bounded rollbackable internal-modem gate is justified.
- Do not attempt Wi-Fi connect or ping until native init proves WLFW service 69 and `wlan0` are both present.
