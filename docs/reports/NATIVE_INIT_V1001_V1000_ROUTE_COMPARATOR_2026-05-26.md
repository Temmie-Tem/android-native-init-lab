# V1001 V1000 Route Comparator Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| host-only comparator | `tmp/wifi/v1001-v1000-route-comparator/manifest.json` | `v1001-select-service-window-scoped-subsys-trigger-support` |

V1001 selects a source/build-only V1002 helper update. The next native live gate
should not wait for `wlfw_start` before `/dev/subsys_esoc0`; V1000 shows Android
can reach `/dev/subsys_esoc0` get first, then `wlfw_start`, WLAN-PD, and ICNSS
QMI inside the service-window actor set.

## Key Evidence

| Event | Time |
| --- | ---: |
| Wi-Fi HAL legacy start | `6.854689s` |
| Wi-Fi HAL ext start | `6.965385s` |
| `wificond` start | `8.147853s` |
| `vendor.mdm_helper` start | `8.256167s` |
| `cnss-daemon` start | `8.263292s` |
| `/dev/subsys_esoc0` get | `8.426630s` |
| `cnss-daemon wlfw_start` | `8.434392s` |
| WLAN-PD indication | `9.448181s` |
| ICNSS QMI connected | `9.450701s` |

Derived deltas:

| Delta | Value |
| --- | ---: |
| `/dev/subsys_esoc0` get → `wlfw_start` | `7.762ms` |
| `wlfw_start` → WLAN-PD | `1013.789ms` |
| WLAN-PD → ICNSS QMI | `2.52ms` |
| `cnss-daemon` start → `/dev/subsys_esoc0` get | `163.338ms` |
| `mdm_helper` start → `/dev/subsys_esoc0` get | `170.463ms` |

## Interpretation

- V998 had the repaired native service-window actor set and correct SELinux
  context, but did not try `/dev/subsys_esoc0`.
- V923 kept `/dev/subsys_esoc0` closed because it waited for a WLFW
  precondition that V1000 now shows may be downstream of the subsystem get.
- V964 still proves blind or insufficiently scoped `/dev/subsys_esoc0` open can
  stall in `sdx50m_toggle_soft_reset`.
- Therefore the next live path must be narrower than a blind trigger but less
  circular than the V923 WLFW-precondition gate.

## Decision

V1002 should be source/build-only and add a helper mode that opens
`/dev/subsys_esoc0` only after all of these are true:

- current-boot SELinux policy/domain proof has been refreshed;
- service-manager, hwservicemanager, vndservicemanager, Wi-Fi HAL legacy/ext,
  `wificond`, `mdm_helper`, and `cnss-daemon` are observable;
- `mdm_helper` holds `/dev/esoc-0`;
- GPIO/eSoC read-only surfaces are captured;
- D-state blocker capture and cleanup reboot are armed;
- scan/connect, credentials, DHCP/routes, and external ping remain blocked.

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_v1000_route_comparator_v1001.py
python3 scripts/revalidation/native_wifi_v1000_route_comparator_v1001.py
```

Result:

```text
decision: v1001-select-service-window-scoped-subsys-trigger-support
pass: True
route: source-build-helper-for-service-window-scoped-subsys-trigger
```

## Guardrails

- Host-only comparator.
- No device command, actor start, eSoC ioctl, `/dev/subsys_esoc0` open, Wi-Fi
  bring-up, scan/connect, credentials, DHCP, external ping, boot image write, or
  partition write occurred in V1001.

## Next

Implement V1002 as source/build-only helper support. Do not run the live native
subsystem trigger until the new mode has explicit preflight checks and cleanup
contracts.
