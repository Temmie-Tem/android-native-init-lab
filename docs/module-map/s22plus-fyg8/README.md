# S22+ FYG8 Module Map

This directory is the reproducible module map for `SM-S906N/g0q/S906NKSS7FYG8`. It is generated
from the pinned FYG8 vendor-ramdisk metadata and all 441 exact `.ko`
files. It contains no firmware binary.

## Evidence Levels

- `STATIC_VERIFIED`: exact file hash, modinfo, depmod metadata, and ELF symbol
  summary were generated from the pinned FYG8 inputs.
- `SOURCE_VERIFIED`: the relevant Samsung probe path was read in the official
  FYG8 kernel source archive.
- `LIVE_BOUND`: the expected driver/device bind or procfs surface was observed
  on the rooted FYG8 Android baseline.
- `INFERRED`: plausible but not directly proved; never sufficient for a live
  gate.
- `UNVERIFIABLE`: no direct observation channel exists for the claim.

Evidence levels are additive. `STATIC_VERIFIED` never implies that a driver
probed successfully.

## Files

- `inventory.tsv`: one row per module with hashes, original load-file line
  positions, deduplicated order, dependencies, modinfo counts, symbol summary,
  and evidence status.
- `dependency-edges.tsv`: normalized hard and soft pre/post ordering edges.
- `symbol-overlap-edges.tsv`: ELF import/export name overlaps. Only rows marked
  `DECLARED_HARD` are accepted module-provider edges; `CANDIDATE_ONLY` overlaps
  are not promoted because the same symbol may be exported by the kernel.
  Imports without a module export remain `kernel-or-unresolved`.
- `subsystem-retention.md`: reviewed `sec_log_buf`/`sec_debug` ownership map.
- `subsystem-usb.md`: current static USB closure and functional bind gates.
- `runtime-gates.md`: conditions required before a module is treated as usable.
- `known-gaps.md`: explicit boundaries and work not yet proved.
- `manifest.json`: source pins, counts, safety envelope, and generated hashes.

## Regeneration

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache \
  python3 workspace/public/src/scripts/revalidation/s22plus_fyg8_module_map.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache \
  python3 workspace/public/src/scripts/revalidation/s22plus_fyg8_module_map.py --check
```

The generator is host-only. It does not use ADB, insert modules, reboot, build
an image, or flash a partition.
