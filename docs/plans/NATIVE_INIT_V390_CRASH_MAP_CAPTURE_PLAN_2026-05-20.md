# Native Init v390 Crash Map Capture Plan

## Purpose

V389 proved that `system-servicemanager` reaches SIGABRT with clean cleanup and now captures selected registers plus bounded memory scans. The remaining gap is attribution: PC/LR point at abort delivery, but the helper does not preserve the `/proc/<pid>/maps` row or file-relative offsets needed to map those addresses to a library and symbol.

V390 adds bounded crash map-row capture for `servicemanager` PC/LR. The goal is symbolization-grade evidence, not runtime repair yet.

## Starting Evidence

- V389 readiness: `docs/reports/NATIVE_INIT_V389_ENHANCED_CRASH_CAPTURE_2026-05-20.md`
- V389 approved live: `docs/reports/NATIVE_INIT_V389_APPROVED_LIVE_RESULT_2026-05-20.md`
- V389 live evidence: `tmp/wifi/v389-approved-live-20260520-062315/`

Key V389 finding:

```text
capture.crash.regset.nt_prstatus.x8=0x00000000000000f0
capture.crash.regset.nt_prstatus.lr=0x0000007f914e5e90
capture.crash.regset.nt_prstatus.pc=0x0000007f914e5ebc
```

`x8=0xf0` maps to AArch64 `rt_tgsigqueueinfo`, so PC/LR are likely in the abort signal-delivery path. V390 must capture map rows and offsets so the next step can decide whether a targeted runtime repair is possible.

## Scope

Implement helper v20 and V390 wrappers:

- bump `a90_android_execns_probe` to `v20`.
- keep compact ptrace output mode.
- for crash snapshots, preserve all v19 fields:
  - x0-x8, lr, sp, pc, pstate.
  - bounded stack scan.
  - bounded register-pointer scans.
- additionally emit map-row evidence for crash PC and LR:
  - matched `/proc/<pid>/maps` row.
  - mapping start/end.
  - mapping permissions.
  - mapping file offset.
  - computed file-relative offset.
  - mapped path.
- keep output bounded and line-oriented.
- preserve V387 cleanup behavior and V389 memory-scan behavior.

## Non-Goals

V390 must not perform:

- Wi-Fi HAL start.
- Wi-Fi scan/connect/link-up.
- credentials, DHCP, routing, rfkill writes.
- driver bind/unbind or firmware mutation.
- Android partition writes.
- unrestricted maps or memory dumping.
- service-manager runtime repair before PC/LR attribution.

## Artifacts

Local helper:

```text
tmp/wifi/v390-a90_android_execns_probe-v20/a90_android_execns_probe
```

SHA256:

```text
44efea328220d37f09d91e4906b7490903d789ef509f0ae2ba74a64049a47171
```

Wrappers:

- `scripts/revalidation/wifi_execns_helper_v20_deploy_preflight.py`
- `scripts/revalidation/wifi_service_manager_start_only_v390_live_runner.py`
- `scripts/revalidation/wifi_v390_deploy_live_executor.py`
- `scripts/revalidation/wifi_service_manager_crash_symbolize.py`

## Expected New Fields

```text
capture.crash.maprow.pc.addr=...
capture.crash.maprow.pc.found=1
capture.crash.maprow.pc.start=...
capture.crash.maprow.pc.end=...
capture.crash.maprow.pc.perms=...
capture.crash.maprow.pc.file_offset=...
capture.crash.maprow.pc.relative_offset=...
capture.crash.maprow.pc.path=...
capture.crash.maprow.pc.line=...
capture.crash.maprow.lr.addr=...
capture.crash.maprow.lr.relative_offset=...
```

## Validation Plan

Local/static validation:

1. Build static ARM64 helper.
2. Confirm required marker and map-row capture strings.
3. Compile V390 wrappers and existing classifier/triage tools.
4. Run host-only symbolizer against V389 evidence and expect `service-manager-crash-symbolization-needs-maprow`.
5. Run deploy/live/executor plan-only gates.
6. Run no-approval full executor and confirm no device command/mutation/daemon/Wi-Fi action.

Read-only real-device validation before approval:

1. Run deploy preflight and expect `remote-helper-v20` blocker while device still has v19.
2. Run live preflight and expect `helper-v20` blocker.
3. Confirm no daemon start and no Wi-Fi bring-up.
4. Confirm read-only `status` is healthy.

## Approval Phrases

Deploy:

```text
approve v390 deploy execns helper v20 only; no daemon start and no Wi-Fi bring-up
```

Live:

```text
approve v390 service-manager crash map capture only; no Wi-Fi HAL start and no Wi-Fi bring-up
```

## Next Step After Approval

After approved V390 deploy/live, parse the new `capture.crash.maprow.pc.*` and `capture.crash.maprow.lr.*` fields. If the mapped library is available from the mounted Android image or extracted artifacts, symbolize the relative offsets and decide whether the next cycle should repair a missing runtime dependency or continue with narrower abort-message capture.
