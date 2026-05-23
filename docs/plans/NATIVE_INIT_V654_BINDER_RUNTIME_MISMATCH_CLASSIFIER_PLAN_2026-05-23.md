# Native Init V654 Binder Runtime Mismatch Classifier Plan

- date: `2026-05-23 KST`
- cycle: `v654`
- scope: host-only classifier
- target: classify the remaining V653 `cnss-daemon` binder `-22` stop after
  fresh service-notifier `74` and bounded service-manager startup

## Background

V653 fixed the V652 ordering regression. The helper waited for a fresh
service-notifier `74` kernel marker before starting the service-manager trio:

```text
qrtr_ns -> rmt_storage -> tftp_server -> pd_mapper
  -> cnss_diag -> cnss-daemon -> service74_gate
    -> servicemanager -> hwservicemanager -> vndservicemanager
```

That preserved service-notifier `180/74`, but native still stopped before WLFW:

```text
service-notifier 180/74: present
cnss-daemon binder tx -22: present
WLFW/WLAN-PD/QMI/BDF/wlan0: absent
```

## Guardrails

V654 must not:

- contact the device;
- write sysfs, `boot_wlan`, `qcwlanstate`, DSP boot nodes, or `esoc0`;
- start companion daemons, service-manager, Wi-Fi HAL, `wificond`, supplicant,
  or hostapd;
- scan/connect/link-up, use credentials, run DHCP, change routes, or ping
  externally.

## Inputs

- V651 host-only CNSS/WLFW continuation classifier:
  `tmp/wifi/v651-cnss-wlfw-continuation/manifest.json`
- V652 service-manager parity live regression:
  `tmp/wifi/v652-service74-binder-parity-live-20260523-082200/manifest.json`
- V653 service `74` gated service-manager live result:
  `tmp/wifi/v653-service74-gated-live-20260523-085337/manifest.json`
- V653 helper transcript and dmesg delta:
  `tmp/wifi/v653-service74-gated-live-20260523-085337/native/`
- Android V649 final replay dmesg references:
  `tmp/wifi/v649-final-live-replay-classifier/android/replay/`

## Checks

1. Verify V653 preserved fresh service-notifier `74`.
2. Verify V653 service-manager children were observable and cleanup-safe.
3. Verify `/dev/binder`, `/dev/hwbinder`, and `/dev/vndbinder` existed and were
   readable inside the private namespace.
4. Verify `cnss-daemon` and `vndservicemanager` both reached `/dev/vndbinder`.
5. Verify SELinux exec contexts were set for `cnss-daemon`,
   `servicemanager`, `hwservicemanager`, and `vndservicemanager`.
6. Compare Android generic binder ioctl `-22` against WLFW continuation to avoid
   misclassifying a non-fatal Android compatibility warning as the native
   blocker.
7. Isolate native-only `cnss-daemon` binder transaction `-22` and compare its
   timing against `service74`, `cnss-daemon` netlink, and service-manager start.
8. Determine whether the next live proof should test vndservicemanager
   readiness plus a fresh `cnss-daemon` binder attempt before any HAL work.

## Success Criteria

V654 passes if it classifies the V653 stop into one of these outcomes:

- `v654-vndbinder-readiness-gap-classified`
- `v654-binder-devnode-gap-classified`
- `v654-selinux-context-gap-classified`
- `v654-android-reference-gap-needs-recapture`

Passing V654 does not authorize Wi-Fi HAL, scan/connect, credentials, DHCP,
route changes, or external ping. The only acceptable next live gate is a
bounded binder-runtime proof that can still clean up and reboot safely.
