# S22+ M34 S8B1A Wide-I2C Beacon Live Gate Ready (2026-07-09)

## Verdict

Host-side live-gate preparation is complete. No live flash was performed by this
unit, and no active `AGENTS.md` live authorization was inserted.

The operator separately observed that the device is not in a bootloop. Current
read-only ADB prelive packet generation also passed on Android serial
`<S22_SERIAL_REDACTED>`.

## Helper

Added fail-closed S8B1A helper:

```text
workspace/public/src/scripts/revalidation/s22plus_m34_s8b1a_wide_i2c_beacon_live_gate.py
```

Added post-run analyzer:

```text
workspace/public/src/scripts/revalidation/analyze_s22plus_m34_s8b1a_result.py
```

Added tests:

```text
tests/test_s22plus_m34_s8b1a_wide_i2c_beacon_live_gate.py
tests/test_analyze_s22plus_m34_s8b1a_result.py
```

## Pinned Artifact

S8B1A AP:

```text
workspace/private/outputs/s22plus_native_init/m34_runtime_gadget_split_v0_9/S8B1A/odin4/AP.tar.md5
```

Pinned hashes:

```text
AP.tar.md5 SHA256: 5c5df5f3fd83adf15c521f4509f90696ba3372e1aee5a79128a29f74a701ceb1
padded boot.img SHA256: df3ee853bb84541f9d494a97f9ba3db5d08bda67662782de0868e90c49d22145
/init SHA256: 6aec230f27edae8e0070b367bf78d2b074f67a289b378958a36e908bb60bf83e
module-list SHA256: c0c35e02fe61a3f6c18c221a9ae2cc1a54aafd38374117fa954dbfa675700998
template source SHA256: 87f45e212b52e517a078c1af7666924c3a62901918a47f710e06cf28332f4353
known-booting Magisk boot SHA256: 2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
```

## Runtime Contract

S8B1A keeps the consumed S8B1/S7A2 module recipe fixed and changes only the B1
predicate:

```text
/sys/class/typec/port0 exists OR any /sys/bus/i2c/devices/*-0066 exists
```

If true, the candidate requests `reboot(download)` and the host classifies a
new Odin endpoint as `download-beacon-hit`. If false, the candidate parks and
the host classifies the bounded observation window as
`download-beacon-miss-parked-manual-download-required`.

S8B1A still performs no configfs setup, no UDC bind, no TypeC role write, no
ssusb role write, no FunctionFS, no stock composite, no Android/Magisk handoff,
no persistent partition mount, and no block write.

## Read-Only Packet

Generated and verified prelive packet:

```text
workspace/private/runs/s22plus_m34_s8b1a_wide_i2c_beacon_live_gate_20260709T083307Z/s22plus_m34_s8b1a_prelive_packet.json
```

Verifier log:

```text
workspace/private/runs/s22plus_m34_s8b1a_wide_i2c_beacon_live_gate_20260709T083333Z/s22plus_m34_s8b1a_wide_i2c_beacon_live_gate.txt
```

The packet captures the pinned artifact paths/hashes, selected serial, Android
stability check, current boot hash, Android S8B1A predicate baseline, reset
context baseline, active exception template, and live runbook material hashes.
It performs no reboot, no Odin transfer, no partition write, and no AGENTS
modification.

## Next Gate

A future live run still requires a fresh narrow boot-only `AGENTS.md` active
exception generated from this helper, exact candidate verification, default
dry-run pass, and explicit operator approval.

## Validation

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/s22plus_m34_s8b1a_wide_i2c_beacon_live_gate.py \
  workspace/public/src/scripts/revalidation/analyze_s22plus_m34_s8b1a_result.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests/test_s22plus_m34_s8b1a_wide_i2c_beacon_live_gate.py \
  tests/test_analyze_s22plus_m34_s8b1a_result.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m34_s8b1a_wide_i2c_beacon_live_gate.py --offline-check

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests/test_s22plus_m34_s8b1_beacon_probe_live_gate.py \
  tests/test_analyze_s22plus_m34_s8b1_result.py \
  tests/test_s22plus_m34_runtime_gadget_split_build.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m34_s8b1a_wide_i2c_beacon_live_gate.py \
  --prelive-packet --serial <S22_SERIAL_REDACTED>

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m34_s8b1a_wide_i2c_beacon_live_gate.py \
  --verify-prelive-packet \
  workspace/private/runs/s22plus_m34_s8b1a_wide_i2c_beacon_live_gate_20260709T083307Z/s22plus_m34_s8b1a_prelive_packet.json \
  --serial <S22_SERIAL_REDACTED>
```

Result:

```text
S8B1A py_compile: OK
S8B1A helper/analyzer tests: Ran 62 tests, OK
S8B1A offline-check: OK
S8B1/S8B1 analyzer/build regression tests: Ran 67 tests, OK
S8B1A prelive-packet: OK
S8B1A verify-prelive-packet: OK
```
