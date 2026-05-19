# v366 Plan: Guarded Runtime Repair Smoke

- date: `2026-05-20`
- scope: bounded temporary runtime repair smoke runner
- boot image change: none
- native baseline: `A90 Linux init 0.9.61 (v319)`
- prerequisite: V365 `service-runtime-repair-packet-ready`
- approval status: exact approval required before mutation

## Summary

V365 produced a ready repair packet for the Android service runtime gaps found by
V364: missing Binder devnodes, missing `/dev/block/sda29`, private property
runtime requirements, and linkerconfig visibility requirements.

V366 adds the guarded executor for that packet. It is intentionally fail-closed:
plan and preflight are safe, but the real smoke run requires the exact approval
phrase plus explicit mutation flags. Without those, it records evidence and exits
with `runtime-repair-smoke-approval-required` without creating any device node.

V366 still does not start service-manager, Wi-Fi HAL, `wificond`, supplicant,
hostapd, `cnss-daemon`, or `cnss_diag`. It also does not scan, connect, bring up
Wi-Fi, touch rfkill, bind/unbind ICNSS, mutate firmware, or write Android
partitions.

## Implementation

Add guarded runner:

```text
scripts/revalidation/wifi_runtime_repair_smoke.py
```

Modes:

```bash
python3 scripts/revalidation/wifi_runtime_repair_smoke.py \
  --out-dir tmp/wifi/v366-runtime-repair-smoke-plan-20260520-r2 \
  plan

python3 scripts/revalidation/wifi_runtime_repair_smoke.py \
  --out-dir tmp/wifi/v366-runtime-repair-smoke-preflight-20260520 \
  preflight

python3 scripts/revalidation/wifi_runtime_repair_smoke.py \
  --out-dir tmp/wifi/v366-runtime-repair-smoke-refusal-20260520 \
  run
```

The approved path is intentionally not the default. It requires all of:

```text
--approval-phrase "approve v366 bounded runtime repair smoke only; no service-manager start and no Wi-Fi bring-up"
--apply
--assume-yes
```

## Approval Boundary

Exact phrase:

```text
approve v366 bounded runtime repair smoke only; no service-manager start and no Wi-Fi bring-up
```

Only after that exact phrase is supplied may the runner perform this bounded
sequence:

1. create temporary `/dev/block/sda29` from verified `/proc/partitions` metadata
   `259:13`;
2. create temporary `/dev/binder`, `/dev/hwbinder`, `/dev/vndbinder` from known
   misc major/minor values;
3. run `/cache/bin/a90_android_execns_probe` in property lookup mode using the
   private property root from V317/V320;
4. cleanup temporary nodes in a `finally` block;
5. verify no service-manager/CNSS process and no Wi-Fi link surface remains.

## Guardrails

Forbidden in V366:

- service-manager, `hwservicemanager`, or `vndservicemanager` execution;
- Wi-Fi HAL, `wificond`, supplicant, hostapd, `cnss-daemon`, or `cnss_diag`
  execution;
- Wi-Fi scan/connect/link-up/credential/DHCP/routing;
- rfkill unblock, ICNSS bind/unbind, module load/unload, or firmware mutation;
- Android partition writes;
- approved mutation without the exact phrase and both mutation flags.

## Validation

Required before commit:

```bash
python3 -m py_compile scripts/revalidation/wifi_runtime_repair_smoke.py
python3 scripts/revalidation/wifi_runtime_repair_smoke.py \
  --out-dir tmp/wifi/v366-runtime-repair-smoke-plan-20260520-r2 \
  plan
python3 scripts/revalidation/wifi_runtime_repair_smoke.py \
  --out-dir tmp/wifi/v366-runtime-repair-smoke-preflight-20260520 \
  preflight
python3 scripts/revalidation/wifi_runtime_repair_smoke.py \
  --out-dir tmp/wifi/v366-runtime-repair-smoke-refusal-20260520 \
  run
git diff --check
```

Expected decisions:

- plan: `runtime-repair-smoke-plan-ready`
- preflight: `runtime-repair-smoke-preflight-ready`
- no-approval run: `runtime-repair-smoke-approval-required`

## Acceptance

- V365 packet is consumed and checked.
- Plan mode does not require live mutation inputs and performs no live command.
- Preflight confirms the current device is ready for a future approved bounded
  smoke.
- No-approval `run` returns PASS with `runtime-repair-smoke-approval-required`
  and no mutation steps.
- Approved smoke is not executed until the exact phrase is provided.
