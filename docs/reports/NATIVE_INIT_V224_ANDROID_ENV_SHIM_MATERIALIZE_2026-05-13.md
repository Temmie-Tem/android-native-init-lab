# v224 Report: Android-Env Shim Dry-Run Materialization

## Summary

v224 implements a host-side Android-env shim dry-run materializer and runs it
against v219/v221/v222/v223 evidence.

- script: `scripts/revalidation/wifi_android_env_shim_materialize.py`
- plan:
  `docs/plans/NATIVE_INIT_V224_ANDROID_ENV_SHIM_DRYRUN_MATERIALIZATION_PLAN_2026-05-13.md`
- output: `tmp/wifi/v224-android-env-shim-materialize`
- result: PASS
- decision: `shim-source-required`
- reason: `dry-run artifacts generated but source vendor root remains required`

This is the expected safe result while v222 remains `export-source-required`.
The tool materializes host-side dry-run artifacts only. It does not execute
daemons, mutate Android properties, write live sysfs/debugfs/configfs state, or
start active Wi-Fi networking.

## What Was Implemented

`wifi_android_env_shim_materialize.py` now:

- loads v219 shim matrix evidence;
- loads v221/v222 vendor evidence state;
- loads v223 recovery policy;
- creates private host-side `shim-root/` artifacts;
- keeps v219 `blocked` rows blocked;
- records v223 reboot-only recovery policy as a hard dependency;
- emits `manifest.json`, `shim-materialization.json`, `summary.md`, and:
  - `shim-root/system-vendor-alias-plan.json`
  - `shim-root/static-properties.json`
  - `shim-root/groups-capabilities.json`
  - `shim-root/log-policy.json`
  - `shim-root/health-capture-plan.json`

## Validation

Static validation:

```bash
python3 -m py_compile scripts/revalidation/wifi_android_env_shim_materialize.py

python3 - <<'PY'
import sys
sys.path.insert(0, 'scripts/revalidation')
import wifi_android_env_shim_materialize
wifi_android_env_shim_materialize.validate_no_active_commands()
print('v224 command guard PASS')
PY
```

Result:

```text
v224 command guard PASS
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

Result:

```text
PASS out_dir=/home/temmie/dev/A90_5G_rooting/tmp/wifi/v224-android-env-shim-materialize decision=shim-source-required reason=dry-run artifacts generated but source vendor root remains required
```

Manifest assertion:

```text
shim-source-required True dry-run artifacts generated but source vendor root remains required
counts {'available': 3, 'blocked': 4, 'host-evidence-required': 1, 'out-of-scope': 1, 'shim-required': 5}
```

Output file modes:

```text
600 tmp/wifi/v224-android-env-shim-materialize/manifest.json
600 tmp/wifi/v224-android-env-shim-materialize/shim-materialization.json
600 tmp/wifi/v224-android-env-shim-materialize/shim-root/groups-capabilities.json
600 tmp/wifi/v224-android-env-shim-materialize/shim-root/health-capture-plan.json
600 tmp/wifi/v224-android-env-shim-materialize/shim-root/log-policy.json
600 tmp/wifi/v224-android-env-shim-materialize/shim-root/static-properties.json
600 tmp/wifi/v224-android-env-shim-materialize/shim-root/system-vendor-alias-plan.json
600 tmp/wifi/v224-android-env-shim-materialize/summary.md
```

## Artifact Summary

| artifact | status | source rows |
| --- | --- | --- |
| system_vendor_alias_plan | source-required | 3 |
| static_properties | evidence-only | 2 |
| groups_capabilities | dry-run-model | 2 |
| log_policy | ready | 2 |
| health_capture_plan | ready | 2 |

## Blocked Rows Kept Blocked

| category | item |
| --- | --- |
| property | Android property service |
| socket-ipc | QMI/PDR/SSR interaction |
| recovery-rollback | ICNSS recovery if broken |
| security | Wi-Fi credentials and `/data/misc/wifi` |

## Artifact Hashes

```text
7754f1532936b46ea7f563b6b48be79345be4063dc9f3f87efc15fdabf017c64  scripts/revalidation/wifi_android_env_shim_materialize.py
e6eb8e97e6b3006712e5ab9ca93afe5fc337c52dd1da68d6a981e4701595ed30  docs/plans/NATIVE_INIT_V224_ANDROID_ENV_SHIM_DRYRUN_MATERIALIZATION_PLAN_2026-05-13.md
20d12711546041c87e9922a6334793d361d1f3ce3e04decb263ff654a33b573e  tmp/wifi/v224-android-env-shim-materialize/manifest.json
4d3e5bcd0d8686b21c0dd1ada95c8a43ef455fabd2691ac2660418cc22776f99  tmp/wifi/v224-android-env-shim-materialize/shim-materialization.json
6a4ed9f00b248ec47da20f554c132ccd8c70f97ed102e98ff81e1d9b3a3da4b1  tmp/wifi/v224-android-env-shim-materialize/summary.md
```

## Interpretation

v224 successfully materializes the host-side dry-run shape, but the vendor root
blocker remains open because v222 has no source vendor root.

Still blocked:

- daemon execution;
- Android property mutation;
- QMI/PDR/SSR writes;
- binder/HAL publication;
- Wi-Fi credential paths;
- rfkill write, link-up, scan/connect.

## Next

v225 may proceed as a read-only exposure/security gate and gate v3 integration.
It must preserve the source vendor root blocker unless v222/v221 are rerun with
real vendor evidence.
