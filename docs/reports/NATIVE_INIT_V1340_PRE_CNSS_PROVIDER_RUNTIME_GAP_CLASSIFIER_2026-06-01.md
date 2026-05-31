# V1340 Pre-CNSS Provider Runtime Gap Classifier

- Date: 2026-06-01
- Scope: host-only native-init Wi-Fi blocker classification
- Inputs:
  - `tmp/wifi/v1339-android-pre-cnss-provider-observer-live/manifest.json`
  - `docs/reports/NATIVE_INIT_V1339_ANDROID_PRE_CNSS_PROVIDER_OBSERVER_2026-05-31.md`
  - `docs/reports/NATIVE_INIT_V1092_PM_PROVIDER_READY_2026-05-27.md`
  - `tmp/wifi/v1191-pm-per-mgr-policy-load/manifest.json`

## Decision

`v1340-policy-load-vndservice-gate-gap-classified` — PASS.

V1339 did start the Android-order pre-CNSS provider chain, but it did not
reproduce the PM provider-positive prerequisites. The PM children were launched
under the private namespace, then remained in the `kernel` SELinux context and
exited before the observe window.

## Key Facts

| Fact | Value |
| --- | --- |
| V1339 decision | `v1339-pre-cnss-provider-chain-no-wlfw` |
| V1339 helper result | `start-only-runtime-gap` |
| `pm-service` lifecycle | observable, then `exit_code=0` |
| `pm-proxy` lifecycle | observable, then `exit_code=1` |
| `pm-service` requested domain | `u:r:vendor_per_mgr:s0` |
| `pm-service` runtime domain | `kernel` |
| `pm-proxy` requested domain | `u:r:vendor_per_proxy:s0` |
| `pm-proxy` runtime domain | `kernel` |
| V1092 positive control | provider registration observed |
| V1191 positive control | `vendor_per_mgr` domain fixed after policy load |

## Interpretation

The V1339 gap is not simply that the Android-order provider actors were absent.
They were present, but their runtime prerequisites were incomplete:

```text
Android-order provider chain starts
  -> PM children stay in kernel SELinux context
  -> pm-service exits 0 and pm-proxy exits 1 before the window
  -> no provider-positive vndservice surface
  -> no provider-triggered /dev/subsys_esoc0 path
  -> no mdm_helper /dev/esoc-0 hold
  -> no ks/MHI/WLFW/wlan0
```

Earlier V1092 evidence already showed that `vendor.qcom.PeripheralManager`
registration needs two conditions:

1. current-boot V490 SELinux policy-load proof;
2. explicit `vndservicemanager` readiness/query before treating `pm-service` as ready.

V1191 then confirmed the domain side of that prerequisite: after the policy load
path, `pm-service` can run as `u:r:vendor_per_mgr:s0`.

## Guardrails

- Host-only classifier; no device command executed.
- No daemon start.
- No Wi-Fi HAL, `wificond`, scan/connect, credentials, DHCP/routes, or external ping.
- No manual `/dev/subsys_esoc0` open.
- No eSoC ioctl/notify/BOOT_DONE spoof.
- No PMIC/GPIO write.
- No flash, boot image write, or partition write.

## Evidence

| Item | Path |
| --- | --- |
| classifier | `scripts/revalidation/native_wifi_pre_cnss_provider_runtime_gap_classifier_v1340.py` |
| manifest | `tmp/wifi/v1340-pre-cnss-provider-runtime-gap-classifier/manifest.json` |
| summary | `tmp/wifi/v1340-pre-cnss-provider-runtime-gap-classifier/summary.md` |

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_pre_cnss_provider_runtime_gap_classifier_v1340.py
python3 scripts/revalidation/native_wifi_pre_cnss_provider_runtime_gap_classifier_v1340.py
```

Result:

```text
decision: v1340-policy-load-vndservice-gate-gap-classified
pass: True
```

## Next

V1341 should repair the current pre-CNSS provider live gate instead of widening
toward Wi-Fi HAL or scan/connect:

1. refresh or require current-boot V490 policy-load proof;
2. start service-manager, hwservicemanager, and vndservicemanager;
3. wait for explicit vndservicemanager readiness and/or query
   `vendor.qcom.PeripheralManager`;
4. then start `pm_proxy_helper`, `pm-service`, and `pm-proxy`;
5. only after provider-positive proof, continue to `mdm_helper`, `cnss_diag`,
   and `cnss-daemon`;
6. keep Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping,
   manual eSoC open, PMIC/GPIO writes, flash, and boot image writes blocked.
