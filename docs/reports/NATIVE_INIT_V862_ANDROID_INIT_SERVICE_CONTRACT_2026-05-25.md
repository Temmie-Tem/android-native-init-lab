# Native Init V862 Android Init Service Contract Report

## Result

V862 passed as a host-only classifier.

| Unit | Evidence | Decision |
|---|---|---|
| classifier | `scripts/revalidation/native_wifi_android_init_service_contract_v862.py` | host-only, no device contact |
| run | `tmp/wifi/v862-android-init-service-contract/manifest.json` | `v862-init-contract-classified-pm-proxy-helper-content-needed` |

## Android Init Contract

| Service | Path | Class | User | Group | Disabled | I/O priority |
|---|---|---|---|---|---|---|
| `vendor.per_mgr` | `/vendor/bin/pm-service` | `core` | `system` | `system` | `false` | `rt 4` |
| `vendor.per_proxy` | `/vendor/bin/pm-proxy` | `core` | `system` | `system` | `true` | none |
| `vendor.per_proxy_helper` | not captured in V210 target rc | unknown | unknown | unknown | unknown | unknown |

Additional lifecycle evidence:

- `vendor.per_proxy` starts from `on property:init.svc.vendor.per_mgr=running`.
- `vendor.per_proxy` stops from `on property:sys.shutdown.requested=*`.
- V210 inventory lists `/vendor/etc/init/pm_proxy_helper.rc`.
- V853 Android dmesg shows Android init processing
  `/vendor/etc/init/pm_proxy_helper.rc` and starting `vendor.per_proxy_helper`
  during `post-fs-data`.

## Native Gap

V861 already proved that direct exec is not enough:

- helper accepted `u:r:vendor_per_mgr:s0` as the target context;
- runtime `attr/current` still stayed `kernel`;
- `pm-service` exited `0`;
- `pm-proxy` exited `1`;
- no `/dev/subsys_esoc0` or `/dev/subsys_modem` fd hold appeared.

V862 adds four concrete init-contract gaps:

| Gap | Status |
|---|---|
| `vendor.per_mgr` uses `ioprio rt 4`, helper has no ioprio model | open |
| `vendor.per_proxy` is disabled and property-started by init, helper starts it directly | open |
| shutdown stop lifecycle is not modelled | open |
| `vendor.per_proxy_helper` is Android-started but its rc content is not captured | open |

## Interpretation

The next native action should not be `mdm_helper`/`ks` yet. Android starts one
more PeripheralManager-adjacent service, `vendor.per_proxy_helper`, before the
lower actor path is complete. Its init rc file was listed by V210 and observed
as started by V853, but its contents were not captured. Modelling it blindly
would create the same class of direct-exec mismatch that V861 just exposed.

## Next Gate

V863 should capture `/vendor/etc/init/pm_proxy_helper.rc` read-only from the
vendor image and classify its service block before any new actor start:

1. mount/export the vendor init file read-only;
2. record `service vendor.per_proxy_helper` options and actions;
3. compare against helper support for `ioprio`, `init.svc` lifecycle, and
   process domain;
4. keep `mdm_helper`, `ks`, Wi-Fi HAL, scan/connect, credentials, DHCP/routes,
   external ping, raw eSoC ioctl, GPIO/sysfs/debugfs writes, module load, boot
   image writes, and partition writes blocked.

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_android_init_service_contract_v862.py
python3 scripts/revalidation/native_wifi_android_init_service_contract_v862.py \
  --out-dir tmp/wifi/v862-android-init-service-contract run
```

Output:

```text
decision: v862-init-contract-classified-pm-proxy-helper-content-needed
pass: True
```
