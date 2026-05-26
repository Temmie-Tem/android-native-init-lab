# V955 PM-Proxy Matrix Support Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| source/build verifier | `tmp/wifi/v955-pm-proxy-matrix-support/manifest.json` | `v955-pm-proxy-matrix-support-pass` |

V955 adds helper `v159` support for one bounded matrix comparator:
`service_manager_order=after-mdm-helper-esoc-fd-with-pm-proxy`.

The new order starts `/vendor/bin/pm-proxy` after `pm-service` has settled and
before `mdm_helper`, then keeps the existing `/dev/esoc-0` fd gate before
starting service managers and CNSS actors.

## Implementation

- Updated `stage3/linux_init/helpers/a90_android_execns_probe.c` to
  `a90_android_execns_probe v159`.
- Added order enum:
  `after-mdm-helper-esoc-fd-with-pm-proxy`.
- Added a `pm_proxy` child using `/vendor/bin/pm-proxy` and
  `COMPOSITE_ID_PER_PROXY`.
- Added provider-readiness snapshot phase:
  `cnss_before_esoc_after_pm_proxy_start`.
- Updated the host matrix wrapper to accept the new order.
- Added verifier:
  `scripts/revalidation/native_wifi_pm_proxy_matrix_support_v955.py`.

## Guardrails

- Source/build-only; no device command was executed by V955.
- No `pm_proxy_helper` child is added or started.
- No `/dev/subsys_esoc0` open is added.
- No eSoC notify, boot-done, GPIO write, sysfs write, Wi-Fi HAL, scan/connect,
  credentials, DHCP/routes, or external ping is added.
- Existing WLFW-precondition gate remains the only path that can open the
  subsystem trigger child.

## Validation

Executed:

```bash
python3 -m py_compile \
  scripts/revalidation/native_wifi_pm_proxy_matrix_support_v955.py \
  scripts/revalidation/native_wifi_cnss_service_manager_matrix_live_v931.py
python3 scripts/revalidation/native_wifi_pm_proxy_matrix_support_v955.py
```

Verifier result:

- decision: `v955-pm-proxy-matrix-support-pass`
- build artifact:
  `tmp/wifi/v955-execns-helper-v159-build/a90_android_execns_probe`
- build sha256:
  `c4eb155c9fa1e105d80a040689dcedc9370b0340b60ac624980ccaf20e9c94d6`
- failed checks: none

## Next

V956 should deploy helper `v159` only. V957 should run the bounded
`after-mdm-helper-esoc-fd-with-pm-proxy` live comparator with
`pm_proxy_helper`, `/dev/subsys_esoc0`, Wi-Fi HAL, scan/connect, credentials,
DHCP/routes, and external ping still blocked.
