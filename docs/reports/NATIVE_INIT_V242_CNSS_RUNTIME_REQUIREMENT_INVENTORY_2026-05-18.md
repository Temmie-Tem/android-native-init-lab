# Native Init v242 CNSS Runtime Requirement Inventory

- generated: `2026-05-18`
- result: `PASS`
- decision: `cnss-runtime-inventory-ready-for-launcher-contract-plan`
- reason: linker prerequisite is closed; remaining work is launcher/runtime contract planning
- device baseline: `A90 Linux init 0.9.59 (v159)`
- boot image change: none
- daemon start: not executed
- evidence: `tmp/wifi/v242-cnss-runtime-inventory-live2/`

## Implementation

- plan: `docs/plans/NATIVE_INIT_V242_CNSS_RUNTIME_REQUIREMENT_INVENTORY_PLAN_2026-05-18.md`
- host tool: `scripts/revalidation/wifi_cnss_runtime_inventory.py`
- output files:
  - `manifest.json`
  - `summary.md`
  - `runtime-requirements.json`
  - `live-captures.json`
  - `captures/*.txt`

## Validation

- `python3 -m py_compile scripts/revalidation/wifi_cnss_runtime_inventory.py` — PASS
- `git diff --check` — PASS
- `python3 scripts/revalidation/wifi_cnss_runtime_inventory.py dry-run --out-dir tmp/wifi/v242-plan-smoke` — PASS
- `python3 scripts/revalidation/wifi_cnss_runtime_inventory.py collect --out-dir tmp/wifi/v242-cnss-runtime-inventory-live2` — PASS

## Prerequisites

| check | result | decision |
| --- | --- | --- |
| v216 service replay model | PASS | `replay-model-ready` |
| v218 CNSS daemon dry-run | PASS | `daemon-dryrun-partial` |
| v241 private VNDK APEX alias probe | PASS | `android-linker-vndk-apex-alias-cnss-list-pass` |

## Service Runtime Contract

| service | executable | args | user | groups | capabilities |
| --- | --- | --- | --- | --- | --- |
| `cnss-daemon` | `/system/vendor/bin/cnss-daemon` | `-n -l` | `system` | `system,inet,net_admin,wifi` | `NET_ADMIN` |
| `cnss_diag` | `/system/vendor/bin/cnss_diag` | `-q -f -t HELIUM` | `system` | `system,wifi,inet,sdcard_rw,media_rw,diag` | none |

## Live Runtime Checks

| check | result |
| --- | --- |
| `version` | PASS |
| `status` | PASS |
| `mountsystem ro` | PASS |
| `/cache/bin/a90_android_execns_probe` | PASS |
| `/cache/bin/a90_real_ld.config.txt` | PASS |
| `/mnt/system/system/bin/linker64` | PASS |
| v241 private vendor `cnss-daemon` linker-list | PASS |

## Start-Only Blockers

| blocker | severity | meaning |
| --- | --- | --- |
| launcher identity contract | blocker before start | native launcher must explicitly handle `system` uid/gid, supplemental groups, and `NET_ADMIN` capability |
| SELinux service context not recreated | known gap | Android evidence uses `u:r:vendor_wcnss_service:s0`; native init does not reproduce Android domain transition |
| Android property runtime gap | probable runtime gap | `/dev/socket/property_service` or `/dev/__properties__` is not visible in native runtime |
| diag device gap | phase2 blocker | `cnss_diag` should remain blocked until `/dev/diag` availability is understood |
| QRTR device gap | runtime risk | `/dev/qrtr` is not visible; QMI/PDR expectations may fail |
| global Android path alias gap | expected private-namespace-only | `/system/vendor` and `/vendor` are not globally ready; start-only must use the private exec namespace helper |

## Interpretation

- v241 closed the linker dependency blocker, not the daemon runtime contract.
- v242 confirms the next correct step is a launcher-contract design, not direct Wi-Fi bring-up.
- `cnss-daemon` start-only remains blocked until identity/capability/path/runtime gaps are handled in a bounded helper.
- `cnss_diag`, Wi-Fi scan/connect/link-up/credential/DHCP/routing remain blocked.

## References

- Android init service options: `service`, `user`, `group`, `capabilities`, `socket`, `file`, `seclabel`
  - https://android.googlesource.com/platform/system/core/+/e8d02c50d7/init/
- Android linker namespace/VNDK runtime isolation: vendor processes use default/VNDK/system namespace relationships and runtime linkerconfig
  - https://source.android.com/docs/core/architecture/vndk/linker-namespace
