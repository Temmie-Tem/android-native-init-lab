#!/usr/bin/env python3
"""Plan the module loads a native-init candidate needs, from the images.

The mux command comes from `pdic_max77705.ko`, which Android loads with
`modprobe`.  A candidate that replaces PID 1 has to load it itself, and three
things decide whether that is even possible:

  1. are the modules reachable without mounting `vendor_dlkm`?
  2. which of them the first stage has not already loaded
  3. in what order they can be inserted

`modules.load` and `modules.load.recovery` answer none of (3).  They are
`modprobe` inputs, and `modprobe` resolves order itself from `modules.dep`; the
list order violates dependencies outright.  A candidate calling `finit_module`
directly needs a topological order, which this computes.

Dependencies are read from each module's `.modinfo` `depends=` field with a
minimal ELF section reader, so this adds no dependency of its own.  Nothing here
touches a device.
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path
from typing import Any

SCHEMA = "s22plus_fyg8_p319_module_closure_plan_v1"


class ClosurePlanError(RuntimeError):
    pass


def elf_section(data: bytes, want: str) -> bytes | None:
    """Return one ELF64 section's bytes, or None. Enough for `.modinfo`."""
    if len(data) < 64 or data[:4] != b"\x7fELF" or data[4] != 2:
        raise ClosurePlanError("not an ELF64 object")
    little = data[5] == 1
    endian = "<" if little else ">"
    sh_off = struct.unpack_from(endian + "Q", data, 0x28)[0]
    sh_entsize, sh_num, sh_strndx = struct.unpack_from(endian + "HHH", data, 0x3A)
    def header(index: int) -> tuple[int, int, int]:
        base = sh_off + index * sh_entsize
        name = struct.unpack_from(endian + "I", data, base)[0]
        offset, size = struct.unpack_from(endian + "QQ", data, base + 24)
        return name, offset, size
    _, str_off, str_size = header(sh_strndx)
    names = data[str_off : str_off + str_size]
    for index in range(sh_num):
        name, offset, size = header(index)
        end = names.find(b"\x00", name)
        if names[name:end].decode("utf-8", "replace") == want:
            return data[offset : offset + size]
    return None


def modinfo(path: Path) -> dict[str, list[str]]:
    section = elf_section(path.read_bytes(), ".modinfo")
    if section is None:
        raise ClosurePlanError(f"no .modinfo section: {path.name}")
    values: dict[str, list[str]] = {}
    for item in section.split(b"\x00"):
        if b"=" in item:
            key, _, value = item.partition(b"=")
            values.setdefault(key.decode("utf-8", "replace"), []).append(
                value.decode("utf-8", "replace")
            )
    return values


def direct_dependencies(path: Path) -> list[str]:
    depends = modinfo(path).get("depends", [""])[0]
    return [f"{name}.ko" for name in depends.split(",") if name]


def read_list(path: Path) -> list[str]:
    if not path.is_file():
        return []
    return [line.strip() for line in path.read_text(errors="replace").splitlines() if line.strip()]


def dep_closure(modules_dir: Path, target: str) -> list[str]:
    line_prefix = f"/lib/modules/{target}:"
    for line in read_list(modules_dir / "modules.dep"):
        if line.startswith(line_prefix):
            return [item.split("/")[-1] for item in line.split(":", 1)[1].split()]
    raise ClosurePlanError(f"{target} not in modules.dep")


def topological(modules_dir: Path, members: list[str]) -> list[str]:
    inside = set(members)
    graph = {
        name: [d for d in direct_dependencies(modules_dir / name) if d in inside]
        for name in members
    }
    order: list[str] = []
    done: set[str] = set()
    active: set[str] = set()

    def visit(name: str) -> None:
        if name in done:
            return
        if name in active:
            raise ClosurePlanError(f"dependency cycle at {name}")
        active.add(name)
        for dependency in graph[name]:
            visit(dependency)
        active.discard(name)
        done.add(name)
        order.append(name)

    for name in members:
        visit(name)
    return order


def order_violations(order: list[str], modules_dir: Path, members: list[str]) -> list[dict[str, str]]:
    """Dependencies a candidate order would load after their dependant."""
    inside = set(members)
    position = {name: index for index, name in enumerate(order)}
    problems = []
    for name in members:
        if name not in position:
            continue
        for dependency in direct_dependencies(modules_dir / name):
            if dependency in inside and position.get(dependency, -1) > position[name]:
                problems.append({"module": name, "needs": dependency})
    return problems


def plan(modules_dir: Path, target: str) -> dict[str, Any]:
    closure = dep_closure(modules_dir, target)
    members = closure + [target]
    present = {name: (modules_dir / name).is_file() for name in members}
    first_stage = read_list(modules_dir / "modules.load")
    recovery = read_list(modules_dir / "modules.load.recovery")
    marginal = [name for name in members if name not in set(first_stage)]
    insmod_order = topological(modules_dir, marginal)
    recovery_order = [name for name in recovery if name in set(marginal)]
    return {
        "schema": SCHEMA,
        "modules_dir": str(modules_dir),
        "target": target,
        "closure_size": len(closure),
        "members": len(members),
        "all_present": all(present.values()),
        "missing": sorted(name for name, ok in present.items() if not ok),
        "first_stage_list": len(first_stage),
        "recovery_list": len(recovery),
        "already_loaded_by_first_stage": sorted(
            name for name in members if name in set(first_stage)
        ),
        "marginal_count": len(marginal),
        "insmod_order": insmod_order,
        "recovery_order": recovery_order,
        # The point of the tool: the shipped list order is not an insmod order.
        "recovery_order_is_insmod_safe": not order_violations(
            recovery_order, modules_dir, marginal
        ),
        "recovery_order_violations": order_violations(
            recovery_order, modules_dir, marginal
        ),
        "insmod_order_is_safe": not order_violations(
            insmod_order, modules_dir, marginal
        ),
        "vermagic": sorted(
            {modinfo(modules_dir / name).get("vermagic", [""])[0] for name in members}
        ),
        "device_contact": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("modules_dir", type=Path)
    parser.add_argument("--target", default="pdic_max77705.ko")
    args = parser.parse_args(argv)
    print(json.dumps(plan(args.modules_dir, args.target), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
