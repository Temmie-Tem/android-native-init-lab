# Native Init v243 CNSS Launcher Contract Plan

- target: bounded CNSS start-only launcher contract
- baseline: v242 runtime inventory PASS
- implementation: host-side contract planner only
- daemon start: still blocked
- output: `tmp/wifi/v243-cnss-launcher-contract-plan/`

## Goal

v242 confirmed that `cnss-daemon` can no longer be treated as a simple
`execve("/vendor/bin/cnss-daemon")` target. Android init starts it with an
identity and capability contract:

- user: `system`
- groups: `system,inet,net_admin,wifi`
- capability: `NET_ADMIN`
- expected service context: `vendor_wcnss_service`
- executable: `/system/vendor/bin/cnss-daemon`
- args: `-n -l`

v243 converts that evidence into an implementation contract for a future
start-only runner. It does not execute the daemon.

## Why This Is Separate From Start-Only

Linux clears capabilities when a process transitions from UID 0 to a non-root
UID unless the launcher deliberately preserves and restores the intended sets.
Android init also has explicit `user`, `group`, `capabilities`, `socket`,
`file`, and `seclabel` service semantics. A native helper must therefore plan
identity, supplemental groups, and `NET_ADMIN` handling before any daemon start.

## Contract Outputs

- `launcher-contract.json`
  - service args
  - Android AID numeric mapping
  - required launcher sequence
  - capability handling requirements
  - namespace/path/linker requirements from v241
- `safety-gates.json`
  - required preflight gates
  - denied actions
  - cleanup/postflight requirements
  - explicit opt-in flags for any future daemon start
- `implementation-plan.json`
  - helper changes required before execution
  - host runner changes required before execution
  - still-blocked items
- `manifest.json`
- `summary.md`

## Guardrails

- No daemon execution in v243.
- No rfkill write.
- No Wi-Fi scan/connect/link-up.
- No DHCP/routing/credential handling.
- No ICNSS bind/unbind.
- No persistent Android partition write.
- Any future start-only runner must require explicit `--allow-daemon-start`
  and `--assume-yes` style confirmation.

## References

- Android init service options:
  - https://android.googlesource.com/platform/system/core/+/e8d02c50d7/init/
- Android AID names/numeric IDs:
  - https://android.googlesource.com/platform/system/core/+/donut-release/include/private/android_filesystem_config.h
- Linux capabilities and UID transition behavior:
  - https://man7.org/linux/man-pages/man7/capabilities.7.html

## Validation

```bash
python3 -m py_compile scripts/revalidation/wifi_cnss_launcher_contract_plan.py
git diff --check
python3 scripts/revalidation/wifi_cnss_launcher_contract_plan.py
```

Expected decision:

- `cnss-launcher-contract-ready`

Expected interpretation:

- v244 may implement a non-starting launcher dry-run/probe or explicit
  capability/identity harness.
- `cnss-daemon` start-only remains blocked until that implementation exists.

