# WSTA154 Seccomp Launcher Gate Model Pass

Date: 2026-07-05 12:10 KST

## Verdict

WSTA154 defines the launcher-side seccomp dry-run gate model from the WSTA153
source policy.  This unit is host-only: it did not touch the device, flash,
reboot, connect Wi-Fi, run DHCP, open a public tunnel, mutate packet filters,
write userdata, switch root, build a seccomp filter, load a seccomp filter, or
enforce seccomp.

Result: PASS.  The generated model binds every launchable Debian service to a
concrete WSTA153 profile, keeps `filter_load_enabled=false`, and fail-closes on
unknown/missing/incomplete policy before any future filter load.

## Source Changes

- Added
  `workspace/public/src/scripts/server-distro/run_wsta154_seccomp_launcher_gate_model.py`.
- Added focused tests in
  `tests/test_server_distro_wsta154_seccomp_launcher_gate_model.py`.

## Generated Model

Model run:

```text
workspace/private/runs/server-distro/wsta154-seccomp-launcher-gate-model-20260705T1210KST/
```

Input WSTA153 policy:

```text
workspace/private/runs/server-distro/wsta153-seccomp-policy-source-20260705T1207KST/wsta153_seccomp_policy.json
```

Decision:

```text
wsta154-seccomp-launcher-gate-model-source-pass
```

Model state:

```text
SECCOMP_LAUNCHER_DRY_RUN_GATE_MODEL_SOURCE_DEFINED
MODEL_ONLY_NOT_ENFORCED
```

Launcher target:

```text
/usr/local/bin/a90-service-launch
```

Service bindings:

| Launcher service | Policy service | Allowlist count |
| --- | --- | ---: |
| `dpublic-smoke-httpd` | `dpublic-smoke-httpd` | 18 |
| `cloudflared-quick-tunnel` | `cloudflared-quick-tunnel` | 52 |
| `dropbear-admin-usb` | `dropbear-admin-usb` | 53 |
| `dpublic-hud` | `dpublic-hud-intent` | 22 |

Global dry-run markers:

```text
A90WSTA154_SECCOMP_POLICY_PRESENT=1
A90WSTA154_SECCOMP_DRY_RUN_ONLY=1
A90WSTA154_SECCOMP_FILTER_LOAD=0
```

Excluded from Debian service seccomp scope:

- `wsta-native-uplink-helper`: native-owned credential and Wi-Fi control
  boundary.
- `native-dpublic-hud-presenter`: native-init KMS owner; Debian launcher covers
  only the HUD intent producer.

## Checks

WSTA154 fail-closes unless:

- the WSTA153 policy JSON is private and present.
- WSTA153 schema/state is exact.
- WSTA153 still says `SOURCE_ONLY_NOT_ENFORCED`.
- exactly four expected WSTA153 policy services are present.
- every profile has a name, non-empty allowlist, stable allowlist count,
  default-deny posture, and `enforcement.enabled=false`.
- native uplink and native HUD presenter boundaries remain excluded.
- the generated launcher model has four service bindings.
- `dpublic-hud` maps to `dpublic-hud-intent`, not the native presenter.
- launcher mode is `dry-run-before-filter-load`.
- every binding and the global launcher integration keep filter loading
  disabled.
- dry-run markers and fail-closed rules are present.
- generated public output is redaction-clean.

## Validation

- `py_compile`:
  - `run_wsta154_seccomp_launcher_gate_model.py`
  - `test_server_distro_wsta154_seccomp_launcher_gate_model.py`
- Focused WSTA153 + WSTA154 tests: `7 tests OK`.
- Full server-distro regression: `539 tests OK`.
- WSTA154 model generation from the real WSTA153 policy: pass.

## Next

WSTA155 should stage the launcher dry-run logging path in a private
rootfs/chroot and prove that the model is observable before any filter load.
Seccomp enforcement remains unproven and must stay behind a separate live gate.
