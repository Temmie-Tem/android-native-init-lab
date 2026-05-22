# Native Init V588 Modem/Subsys Window Values Plan

- date: `2026-05-22 KST`
- objective: capture companion-window modem/subsystem sysfs values before any qcwlanstate, HAL, scan/connect, or external ping retry
- status: `planned`

## Context

V587 proved the helper can capture in-window QRTR/modem surfaces without a boot-time PID1 hook. It also showed that `/sys/bus/msm_subsys`, `/sys/bus/rpmsg`, and the modem platform nodes are visible, while `/proc/net/qrtr`, `/dev/qrtr`, `service_notifier`, active rpmsg endpoints, QRTR/QMI/WLFW/BDF/FW-ready markers, and `wlan0` remain absent.

The next useful distinction is whether the native companion window has the same subsystem state that Android has before QRTR modem readiness. Current native read-only spot checks show the modem and external modem subsystem state can be `OFFLINING`; V588 captures those values inside the bounded helper window instead of relying on post-window host reads.

## Gate

- Gate: `start-only` evidence expansion.
- Helper version: `a90_android_execns_probe v99`.
- Runner: `scripts/revalidation/native_wifi_modem_subsys_window_values_v588.py`.
- Deploy wrapper: `scripts/revalidation/wifi_execns_helper_v99_deploy_preflight.py`.

## Guardrails

- No boot image flash.
- No reboot or recovery handoff.
- No PID1/native-init boot hook.
- No subsystem sysfs writes.
- No qcwlanstate/sysfs driver-state write.
- No Wi-Fi HAL or `IWifi.start()`.
- No supplicant/hostapd/wificond.
- No scan/connect/link-up/DHCP/routing.
- No external ping.
- No credential use or credential-bearing evidence.
- Companion children remain bounded and cleanup-checked.

## Implementation

1. Extend `stage3/linux_init/helpers/a90_android_execns_probe.c` from v98 to v99.
2. Keep the existing V585 private firmware/modem mount and V587 companion-window contract.
3. During the companion observe window, capture compact read-only values:
   - `/sys/devices/platform/soc/4080000.qcom,mss/subsys0/{uevent,name,state,restart_level,firmware_name,crash_count}`
   - `/sys/devices/platform/soc/soc:qcom,mdm3/subsys9/{uevent,name,state,restart_level,firmware_name,crash_count}`
   - `/sys/bus/rpmsg/drivers`
   - `/sys/bus/rpmsg/drivers_autoprobe`
4. Parse the helper output and classify whether the native window shows:
   - missing value capture,
   - lower readiness marker change,
   - modem/esoc subsystem offline/offlining state,
   - or no readiness delta despite captured values.

## Success Criteria

V588 passes if it produces a bounded evidence-backed classification and cleanup remains safe. It does not need to connect Wi-Fi yet. It must either observe a lower readiness marker or identify whether the modem/subsystem state itself is below the qcwlanstate/HAL retry gate.

## Expected Decision

Likely decision: `v588-modem-subsys-offline-window`.

That means the helper captured modem/subsystem values inside the same bounded companion window, but the subsystem state remains below the Android QRTR/QMI readiness point.

## Next Gate After V588

If V588 shows an offline/offlining subsystem state with no marker delta, the next gate should compare Android boot-time subsystem values and locate the smallest safe, read-mostly subsystem-readiness trigger. Do not retry qcwlanstate/HAL, scan/connect, or external ping until a lower readiness marker changes.
