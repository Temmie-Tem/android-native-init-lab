# Native Init V928 CNSS Binder / Lower Publication Intersection Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| V928 host-only classifier | `tmp/wifi/v928-cnss-binder-lower-intersection/manifest.json` | `v928-cnss-binder-lower-publication-intersection-gap` |

V928 closes the V927 follow-up as a same-window ordering problem. Helper `v153`
removed the output-truncation and linkerconfig namespace blockers, but
`cnss-daemon` still repeats Binder failure before `wlfw_start`. Older V603
evidence proves that service-manager can clear the Binder failure, but that
ordering regressed service-notifier `180`.

## Evidence Matrix

| Question | Finding |
| --- | --- |
| V927 namespace repair active | `surface_mode=compact`, `linkerconfig_mode=copy-real`, `vndk_apex_alias_mode=v30-to-system-ext-v30`, property root present |
| V927 transcript truncation | `false` |
| V927 CNSS kernel reachability | `cnss_daemon_cld80211=4`, `cnss_diag_cld80211=8` |
| V927 Binder failure | `cnss_daemon_binder_failure=56` |
| V927 upper Wi-Fi progress | `wlfw_start=0`, `BDF=0`, `wlan0=0` |
| V603 service-manager effect | Binder transaction failures cleared to `0` |
| V603 regression | service-notifier `180=0`, service-notifier `74=0`, `wlfw_start=0` |

## Interpretation

The next blocker is no longer “repair linkerconfig/property namespace” or
“avoid full-output truncation.” Those were addressed by V925/V927.

The current blocker is an intersection:

1. CNSS without service-manager reaches `cld80211` but loops on Binder failure.
2. CNSS with QRTR-first service-manager removes the Binder failure but loses the
   lower service-notifier publication path.

The next unit should therefore be source/build-only support for a delayed
service-manager/CNSS ordering gate. The intended live shape is: preserve lower
publication first, start service-manager trio at the correct point, then start
CNSS with compact output and observe whether Binder failure and WLFW absence are
both improved in the same window.

## Guardrails

V928 is host-only:

- no device command;
- no daemon start;
- no service-manager start;
- no Wi-Fi HAL start;
- no scan/connect/link-up;
- no credential use;
- no DHCP, route change, or external ping;
- no eSoC ioctl, subsystem open, GPIO/sysfs/debugfs write, boot image write, or
  partition write.

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_cnss_binder_lower_intersection_v928.py
python3 scripts/revalidation/native_wifi_cnss_binder_lower_intersection_v928.py
```

## Next

V929 should be source/build-only: add helper/runner support for a delayed
service-manager/CNSS intersection gate using helper `v153` compact output. Do
not proceed to Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external
ping until WLFW/BDF/`wlan0` progresses.
