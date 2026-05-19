# Native Init v389 Enhanced Crash Capture Plan

## Purpose

V388 proved that V387 captured `system-servicemanager` SIGABRT but did not capture enough detail to select the exact AOSP fatal site. V389 adds bounded enhanced crash capture to the existing service-manager `ptrace-lite` path.

The goal is evidence quality, not runtime repair yet.

## Starting Evidence

- V387 approved live: `docs/reports/NATIVE_INIT_V387_APPROVED_LIVE_RESULT_2026-05-20.md`
- V388 triage: `docs/reports/NATIVE_INIT_V388_SERVICEMANAGER_SIGABRT_TRIAGE_2026-05-20.md`
- V388 decision: `servicemanager-sigabrt-triage-needs-enhanced-crash-capture`

Missing evidence from V388:

- abort message.
- selected register values, especially PC/LR/SP and x0-x8.
- bounded stack bytes or stack ASCII summary.
- bounded abort-message/string memory scan.

## Scope

Implement helper v19 and V389 wrappers:

- bump `a90_android_execns_probe` to `v19`.
- keep compact ptrace output mode.
- for crash snapshots, emit selected AArch64 register values from `NT_PRSTATUS`:
  - x0-x8
  - lr/x30
  - sp
  - pc
  - pstate
- scan bounded memory while the tracee is ptrace-stopped:
  - stack at SP, up to 512 bytes.
  - plausible x0-x8 pointer targets, up to 128 bytes each.
- emit only compact ASCII summaries, not raw memory dumps.
- preserve V387 cleanup behavior.

## Non-Goals

V389 must not perform:

- Wi-Fi HAL start.
- Wi-Fi scan/connect/link-up.
- credentials, DHCP, routing, rfkill writes.
- driver bind/unbind or firmware mutation.
- Android partition writes.
- unrestricted memory dumping.
- runtime repair before fatal site mapping.

## Artifacts

Local helper:

```text
tmp/wifi/v389-a90_android_execns_probe-v19/a90_android_execns_probe
```

SHA256:

```text
e3da79dec1c7ca58d3208fb0d9a55ce1411fff7159ab613ff9daf6d6befd3e6d
```

Wrappers:

- `scripts/revalidation/wifi_execns_helper_v19_deploy_preflight.py`
- `scripts/revalidation/wifi_service_manager_start_only_v389_live_runner.py`
- `scripts/revalidation/wifi_v389_deploy_live_executor.py`

## Expected New Fields

```text
capture.crash.regset.nt_prstatus.x0=...
capture.crash.regset.nt_prstatus.x8=...
capture.crash.regset.nt_prstatus.lr=...
capture.crash.regset.nt_prstatus.sp=...
capture.crash.regset.nt_prstatus.pc=...
capture.crash.stack.addr=...
capture.crash.stack.bytes=...
capture.crash.stack.ascii.count=...
capture.crash.reg_x0_scan.bytes=...
```

## Validation Plan

Local/static validation:

1. Build static ARM64 helper.
2. Confirm required marker and enhanced capture strings.
3. Compile V389 wrappers and the V388 triage tool.
4. Run deploy/live/executor plan-only gates.
5. Run no-approval full executor and confirm no device command/mutation/daemon/Wi-Fi action.

Read-only real-device validation before approval:

1. Run deploy preflight and expect `remote-helper-v19` blocker while device still has v18.
2. Run live preflight and expect `helper-v19` blocker.
3. Confirm no daemon start and no Wi-Fi bring-up.
4. Confirm read-only `status` is healthy.

## Approval Phrases

Deploy:

```text
approve v389 deploy execns helper v19 only; no daemon start and no Wi-Fi bring-up
```

Live:

```text
approve v389 service-manager enhanced crash capture only; no Wi-Fi HAL start and no Wi-Fi bring-up
```

## Next Step After Approval

After approved V389 deploy/live, run `wifi_service_manager_sigabrt_triage.py` against the new live manifest. If register and stack evidence are present but abort message remains absent, map PC/LR to known AOSP/libbinder/libbase fatal candidates or add a narrower abort-message capture in the next version.
