# S22+ M34 S8B1 Beacon-Probe Live Runbook (2026-07-09)

This document is inert. It does not authorize a live flash, does not insert an
`AGENTS.md` exception, and does not replace the helper gates. It pins the latest
no-write prelive packet and the operator-facing sequence for the next S8B1
live gate if the operator later gives explicit live approval.

## Scope

Target:

```text
SM-S906N/g0q/S906NKSS7FYG8
```

Helper:

```text
workspace/public/src/scripts/revalidation/s22plus_m34_s8b1_beacon_probe_live_gate.py
```

Live ack:

```text
S22PLUS-M34-S8B1-BEACON-PROBE-LIVE-GATE
```

Rollback ack:

```text
S22PLUS-M34-S8B1-BEACON-PROBE-ROLLBACK-FROM-DOWNLOAD
```

## Pinned Packet

Latest no-write packet:

```text
workspace/private/runs/s22plus_m34_s8b1_beacon_probe_live_gate_20260709T031713Z/s22plus_m34_s8b1_prelive_packet.json
```

Packet sidecars:

```text
workspace/private/runs/s22plus_m34_s8b1_beacon_probe_live_gate_20260709T031713Z/s22plus_m34_s8b1_live_runbook.txt
workspace/private/runs/s22plus_m34_s8b1_beacon_probe_live_gate_20260709T031713Z/s22plus_m34_s8b1_active_exception_template.txt
workspace/private/runs/s22plus_m34_s8b1_beacon_probe_live_gate_20260709T031713Z/s22plus_m34_s8b1_android_predicate_baseline.json
workspace/private/runs/s22plus_m34_s8b1_beacon_probe_live_gate_20260709T031713Z/s22plus_m34_s8b1_android_reset_context_baseline.json
```

Pinned hashes:

```text
prelive packet                 d5a7b0e4cea4b0a84015a22959b864f47b156e08b062177c556e69f68f21c08d
live runbook                   84da9aa90905f3ee7c420159a922a67743528286b0c8f0f13dc72b5cf5a93781
active exception template       66f1e39a3a01da4be3b100c899fd39c553cf31a014fa47532973daf5e2e8ac8f
Android predicate baseline      6bb78214e3cf91b10ba259902a21d46fdf50464d27c497d37c4720057f284ee2
Android reset-context baseline  d8b3c2c1e43ca0ad78cf20a495ae94fb1eed3f94a58267c26e9a798a2d848883
```

The packet embeds the same sidecar hashes under `material_sha256`; the verifier
recomputes them and rejects drift.

Verify the pinned packet before any live authorization work:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m34_s8b1_beacon_probe_live_gate.py \
  --verify-prelive-packet \
  workspace/private/runs/s22plus_m34_s8b1_beacon_probe_live_gate_20260709T031713Z/s22plus_m34_s8b1_prelive_packet.json
```

Expected result:

```text
verify-prelive-packet ok: packet matches current S8B1 helper contract, selected_serial=RFCT519XWGK; no device action
```

## Current Baselines

Android baseline from the packet:

```text
selected_serial=RFCT519XWGK
predicate=/sys/class/typec/port0 OR /sys/bus/i2c/devices/57-0066
/sys/bus/i2c/devices/57-0066 exists
/sys/class/typec/port0 absent
predicate_true=1
```

Future B2 hints captured from stock Android:

```text
/sys/devices/platform/soc/994000.i2c/i2c-57/57-0066/max77705-usbc/typec/port0 exists
/sys/devices/platform/soc/994000.i2c/i2c-57/57-0066/max77705-usbc/typec/port0/port0-partner exists
data_role=host [device]
power_role=source [sink]
port_type=[dual] source sink
power_operation_mode=1.5A
partner supports_usb_power_delivery=no
partner usb_power_delivery_revision=0.0
partner accessory_mode=none
```

Reset-context baseline from the packet:

```text
ro.boot.bootreason=reboot,download
/proc/reset_reason=MPON
/proc/reset_rwc=41
/proc/store_lastkmsg=1
reset_history_pmic_abnormal_count=10
reset_history_upload_cause_count=10
```

## Live Semantics

S8B1 keeps the S7A2 module recipe fixed and reads exactly one predicate after
module load:

```text
/sys/class/typec/port0 exists OR /sys/bus/i2c/devices/57-0066 exists
```

True branch:

```text
reboot(download)
host-visible result = download-beacon-hit
```

False branch:

```text
park
host-visible result = download-beacon-miss-parked-manual-download-required
```

The live helper treats a new Odin Download endpoint after the original Download
endpoint disconnects as the HIT proof. If no new Odin endpoint appears during
the bounded observation window, the device is expected to require manual
Download-mode rollback.

## Operator Sequence

The exact command sequence is stored in:

```text
workspace/private/runs/s22plus_m34_s8b1_beacon_probe_live_gate_20260709T031713Z/s22plus_m34_s8b1_live_runbook.txt
```

Use that file as the source of truth for the command lines. Its phases are:

```text
1. no-write readonly-preflight
2. print active AGENTS.md exception template for manual review/insertion
3. default dry-run after AGENTS.md contains the active exception
4. live gate with explicit live ack
5. fallback rollback-from-download only if live exits after MISS without rollback
6. analyzer gates on the live result.json
```

The default dry-run/live gate requires `AGENTS.md` to contain the exact
helper-generated active-template text, not only all marker strings. If the
template is manually edited while retaining the markers, the helper must fail
closed before live.

The planned run directories are intentionally distinct:

```text
preflight: workspace/private/runs/s22plus_m34_s8b1_beacon_probe_live_gate_20260709T031713Z_live_preflight
template:  workspace/private/runs/s22plus_m34_s8b1_beacon_probe_live_gate_20260709T031713Z_live_template
dryrun:    workspace/private/runs/s22plus_m34_s8b1_beacon_probe_live_gate_20260709T031713Z_live_dryrun
live:      workspace/private/runs/s22plus_m34_s8b1_beacon_probe_live_gate_20260709T031713Z_live
rollback:  workspace/private/runs/s22plus_m34_s8b1_beacon_probe_live_gate_20260709T031713Z_live_rollback
```

Do not create these planned directories casually before the live approval flow:
the packet verifier intentionally checks that they are not already stale.

## Interpretation

Analyze only the live run result as B1 proof:

```text
workspace/private/runs/s22plus_m34_s8b1_beacon_probe_live_gate_20260709T031713Z_live/result.json
```

The fallback rollback result is cleanup evidence, not B1 proof:

```text
workspace/private/runs/s22plus_m34_s8b1_beacon_probe_live_gate_20260709T031713Z_live_rollback/result.json
```

Use:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/analyze_s22plus_m34_s8b1_result.py \
  workspace/private/runs/s22plus_m34_s8b1_beacon_probe_live_gate_20260709T031713Z_live/result.json \
  --write-report
```

Decision rules:

```text
download-beacon-hit + clean Magisk rollback + required timeline = B1 proved; S8B2 design may proceed.
download-beacon-hit + stock fallback rollback = B1 proved, but not next-live-ready until Magisk baseline is restored.
download-beacon-miss-parked-manual-download-required = B1 failed; stop before B2.
rollback-only/no-proof/ambiguous timeline = stop; do not infer B1.
PMIC/RDX abnormal reset before the observation window = fail, not HIT.
```

## Forbidden During This Run

- no recovery, vendor_boot, dtbo, vbmeta, vbmeta_system, BL, CP, CSC, super,
  persist, userdata, EFS, sec_efs, RPMB, keymaster, modem, bootloader, or any
  non-boot partition action;
- no raw host `dd`;
- no fastboot;
- no Magisk module install;
- no multidisabler;
- no format data;
- no TypeC role-node write;
- no ssusb role-node write;
- no configfs gadget setup;
- no UDC bind;
- no charge-current, OTG/VBUS boost, regulator, GDSC, GPIO, display, raw PMIC,
  or EUD sysfs write;
- no S1/S2/S3/S4/S5/S6/S7A/S7A2 repeat under this gate;
- no B2/B3/B4, descriptor/composition pivot, FunctionFS, stock composite,
  display/distro candidate, kernel rebuild, or RDX PC dump retrieval under this
  gate.

## Current Status

As of this document, `AGENTS.md` has no active S8B1 exception. The next live
step remains blocked on explicit operator live approval plus active
SHA-pinned exception insertion. Until then, only the packet verifier and other
no-write checks are allowed.
