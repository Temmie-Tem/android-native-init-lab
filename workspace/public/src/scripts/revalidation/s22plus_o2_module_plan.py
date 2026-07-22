#!/usr/bin/env python3
"""Build the S22+ O2 stock-parity native module load plan.

Host-only. The planner combines hard dependencies, softdep pre/post edges, and
stock load-order tie-breaks. It also inventories aliases, enforces the stock
blocklist, carries module options into finit_module parameters, and emits the
functional bind gates that a later direct-PID1 candidate must prove.
"""

from __future__ import annotations

import argparse
import hashlib
import heapq
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


SCHEMA = "s22plus_o2_module_plan_v1"
TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
DEFAULT_METADATA_DIR = Path(
    "workspace/private/inputs/s22plus_firmware/S906NKSS7FYG8_SKC/"
    "extracted-images/ramdisk-list/vendor/extract/lib/modules"
)
DEFAULT_OUT = Path("workspace/private/outputs/s22plus_native_init/o2_loader_parity_v0_1")
DEFAULT_ROOTS = [
    "qcom_rpmh.ko",
    "gcc-waipio.ko",
    "dwc3-msm.ko",
]
EXPECTED_DEFAULT_PLAN_COUNT = 42
EXPECTED_DEFAULT_PLAN_TSV_SHA256 = "47b9a44331310951eb8bcb27d9dfe58bf44441ef7d981eee42ab658f60643987"
O3_MINIMAL_ACM_ROOTS = [
    "clk-qcom.ko",
    "pinctrl-msm.ko",
    "qcom_rpmh.ko",
    "icc-rpmh.ko",
    "icc-bcm-voter.ko",
    "gcc-waipio.ko",
    "pinctrl-waipio.ko",
    "clk-rpmh.ko",
    "rpmh-regulator.ko",
    "gdsc-regulator.ko",
    "qnoc-waipio.ko",
    "arm_smmu.ko",
    "qcom-pdc.ko",
    "dwc3-msm.ko",
    "gh_virt_wdt.ko",
]
EXPECTED_O3_MINIMAL_ACM_PLAN_COUNT = 59
EXPECTED_O3_MINIMAL_ACM_PLAN_TSV_SHA256 = (
    "a34ebbad3b5d770f133e37a450cc3007e4a84ab831788484680e88aad6b3d534"
)
E2_PROVEN_E1B_FOUNDATION = (
    "qcom_hwspinlock.ko",
    "smem.ko",
    "minidump.ko",
    "qcom-scm.ko",
    "qcom_wdt_core.ko",
    "gh_virt_wdt.ko",
)
EXPECTED_E2_PROFILE_PLAN_COUNT = 59
EXPECTED_E2_PROFILE_PLAN_TSV_SHA256 = (
    "fc8169da1036ae8ba76e81ffe6afb17d063d114735a427e858afeeaa82a2218e"
)
TOLERATED_FYG8_UNRESOLVED_SOFTDEPS = {
    "pinctrl-waipio.ko": frozenset({"pre:qcom_tlmm_vm_irqchip"}),
}

REQUIRED_FILES = (
    "modules.dep",
    "modules.softdep",
    "modules.load",
    "modules.load.recovery",
    "modules.alias",
    "modules.blocklist",
)
OPTIONAL_OPTIONS_FILE = "modules.options"
EXPECTED_FYG8_HASHES = {
    "modules.dep": "21eae389f1d8b0a9fc93cec0b12d36e736cfac656d91ae55055c793f2ed67b27",
    "modules.softdep": "21d6a678d186356c2fb0349a8a9a5190e6e225dab0feb5012e495a100c33afb0",
    "modules.load": "8491b842e6e05cfba42694ad003301a6598e8d152ec10cc8f0cc6fb17f10e232",
    "modules.load.recovery": "616bdb71f2b68d76eca23f72883aea25d5202d4e14f5c99dd934720df863ac10",
    "modules.alias": "5679e647fcdcb6a13bd4f20d24a901f158e641fbd0a813274c99006ec8fa2c20",
    "modules.blocklist": "1fd4e3e5e5a13920c2fa75f0cdb7149869ceef6c194f2516ce977c0e492cb706",
}
EXPECTED_FYG8_COUNTS = {
    "modules.dep": 441,
    "modules.softdep": 31,
    "modules.load": 140,
    "modules.load.recovery": 446,
    "modules.alias": 901,
    "modules.blocklist": 64,
}

MODULE_TOKEN_RE = re.compile(r"^[A-Za-z0-9_.+-]+$")


class PlanError(ValueError):
    pass


@dataclass(frozen=True)
class ModuleMetadata:
    metadata_dir: Path
    files: tuple[str, ...]
    runtime_to_file: dict[str, str]
    hard_deps: dict[str, tuple[str, ...]]
    soft_pre: dict[str, tuple[str, ...]]
    soft_post: dict[str, tuple[str, ...]]
    unresolved_softdeps: dict[str, tuple[str, ...]]
    unresolved_softdep_targets: tuple[str, ...]
    aliases: dict[str, tuple[str, ...]]
    unresolved_alias_targets: tuple[str, ...]
    blocked_runtime_names: frozenset[str]
    duplicate_blocklist_names: tuple[str, ...]
    options: dict[str, tuple[str, ...]]
    orphan_options: tuple[str, ...]
    firststage_order: tuple[str, ...]
    recovery_order: tuple[str, ...]
    metadata_hashes: dict[str, str]
    source_line_counts: dict[str, int]
    options_file_present: bool

    def resolve(self, token: str) -> str:
        base = token.rsplit("/", 1)[-1]
        if base in self.hard_deps:
            return base
        runtime = normalize_module_name(base)
        found = self.runtime_to_file.get(runtime)
        if found is None:
            raise PlanError(f"module reference does not resolve: {token!r}")
        return found

    def stock_key(self, module: str) -> tuple[int, int, int, str]:
        try:
            return (0, self.firststage_order.index(module), 0, module)
        except ValueError:
            pass
        try:
            return (1, self.recovery_order.index(module), 0, module)
        except ValueError:
            pass
        return (2, self.files.index(module), 0, module)


@dataclass(frozen=True)
class ModulePlan:
    requested_roots: tuple[str, ...]
    resolved_roots: tuple[str, ...]
    modules: tuple[str, ...]
    constraints: tuple[dict[str, Any], ...]
    provenance: dict[str, tuple[str, ...]]
    tolerated_unresolved_softdeps: dict[str, tuple[str, ...]]


FUNCTIONAL_BIND_GATES: tuple[dict[str, Any], ...] = (
    {
        "order": 1,
        "id": "hwspinlock",
        "kind": "driver-bind-symlink",
        "path": "/sys/bus/platform/drivers/qcom_hwspinlock/soc:hwlock",
        "required_runtime_modules": ["qcom_hwspinlock"],
    },
    {
        "order": 2,
        "id": "smem",
        "kind": "driver-bind-symlink",
        "path": "/sys/bus/platform/drivers/qcom-smem/soc:qcom,smem",
        "required_runtime_modules": ["smem"],
    },
    {
        "order": 3,
        "id": "cmd-db",
        "kind": "driver-bind-symlink",
        "path": "/sys/bus/platform/drivers/cmd-db/80860000.aop_cmd_db_region",
        "required_runtime_modules": ["cmd_db"],
    },
    {
        "order": 4,
        "id": "rpmh",
        "kind": "driver-bind-symlink",
        "path": "/sys/bus/platform/drivers/rpmh/af20000.rsc",
        "required_runtime_modules": ["qcom_rpmh"],
    },
    {
        "order": 5,
        "id": "gcc-waipio",
        "kind": "driver-bind-symlink",
        "path": "/sys/bus/platform/drivers/gcc-waipio/100000.clock-controller",
        "required_runtime_modules": ["gcc_waipio"],
    },
    {
        "order": 6,
        "id": "ssusb",
        "kind": "driver-bind-symlink",
        "path": "/sys/bus/platform/drivers/msm-dwc3/a600000.ssusb",
        "required_runtime_modules": ["dwc3_msm"],
    },
    {
        "order": 7,
        "id": "dwc3-core",
        "kind": "driver-bind-symlink",
        "path": "/sys/bus/platform/drivers/dwc3/a600000.dwc3",
        "required_runtime_modules": [],
        "built_in_driver": True,
    },
    {
        "order": 8,
        "id": "udc",
        "kind": "class-device",
        "path": "/sys/class/udc/a600000.dwc3",
        "required_runtime_modules": [],
    },
)


def repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "GOAL.md").is_file() and (parent / "AGENTS.md").is_file():
            return parent
    raise PlanError("repository root not found")


def resolve(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else (root / path).resolve()


def display_path(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path.resolve())


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("ascii")).hexdigest()


def source_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if line:
            lines.append(line)
    return lines


def module_basename(token: str) -> str:
    base = token.rsplit("/", 1)[-1]
    if not base.endswith(".ko") or not MODULE_TOKEN_RE.fullmatch(base):
        raise PlanError(f"invalid module filename: {token!r}")
    return base


def normalize_module_name(token: str) -> str:
    base = token.rsplit("/", 1)[-1]
    if base.endswith(".ko"):
        base = base[:-3]
    if not base or not MODULE_TOKEN_RE.fullmatch(base):
        raise PlanError(f"invalid module name: {token!r}")
    return base.replace("-", "_")


def dedupe(values: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            ordered.append(value)
    return tuple(ordered)


def parse_modules_dep(text: str) -> tuple[tuple[str, ...], dict[str, tuple[str, ...]], dict[str, str]]:
    raw: list[tuple[str, list[str]]] = []
    files: list[str] = []
    runtime_to_file: dict[str, str] = {}
    for line in source_lines(text):
        lhs, sep, rhs = line.partition(":")
        if sep != ":":
            raise PlanError(f"malformed modules.dep line: {line!r}")
        filename = module_basename(lhs.strip())
        if filename in files:
            raise PlanError(f"duplicate modules.dep lhs: {filename}")
        runtime = normalize_module_name(filename)
        if runtime in runtime_to_file:
            raise PlanError(
                f"ambiguous normalized module name {runtime}: "
                f"{runtime_to_file[runtime]} and {filename}"
            )
        files.append(filename)
        runtime_to_file[runtime] = filename
        raw.append((filename, rhs.split()))

    file_set = set(files)
    hard_deps: dict[str, tuple[str, ...]] = {}
    for filename, rhs_tokens in raw:
        deps = [module_basename(token) for token in rhs_tokens]
        missing = [dep for dep in deps if dep not in file_set]
        if missing:
            raise PlanError(f"modules.dep missing target(s) for {filename}: {missing}")
        hard_deps[filename] = dedupe(deps)
    return tuple(files), hard_deps, runtime_to_file


def resolve_known(token: str, hard_deps: dict[str, tuple[str, ...]], runtime_to_file: dict[str, str]) -> str:
    base = token.rsplit("/", 1)[-1]
    if base in hard_deps:
        return base
    runtime = normalize_module_name(base)
    found = runtime_to_file.get(runtime)
    if found is None:
        raise PlanError(f"metadata references unknown module: {token!r}")
    return found


def parse_modules_softdep(
    text: str,
    hard_deps: dict[str, tuple[str, ...]],
    runtime_to_file: dict[str, str],
) -> tuple[
    dict[str, tuple[str, ...]],
    dict[str, tuple[str, ...]],
    dict[str, tuple[str, ...]],
    tuple[str, ...],
]:
    pre: dict[str, list[str]] = {}
    post: dict[str, list[str]] = {}
    unresolved: dict[str, list[str]] = {}
    unresolved_targets: list[str] = []
    for line in source_lines(text):
        fields = line.split()
        if len(fields) < 4 or fields[0] != "softdep":
            raise PlanError(f"malformed modules.softdep line: {line!r}")
        try:
            target = resolve_known(fields[1], hard_deps, runtime_to_file)
        except PlanError:
            unresolved_targets.append(line)
            continue
        mode: str | None = None
        saw_marker = False
        for token in fields[2:]:
            if token in {"pre:", "post:"}:
                mode = token[:-1]
                saw_marker = True
                continue
            if mode is None:
                raise PlanError(f"softdep dependency appears before pre:/post:: {line!r}")
            try:
                dep = resolve_known(token, hard_deps, runtime_to_file)
            except PlanError:
                unresolved.setdefault(target, []).append(f"{mode}:{token}")
                continue
            (pre if mode == "pre" else post).setdefault(target, []).append(dep)
        if not saw_marker:
            raise PlanError(f"softdep has no pre:/post: marker: {line!r}")
    return (
        {module: dedupe(values) for module, values in pre.items()},
        {module: dedupe(values) for module, values in post.items()},
        {module: dedupe(values) for module, values in unresolved.items()},
        tuple(unresolved_targets),
    )


def parse_load_order(
    text: str,
    hard_deps: dict[str, tuple[str, ...]],
    runtime_to_file: dict[str, str],
) -> tuple[str, ...]:
    resolved: list[str] = []
    for line in source_lines(text):
        fields = line.split()
        if len(fields) != 1:
            raise PlanError(f"load-order line must contain one module: {line!r}")
        resolved.append(resolve_known(fields[0], hard_deps, runtime_to_file))
    return dedupe(resolved)


def parse_modules_alias(
    text: str,
    hard_deps: dict[str, tuple[str, ...]],
    runtime_to_file: dict[str, str],
) -> tuple[dict[str, tuple[str, ...]], tuple[str, ...]]:
    aliases: dict[str, list[str]] = {}
    unresolved: list[str] = []
    for line in source_lines(text):
        fields = line.split()
        if len(fields) != 3 or fields[0] != "alias":
            raise PlanError(f"malformed modules.alias line: {line!r}")
        pattern, target = fields[1], fields[2]
        try:
            filename = resolve_known(target, hard_deps, runtime_to_file)
        except PlanError:
            unresolved.append(f"{pattern}->{target}")
            continue
        aliases.setdefault(pattern, []).append(filename)
    return ({pattern: dedupe(values) for pattern, values in aliases.items()}, tuple(unresolved))


def parse_modules_blocklist(text: str) -> tuple[frozenset[str], tuple[str, ...]]:
    blocked: set[str] = set()
    duplicates: list[str] = []
    for line in source_lines(text):
        fields = line.split()
        if len(fields) != 2 or fields[0] != "blocklist":
            raise PlanError(f"malformed modules.blocklist line: {line!r}")
        runtime = normalize_module_name(fields[1])
        if runtime in blocked:
            duplicates.append(runtime)
        blocked.add(runtime)
    return frozenset(blocked), tuple(duplicates)


def parse_modules_options(
    text: str,
    hard_deps: dict[str, tuple[str, ...]],
    runtime_to_file: dict[str, str],
) -> tuple[dict[str, tuple[str, ...]], tuple[str, ...]]:
    options: dict[str, list[str]] = {}
    orphan: list[str] = []
    for line in source_lines(text):
        fields = line.split(maxsplit=2)
        if len(fields) != 3 or fields[0] != "options":
            raise PlanError(f"malformed modules.options line: {line!r}")
        if "\t" in fields[2] or "\n" in fields[2]:
            raise PlanError(f"module options contain unsupported control characters: {line!r}")
        try:
            filename = resolve_known(fields[1], hard_deps, runtime_to_file)
        except PlanError:
            orphan.append(line)
            continue
        options.setdefault(filename, []).append(fields[2])
    return ({module: tuple(values) for module, values in options.items()}, tuple(orphan))


def load_metadata(metadata_dir: Path, options_file: Path | None = None) -> ModuleMetadata:
    missing = [name for name in REQUIRED_FILES if not (metadata_dir / name).is_file()]
    if missing:
        raise PlanError(f"module metadata file(s) missing: {missing}")
    texts = {name: (metadata_dir / name).read_text(encoding="utf-8") for name in REQUIRED_FILES}
    files, hard_deps, runtime_to_file = parse_modules_dep(texts["modules.dep"])
    soft_pre, soft_post, unresolved_softdeps, unresolved_softdep_targets = parse_modules_softdep(
        texts["modules.softdep"], hard_deps, runtime_to_file
    )
    firststage = parse_load_order(texts["modules.load"], hard_deps, runtime_to_file)
    recovery = parse_load_order(texts["modules.load.recovery"], hard_deps, runtime_to_file)
    aliases, unresolved_aliases = parse_modules_alias(texts["modules.alias"], hard_deps, runtime_to_file)
    blocked, duplicate_blocked = parse_modules_blocklist(texts["modules.blocklist"])

    selected_options = options_file if options_file is not None else metadata_dir / OPTIONAL_OPTIONS_FILE
    options_present = selected_options.is_file()
    options, orphan_options = (
        parse_modules_options(selected_options.read_text(encoding="utf-8"), hard_deps, runtime_to_file)
        if options_present
        else ({}, ())
    )
    hashes = {name: sha256_file(metadata_dir / name) for name in REQUIRED_FILES}
    if options_present:
        hashes[OPTIONAL_OPTIONS_FILE] = sha256_file(selected_options)
    counts = {name: len(source_lines(text)) for name, text in texts.items()}
    if options_present:
        counts[OPTIONAL_OPTIONS_FILE] = len(source_lines(selected_options.read_text(encoding="utf-8")))

    return ModuleMetadata(
        metadata_dir=metadata_dir,
        files=files,
        runtime_to_file=runtime_to_file,
        hard_deps=hard_deps,
        soft_pre=soft_pre,
        soft_post=soft_post,
        unresolved_softdeps=unresolved_softdeps,
        unresolved_softdep_targets=unresolved_softdep_targets,
        aliases=aliases,
        unresolved_alias_targets=unresolved_aliases,
        blocked_runtime_names=blocked,
        duplicate_blocklist_names=duplicate_blocked,
        options=options,
        orphan_options=orphan_options,
        firststage_order=firststage,
        recovery_order=recovery,
        metadata_hashes=hashes,
        source_line_counts=counts,
        options_file_present=options_present,
    )


def resolve_roots(metadata: ModuleMetadata, requested: Iterable[str]) -> tuple[str, ...]:
    resolved: list[str] = []
    for root in requested:
        if root.startswith("alias:"):
            pattern = root[len("alias:") :]
            targets = metadata.aliases.get(pattern, ())
            if len(targets) != 1:
                raise PlanError(f"alias root must resolve to exactly one module: {pattern!r} -> {targets}")
            resolved.append(targets[0])
        else:
            resolved.append(metadata.resolve(root))
    if not resolved:
        raise PlanError("at least one root module is required")
    return dedupe(resolved)


def build_plan(metadata: ModuleMetadata, requested_roots: Iterable[str]) -> ModulePlan:
    requested = tuple(requested_roots)
    roots = resolve_roots(metadata, requested)
    selected: set[str] = set()
    pending = list(roots)
    edges: dict[tuple[str, str], set[str]] = {}
    provenance: dict[str, set[str]] = {root: {"root"} for root in roots}
    tolerated_unresolved: dict[str, tuple[str, ...]] = {}

    def add_edge(before: str, after: str, reason: str) -> None:
        edges.setdefault((before, after), set()).add(reason)
        provenance.setdefault(before, set()).add(reason)
        provenance.setdefault(after, set()).add(reason)

    while pending:
        module = pending.pop()
        if module in selected:
            continue
        selected.add(module)
        unresolved = set(metadata.unresolved_softdeps.get(module, ()))
        tolerated = set(TOLERATED_FYG8_UNRESOLVED_SOFTDEPS.get(module, ()))
        unexpected_unresolved = sorted(unresolved - tolerated)
        if unexpected_unresolved:
            raise PlanError(
                f"selected module has unresolved softdep(s): "
                f"{module} -> {unexpected_unresolved}"
            )
        selected_tolerated = tuple(sorted(unresolved & tolerated))
        if selected_tolerated:
            tolerated_unresolved[module] = selected_tolerated
            provenance.setdefault(module, set()).update(
                f"tolerated-unresolved-softdep:{value}" for value in selected_tolerated
            )
        for dep in metadata.hard_deps[module]:
            add_edge(dep, module, f"hard:{module}")
            pending.append(dep)
        for dep in metadata.soft_pre.get(module, ()):
            add_edge(dep, module, f"softpre:{module}")
            pending.append(dep)
        for dep in metadata.soft_post.get(module, ()):
            add_edge(module, dep, f"softpost:{module}")
            pending.append(dep)

    blocked = sorted(
        module for module in selected if normalize_module_name(module) in metadata.blocked_runtime_names
    )
    if blocked:
        raise PlanError(f"selected closure intersects stock modules.blocklist: {blocked}")

    indegree = {module: 0 for module in selected}
    outgoing: dict[str, set[str]] = {module: set() for module in selected}
    for before, after in edges:
        if before not in selected or after not in selected:
            raise PlanError(f"internal edge escaped selected closure: {before}->{after}")
        if after not in outgoing[before]:
            outgoing[before].add(after)
            indegree[after] += 1

    ready: list[tuple[tuple[int, int, int, str], str]] = []
    for module, degree in indegree.items():
        if degree == 0:
            heapq.heappush(ready, (metadata.stock_key(module), module))
    ordered: list[str] = []
    while ready:
        _, module = heapq.heappop(ready)
        ordered.append(module)
        for consumer in sorted(outgoing[module], key=metadata.stock_key):
            indegree[consumer] -= 1
            if indegree[consumer] == 0:
                heapq.heappush(ready, (metadata.stock_key(consumer), consumer))
    if len(ordered) != len(selected):
        cycle = sorted(module for module, degree in indegree.items() if degree > 0)
        raise PlanError(f"hard/soft dependency cycle in selected closure: {cycle}")

    positions = {module: index for index, module in enumerate(ordered)}
    constraints = tuple(
        {
            "before": before,
            "after": after,
            "reasons": sorted(reasons),
        }
        for (before, after), reasons in sorted(
            edges.items(), key=lambda item: (positions[item[0][0]], positions[item[0][1]])
        )
    )
    for constraint in constraints:
        if positions[constraint["before"]] >= positions[constraint["after"]]:
            raise PlanError(f"planner emitted an invalid dependency order: {constraint}")

    return ModulePlan(
        requested_roots=requested,
        resolved_roots=roots,
        modules=tuple(ordered),
        constraints=constraints,
        provenance={module: tuple(sorted(values)) for module, values in sorted(provenance.items())},
        tolerated_unresolved_softdeps=tolerated_unresolved,
    )


def require_softdep(metadata: ModuleMetadata, target: str, relation: str, dependency: str) -> dict[str, str]:
    target_file = metadata.resolve(target)
    dep_file = metadata.resolve(dependency)
    mapping = metadata.soft_pre if relation == "pre" else metadata.soft_post
    if dep_file not in mapping.get(target_file, ()):
        raise PlanError(f"required softdep missing: {target} {relation}: {dependency}")
    return {"target": target_file, "relation": relation, "dependency": dep_file}


def validate_plan_contract(metadata: ModuleMetadata, plan: ModulePlan) -> dict[str, Any]:
    critical_softdeps = [
        require_softdep(metadata, "smem", "pre", "qcom_hwspinlock"),
        require_softdep(metadata, "qmi_helpers", "pre", "qrtr"),
        require_softdep(metadata, "dwc3_msm", "pre", "phy-generic"),
        require_softdep(metadata, "dwc3_msm", "pre", "phy-msm-snps-hs"),
        require_softdep(metadata, "dwc3_msm", "pre", "phy-msm-snps-eusb2"),
        require_softdep(metadata, "dwc3_msm", "pre", "phy-msm-ssusb-qmp"),
        require_softdep(metadata, "dwc3_msm", "pre", "eud"),
        require_softdep(metadata, "dwc3_msm", "post", "ucsi_glink"),
    ]
    plan_set = set(plan.modules)
    missing_softdeps = sorted(
        entry["dependency"] for entry in critical_softdeps if entry["dependency"] not in plan_set
    )
    if missing_softdeps:
        raise PlanError(f"critical softdep module(s) absent from plan: {missing_softdeps}")

    runtime_set = {normalize_module_name(module) for module in plan.modules}
    missing_gate_modules: dict[str, list[str]] = {}
    for gate in FUNCTIONAL_BIND_GATES:
        missing = [name for name in gate["required_runtime_modules"] if name not in runtime_set]
        if missing:
            missing_gate_modules[gate["id"]] = missing
    if missing_gate_modules:
        raise PlanError(f"functional gate provider module(s) absent from plan: {missing_gate_modules}")
    return {
        "critical_softdeps": critical_softdeps,
        "functional_bind_gates": list(FUNCTIONAL_BIND_GATES),
    }


def verify_default_plan_identity(metadata: ModuleMetadata, plan: ModulePlan) -> None:
    if plan.requested_roots != tuple(DEFAULT_ROOTS):
        return
    actual_count = len(plan.modules)
    actual_sha = sha256_text(render_plan_tsv(metadata, plan))
    if actual_count != EXPECTED_DEFAULT_PLAN_COUNT or actual_sha != EXPECTED_DEFAULT_PLAN_TSV_SHA256:
        raise PlanError(
            "default O2 plan identity drifted: "
            f"count={actual_count}/{EXPECTED_DEFAULT_PLAN_COUNT} "
            f"sha256={actual_sha}/{EXPECTED_DEFAULT_PLAN_TSV_SHA256}"
        )


def verify_o3_minimal_acm_plan_identity(metadata: ModuleMetadata, plan: ModulePlan) -> None:
    if plan.requested_roots != tuple(O3_MINIMAL_ACM_ROOTS):
        return
    actual_count = len(plan.modules)
    actual_sha = sha256_text(render_plan_tsv(metadata, plan))
    if (
        actual_count != EXPECTED_O3_MINIMAL_ACM_PLAN_COUNT
        or actual_sha != EXPECTED_O3_MINIMAL_ACM_PLAN_TSV_SHA256
    ):
        raise PlanError(
            "O3 minimal ACM plan identity drifted: "
            f"count={actual_count}/{EXPECTED_O3_MINIMAL_ACM_PLAN_COUNT} "
            f"sha256={actual_sha}/{EXPECTED_O3_MINIMAL_ACM_PLAN_TSV_SHA256}"
        )


def build_e2_profile_plan(metadata: ModuleMetadata) -> ModulePlan:
    """Preserve the proven E1B foundation without violating O3 dependencies."""
    canonical = build_plan(metadata, O3_MINIMAL_ACM_ROOTS)
    canonical_set = set(canonical.modules)
    if any(module not in canonical_set for module in E2_PROVEN_E1B_FOUNDATION):
        raise PlanError("E2 proven E1B foundation escaped the canonical O3 closure")
    modules = E2_PROVEN_E1B_FOUNDATION + tuple(
        module
        for module in canonical.modules
        if module not in E2_PROVEN_E1B_FOUNDATION
    )
    positions = {module: index for index, module in enumerate(modules)}
    violations = [
        constraint
        for constraint in canonical.constraints
        if positions[constraint["before"]] >= positions[constraint["after"]]
    ]
    if violations:
        raise PlanError(f"E2 profile order violates dependency metadata: {violations}")
    return ModulePlan(
        requested_roots=canonical.requested_roots,
        resolved_roots=canonical.resolved_roots,
        modules=modules,
        constraints=canonical.constraints,
        provenance=canonical.provenance,
        tolerated_unresolved_softdeps=canonical.tolerated_unresolved_softdeps,
    )


def verify_e2_profile_plan_identity(metadata: ModuleMetadata, plan: ModulePlan) -> None:
    if plan.modules[: len(E2_PROVEN_E1B_FOUNDATION)] != E2_PROVEN_E1B_FOUNDATION:
        raise PlanError("E2 profile lost the proven E1B foundation prefix")
    actual_count = len(plan.modules)
    actual_sha = sha256_text(render_plan_tsv(metadata, plan))
    if (
        actual_count != EXPECTED_E2_PROFILE_PLAN_COUNT
        or actual_sha != EXPECTED_E2_PROFILE_PLAN_TSV_SHA256
    ):
        raise PlanError(
            "E2 profile plan identity drifted: "
            f"count={actual_count}/{EXPECTED_E2_PROFILE_PLAN_COUNT} "
            f"sha256={actual_sha}/{EXPECTED_E2_PROFILE_PLAN_TSV_SHA256}"
        )


def c_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=True)


def render_plan_tsv(metadata: ModuleMetadata, plan: ModulePlan) -> str:
    rows: list[str] = []
    for module in plan.modules:
        params = " ".join(metadata.options.get(module, ()))
        if "\t" in params or "\n" in params:
            raise PlanError(f"module params cannot be represented in TSV: {module}")
        rows.append(f"{module}\t{normalize_module_name(module)}\t{params}")
    return "\n".join(rows) + "\n"


def render_plan_header(metadata: ModuleMetadata, plan: ModulePlan) -> str:
    lines = [
        "#ifndef S22PLUS_O2_MODULE_PLAN_GENERATED_H",
        "#define S22PLUS_O2_MODULE_PLAN_GENERATED_H",
        "",
        "#ifndef S22PLUS_O2_PLAN_TYPES_DEFINED",
        "#define S22PLUS_O2_PLAN_TYPES_DEFINED",
        "struct s22plus_o2_module_plan_entry {",
        "    const char *filename;",
        "    const char *runtime_name;",
        "    const char *params;",
        "};",
        "",
        "struct s22plus_o2_bind_gate_entry {",
        "    unsigned int order;",
        "    const char *id;",
        "    const char *kind;",
        "    const char *path;",
        "};",
        "#endif",
        "",
        "static const struct s22plus_o2_module_plan_entry s22plus_o2_module_plan[] = {",
    ]
    for module in plan.modules:
        params = " ".join(metadata.options.get(module, ()))
        lines.append(
            f"    {{{c_string(module)}, {c_string(normalize_module_name(module))}, {c_string(params)}}},"
        )
    lines.extend(
        [
            "};",
            "",
            "#define S22PLUS_O2_MODULE_PLAN_COUNT \\",
            "    (sizeof(s22plus_o2_module_plan) / sizeof(s22plus_o2_module_plan[0]))",
            "",
            "static const struct s22plus_o2_bind_gate_entry s22plus_o2_bind_gates[] = {",
        ]
    )
    for gate in FUNCTIONAL_BIND_GATES:
        lines.append(
            "    {"
            f"{gate['order']}U, {c_string(gate['id'])}, {c_string(gate['kind'])}, {c_string(gate['path'])}"
            "},"
        )
    lines.extend(
        [
            "};",
            "",
            "#define S22PLUS_O2_BIND_GATE_COUNT \\",
            "    (sizeof(s22plus_o2_bind_gates) / sizeof(s22plus_o2_bind_gates[0]))",
            "",
            "#endif",
            "",
        ]
    )
    return "\n".join(lines)


def verify_fyg8_pins(metadata: ModuleMetadata) -> None:
    mismatches = {
        name: {"expected": expected, "actual": metadata.metadata_hashes.get(name)}
        for name, expected in EXPECTED_FYG8_HASHES.items()
        if metadata.metadata_hashes.get(name) != expected
    }
    count_mismatches = {
        name: {"expected": expected, "actual": metadata.source_line_counts.get(name)}
        for name, expected in EXPECTED_FYG8_COUNTS.items()
        if metadata.source_line_counts.get(name) != expected
    }
    if mismatches or count_mismatches:
        raise PlanError(f"FYG8 metadata pin mismatch hashes={mismatches} counts={count_mismatches}")


def write_outputs(
    root: Path,
    out_dir: Path,
    metadata: ModuleMetadata,
    plan: ModulePlan,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    tsv_path = out_dir / "module-plan.tsv"
    header_path = out_dir / "module-plan.generated.h"
    gates_path = out_dir / "functional-bind-gates.json"
    manifest_path = out_dir / "manifest.json"
    tsv_path.write_text(render_plan_tsv(metadata, plan), encoding="ascii")
    header_path.write_text(render_plan_header(metadata, plan), encoding="ascii")
    contract = validate_plan_contract(metadata, plan)
    gates_path.write_text(
        json.dumps(contract["functional_bind_gates"], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    firststage_positions = {module: index + 1 for index, module in enumerate(metadata.firststage_order)}
    recovery_positions = {module: index + 1 for index, module in enumerate(metadata.recovery_order)}
    entries = []
    for index, module in enumerate(plan.modules, 1):
        entries.append(
            {
                "index": index,
                "filename": module,
                "runtime_name": normalize_module_name(module),
                "params": " ".join(metadata.options.get(module, ())),
                "firststage_position": firststage_positions.get(module),
                "recovery_position": recovery_positions.get(module),
                "provenance": list(plan.provenance.get(module, ())),
            }
        )
    manifest = {
        "schema": SCHEMA,
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "target": TARGET,
        "metadata": {
            "directory": display_path(root, metadata.metadata_dir),
            "hashes": metadata.metadata_hashes,
            "source_line_counts": metadata.source_line_counts,
            "module_count": len(metadata.files),
            "firststage_order_count": len(metadata.firststage_order),
            "recovery_order_count": len(metadata.recovery_order),
            "softdep_target_count": len(set(metadata.soft_pre) | set(metadata.soft_post)),
            "unresolved_softdeps": {
                module: list(values) for module, values in sorted(metadata.unresolved_softdeps.items())
            },
            "unresolved_softdep_targets": list(metadata.unresolved_softdep_targets),
            "alias_pattern_count": len(metadata.aliases),
            "unresolved_alias_targets": list(metadata.unresolved_alias_targets),
            "blocklist_count": len(metadata.blocked_runtime_names),
            "duplicate_blocklist_names": list(metadata.duplicate_blocklist_names),
            "options_file_present": metadata.options_file_present,
            "orphan_options": list(metadata.orphan_options),
        },
        "selection": {
            "requested_roots": list(plan.requested_roots),
            "resolved_roots": list(plan.resolved_roots),
            "root_model": "functional substrate roots plus selected dwc3-msm USB leaf",
            "tolerated_unresolved_softdeps": {
                module: list(values)
                for module, values in sorted(plan.tolerated_unresolved_softdeps.items())
            },
        },
        "semantics": {
            "recursive_hard_dependencies": True,
            "recursive_softdep_pre_post": True,
            "stock_tie_break": "modules.load, then modules.load.recovery, then modules.dep order",
            "aliases": "parsed and exact alias roots supported; no wildcard modalias runtime autoload",
            "blocklist": "selected closure intersection is fatal",
            "options": "modules.options params passed to finit_module when file is present",
            "proc_modules": "runtime consumer must stream to EOF; fixed-size one-read scans forbidden",
            "registration_is_not_bind_proof": True,
        },
        "plan": {
            "module_count": len(plan.modules),
            "entries": entries,
            "constraints": list(plan.constraints),
            "tsv_sha256": sha256_file(tsv_path),
            "generated_header_sha256": sha256_file(header_path),
        },
        "critical_softdeps": contract["critical_softdeps"],
        "functional_bind_gates": contract["functional_bind_gates"],
        "artifacts": {
            "module_plan_tsv": display_path(root, tsv_path),
            "module_plan_header": display_path(root, header_path),
            "functional_bind_gates": display_path(root, gates_path),
        },
        "safety": {
            "host_only": True,
            "device_action": False,
            "flash": False,
            "reboot": False,
            "partition_write": False,
            "sysfs_write": False,
            "configfs_write": False,
            "module_insertion": False,
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata-dir", type=Path, default=DEFAULT_METADATA_DIR)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--profile",
        choices=("o2-default", "o3-minimal-acm", "e2-profile"),
        default="o2-default",
    )
    parser.add_argument("--root", action="append", dest="roots")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.roots and args.profile != "o2-default":
        raise PlanError("--root cannot be combined with a non-default --profile")
    root = repo_root()
    metadata_dir = resolve(root, args.metadata_dir)
    out_dir = resolve(root, args.out)
    metadata = load_metadata(metadata_dir)
    verify_fyg8_pins(metadata)
    profile_roots = (
        O3_MINIMAL_ACM_ROOTS
        if args.profile in {"o3-minimal-acm", "e2-profile"}
        else DEFAULT_ROOTS
    )
    plan = (
        build_e2_profile_plan(metadata)
        if args.profile == "e2-profile"
        else build_plan(metadata, args.roots or profile_roots)
    )
    verify_default_plan_identity(metadata, plan)
    if args.profile == "o3-minimal-acm":
        verify_o3_minimal_acm_plan_identity(metadata, plan)
    if args.profile == "e2-profile":
        verify_e2_profile_plan_identity(metadata, plan)
    manifest = write_outputs(root, out_dir, metadata, plan)
    print(
        json.dumps(
            {
                "result": "pass",
                "target": TARGET,
                "out": display_path(root, out_dir),
                "module_count": manifest["plan"]["module_count"],
                "roots": manifest["selection"]["resolved_roots"],
                "options_file_present": manifest["metadata"]["options_file_present"],
                "critical_softdeps": manifest["critical_softdeps"],
                "functional_gate_count": len(manifest["functional_bind_gates"]),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except PlanError as exc:
        raise SystemExit(str(exc)) from exc
