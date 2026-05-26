# V960 V959 Full-Surface Classifier Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| host-only classifier | `tmp/wifi/v960-v959-full-surface-classifier/manifest.json` | `v960-full-surface-confirms-post-provider-wlfw-gap` |

V960 classifies the V959 full-surface evidence. The current blocker is no
longer provider lifecycle or CNSS netlink reachability. The remaining blocker is
the post-provider WLFW path: MHI devices, WLFW/BDF, and `wlan0` remain absent.

## Findings

| Marker | Value |
| --- | --- |
| provider keys | `786` |
| surface keys | `1222` |
| full surface | `true` |
| provider persisted | `true` |
| CNSS netlink reached | `true` |
| MHI devices empty | `true` |
| `mdm3` still `OFFLINING` | `true` |
| `wlan0` absent | `true` |
| WLFW/BDF absent | `true` |
| fail-closed safety | `true` |

## Interpretation

The native Android-userspace companion now reaches:

- `pm-service` + `pm-proxy` provider surface;
- service-manager trio;
- `mdm_helper` with `/dev/esoc-0`;
- `cnss_diag`;
- `cnss-daemon` with `cld80211` netlink.

Despite that, no WLFW/BDF/`wlan0` edge appears. The existing helper gate opens
`/dev/subsys_esoc0` only after WLFW precondition appears. V960 shows that this
may now be a circular gate: the signal being waited for may require a lower
trigger that the current gate never allows.

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_v959_full_surface_classifier_v960.py
python3 scripts/revalidation/native_wifi_v959_full_surface_classifier_v960.py
```

## Next

Plan a host-only trigger-gate redesign. Do not open `/dev/subsys_esoc0`, start
`pm_proxy_helper`, start Wi-Fi HAL, scan/connect, use credentials, run DHCP, or
ping externally until the new gate is explicit and documented.
