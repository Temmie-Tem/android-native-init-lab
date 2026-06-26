# Native Init V3303 GPU Compute C3 Eye-Confirm Replay USB Absent

## Summary

- Cycle: `V3303`
- Track: GPU visible compute demo C3, operator eye-confirm replay.
- Decision: `v3303-c3-eye-confirm-replay-paused-usb-absent`
- Result: PAUSED before a new C3 replay proof could be collected.
- Device flash: `no`.
- Boot image touched: `none`.
- Current intended resident from last successful validation: `A90 Linux init 0.11.77 (v3303-gpu-compute-c3-kms-probe)`.

## Context

The previous V3303 live validation already proved the device-side C3 path:

- `gpu.c3.kms.result=compute-pattern-presented`
- `gpu.c3.vis.result=compute-pattern-presented-held`
- `gpu.c3.kms.present_rc=0`
- `gpu.c3.kms.snapshot_expected_match_count=16384`
- `gpu.c3.kms.snapshot_mismatch_count=0`
- Post-probe selftest: `fail=0`

GOAL still required operator eye confirmation of the held panel pattern. This iteration attempted to replay the C3
screen with a longer hold window for visual confirmation.

## Evidence

- Worktree was clean before replay work.
- Bridge status initially reported the managed bridge process alive.
- Resident version check returned:
  - `A90 Linux init 0.11.77 (v3303-gpu-compute-c3-kms-probe)`
  - `A90P1 END seq=8 cmd=version rc=0 errno=0 duration_ms=0 flags=0x0 status=ok`
- The subsequent replay attempt hit a host-side socket `BrokenPipeError`.
- Follow-up bridge status reported `bridge_probe=serial-missing`.
- Host USB inventory showed no A90/Samsung USB gadget, no `/dev/serial/by-id`, no `/dev/ttyACM*`, no ADB device, and no NCM interface.
- A 90 second poll found no return of serial, ACM, ADB, A90/Samsung USB device, or NCM.
- Bridge stderr contained `serial disconnected` entries.
- Fault filter over bridge logs matched no KGSL/GMU/ringbuffer/CP/GPU/IOMMU/page-fault pattern; only bridge serial disconnect lines matched the broader diagnostic search.

## Safety

- No flash was attempted.
- No rollback was attempted because the host could not see any USB recovery/native-init endpoint.
- No forbidden partition, power-domain, PMIC, regulator, GDSC, GPIO, panel-init, backlight, or raw partition write was attempted.
- Per no-cascading-bad-flashes discipline, no new experimental image should be flashed until the device is visible again and health-checked.

## Next Step

Restore physical USB visibility or device boot visibility, then re-run bridge/resident health:

```text
python3 workspace/public/src/scripts/revalidation/a90_bridge.py status --json
python3 workspace/public/src/scripts/revalidation/a90ctl.py --input-mode slow --timeout 15 version
python3 workspace/public/src/scripts/revalidation/a90ctl.py --input-mode slow --timeout 20 selftest verbose
```

After health is confirmed, replay the existing V3303 C3 screen for visual confirmation. No rebuild is required.
