# v229 Controlled CNSS Start-Only Runner Report

## Summary

v229 adds the first host-side controlled CNSS start-only runner:

```text
scripts/revalidation/wifi_cnss_start_experiment.py
```

The implemented runner supports:

- `plan`: validate prerequisite manifests and v228 plan artifacts only;
- `dry-run`: emit the exact v229 execution graph without bridge/device calls;
- `preflight`: collect live read-only native state through cmdv1;
- `run`: opt-in daemon start-only attempt, gated by `--allow-daemon-start --assume-yes`.

No live CNSS daemon execution was performed in this report. The validated state is
`dry-run-ready`, and live preflight later produced the expected safe stop label
`start-only-runtime-gap`.

## Validation

Commands run:

```bash
python3 -m py_compile \
  scripts/revalidation/wifi_cnss_start_experiment.py \
  scripts/revalidation/wifi_cnss_start_plan.py \
  scripts/revalidation/a90ctl.py

python3 scripts/revalidation/wifi_cnss_start_experiment.py plan \
  --out-dir tmp/wifi/v229-controlled-cnss-start-experiment-plan-test

python3 scripts/revalidation/wifi_cnss_start_experiment.py dry-run \
  --out-dir tmp/wifi/v229-controlled-cnss-start-experiment-dryrun-test

python3 scripts/revalidation/wifi_cnss_start_experiment.py dry-run \
  --out-dir tmp/wifi/v229-controlled-cnss-start-experiment

python3 scripts/revalidation/a90ctl.py --json version

python3 scripts/revalidation/wifi_cnss_start_experiment.py preflight \
  --out-dir tmp/wifi/v229-controlled-cnss-start-experiment-preflight
```

Result:

```text
decision=dry-run-ready pass=True
reason=v229 plan/dry-run graph is ready; no live daemon execution performed

decision=start-only-runtime-gap pass=True
reason=preflight found missing Android runtime execution namespace paths
```

Primary artifact:

```text
tmp/wifi/v229-controlled-cnss-start-experiment/manifest.json
tmp/wifi/v229-controlled-cnss-start-experiment-preflight/manifest.json
```

Preflight summary:

```text
command_count=29
ok_count=23
required_failures=['stat-mnt-system-vendor-bin-cnss-daemon']
runandroid_required_missing=['stat-system-bin-toybox', 'stat-system-vendor-bin-cnss-daemon', 'stat-system-bin-linker64']
active_wifi_warnings=[]
live_daemon_start=False
```

Interpretation:

- `/mnt/system/system/bin/linker64` and `/mnt/system/system/bin/toybox` are visible.
- `/mnt/system/vendor/bin/cnss-daemon` is not visible through the current mounted-system layout.
- Global Android paths such as `/system/bin/linker64` and `/system/vendor/bin/cnss-daemon` are not present in the current native execution namespace.
- Therefore the runner correctly stops before daemon execution with `start-only-runtime-gap`.

## Guardrails Preserved

- Live daemon start requires `--allow-daemon-start --assume-yes`.
- `cnss_diag` remains disabled in v229.
- Scan/connect/link-up/credential/DHCP/routing remain blocked.
- Generic ICNSS unbind/bind and `driver_override` remain blocked.
- Output uses private `EvidenceStore` helpers.

## Current Decision

`start-only-runtime-gap`

This means the host runner and live read-only preflight are working, but the
current native execution namespace is not sufficient to start Android dynamic
binaries directly. It does not authorize Wi-Fi scan/connect.

## Next Step

Plan v230 around a temporary Android execution namespace:

- expose read-only vendor source containing `cnss-daemon`;
- expose `/system/bin/linker64` and `/system/bin/toybox` paths expected by Android ELF execution;
- keep all paths temporary and non-persistent;
- rerun v229 preflight before any daemon start.
