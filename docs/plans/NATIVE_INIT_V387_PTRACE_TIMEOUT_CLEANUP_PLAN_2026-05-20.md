# Native Init v387 Ptrace Timeout Cleanup Plan

## Purpose

V387 fixes the cleanup bug exposed by the approved V386 compact ptrace live run. V386 solved the serial output problem, but `system-hwservicemanager` still ended as `start-only-reboot-required` because the timeout cleanup path could treat a ptrace-stopped child as reaped.

The goal is a tighter service-manager start-only proof before any Wi-Fi HAL/start/scan/connect step.

## Starting Evidence

- V386 result report: `docs/reports/NATIVE_INIT_V386_APPROVED_LIVE_RESULT_2026-05-20.md`
- V386 deploy evidence: `tmp/wifi/v386-approved-deploy-serial-20260520-053704/`
- V386 live evidence: `tmp/wifi/v386-approved-live-20260520-054304/`

Key V386 blocker:

```text
service_manager_start.timed_out=1
service_manager_start.reaped=1
service_manager_start.residual_cleared=0
service_manager_start.pgid_scan.before_final_kill.entry.0=pid:1739 state:t comm:hwservicemanage
service_manager_start.pgid_scan.after_final_kill.entry.0=pid:1739 state:Z comm:hwservicemanage
service_manager_start.result=start-only-reboot-required
```

Interpretation: the helper claimed `reaped=1` too early. `WIFSTOPPED` is not a terminal child state and must not be counted as cleanup success.

## Scope

Implement helper v18 and V387 wrappers only:

- bump `a90_android_execns_probe` to `v18`.
- change service-manager `ptrace-lite` timeout cleanup so `WIFSTOPPED` is not treated as reaped.
- on cleanup stops, continue the tracee with the intended termination signal:
  - TERM phase: `PTRACE_CONT(..., SIGTERM)`.
  - KILL phase: `PTRACE_CONT(..., SIGKILL)`.
- only set `service_manager_start.reaped=1` after `WIFEXITED` or `WIFSIGNALED`.
- preserve compact capture and residual PGID evidence.
- add machine-readable cleanup fields for review.

## Non-Goals

V387 must not perform:

- Wi-Fi HAL start.
- Wi-Fi scan/connect/link-up.
- credentials, DHCP, routing, rfkill writes.
- driver bind/unbind or firmware mutation.
- Android partition writes.
- full service-manager runtime bring-up beyond the existing bounded start-only proof.

## Expected New Evidence Fields

```text
service_manager_start.cleanup.term.stop.signal=<signal>
service_manager_start.cleanup.term.stop.event=<event>
service_manager_start.cleanup.term.stop.deliver_signal=15
service_manager_start.cleanup.kill.stop.signal=<signal>
service_manager_start.cleanup.kill.stop.event=<event>
service_manager_start.cleanup.kill.stop.deliver_signal=9
service_manager_start.cleanup_stop_continued=<count>
service_manager_start.cleanup_stop_last_signal=<signal>
service_manager_start.cleanup_continue_errors=<count>
```

Success requires that `service_manager_start.reaped=1` is only emitted after a real terminal wait status.

## Host Tools

- `scripts/revalidation/wifi_execns_helper_v18_deploy_preflight.py`
- `scripts/revalidation/wifi_service_manager_start_only_v387_live_runner.py`
- `scripts/revalidation/wifi_v387_deploy_live_executor.py`

## Validation Plan

Local/static validation:

1. Build static ARM64 helper.
2. Confirm required marker and cleanup strings.
3. Compile V387 Python wrappers.
4. Run plan-only deploy/live/executor gates.
5. Run no-approval full executor and confirm no device command/mutation/daemon/Wi-Fi action.

Read-only real-device validation before approval:

1. Run deploy preflight and expect `remote-helper-v18` blocker while the device still has v17.
2. Run live preflight and expect `helper-v18` blocker.
3. Confirm both preflights report no daemon start and no Wi-Fi bring-up.

Approved live sequence, only after explicit user approval:

1. Deploy helper v18 to `/cache/bin/a90_android_execns_probe`.
2. Run bounded service-manager start-only ptrace cleanup smoke.
3. Review `system-servicemanager` and `system-hwservicemanager` fields.
4. Confirm postflight process surface and Wi-Fi link surface are clean.

## Approval Phrases

Deploy:

```text
approve v387 deploy execns helper v18 only; no daemon start and no Wi-Fi bring-up
```

Live:

```text
approve v387 service-manager ptrace timeout cleanup only; no Wi-Fi HAL start and no Wi-Fi bring-up
```

## Pass Criteria

V387 readiness passes when local static validation, no-approval gates, and read-only preflight blockers are documented.

Approved live can pass only if the helper proves bounded cleanup without treating ptrace stop events as reaped. If `hwservicemanager` still cannot be proven stopped, Wi-Fi remains blocked and the next version must continue lifecycle repair.
