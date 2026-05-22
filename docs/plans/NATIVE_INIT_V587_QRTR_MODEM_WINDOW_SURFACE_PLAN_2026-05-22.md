# Native Init V587 QRTR/Modem Window Surface Plan

- date: `2026-05-22 KST`
- objective: add post-boot, host-controlled in-window QRTR/modem surface evidence before any qcwlanstate, HAL, scan/connect, or external ping retry
- status: `planned`

## Context

V586 confirmed that V585 companions and private firmware mounts were alive, but
`QIPCRTR` sockets stayed `0`, `/proc/net/qrtr` was absent, and Android-only
QRTR/QMI/WLAN-PD/WLFW/BDF markers remained missing. The next step must not
repeat the V572 boot-time PID1 probe. The serial bridge is one-command-at-a-time,
so in-window captures must be performed by the bounded helper itself.

## Gate

- Gate: `start-only` evidence expansion.
- Helper version: `a90_android_execns_probe v98`.
- Runner: `scripts/revalidation/native_wifi_qrtr_modem_window_surface_v587.py`.
- Deploy wrapper: `scripts/revalidation/wifi_execns_helper_v98_deploy_preflight.py`.

## Guardrails

- No boot image flash.
- No reboot or recovery handoff.
- No PID1/native-init boot hook.
- No qcwlanstate/sysfs driver-state write.
- No Wi-Fi HAL or `IWifi.start()`.
- No supplicant/hostapd/wificond.
- No scan/connect/link-up/DHCP/routing.
- No external ping.
- Companion children remain bounded and cleanup-checked.

## Implementation

1. Extend `stage3/linux_init/helpers/a90_android_execns_probe.c` from v97 to v98.
2. Keep the existing V585 private firmware/modem mount and companion start-only contract.
3. During the companion observe window, capture compact in-namespace surface snapshots:
   - `/proc/net/protocols`
   - `/proc/net/qrtr`
   - `/sys/bus/msm_subsys/devices`
   - `/sys/bus/rpmsg/devices`
   - `/sys/class/remoteproc`
   - `/sys/kernel/debug/service_notifier`
   - `/sys/devices/platform/soc/soc:qcom,mdm3`
   - `/sys/devices/platform/soc/4080000.qcom,mss`
   - `/dev` entries matching `qrtr`, `qmi`, `cnss`, `diag`, `wlan`
4. Parse the helper output and classify whether the native companion window is missing:
   - QRTR family only,
   - QRTR proc/dev visibility,
   - rpmsg/subsys/modem readiness,
   - service-notifier/sysmon readiness,
   - or a changed lower marker that justifies qcwlanstate/HAL retry.

## Success Criteria

V587 passes if it produces a bounded evidence-backed classification and cleanup remains safe.
It does not need to connect Wi-Fi yet. It must either find a lower readiness marker or narrow the
next blocker without boot-time execution.

## Expected Decision

Likely decision: `v587-window-surface-no-readiness-delta`.

That means helper v98 adds the missing in-window surface evidence, but native still does not expose
QRTR modem readiness, WLFW, QMI server connected, BDF, firmware-ready, or `wlan0` markers.

## Next Gate After V587

If V587 still shows no marker delta, the next gate should compare Android and native modem/rpmsg/subsys
state more directly or introduce the smallest host-controlled QRTR readiness input proof. Do not retry
qcwlanstate/HAL, scan/connect, or external ping until a lower readiness marker changes.
