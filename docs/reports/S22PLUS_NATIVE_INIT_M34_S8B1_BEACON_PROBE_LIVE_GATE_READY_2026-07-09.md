# S22+ M34 S8B1 Download-Beacon Probe Live Gate Ready (2026-07-09)

Host-side live-gate preparation only. No S22+ live flash is authorized by this
report.

## Helper

Added fail-closed helper:

```text
workspace/public/src/scripts/revalidation/s22plus_m34_s8b1_beacon_probe_live_gate.py
```

Added tests:

```text
tests/test_s22plus_m34_s8b1_beacon_probe_live_gate.py
```

The helper pins the S8B1 host-built artifact from:

```text
workspace/private/outputs/s22plus_native_init/m34_runtime_gadget_split_v0_8/S8B1/odin4/AP.tar.md5
```

Pinned S8B1 hashes:

```text
AP.tar.md5 SHA256: 0bf313cdf24a5f5babc3d0073a1e90686f1b734b6dafdfa548154ef3eac6c2c8
padded boot.img SHA256: 4e599087f242fdf2ae6bee1465e0725b60057bad893b665a178bcf87b88b9a20
/init SHA256: a1cbc9828a24a7e302bd569de93b4f41e2ceb159130ea373d2ea9c9572f5a20d
module-list SHA256: c0c35e02fe61a3f6c18c221a9ae2cc1a54aafd38374117fa954dbfa675700998
template source SHA256: 35978182a80e0502a0aec89ec66e35ca378ebbb3b7c58c573ad0e8ff55cc248d
preserved kernel SHA256: bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff
known-booting Magisk boot SHA256: 2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
```

Ack tokens:

```text
live: S22PLUS-M34-S8B1-BEACON-PROBE-LIVE-GATE
rollback: S22PLUS-M34-S8B1-BEACON-PROBE-ROLLBACK-FROM-DOWNLOAD
```

## Live Semantics

S8B1 keeps the S7A2 module recipe fixed, then reads exactly one predicate:

```text
/sys/class/typec/port0 exists OR /sys/bus/i2c/devices/57-0066 exists
```

If true, the candidate requests `reboot(download)`. The helper interprets a new
Odin Download endpoint after the original candidate-flash Download endpoint
disconnects as:

```text
download-beacon-hit
```

If no new Odin endpoint appears during the bounded observation window, the
helper records:

```text
download-beacon-miss-parked-manual-download-required
```

That MISS path requires manual Download-mode rollback. The helper does not
treat the original Odin endpoint staying connected as proof.

Observer classification is covered by host-only unit tests:

- one new Odin endpoint after the original Download endpoint disconnected is
  `download-beacon-hit`
- no Odin endpoint during the bounded window is
  `download-beacon-miss-parked-manual-download-required`
- more than one Odin endpoint is refused as ambiguous
- ADB returning before rollback is classified as
  `unexpected-adb-before-rollback`

## Safety Contract

The helper verifies the v0.8 manifest before any live action:

- stage is `S8B1`, stage number `9`
- module count is `86`
- module list is the same GENI I2C plus max77705 session-producer closure as
  S7A2
- `i2c-msm-geni.ko` loads before `pdic_max77705.ko`
- `configfs_gadget=0`
- `udc_bind=0`
- `ssusb_mode_peripheral=0`
- `typec_readback=0`
- `role_write_discriminator=0`
- `reboot_request=download`
- `download_beacon=1`
- no configfs gadget setup, no UDC bind, no TypeC role write, no ssusb role
  write, no FunctionFS, no stock composite
- no Android/Magisk handoff, no persistent partition mount, no block write

The helper also prints a draft and active-template `AGENTS.md` exception, but
does not insert it by itself. `--live` and `--rollback-from-download` fail
closed unless a fresh active exception is present in `AGENTS.md` and the
matching ack token is passed. The active-exception gate now requires the exact
helper-generated active-template text to be present in `AGENTS.md`;
marker-complete but edited authorization text is rejected.

The helper also provides a non-live readiness mode:

```text
--readonly-preflight
--prelive-packet
--verify-prelive-packet <json>
--print-live-runbook
--write-agents-candidate <path>
--verify-agents-candidate <path>
```

`--readonly-preflight` verifies the S8B1 candidate artifacts and rollback APs,
then checks current Android identity, stability, current boot SHA256, the
read-only Android S8B1 predicate baseline, the Android reset-context baseline,
and a host snapshot. It intentionally
skips the `AGENTS.md` active-exception gate because it performs no reboot, no
Odin transfer, no partition write, and no rollback action. It refuses the
preflight if both S8B1 probe paths are false on the known-good Android baseline.
It also fails closed if the reset-context collector is not strictly
read-only/no-reboot/no-flash or if the expected Samsung reset fields are absent.

`--print-live-runbook` verifies the same pinned artifacts, then prints the exact
operator command sequence for read-only preflight, active exception review,
full AGENTS candidate generation/verification, post-exception dry-run, live
ack, manual-download rollback, and analyzer gates.
The printed sequence carries any custom candidate, manifest, Odin, rollback,
and run-directory paths supplied to the runbook command. It does not check
`AGENTS.md`, call ADB, reboot, flash, or rollback. The runbook explicitly says
that the live command handles HIT rollback and, on MISS, waits for manual
Download and performs rollback inside the live run directory if Download appears
within the bounded wait. The separate `--rollback-from-download` command is a
fallback only if the live command exits after MISS without rollback, or if the
device is placed in Download mode later.

`--write-agents-candidate <path>` generates a full AGENTS candidate by inserting
the exact helper-generated active S8B1 exception before the consumed M34 S7A2
block. It refuses to write repo `AGENTS.md` directly, refuses to overwrite an
existing candidate, verifies the resulting candidate, and performs no
`AGENTS.md` write, no ADB call, no reboot, no flash, and no requested
`--run-dir` creation.

`--verify-agents-candidate <path>` verifies a reviewed full AGENTS candidate
file before replacing the repo file. It verifies the same pinned artifacts,
checks that the candidate contains the exact helper-generated active S8B1
exception rather than only marker-complete edited text, and performs no
`AGENTS.md` write, no ADB call, no reboot, no flash, and no requested
`--run-dir` creation.

`--prelive-packet` performs the read-only preflight and writes a self-contained
run directory packet:

```text
s22plus_m34_s8b1_prelive_packet.json
s22plus_m34_s8b1_live_runbook.txt
s22plus_m34_s8b1_active_exception_template.txt
```

The packet intentionally does not insert `AGENTS.md` authorization and does not
perform any Odin transfer, reboot, rollback, or partition write. The packet
pins the selected ADB serial into the generated runbook even if `--serial` was
not supplied by the operator, so later dry-run/live commands do not float across
attached devices. The packet
directory is separate from the planned live run directory because `--run-dir`
is created with `exist_ok=False`; the runbook targets distinct not-yet-created
phase sibling directories for preflight, template, dry-run, live, rollback,
and analyzer output so the commands can be run after reviewing the packet. The
packet JSON also records `planned_phase_run_dirs`, `planned_result_json`,
`planned_rollback_result_json`, `android_s8b1_predicate_baseline`,
`android_s8b1_predicate_baseline_json`, `android_reset_context_baseline`,
`android_reset_context_baseline_json`, `runbook_options`, and
`runbook_notes` for machine-readable handoff. It also records
`material_sha256` for the runbook, active exception template, Android predicate
baseline JSON, and Android reset-context baseline JSON. `planned_result_json` is the B1 proof target; the
rollback-only fallback result path is cleanup evidence if that command is needed.
The stored `runbook_options` let later checks replay the exact timing/options
used to generate the live runbook without relying on shell history.

`--verify-prelive-packet <json>` is a no-device/no-write staleness check. It
verifies the packet against current S8B1 constants, artifact paths, active
exception template, generated runbook text, selected serial, stored Android
predicate baseline, stored Android reset-context baseline, stored runbook
options, material hashes, and still-empty planned phase directories. It intentionally skips ADB, Odin transfer, `AGENTS.md`
active-exception checks, reboot, flash, and rollback.

Live and rollback paths also write a machine-readable result file:

```text
result.json
s22plus_m34_s8b1_result_analysis.json
```

Schema:

```text
s22plus_m34_s8b1_result_v1
```

The result file records the final `result`, `rc`, actual rollback target,
actual rollback Odin endpoint, optional post-rollback Android serial, and the
pinned candidate/base hashes. If Magisk rollback falls back to stock, the
result file records `stock` and the fallback Odin endpoint rather than the
original requested target/device. This is the authoritative host-side summary
to classify B1 after a live run, alongside `timeline.json` and the text log.
The helper writes the analysis JSON immediately after `result.json` using the
same fail-closed classifier below, so the run directory carries the current
B1/B2 decision even before a separate post-run command is executed.
The canonical `rollback_flash_done` timeline event is emitted after the final
actual rollback flash attempt, including stock fallback.

Added host-only post-live classifier:

```text
workspace/public/src/scripts/revalidation/analyze_s22plus_m34_s8b1_result.py
```

Usage after a live run:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/analyze_s22plus_m34_s8b1_result.py \
  <run-dir>/result.json \
  --write-report

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/analyze_s22plus_m34_s8b1_result.py \
  <run-dir>/result.json \
  --require-advance

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/analyze_s22plus_m34_s8b1_result.py \
  <run-dir>/result.json \
  --require-live-next-stage
```

It consumes `result.json` plus sibling `timeline.json` by default. It only marks
the run as B2-ready when the S8B1 result is `download-beacon-hit`, `rc=0`, and
the result schema records a valid rollback target plus Android return, the
canonical timeline contains each required live/flash/rollback event exactly
once and in order, and the full timeline has parseable, monotonic UTC
timestamps. A clean MISS is classified as a stop before B2: investigate GENI
I2C/max77705/TypeC reachability. Rollback-only, incomplete, out-of-order,
duplicate-canonical-event, timestamp-regressing timeline, malformed rollback
metadata, nonzero `rc`, or hash mismatch all fail closed and do not authorize
B2.
The analyzer also separates ladder proof from next-live readiness: a HIT with
stock fallback is valid B1 evidence, but `ok_to_live_next_stage` remains false
until the Magisk baseline is restored and verified. The CLI defaults to
classification output, while `--require-advance` and
`--require-live-next-stage` make automation fail nonzero unless the evidence
meets the requested gate. This prevents a clean MISS, rollback-only result,
no-proof timeline, or stock-fallback HIT from being mistaken for next-live
readiness by exit status alone.

The S8B1 helper tests now cross-check the helper's own
`record_timeline_event()` + `write_result_summary()` output against the analyzer
for both HIT and MISS, and assert that `write_result_summary()` emits the
analysis JSON. The next live run's machine-readable evidence path is tested
end-to-end at the host level.

## Validation

Commands run:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/revalidation/s22plus_m34_s8b1_beacon_probe_live_gate.py
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/s22plus_m34_s8b1_beacon_probe_live_gate.py --offline-check
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/s22plus_m34_s8b1_beacon_probe_live_gate.py --readonly-preflight --android-stability-samples 2 --android-stability-interval-sec 1
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/s22plus_m34_s8b1_beacon_probe_live_gate.py --prelive-packet --android-stability-samples 2 --android-stability-interval-sec 0.5
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/s22plus_m34_s8b1_beacon_probe_live_gate.py --verify-prelive-packet workspace/private/runs/s22plus_m34_s8b1_beacon_probe_live_gate_20260709T035730Z/s22plus_m34_s8b1_prelive_packet.json
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/s22plus_m34_s8b1_beacon_probe_live_gate.py --print-live-runbook
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/s22plus_m34_s8b1_beacon_probe_live_gate.py --print-agents-exception-draft
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/s22plus_m34_s8b1_beacon_probe_live_gate.py --print-agents-exception-active-template
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/s22plus_m34_s8b1_beacon_probe_live_gate.py --write-agents-candidate workspace/private/runs/s22plus_m34_s8b1_agents_candidate_20260709T035315Z/AGENTS.candidate.md
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/s22plus_m34_s8b1_beacon_probe_live_gate.py --verify-agents-candidate workspace/private/runs/s22plus_m34_s8b1_agents_candidate_20260709T035315Z/AGENTS.candidate.md
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/s22plus_m34_s8b1_beacon_probe_live_gate.py
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest tests/test_s22plus_m34_s8b1_beacon_probe_live_gate.py
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest tests/test_analyze_s22plus_m34_s8b1_result.py
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest tests/test_s22plus_m34_runtime_gadget_split_build.py tests/test_s22plus_m34_s7a2_geni_i2c_live_gate.py
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest tests/test_s22plus_m34_runtime_gadget_split_build.py tests/test_s22plus_m34_s7a2_geni_i2c_live_gate.py tests/test_s22plus_m34_s8b1_beacon_probe_live_gate.py tests/test_analyze_s22plus_m34_s8b1_result.py
```

Results:

```text
py_compile: OK
offline-check: OK, no device action
readonly-preflight: OK, no reboot/flash/write
prelive-packet: OK, no AGENTS insert/reboot/flash/write
verify-prelive-packet: OK, no device action
live-runbook generation: OK, no device action
draft exception generation: OK
active-template generation: OK
default run without active AGENTS exception: correctly fails closed
S8B1 tests: Ran 40 tests, OK
S8B1 analyzer tests: Ran 20 tests, OK
S8B1/analyzer evidence-path cross-check: included in S8B1 tests
runbook fallback/staleness-contract tests: included in S8B1 tests
Android predicate-baseline tests: included in S8B1 tests
Android reset-context packet tests: included in S8B1 tests
exact active-template authorization tests: included in S8B1 tests
write-agents-candidate tests: included in S8B1 tests
verify-agents-candidate tests: included in S8B1 tests
material-hash staleness tests: included in S8B1 tests
print-only run-dir side-effect tests: included in S8B1 tests
M34/S7A2/S8B1/analyzer regression: Ran 75 tests, OK
post-RDX readonly-preflight with future B2 hints: OK, no reboot/flash/write
post-RDX prelive packet with reset-context baseline: OK, no reboot/flash/write
latest readonly-preflight refresh: OK, no reboot/flash/write
print-live-runbook no requested run-dir side effect: OK
```

## Read-Only Current Device Note

After the operator reported an RDX-to-Download path, host read-only checks saw
the phone back in normal Android/MTP + ADB:

```text
lsusb: 04e8:6860 Samsung Galaxy series, MTP mode
adb serial: RFCT519XWGK device
model/device/build: SM-S906N / g0q / S906NKSS7FYG8
ro.boot.verifiedbootstate: orange
sys.boot_completed: 1
su id: uid=0(root) gid=0(root) context=u:r:magisk:s0
/proc/last_kmsg: missing in this boot
/sys/fs/pstore: missing/empty in this boot
current boot SHA256: 2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
```

This was observation only. No S8B1 live flash or rollback was performed by this
report.

Additional read-only S8B1 preflight component check:

```text
workspace/private/runs/s22plus_m34_s8b1_readonly_preflight_20260709T0027Z/
```

That check ran the same Android identity, stability, current boot hash, and
host-snapshot components used by the live helper after the `AGENTS.md` gate.
Result:

```text
android_stability_result=ok samples=2
current_boot_hash_rc=0
2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e  /dev/block/by-name/boot
```

The committed `--readonly-preflight` mode then passed against the same live
Android baseline:

```text
workspace/private/runs/s22plus_m34_s8b1_beacon_probe_live_gate_20260709T022859Z/
```

Key rows:

```text
android_stability_result=ok samples=2
current_boot_hash_rc=0
2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e  /dev/block/by-name/boot
s8b1_android_predicate_baseline: /sys/bus/i2c/devices/57-0066 exists, /sys/class/typec/port0 absent, predicate_true=1
android_readonly_preflight=ok device_action=0 agents_exception_checked=0 android_checked=1 current_boot_hash_checked=1
```

The predicate baseline matters for interpretation: on the current known-good
Android boot, the S8B1 OR predicate is true because the max77705 I2C device
exists at `/sys/devices/platform/soc/994000.i2c/i2c-57/57-0066`, while
`/sys/class/typec/port0` is absent. Therefore an S8B1 HIT primarily proves the
native-init module path reached the I2C/max77705 chip state, not necessarily
that the TypeC class port was created.

After that observation, the helper was tightened to record future B2 hint
paths in the same read-only baseline JSON. The refreshed preflight passed at:

```text
workspace/private/runs/s22plus_m34_s8b1_beacon_probe_live_gate_20260709T024302Z/
```

The new baseline still has S8B1 predicate true through I2C and class
`/sys/class/typec/port0` absent, but it records the actual Android TypeC
subtree under the max77705 platform device:

```text
/sys/devices/platform/soc/994000.i2c/i2c-57/57-0066/max77705-usbc exists
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

This does not build or authorize S8B2. It only prevents the next design step
from relying on stale `/sys/class/typec/port0` assumptions when the stock
Android path exposes TypeC below `max77705-usbc/typec/port0`.

The latest no-write prelive packet with explicit fallback-rollback notes,
selected-serial pinning, stored runbook options, Android predicate baseline,
Android reset-context baseline, full AGENTS candidate generation/verification
step, and embedded sidecar material hashes is:

```text
workspace/private/runs/s22plus_m34_s8b1_beacon_probe_live_gate_20260709T035730Z/
```

It was verified with `--verify-prelive-packet` at:

```text
workspace/private/runs/s22plus_m34_s8b1_beacon_probe_live_gate_20260709T035851Z/
```

It plans the live B1 proof directory and rollback-only fallback directory
separately:

```text
planned_result_json:
workspace/private/runs/s22plus_m34_s8b1_beacon_probe_live_gate_20260709T035730Z_live/result.json

planned_rollback_result_json:
workspace/private/runs/s22plus_m34_s8b1_beacon_probe_live_gate_20260709T035730Z_live_rollback/result.json
```

The same packet now embeds the reset-context baseline captured by the
read-only reset helper:

```text
ro.boot.bootreason=reboot,download
/proc/reset_reason=MPON
/proc/reset_rwc=41
/proc/store_lastkmsg=1
reset_history_pmic_abnormal_count=10
reset_history_upload_cause_count=10
```

The inert operator-facing runbook index for this packet is:

```text
docs/operations/S22PLUS_M34_S8B1_BEACON_PROBE_LIVE_RUNBOOK_2026-07-09.md
```

It pins the packet and sidecar hashes, summarizes the current Android
predicate/reset baselines, and points to the exact private runbook command
file. It does not itself authorize a live flash or insert `AGENTS.md`.

The helper generated and verified this full candidate `AGENTS.md`, and repo
`AGENTS.md` now matches it byte-for-byte:

```text
workspace/private/runs/s22plus_m34_s8b1_agents_candidate_20260709T035315Z/AGENTS.candidate.md
sha256=0186b2dc881ba1a35565bc34e98c8283513d7fd0fc6aae3c000a88c3f1bbdf48
```

`--verify-agents-candidate AGENTS.md` passes with exact active-template
coverage.

The latest packet was generated after the print-only run-dir side-effect fix
and candidate-writer addition, and confirmed the current Android baseline is
still suitable for the same S8B1 live gate. It did not create any planned live
directories at packet generation time:

```text
android_stability_result=ok samples=2
current boot SHA256: 2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
/sys/bus/i2c/devices/57-0066 exists
/sys/class/typec/port0 absent
predicate_true=1
/sys/devices/platform/soc/994000.i2c/i2c-57/57-0066/max77705-usbc/typec/port0 exists
/sys/devices/platform/soc/994000.i2c/i2c-57/57-0066/max77705-usbc/typec/port0/port0-partner exists
ro.boot.bootreason=reboot,download
/proc/reset_reason=MPON
/proc/reset_rwc=41
/proc/store_lastkmsg=1
```

After the active exception was inserted, the default no-live dry-run passed in:

```text
workspace/private/runs/s22plus_m34_s8b1_beacon_probe_live_gate_20260709T035730Z_live_dryrun/
```

The dry-run verified exact `AGENTS.md` template coverage, artifacts, Android
stability, current boot SHA256
`2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`,
S8B1 predicate true through `/sys/bus/i2c/devices/57-0066`, and the future B2
hint path with `port0-partner`. It performed no Odin transfer, reboot, live
flash, or rollback. Because that dry-run directory now exists, the earlier
prelive packet verifier remains historical pre-dry-run staleness evidence;
generate a fresh packet before expecting empty planned phase directories again.

Latest packet sidecar SHA256s:

```text
s22plus_m34_s8b1_prelive_packet.json: 2b20488162bb630eed0197d426a7c688f3e37f640b11289cc8bae14e81305aa6
s22plus_m34_s8b1_live_runbook.txt: a4a24808320b57409be34e237fcc72ec3ba5c1458177bde65e0813cd88eebada
s22plus_m34_s8b1_active_exception_template.txt: 66f1e39a3a01da4be3b100c899fd39c553cf31a014fa47532973daf5e2e8ac8f
s22plus_m34_s8b1_android_predicate_baseline.json: 73e0473188a9fec9e8485f14c57211f58ded30a96e277e06824e1321374009cb
s22plus_m34_s8b1_android_reset_context_baseline.json: 0488d8cb5d8214d09ddeabe1446fa5ff0c16b46d491425df5e10cfdb54f784b0
```

## Next Gate

To run live, use the runbook command for one attended `--live` pass with
explicit operator approval and ack token
`S22PLUS-M34-S8B1-BEACON-PROBE-LIVE-GATE`. If the same planned run directory
has been consumed by any later non-live experiment, generate a fresh prelive
packet/runbook first so phase directories are clean. Without explicit live
approval and the ack token, S8B1 remains prepared but not executed.
