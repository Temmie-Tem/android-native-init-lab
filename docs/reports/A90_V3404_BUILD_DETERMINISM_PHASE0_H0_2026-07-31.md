# A90 V3404 Build Determinism Phase 0 H0 Closure

- Date: `2026-07-31`
- Decision: `A90_V3404_BUILD_DETERMINISM_PHASE0_HOST_PASS`
- Scope: host-only audit, isolated A/B builds, artifact comparison
- Device, staging, reboot, flash, or network-to-device action: none

## Frozen reference

The accepted V3404 boot remained byte-identical before and after the unit:

```text
0a8827aeb46e2fb2cdf1e7cf7320626b4b3a43fcdbbff2024d92dcbc088e83d3
```

The effective versioned builder chain contains 171 unique Python modules,
starting at V3404 and ending at V726. Each path and SHA256 is retained in the
private receipt. The selected native-init and helper sources were not edited.

```text
init_v724.c                    88363bfaea42b93cf652b0e5bb5bf2beff88d7ce11595c019e2d4d59529378ba
a90_android_execns_probe.c     d71446bb9073362fa75a263ce7bf20b4eea0279f12f3f494610b4a08346ab635
```

## Isolated execution

The versioned runner rebounded only output variables in fresh child processes.
It did not write the accepted boot path. Failed private attempts `01` and `02`
stopped before compilation because a legacy parser consumed the child
argument. They were not reused. Fresh run `03` fixed child-process argv
isolation and completed both builds.

Environment:

```text
LC_ALL=C
LANG=C
TZ=UTC
Python 3.14.4
aarch64-linux-gnu-gcc 15.2.0
GNU strip 2.46
```

## Golden reproducible profile

Build A and build B match in size and SHA256 for every declared artifact:

```text
boot     66379776  6a190019e1242cf2aa16173f87e7e4f5e4bc20102d1859b0a1857edeb474d230
ramdisk  16545280  ef871b5bf548ee48a539899197182e41550dbc29464e83ed9ad9e43befab91a5
init      1855248  beb44eea342e5a151f66b0379c3fb3872b7c29d61afaa27d3946072975606628
helper    1649904  fa395d3ecb6944a57487f3966948a634596157e4de3fdc39575a2fc502d1ceef
engine    1201512  ffc83e5d7ee373cb8d8c7fb4a6323b04052dbeb196302695d084e3eaa3a3c5ef
```

The reproducible boot and ramdisk are not promoted over the historical
accepted V3404 identity. They are the Phase 0 golden profile for a future flat
builder. Runtime adoption would require a separate candidate identity and
fresh live process.

## Validation

- focused tests: `2/2`;
- Python `py_compile`: pass;
- effective chain uniqueness and terminus: pass;
- accepted boot pin before and after: pass;
- isolated A/B build: pass;
- five-artifact byte identity: pass;
- static AArch64 `file` inspection for init, helper, and engine: pass;
- tracked native-init/helper C diff: none; and
- private artifacts and receipt remain ignored under `workspace/private/`.

## Disposition

Phase 0 closes. The next host-only unit is Phase 1: flatten the effective V3404
builder into one reviewable versioned snapshot and require it to reproduce the
five golden hashes above. This report grants no device authority.
