# V1039 PM Proxy Context Parity Support

- date: `2026-05-26`
- scope: source/build-only helper support
- decision: `v1039-pm-proxy-context-parity-support-pass`
- pass: `True`
- evidence: `tmp/wifi/v1039-pm-proxy-context-parity-support/manifest.json`
- artifact: `tmp/wifi/v1039-execns-helper-v177-build/a90_android_execns_probe`
- artifact sha256: `d71c7c87a7759eb8e2eb0058c2057e0e9348a4c6f572f48d6d9b2962053a4795`

## Summary

V1039 implements the V1038 source-level parity repair.

The helper is now `a90_android_execns_probe v177`. It keeps
`/vendor/bin/pm-service` in `u:r:vendor_per_mgr:s0`, but maps
`/vendor/bin/pm-proxy` to Android's observed `u:r:vendor_per_proxy:s0` domain.
This removes the concrete helper-side mismatch left after the V1037 PM runtime
domain proof.

V1039 also adds focused evidence capture for the next PM full-contract live gate.
When the PM full-contract fd predicate still fails, the helper records compact
fd links and stall snapshots for:

- `cnss_before_esoc_pm_full_gap_pm_proxy_helper`
- `cnss_before_esoc_pm_full_gap_per_mgr`

The final summary now reports
`cnss_before_esoc.pm_full_contract_gap_snapshot_captured`.

## Checks

| Check | Result |
| --- | --- |
| helper version `v177` | pass |
| `pm-service -> vendor_per_mgr` | pass |
| `pm-proxy -> vendor_per_proxy` | pass |
| shared `pm-service`/`pm-proxy` `vendor_per_mgr` mapping removed | pass |
| PM context allowlist preserved | pass |
| PM full-contract mode preserved | pass |
| PM gap snapshot labels present | pass |
| static AArch64 build | pass |
| artifact strings confirm marker, contexts, and gap labels | pass |

## Guardrails

- No device command was executed.
- No deploy, actor start, daemon start, Wi-Fi HAL, scan/connect, credentials,
  DHCP/routes, external ping, boot image write, partition write, firmware
  mutation, GPIO/sysfs/debugfs write, eSoC ioctl, or live `/dev/subsys_esoc0`
  open occurred.
- The change only affects helper source/build behavior and next-run evidence
  collection.

## Validation

Commands:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_pm_proxy_context_parity_support_v1039.py
python3 scripts/revalidation/native_wifi_pm_proxy_context_parity_support_v1039.py
```

Result:

```text
decision: v1039-pm-proxy-context-parity-support-pass
pass: True
artifact_sha256: d71c7c87a7759eb8e2eb0058c2057e0e9348a4c6f572f48d6d9b2962053a4795
```

## Next

V1040 should deploy helper `v177` only. After deploy parity is verified, a
separate bounded live PM full-contract retry can determine whether the corrected
`pm-proxy` domain is sufficient for `/dev/subsys_modem` fd formation or whether
the new fd/wchan evidence identifies the next blocker.
