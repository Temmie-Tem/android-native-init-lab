#!/usr/bin/env python3
"""Bind the recovered FYG8 normal-load orders to the proposed 67-module set."""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any


SCHEMA = "s22plus_fyg8_max77705_order_authority_v1"
TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
PLAN = Path(
    "workspace/private/outputs/s22plus_fyg8_p315/intent/materialized-sources/"
    "s22plus_fyg8_p286_e3_plan.h"
)
MODULE_DIR = Path(
    "workspace/private/inputs/s22plus_firmware/S906NKSS7FYG8_SKC/"
    "extracted-images/ramdisk-list/vendor/extract/lib/modules"
)
FIRST_STAGE = MODULE_DIR / "modules.load"
RECOVERY = MODULE_DIR / "modules.load.recovery"
DEPENDENCIES = MODULE_DIR / "modules.dep"
SECOND_STAGE = Path(
    "workspace/private/outputs/s22plus_fyg8_max77705_gate0/"
    "order-authority-20260811-01/modules.load"
)
DEFAULT_OUTPUT = Path(
    "workspace/private/outputs/s22plus_fyg8_max77705_gate0/"
    "order-authority-20260811-01/max77705-67-order-audit.json"
)

EXPECTED_IDENTITIES = {
    "plan": (4_707, "d5ec1423cd47aba29c935512690c4e0b9af3302e4df1b91e50ed1cc816199005"),
    "first_stage": (2_228, "8491b842e6e05cfba42694ad003301a6598e8d152ec10cc8f0cc6fb17f10e232"),
    "recovery": (7_239, "616bdb71f2b68d76eca23f72883aea25d5202d4e14f5c99dd934720df863ac10"),
    "dependencies": (74_710, "21eae389f1d8b0a9fc93cec0b12d36e736cfac656d91ae55055c793f2ed67b27"),
    "second_stage": (5_843, "8411620a0384d07fed491a2f8f7c146e354d022c8446940fc59f49cb2d98d360"),
}
EXPECTED_DUPLICATES = {
    "gh_virt_wdt.ko": 2,
    "qcom_wdt_core.ko": 2,
    "qcom_tsens.ko": 2,
    "thermal_pause.ko": 2,
    "cpu_hotplug.ko": 2,
}
PROPOSED_ADDITIONS = (
    "msm-geni-se.ko",
    "gpi.ko",
    "i2c-msm-geni.ko",
    "spu_verify.ko",
    "mfd_max77705.ko",
    "pdic_max77705.ko",
)
POSITION_FOCUS = (
    "msm-geni-se.ko",
    "gpi.ko",
    "i2c-msm-geni.ko",
    "ucsi_glink.ko",
    "usb_notify_layer.ko",
    "common_muic.ko",
    "vbus_notifier.ko",
    "usb_typec_manager.ko",
    "if_cb_manager.ko",
    "pdic_notifier_module.ko",
    "mfd_max77705.ko",
    "pdic_max77705.ko",
    "spu_verify.ko",
)
PLAN_ROW = re.compile(
    r'^\s*\{"([^"]+\.ko)",\s*"([^"]+)",\s*"([^"]*)"\},$', re.MULTILINE
)


class OrderError(ValueError):
    pass


def repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "GOAL.md").is_file() and (parent / "AGENTS.md").is_file():
            return parent
    raise OrderError("repository root not found")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_identity(path: Path, expected: tuple[int, str], label: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise OrderError(f"{label} is not a direct regular file: {path}")
    size = path.stat().st_size
    digest = sha256_file(path)
    if (size, digest) != expected:
        raise OrderError(f"{label} identity mismatch: {(size, digest)}")
    return {"path": str(path), "size": size, "sha256": digest}


def module_lines(path: Path, label: str) -> list[str]:
    data = path.read_bytes()
    if not data.endswith(b"\n") or b"\r" in data or b"\0" in data:
        raise OrderError(f"{label} has invalid line termination")
    try:
        lines = data.decode("ascii").splitlines()
    except UnicodeDecodeError as exc:
        raise OrderError(f"{label} is not ASCII") from exc
    if not lines or any(not line.endswith(".ko") or Path(line).name != line for line in lines):
        raise OrderError(f"{label} has an invalid module name")
    return lines


def parse_plan(text: str) -> list[str]:
    rows = PLAN_ROW.findall(text)
    filenames = [row[0] for row in rows]
    if len(rows) != 61 or len(filenames) != len(set(filenames)):
        raise OrderError(f"P3.15 plan shape mismatch: {len(rows)}/{len(set(filenames))}")
    return filenames


def parse_dependencies(path: Path) -> dict[str, tuple[str, ...]]:
    result: dict[str, tuple[str, ...]] = {}
    for number, line in enumerate(path.read_text(encoding="ascii").splitlines(), 1):
        left, separator, right = line.partition(":")
        if not separator or not left.startswith("/lib/modules/"):
            raise OrderError(f"invalid modules.dep row {number}")
        module = Path(left).name
        dependencies = tuple(Path(item).name for item in right.split())
        if module in result or any(not item.endswith(".ko") for item in dependencies):
            raise OrderError(f"invalid or duplicate modules.dep module at row {number}")
        result[module] = dependencies
    if len(result) != 441:
        raise OrderError(f"modules.dep row count mismatch: {len(result)}")
    return result


def positions(lines: list[str], name: str) -> list[int]:
    return [index for index, value in enumerate(lines, 1) if value == name]


def unique_selected_order(lines: list[str], selected: set[str]) -> list[str]:
    result: list[str] = []
    for name in lines:
        if name in selected and name not in result:
            result.append(name)
    return result


def dependency_violations(
    order: list[str], dependencies: dict[str, tuple[str, ...]]
) -> list[dict[str, Any]]:
    location = {name: index for index, name in enumerate(order, 1)}
    result: list[dict[str, Any]] = []
    for consumer in order:
        for dependency in dependencies[consumer]:
            if dependency in location and location[dependency] > location[consumer]:
                result.append(
                    {
                        "consumer": consumer,
                        "consumer_position": location[consumer],
                        "dependency": dependency,
                        "dependency_position": location[dependency],
                    }
                )
    return result


def audit(root: Path) -> dict[str, Any]:
    paths = {
        "plan": root / PLAN,
        "first_stage": root / FIRST_STAGE,
        "recovery": root / RECOVERY,
        "dependencies": root / DEPENDENCIES,
        "second_stage": root / SECOND_STAGE,
    }
    identities = {
        name: validate_identity(path, EXPECTED_IDENTITIES[name], name)
        for name, path in paths.items()
    }
    plan = parse_plan(paths["plan"].read_text(encoding="ascii"))
    first = module_lines(paths["first_stage"], "first-stage modules.load")
    recovery = module_lines(paths["recovery"], "recovery modules.load")
    second = module_lines(paths["second_stage"], "vendor_dlkm modules.load")
    dependencies = parse_dependencies(paths["dependencies"])

    first_duplicates = {
        name: count for name, count in collections.Counter(first).items() if count > 1
    }
    recovery_duplicates = {
        name: count for name, count in collections.Counter(recovery).items() if count > 1
    }
    if first_duplicates != EXPECTED_DUPLICATES or recovery_duplicates != EXPECTED_DUPLICATES:
        raise OrderError("first-stage/recovery duplicate geometry mismatch")
    if len(second) != 356 or len(second) != len(set(second)):
        raise OrderError("second-stage modules.load uniqueness mismatch")

    proposed = plan + list(PROPOSED_ADDITIONS)
    selected = set(proposed)
    if len(plan) != 61 or len(proposed) != 67 or len(selected) != 67:
        raise OrderError("proposed module cardinality mismatch")
    first_selected = selected & set(first)
    second_selected = selected & set(second)
    if len(first_selected) != 37 or len(second_selected) != 30:
        raise OrderError("37/30 normal-stage partition mismatch")
    if first_selected & second_selected or selected != first_selected | second_selected:
        raise OrderError("normal-stage partition overlap or uncovered module")
    if not selected <= set(recovery):
        raise OrderError("selected module is absent from recovery order")
    if not selected <= set(dependencies):
        raise OrderError("selected module is absent from modules.dep")

    missing_closure = {
        module: sorted(set(dependencies[module]) - selected)
        for module in sorted(selected)
        if set(dependencies[module]) - selected
    }
    if missing_closure:
        raise OrderError(f"67-module dependency closure is incomplete: {missing_closure}")

    proposed_violations = dependency_violations(proposed, dependencies)
    if proposed_violations:
        raise OrderError(f"proposed native order has forward dependencies: {proposed_violations}")
    normal_order = unique_selected_order(first, selected) + unique_selected_order(second, selected)
    if len(normal_order) != 67 or len(set(normal_order)) != 67:
        raise OrderError("effective normal-stage selected order is incomplete")
    normal_violations = dependency_violations(normal_order, dependencies)
    if len(normal_violations) != 126:
        raise OrderError(f"normal line-order dependency inversion count drift: {len(normal_violations)}")

    rows = []
    for name in proposed:
        rows.append(
            {
                "module": name,
                "source": "p315-base" if name in plan else "max77705-addition",
                "proposed_native_position": proposed.index(name) + 1,
                "p315_position": plan.index(name) + 1 if name in plan else None,
                "normal_stage": "first-stage" if name in first_selected else "vendor_dlkm",
                "first_stage_positions": positions(first, name),
                "vendor_dlkm_positions": positions(second, name),
                "recovery_positions": positions(recovery, name),
                "direct_dependencies": list(dependencies[name]),
            }
        )

    return {
        "schema": SCHEMA,
        "target": TARGET,
        "host_only": True,
        "device_contact": False,
        "inputs": identities,
        "counts": {
            "p315_base_unique": len(plan),
            "additions_unique": len(PROPOSED_ADDITIONS),
            "proposed_unique": len(proposed),
            "first_stage_lines": len(first),
            "first_stage_unique": len(set(first)),
            "recovery_lines": len(recovery),
            "recovery_unique": len(set(recovery)),
            "vendor_dlkm_lines": len(second),
            "vendor_dlkm_unique": len(set(second)),
            "selected_first_stage_unique": len(first_selected),
            "selected_vendor_dlkm_unique": len(second_selected),
        },
        "duplicate_entries": {
            "first_stage": first_duplicates,
            "recovery": recovery_duplicates,
            "vendor_dlkm": {},
        },
        "dependency": {
            "selected_missing_closure": missing_closure,
            "proposed_native_forward_violation_count": len(proposed_violations),
            "normal_line_order_forward_violation_count": len(normal_violations),
            "normal_line_order_is_not_a_direct_finit_module_order": True,
        },
        "proposed_additions": list(PROPOSED_ADDITIONS),
        "proposed_native_order": proposed,
        "proposed_native_order_sha256": hashlib.sha256(
            ("\n".join(proposed) + "\n").encode("ascii")
        ).hexdigest(),
        "effective_normal_selected_order": normal_order,
        "effective_normal_selected_order_sha256": hashlib.sha256(
            ("\n".join(normal_order) + "\n").encode("ascii")
        ).hexdigest(),
        "focused_positions": {
            name: next(row for row in rows if row["module"] == name)
            for name in POSITION_FOCUS
        },
        "modules": rows,
        "interpretation": (
            "The recovered Android line orders are stage and priority authority, not a direct "
            "finit_module sequence. The inherited P3.15 order plus the six dependency-ordered "
            "additions is closed and has zero forward dependency edges."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = repo_root()
    output = args.output if args.output.is_absolute() else (root / args.output).absolute()
    private_root = (root / "workspace/private").resolve()
    try:
        output.relative_to(private_root)
    except ValueError as exc:
        raise SystemExit(f"FAIL: output must remain under workspace/private: {output}") from exc
    if output.exists() or output.is_symlink():
        raise SystemExit(f"FAIL: output already exists: {output}")
    result = audit(root)
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{output.name}.", dir=output.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="ascii") as handle:
            json.dump(result, handle, indent=2, sort_keys=True)
            handle.write("\n")
        temporary.chmod(0o600)
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
    print(json.dumps(result["counts"], indent=2, sort_keys=True))
    print(json.dumps(result["dependency"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
