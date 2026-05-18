# Native Init v243 CNSS Launcher Contract Plan

- generated: `2026-05-18`
- result: `PASS`
- decision: `cnss-launcher-contract-ready`
- reason: contract is ready; daemon start remains blocked until implementation and explicit approval
- device baseline: `A90 Linux init 0.9.59 (v159)`
- boot image change: none
- daemon start: not executed
- evidence: `tmp/wifi/v243-cnss-launcher-contract-plan/`

## Implementation

- plan: `docs/plans/NATIVE_INIT_V243_CNSS_LAUNCHER_CONTRACT_PLAN_2026-05-18.md`
- host tool: `scripts/revalidation/wifi_cnss_launcher_contract_plan.py`
- output files:
  - `launcher-contract.json`
  - `safety-gates.json`
  - `implementation-plan.json`
  - `manifest.json`
  - `summary.md`

## Validation

- `python3 -m py_compile scripts/revalidation/wifi_cnss_launcher_contract_plan.py` — PASS
- `git diff --check` — PASS
- `python3 scripts/revalidation/wifi_cnss_launcher_contract_plan.py` — PASS

## Contract Summary

| item | value |
| --- | --- |
| target | `/vendor/bin/cnss-daemon -n -l` inside private Android execution namespace |
| Android service executable | `/system/vendor/bin/cnss-daemon` |
| user | `system` / `1000` |
| primary group | `system` / `1000` |
| supplemental groups | `inet=3003`, `net_admin=3005`, `wifi=1010` |
| capability | `NET_ADMIN` / `CAP_NET_ADMIN` |
| daemon start in v243 | blocked |

## Required Preflight Before Any Start

- helper exists and hash/version is expected
- real linkerconfig is present
- private VNDK APEX alias linker-list still passes
- harmless identity/capability probe passes before daemon entrypoint
- ACM rescue or NCM control path is available before start

## Required Future Helper Behavior

- prepare the same private namespace as v241
- use private `/dev/null`, real linkerconfig, and VNDK APEX alias
- map Android AID names to numeric uid/gid
- call `setgroups`, `setgid`, and `setuid` in a tested order
- prove `CAP_NET_ADMIN` preservation/restoration on a harmless probe first
- run in a tracked session/process group
- enforce timeout, cleanup, and stale-process postflight

## Still Blocked

- first `cnss-daemon` start-only attempt
- `cnss_diag`
- Wi-Fi HAL, `wificond`, supplicant, hostapd
- Wi-Fi scan/connect/link-up/credential/DHCP/routing
- any public network listener expansion

## Interpretation

- v243 converts v242 blockers into a concrete launcher contract.
- The next safe version is v244: non-starting launcher dry-run and harmless identity/capability probe.
- Direct daemon execution is still not approved by this report.

## References

- Android init service options:
  - https://android.googlesource.com/platform/system/core/+/e8d02c50d7/init/
- Android AID mapping:
  - https://android.googlesource.com/platform/system/core/+/donut-release/include/private/android_filesystem_config.h
- Linux capabilities and UID transitions:
  - https://man7.org/linux/man-pages/man7/capabilities.7.html

