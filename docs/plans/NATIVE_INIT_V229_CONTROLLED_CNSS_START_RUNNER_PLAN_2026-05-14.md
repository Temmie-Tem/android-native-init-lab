# v229 Plan: Controlled CNSS Start-Only Runner

## Summary

v229 is the first implementation step after v228 produced
`cnss-start-plan-ready`. It builds an opt-in host/device runner for a bounded
`cnss-daemon` start-only experiment under native init.

The default behavior must remain non-destructive:

- default command mode is dry-run/preflight;
- live daemon start requires explicit `--allow-daemon-start` and confirmation;
- no Wi-Fi scan/connect/link-up/credential/DHCP/routing operation is allowed;
- no persistent Android filesystem, firmware, property, or ICNSS mutation is
  allowed;
- recovery remains reboot-only if daemon/kernel state cannot be restored.

The purpose is to answer one narrow question: can native init start the Android
CNSS user-space daemon briefly, observe it, and stop it without changing Wi-Fi
link state or requiring unsafe kernel reprobe.

## Inputs

v229 must require these prior decisions before any live start attempt:

| version | required decision | role |
| --- | --- | --- |
| v221 | `elf-evidence-ready` | vendor daemon ELF/library dependency evidence |
| v222 | `vendor-root-ready` | native read-only vendor source availability |
| v223 | `reboot-recovery-accepted` | only accepted recovery primitive |
| v224 | `shim-dryrun-ready` | Android-env shim materialization model |
| v225 | `cnss-start-plan-approved` | exposure/security preflight approval |
| v227 | `system-root-ready` | Android core/system library source availability |
| v228 | `cnss-start-plan-ready` | command allowlist, rollback, exposure boundary |

The runner must reject execution if any manifest is missing, stale, unreadable,
or has a mismatched decision.

## Implementation Scope

Add the host-side runner:

```text
scripts/revalidation/wifi_cnss_start_experiment.py
```

Recommended subcommands:

```text
plan       validate v228 plan artifacts only; no bridge/device calls
preflight  collect live read-only native state; no daemon start
dry-run    build exact execution graph and evidence paths; no daemon start
run        opt-in start-only experiment; requires explicit dangerous flags
```

Required flags for `run`:

```text
--allow-daemon-start
--assume-yes
--max-runtime-sec 10
```

Hard limits:

- default runtime: 10 seconds;
- hard max without source edit: 30 seconds;
- no automatic retry loop;
- one daemon start attempt per run;
- `cnss_diag` remains disabled in v229 unless a separate phase flag is added
  later and reviewed.

## Device Execution Shape

Do not expose a free-form root `run` path from the host runner. The script must
construct only known-safe command families from v228 `command-allowlist.json`.

Preferred v229 execution model:

1. host runner validates v228 allowlist and manifests;
2. host runner performs read-only bridge preflight;
3. host runner stages a temporary runtime directory under `/tmp/a90-v229-*` or
   an equivalent ephemeral native path;
4. host runner starts a tightly scoped device helper or exact structured command
   to run `cnss-daemon`;
5. host runner captures process and kernel observations;
6. host runner stops/reaps the process group;
7. host runner captures postflight inventory and emits private evidence.

If an Android dynamic linker/interpreter path such as `/system/bin/linker64` is
not available in the execution namespace, v229 must stop with
`start-only-runtime-gap`. It must not create persistent `/system` or `/vendor`
mutations to force execution.

## Runtime Shim Rules

The runtime shim is temporary and read-only with respect to Android partitions:

- source vendor tree: live native read-only vendor export from v222/v226;
- source system libraries: live native read-only system evidence from v227;
- temporary root/shim path: `/tmp/a90-v229-*` or equivalent ephemeral path;
- library paths must be explicit and recorded;
- property service emulation is not included in v229;
- missing Android sockets/properties are treated as runtime gaps, not reasons to
  mutate system state.

Allowed runtime preparation examples:

- create temporary directories under `/tmp`;
- create temporary symlinks inside the v229 temporary root only;
- read `stat`, `cat`, `/proc`, `/sys`, and mounted read-only evidence paths;
- delete temporary v229 runtime paths on cleanup.

Denied runtime preparation examples:

- persistent writes under `/system`, `/vendor`, `/data`, `/efs`, firmware paths;
- bind mounting over real Android paths;
- ICNSS unbind/bind, `driver_override`, debugfs/sysfs writes;
- property mutation via `setprop`, `ctl.start`, `ctl.restart`, `class_start`;
- `rfkill`, `ip link set wlan* up`, `iw scan/connect`, supplicant/HAL start.

## Preflight Checks

`preflight` must collect and gate at least:

- `version`, `status`, `bootstatus`, `selftest verbose`;
- `wifiinv full` or the current equivalent;
- `kernelinv summary`;
- ICNSS sysfs presence/bound state from the latest read-only inventory command;
- firmware loader path readback and expected rollback value;
- exposure status for ACM/NCM/tcpctl/rshell/broker/netservice;
- `mountsystem ro` availability and vendor/system source path visibility;
- dynamic linker/interpreter path visibility;
- free memory, CPU/GPU temperature, battery/power state;
- longsoak/log path status if active.

Fail closed before daemon start if:

- bridge or broker is unstable;
- ICNSS state is not the known post-reboot baseline;
- firmware path is not the expected rollback value;
- root-control exposure is broader than the v225/v228 boundary;
- a Wi-Fi interface is already up unexpectedly;
- required daemon/interpreter/library source paths are missing.

## Start-Only Observation

During the brief live run, collect:

- daemon pid/process group;
- stdout/stderr transcript;
- native log excerpt;
- kernel log excerpt if available;
- `/proc/<pid>/status`;
- fd list summary;
- maps summary with path redaction if needed;
- pre/post `wifiinv` delta;
- pre/post network interface and rfkill state;
- exit status or stop reason.

`start-only-pass` requires:

- daemon process became observable;
- no scan/connect/link-up/credential path was used;
- no new unexpected WLAN state was activated;
- daemon stopped and reaped cleanly;
- postflight inventory matches allowed deltas.

## Stop and Recovery

Normal cleanup:

1. SIGTERM process group;
2. wait bounded interval;
3. SIGKILL if still alive;
4. reap;
5. verify no `cnss-daemon` or `cnss_diag` remains;
6. remove temporary v229 runtime paths;
7. capture postflight inventory.

Failure cleanup:

- if the process cannot be killed/reaped, set `start-only-reboot-required`;
- if ICNSS/WLAN state changes unexpectedly, set `start-only-reboot-required`;
- if serial/broker control is lost, stop host automation and request operator
  recovery;
- reboot is allowed only after operator acknowledgement, matching v223 policy;
- generic ICNSS unbind/bind remains denied.

## Evidence Output

Use private/no-follow host output helpers. Output path:

```text
tmp/wifi/v229-controlled-cnss-start-experiment/
├── manifest.json
├── preflight.json
├── dry-run-plan.json
├── process-observation.json
├── postflight.json
├── cleanup.json
├── logs/
└── summary.md
```

Manifest decision labels:

- `dry-run-ready`: plan/preflight graph is valid, no live run executed;
- `start-only-pass`: daemon start/observe/stop succeeded safely;
- `start-only-runtime-gap`: Android runtime primitive is missing and no unsafe
  mutation was performed;
- `start-only-reboot-required`: cleanup cannot prove safe restored state;
- `manual-review-required`: evidence drift or unexpected state needs review;
- `start-only-blocked`: prerequisite or safety gate failed before execution.

## Test Plan

Static validation:

```bash
python3 -m py_compile \
  scripts/revalidation/wifi_cnss_start_experiment.py \
  scripts/revalidation/wifi_cnss_start_plan.py \
  scripts/revalidation/a90ctl.py

git diff --check
```

Planner/dry-run validation:

```bash
python3 scripts/revalidation/wifi_cnss_start_experiment.py plan \
  --plan-dir tmp/wifi/v228-controlled-cnss-start-plan \
  --out-dir tmp/wifi/v229-controlled-cnss-start-experiment

python3 scripts/revalidation/wifi_cnss_start_experiment.py dry-run \
  --plan-dir tmp/wifi/v228-controlled-cnss-start-plan \
  --out-dir tmp/wifi/v229-controlled-cnss-start-experiment
```

Live preflight validation:

```bash
python3 scripts/revalidation/wifi_cnss_start_experiment.py preflight \
  --plan-dir tmp/wifi/v228-controlled-cnss-start-plan \
  --out-dir tmp/wifi/v229-controlled-cnss-start-experiment
```

Opt-in live start-only validation, only after preflight PASS:

```bash
python3 scripts/revalidation/wifi_cnss_start_experiment.py run \
  --plan-dir tmp/wifi/v228-controlled-cnss-start-plan \
  --out-dir tmp/wifi/v229-controlled-cnss-start-experiment \
  --max-runtime-sec 10 \
  --allow-daemon-start \
  --assume-yes
```

Regression checks after any live run:

- bridge/broker still answers `version`, `status`, `bootstatus`;
- `selftest verbose` has no new FAIL;
- `wifiinv full` has no unexpected active WLAN state;
- exposure status remains within v225/v228 boundary;
- temporary v229 paths are removed;
- if `start-only-reboot-required`, reboot recovery is performed and recorded.

## Acceptance

v229 is accepted when one of these is true:

1. dry-run/preflight PASS proves execution graph and safety gates are ready, with
   no live daemon start; or
2. opt-in run returns `start-only-pass` or `start-only-runtime-gap` with complete
   evidence and no forbidden Wi-Fi activity; or
3. opt-in run returns `start-only-reboot-required`, operator recovery succeeds,
   and the report clearly blocks further Wi-Fi work until reviewed.

`start-only-pass` does not authorize scan/connect. It only unlocks the next
planning step for phase-2 diagnostics or controlled WLAN link preparation.

## Next Work After v229

If v229 passes cleanly, the next candidate is v230:

- evaluate whether `cnss_diag` is needed as a diagnostic-only sidecar;
- decide whether runtime gaps require a minimal Android property/socket shim;
- keep scan/connect blocked until daemon health, exposure, rollback, and
  credential policy are reviewed again.
