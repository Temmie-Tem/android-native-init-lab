#!/usr/bin/env python3
"""Generate the pinned S22+ FYG8 module map documentation.

Host-only. This combines depmod metadata with exact module hashes, modinfo, and
ELF symbol inspection. Curated subsystem documents remain explicit about the
difference between static metadata, source review, and live driver binding.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import s22plus_o2_module_plan as o2


SCHEMA = "s22plus_fyg8_module_map_v1"
TARGET = o2.TARGET
DEFAULT_METADATA_DIR = o2.DEFAULT_METADATA_DIR
DEFAULT_OUT = Path("docs/module-map/s22plus-fyg8")
LIVE_SIDECARS = frozenset({"stock-usb-runtime-topology.json"})
EXPECTED_MODULE_COUNT = 441
EXPECTED_VERMAGIC = (
    "5.10.226-android12-9-gki-30958166-abS906NKSS7FYG8 "
    "SMP preempt mod_unload modversions aarch64"
)
MODINFO_TOOL = "modinfo"
NM_TOOL = "aarch64-linux-gnu-nm"

RETENTION_MODULES = {
    "sec_log_buf.ko": {
        "role": "reserved-memory printk ring and last_kmsg/ap_klog owner",
        "source_status": "SOURCE_VERIFIED",
        "runtime_status": "LIVE_BOUND",
        "compatible": "samsung,kernel_log_buf",
        "bind": "/sys/bus/platform/drivers/samsung,kernel_log_buf/8.samsung,kernel_log_buf",
    },
    "sec_debug.ko": {
        "role": "Samsung panic notifier, statistics, and debug controls",
        "source_status": "SOURCE_VERIFIED",
        "runtime_status": "LIVE_BOUND",
        "compatible": "samsung,sec_debug",
        "bind": "/sys/bus/platform/drivers/samsung,sec_debug/soc:samsung,sec_debug",
    },
}


class MapError(ValueError):
    pass


@dataclass(frozen=True)
class ModuleInspection:
    filename: str
    runtime_name: str
    size: int
    sha256: str
    vermagic: str
    modinfo_depends: tuple[str, ...]
    modinfo_aliases: tuple[str, ...]
    parameters: tuple[str, ...]
    undefined_symbols: tuple[str, ...]
    exported_symbols: tuple[str, ...]


@dataclass(frozen=True)
class MapModel:
    metadata: o2.ModuleMetadata
    inspections: dict[str, ModuleInspection]
    aliases_by_module: dict[str, tuple[str, ...]]
    firststage_line_positions: dict[str, tuple[int, ...]]
    recovery_line_positions: dict[str, tuple[int, ...]]
    symbol_overlap_edges: dict[tuple[str, str], tuple[str, ...]]
    unresolved_symbol_counts: dict[str, int]
    ambiguous_symbol_counts: dict[str, int]


def run_tool(command: list[str]) -> str:
    env = os.environ.copy()
    env["LC_ALL"] = "C"
    result = subprocess.run(command, capture_output=True, text=True, env=env, check=False)
    if result.returncode != 0:
        raise MapError(
            f"tool failed rc={result.returncode}: {' '.join(command)}: "
            f"{result.stderr.strip()}"
        )
    return result.stdout


def parse_modinfo(path: Path) -> dict[str, tuple[str, ...]]:
    fields: dict[str, list[str]] = {}
    for raw in run_tool([MODINFO_TOOL, str(path)]).splitlines():
        key, sep, value = raw.partition(":")
        if not sep:
            raise MapError(f"malformed modinfo line for {path.name}: {raw!r}")
        fields.setdefault(key.strip(), []).append(value.strip())
    return {key: tuple(values) for key, values in fields.items()}


def parse_nm_symbols(path: Path, *, defined: bool) -> tuple[str, ...]:
    command = [NM_TOOL]
    if defined:
        command.extend(["-g", "--defined-only"])
    else:
        command.append("-u")
    command.append(str(path))
    symbols: set[str] = set()
    for raw in run_tool(command).splitlines():
        fields = raw.split()
        if fields:
            symbols.add(fields[-1])
    return tuple(sorted(symbols))


def one(values: tuple[str, ...], field: str, module: str) -> str:
    if len(values) != 1:
        raise MapError(f"expected one {field} for {module}, got {values}")
    return values[0]


def inspect_module(metadata: o2.ModuleMetadata, filename: str) -> ModuleInspection:
    path = metadata.metadata_dir / filename
    if not path.is_file():
        raise MapError(f"module file missing: {path}")
    fields = parse_modinfo(path)
    runtime_name = o2.normalize_module_name(filename)
    modinfo_name = one(fields.get("name", ()), "modinfo name", filename)
    if modinfo_name != runtime_name:
        raise MapError(f"runtime name mismatch for {filename}: {modinfo_name} != {runtime_name}")
    vermagic = one(fields.get("vermagic", ()), "vermagic", filename)
    if vermagic != EXPECTED_VERMAGIC:
        raise MapError(f"vermagic mismatch for {filename}: {vermagic!r}")
    depends_text = one(fields.get("depends", ()), "depends", filename)
    depends = tuple(value for value in depends_text.split(",") if value)
    return ModuleInspection(
        filename=filename,
        runtime_name=runtime_name,
        size=path.stat().st_size,
        sha256=o2.sha256_file(path),
        vermagic=vermagic,
        modinfo_depends=depends,
        modinfo_aliases=tuple(sorted(fields.get("alias", ()))),
        parameters=tuple(sorted(fields.get("parm", ()))),
        undefined_symbols=parse_nm_symbols(path, defined=False),
        exported_symbols=parse_nm_symbols(path, defined=True),
    )


def invert_aliases(metadata: o2.ModuleMetadata) -> dict[str, tuple[str, ...]]:
    inverted: dict[str, list[str]] = {module: [] for module in metadata.files}
    for pattern, targets in metadata.aliases.items():
        for target in targets:
            inverted[target].append(pattern)
    return {module: tuple(sorted(values)) for module, values in inverted.items()}


def load_line_positions(
    metadata: o2.ModuleMetadata,
    filename: str,
) -> dict[str, tuple[int, ...]]:
    positions: dict[str, list[int]] = {module: [] for module in metadata.files}
    text = (metadata.metadata_dir / filename).read_text(encoding="utf-8")
    for line_number, token in enumerate(o2.source_lines(text), 1):
        fields = token.split()
        if len(fields) != 1:
            raise MapError(f"invalid {filename} line {line_number}: {token!r}")
        module = metadata.resolve(fields[0])
        positions[module].append(line_number)
    return {module: tuple(values) for module, values in positions.items()}


def build_symbol_model(
    metadata: o2.ModuleMetadata,
    inspections: dict[str, ModuleInspection],
) -> tuple[dict[tuple[str, str], tuple[str, ...]], dict[str, int], dict[str, int]]:
    providers: dict[str, set[str]] = {}
    for module in metadata.files:
        for symbol in inspections[module].exported_symbols:
            providers.setdefault(symbol, set()).add(module)

    edges: dict[tuple[str, str], set[str]] = {}
    unresolved: dict[str, int] = {}
    ambiguous: dict[str, int] = {}
    for consumer in metadata.files:
        unresolved_count = 0
        ambiguous_count = 0
        for symbol in inspections[consumer].undefined_symbols:
            candidates = providers.get(symbol, set()) - {consumer}
            if len(candidates) == 1:
                provider = next(iter(candidates))
                edges.setdefault((consumer, provider), set()).add(symbol)
            elif not candidates:
                unresolved_count += 1
            else:
                ambiguous_count += 1
        unresolved[consumer] = unresolved_count
        ambiguous[consumer] = ambiguous_count
    return (
        {edge: tuple(sorted(symbols)) for edge, symbols in edges.items()},
        unresolved,
        ambiguous,
    )


def build_model(metadata_dir: Path) -> MapModel:
    for tool in (MODINFO_TOOL, NM_TOOL):
        if shutil.which(tool) is None:
            raise MapError(f"required host tool missing: {tool}")
    metadata = o2.load_metadata(metadata_dir)
    o2.verify_fyg8_pins(metadata)
    if len(metadata.files) != EXPECTED_MODULE_COUNT:
        raise MapError(f"module count mismatch: {len(metadata.files)} != {EXPECTED_MODULE_COUNT}")
    inspections = {module: inspect_module(metadata, module) for module in metadata.files}
    edges, unresolved, ambiguous = build_symbol_model(metadata, inspections)
    return MapModel(
        metadata=metadata,
        inspections=inspections,
        aliases_by_module=invert_aliases(metadata),
        firststage_line_positions=load_line_positions(metadata, "modules.load"),
        recovery_line_positions=load_line_positions(metadata, "modules.load.recovery"),
        symbol_overlap_edges=edges,
        unresolved_symbol_counts=unresolved,
        ambiguous_symbol_counts=ambiguous,
    )


def list_field(values: Iterable[str]) -> str:
    text = ",".join(values)
    if any(character in text for character in "\t\r\n"):
        raise MapError(f"TSV field contains a control character: {text!r}")
    return text


def optional_position(order: tuple[str, ...], module: str) -> str:
    try:
        return str(order.index(module) + 1)
    except ValueError:
        return ""


def evidence_status(module: str) -> str:
    if module in RETENTION_MODULES:
        data = RETENTION_MODULES[module]
        return f"STATIC_VERIFIED+{data['source_status']}+{data['runtime_status']}"
    return "STATIC_VERIFIED"


def render_inventory(model: MapModel) -> str:
    metadata = model.metadata
    header = [
        "filename",
        "runtime_name",
        "sha256",
        "size_bytes",
        "vermagic",
        "firststage_line_positions",
        "firststage_unique_position",
        "recovery_line_positions",
        "recovery_unique_position",
        "hard_deps",
        "soft_pre",
        "soft_post",
        "modinfo_depends",
        "options",
        "blocklisted",
        "metadata_alias_count",
        "modinfo_alias_count",
        "parameter_count",
        "undefined_symbol_count",
        "declared_symbol_provider_count",
        "candidate_symbol_overlap_provider_count",
        "kernel_or_unresolved_symbol_count",
        "ambiguous_symbol_count",
        "evidence_status",
    ]
    rows = ["\t".join(header)]
    for module in metadata.files:
        inspection = model.inspections[module]
        providers = {
            provider for consumer, provider in model.symbol_overlap_edges if consumer == module
        }
        declared_providers = providers & set(metadata.hard_deps[module])
        candidate_providers = providers - declared_providers
        values = [
            module,
            inspection.runtime_name,
            inspection.sha256,
            str(inspection.size),
            inspection.vermagic,
            list_field(str(value) for value in model.firststage_line_positions[module]),
            optional_position(metadata.firststage_order, module),
            list_field(str(value) for value in model.recovery_line_positions[module]),
            optional_position(metadata.recovery_order, module),
            list_field(metadata.hard_deps[module]),
            list_field(metadata.soft_pre.get(module, ())),
            list_field(metadata.soft_post.get(module, ())),
            list_field(inspection.modinfo_depends),
            list_field(metadata.options.get(module, ())),
            "1" if inspection.runtime_name in metadata.blocked_runtime_names else "0",
            str(len(model.aliases_by_module[module])),
            str(len(inspection.modinfo_aliases)),
            str(len(inspection.parameters)),
            str(len(inspection.undefined_symbols)),
            str(len(declared_providers)),
            str(len(candidate_providers)),
            str(model.unresolved_symbol_counts[module]),
            str(model.ambiguous_symbol_counts[module]),
            evidence_status(module),
        ]
        rows.append("\t".join(values))
    return "\n".join(rows) + "\n"


def render_dependency_edges(model: MapModel) -> str:
    metadata = model.metadata
    rows = ["relation\tbefore\tafter\tsource"]
    edges: set[tuple[str, str, str, str]] = set()
    for consumer in metadata.files:
        for provider in metadata.hard_deps[consumer]:
            edges.add(("hard", provider, consumer, "modules.dep"))
        for provider in metadata.soft_pre.get(consumer, ()):
            edges.add(("soft_pre", provider, consumer, "modules.softdep"))
        for post in metadata.soft_post.get(consumer, ()):
            edges.add(("soft_post", consumer, post, "modules.softdep"))
    for relation, before, after, source in sorted(edges):
        rows.append(f"{relation}\t{before}\t{after}\t{source}")
    return "\n".join(rows) + "\n"


def render_symbol_overlaps(model: MapModel) -> str:
    rows = ["consumer\tcandidate_provider\tsymbol_count\tsymbols\tmetadata_status"]
    for (consumer, provider), symbols in sorted(model.symbol_overlap_edges.items()):
        status = (
            "DECLARED_HARD"
            if provider in model.metadata.hard_deps[consumer]
            else "CANDIDATE_ONLY"
        )
        rows.append(
            f"{consumer}\t{provider}\t{len(symbols)}\t{list_field(symbols)}\t{status}"
        )
    return "\n".join(rows) + "\n"


def render_readme(model: MapModel) -> str:
    return f"""# S22+ FYG8 Module Map

This directory is the reproducible module map for `{TARGET}`. It is generated
from the pinned FYG8 vendor-ramdisk metadata and all {len(model.metadata.files)} exact `.ko`
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
- `stock-usb-runtime-topology.json`: separately collected, serial-redacted stock
  Android read-only snapshot. It is preserved but not generated from firmware.
- `runtime-gates.md`: conditions required before a module is treated as usable.
- `known-gaps.md`: explicit boundaries and work not yet proved.
- `manifest.json`: source pins, counts, safety envelope, and generated hashes.

## Regeneration

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache \\
  python3 workspace/public/src/scripts/revalidation/s22plus_fyg8_module_map.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache \\
  python3 workspace/public/src/scripts/revalidation/s22plus_fyg8_module_map.py --check
```

The generator is host-only. It does not use ADB, insert modules, reboot, build
an image, or flash a partition.
"""


def render_retention(model: MapModel) -> str:
    metadata = model.metadata
    logbuf = model.inspections["sec_log_buf.ko"]
    debug = model.inspections["sec_debug.ko"]
    return f"""# Retention Subsystem

## Status

`SOURCE_VERIFIED + LIVE_BOUND` on the rooted FYG8 Android baseline. Direct-PID1
retention remains `UNVERIFIABLE` for candidates that did not load the owner.

| Module | Stock order | Hard deps | Softdeps | Role | Runtime proof |
|---|---:|---|---|---|---|
| `sec_log_buf.ko` | {list_field(str(value) for value in model.firststage_line_positions['sec_log_buf.ko'])} | none | none | reserved-memory printk ring; creates `/proc/last_kmsg` and `/proc/ap_klog` | `8.samsung,kernel_log_buf` bound |
| `sec_debug.ko` | {list_field(str(value) for value in model.firststage_line_positions['sec_debug.ko'])} | none | none | panic notifier, statistics, MID/upload controls | `soc:samsung,sec_debug` bound |

Exact hashes:

```text
sec_log_buf.ko {logbuf.sha256}
sec_debug.ko   {debug.sha256}
```

## Load-Bearing Conditions

`sec_log_buf.ko` requires more than an empty `depends=` field:

1. Exact FYG8 GKI ABI and exported `android_vh_logbuf` hooks.
2. DT compatible `samsung,kernel_log_buf`.
3. DT `sec,strategy=3` (`SEC_LOG_BUF_STRATEGY_VH_LOGBUF`).
4. A valid DT `memory-region` reserved-memory phandle and range.
5. Successful platform-driver probe and procfs registration.

`sec_debug.ko` separately requires DT compatible `samsung,sec_debug` and
`sec,panic_notifier-priority`. MID can affect Samsung panic/upload behavior but
does not instantiate the retained printk ring.

## Candidate Consequence

The O3/O3F 59-module plan included `sec_debug.ko` and omitted
`sec_log_buf.ko`. O3R1 loaded neither. Their retained marker misses therefore do
not disprove marker retention with the actual owner active.

Detailed source audit:

`docs/reports/NATIVE_INIT_V3421_S22PLUS_RETENTION_MODULE_CLOSURE_HOST_AUDIT_2026-07-10.md`
"""


def render_usb(model: MapModel) -> str:
    plan = o2.build_plan(model.metadata, o2.O3_MINIMAL_ACM_ROOTS)
    o2.verify_o3_minimal_acm_plan_identity(model.metadata, plan)
    gates = o2.validate_plan_contract(model.metadata, plan)["functional_bind_gates"]
    gate_rows = []
    for gate in gates:
        providers = ", ".join(f"`{name}`" for name in gate["required_runtime_modules"]) or "built-in"
        gate_rows.append(
            f"| {gate['order']} | `{gate['id']}` | {providers} | `{gate['path']}` | `UNVERIFIABLE` in direct PID1 |"
        )
    return f"""# USB Subsystem

## Status

- FYG8 metadata closure: `STATIC_VERIFIED`.
- Stock Android DWC3/UDC/gadget path: `LIVE_BOUND` in V3420 recovery checks.
- Direct-PID1 module execution and bind sequence: `UNVERIFIABLE` after O3/O3F.

The current O3 minimal-ACM metadata plan contains {len(plan.modules)} modules and
passes recursive hard dependency, softdep pre/post, stock-order, alias,
blocklist, and options parsing. This proves a static load plan only.

## Functional Gates

| Order | Gate | Provider | Required path | Direct-PID1 status |
|---:|---|---|---|---|
{chr(10).join(gate_rows)}

A `finit_module` return code or `/proc/modules` name proves registration only.
The next gate advances only after its driver/device path exists. O3 PASS remains
a framed host/device ACM request-response plus device-reported bind state, not
enumeration or survival.

Current active work remains O0 stock `/dev/ttyGS0` to host `/dev/ttyACM0`, then
O1 stock-first-stage observation. No direct-PID1 USB candidate is authorized by
this map. The latest stock read-only evidence is maintained separately in
`stock-usb-runtime-topology.json`.
"""


def render_runtime_gates() -> str:
    return """# Runtime Gate Rules

## Generic Module Gate

A module is usable only after all applicable gates pass in order:

1. `artifact`: exact module SHA256 and target kernel identity match.
2. `metadata`: hard dependencies and soft pre/post ordering are satisfied.
3. `insert`: `finit_module` succeeds, or an already-loaded state is proved.
4. `registration`: `/proc/modules` is read to EOF and contains the runtime name.
5. `match`: the expected DT/platform device exists and matches the driver.
6. `probe`: the driver/device bind symlink exists and probe did not defer/fail.
7. `surface`: the expected `/proc`, `/sys`, `/dev`, class, or protocol surface
   exists and behaves correctly.
8. `function`: a bounded end-to-end operation succeeds.

Failure at one gate stops interpretation at that gate. Source intent cannot be
promoted to runtime proof.

## Retention Gate

`sec_log_buf.ko` requires `registration -> platform bind -> /proc/last_kmsg and
/proc/ap_klog -> emit unique kmsg marker -> next-boot exact marker readback`.
`sec_debug.ko` is a separate optional panic-notifier/upload rung.

## USB Gate

The ordered USB bind gates are maintained in `subsystem-usb.md`. Host
enumeration without a device-reported bind bundle remains ambiguous.
"""


def render_known_gaps(model: MapModel) -> str:
    candidate_only = sum(
        1
        for (consumer, provider) in model.symbol_overlap_edges
        if provider not in model.metadata.hard_deps[consumer]
    )
    unresolved = sum(model.unresolved_symbol_counts.values())
    ambiguous = sum(model.ambiguous_symbol_counts.values())
    return f"""# Known Gaps

- Only `sec_log_buf.ko` and `sec_debug.ko` currently have curated Samsung source
  review and live bind evidence in this map. Other modules are
  `STATIC_VERIFIED` only.
- ELF imports with no module provider total {unresolved}. They are labeled
  kernel-or-unresolved; this map does not assume every one is a valid built-in
  export for the running kernel.
- Ambiguous ELF imports with multiple module providers total {ambiguous}.
- Import/export symbol-name overlaps absent from `modules.dep` total
  {candidate_only}; they remain visible in `symbol-overlap-edges.tsv` as
  `CANDIDATE_ONLY`. They are not treated as providers or promoted into load
  order because the same symbol may come from the kernel.
- DT clocks, regulators, interconnects, IOMMUs, reserved-memory regions, device
  links, and deferred-probe causes are not derivable from depmod alone. They
  require subsystem source review and runtime bind gates.
- Display, GPU, audio, storage, networking, and power subsystem maps are not yet
  curated. Add them one subsystem at a time with a named discriminator.
- This directory is not a live snapshot. A `LIVE_BOUND` claim must cite a report
  and target baseline; it does not automatically carry across a kernel boot.
"""


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("ascii")).hexdigest()


def build_artifacts(model: MapModel) -> dict[str, str]:
    artifacts = {
        "README.md": render_readme(model),
        "inventory.tsv": render_inventory(model),
        "dependency-edges.tsv": render_dependency_edges(model),
        "symbol-overlap-edges.tsv": render_symbol_overlaps(model),
        "subsystem-retention.md": render_retention(model),
        "subsystem-usb.md": render_usb(model),
        "runtime-gates.md": render_runtime_gates(),
        "known-gaps.md": render_known_gaps(model),
    }
    symbol_undeclared = sum(
        1
        for (consumer, provider) in model.symbol_overlap_edges
        if provider not in model.metadata.hard_deps[consumer]
    )
    declared_symbol_overlaps = len(model.symbol_overlap_edges) - symbol_undeclared
    manifest = {
        "schema": SCHEMA,
        "target": TARGET,
        "inputs": {
            "metadata_directory": o2.display_path(o2.repo_root(), model.metadata.metadata_dir),
            "metadata_hashes": model.metadata.metadata_hashes,
            "module_count": len(model.metadata.files),
            "module_files_total_bytes": sum(item.size for item in model.inspections.values()),
        },
        "counts": {
            "firststage_modules": len(model.metadata.firststage_order),
            "recovery_modules": len(model.metadata.recovery_order),
            "hard_edges": sum(len(values) for values in model.metadata.hard_deps.values()),
            "soft_pre_edges": sum(len(values) for values in model.metadata.soft_pre.values()),
            "soft_post_edges": sum(len(values) for values in model.metadata.soft_post.values()),
            "symbol_overlap_edges": len(model.symbol_overlap_edges),
            "declared_symbol_provider_overlaps": declared_symbol_overlaps,
            "candidate_only_symbol_overlaps": symbol_undeclared,
            "kernel_or_unresolved_symbols": sum(model.unresolved_symbol_counts.values()),
            "ambiguous_symbols": sum(model.ambiguous_symbol_counts.values()),
        },
        "retention": {
            module: {
                "sha256": model.inspections[module].sha256,
                **data,
            }
            for module, data in RETENTION_MODULES.items()
        },
        "artifacts": {
            name: {"sha256": sha256_text(text), "bytes": len(text.encode("ascii"))}
            for name, text in sorted(artifacts.items())
        },
        "safety": {
            "host_only": True,
            "adb": False,
            "module_insertion": False,
            "reboot": False,
            "image_build": False,
            "flash": False,
            "partition_write": False,
            "sysfs_write": False,
            "configfs_write": False,
        },
    }
    artifacts["manifest.json"] = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    return artifacts


def write_artifacts(out_dir: Path, artifacts: dict[str, str]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    expected = set(artifacts)
    existing = {path.name for path in out_dir.iterdir() if path.is_file()}
    stale = sorted(existing - expected - LIVE_SIDECARS)
    if stale:
        raise MapError(f"refusing to leave stale module-map files: {stale}")
    for name, text in artifacts.items():
        (out_dir / name).write_text(text, encoding="ascii")


def check_artifacts(out_dir: Path, artifacts: dict[str, str]) -> None:
    mismatches: list[str] = []
    expected = set(artifacts)
    existing = {path.name for path in out_dir.iterdir() if path.is_file()} if out_dir.is_dir() else set()
    for name, text in artifacts.items():
        path = out_dir / name
        if not path.is_file() or path.read_text(encoding="ascii") != text:
            mismatches.append(name)
    stale = sorted(existing - expected - LIVE_SIDECARS)
    if mismatches or stale:
        raise MapError(f"module map drifted mismatches={sorted(mismatches)} stale={stale}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata-dir", type=Path, default=DEFAULT_METADATA_DIR)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--check", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = o2.repo_root()
    metadata_dir = o2.resolve(root, args.metadata_dir)
    out_dir = o2.resolve(root, args.out)
    model = build_model(metadata_dir)
    artifacts = build_artifacts(model)
    if args.check:
        check_artifacts(out_dir, artifacts)
        mode = "check"
    else:
        write_artifacts(out_dir, artifacts)
        mode = "write"
    manifest = json.loads(artifacts["manifest.json"])
    print(
        json.dumps(
            {
                "result": "pass",
                "mode": mode,
                "target": TARGET,
                "out": o2.display_path(root, out_dir),
                "module_count": len(model.metadata.files),
                "hard_edges": manifest["counts"]["hard_edges"],
                "soft_edges": manifest["counts"]["soft_pre_edges"]
                + manifest["counts"]["soft_post_edges"],
                "symbol_overlap_edges": manifest["counts"]["symbol_overlap_edges"],
                "artifact_count": len(artifacts),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (MapError, o2.PlanError) as exc:
        raise SystemExit(str(exc)) from exc
