# Native Init V661 Binder Registration Context Classifier Report

- date: `2026-05-23 KST`
- status: `classified`; Wi-Fi external ping is **not** complete
- runner:
  `scripts/revalidation/native_wifi_binder_registration_context_classifier_v661.py`
- plan:
  `docs/plans/NATIVE_INIT_V661_BINDER_REGISTRATION_CONTEXT_CLASSIFIER_PLAN_2026-05-23.md`
- evidence: `tmp/wifi/v661-binder-registration-context-classifier/`
- decision: `v661-binder-registration-context-gap-classified`

## Scope

V661 is host-only. It reads existing V660, V659, V654, and Android V649
reference evidence. It did not contact the device, write sysfs, start daemons,
start service-manager, start Wi-Fi HAL, scan/connect, use credentials, run
DHCP, change routes, or ping externally.

## Result

```text
decision: v661-binder-registration-context-gap-classified
pass: True
reason: V660 proves service 74, service-manager trio startup, vndservicemanager readiness, and fresh cnss retry are not enough; the remaining native-only gap is dynamic vendor binder registration, context-manager state, or property namespace visibility before WLFW.
next: plan V662 as a bounded service-registry/property-context snapshot gate before any Wi-Fi HAL, scan/connect, credentials, DHCP, routes, or external ping
```

## Evidence Matrix

| subject | classification | evidence | next |
| --- | --- | --- | --- |
| readiness/order | ruled out as primary blocker | `vnd_ready=True`, retry order `10`, ready index `8` | do not repeat readiness-only or unchanged CNSS retry |
| binder devnodes and SELinux context files | present | binder devnodes and service/hwservice context files are present/readable | inspect dynamic registration rather than remounting devnodes |
| native retry stop condition | active blocker | `cnss_tx=1`, `wlfw=0`, `wlan_pd=0`, `qmi=0` | capture vendor binder registration/context before another retry changes behavior |
| Android continuation | reference positive | Android reaches WLFW/WLAN-PD/QMI with no CNSS binder transaction failure | generic binder ioctl noise is not enough to explain native stop |
| dynamic service registration | not captured yet | no service-list/vndservice-list/context-manager snapshot in V660 helper transcript | add bounded service registry/context snapshot gate |
| property namespace | candidate gap | `/dev/__properties__` is absent and the property shim is disabled in V660 private root | snapshot property area and service-context dependencies before HAL |

## Marker Summary

| marker | native V660 | Android reference |
| --- | ---: | ---: |
| service `74` | 1 | 1 |
| CNSS netlink | 10 | >0 |
| CNSS binder transaction failure | 1 | 0 |
| WLFW start | 0 | >0 |
| WLAN-PD | 0 | >0 |
| QMI server connected | 0 | >0 |
| BDF/regdb | 0 | >0 |
| BDF/bdwlan | 0 | >0 |
| firmware ready | 0 | >0 |
| `wlan0` | 0 | >0 |

## Interpretation

V661 moves the blocker one layer narrower than V654:

```text
V654: vndservicemanager readiness was unproven.
V659: vndservicemanager readiness was proven without CNSS retry.
V660: fresh CNSS retry after proven readiness still hit binder transaction -22.
V661: readiness/order/devnode/context-file causes are deprioritized.
```

The next useful live gate is not another unchanged retry and not Wi-Fi HAL. It
should capture dynamic binder registration and property/runtime context while
the same lower stack is alive:

1. service `74` gate;
2. service-manager trio;
3. `vndservicemanager_ready`;
4. service list / vendor service list / context-manager evidence;
5. property namespace snapshot;
6. only then decide whether a fresh `cnss-daemon` retry is worth attaching.

## Guardrails

Keep Wi-Fi HAL, scan/connect, credentials, DHCP, route changes, external ping,
partition writes, and boot-image changes blocked until WLFW/WLAN-PD/BDF or safe
`wlan0` evidence advances.
