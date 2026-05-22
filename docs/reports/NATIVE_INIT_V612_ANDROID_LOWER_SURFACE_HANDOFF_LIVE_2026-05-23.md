# Native Init V612 Android Lower-Surface Handoff Live Report

- date: `2026-05-23 KST`
- status: `pass`; Wi-Fi external ping is **not** complete
- handoff evidence: `tmp/wifi/v612-android-lower-surface-handoff-20260523-011739/`
- V611 evidence:
  `tmp/wifi/v612-android-lower-surface-handoff-20260523-011739/v611-android-lower-surface-recapture-run/`
- wrapper: `scripts/revalidation/android_lower_surface_recapture_handoff_v612.py`
- collector: `scripts/revalidation/native_wifi_android_lower_surface_recapture_v611.py`

## Scope

V612 temporarily booted Android, waited for `sys.boot_completed=1`, ran the V611
read-only lower-surface collector, rebooted recovery, and restored native init.

It did not enable Wi-Fi from the test, start native daemons, start native
service-manager, start native Wi-Fi HAL, write subsystem sysfs, write
`qcwlanstate`, send QMI payloads, scan/connect/link-up, use credentials, run
DHCP, change routes, ping externally, or leave Android boot installed.

## Result

```text
decision: v611-ready-for-native-targeted-trigger
pass: True
reason: Android lower-surface recapture contains sibling sysmon and service-notifier publication evidence
device_commands_executed: True
device_mutations: True
daemon_start_executed: False
wifi_bringup_executed: False
external_ping_executed: False
```

## Handoff Steps

| step | status | duration |
| --- | --- | --- |
| native-version | ok | 0.435s |
| native-status | ok | 0.466s |
| hide-menu | ok | 0.002s |
| native-recovery | ok | 0.101s |
| wait-recovery | ok | 15.074s |
| push-android-boot | ok | 0.660s |
| remote-android-sha | ok | 0.109s |
| flash-android-boot | ok | 0.474s |
| readback-android-boot | ok | 0.244s |
| reboot-android | ok | 0.216s |
| wait-android | ok | 34.163s |
| wait-boot-complete | ok | 3.374s |
| settle-after-boot-complete | ok | 20.210s |
| v611-android-lower-surface-recapture | ok | 7.500s |
| wait-android-before-rollback | ok | 0.005s |
| reboot-recovery-for-rollback | ok | 3.228s |
| wait-rollback-recovery | ok | 30.151s |
| restore-native | ok | 22.594s |

## Rollback Verification

Post-handoff native verification passed:

```text
A90 Linux init 0.9.61 (v319)
boot: BOOT OK shell 4.1s
selftest: pass=11 warn=1 fail=0
exposure: boundary=usb-local
storage: sd present=yes mounted=yes rw=yes
```

## Android Lower-Surface Evidence

V611 captured Android state:

```text
mss_state=ONLINE
mdm3_state=ONLINE
rpmsg_drivers_autoprobe=1
has_qipcrtr_protocol=True
has_proc_net_qrtr=False
has_rpmsg_ipcrtr=True
has_memshare_evidence=True
has_service_locator=True
has_service_notifier_pair=True
has_sibling_sysmon=True
```

Marker counts from the V611 Android capture:

```text
qrtr_rx=1
qrtr_tx=1
sysmon_modem=1
sysmon_slpi=1
sysmon_cdsp=1
sysmon_adsp=1
sysmon_esoc0=1
service_notifier_180=1
service_notifier_74=1
wlan_pd=2
qmi_server_connected=1
bdf_regdb=1
bdf_bdwlan=1
wlan_fw_ready=1
wlan0=3
rmt_storage_ready=1
rmt_storage_open=3
service_locator=1
memshare_request=2
memshare_fail=4
cma_alloc_fail=1
```

Important Android lower-surface ordering:

```text
memshare/cma events appear around sysmon
sysmon-qmi slpi/adsp/cdsp/modem appear together
service locator appears about 38.830ms after modem sysmon
service-notifier 180 appears about 53.927ms after modem sysmon
service-notifier 74 appears about 1.466ms after service-notifier 180
WLAN-PD appears about 2319.436ms after service-notifier 180
```

## Comparison Against Native V609

V610's prior classification is now stronger:

| surface | Android V611 | Native V609 |
| --- | --- | --- |
| `mss` | `ONLINE` | `ONLINE` |
| `mdm3` / `esoc0` | `ONLINE` | `OFFLINING` |
| sibling sysmon | `slpi/cdsp/adsp/esoc0` present | missing |
| service-notifier | `180` and `74` present | missing |
| QIPCRTR protocol | present | present |
| rpmsg IPCRTR | modem/dsps/cdsp/adsp IPCRTR present | modem IPCRTR only captured |
| service locator | present | present |
| memshare/CMA failure | present | present |
| WLFW service `69` readback | Android proceeds to WLAN-PD/BDF | native clean end-of-list |
| `wlan0` | present | missing |

So the remaining native blocker is not basic modem PIL, QIPCRTR protocol
registration, service-locator presence, or rmt_storage reads. The strongest
remaining delta is `mdm3`/`esoc0` and sibling subsystem/sysmon readiness.

## Next Gate

Recommended V613:

1. Build a native targeted observer for `mdm3`/`esoc0` that avoids the unsafe
   raw close path observed in V595.
2. If `esoc0` must be opened, use a no-close holder and reboot cleanup, not a
   close/release within the live window.
3. Keep the primary observer below CNSS, service-manager, Wi-Fi HAL,
   scan/connect, credentials, DHCP, routing, and external ping.
4. Success is `mdm3=ONLINE`, sibling sysmon, service-notifier `180/74`, or WLFW
   service `69` publication under bounded cleanup.
