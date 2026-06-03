# Native Init V1891 Android Capture Parser Handoff

## Summary

- Cycle: `V1891`
- Type: host-only handoff gate from normal-Android PM msg-id capture runner to parser
- Decision: `v1891-android-capture-parser-handoff-host-pass`
- Label: `android-capture-parser-handoff-ready`
- Result: PASS
- Reason: V1890 runner outputs satisfy the V1888 parser input contract; future normal-Android capture and parser commands are fixed
- Evidence: `tmp/wifi/v1891-android-capture-parser-handoff`

## Inputs

- V1887 contract: `tmp/wifi/v1887-normal-android-pm-msgid-capture-contract/manifest.json`
- V1888 parser baseline: `tmp/wifi/v1888-pm-msgid-capture-diff-classifier/manifest.json`
- V1890 runner manifest: `tmp/wifi/v1890-android-pm-msgid-log-capture-runner/manifest.json`
- V1890 generated shell: `tmp/wifi/v1890-android-pm-msgid-log-capture-runner/host/android-pm-msgid-log-capture.sh`
- V1890 command manifest: `tmp/wifi/v1890-android-pm-msgid-log-capture-runner/host/android-pm-msgid-log-capture-commands.json`
- Parser script: `scripts/revalidation/native_wifi_pm_msgid_capture_diff_classifier_v1888.py`

## Handoff Checks

- contract/diff/runner ready: `True` / `True` / `True`
- shell/runner/parser present: `True` / `True` / `True`
- required parser inputs declared: `True`
- expected outputs declared: `True`
- forbidden command surface absent: `True`
- required parser inputs: `["android/logcat-filtered.txt", "android/dmesg-filtered.txt", "android/request-lines.txt"]`
- missing required/expected outputs: `[]` / `[]`

## Future Handoff

- Capture output dir: `tmp/wifi/v1891-normal-android-capture-run`
- Diff output dir: `tmp/wifi/v1891-normal-android-capture-diff`
- Capture command: `python3 scripts/revalidation/native_wifi_android_pm_msgid_log_capture_runner_v1890.py --execute --out-dir tmp/wifi/v1891-normal-android-capture-run`
- Parser command: `python3 scripts/revalidation/native_wifi_pm_msgid_capture_diff_classifier_v1888.py --android-dir tmp/wifi/v1891-normal-android-capture-run/android --out-dir tmp/wifi/v1891-normal-android-capture-diff`

## Selected Diff

- Label: `android-capture-parser-handoff-ready`.
- The unresolved comparison remains internal-modem PM post-vote to WLAN guest-PD load, not SDX50M/eSoC/PCIe/GDSC.
- V1890 declares the exact Android files consumed by V1888: `logcat-filtered.txt`, `dmesg-filtered.txt`, and `request-lines.txt` under the captured `android/` directory.
- The next useful live evidence is a normal Android ADB/root capture across per_mgr vote to first `wlanmdsp.mbn`, then immediate V1888 parsing of that captured `android/` directory.

## Safety Scope

- host-only/device-contact/live-capture: `True` / `False` / `False`
- Wi-Fi HAL/scan-connect/credential/DHCP/routes/ping: `False` / `False` / `False` / `False` / `False`
- PMIC-GPIO-GDSC/forced-RC1/subsys-esoc0/eSoC notify/PCI rescan/platform bind: `False` / `False` / `False` / `False` / `False` / `False`

## Next

- Run the capture command only on a normal Android boot with ADB/root available; reject degraded 257s captures or any pre-wlan0 PCIe/MHI path.
- Promote only if V1888 sees Android msg `0x22` before `wlanmdsp.mbn` while native post-open still lacks msg22/WLFW69/wlanmdsp/wlan0.
- Do not attempt Wi-Fi connect or ping until native init proves WLFW service 69 and `wlan0` are both present.
