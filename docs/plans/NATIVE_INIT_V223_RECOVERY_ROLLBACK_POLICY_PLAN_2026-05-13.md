# v223 Plan: Recovery / Rollback Policy Hardening

## Summary

v223 follows v220 `no-go`, v221 `vendor-root-required`, and v222
`export-source-required`. The goal is not to bring Wi-Fi up. The goal is to
turn the current recovery evidence into an explicit policy that future
temporary mutation plans must obey.

- baseline native runtime: `A90 Linux init 0.9.59 (v159)`
- previous result: v222 PASS, decision `export-source-required`
- planned tool: `scripts/revalidation/wifi_recovery_rollback_policy.py`
- evidence output: `tmp/wifi/v223-recovery-rollback-policy`
- report after execution:
  `docs/reports/NATIVE_INIT_V223_RECOVERY_ROLLBACK_POLICY_2026-05-13.md`

v223 is `read-only` and policy-only. It must not execute Wi-Fi daemons, mutate
ICNSS controls, write firmware paths, run rfkill/link-up/scan/connect, or reboot
the device by itself.

## Background

Current evidence says:

- v214 opt-in ICNSS reprobe failed with decision `icnss-rebind-failed`.
- v214 post-reboot check showed ICNSS returned to the bound state.
- v217 classified ICNSS recovery/debug controls as read-only evidence with
  writable/recovery controls unsafe.
- v220 kept `icnss_recovery` blocked.
- v222 did not close the vendor evidence blocker; it only prepared the export
  helper and returned `export-source-required`.

Therefore v223 must assume:

- generic ICNSS unbind/bind is not a safe recovery primitive;
- reboot is the only proven recovery path;
- active CNSS/Wi-Fi experiments remain blocked until a later gate explicitly
  accepts the recovery risk.

## Scope

Implement a host-side policy generator:

```text
scripts/revalidation/wifi_recovery_rollback_policy.py
```

The tool should load:

- `tmp/wifi/v214-icnss-reprobe/manifest.json`
- `tmp/wifi/v217-icnss-debug-recovery-inventory-native/manifest.json`
- `tmp/wifi/v220-bringup-gate-v2/manifest.json`
- `tmp/wifi/v222-vendor-root-evidence-export/manifest.json`

It should write:

- `manifest.json`
- `recovery-policy.json`
- `summary.md`

## Policy Model

The generated policy should contain:

- recovery primitive classification:
  - `accepted`: native reboot
  - `denied`: generic ICNSS `unbind`/`bind`
  - `denied`: `driver_override`
  - `denied`: unreviewed sysfs/debugfs writes
- stop conditions:
  - ICNSS not bound after an experiment
  - firmware path rollback mismatch
  - serial/ACM rescue unavailable
  - NCM rescue unavailable when the experiment depends on NCM
  - daemon process cannot be stopped/reaped
  - unexpected WLAN netdev/rfkill state change
  - kernel log contains known ICNSS probe/recovery failure markers
- preflight requirements:
  - `version`
  - `status`
  - `bootstatus`
  - `selftest verbose`
  - `netservice status`
  - `wifiinv full` or current Wi-Fi inventory equivalent
  - v222/v221 vendor evidence status if daemon execution is later proposed
- post-reboot verification:
  - bridge reconnects
  - `version` matches expected native init
  - ICNSS bound state is restored
  - firmware path rollback state is expected
  - no stale test daemon remains
  - longsoak/log evidence remains readable

## Decision Model

- `reboot-recovery-accepted`
  - v214 post-reboot recovery evidence exists;
  - v217 still denies direct recovery controls;
  - policy explicitly restricts future mutation plans to reboot-backed recovery;
  - no active Wi-Fi operation is approved by this decision.
- `active-mutation-blocked`
  - v214/v217/v220 evidence is missing or contradictory;
  - rescue path requirements cannot be stated;
  - stop conditions are incomplete.
- `manual-review-required`
  - loaded manifests disagree with the expected v220/v222 blocker state.

## Guardrails

The v223 tool must not:

- run live device commands by default;
- reboot the device;
- write `/sys`, `/proc/sys`, debugfs, or configfs;
- run `cnss-daemon`, `cnss_diag`, Wi-Fi HAL, `wificond`, supplicant, or hostapd;
- run rfkill write, link-up, scan, connect, DHCP, or credential handling;
- alter `firmware_class.path`;
- change NCM/ACM/tcpctl state.

## Validation

Static:

```bash
python3 -m py_compile scripts/revalidation/wifi_recovery_rollback_policy.py
git diff --check
python3 - <<'PY'
import sys
sys.path.insert(0, 'scripts/revalidation')
import wifi_recovery_rollback_policy
wifi_recovery_rollback_policy.validate_no_active_commands()
print('v223 command guard PASS')
PY
```

Policy run:

```bash
python3 scripts/revalidation/wifi_recovery_rollback_policy.py \
  --v214-manifest tmp/wifi/v214-icnss-reprobe/manifest.json \
  --v217-native-manifest tmp/wifi/v217-icnss-debug-recovery-inventory-native/manifest.json \
  --v220-manifest tmp/wifi/v220-bringup-gate-v2/manifest.json \
  --v222-manifest tmp/wifi/v222-vendor-root-evidence-export/manifest.json \
  --out-dir tmp/wifi/v223-recovery-rollback-policy
```

Expected:

- PASS
- decision `reboot-recovery-accepted` if v214 post-reboot recovery evidence is
  present and v217/v220 remain in the expected blocked state
- no live device command capture

## Acceptance

v223 is complete when:

- a policy manifest exists;
- reboot is explicitly recorded as the only currently accepted recovery path;
- direct ICNSS recovery writes remain denied;
- future mutation preflight/stop/post-reboot checks are listed;
- v224 can use the policy as a hard dependency without weakening the current
  Wi-Fi blockers.

## Next

If v223 returns `reboot-recovery-accepted`, v224 may plan reversible Android-env
shim materialization dry-run. If v223 returns `active-mutation-blocked`, v224
must stay documentation-only and no reversible mutation should be attempted.
