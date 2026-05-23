# Native Init V654 Binder Runtime Mismatch Classifier Report

- date: `2026-05-23 KST`
- status: `classified`; Wi-Fi external ping is **not** complete
- runner:
  `scripts/revalidation/native_wifi_binder_runtime_mismatch_classifier_v654.py`
- evidence: `tmp/wifi/v654-binder-runtime-mismatch-classifier/`
- decision: `v654-vndbinder-readiness-gap-classified`

## Scope

V654 is host-only. It compares existing V651, V652, V653, and Android V649
evidence. It did not contact the device, write sysfs, start daemons,
start service-manager, start Wi-Fi HAL, scan/connect, use credentials, run DHCP,
change routes, or ping externally.

## Result

```text
decision: v654-vndbinder-readiness-gap-classified
pass: True
reason: V653 preserved service 74 and mounted the binder/SELinux runtime surface, but cnss-daemon opened vndbinder before vndservicemanager readiness was proven and then hit a cnss-specific binder transaction -22. Generic binder ioctl -22 is not sufficient as a root cause because Android logs that class while still reaching WLFW.
next: plan V655 as a bounded vndservicemanager-readiness plus fresh cnss-daemon binder attempt proof; keep Wi-Fi HAL, scan/connect, credentials, DHCP, routes, and external ping blocked
device_commands_executed: False
daemon_start_executed: False
service_manager_start_executed: False
wifi_bringup_executed: False
```

## Checks

| check | value |
| --- | --- |
| V651 binder blocker classified | `True` |
| V652 delayed service-manager regressed service `74` | `True` |
| V653 service `74` gate preserved | `True` |
| V653 service-manager trio observable | `True` |
| V653 `cnss-daemon` reaches `/dev/vndbinder` | `True` |
| V653 `vndservicemanager` reaches `/dev/vndbinder` | `True` |
| V653 binder devnodes present/readable | `True` |
| V653 SELinux exec contexts set | `True` |
| Android `cnss-daemon` reaches WLFW | `True` |
| Android `cnss-daemon` binder transaction absent | `True` |
| Android generic binder ioctl `-22` non-fatal | `True` |
| Native `cnss-daemon` binder transaction blocks WLFW | `True` |
| `cnss-daemon` started before `vndservicemanager` | `True` |
| `vndservicemanager` readiness unproven | `True` |

## Timing

| source | delta | ms |
| --- | --- | --- |
| Android V649 | service `74` -> `cnss-daemon` netlink | `1229.193` |
| Android V649 | `cnss-daemon` netlink -> genl fail | `47.398` |
| Android V649 | `cnss-daemon` netlink -> WLFW start | `62.71` |
| Android V649 | genl fail -> WLFW start | `15.312` |
| Android V649 | WLFW start -> WLAN-PD | `1068.607` |
| native V653 | service `74` -> `cnss-daemon` netlink | `418.882` |
| native V653 | service `74` -> service-manager binder ioctl `-22` | `459.919` |
| native V653 | service `74` -> `cnss-daemon` binder transaction `-22` | `503.871` |
| native V653 | `cnss-daemon` netlink -> service-manager binder ioctl `-22` | `41.037` |
| native V653 | `cnss-daemon` netlink -> `cnss-daemon` binder transaction `-22` | `84.989` |
| native V653 | service-manager binder ioctl `-22` -> `cnss-daemon` binder transaction `-22` | `43.952` |

## Interpretation

V653 rules out several lower-level suspects:

- binder devnodes exist and are readable;
- `cnss-daemon` opens `/dev/vndbinder`;
- `vndservicemanager` opens `/dev/vndbinder`;
- service-manager children are observable and cleanup-safe;
- SELinux exec contexts are set for the relevant children;
- Android logs generic binder ioctl `-22` while still reaching WLFW.

The remaining native-only stop condition is narrower:

```text
Android: service 74 -> cnss netlink -> genl fail -> WLFW -> WLAN-PD/QMI/BDF
Native:  service 74 -> cnss netlink -> cnss vndbinder transaction -22 -> no WLFW
```

The helper sequence starts `cnss-daemon` at order `6` and
`vndservicemanager` at order `9`. That means V653 proves process existence and
cleanup, but it does not prove that the vendor binder context manager was ready
before `cnss-daemon` made its failing binder transaction.

## Next Gate

Proceed to V655 as a bounded binder-runtime proof:

1. preserve the V653 service `74` gate;
2. start and verify `vndservicemanager` readiness explicitly;
3. trigger a fresh `cnss-daemon` binder attempt after vendor binder readiness,
   preferably by bounded restart or split-start;
4. observe only up to WLFW/WLAN-PD/QMI/BDF markers;
5. keep Wi-Fi HAL, scan/connect, credentials, DHCP, route changes, and external
   ping blocked until native reaches WLFW/BDF cleanly.
