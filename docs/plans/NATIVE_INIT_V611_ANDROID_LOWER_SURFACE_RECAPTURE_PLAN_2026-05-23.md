# Native Init V611 Android Lower-Surface Recapture Plan

- date: `2026-05-23 KST`
- status: `planned`
- target: close the V610 Android evidence limit without native Wi-Fi daemon retry

## Context

V610 classified the current blocker as `v610-companion-surface-gap`:

- Android reaches `mss=ONLINE`, `mdm3=ONLINE`, sibling sysmon services,
  service-notifier `180`/`74`, WLAN-PD, BDF, firmware-ready, and `wlan0`.
- Native V609 reaches modem PIL, QRTR RX/TX, and modem `sysmon-qmi`, but keeps
  `mdm3=OFFLINING` and lacks sibling sysmon, service-notifier, WLFW service
  `69`, and `wlan0`.

The Android dmesg input was filtered for Wi-Fi/CNSS terms, so it cannot prove
the lower memshare/service-locator/QIPCRTR/rpmsg surfaces that may explain the
publication gap.

## Scope

V611 should collect Android read-only evidence only. It may use the existing
Android handoff path if the device is currently in native init.

It must not enable Wi-Fi explicitly, start native daemons, write subsystem sysfs,
open `esoc0` from native, write `qcwlanstate`, send QMI payloads, start Wi-Fi
HAL from native, scan/connect/link-up, use credentials, run DHCP, change routes,
ping externally, or write persistent partitions except the already established
temporary boot-image handoff/rollback path if handoff is used.

## Capture Targets

Collect these from Android after boot settles:

```text
dmesg full lower slice around QRTR/sysmon/service-notifier
/sys/devices/platform/soc/4080000.qcom,mss/subsys0/{name,state,restart_level,firmware_name,crash_count}
/sys/devices/platform/soc/soc:qcom,mdm3/subsys9/{name,state,restart_level,firmware_name,crash_count}
/sys/bus/rpmsg/drivers_autoprobe
/sys/bus/rpmsg/devices
/proc/net/protocols
/proc/net/qrtr if present
/sys/kernel/debug/esoc if present and read-only accessible
```

The dmesg slice must include unfiltered terms:

```text
memshare
cma_alloc
servloc
service_locator
QIPCRTR
rpmsg
rmt_storage
tftp
pd-mapper
sysmon-qmi
service-notifier
```

## Success Criteria

V611 passes if it produces a read-only Android evidence bundle and one
comparison table against V609 showing whether Android has lower surfaces that
native currently lacks.

V611 fails closed if Android ADB is unavailable or the capture is too filtered
to compare against V609.

## Decision Labels

- `v611-android-lower-surface-captured`
- `v611-android-adb-unavailable`
- `v611-capture-too-filtered`
- `v611-ready-for-native-targeted-trigger`

## Next Decision

- If Android proves an extra read-only lower surface, implement the narrowest
  native bounded observer for that surface.
- If the missing surface requires touching `esoc0`, first design a no-close or
  reboot-cleanup safety contract. Do not repeat the raw V595 close path.
- If Android still lacks enough detail, recapture Android with a broader
  read-only bundle before changing native runtime behavior.
