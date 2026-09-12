# S22+ CPU/GPU/DDR thermal development profile V2

Status: **H0 implementation; no grant or live temperature proof.**
Target: **SM-S906N / g0q / S906NKSS7FYG8**, G0Q board revision 12.

The bounded successor P390 / `v0.2.0-rc.8` corrects the CPU DT parent path,
adds named GPU and SoC DDR-region measurements, and retains their diagnostic
provenance. It uses the existing [native baseline V2](S22PLUS_NATIVE_BASELINE_V2.md)
owner: admitted P387 N, one distinct P390 E, normal restoration of exact N after
proved E health/timely Download, and the original exact Android A as failure-only
fallback. The user requested preparation through exact F1 approval-code issuance.
That request is not a returned finite grant or an instruction to execute F1.

P387's native byte inputs and artifacts remain unchanged. P389's frozen native
source/profile, artifacts, consumed claim and original run records remain
historical inputs. V2 composes the unchanged V1 battery/driver scaffolding and
resident control platform at explicit source boundaries; it is a new E profile.
This document adds no permanent-boundary exception or standing authority.

## Sensor binding and concrete effects

The actual stock base-plus-r12-overlay trees locate the thermal zones at
`/soc/thermal-zones`. The provider validates the exact root, two TSENS resources,
and each selected zone/provider/sensor join before any corresponding status read.
The selected sensor order is CPU `cpu-1-0..8` at bank 0 IDs 5-13, CPU
`cpu-0-0..3` at bank 1 IDs 1-4, GPU `gpuss-0..1` at bank 0 IDs 14-15, and
`ddr` at bank 1 ID 9. Sample bits 0-12, 13-14 and 15 use that fixed order.
Each CPU bank retains V1's complete CPU-map prerequisite; optional GPU/DDR
mapping failure withholds only the affected optional measurements.

Only VERSION, ENABLE, TRDY and selected status words are read. Each accepted
status joins its VALID bit and signed temperature in one read. There is no
TSENS enable, calibration, reset, threshold or IRQ write, no retry loop, and no
GPU workload. Per-sensor values and masks distinguish valid zero from absence.
CPU/GPU summaries are maxima over available locations with their own coverage.
The DDR label is **SoC DDR region**, never RAM-package or DRAM-die temperature.

The battery path, exact 23-entry table, single processed ADC7 conversion,
one-second acquisition pacing and per-boot ADC fault latch remain V1's surface.
ADC configuration/conversion writes and its existing bounded EOC IRQ/wait are
still explicit effects. No new ADC channel, PMIC/GPIO control, UFS query,
charger driver or fuel-gauge write is added. An internal sample-validation or
format failure also stops further ADC conversions in that boot.

## Diagnostics, private IPC and retained evidence

One `S22THERM2` sample contains 16 signed millidegree values, mapping and valid
masks, battery conversion provenance, and each bank's error and register state.
The bank phase distinguishes an unseen bank, a retained probe snapshot, and
state read during this acquisition. Separate presence bits say whether VERSION,
ENABLE, TRDY and selected status words were actually read. Unread fields are
zero placeholders with clear presence bits, not observed zero register values.
Probe failures remain visible even when no live bank binding was published.

The collector accepts a new increasing sequence acquired after its current
collection start, completed no later than the current BOOTTIME, and within the
existing five-second freshness bound. Missing/invalid samples clear temperature
availability. PID1 keeps the thermal sequence/time high-water marks across such
gaps. Hardware conversion age remains unproved by these software timestamps.

Only E extends the boot-local IPC: `status_metrics` is 304 bytes and
`hud_snapshot` is 656 bytes, with new sample/view magic values. Both E's actual
PID1 helper and renderer/collectors compile the same generated header and exact
validation. N's 128/304-byte IPC stays unchanged. The external authenticated
resident control wire, command list, three child slots, no-respawn behavior,
60-second observer, settling interval, 30-second CONTROL and finite grant limits
remain the existing paths.

The existing 64-record ring and 768-byte record limit are retained. Each frame
has a bounded `RESIDENT_THERMAL_SAMPLE` companion and a
`RESIDENT_THERMAL2_FRAME` record joined by frame and acquisition identities.
Missing companions after ring eviction cannot establish temperature proof;
duplicate, late or conflicting companions are malformed. Retained values,
coverage and diagnostic provenance must agree with the frame. The fixed optional
HUD export retains its existing 50,000-byte decoder bound.

## Completion and preparation

H0 qualification covers the exact merged-DT fixture, original-parent rejection,
partial/missing values, valid zero/negative temperatures, probe/read presence,
ADC fault latch, stale/replayed acquisition and worst-case row sizes. The actual
generated PID1/collector/renderer IPC and N/E/N owner are exercised, including
crossed old/new IPC rejection and temperature unavailability with healthy return.
Actual AArch64 A/B init, renderer and module outputs must agree; source/header,
Image/module import CRC, actual boot-only AP and all published metadata are
rederived by the real readers. Current P387 admission must reopen unchanged.

Independent review covers the changed reachable source/IPC/builder/observer
closure and its higher-precedence interactions before exact F1 code issuance.
Code issuance prepares a reviewable request only. Live use still needs its exact
returned approval, attendance, fresh authenticated N health and current target,
artifact and recovery binding through the existing owner.

Live feature qualification is separate for CPU, GPU, SoC DDR region and battery.
Each needs a fresh accepted value; CPU/GPU coverage remains explicit, including
partial coverage. Missing temperature evidence is `NO_PROOF` for that feature.
It does not repeat E or prevent the policy's normal N restoration after complete
fixed health and timely Download. An unexplained session/transfer failure retains
only the original one-shot A fallback and exact final health. No live outcome
is established by this H0 definition.
