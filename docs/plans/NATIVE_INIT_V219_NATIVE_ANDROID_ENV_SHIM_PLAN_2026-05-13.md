# v219 Plan: Native Android-Env Shim Plan

## Summary

v219 follows v218 `daemon-dryrun-partial`. The goal is to design the smallest
native Android-environment shim that could support a later controlled CNSS
service experiment without turning native init into a broad Android framework
clone.

This version is planning/modeling only. It must not execute `cnss-daemon`,
`cnss_diag`, Wi-Fi HAL, `wificond`, supplicant, hostapd, rfkill, link-up, scan,
or connect.

- baseline native runtime: `A90 Linux init 0.9.59 (v159)`
- previous result: v218 PASS, `daemon-dryrun-partial`
- planned design output: `docs/reports/NATIVE_INIT_V219_NATIVE_ANDROID_ENV_SHIM_2026-05-13.md`
- optional planner: `scripts/revalidation/wifi_android_env_shim_plan.py`
- evidence input:
  - `tmp/wifi/v216-service-replay-model/manifest.json`
  - `tmp/wifi/v217-icnss-debug-recovery-inventory-native/manifest.json`
  - `tmp/wifi/v218-cnss-daemon-dryrun/manifest.json`
  - `tmp/wifi/v218-cnss-daemon-dryrun-native/manifest.json`
- evidence output: `tmp/wifi/v219-native-android-env-shim`

## Reference Notes

- Android init service execution includes users, groups, capabilities, service
  classes, sockets, property triggers, disabled/oneshot flags, and `ctl.*`
  control. v219 must model only the pieces required for later CNSS testing:
  <https://chromium.googlesource.com/aosp/platform/system/core/+/master/init/README.md>
- Native init already owns PID 1 and should avoid recreating Android framework
  services such as property service, hwservicemanager, servicemanager, zygote,
  SurfaceFlinger, or Wi-Fi framework.
- v218 proves binary visibility is mapped but ELF/library inspection still
  needs a host-visible vendor root or equivalent read-only extraction.
- v217 proves ICNSS writable recovery/debug controls are not approved; reboot is
  the only proven recovery from a broken ICNSS state.

## Required Shim Areas

### Mount / Path Visibility

Required:

- temporary read-only `/vendor` visibility
- `/system/vendor -> /vendor` compatibility for `/system/vendor/bin/cnss-daemon`
- no persistent mount changes
- no bind mount unless a later explicit opt-in plan approves it

Denied:

- mounting `/data`
- exposing `/data/misc/wifi`
- persistent `/vendor` or `/system` remapping
- writable vendor/system mounts

### Property Policy

Required:

- read-only model of required `ro.*`, `persist.*`, and `init.svc.*` properties
- explicit list of properties that can be stubbed for later dry-run

Denied:

- real Android property service recreation in v219
- `setprop ctl.start` / `ctl.restart`
- changing Wi-Fi enablement properties

### Socket / IPC Policy

Required:

- list of sockets or IPC endpoints required by `cnss-daemon`/`cnss_diag`
- classification as absent, shim-able, or Android-framework-only

Denied:

- binder/hwbinder service publication
- hwservicemanager/servicemanager replacement
- QMI/PDR control socket writes before v221+

### User / Group / Capability Policy

Required:

- map `system`, `wifi`, `inet`, `net_admin`, `diag`, `media_rw`, `sdcard_rw`
  requirements to native UID/GID availability
- define whether later experiments run as root with bounded capabilities or as
  emulated Android users

Denied:

- broad `SYS_MODULE` enablement
- persistent passwd/group mutation
- unbounded root network service exposure

### Logging / Evidence Policy

Required:

- redirect daemon stdout/stderr to private evidence files
- collect before/after ICNSS, dmesg, netdev, rfkill, wiphy, firmware path,
  process, and mount state
- redact MAC/serial/credential-like data

Denied:

- saving Wi-Fi credentials
- collecting `/data/misc/wifi`
- world-readable evidence

### Recovery / Rollback Policy

Required:

- timeout and process-group kill for later daemon experiment
- rollback temporary mount/path state
- confirm ACM/NCM control channel survives
- reboot-only recovery policy if ICNSS breaks

Denied:

- repeated ICNSS `bind`/`unbind`
- recovery/debug sysfs writes without a later explicit opt-in safety plan

## Planned Work

Add `scripts/revalidation/wifi_android_env_shim_plan.py`.

The planner should:

- consume v216/v217/v218 manifests
- produce a shim requirement matrix
- classify each requirement as:
  - `available`
  - `shim-required`
  - `host-evidence-required`
  - `blocked`
  - `out-of-scope`
- produce explicit allow/deny lists
- produce v220 gate inputs

## Decision Model

- `shim-plan-ready`
  - required shim scope is bounded enough for v220 gate design.
- `shim-plan-partial`
  - core shim areas are mapped, but ELF/library or property/socket details are
    incomplete.
- `shim-too-wide`
  - required Android compatibility layer is too broad or risky.
- `manual-review-required`
  - evidence conflicts or requirements cannot be classified.

## Validation

Static:

```sh
python3 -m py_compile scripts/revalidation/wifi_android_env_shim_plan.py
git diff --check
python3 - <<'PY'
import sys
sys.path.insert(0, 'scripts/revalidation')
import wifi_android_env_shim_plan
wifi_android_env_shim_plan.validate_no_active_commands()
print('v219 command guard PASS')
PY
```

Planner run:

```sh
python3 scripts/revalidation/wifi_android_env_shim_plan.py \
  --v216-manifest tmp/wifi/v216-service-replay-model/manifest.json \
  --v217-native-manifest tmp/wifi/v217-icnss-debug-recovery-inventory-native/manifest.json \
  --v218-manifest tmp/wifi/v218-cnss-daemon-dryrun/manifest.json \
  --v218-native-manifest tmp/wifi/v218-cnss-daemon-dryrun-native/manifest.json \
  --out-dir tmp/wifi/v219-native-android-env-shim
```

## Acceptance

- No active device command is required.
- The shim matrix has explicit allow and deny lists.
- The plan preserves ACM/NCM rescue control as mandatory.
- The plan does not approve daemon execution by itself.
- The output says whether v220 can upgrade `wififeas gate` with lifecycle and
  shim evidence.

## Next Step

If v219 returns `shim-plan-ready` or `shim-plan-partial`, v220 should implement
Wi-Fi bring-up preflight gate v2. If v219 returns `shim-too-wide`, stop before
active CNSS experiments and reassess whether Wi-Fi requires a larger Android
compatibility layer outside current project scope.
