# Native Init V1141 Post-PM Lower Trace Helper Build Report

Date: `2026-05-27`

## Result

- Decision: `v1141-post-pm-lower-trace-helper-build-pass`
- Pass: `true`
- Source: `stage3/linux_init/helpers/a90_android_execns_probe.c`
- Build gate: `scripts/revalidation/native_wifi_post_pm_lower_trace_helper_build_v1141.py`
- Artifact: `tmp/wifi/v1141-execns-helper-v215-build/a90_android_execns_probe`
- Manifest: `tmp/wifi/v1141-execns-helper-v215-build/manifest.json`
- SHA256: `7bf107db54e4e3b2f9bbee196d40564ab4c62b2de1bcaa392ba843a6a6f3419e`
- Size: `1253872`

## Summary

V1141 is source/build-only. It adds opt-in post-PM lower tracing to the existing
V1139 helper path. The helper version is now:

```text
a90_android_execns_probe v215
```

New explicit allow flag:

```text
--allow-post-pm-mdm-helper-lower-trace
```

This flag is valid only with:

```text
--mode wifi-companion-post-pm-mdm-helper-esoc-observer
--allow-post-pm-mdm-helper-esoc-observer
```

## Implementation

- Added `post_pm_mdm_helper_lower_trace.*` read-only snapshots after post-PM
  `mdm_helper` is observable.
- Captures compact repeated samples of:
  - `/dev/esoc-0` fd count;
  - `/dev/subsys_esoc0` fd count;
  - MHI pipe fd count;
  - `ks` process and MHI pipe command-line evidence;
  - `mdm_helper` thread `wchan` and `/proc/*/syscall` state.
- Adds one final compact fd-link/stall snapshot for `mdm_helper`.
- Allows `ptrace-lite` syscall tracing for `mdm_helper` only when the new lower
  trace flag is explicitly enabled.
- Keeps the default V1139 behavior unchanged unless the new flag is supplied.

## Guardrails

This build did not execute any live device action.

- Deploy: not executed.
- PM/CNSS live actors: not executed.
- `mdm_helper`: not started by this build gate.
- Wi-Fi HAL: not executed.
- Scan/connect/link-up: not executed.
- Credentials: not used.
- DHCP/route/external ping: not executed.
- Partition write/boot image write/flash/reboot: not executed.

The lower trace mode emits explicit safety markers:

```text
post_pm_mdm_helper_lower_trace.subsys_esoc0_open_attempted=0
post_pm_mdm_helper_lower_trace.wifi_hal_start_executed=0
post_pm_mdm_helper_lower_trace.scan_connect_linkup=0
post_pm_mdm_helper_lower_trace.credentials=0
post_pm_mdm_helper_lower_trace.dhcp_routing=0
post_pm_mdm_helper_lower_trace.external_ping=0
```

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_post_pm_lower_trace_helper_build_v1141.py
python3 scripts/revalidation/native_wifi_post_pm_lower_trace_helper_build_v1141.py run
```

The build gate reran:

```bash
bash scripts/revalidation/build_android_execns_probe_helper.sh \
  tmp/wifi/v1141-execns-helper-v215-build/a90_android_execns_probe
```

Build result:

```text
ELF 64-bit LSB executable, ARM aarch64, statically linked, stripped
There is no dynamic section in this file.
```

Required binary markers were present:

```text
a90_android_execns_probe v215
--allow-post-pm-mdm-helper-lower-trace
post_pm_mdm_helper_lower_trace.begin=1
post_pm_mdm_helper_lower_trace.thread_probe
post_pm_mdm_helper_lower_trace.subsys_esoc0_open_attempted=0
```

## Next

V1142 should deploy helper `v215` only, verify remote SHA/version/usage markers,
and keep PM actors, `mdm_helper`, Wi-Fi HAL, scan/connect, credentials, DHCP,
routes, external ping, reboot, flash, and partition writes blocked. After that,
V1143 can run a bounded post-PM lower-trace live gate.
