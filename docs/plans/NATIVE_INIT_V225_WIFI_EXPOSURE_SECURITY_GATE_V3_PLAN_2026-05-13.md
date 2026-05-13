# v225 Plan: Wi-Fi Exposure / Credential Security Gate v3

## Summary

v225 follows v224 `shim-source-required`. The goal is to integrate the
v221-v224 prerequisite closure results with existing root-control exposure and
security hardening evidence, then produce a read-only gate v3 decision before
any controlled CNSS/Wi-Fi start plan is written.

The expected current result is conservative: `still-no-go`. v225 can prove that
the exposure/security model is documented, but it must not close the missing
vendor-root and shim-source blockers by assumption.

Baseline:

- previous result: v224 PASS, `shim-source-required`
- mode: `read-only`
- planned tool: `scripts/revalidation/wifi_exposure_security_gate_v3.py`
- evidence output: `tmp/wifi/v225-exposure-security-gate-v3`
- report:
  `docs/reports/NATIVE_INIT_V225_WIFI_EXPOSURE_SECURITY_GATE_V3_2026-05-13.md`

## Inputs

Required manifests:

- `tmp/wifi/v220-bringup-gate-v2/manifest.json`
- `tmp/wifi/v221-host-vendor-elf-library-evidence/manifest.json`
- `tmp/wifi/v222-vendor-root-evidence-export/manifest.json`
- `tmp/wifi/v223-recovery-rollback-policy/manifest.json`
- `tmp/wifi/v224-android-env-shim-materialize/manifest.json`

Reference documents:

- `docs/reports/NATIVE_INIT_V134_NETWORK_EXPOSURE_GUARDRAIL_2026-05-07.md`
- `docs/reports/NATIVE_INIT_V153_LONGSOAK_SECURITY_2026-05-08.md`
- `docs/reports/NATIVE_INIT_V193_BROKER_AUTH_HARDENING_2026-05-11.md`
- `docs/reports/NATIVE_INIT_V196_SECURITY_SCAN_FOLLOWUP_2026-05-11.md`
- `docs/reports/NATIVE_INIT_V220_WIFI_PREFLIGHT_GATE_V2_2026-05-13.md`
- `docs/reports/NATIVE_INIT_V221_HOST_VENDOR_ELF_LIBRARY_EVIDENCE_2026-05-13.md`
- `docs/reports/NATIVE_INIT_V222_VENDOR_ROOT_EVIDENCE_EXPORT_2026-05-13.md`
- `docs/reports/NATIVE_INIT_V223_RECOVERY_ROLLBACK_POLICY_2026-05-13.md`
- `docs/reports/NATIVE_INIT_V224_ANDROID_ENV_SHIM_MATERIALIZE_2026-05-13.md`

## Gate Categories

### Vendor Evidence

Status is blocked unless v221 has complete ELF/library evidence and v222 has a
host-visible vendor root export.

Current expected result:

- `blocked`
- reason: v221 returned `vendor-root-required`; v222 returned
  `export-source-required`

### Recovery Policy

Status may pass because v223 accepted reboot-only recovery as a future
opt-in-planning recovery primitive.

Current expected result:

- `pass`
- reason: v223 returned `reboot-recovery-accepted`

### Shim Materialization

Status remains blocked or warning unless v224 has source-backed dry-run
materialization.

Current expected result:

- `blocked`
- reason: v224 returned `shim-source-required`

### Root-Control Exposure

Status checks whether current root-control paths remain inside trusted
operator-controlled boundaries before Wi-Fi introduces wider reachability.

The exposure matrix must cover:

- USB ACM serial bridge: host bridge stays bound to localhost
- USB NCM tcpctl: token-authenticated and USB-local only
- rshell: token-authenticated, opt-in, USB-local only
- broker: host-local control and audit policy
- netservice: opt-in persistence and explicit operator action
- future Wi-Fi: must not expose root-control listeners to WLAN

Current expected result:

- `pass` or `warn`
- reason: existing guardrail and broker hardening evidence exists, but v225 must
  explicitly preserve the USB-local-only rule for future Wi-Fi

### Credential Policy

Status must deny credential collection and persistent plaintext secrets in this
track. First test AP credentials require a later explicit security plan.

Current expected result:

- `pass`
- reason: v219/v224 keep Wi-Fi credential and `/data/misc/wifi` handling
  blocked/out of scope

### Active Wi-Fi Operations

Status must remain blocked. v225 is a gate, not an operation plan.

Denied in v225:

- `cnss-daemon` / `cnss_diag` execution
- Wi-Fi HAL / `wificond` / supplicant / hostapd execution
- rfkill write
- `ip link up`
- nl80211 scan
- association / DHCP / Internet routing
- firewall mutation
- token or PSK logging

## Decision Model

The tool should produce one of:

- `still-no-go`: v225 completed but one or more hard prerequisites remain open.
- `cnss-start-plan-approved`: only permits writing a later controlled CNSS
  start plan; it does not permit daemon execution in v225.
- `manual-review-required`: evidence is missing, contradictory, or indicates
  that root-control exposure may leave the trusted USB-local boundary.

Expected current decision:

- `still-no-go`

Expected blockers:

- `vendor_evidence`
- `shim_materialization`

## Planned Tool Behavior

`scripts/revalidation/wifi_exposure_security_gate_v3.py` should:

1. load v220-v224 manifests;
2. read reference report presence and selected metadata;
3. produce `gate-v3.json`, `manifest.json`, and `summary.md`;
4. use private output directory/file handling consistent with hardened host
   tooling;
5. perform no live device command by default;
6. perform no daemon execution, Wi-Fi scan/connect, token print, credential
   collection, listener bind broadening, or firewall mutation.

## Validation

Static checks:

```bash
python3 -m py_compile scripts/revalidation/wifi_exposure_security_gate_v3.py
git diff --check
```

Command guard:

```bash
python3 - <<'PY'
from pathlib import Path
p = Path('scripts/revalidation/wifi_exposure_security_gate_v3.py')
text = p.read_text()
for token in ('rfkill', 'iw ', 'wpa_supplicant', 'hostapd', 'cnss-daemon',
              'cnss_diag', 'ip link set', 'iptables', 'nft '):
    if token in text:
        raise SystemExit(f'forbidden token in v225 tool: {token}')
print('v225 command guard PASS')
PY
```

Run:

```bash
python3 scripts/revalidation/wifi_exposure_security_gate_v3.py \
  --v220-manifest tmp/wifi/v220-bringup-gate-v2/manifest.json \
  --v221-manifest tmp/wifi/v221-host-vendor-elf-library-evidence/manifest.json \
  --v222-manifest tmp/wifi/v222-vendor-root-evidence-export/manifest.json \
  --v223-manifest tmp/wifi/v223-recovery-rollback-policy/manifest.json \
  --v224-manifest tmp/wifi/v224-android-env-shim-materialize/manifest.json \
  --out-dir tmp/wifi/v225-exposure-security-gate-v3
```

Expected assertion:

```bash
python3 - <<'PY'
import json
from pathlib import Path
manifest = json.loads(Path('tmp/wifi/v225-exposure-security-gate-v3/manifest.json').read_text())
assert manifest['pass'] is True
assert manifest['decision'] == 'still-no-go'
assert 'vendor_evidence' in manifest['blockers']
assert 'shim_materialization' in manifest['blockers']
print('v225 manifest assertion PASS')
PY
```

## Acceptance

v225 is complete when:

- all v220-v224 manifest inputs are represented in gate v3;
- root-control exposure policy is explicitly tied to USB-local-only control
  paths;
- credential handling remains denied until a separate test-AP security plan;
- current missing vendor-root and shim-source blockers remain visible;
- the report records `still-no-go` unless the actual evidence changes;
- README/task queue/roadmap state that v225 is a gate, not active Wi-Fi.

## Next Step After v225

If v225 returns `still-no-go`, the immediate next work is not active Wi-Fi. The
next actionable track is:

1. provide a host-visible vendor root to v222;
2. rerun v221 with the exported `vendor-root/`;
3. rerun v224 with source-backed shim materialization;
4. rerun v225 gate v3;
5. only then plan a controlled CNSS start experiment.
