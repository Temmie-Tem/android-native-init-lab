# WSTA153 Seccomp Policy Source Pass

Date: 2026-07-05 12:02 KST

## Verdict

WSTA153 derives a concrete source-only seccomp policy draft from the live
syscall baselines already folded into WSTA108.  This unit is host-only: it did
not touch the device, flash, reboot, connect Wi-Fi, run DHCP, open a public
tunnel, mutate packet filters, write userdata, switch root, or load/enforce a
seccomp filter.

Result: PASS.  The generated policy has four default-deny service profiles and
explicitly records `SOURCE_ONLY_NOT_ENFORCED`.

## Source Changes

- Added
  `workspace/public/src/scripts/server-distro/run_wsta153_seccomp_policy_source.py`.
- Added focused tests in
  `tests/test_server_distro_wsta153_seccomp_policy_source.py`.
- Updated WSTA108 compact status to retain the full cloudflared runtime syscall
  list, so the WSTA153 policy can be derived from a single operator-status
  artifact.

## Generated Policy

Policy run:

```text
workspace/private/runs/server-distro/wsta153-seccomp-policy-source-20260705T1207KST/
```

Input WSTA108 status:

```text
workspace/private/runs/server-distro/wsta153-operator-status-seccomp-baseline-20260705T1205KST/wsta108_operator_server_status.json
```

Decision:

```text
wsta153-seccomp-policy-source-pass
```

Policy state:

```text
SECCOMP_POLICY_DRAFT_FROM_LIVE_BASELINES
SOURCE_ONLY_NOT_ENFORCED
```

Service profiles:

| Service | Source state | Allowlist count |
| --- | --- | ---: |
| `dpublic-smoke-httpd` | `SMOKE_SERVICE_SYSCALL_TRACE_LIVE_PROVEN` | 18 |
| `cloudflared-quick-tunnel` | `CLOUDFLARED_RUNTIME_LIVE_PROVEN` | 52 |
| `dropbear-admin-usb` | `DROPBEAR_ADMIN_SYSCALL_TRACE_LIVE_PROVEN` | 53 |
| `dpublic-hud-intent` | `DPUBLIC_HUD_INTENT_SYSCALL_TRACE_LIVE_PROVEN` | 22 |

Policy posture:

- architecture: `aarch64`.
- default action: `ERRNO(EPERM)`.
- every profile: `deny_by_default=true`.
- every profile: `enforcement.enabled=false`.
- no public URL value or secret value logged.

Excluded from Debian service seccomp scope:

- `wsta-native-uplink-helper`: native-owned credential and Wi-Fi control
  boundary.
- `native-dpublic-hud-presenter`: native-init KMS owner; Debian profile covers
  only the HUD intent producer.

## Checks

WSTA153 fail-closes unless:

- WSTA108 decision is `wsta108-operator-server-status-source-pass`.
- Server state is `SERVER_PROFILE_READY_DEFAULT_OFF`.
- WSTA108 says seccomp profile source is ready.
- remaining syscall profiles are empty.
- smoke, cloudflared, Dropbear admin, and HUD intent syscall proofs are all
  live-proven.
- every source has a full non-empty syscall list.
- generated policy has exactly the expected four profiles.
- every profile is default-deny and not enforced.
- generated public output is redaction-clean.

## Validation

- `py_compile`:
  - `run_wsta108_operator_server_status.py`
  - `run_wsta153_seccomp_policy_source.py`
  - `test_server_distro_wsta108_operator_server_status.py`
  - `test_server_distro_wsta153_seccomp_policy_source.py`
- Focused WSTA108 + WSTA153 tests: `51 tests OK`.
- Full server-distro regression: `535 tests OK`.
- WSTA108 status regeneration for WSTA153 input: pass.
- WSTA153 policy generation: pass.

## Next

WSTA154 should design the launcher-side seccomp integration/dry-run gate before
any filter is loaded.  The policy is now concrete enough to wire, but not yet
proven safe to enforce live.
