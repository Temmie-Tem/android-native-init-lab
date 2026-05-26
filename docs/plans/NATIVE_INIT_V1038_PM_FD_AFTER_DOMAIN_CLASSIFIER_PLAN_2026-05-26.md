# V1038 PM fd Gap After Domain Proof Plan

- date: `2026-05-26`
- type: host-only classifier
- input:
  - `docs/reports/NATIVE_INIT_V1024_FAST_FD_CONTRACT_CLASSIFIER_2026-05-26.md`
  - `docs/reports/NATIVE_INIT_V1028_PM_PROXY_HELPER_MODEM_GET_CLASSIFIER_2026-05-26.md`
  - `docs/reports/NATIVE_INIT_V1029_PM_RUNTIME_INPUT_DELTA_2026-05-26.md`
  - `docs/reports/NATIVE_INIT_V1036_PM_SELINUX_DOMAIN_PROOF_V176_2026-05-26.md`
  - `docs/reports/NATIVE_INIT_V1037_PM_RUNTIME_DOMAIN_GUARD_LIVE_V176_2026-05-26.md`

## Objective

Classify the PM fd contract blocker after V1037.

V1037 removed the earlier PM runtime-domain blocker: all guarded PM actors
matched their requested runtime domains. The remaining question is why Android
captures the PM fd contract while native still does not.

## Evidence Compared

- Android V1024:
  - `pm_proxy_helper` holds `/dev/subsys_modem`
  - `pm-service` holds `/dev/subsys_modem`
  - `pm-proxy` runs as `u:r:vendor_per_proxy:s0`
  - `mdm_helper` holds `/dev/esoc-0`
- V1036:
  - static proof for required PM domains, including
    `u:r:vendor_per_proxy:s0`
- V1037:
  - runtime-domain guard matched four PM actors
  - `pm_proxy_helper` and `pm-service` still showed zero
    `/dev/subsys_modem` fd count
  - `mdm_helper` held `/dev/esoc-0`
  - service-manager/CNSS and `/dev/subsys_esoc0` remained blocked
- helper source:
  - current service-default mapping for `pm-proxy`

## Guardrails

- host-only
- no device command
- no actor start
- no daemon start
- no Wi-Fi HAL start
- no scan/connect/link-up
- no credentials
- no DHCP, route, or external ping
- no eSoC ioctl, subsystem open, GPIO/sysfs/debugfs write
- no boot image write or partition write

## Commands

```bash
python3 -m py_compile scripts/revalidation/native_wifi_pm_fd_after_domain_classifier_v1038.py
python3 scripts/revalidation/native_wifi_pm_fd_after_domain_classifier_v1038.py plan
python3 scripts/revalidation/native_wifi_pm_fd_after_domain_classifier_v1038.py run
```

## Success Criteria

- Prove whether the V1029 domain-gap hypothesis is resolved by V1036/V1037.
- Preserve the remaining PM fd blocker if `/dev/subsys_modem` fd counts are
  still zero.
- Identify any concrete Android/native service-default context mismatch.
- Select a next unit that changes source/build only before another live retry.

## Next

If a source parity bug is found, V1039 should repair the helper and build a new
artifact. Live actor retry remains a separate later gate.
