# V1025 PM Full-Contract Support

- date: `2026-05-26`
- scope: source/build-only helper support
- helper: `a90_android_execns_probe v174`
- verifier: `scripts/revalidation/native_wifi_pm_full_contract_support_v1025.py`
- decision: `v1025-pm-full-contract-support-pass`
- evidence: `tmp/wifi/v1025-pm-full-contract-support/manifest.json`
- build artifact: `tmp/wifi/v1025-execns-helper-v174-build/a90_android_execns_probe`
- build sha256: `07b9efdebddd955e388026afa2afed86cd52d762dcc4ac36638318f4661fe78f`

## Summary

V1025 adds a new helper order:

```text
after-mdm-helper-esoc-fd-with-pm-full-contract
```

This order models the Android-good PM/eSoC fd contract captured in V1024:

| Actor | Required fd |
| --- | --- |
| `pm_proxy_helper` | `/dev/subsys_modem` |
| `pm-service` | `/dev/subsys_modem` |
| `pm-proxy` | service companion |
| `mdm_helper` | `/dev/esoc-0` |

The new path is fail-closed: service-manager/CNSS progression and the
`post-provider-no-wlfw` subsystem retry require the PM full-contract predicate.
If the predicate never appears, the helper reports
`pm-full-contract-missing-no-open` rather than opening `/dev/subsys_esoc0`.

## Guardrails

- V1025 is source/build-only.
- No device command, deploy, daemon start, Wi-Fi HAL live start, scan/connect,
  credentials, DHCP/routes, external ping, boot image write, partition write,
  firmware mutation, GPIO/sysfs/debugfs write, or live `/dev/subsys_esoc0`
  open.
- The existing `pm-proxy` order remains available for prior evidence
  comparison.

## Validation

Commands:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_pm_full_contract_support_v1025.py
python3 scripts/revalidation/native_wifi_pm_full_contract_support_v1025.py
git diff --check
files=$( { git diff --name-only; git ls-files --others --exclude-standard; } | sort -u )
# secret scan used the actual SSID/password literals and hex encodings; omitted here
```

Verifier result:

```text
decision: v1025-pm-full-contract-support-pass
pass: True
next: deploy helper v174 only, then run a bounded live PM full-contract classifier before any Wi-Fi scan/connect
```

`git diff --check` passed. The scoped secret scan returned no matches for the
actual SSID/password literals or their hex encodings.

## Next

If the verifier passes, V1026 should deploy helper `v174` only. The next live
classifier should prove or disprove the PM full-contract fd predicate before any
new subsystem retry or Wi-Fi scan/connect attempt.
