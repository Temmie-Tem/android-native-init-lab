#!/usr/bin/env python3
"""Cross-check the FYG8 USB role chain on stock Android without device writes."""

from __future__ import annotations

import argparse
import json
import re
import shlex
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import s22plus_fyg8_usb_role_static_re as static_re
import s22plus_stock_usb_topology_readonly as topology


ROOT = Path(__file__).resolve().parents[5]
TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
SCHEMA = "s22plus_stock_usb_role_crosscheck_readonly_v1"
EXPECTED_BOOT_SHA256 = "2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e"
DEFAULT_RUN_ROOT = Path("workspace/private/runs")
DEFAULT_PUBLISH = Path("docs/module-map/s22plus-fyg8/deep-usb-re/live-crosscheck.json")

EXPECTED_MODULES = (
    "pdic_max77705",
    "usb_typec_manager",
    "usb_notifier_qcom",
    "usb_notify_layer",
    "dwc3_msm",
)

DEVICE_COMMANDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("dt_model", ("su", "-c", "cat /proc/device-tree/model")),
    ("dt_symbol_usb0", ("su", "-c", "cat /proc/device-tree/__symbols__/usb0")),
    ("dt_symbol_ucsi", ("su", "-c", "cat /proc/device-tree/__symbols__/ucsi")),
    (
        "dt_symbol_qupv3_se5_i2c",
        ("su", "-c", "cat /proc/device-tree/__symbols__/qupv3_se5_i2c"),
    ),
    (
        "dt_parent_role_switch_size",
        ("su", "-c", "stat -c %s /proc/device-tree/soc/ssusb@a600000/usb-role-switch"),
    ),
    (
        "dt_child_role_switch_size",
        (
            "su",
            "-c",
            "stat -c %s /proc/device-tree/soc/ssusb@a600000/dwc3@a600000/usb-role-switch",
        ),
    ),
    (
        "dt_child_dr_mode",
        ("su", "-c", "cat /proc/device-tree/soc/ssusb@a600000/dwc3@a600000/dr_mode"),
    ),
    (
        "dt_max77705_compatible",
        ("su", "-c", "cat /proc/device-tree/soc/i2c@994000/max77705@66/compatible"),
    ),
    (
        "dt_max77705_status",
        ("su", "-c", "cat /proc/device-tree/soc/i2c@994000/max77705@66/status"),
    ),
    (
        "dt_pdic_compatible",
        (
            "su",
            "-c",
            "cat /proc/device-tree/soc/i2c@994000/max77705@66/max77705_pdic/compatible",
        ),
    ),
    (
        "dt_pdic_status",
        (
            "su",
            "-c",
            "cat /proc/device-tree/soc/i2c@994000/max77705@66/max77705_pdic/status",
        ),
    ),
    (
        "dt_pdic_role_swap_size",
        (
            "su",
            "-c",
            "stat -c %s /proc/device-tree/soc/i2c@994000/max77705@66/max77705_pdic/support_pd_role_swap",
        ),
    ),
    (
        "dt_usb_notifier_compatible",
        ("su", "-c", "cat /proc/device-tree/soc/usb-notifier/compatible"),
    ),
    (
        "bind_max77705_driver",
        (
            "su",
            "-c",
            "readlink -f /sys/module/pdic_max77705/drivers/platform:max77705-usbc",
        ),
    ),
    (
        "bind_usb_notifier_driver",
        (
            "su",
            "-c",
            "readlink -f /sys/module/usb_notifier_qcom/drivers/platform:usb_notifier",
        ),
    ),
    (
        "bind_dwc3_msm_driver",
        (
            "su",
            "-c",
            "readlink -f /sys/module/dwc3_msm/drivers/platform:msm-dwc3",
        ),
    ),
    (
        "bind_usb_notifier_module",
        (
            "su",
            "-c",
            "readlink -f /sys/bus/platform/drivers/usb_notifier/soc:usb-notifier/driver/module",
        ),
    ),
    (
        "bind_ssusb_module",
        (
            "su",
            "-c",
            "readlink -f /sys/devices/platform/soc/a600000.ssusb/driver/module",
        ),
    ),
    (
        "bind_typec_module",
        ("su", "-c", "readlink -f /sys/class/typec/port0/device/driver/module"),
    ),
    ("dmesg", ("su", "-c", "dmesg")),
)

LOG_MARKERS = (
    "max77705_ccic_event_notifier",
    "manager_handle_pdic_notification",
    "manager_event_notify",
    "ccic_usb_handle_notification",
    "send_otg_notify",
    "dwc_msm_id_event",
    "dwc_msm_vbus_event",
)
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


class CrosscheckError(ValueError):
    pass


def resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path.resolve())


def scalar(result: dict[str, Any]) -> str:
    return result["stdout"].replace("\x00", "").strip()


def compatible_values(result: dict[str, Any]) -> list[str]:
    return [value for value in result["stdout"].split("\x00") if value]


def filtered_dmesg(text: str) -> str:
    clean = ANSI_RE.sub("", text)
    lines = [line for line in clean.splitlines() if any(marker in line for marker in LOG_MARKERS)]
    return "\n".join(lines[-256:]) + ("\n" if lines else "")


def relay_sequence_count(text: str) -> int:
    expected = (
        "max77705_ccic_event_notifier",
        "manager_handle_pdic_notification",
        "manager_event_notify:",
        "manager_event_notify: notify done",
    )
    state = 0
    count = 0
    for line in text.splitlines():
        marker = expected[state]
        if marker in line:
            state += 1
            if state == len(expected):
                count += 1
                state = 0
        elif expected[0] in line:
            state = 1
    return count


def collect_extra(serial: str) -> dict[str, dict[str, Any]]:
    commands: dict[str, dict[str, Any]] = {}
    for label, argv in DEVICE_COMMANDS:
        result = topology.adb_command(serial, argv, timeout=60.0 if label == "dmesg" else 30.0)
        if label == "dmesg" and result["rc"] == 0:
            result["stdout"] = filtered_dmesg(result["stdout"])
        commands[label] = result
    return commands


def summarize(
    static_payload: dict[str, Any],
    baseline: dict[str, Any],
    baseline_commands: dict[str, dict[str, Any]],
    commands: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    modules_text = baseline_commands["proc_modules"]["stdout"]
    modules = {
        name: bool(re.search(rf"(?m)^{re.escape(name)}\s", modules_text))
        for name in EXPECTED_MODULES
    }
    dt = {
        "model": scalar(commands["dt_model"]),
        "usb0_symbol": scalar(commands["dt_symbol_usb0"]),
        "ucsi_symbol": scalar(commands["dt_symbol_ucsi"]),
        "qupv3_se5_i2c_symbol": scalar(commands["dt_symbol_qupv3_se5_i2c"]),
        "parent_role_switch_property_size": scalar(commands["dt_parent_role_switch_size"]),
        "child_role_switch_property_size": scalar(commands["dt_child_role_switch_size"]),
        "child_dr_mode": scalar(commands["dt_child_dr_mode"]),
        "max77705_compatible": compatible_values(commands["dt_max77705_compatible"]),
        "max77705_status": scalar(commands["dt_max77705_status"]),
        "pdic_compatible": compatible_values(commands["dt_pdic_compatible"]),
        "pdic_status": scalar(commands["dt_pdic_status"]),
        "pdic_role_swap_property_size": scalar(commands["dt_pdic_role_swap_size"]),
        "usb_notifier_compatible": compatible_values(commands["dt_usb_notifier_compatible"]),
    }
    binds = {
        "max77705_driver": scalar(commands["bind_max77705_driver"]),
        "usb_notifier_driver": scalar(commands["bind_usb_notifier_driver"]),
        "dwc3_msm_driver": scalar(commands["bind_dwc3_msm_driver"]),
        "usb_notifier_module": scalar(commands["bind_usb_notifier_module"]),
        "ssusb_module": scalar(commands["bind_ssusb_module"]),
        "typec_module": scalar(commands["bind_typec_module"]),
    }
    dt_checks = {
        "active_g0q_revision_12": "board-id,12" in dt["model"],
        "usb0_symbol_exact": dt["usb0_symbol"] == "/soc/ssusb@a600000",
        "ucsi_symbol_exact": dt["ucsi_symbol"] == "/soc/qcom,pmic_glink/qcom,ucsi",
        "qupv3_se5_i2c_symbol_exact": dt["qupv3_se5_i2c_symbol"] == "/soc/i2c@994000",
        "parent_role_switch_present": dt["parent_role_switch_property_size"] == "0",
        "child_role_switch_present": dt["child_role_switch_property_size"] == "0",
        "child_otg_mode": dt["child_dr_mode"] == "otg",
        "max77705_compatible": "maxim,max77705" in dt["max77705_compatible"],
        "max77705_enabled": dt["max77705_status"] in {"ok", "okay"},
        "pdic_compatible": "maxim,max77705_pdic" in dt["pdic_compatible"],
        "pdic_enabled": dt["pdic_status"] in {"ok", "okay"},
        "pd_role_swap_present": dt["pdic_role_swap_property_size"] == "0",
        "usb_notifier_compatible": "samsung,usb-notifier" in dt["usb_notifier_compatible"],
    }
    bind_checks = {
        "max77705_driver": binds["max77705_driver"].endswith("/max77705-usbc"),
        "usb_notifier_driver": binds["usb_notifier_driver"].endswith("/usb_notifier"),
        "dwc3_msm_driver": binds["dwc3_msm_driver"].endswith("/msm-dwc3"),
        "usb_notifier_module": binds["usb_notifier_module"].endswith("/usb_notifier_qcom"),
        "ssusb_module": binds["ssusb_module"].endswith("/dwc3_msm"),
        "typec_module": binds["typec_module"].endswith("/pdic_max77705"),
    }
    command_failures = sorted(
        label for label, result in commands.items() if result["rc"] != 0 or result["timeout"]
    )
    log = commands["dmesg"]["stdout"]
    sequences = relay_sequence_count(log)
    downstream_markers = {
        marker: marker in log
        for marker in (
            "ccic_usb_handle_notification",
            "send_otg_notify",
            "dwc_msm_id_event",
            "dwc_msm_vbus_event",
        )
    }
    static_ok = static_payload.get("result") == "pass-static-role-path-reconstructed"
    baseline_ok = (
        baseline.get("result") == "pass-stock-topology-partial"
        and baseline.get("stock_state", {}).get("boot_sha256") == EXPECTED_BOOT_SHA256
    )
    required = (
        static_ok
        and baseline_ok
        and all(modules.values())
        and all(dt_checks.values())
        and all(bind_checks.values())
        and not command_failures
        and sequences > 0
    )
    return {
        "schema": SCHEMA,
        "result": "pass-live-role-crosscheck-partial" if required else "fail",
        "target": TARGET,
        "captured_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "static_result": static_payload.get("result", "missing"),
        "baseline_result": baseline.get("result", "missing"),
        "modules_loaded": modules,
        "device_tree": dt,
        "device_tree_checks": dt_checks,
        "driver_binds": binds,
        "driver_bind_checks": bind_checks,
        "notifier_log": {
            "filtered_lines": log.splitlines(),
            "pdic_to_manager_relay_sequence_count": sequences,
            "downstream_usb_role_markers": downstream_markers,
        },
        "command_failures": command_failures,
        "conclusions": {
            "exact_fyg8_automatic_role_path": "ELF_SOURCE_DT_VERIFIED" if static_ok else "UNVERIFIABLE",
            "stock_components_and_dt": "LIVE_BOUND" if required else "UNVERIFIABLE",
            "pdic_to_typec_manager_relay": "LIVE_OBSERVED" if sequences > 0 else "NOT_CAPTURED_THIS_BOOT",
            "typec_manager_notifier_dispatch": "LIVE_OBSERVED" if sequences > 0 else "NOT_CAPTURED_THIS_BOOT",
            "usb_attach_through_usb_notifier_qcom": (
                "LIVE_LOG_HINT" if downstream_markers["ccic_usb_handle_notification"] else "NOT_CAPTURED_THIS_BOOT"
            ),
            "usb_notifier_to_dwc3_role_event": (
                "LIVE_LOG_HINT"
                if downstream_markers["dwc_msm_id_event"] or downstream_markers["dwc_msm_vbus_event"]
                else "NOT_CAPTURED_THIS_BOOT"
            ),
            "direct_pid1_automatic_role_without_samsung_chain": "NOT_PROVED",
            "direct_pid1_forced_peripheral_bypass": "PLAUSIBLE_NOT_PROVED",
        },
        "safety": {
            "device_read_only": True,
            "serial_redacted": True,
            "flash": False,
            "reboot": False,
            "partition_write": False,
            "module_insertion": False,
            "service_control": False,
            "sysfs_write": False,
            "configfs_write": False,
        },
    }


def offline_check() -> dict[str, Any]:
    root_read_programs = {"cat", "dmesg", "readlink", "stat"}
    fixed_read_commands: dict[str, bool] = {}
    for label, argv in DEVICE_COMMANDS:
        try:
            shell_argv = shlex.split(argv[2]) if len(argv) == 3 and argv[:2] == ("su", "-c") else []
        except ValueError:
            shell_argv = []
        fixed_read_commands[label] = (
            bool(shell_argv)
            and shell_argv[0] in root_read_programs
            and not any(token in argv[2] for token in (";", "|", "&", ">", "<", "`", "$("))
        )
    topology_contract = topology.offline_check()
    passed = all(fixed_read_commands.values()) and topology_contract["result"] == "pass"
    return {
        "result": "pass" if passed else "fail",
        "target": TARGET,
        "device_command_count": len(DEVICE_COMMANDS),
        "fixed_read_commands": fixed_read_commands,
        "baseline_contract": topology_contract["result"],
        "safety": {
            "read_only": True,
            "flash": False,
            "reboot": False,
            "module_insertion": False,
            "service_control": False,
            "sysfs_write": False,
            "configfs_write": False,
        },
    }


def allocate_run_dir(base: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = base / f"s22plus_stock_usb_role_crosscheck_readonly_{stamp}"
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serial")
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
    parser.add_argument("--publish", type=Path, default=DEFAULT_PUBLISH)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    contract = offline_check()
    if contract["result"] != "pass":
        raise CrosscheckError("read-only command contract failed")
    static_payload = static_re.build_payload()
    if args.dry_run:
        print(json.dumps({"result": "pass-dry-run", "contract": contract}, indent=2, sort_keys=True))
        return 0

    serial = topology.select_serial(args.serial)
    run_dir = allocate_run_dir(resolve(args.run_root))
    baseline, baseline_commands = topology.collect(serial)
    commands = collect_extra(serial)
    payload = summarize(static_payload, baseline, baseline_commands, commands)
    payload["serial"] = "<S22_SERIAL_REDACTED>"
    payload["private_run"] = rel(run_dir)
    write_json(run_dir / "contract.json", contract)
    write_json(run_dir / "baseline.json", baseline)
    write_json(run_dir / "baseline-commands.json", baseline_commands)
    write_json(run_dir / "commands.json", commands)
    write_json(run_dir / "result.json", payload)
    write_json(resolve(args.publish), payload)
    print(
        json.dumps(
            {
                "result": payload["result"],
                "private_run": rel(run_dir),
                "publish": rel(resolve(args.publish)),
                "relay_sequences": payload["notifier_log"]["pdic_to_manager_relay_sequence_count"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if payload["result"] == "pass-live-role-crosscheck-partial" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (CrosscheckError, static_re.StaticReError, topology.TopologyError) as exc:
        print(f"USB role cross-check failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
