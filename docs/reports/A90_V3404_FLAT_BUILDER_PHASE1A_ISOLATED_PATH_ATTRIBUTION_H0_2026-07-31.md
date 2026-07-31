# A90 V3404 Flat Builder Phase 1A Isolated Path Attribution H0

- Date: `2026-07-31`
- Decision: `A90_V3404_PHASE1A_ISOLATED_PATH_ATTRIBUTION_PASS`
- Schema: `flat-builder-v1`
- Device, staging, reboot, flash, or network-to-device action: none

## Isolation result

A minimal tracked export plus exact V3403/V3404 boot inputs, V3403 Doom
sources, and recovered V535 property material was created below
`workspace/private/outputs/`. Bubblewrap exposed that clone only as `/work`
with a private mount, PID, user, IPC, UTS, cgroup, and network namespace.

The pre-import fault test proved:

- the canonical repository absolute path was absent;
- clone-private writes succeeded;
- the V3403 and V3404 boot hashes matched their pins; and
- no canonical private path was bound into the namespace.

## Unmapped clone A/B

Two legacy builds inside the isolated clone were byte-identical to each other.
They matched Phase 0 for init and helper but differed for engine, ramdisk, and
boot:

```text
init     beb44eea342e5a151f66b0379c3fb3872b7c29d61afaa27d3946072975606628
helper   fa395d3ecb6944a57487f3966948a634596157e4de3fdc39575a2fc502d1ceef
engine   b12c4dc1003752f2f5ffeb2cccf2a2ac85d7ab1586be7df937598ad25aa9bc1e
ramdisk  aa2b82d445ff2b97e2c6efc2362782cf455da1fecf4b2466ad98137e0b1512db
boot     b92be81e56638c4f296ed71d4cd74837cd2c10ec9428c293f675615e6560f1df
```

The generated engine adapter and SFX sources were byte-identical to Phase 0.
Only the compiled Doom objects exposed a difference: `r_data.c` and `w_wad.c`
retained their compiler `__FILE__` path. That changed the engine Build ID and
then changed the containing ramdisk and boot image.

## Attribution control

A clone-private diagnostic `-ffile-prefix-map` translated `/work` to the
legacy Phase 0 source prefix. It was not added to tracked source. The second
isolated A/B then reproduced all five Phase 0 golden hashes exactly:

```text
init     beb44eea342e5a151f66b0379c3fb3872b7c29d61afaa27d3946072975606628
helper   fa395d3ecb6944a57487f3966948a634596157e4de3fdc39575a2fc502d1ceef
engine   ffc83e5d7ee373cb8d8c7fb4a6323b04052dbeb196302695d084e3eaa3a3c5ef
ramdisk  ef871b5bf548ee48a539899197182e41550dbc29464e83ed9ad9e43befab91a5
boot     6a190019e1242cf2aa16173f87e7e4f5e4bc20102d1859b0a1857edeb474d230
```

This proves the Phase 0 difference is fully attributable to a private absolute
source path, not source bytes, toolchain drift, archive order, or random code
generation.

## Disposition

Phase 1A closes as an isolation and attribution PASS. It does not accept a flat
builder. The legacy Phase 0 golden profile is reproducible only when its
private source prefix is reproduced, so it is unsuitable as the final
portable profile.

Phase 1B must materialize the effective adapter/SFX sources and flat manifest,
compile with a stable public virtual source prefix, and establish a new
portable A/B golden profile. The old five hashes remain an exact semantic
bridge control, not the final production identity. This report grants no
device authority.
