# A90 V3404 Flat Builder Phase 1D Shallow Manifest H0

- Date: `2026-07-31`
- Decision: `A90_V3404_FLAT_BUILDER_PHASE1D_SHALLOW_MANIFEST_PASS`
- Schema: `a90-flat-builder-v1`
- Fixture: `flat-builder-v1-noop`
- Device authority: none
- Device, staging, reboot, flash, or network-to-device action: none

## Result

The flat builder now resolves one data-only child manifest over one flattened
sibling baseline. It does not import or mutate a Python parent module. The
two-line `flat-builder-v1-noop` fixture resolves exactly to
`v3404-effective-portable-v1`.

The baseline and child have the same canonical effective-manifest SHA256:

```text
ea93bf938143c58214c4bca0daea5fb0dd5527fcb2c5314aa5cb726d17030d06
```

The child file retains its separate raw identity:

```text
b41387c1885c617af547ce1e4adbe11bca237d3fff36487ed3a32981e6f7eb53
```

Receipts now record both identities and the ordered child-to-parent lineage
with each raw SHA256. The raw lineage is snapshotted from the same bytes that
were parsed and revalidated before each build receipt and the final A/B
receipt.

## Resolver contract

The resolver enforces:

- an `extends` value is a sibling profile name, not a filesystem path;
- requested and parent manifest file/profile symlinks are rejected;
- inheritance depth is at most one child over one flat parent;
- cycles are rejected before resolution;
- unknown top-level and nested overlay keys are rejected;
- an override cannot change the inherited value type;
- dictionaries merge by known key and lists replace atomically;
- `candidate_authority` must remain false;
- the writing entrypoint accepts only
  `versions/<host-profile>/manifest.toml`; and
- each resolved leaf retains its source manifest, so inherited materialized
  source paths remain relative to the baseline that declared them; and
- every lineage member's raw bytes are revalidated after building before a
  receipt can be accepted.

No V3406 directory or candidate identity was created.

## Static and artifact validation

Focused tests passed `14/14`, including:

- exact no-op effective-data and effective-hash equality;
- inherited materialized-source origin and input-pin equality;
- two-node cycle and excessive-depth rejection;
- path-like `extends` rejection;
- manifest-file and parent-profile symlink rejection;
- inherited-value type-change rejection;
- post-resolution raw-lineage drift rejection;
- unknown top-level and nested-key rejection;
- candidate-authority escalation rejection; and
- execution-manifest path confinement.

The final-code no-op child A/B run was byte-identical and reproduced the Phase
1C portable identities:

```text
init     beb44eea342e5a151f66b0379c3fb3872b7c29d61afaa27d3946072975606628
helper   fa395d3ecb6944a57487f3966948a634596157e4de3fdc39575a2fc502d1ceef
engine   5b262978867bf98239e5d7e1b112f29b0217b59f057fc48c5b6e91d90eb5eaad
ramdisk  38e1edc8d9e8b0f396acaf366ef7d48311595a51df4ddf7849e183c8c505cbf2
boot     5839b260ef30d7ece9566a296155f571ad62b7f90ba3499b687f3db53eb956c2
```

The accepted V3404 boot was unchanged. Both sides were free of canonical and
sandbox source paths. Init, helper, and engine remained stripped, static
AArch64 ELF executables. No native-init, helper, or engine C source changed.

## Independent review

Independent H0 review returned `GO` with no Critical, High, or Medium finding.
The reviewed execution closure was:

```text
buildlib.py  25822555cc674a65b6494dcc0245402c0cc0c08e57fa74550b5406ac3660d8da
build.py     22e47981fa385708a2eee62337548b489176682f062fd97d718ed1c3d7394511
tests        0cd6f814398a7f09e350ee990682fc5447f6e2c413ca3c8c9d0194b32d23bbae
child        b41387c1885c617af547ce1e4adbe11bca237d3fff36487ed3a32981e6f7eb53
```

The reviewer independently reran the 14 focused tests, Python compilation,
audit-only path, and `git diff --check`, then checked the fresh final-code
`ab-03` receipt and artifact format/path results.

## Disposition

Phase 1 is closed. The flat V3404 snapshot and shallow manifest resolver
replace the 171-module Python mutation chain as the qualified host baseline for
future versions. The legacy chain remains historical evidence and is not
deleted.

The next bounded unit is Phase 2A H0: inventory the carried kernel, native-init,
and Debian rootfs display ownership surfaces and write the DRM/KMS plus
VT/session handoff contract. It must not create a candidate or device
authority.
