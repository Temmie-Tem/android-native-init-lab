# S22+ M34 S8B1A Wide-I2C Beacon Host Build (2026-07-09)

## Verdict

Host build complete. No live flash was performed or authorized.

S8B1A is the next host-only probe after the consumed S8B1 live MISS. It keeps
the S8B1/S7A2 module recipe and changes only the B1 predicate from exact
`/sys/bus/i2c/devices/57-0066` to any `/sys/bus/i2c/devices/*-0066`.

## Why

S8B1 returned `download-beacon-miss-parked-manual-download-required`, so B2/B3/B4
must not proceed. The remaining cheap false-negative to remove is the Android
i2c-adapter-number assumption: Android showed `57-0066`, but native-init may
instantiate the same max77705 client under a different adapter number.

S8B1A tests exactly that without adding configfs, UDC bind, role writes,
descriptors, persistent mounts, or block writes.

## Artifact

Output directory:

```text
workspace/private/outputs/s22plus_native_init/m34_runtime_gadget_split_v0_9/
```

S8B1A AP path:

```text
workspace/private/outputs/s22plus_native_init/m34_runtime_gadget_split_v0_9/S8B1A/odin4/AP.tar.md5
```

Pinned hashes:

```text
S8B1A AP.tar.md5 SHA256: 5c5df5f3fd83adf15c521f4509f90696ba3372e1aee5a79128a29f74a701ceb1
S8B1A padded boot.img SHA256: df3ee853bb84541f9d494a97f9ba3db5d08bda67662782de0868e90c49d22145
S8B1A /init SHA256: 6aec230f27edae8e0070b367bf78d2b074f67a289b378958a36e908bb60bf83e
S8B1A module-list SHA256: c0c35e02fe61a3f6c18c221a9ae2cc1a54aafd38374117fa954dbfa675700998
Template source SHA256: 87f45e212b52e517a078c1af7666924c3a62901918a47f710e06cf28332f4353
Known booting Magisk base boot SHA256: 2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
```

The v0.9 manifest also confirms the consumed S8B1 artifact stayed byte-stable:

```text
S8B1 AP.tar.md5 SHA256: 0bf313cdf24a5f5babc3d0073a1e90686f1b734b6dafdfa548154ef3eac6c2c8
S8B1 padded boot.img SHA256: 4e599087f242fdf2ae6bee1465e0725b60057bad893b665a178bcf87b88b9a20
S8B1 /init SHA256: a1cbc9828a24a7e302bd569de93b4f41e2ceb159130ea373d2ea9c9572f5a20d
```

## Runtime Contract

S8B1A:

- loads the same 86-module S7A2 closure;
- emits the M34 marker with `stage=S8B1A`;
- polls `/sys/class/typec/port0` OR `/sys/bus/i2c/devices/*-0066`;
- requests `reboot(download)` only if the predicate is true;
- parks if the predicate is false.

It does not create a USB gadget, bind UDC, write TypeC role nodes, write EUD
sysfs knobs, mount persistent partitions, write block devices, or start Android.

## Interpretation

If a future S8B1A live run HITs, the consumed S8B1 MISS was likely a bus-number
false negative and the next unit should inspect native-init sysfs naming before
resuming B2.

If a future S8B1A live run MISSes, max77705 did not instantiate anywhere under
`/sys/bus/i2c/devices/*-0066` with the current S7A2 module recipe. The next unit
should stop at module/driver reachability rather than downstream USB behavior.

## Validation

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/build_s22plus_m34_runtime_gadget_split.py \
  workspace/public/src/scripts/revalidation/s22plus_m34_s8b1_beacon_probe_live_gate.py \
  workspace/public/src/scripts/revalidation/analyze_s22plus_m34_s8b1_result.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/build_s22plus_m34_runtime_gadget_split.py --force

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests/test_s22plus_m34_runtime_gadget_split_build.py
```

Result:

```text
build_s22plus_m34_runtime_gadget_split.py --force: OK
tests/test_s22plus_m34_runtime_gadget_split_build.py: Ran 5 tests, OK
```

## Next Gate

No active live authorization exists. A future S8B1A live run requires a fresh
boot-only AGENTS exception, a dedicated fail-closed live helper, pinned S8B1A
hashes, rollback proof, and explicit operator approval.
