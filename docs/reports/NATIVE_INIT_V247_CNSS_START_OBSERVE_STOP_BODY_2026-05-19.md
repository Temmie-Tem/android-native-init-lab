# Native Init v247 CNSS Start/Observe/Stop Body

- generated: `2026-05-19`
- result: `PASS`
- decision: `v247-safe-body-ready-live-approval-required`
- reason: helper now contains guarded start/observe/stop body and all safe no-start validations pass; first daemon execution still requires explicit operator approval
- device baseline: `A90 Linux init 0.9.59 (v159)`
- boot image change: none
- daemon start: not executed
- evidence:
  - `tmp/wifi/v247-cnss-start-body-noallow.txt`
  - `tmp/wifi/v247-cnss-start-body-plan/`
  - `tmp/wifi/v247-cnss-start-body-preflight/`
  - `tmp/wifi/v247-cnss-start-body-dryrun/`
  - `tmp/wifi/v247-cnss-start-body-run-blocked/`

## Implementation

- plan: `docs/plans/NATIVE_INIT_V247_CNSS_START_OBSERVE_STOP_BODY_PLAN_2026-05-19.md`
- helper: `stage3/linux_init/helpers/a90_android_execns_probe.c`
- host tool: `scripts/revalidation/wifi_cnss_start_only_runner.py`
- helper version: `a90_android_execns_probe v8`
- helper SHA-256: `77fbdcdcbc6774abe5e34712097496edbac4a4ed763d87c82cf02effb88cd319`
- remote helper: `/cache/bin/a90_android_execns_probe`

## What Changed

- helper `cnss-start-only` mode now has a real guarded lifecycle body behind `--allow-cnss-start-only`:
  - fork one child
  - create a private process group/session
  - chroot into the private Android namespace
  - apply system uid/gid/groups and `CAP_NET_ADMIN`
  - exec fixed `/vendor/bin/cnss-daemon -n -l`
  - observe bounded output and process state
  - capture selected `/proc/<pid>` evidence if observable
  - stop with SIGTERM then SIGKILL if needed
  - reap and emit stable `cnss_start.*` keys
- host runner can parse `cnss_start.*` keys and classify helper decisions when a future approved `run` executes.
- default `plan`/`preflight`/`dry-run` remain non-starting.
- `run` without all dangerous flags remains fail-closed.

## Safe Validation

- `scripts/revalidation/build_android_execns_probe_helper.sh` — PASS
- `python3 -m py_compile scripts/revalidation/wifi_cnss_start_only_runner.py scripts/revalidation/wifi_cnss_identity_probe.py` — PASS
- `git diff --check` — PASS
- `strings stage3/linux_init/helpers/a90_android_execns_probe | rg 'cnss-start-only|allow-cnss-start-only|start-only-pass|start-only-reboot-required'` — PASS
- helper deploy over NCM transfer — PASS
- direct helper no-allow run — PASS / `cnss_start.result=start-only-blocked`
- `python3 scripts/revalidation/wifi_cnss_start_only_runner.py --out-dir tmp/wifi/v247-cnss-start-body-plan plan` — PASS / `dry-run-ready`
- `python3 scripts/revalidation/wifi_cnss_start_only_runner.py --out-dir tmp/wifi/v247-cnss-start-body-preflight preflight` — PASS / `preflight-ready`
- `python3 scripts/revalidation/wifi_cnss_start_only_runner.py --out-dir tmp/wifi/v247-cnss-start-body-dryrun dry-run` — PASS / `preflight-ready`
- `python3 scripts/revalidation/wifi_cnss_start_only_runner.py --out-dir tmp/wifi/v247-cnss-start-body-run-blocked run` — expected FAIL-CLOSED / `start-only-blocked`
- `run /cache/bin/toybox pidof cnss-daemon` — expected absent / exit `1`
- parser synthetic `cnss_start.*` test — PASS

## Direct No-Allow Evidence

| item | value |
| --- | --- |
| helper mode | `cnss-start-only` |
| allow flag | absent |
| namespace status | `namespace-ready` |
| target visible | `/vendor/bin/cnss-daemon` exists in private namespace |
| APEX materialization | `<private-bind-farm>` |
| `cnss_start.allowed` | `0` |
| `cnss_start.exec_attempted` | `0` |
| `cnss_start.child_started` | `0` |
| `cnss_start.pid` | `-1` |
| `cnss_start.postflight_safe` | `1` |
| `cnss_start.result` | `start-only-blocked` |
| `cnss_start.reason` | `missing-allow-cnss-start-only` |
| daemon start executed | `false` |

## Runner Safe Results

| mode | decision | pass | daemon start |
| --- | --- | --- | --- |
| `plan` | `dry-run-ready` | `true` | `false` |
| `preflight` | `preflight-ready` | `true` | `false` |
| `dry-run` | `preflight-ready` | `true` | `false` |
| `run` without flags | `start-only-blocked` | `false` | `false` |

## Guardrails Preserved

- no Wi-Fi scan/connect/link-up/credential/DHCP/routing
- no `cnss_diag`
- no rfkill unblock
- no `ip link set wlan* up`
- no `iw scan` / `iw connect`
- no supplicant/HAL/wificond/hostapd start
- no ICNSS bind/unbind
- no firmware mutation
- no persistent Android partition write
- no automatic reboot

## Interpretation

v247 implements the missing lifecycle body but deliberately validates only the safe path. The repository is now at an explicit approval boundary: the first bounded live `/vendor/bin/cnss-daemon -n -l` start-only attempt can be performed only after operator approval and recovery readiness confirmation. If approved, the expected host command is the v247 runner `run` mode with `--allow-daemon-start --assume-yes --i-understand-reboot-only-recovery`.
