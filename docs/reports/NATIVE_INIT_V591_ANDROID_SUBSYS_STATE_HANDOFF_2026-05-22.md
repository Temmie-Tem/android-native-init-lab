# Native Init V591 Android Subsystem State Handoff

- date: `2026-05-22 KST`
- objective: temporarily boot Android, collect the V590 read-only modem/esoc subsystem state sample, and restore native init
- status: `pass`; Wi-Fi external ping is **not** complete

## Scope

- Handoff runner: `scripts/revalidation/android_subsys_state_sample_handoff_v591.py`
- Handoff evidence: `tmp/wifi/v591-android-subsys-state-sample-handoff/`
- Inner V590 evidence: `tmp/wifi/v591-android-subsys-state-sample-handoff/v590-android-subsys-state-sample-run/`
- Android state sample: `tmp/wifi/v591-android-subsys-state-sample-handoff/v590-android-subsys-state-sample-run/android-subsys-state.txt`
- Follow-up V589 evidence: `tmp/wifi/v589-android-subsys-state-gap/`

## Guardrails

- Android boot was temporary and rollback returned to native init v319.
- No Wi-Fi enable command.
- No Wi-Fi HAL start.
- No daemon start.
- No subsystem sysfs write.
- No qcwlanstate/sysfs driver-state write.
- No scan/connect/link-up/DHCP/routing.
- No external ping.
- No credential use or credential-bearing evidence.

## Live Result

```text
decision: v590-android-subsys-nonoffline-captured
pass: True
reason: Android read-only sample captured non-offline modem/esoc state: mss=ONLINE mdm3=ONLINE
device_commands_executed: True
device_mutations: True
daemon_start_executed: False
wifi_bringup_executed: False
external_ping_executed: False
```

## Captured Android State

```text
mss_state=ONLINE
mdm3_state=ONLINE
state_values_ready=True
non_offline_state=True
has_qrtr_readiness=True
has_sysmon_qmi=True
has_service_notifier=True
has_wlan_pd=True
```

## Handoff Steps

| step | status | duration |
| --- | --- | --- |
| native-version | ok | 0.434s |
| native-status | ok | 0.466s |
| native-recovery | ok | 0.101s |
| wait-recovery | ok | 27.130s |
| push-android-boot | ok | 0.671s |
| remote-android-sha | ok | 0.102s |
| flash-android-boot | ok | 0.465s |
| readback-android-boot | ok | 0.386s |
| reboot-android | ok | 0.755s |
| wait-android | ok | 34.164s |
| wait-boot-complete | ok | 3.347s |
| settle-after-boot-complete | ok | 20.194s |
| v590-android-subsys-state-sample | ok | 6.645s |
| reboot-recovery-for-rollback | ok | 3.411s |
| wait-rollback-recovery | ok | 30.136s |
| restore-native | ok | 35.753s |

## Rollback Verification

After the handoff, native init responded as:

```text
A90 Linux init 0.9.61 (v319)
version: 0.9.61 build=v319
```

Native status after rollback:

```text
boot: BOOT OK shell 4.1s
exposure: guard=ok warn=0 fail=0 ncm=absent tcpctl=stopped rshell=stopped boundary=usb-local
storage: sd present=yes mounted=yes expected=yes rw=yes
```

## V589 Follow-up

The V591 Android sample was fed back into V589:

```text
decision: v589-android-native-subsys-state-delta-confirmed
pass: True
reason: native V588 window is OFFLINING while Android state sample has non-offline states: {'mdm3': 'ONLINE', 'mss': 'ONLINE'}
next: plan the smallest safe subsystem-readiness trigger; keep HAL/scan/connect blocked until lower markers change
device_commands_executed: False
device_mutations: False
wifi_bringup_executed: False
```

## Conclusion

V591 closes the V589 evidence gap: Android reaches `ONLINE` for both modem/esoc subsystem surfaces, while the prior native V588 companion window remained `OFFLINING`. The next gate should not jump to Wi-Fi scan/connect yet. It should identify the smallest safe native readiness trigger that moves the lower modem/esoc/QRTR path toward Android-equivalent readiness while keeping HAL, scan/connect, credentials, routing, and external ping blocked.
