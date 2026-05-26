# V1025 PM Full-Contract Support Plan

- date: `2026-05-26`
- type: source/build-only
- target helper: `a90_android_execns_probe v174`
- prior evidence: `docs/reports/NATIVE_INIT_V1024_FAST_FD_CONTRACT_CLASSIFIER_2026-05-26.md`

## Objective

Add helper support for an Android-good PeripheralManager/eSoC contract before
another native `/dev/subsys_esoc0` retry.

V1024 showed Android holds this contract before WLFW:

```text
pm_proxy_helper -> /dev/subsys_modem
pm-service      -> /dev/subsys_modem
pm-proxy        -> PM service companion
mdm_helper      -> /dev/esoc-0
```

Native V1020/V963 reached the lower `/dev/subsys_esoc0` surface without proving
the `pm_proxy_helper` + `pm-service` `/dev/subsys_modem` contract, then stalled
inside `sdx50m_toggle_soft_reset`.

## Gate

Add a new service-manager order:

```text
after-mdm-helper-esoc-fd-with-pm-full-contract
```

The helper must:

1. start `pm_proxy_helper` before `pm-service`
2. start `pm-service`, then `pm-proxy`, then `mdm_helper`
3. scan `pm_proxy_helper` and `pm-service` fds for `/dev/subsys_modem`
4. scan `mdm_helper` fds for `/dev/esoc-0`
5. allow upper CNSS/service-manager progress only after the PM full contract is observed
6. arm `post-provider-no-wlfw` subsystem retry only after the PM full contract is observed
7. report `pm-full-contract-missing-no-open` if the contract does not materialize

## Guardrails

- no device command in V1025
- no deploy
- no daemon start on-device
- no Wi-Fi HAL live start
- no scan/connect/link-up
- no credentials
- no DHCP/route/external ping
- no boot image write
- no GPIO/sysfs/debugfs write
- no live `/dev/subsys_esoc0` open

## Validation

Run:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_pm_full_contract_support_v1025.py
python3 scripts/revalidation/native_wifi_pm_full_contract_support_v1025.py
git diff --check
```

Expected decision:

```text
v1025-pm-full-contract-support-pass
```

## Next

If V1025 passes, proceed to a deploy-only V1026 for helper `v174`, then a
separate bounded live PM full-contract classifier. Do not start Wi-Fi
scan/connect until WLFW/BDF/`wlan0` evidence exists.
