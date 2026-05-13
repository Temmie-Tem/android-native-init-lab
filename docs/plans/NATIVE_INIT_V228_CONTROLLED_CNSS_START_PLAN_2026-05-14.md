# v228 Plan: Controlled CNSS Start-Only Experiment

## Summary

v228 is the first plan allowed after v225 returned `cnss-start-plan-approved`.
It does **not** perform Wi-Fi scan/connect. It designs a bounded, observable,
start-only experiment for the Qualcomm CNSS user-space daemons under native init.

Current prerequisite state:

- v221: `elf-evidence-ready`
- v222: `vendor-root-ready`
- v223: `reboot-recovery-accepted`
- v224: `shim-dryrun-ready`
- v225: `cnss-start-plan-approved`
- v227: `system-root-ready`

The next implementation must still be opt-in and must stop at daemon start/health
observation. Link-up, scan, connect, credentials, routing, DHCP, and Internet
access remain out of scope.

## Reference Notes

- Android init starts and stops services through service records, `start`,
  `stop`, and class controls; this project should model the original service
  metadata instead of directly launching arbitrary binaries without policy.
  Reference: Android init README, service control semantics:
  https://android.googlesource.com/platform/system/core/+/d12c75f531d1d37d54fdad8007925e031b772117/init/README.md
- AOSP device examples show `cnss_diag` and `cnss-daemon` as Android init
  services, with `cnss-daemon` using `system inet net_admin wifi` group context.
  Reference example, Google Marlin init.common.rc:
  https://android.googlesource.com/device/google/marlin/+/android-7.1.1_r6/init.common.rc
- Linux capabilities split root privilege into per-thread/per-exec privilege
  sets; `NET_ADMIN` must be treated as a high-risk explicit requirement rather
  than an incidental root shell side effect. Reference:
  https://man7.org/linux/man-pages/man7/capabilities.7.html

## Goal

Produce a reviewed v229 implementation plan/tool that can run the smallest
start-only experiment:

1. prepare temporary Android-like runtime aliases and environment;
2. start `cnss-daemon` under bounded command construction;
3. optionally start `cnss_diag` only if `cnss-daemon` is stable;
4. observe process, logs, netlink/kernel symptoms, and Wi-Fi inventory deltas;
5. stop/reap the process or mark reboot as the only recovery if stop fails;
6. generate private evidence.

## Non-Goals

The following are explicitly not allowed in v228/v229 start-only scope:

- `ip link set wlan* up`
- `rfkill unblock`
- `iw scan`, `iw connect`, `wpa_supplicant`, `hostapd`, `wificond`, Wi-Fi HAL
- Wi-Fi credential collection or test-AP password handling
- DHCP, routing, NAT, DNS, or Internet connectivity
- persistent property mutation
- persistent `/system`, `/vendor`, `/data`, `/efs`, or firmware writes
- generic ICNSS unbind/bind or driver_override writes
- automatic reboot without operator acknowledgement

## Candidate v229 Tool Shape

Add a host-side planner/runner pair instead of embedding the first experiment in
PID1:

```text
scripts/revalidation/wifi_cnss_start_plan.py
scripts/revalidation/wifi_cnss_start_experiment.py  # only after plan review
```

Recommended v228 deliverable is the planner only:

```bash
python3 scripts/revalidation/wifi_cnss_start_plan.py \
  --out-dir tmp/wifi/v228-controlled-cnss-start-plan
```

The planner should read:

- `tmp/wifi/v216-service-replay-model/manifest.json`
- `tmp/wifi/v221-host-vendor-elf-library-evidence/manifest.json`
- `tmp/wifi/v222-vendor-root-evidence-export/manifest.json`
- `tmp/wifi/v223-recovery-rollback-policy/manifest.json`
- `tmp/wifi/v224-android-env-shim-materialize/manifest.json`
- `tmp/wifi/v225-exposure-security-gate-v3/manifest.json`
- `tmp/wifi/v227-android-core-system-library-evidence/manifest.json`

Expected planner decision:

- `cnss-start-plan-ready` if all prerequisites still match;
- `manual-review-required` if service metadata, recovery, exposure, or evidence
  changed;
- `start-plan-blocked` if any prerequisite regresses.

## Service Model

From local evidence:

| service | binary | args | user/groups/caps | role |
| --- | --- | --- | --- | --- |
| `cnss-daemon` | `/system/vendor/bin/cnss-daemon` | `-n -l` | `system`, groups `system inet net_admin wifi`, capability `NET_ADMIN` | primary CNSS runtime daemon |
| `cnss_diag` | `/system/vendor/bin/cnss_diag` | `-q -f -t HELIUM` | Android evidence shows system/wifi/inet/sdcard/diag groups; no explicit capability | diagnostics/logging sidecar |

v229 should start only `cnss-daemon` first. `cnss_diag` should remain phase 2 of
the same plan and only run after `cnss-daemon` start-only passes.

## Runtime Shim Requirements

The experiment must not mutate the real Android filesystem. Use temporary native
paths only:

- alias `/system/vendor` and `/vendor` behavior through exported evidence roots
  or temporary mount/symlink tree under `/tmp/a90-v229-*`;
- expose only required read-only vendor/system library trees;
- keep output logs under a private evidence directory or `/mnt/sdext/a90/logs`
  if available;
- set `LD_LIBRARY_PATH` explicitly to the temporary vendor/system lib dirs;
- never read credential paths such as Wi-Fi configs;
- avoid persistent property service emulation in first run.

If the daemon requires Android properties or control sockets, the v229 run must
record the missing primitive and stop. It must not improvise property mutation.

## Preflight Checks

Before any daemon execution, v229 must capture and gate:

- native `version`, `status`, `bootstatus`, `selftest verbose`
- `wifiinv full` or current equivalent
- `kernelinv summary` or latest kernel capability snapshot
- ICNSS bound/present state from v217-compatible read-only inventory
- firmware path readback and expected rollback value
- netservice/rshell/broker exposure status
- v221/v222/v224/v225/v227 decisions
- free memory, CPU/GPU temperature, battery/power state
- log path and longsoak status if active

Fail closed if:

- serial bridge is unstable;
- evidence manifests are missing or stale;
- ICNSS state does not match the known post-reboot baseline;
- firmware path is not the expected rollback value;
- root-control exposure is broader than USB-local/host-local;
- active Wi-Fi interface is already up unexpectedly.

## Start-Only Execution Envelope

The future v229 runner should be bounded by these limits:

- default timeout: 10 seconds for daemon start observation;
- hard maximum: 30 seconds without explicit override;
- process group tracking and kill through existing host/device run controls;
- no automatic retry loop;
- no daemon persistence flag;
- capture stdout/stderr/native log/kmsg excerpts;
- capture process status from `/proc/<pid>/status`, fd list, maps summary, and
  exit status if it terminates;
- capture Wi-Fi inventory before/after and assert no scan/connect occurred.

Allowed command family in v229 must be an explicit allowlist, not free-form
`run` passthrough.

## Stop and Recovery Policy

Normal stop path:

1. send SIGTERM to the daemon process group;
2. wait bounded interval;
3. send SIGKILL if still alive;
4. reap and verify no stale `cnss-daemon` / `cnss_diag` remains;
5. re-run read-only inventory.

Failure path:

- if process cannot be killed/reaped, mark `reboot-required`;
- if ICNSS state changes unexpectedly, mark `reboot-required`;
- if serial bridge is lost, use only already-proven rescue paths;
- reboot is the only accepted recovery primitive from v223;
- do not use generic ICNSS unbind/bind as recovery.

## Evidence Output

Output should use private/no-follow evidence helpers:

```text
tmp/wifi/v228-controlled-cnss-start-plan/
├── manifest.json
├── start-plan.json
├── command-allowlist.json
├── rollback-policy.json
├── exposure-boundary.json
└── summary.md
```

For v229 execution output:

```text
tmp/wifi/v229-controlled-cnss-start-experiment/
├── manifest.json
├── preflight.json
├── postflight.json
├── process-observation.json
├── logs/
└── summary.md
```

## Acceptance for v228

v228 is complete when:

- a start-only plan manifest is generated from current v221-v227 evidence;
- the plan explicitly denies scan/connect/credential paths;
- command allowlist is concrete;
- timeout, stop, and reboot-only recovery are documented;
- no live CNSS daemon execution occurs in v228;
- docs and task queue point to v229 as the first possible opt-in execution step.

## Proposed v229 Outcome Labels

- `start-only-pass`: daemon starts, is observable, and stops cleanly; no active
  Wi-Fi operation occurred.
- `start-only-runtime-gap`: daemon fails because Android runtime primitive is
  missing; no unsafe mutation performed.
- `start-only-reboot-required`: daemon or kernel state cannot be cleanly restored
  without reboot.
- `manual-review-required`: evidence drift, exposure drift, or unexpected state.

## Next Work After v228

If v228 plan is accepted, v229 should implement the planner first and then only
run the start-only experiment after an explicit operator confirmation flag.
Active scan/connect remains v230+ at the earliest and only if v229 is clean.
