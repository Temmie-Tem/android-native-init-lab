# Native Init V590 Android Subsystem State Sample

- date: `2026-05-22 KST`
- objective: collect Android read-only modem/esoc subsystem state values needed after V589
- status: `implemented/currently adb-unavailable`; Wi-Fi external ping is **not** complete

## Scope

- Runner: `scripts/revalidation/native_wifi_android_subsys_state_sample_v590.py`
- Evidence: `tmp/wifi/v590-android-subsys-state-sample/`
- Plan: `docs/plans/NATIVE_INIT_V590_ANDROID_SUBSYS_STATE_SAMPLE_PLAN_2026-05-22.md`
- Normalized output when Android is available: `tmp/wifi/v590-android-subsys-state-sample/android-subsys-state.txt`

## Guardrails

- Android ADB only; no native daemon replay.
- No boot image flash from this collector.
- No reboot or recovery handoff from this collector.
- No daemon start.
- No subsystem sysfs write.
- No qcwlanstate/sysfs driver-state write.
- No Wi-Fi enable command.
- No Wi-Fi HAL start.
- No supplicant/hostapd/wificond start.
- No scan/connect/link-up/DHCP/routing.
- No external ping.
- No credential use or credential-bearing evidence.

## V590 Current Result

Current device state is native init, so Android ADB is not visible:

```text
decision: v590-android-adb-unavailable
pass: True
reason: no Android ADB device is currently visible
next: boot Android or run approved Android handoff before V590 run
device_commands_executed: False
device_mutations: False
daemon_start_executed: False
wifi_bringup_executed: False
```

ADB inventory:

```text
List of devices attached
```

No subsystem values were collected in the current native state.

## Collector Contract

When Android ADB is available, the collector captures only read-only evidence:

```text
sys.boot_completed
init.svc.vendor.qrtr-ns
init.svc.cnss-daemon
init.svc.cnss_diag
/sys/devices/platform/soc/4080000.qcom,mss/subsys0/{uevent,name,state,restart_level,firmware_name,crash_count}
/sys/devices/platform/soc/soc:qcom,mdm3/subsys9/{uevent,name,state,restart_level,firmware_name,crash_count}
/sys/bus/rpmsg/drivers_autoprobe
/sys/bus/rpmsg/devices
/proc/net/qrtr
readiness dmesg tail
```

The command contract intentionally excludes:

```text
svc wifi enable
qcwlanstate
IWifi.start
wpa_supplicant
hostapd
wificond
scan/connect
DHCP/routing
external ping
credentials
```

## Validation

```bash
python3 -m py_compile scripts/revalidation/native_wifi_android_subsys_state_sample_v590.py
git diff --check
python3 scripts/revalidation/native_wifi_android_subsys_state_sample_v590.py plan
python3 scripts/revalidation/native_wifi_android_subsys_state_sample_v590.py preflight
python3 scripts/revalidation/native_wifi_android_subsys_state_sample_v590.py run
```

Tracked diff secret scan for the target network strings returned no hits.

## Next Gate

1. Boot Android or run the existing approved Android handoff path.
2. Run:

```bash
python3 scripts/revalidation/native_wifi_android_subsys_state_sample_v590.py run
```

3. If V590 captures `android-subsys-state.txt`, rerun V589 with that sample:

```bash
python3 scripts/revalidation/native_wifi_android_subsys_state_gap_v589.py \
  --android-state-sample tmp/wifi/v590-android-subsys-state-sample/android-subsys-state.txt \
  run
```

4. Only plan native subsystem readiness triggers if Android proves a non-offline state delta before the Wi-Fi HAL/scan/connect gate.
