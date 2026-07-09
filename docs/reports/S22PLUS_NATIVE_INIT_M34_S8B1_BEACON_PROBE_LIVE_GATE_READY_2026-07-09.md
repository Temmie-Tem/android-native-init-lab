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
does not insert it. `--live` and `--rollback-from-download` fail closed unless a
fresh active exception is present in `AGENTS.md` and the matching ack token is
passed.

The helper also provides a non-live readiness mode:

```text
--readonly-preflight
```

This mode verifies the S8B1 candidate artifacts and rollback APs, then checks
current Android identity, stability, current boot SHA256, and a host snapshot.
It intentionally skips the `AGENTS.md` active-exception gate because it performs
no reboot, no Odin transfer, no partition write, and no rollback action.

Live and rollback paths also write a machine-readable result file:

```text
result.json
```

Schema:

```text
s22plus_m34_s8b1_result_v1
```

The result file records the final `result`, `rc`, rollback target, optional
rollback Odin endpoint, optional post-rollback Android serial, and the pinned
candidate/base hashes. This is the authoritative host-side summary to classify
B1 after a live run, alongside `timeline.json` and the text log.

Added host-only post-live classifier:

```text
workspace/public/src/scripts/revalidation/analyze_s22plus_m34_s8b1_result.py
```

Usage after a live run:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/analyze_s22plus_m34_s8b1_result.py \
  <run-dir>/result.json \
  --write-report
```

It consumes `result.json` plus sibling `timeline.json` by default. It only marks
the run as B2-ready when the S8B1 result is `download-beacon-hit`, `rc=0`, and
the canonical timeline contains the required live/flash/rollback events. A
clean MISS is classified as a stop before B2: investigate GENI I2C/max77705/
TypeC reachability. Rollback-only, incomplete timeline, nonzero `rc`, or hash
mismatch all fail closed and do not authorize B2.

The S8B1 helper tests now cross-check the helper's own
`record_timeline_event()` + `write_result_summary()` output against the analyzer
for both HIT and MISS, so the next live run's machine-readable evidence path is
tested end-to-end at the host level.

## Validation

Commands run:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/revalidation/s22plus_m34_s8b1_beacon_probe_live_gate.py
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/s22plus_m34_s8b1_beacon_probe_live_gate.py --offline-check
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/s22plus_m34_s8b1_beacon_probe_live_gate.py --readonly-preflight --android-stability-samples 2 --android-stability-interval-sec 1
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/s22plus_m34_s8b1_beacon_probe_live_gate.py --print-agents-exception-draft
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/s22plus_m34_s8b1_beacon_probe_live_gate.py --print-agents-exception-active-template
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
draft exception generation: OK
active-template generation: OK
default run without active AGENTS exception: correctly fails closed
S8B1 tests: Ran 18 tests, OK
S8B1 analyzer tests: Ran 7 tests, OK
S8B1/analyzer evidence-path cross-check: included in S8B1 tests
M34/S7A2/S8B1/analyzer regression: Ran 40 tests, OK
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
workspace/private/runs/s22plus_m34_s8b1_beacon_probe_live_gate_20260709T003315Z/
```

Key rows:

```text
android_stability_result=ok samples=2
current_boot_hash_rc=0
2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e  /dev/block/by-name/boot
android_readonly_preflight=ok device_action=0 agents_exception_checked=0 android_checked=1 current_boot_hash_checked=1
```

## Next Gate

To run live, insert a fresh active SHA-pinned `AGENTS.md` exception generated by:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/s22plus_m34_s8b1_beacon_probe_live_gate.py --print-agents-exception-active-template
```

Then, only after explicit operator approval, run one attended `--live` pass with
the live ack token. Without that exception and approval, S8B1 remains host-only
prepared.
