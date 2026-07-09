# V3422 S22+ FYG8 Module Map Host Build

## Verdict

`PASS; REPRODUCIBLE 441-MODULE MAP GENERATED; HOST-ONLY`.

V3422 converts the V3421 retention correction into a reusable module-map
system. The map separates machine-generated facts from curated source/runtime
interpretation so a metadata edge, symbol-name coincidence, source intent, and
successful live probe cannot be conflated.

No ADB command, module insertion, reboot, image build, flash, partition write,
sysfs write, or configfs write occurred in this unit.

## Artifacts

```text
docs/module-map/s22plus-fyg8/README.md
docs/module-map/s22plus-fyg8/inventory.tsv
docs/module-map/s22plus-fyg8/dependency-edges.tsv
docs/module-map/s22plus-fyg8/symbol-overlap-edges.tsv
docs/module-map/s22plus-fyg8/subsystem-retention.md
docs/module-map/s22plus-fyg8/subsystem-usb.md
docs/module-map/s22plus-fyg8/runtime-gates.md
docs/module-map/s22plus-fyg8/known-gaps.md
docs/module-map/s22plus-fyg8/manifest.json
```

Generator and tests:

```text
workspace/public/src/scripts/revalidation/s22plus_fyg8_module_map.py
tests/test_s22plus_fyg8_module_map.py
```

## Generated Scope

```text
exact_module_count=441
inventory_rows=441
modules.load_source_lines=140
modules.load_unique_modules=135
modules.load.recovery_unique_modules=441
hard_edges=2175
soft_pre_edges=32
soft_post_edges=1
symbol_overlap_edges=730
declared_symbol_provider_overlaps=664
candidate_only_symbol_overlaps=66
kernel_or_unresolved_symbols=19086
ambiguous_symbols=0
```

Every inventory row includes the exact module SHA256, size, FYG8 vermagic,
original load-file line positions, deduplicated order, hard dependencies,
softdep pre/post edges, modinfo dependencies/options/alias counts, blocklist
state, ELF import summary, and evidence status.

## Interpretation Boundary

`modules.dep` remains the authoritative loadable-module hard dependency graph.
ELF import/export inspection is recorded as a separate overlap graph:

- `DECLARED_HARD`: the symbol overlap agrees with a `modules.dep` edge.
- `CANDIDATE_ONLY`: names overlap but depmod does not declare the module edge.

`CANDIDATE_ONLY` is deliberately not called a provider. For example, a module
may export a common symbol that the kernel also exports. Without the exact
running-kernel export map, a same-name module symbol cannot establish runtime
ownership.

Likewise, `STATIC_VERIFIED` means only that the pinned artifact and mechanical
metadata were verified. It does not imply DT match, successful probe, driver
bind, surface creation, or end-to-end function.

## Curated Subsystems

Retention:

```text
sec_log_buf.ko = STATIC_VERIFIED + SOURCE_VERIFIED + LIVE_BOUND
sec_debug.ko   = STATIC_VERIFIED + SOURCE_VERIFIED + LIVE_BOUND
```

USB:

```text
O3 metadata closure = STATIC_VERIFIED
stock Android DWC3/UDC/gadget = LIVE_BOUND
direct-PID1 module/bind sequence = UNVERIFIABLE
```

The runtime-gate document requires artifact, metadata, insertion,
registration, DT match, probe/bind, surface, and bounded functional proof in
that order. Failure at one gate stops interpretation there.

## Validation

```text
python3 -m py_compile ... = PASS
unittest tests.test_s22plus_fyg8_module_map = 6/6 PASS
generator write = PASS
generator --check = PASS
git diff --check = PASS
```

The `--check` mode regenerates all content in memory and fails closed on a
missing, stale, or byte-different artifact.

## Next Bound

The module map does not authorize another direct-PID1 or panic candidate. The
active direction remains O0 stock TTY request/response, then O1
stock-first-stage observation. Before O0, restore and prove the normal Android
`/dev/null` character device baseline documented by V3421.
