#!/usr/bin/env python3
"""Derive a host-side S22+ observable native-init module recipe.

Input is a private M1 capture text file containing:

- ### proc_modules
- ### module_metadata

The script deduplicates modules.load, parses modules.dep, computes dependency
closures for selected observation roles, and writes a redacted JSON recipe for
future native-init work. It is host-only: no adb, no device mutation.
"""

from __future__ import annotations

import argparse
import json
from collections import OrderedDict
from pathlib import Path


DEFAULT_RUN_ROOT = Path("workspace/private/runs")
DEFAULT_OUTPUT_ROOT = Path("workspace/private/outputs/s22plus_observable_init_recipe")

ROLE_ANCHORS = {
    "usb_observation_core": [
        "phy-msm-ssusb-qmp.ko",
        "phy-msm-snps-eusb2.ko",
        "dwc3-msm.ko",
        "usb_f_ss_mon_gadget.ko",
        "usb_f_diag.ko",
        "usb_f_qdss.ko",
        "usb_f_gsi.ko",
        "usb_f_conn_gadget.ko",
        "usb_f_ss_acm.ko",
    ],
    "usb_android_support": [
        "usb_notifier_qcom.ko",
        "usb_notify_layer.ko",
        "usb_typec_manager.ko",
        "usb_bam.ko",
        "qc_usb_audio.ko",
        "redriver.ko",
        "if_cb_manager.ko",
        "pdic_max77705.ko",
        "mfd_max77705.ko",
    ],
    "display_probe": [
        "lcd.ko",
        "gpucc-waipio.ko",
        "msm_kgsl.ko",
        "msm_drm.ko",
    ],
}

CONFIGFS_FUNCTIONS = [
    "ffs.adb",
    "ncm.0",
    "rndis.rndis",
]


def find_latest_capture() -> Path:
    candidates = sorted(
        DEFAULT_RUN_ROOT.glob(
            "s22plus_magisk_boot_time_capture_m1_*/device_capture/s22plus_boot_capture_m1/post_fs_data_*.txt"
        ),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise SystemExit("no M1 post_fs_data capture found; pass --capture-file")
    return candidates[0]


def section(lines: list[str], header: str, next_header: str | None = None) -> list[str]:
    try:
        start = lines.index(header) + 1
    except ValueError:
        return []
    end = len(lines)
    if next_header is not None:
        try:
            end = lines.index(next_header, start)
        except ValueError:
            pass
    else:
        for idx in range(start, len(lines)):
            if lines[idx].startswith("### "):
                end = idx
                break
    return lines[start:end]


def basename_module(path: str) -> str:
    name = path.strip().split("/")[-1]
    return name


def parse_module_metadata(lines: list[str]) -> tuple[OrderedDict[str, int], dict[str, list[str]]]:
    load_order: OrderedDict[str, int] = OrderedDict()
    deps: dict[str, list[str]] = {}
    current = ""
    raw_index = 0
    for line in lines:
        if line.startswith("--- "):
            current = line[4:].strip()
            continue
        stripped = line.strip()
        if not stripped:
            continue
        if current.endswith("modules.load"):
            raw_index += 1
            module = basename_module(stripped)
            load_order.setdefault(module, raw_index)
        elif current.endswith("modules.dep") and ":" in stripped:
            target, dep_text = stripped.split(":", 1)
            target_module = basename_module(target)
            dep_modules = [basename_module(item) for item in dep_text.split() if item.strip()]
            deps[target_module] = dep_modules
    return load_order, deps


def parse_loaded_modules(lines: list[str]) -> list[str]:
    modules: list[str] = []
    for line in lines:
        if not line.strip():
            continue
        modules.append(line.split()[0])
    return modules


def module_to_proc_name(module: str) -> str:
    return module.removesuffix(".ko").replace("-", "_")


def closure_for(anchors: list[str], deps: dict[str, list[str]]) -> set[str]:
    seen: set[str] = set()

    def visit(module: str) -> None:
        if module in seen:
            return
        seen.add(module)
        for dep in deps.get(module, []):
            visit(dep)

    for anchor in anchors:
        visit(anchor)
    return seen


def ordered_modules(modules: set[str], load_order: OrderedDict[str, int]) -> list[str]:
    return sorted(modules, key=lambda module: (load_order.get(module, 10**9), module))


def role_recipe(name: str, anchors: list[str], load_order: OrderedDict[str, int], deps: dict[str, list[str]], loaded: set[str]) -> dict[str, object]:
    closure = closure_for(anchors, deps)
    ordered = ordered_modules(closure, load_order)
    missing_from_load = sorted(module for module in closure if module not in load_order)
    missing_from_live = sorted(module for module in closure if module_to_proc_name(module) not in loaded)
    return {
        "anchors": anchors,
        "closure_count": len(ordered),
        "modules": ordered,
        "missing_from_modules_load": missing_from_load,
        "missing_from_live_proc_modules": missing_from_live,
        "load_order_positions": {module: load_order.get(module) for module in ordered if module in load_order},
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-file", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args(argv)

    capture_file = args.capture_file or find_latest_capture()
    text = capture_file.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    metadata = section(lines, "### module_metadata", "### usb_configfs_tree")
    proc_modules = section(lines, "### proc_modules", "### module_metadata")
    load_order, deps = parse_module_metadata(metadata)
    loaded_modules = set(parse_loaded_modules(proc_modules))

    roles = {
        name: role_recipe(name, anchors, load_order, deps, loaded_modules)
        for name, anchors in ROLE_ANCHORS.items()
    }
    all_usb_modules = set(roles["usb_observation_core"]["modules"]) | set(roles["usb_android_support"]["modules"])
    usb_first_ordered = ordered_modules(all_usb_modules, load_order)

    recipe = {
        "source_capture": str(capture_file),
        "source_capture_private": True,
        "modules_load_unique_count": len(load_order),
        "modules_dep_count": len(deps),
        "proc_modules_count": len(loaded_modules),
        "roles": roles,
        "usb_first_combined": {
            "module_count": len(usb_first_ordered),
            "modules": usb_first_ordered,
        },
        "configfs_functions_seen_by_m1": CONFIGFS_FUNCTIONS,
        "interpretation": [
            "Magisk post-fs-data already sees USB/display/GPU modules loaded; use modules.load/modules.dep as ordering input.",
            "ffs.adb and ncm.0 are configfs functions in the live gadget, not modules found in modules.load.",
            "Use USB-first modules for the first native-init observability candidate; defer display_probe until USB/pstore observation works.",
        ],
    }

    output_dir = args.output_dir or DEFAULT_OUTPUT_ROOT / capture_file.parent.parent.parent.name
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "observable_init_recipe.json"
    output_path.write_text(json.dumps(recipe, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(output_path)
    print(json.dumps({
        "modules_load_unique_count": recipe["modules_load_unique_count"],
        "modules_dep_count": recipe["modules_dep_count"],
        "proc_modules_count": recipe["proc_modules_count"],
        "usb_first_module_count": recipe["usb_first_combined"]["module_count"],
        "display_probe_module_count": roles["display_probe"]["closure_count"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(__import__("sys").argv[1:]))
