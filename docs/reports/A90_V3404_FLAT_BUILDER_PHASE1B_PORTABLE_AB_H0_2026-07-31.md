# A90 V3404 Flat Builder Phase 1B Portable A/B H0

- Date: `2026-07-31`
- Decision: `A90_V3404_FLAT_BUILDER_PHASE1B_PORTABLE_AB_PASS`
- Schema: `a90-flat-builder-v1`
- Profile: `v3404-effective-portable-v1`
- Device authority: none
- Device, staging, reboot, flash, or network-to-device action: none

## Result

The effective V3404 build state is now one flattened TOML manifest, three
materialized generated sources, a read-only `buildlib`, and one writing
entrypoint. The new path imports no `build_native_init_*` module and mutates no
parent module global.

A disposable tracked export was exposed only as `/work` inside a bubblewrap
namespace. Two fresh builds from that export were byte-identical for all five
declared artifacts:

```text
init     beb44eea342e5a151f66b0379c3fb3872b7c29d61afaa27d3946072975606628
helper   fa395d3ecb6944a57487f3966948a634596157e4de3fdc39575a2fc502d1ceef
engine   5b262978867bf98239e5d7e1b112f29b0217b59f057fc48c5b6e91d90eb5eaad
ramdisk  38e1edc8d9e8b0f396acaf366ef7d48311595a51df4ddf7849e183c8c505cbf2
boot     5839b260ef30d7ece9566a296155f571ad62b7f90ba3499b687f3db53eb956c2
```

The accepted historical V3404 boot remained
`0a8827aeb46e2fb2cdf1e7cf7320626b4b3a43fcdbbff2024d92dcbc088e83d3`.

## Effective-state capture

The flat manifest fixes:

- 60 native-init translation units and an 84-flag effective compile profile;
- the exact 25 inherited helper feature flags after the four base flags;
- 80 Doom translation units from the pinned source;
- the native-init, helper, Doom, mkbootimg, base-boot, and accepted-boot input
  closures;
- the preserved V3403 ramdisk overlay and obsolete-engine removal list; and
- a fixed random seed plus `/usr/src/a90/...` virtual source prefixes.

The materialized generated-source pins are:

```text
adapter   d5bcb088a554cf53278a5d4995bf24768c49964eb6b4159a33eb80b39ab953ca
sfx       e52f5fef6db417359066aff1c00d0f11f8f3ac3462175093ec4a9eda99a7720f
SDL stub  18bf8a8f46a757399bfea90f7db828534e4b579efbf2e7754c10424dcbe690cd
```

Two gated bootstrap attempts exposed state that the legacy prose manifest had
not recorded. The first stopped on the missing 59 inherited native-init flags;
the second stopped on the missing 24 inherited helper flags. These were
different absent inputs, not retries of the same material failure. A
clone-private legacy command capture supplied the exact order, and static
comparison proved the flat lists equal before the passing A/B run.

## Bridge and attribution

The portable init and helper still match the Phase 0 legacy golden hashes
exactly. The engine differs because its two path-bearing `__FILE__` strings now
name `/usr/src/a90/doomgeneric/...` instead of a private host prefix.

Offline extraction found 30 files in each ramdisk and exactly one changed
member:

```text
bin/a90_doomgeneric_private_engine_v3404
```

Therefore the new ramdisk and boot identities are attributable only to the
portable engine identity. No final artifact contains the canonical repository
path or the `/work/workspace` sandbox path.

All three ELFs are static AArch64 executables with no `INTERP` segment. Required
V3404 init, helper-v427, and engine markers passed.

## Disposition

Phase 1B establishes the first portable local A/B golden profile. It does not
create V3406, a candidate artifact, a live manifest, or device authority. The
171-module legacy chain remains frozen evidence until a fresh committed export
reproduces these five hashes without manual working-tree injection.
