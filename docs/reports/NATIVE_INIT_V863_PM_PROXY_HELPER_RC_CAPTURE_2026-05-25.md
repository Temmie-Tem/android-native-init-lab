# Native Init V863 pm_proxy_helper.rc Capture Report

## Result

V863 passed as a bounded read-only live capture.

| Unit | Evidence | Decision |
|---|---|---|
| runner | `scripts/revalidation/native_wifi_pm_proxy_helper_rc_capture_v863.py` | dynamic `sda29` major/minor, temporary `ro,noload` vendor mount |
| plan | `tmp/wifi/v863-pm-proxy-helper-rc-plan/manifest.json` | `v863-pm-proxy-helper-rc-capture-plan-ready` |
| live | `tmp/wifi/v863-pm-proxy-helper-rc-live/manifest.json` | `v863-pm-proxy-helper-contract-captured` |

## Captured Contract

Captured file: `tmp/wifi/v863-pm-proxy-helper-rc-live/native/cat-target.txt`

```text
service vendor.per_proxy_helper /vendor/bin/pm_proxy_helper
    class core
    user system
    group system
    disabled
    oneshot

on post-fs-data
    start vendor.per_proxy_helper
```

Parsed service fields:

| Field | Value |
|---|---|
| service | `vendor.per_proxy_helper` |
| path | `/vendor/bin/pm_proxy_helper` |
| class | `core` |
| user | `system` |
| group | `system` |
| disabled | `true` |
| oneshot | `true` |
| trigger | `on post-fs-data -> start vendor.per_proxy_helper` |

## Runtime Notes

- Current `sda29` major/minor was `259:13`; older hardcoded `259:22` is stale.
- The temporary vendor mount used ext4 `ro,noload`.
- `cleanup_ok=true`; post-cleanup `/proc/mounts` contained no V863 temp path.
- Post-run selftest passed.

## Guardrails

- No `mdm_helper`, `ks`, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or
  external ping.
- No raw eSoC ioctl, GPIO/sysfs/debugfs/subsystem write, module load/unload,
  boot image write, or partition write.

## Interpretation

Android starts `vendor.per_proxy_helper` as a disabled, oneshot, `post-fs-data`
service under `system:system`. This is a separate init-managed service from
`vendor.per_mgr` and `vendor.per_proxy`; the current helper has no explicit
model for it. Before any new service start, the next gate should classify how
this helper relates to `pm-service` fd ownership and whether an init-equivalent
wrapper must model:

1. `vendor.per_proxy_helper` post-fs-data oneshot execution,
2. `vendor.per_mgr` `ioprio rt 4`,
3. `vendor.per_proxy` property-start lifecycle,
4. SELinux/domain transition behavior still observed as `kernel` in V861.

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_pm_proxy_helper_rc_capture_v863.py
python3 scripts/revalidation/native_wifi_pm_proxy_helper_rc_capture_v863.py \
  --out-dir tmp/wifi/v863-pm-proxy-helper-rc-plan plan
python3 scripts/revalidation/native_wifi_pm_proxy_helper_rc_capture_v863.py \
  --out-dir tmp/wifi/v863-pm-proxy-helper-rc-live run
```

Live output:

```text
decision: v863-pm-proxy-helper-contract-captured
pass: True
cleanup_ok: True
```

