# v224 Plan: Android-Env Shim Dry-Run Materialization

## Summary

v224 follows v219 `shim-plan-partial`, v222 `export-source-required`, and v223
`reboot-recovery-accepted`. The goal is to materialize the **shape** of the
Android-like runtime shim without executing daemons or mutating live Wi-Fi
state.

- baseline native runtime: `A90 Linux init 0.9.59 (v159)`
- previous result: v223 PASS, decision `reboot-recovery-accepted`
- planned tool: `scripts/revalidation/wifi_android_env_shim_materialize.py`
- evidence output: `tmp/wifi/v224-android-env-shim-materialize`
- report after execution:
  `docs/reports/NATIVE_INIT_V224_ANDROID_ENV_SHIM_MATERIALIZE_2026-05-13.md`

v224 is a host-side dry-run/materialization plan by default. It does not run
`cnss-daemon`, `cnss_diag`, Wi-Fi HAL, `wificond`, supplicant, hostapd, rfkill,
scan, connect, DHCP, QMI/PDR/SSR writes, or Android property mutation.

## Inputs

The tool should load:

- `tmp/wifi/v219-native-android-env-shim/manifest.json`
- `tmp/wifi/v221-host-vendor-elf-library-evidence/manifest.json`
- `tmp/wifi/v222-vendor-root-evidence-export/manifest.json`
- `tmp/wifi/v223-recovery-rollback-policy/manifest.json`

Optional input:

- `--vendor-root tmp/wifi/v222-vendor-root-evidence-export/vendor-root`

When `--vendor-root` is absent or v222 still says `export-source-required`, v224
should produce a partial dry-run plan and keep daemon execution blocked.

## Materialization Model

The v224 tool should produce a private host-side shim plan tree:

```text
tmp/wifi/v224-android-env-shim-materialize/
├── manifest.json
├── shim-materialization.json
├── summary.md
└── shim-root/
    ├── system-vendor-alias-plan.json
    ├── static-properties.json
    ├── groups-capabilities.json
    ├── log-policy.json
    └── health-capture-plan.json
```

This tree is evidence only. It is not copied to the device and is not a boot
image payload.

## Allowed Dry-Run Areas

From v219, v224 may materialize or model:

- `/system/vendor -> /vendor` compatibility as a path alias plan;
- static property evidence as `static-properties.json`, not a live property
  service;
- root-only temporary execution model or explicit future group/capability table;
- private daemon stdout/stderr log policy;
- before/after health capture plan;
- ACM/NCM rescue control preflight checklist;
- v223 reboot-only recovery policy dependency.

## Denied Areas

The tool must keep these blocked:

- Android property mutation and `setprop`/`ctl.*` writes;
- QMI/PDR/SSR writes;
- binder/hwbinder service publication;
- daemon execution;
- Wi-Fi credentials and `/data/misc/wifi`;
- rfkill write, link-up, scan, connect, DHCP;
- live `/sys`, debugfs, configfs writes;
- persistent passwd/group mutation;
- persistent mount or boot image modification.

## Decision Model

- `shim-dryrun-ready`
  - v219 shim matrix is loaded;
  - v223 decision is `reboot-recovery-accepted`;
  - all blocked v219 rows remain blocked in the dry-run model;
  - required dry-run artifacts are generated;
  - no live action is required.
- `shim-source-required`
  - dry-run artifacts are generated, but vendor-root dependent path/library
    evidence remains incomplete because v222 returned `export-source-required`.
- `shim-too-wide`
  - the required shim would need property service recreation, QMI/PDR/SSR writes,
    binder/HAL publication, credentials, or daemon execution.
- `manual-review-required`
  - input manifests are missing or conflict with expected v219/v223 state.

## Guardrails

The v224 tool must not:

- run live device commands by default;
- execute vendor binaries;
- write to the device;
- create world-readable evidence;
- follow destination symlinks;
- perform mounts by default;
- mutate Android properties;
- start any Wi-Fi/CNSS service;
- perform active network operations.

## Validation

Static:

```bash
python3 -m py_compile scripts/revalidation/wifi_android_env_shim_materialize.py
git diff --check
python3 - <<'PY'
import sys
sys.path.insert(0, 'scripts/revalidation')
import wifi_android_env_shim_materialize
wifi_android_env_shim_materialize.validate_no_active_commands()
print('v224 command guard PASS')
PY
```

Dry-run:

```bash
python3 scripts/revalidation/wifi_android_env_shim_materialize.py \
  --v219-manifest tmp/wifi/v219-native-android-env-shim/manifest.json \
  --v221-manifest tmp/wifi/v221-host-vendor-elf-library-evidence/manifest.json \
  --v222-manifest tmp/wifi/v222-vendor-root-evidence-export/manifest.json \
  --v223-manifest tmp/wifi/v223-recovery-rollback-policy/manifest.json \
  --out-dir tmp/wifi/v224-android-env-shim-materialize
```

Expected while source vendor root is absent:

- PASS
- decision `shim-source-required`
- all live mutation/daemon/network areas remain denied

Optional vendor-root dry-run:

```bash
python3 scripts/revalidation/wifi_android_env_shim_materialize.py \
  --vendor-root tmp/wifi/v222-vendor-root-evidence-export/vendor-root \
  --out-dir tmp/wifi/v224-android-env-shim-materialize
```

Expected only if v222 returned `vendor-root-ready`:

- PASS
- decision `shim-dryrun-ready`

## Acceptance

v224 is complete when:

- a private shim materialization manifest exists;
- v219 `shim-required` rows are represented as dry-run artifacts;
- v219 `blocked` rows remain blocked;
- v223 reboot-only recovery policy is recorded as a hard dependency;
- v225 can consume the result for exposure/security gate v3;
- no daemon execution, Wi-Fi active operation, or live device mutation occurs.

## Next

If v224 returns `shim-source-required`, keep source vendor root acquisition as a
parallel blocker and continue only to read-only v225 security/exposure gate
planning. If v224 returns `shim-dryrun-ready`, v225 may integrate v221-v224
results into gate v3.
