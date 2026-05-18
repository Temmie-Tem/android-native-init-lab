# Native Init v246 CNSS Start-Only Helper Mode

- generated: `2026-05-19`
- result: `PASS`
- decision: `preflight-ready`
- reason: helper exposes guarded `cnss-start-only` mode and safe validation proves daemon execution remains blocked without explicit allow flags
- device baseline: `A90 Linux init 0.9.59 (v159)`
- boot image change: none
- daemon start: not executed
- evidence:
  - `tmp/wifi/v246-cnss-start-only-helper-noallow.txt`
  - `tmp/wifi/v246-cnss-start-only-helper-plan/`
  - `tmp/wifi/v246-cnss-start-only-helper-preflight/`
  - `tmp/wifi/v246-cnss-start-only-helper-dryrun/`
  - `tmp/wifi/v246-cnss-start-only-helper-run-blocked/`

## Implementation

- plan: `docs/plans/NATIVE_INIT_V246_CNSS_START_ONLY_HELPER_MODE_PLAN_2026-05-19.md`
- helper: `stage3/linux_init/helpers/a90_android_execns_probe.c`
- host tool: `scripts/revalidation/wifi_cnss_start_only_runner.py`
- helper version: `a90_android_execns_probe v8`
- helper SHA-256: `5ae105f0d397f845cd602eb4b283cdbd817146eff9405d10c090320eded25c65`
- remote helper: `/cache/bin/a90_android_execns_probe`

## Validation

- `scripts/revalidation/build_android_execns_probe_helper.sh` — PASS
- `python3 -m py_compile scripts/revalidation/wifi_cnss_start_only_runner.py scripts/revalidation/wifi_cnss_identity_probe.py` — PASS
- `git diff --check` — PASS
- helper deploy over NCM transfer — PASS
- direct helper no-allow run — PASS / `cnss_start.result=start-only-blocked`
- `python3 scripts/revalidation/wifi_cnss_start_only_runner.py --out-dir tmp/wifi/v246-cnss-start-only-helper-plan plan` — PASS / `dry-run-ready`
- `python3 scripts/revalidation/wifi_cnss_start_only_runner.py --out-dir tmp/wifi/v246-cnss-start-only-helper-preflight preflight` — PASS / `preflight-ready`
- `python3 scripts/revalidation/wifi_cnss_start_only_runner.py --out-dir tmp/wifi/v246-cnss-start-only-helper-dryrun dry-run` — PASS / `preflight-ready`
- `python3 scripts/revalidation/wifi_cnss_start_only_runner.py --out-dir tmp/wifi/v246-cnss-start-only-helper-run-blocked run` — expected FAIL-CLOSED / `start-only-blocked`

## Live Safe Evidence

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
| `cnss_start.postflight_safe` | `1` |
| `cnss_start.result` | `start-only-blocked` |
| `cnss_start.reason` | `missing-allow-cnss-start-only` |
| daemon start executed | `false` |

## Preflight Result

| item | value |
| --- | --- |
| command count | `18` |
| ok commands | `18` |
| helper SHA match | `true` |
| required failures | `[]` |
| active Wi-Fi warnings | `[]` |

## Interpretation

v246 adds the helper-side mode and guard surface needed before any real start-only experiment. It deliberately does not implement live `cnss-daemon` execution behind the allow flag yet; even with the host runner, the default `run` path remains fail-closed. The next step is either implementing the actual start/observe/stop body behind the helper guard or asking for explicit operator approval before moving to the first bounded live start-only attempt.
