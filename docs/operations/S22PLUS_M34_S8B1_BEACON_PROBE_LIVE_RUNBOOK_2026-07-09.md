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
workspace/private/runs/s22plus_m34_s8b1_beacon_probe_live_gate_20260709T041315Z/s22plus_m34_s8b1_prelive_packet.json
```

Packet sidecars:

```text
workspace/private/runs/s22plus_m34_s8b1_beacon_probe_live_gate_20260709T041315Z/s22plus_m34_s8b1_live_runbook.txt
workspace/private/runs/s22plus_m34_s8b1_beacon_probe_live_gate_20260709T041315Z/s22plus_m34_s8b1_active_exception_template.txt
workspace/private/runs/s22plus_m34_s8b1_beacon_probe_live_gate_20260709T041315Z/s22plus_m34_s8b1_android_predicate_baseline.json
workspace/private/runs/s22plus_m34_s8b1_beacon_probe_live_gate_20260709T041315Z/s22plus_m34_s8b1_android_reset_context_baseline.json
```

Pinned hashes:

```text
prelive packet                 fd754158459b78f4b2e6ae5b136b5d53ac05cdb3c7c72b83a483da742509e2b1
live runbook                   e3b7e41ec26fdfb03f38142a32d0a4917f5e24088e3b78c7f7cf1084142d96ec
active exception template       66f1e39a3a01da4be3b100c899fd39c553cf31a014fa47532973daf5e2e8ac8f
Android predicate baseline      ede39a5ab7e5cd6c674a86efcb28e7035f8530fa1d2f261592032ee5e949806e
Android reset-context baseline  325d8803548c5b37bbe5b9e22d641c9eebb3cc170ff877b6e99504e85e49ab1c
```

The packet embeds the same sidecar hashes under `material_sha256`; the verifier
recomputes them and rejects drift.

The pinned packet was verified before the dry-run created its planned dry-run
directory:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m34_s8b1_beacon_probe_live_gate.py \
  --verify-prelive-packet \
  workspace/private/runs/s22plus_m34_s8b1_beacon_probe_live_gate_20260709T041315Z/s22plus_m34_s8b1_prelive_packet.json
```

Expected result:

```text
verify-prelive-packet ok: packet matches current S8B1 helper contract, selected_serial=RFCT519XWGK; no device action
```

Do not rerun this verifier after the dry-run unless a fresh packet is generated:
the verifier intentionally fails once any planned phase directory already
exists. Stored verifier evidence for this packet is in:

```text
workspace/private/runs/s22plus_m34_s8b1_beacon_probe_live_gate_20260709T041315Z_packet_verify/
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

Readonly-preflight refresh at `2026-07-09T03:24:42Z` confirmed the same live
input conditions remain true: `android_stability_result=ok`, current boot hash
matches the known Magisk baseline, `/sys/bus/i2c/devices/57-0066` exists,
`/sys/class/typec/port0` is absent, and the future B2 hint path
`/sys/devices/platform/soc/994000.i2c/i2c-57/57-0066/max77705-usbc/typec/port0`
with `port0-partner` still exists. Reset context remained
`ro.boot.bootreason=reboot,download`, `/proc/reset_reason=MPON`,
`/proc/reset_rwc=41`, and `/proc/store_lastkmsg=1`.

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
workspace/private/runs/s22plus_m34_s8b1_beacon_probe_live_gate_20260709T041315Z/s22plus_m34_s8b1_live_runbook.txt
```

Use that file as the source of truth for the command lines. Its phases are:

```text
1. no-write readonly-preflight
2. print active AGENTS.md exception template for manual review
3. generate a full AGENTS.md candidate without replacing the repo file
4. no-write verify-agents-candidate on the reviewed full AGENTS.md candidate
5. default dry-run after AGENTS.md contains the active exception
6. live gate with explicit live ack
7. fallback rollback-from-download only if live exits after MISS without rollback
8. analyzer gates on the live result.json
```

The default dry-run/live gate requires `AGENTS.md` to contain the exact
helper-generated active-template text, not only all marker strings. If the
template is manually edited while retaining the markers, the helper must fail
closed before live.
Print-only helper modes such as `--print-live-runbook` and
`--print-agents-exception-active-template` verify artifacts through a temporary
log and must not create the requested `--run-dir` or any planned phase
directory.
The `--write-agents-candidate <path>` mode generates a full candidate
`AGENTS.md` by inserting the exact active S8B1 exception before the consumed
M34 S7A2 block. It refuses to write repo `AGENTS.md` directly, refuses to
overwrite an existing candidate, and must not create the requested `--run-dir`,
call ADB, reboot, or flash.
The `--verify-agents-candidate <path>` mode verifies a reviewed full AGENTS
candidate file before replacing the repo file. It also uses a temporary log and
must not create the requested `--run-dir`, call ADB, reboot, flash, or edit
`AGENTS.md`.

Latest generated and verified candidate:

```text
workspace/private/runs/s22plus_m34_s8b1_agents_candidate_20260709T035315Z/AGENTS.candidate.md
sha256=0186b2dc881ba1a35565bc34e98c8283513d7fd0fc6aae3c000a88c3f1bbdf48
```

The planned run directories are intentionally distinct:

```text
preflight: workspace/private/runs/s22plus_m34_s8b1_beacon_probe_live_gate_20260709T041315Z_live_preflight
template:  workspace/private/runs/s22plus_m34_s8b1_beacon_probe_live_gate_20260709T041315Z_live_template
dryrun:    workspace/private/runs/s22plus_m34_s8b1_beacon_probe_live_gate_20260709T041315Z_live_dryrun
live:      workspace/private/runs/s22plus_m34_s8b1_beacon_probe_live_gate_20260709T041315Z_live
rollback:  workspace/private/runs/s22plus_m34_s8b1_beacon_probe_live_gate_20260709T041315Z_live_rollback
```

The packet verifier checked these planned directories before dry-run. The
latest dry-run directory now exists by design; the live directory must remain
uncreated until the attended live command consumes it.

## Interpretation

Analyze only the live run result as B1 proof:

```text
workspace/private/runs/s22plus_m34_s8b1_beacon_probe_live_gate_20260709T041315Z_live/result.json
```

The fallback rollback result is cleanup evidence, not B1 proof:

```text
workspace/private/runs/s22plus_m34_s8b1_beacon_probe_live_gate_20260709T041315Z_live_rollback/result.json
```

Use:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/analyze_s22plus_m34_s8b1_result.py \
  workspace/private/runs/s22plus_m34_s8b1_beacon_probe_live_gate_20260709T041315Z_live/result.json \
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

Repo `AGENTS.md` now matches the verified S8B1 full candidate byte-for-byte
and `--verify-agents-candidate AGENTS.md` passes with exact active-template
coverage. The latest default no-live dry-run also passed in:

```text
workspace/private/runs/s22plus_m34_s8b1_beacon_probe_live_gate_20260709T041315Z_live_dryrun/
```

That dry-run verified artifacts, Android stability, current Magisk boot hash,
the active `AGENTS.md` exception, the S8B1 Android predicate baseline, and the
future B2 hint path. It performed no Odin transfer, reboot, live flash, or
rollback.

The latest packet verifier ran before this dry-run and passed in
`workspace/private/runs/s22plus_m34_s8b1_beacon_probe_live_gate_20260709T041315Z_packet_verify/`.
Since the planned dry-run directory now exists, do not rerun that same packet
verifier expecting all planned phase directories to be empty unless another
fresh packet is generated. The planned live directory remains uncreated.

The next live step remains blocked on explicit operator live approval and the
live ack token. Until then, only no-write checks, dry-run checks, and report
updates are allowed.
