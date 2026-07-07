#!/usr/bin/env python3
"""Host-only SM8450/S22+ OpenOCD target-cfg derivation audit.

This helper performs no device action.  It decompiles the stock S22+ DTB with
dtc, extracts APSS CPU and CTI topology, and checks that the public OpenOCD cfg
matches the source-derived CTI bases without inventing an unproven DBGBASE list.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_RUN_ROOT = Path("workspace/private/runs")
DEFAULT_DTB = Path(
    "workspace/private/inputs/s22plus_firmware/S906NKSS7FYG8_SKC/"
    "extracted-images/unpack-vendor-boot/dtb"
)
DEFAULT_CFG = Path("workspace/public/src/openocd/target/qualcomm/sm8450_s22plus_romtable.cfg")
PRIVATE_DTC = Path("workspace/private/tools/dtc_pkg/sysroot/usr/bin/dtc")
EXPECTED_TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
EXPECTED_CTIBASE = [0x12010000 + (index * 0x10000) for index in range(8)]


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".git").is_dir():
            return parent
    raise RuntimeError(f"could not locate repo root from {current}")


def resolve(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else root / path


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)


def resolve_run_dir(root: Path, requested: Path | None) -> Path:
    if requested is not None:
        run_dir = resolve(root, requested)
        run_dir.mkdir(parents=True, exist_ok=False)
        return run_dir
    stamp = utc_now().replace("-", "").replace(":", "").replace("Z", "Z")
    base = resolve(root, DEFAULT_RUN_ROOT / f"s22plus_sm8450_openocd_target_cfg_audit_{stamp}")
    for suffix in range(100):
        run_dir = base if suffix == 0 else Path(f"{base}_{suffix:02d}")
        try:
            run_dir.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            continue
        return run_dir
    raise SystemExit(f"could not allocate unique run directory under {base.parent}")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run_command(argv: list[str | Path], timeout: float = 20.0) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            [str(part) for part in argv],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            check=False,
        )
        return {
            "argv": [str(part) for part in argv],
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "timeout": False,
        }
    except FileNotFoundError as exc:
        return {
            "argv": [str(part) for part in argv],
            "returncode": 127,
            "stdout": "",
            "stderr": str(exc),
            "timeout": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "argv": [str(part) for part in argv],
            "returncode": 124,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
            "timeout": True,
        }


def choose_dtc(root: Path, requested: Path | None) -> Path | None:
    candidates: list[Path] = []
    if requested is not None:
        candidates.append(resolve(root, requested))
    candidates.append(resolve(root, PRIVATE_DTC))
    system = shutil.which("dtc")
    if system:
        candidates.append(Path(system))
    for candidate in candidates:
        if candidate.is_file() and candidate.stat().st_mode & 0o111:
            return candidate
    return None


def decompile_dtb(dtc: Path, dtb: Path, out_dts: Path) -> dict[str, Any]:
    result = run_command([dtc, "-I", "dtb", "-O", "dts", "-o", out_dts, dtb], timeout=30.0)
    write_text(out_dts.with_suffix(out_dts.suffix + ".stderr"), result["stderr"])
    return result


def parse_cell_values(text: str) -> list[int]:
    return [int(value, 16) for value in re.findall(r"0x[0-9a-fA-F]+", text)]


def parse_cpu_reg(cells: str) -> int | None:
    values = parse_cell_values(cells)
    if len(values) == 1:
        return values[0]
    if len(values) >= 2:
        return (values[0] << 32) | values[1]
    return None


def parse_reg_addr_size(cells: str) -> tuple[int, int] | None:
    values = parse_cell_values(cells)
    if len(values) == 2:
        return values[0], values[1]
    if len(values) >= 4:
        return ((values[0] << 32) | values[1], (values[2] << 32) | values[3])
    return None


def node_blocks(dts: str, prefix: str) -> list[tuple[str, str]]:
    pattern = re.compile(rf"(?ms)^\s*(?P<node>{re.escape(prefix)}@[^\s{{]+)\s*\{{\n(?P<body>.*?^\s*\}};)")
    return [(match.group("node"), match.group("body")) for match in pattern.finditer(dts)]


def extract_cpus(dts: str) -> list[dict[str, Any]]:
    cpus: list[dict[str, Any]] = []
    for node, body in node_blocks(dts, "cpu"):
        reg = re.search(r"\breg\s*=\s*<(?P<cells>[^>]+)>;", body)
        phandle = re.search(r"\bphandle\s*=\s*<(?P<cells>[^>]+)>;", body)
        cpus.append(
            {
                "node": node,
                "reg": parse_cpu_reg(reg.group("cells")) if reg else None,
                "phandle": parse_cell_values(phandle.group("cells"))[0] if phandle else None,
            }
        )
    return sorted(cpus, key=lambda item: item["reg"] if item["reg"] is not None else -1)


def extract_cpu_ctis(dts: str) -> list[dict[str, Any]]:
    ctis: list[dict[str, Any]] = []
    for node, body in node_blocks(dts, "cti"):
        name = re.search(r'coresight-name\s*=\s*"coresight-cti-cpu(?P<cpu>[0-7])";', body)
        if not name:
            continue
        reg = re.search(r"\breg\s*=\s*<(?P<cells>[^>]+)>;", body)
        addr_size = parse_reg_addr_size(reg.group("cells")) if reg else None
        ctis.append(
            {
                "cpu": int(name.group("cpu")),
                "node": node,
                "reg_addr": addr_size[0] if addr_size else None,
                "reg_size": addr_size[1] if addr_size else None,
            }
        )
    return sorted(ctis, key=lambda item: item["cpu"])


def collect_debugbase_hints(dts: str) -> list[dict[str, Any]]:
    hints: list[dict[str, Any]] = []
    patterns = [
        re.compile(r"dbgbase|debug-base", re.IGNORECASE),
        re.compile(r"coresight-[^;\n]*debug|debug[^;\n]*coresight", re.IGNORECASE),
        re.compile(r"cpu[^;\n]*debug|debug[^;\n]*cpu", re.IGNORECASE),
        re.compile(r"^\s*debug@12[0-9a-fA-F]+", re.IGNORECASE),
    ]
    false_positive = re.compile(r"cpufreq|epss", re.IGNORECASE)
    for line_no, line in enumerate(dts.splitlines(), start=1):
        stripped = line.strip()
        if false_positive.search(stripped):
            continue
        if any(pattern.search(stripped) for pattern in patterns):
            hints.append({"line": line_no, "text": stripped})
    return hints


def collect_trace_hints(dts: str) -> dict[str, Any]:
    ete_names = sorted(set(re.findall(r'coresight-name\s*=\s*"coresight-ete([0-7])";', dts)))
    funnel_ete = bool(re.search(r"\bfunnel_ete\s*\{", dts))
    return {
        "ete_count": len(ete_names),
        "ete_indices": [int(value) for value in ete_names],
        "funnel_ete_present": funnel_ete,
    }


def inspect_cfg(cfg: Path, expected_ctibase: list[int]) -> dict[str, Any]:
    if not cfg.is_file():
        return {"present": False, "checks_passed": False, "reasons": ["cfg-missing"]}
    text = cfg.read_text(encoding="utf-8")
    command_text = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))
    reasons: list[str] = []
    for addr in expected_ctibase:
        if f"0x{addr:08x}" not in text:
            reasons.append(f"missing-ctibase-0x{addr:08x}")
    if "-dbgbase" in command_text:
        reasons.append("cfg-hardcodes-dbgbase")
    if "ROM table" not in text and "ROM-table" not in text:
        reasons.append("cfg-missing-romtable-note")
    return {
        "present": True,
        "path": str(cfg),
        "checks_passed": not reasons,
        "reasons": reasons,
        "hardcodes_dbgbase": "-dbgbase" in command_text,
    }


def classify(cpus: list[dict[str, Any]], ctis: list[dict[str, Any]], dbgbase_hints: list[dict[str, Any]], cfg: dict[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    cti_by_cpu = {item["cpu"]: item["reg_addr"] for item in ctis}
    expected_by_cpu = {index: addr for index, addr in enumerate(EXPECTED_CTIBASE)}
    if len(cpus) != 8:
        reasons.append(f"cpu-count-{len(cpus)}")
    missing_cti = [cpu for cpu in range(8) if cpu not in cti_by_cpu]
    if missing_cti:
        reasons.append("missing-cti-cpu-" + ",".join(str(cpu) for cpu in missing_cti))
    wrong_cti = [
        cpu for cpu, expected in expected_by_cpu.items() if cti_by_cpu.get(cpu) is not None and cti_by_cpu[cpu] != expected
    ]
    if wrong_cti:
        reasons.append("wrong-cti-cpu-" + ",".join(str(cpu) for cpu in wrong_cti))
    if not cfg["present"]:
        reasons.append("cfg-missing")
    elif not cfg["checks_passed"]:
        reasons.extend(cfg["reasons"])

    if reasons:
        result = "blocked_sm8450_cfg_source_mismatch"
    elif dbgbase_hints:
        result = "sm8450_cfg_source_has_dbgbase_hints"
    else:
        result = "sm8450_cfg_draft_ready_romtable_dbgbase"
        reasons.append("dbgbase-not-source-proven-romtable-required")
    return {"result": result, "reasons": reasons}


def build_report(root: Path, args: argparse.Namespace) -> tuple[Path, dict[str, Any]]:
    run_dir = resolve_run_dir(root, args.run_dir)
    dtb = resolve(root, args.dtb)
    cfg_path = resolve(root, args.cfg)
    dtc = choose_dtc(root, args.dtc)

    summary: dict[str, Any] = {
        "generated_at_utc": utc_now(),
        "target": EXPECTED_TARGET,
        "device_action": False,
        "writes_performed": False,
        "reboots_performed": False,
        "flashes_performed": False,
        "sysfs_writes_performed": False,
        "dtb": str(dtb),
        "cfg": str(cfg_path),
        "dtc": str(dtc) if dtc else None,
    }
    if dtc is None:
        summary["classification"] = {"result": "blocked_missing_dtc", "reasons": ["dtc-missing"]}
        write_text(run_dir / "summary.json", json.dumps(summary, indent=2, sort_keys=True) + "\n")
        return run_dir, summary
    if not dtb.is_file():
        summary["classification"] = {"result": "blocked_missing_dtb", "reasons": ["dtb-missing"]}
        write_text(run_dir / "summary.json", json.dumps(summary, indent=2, sort_keys=True) + "\n")
        return run_dir, summary

    dts_path = run_dir / "vendor_boot.dts"
    decompile = decompile_dtb(dtc, dtb, dts_path)
    summary["decompile"] = {
        "returncode": decompile["returncode"],
        "timeout": decompile["timeout"],
        "stderr_path": str(dts_path.with_suffix(dts_path.suffix + ".stderr")),
    }
    if decompile["returncode"] != 0 or decompile["timeout"]:
        summary["classification"] = {"result": "blocked_dtc_decompile_failed", "reasons": ["dtc-decompile-failed"]}
        write_text(run_dir / "summary.json", json.dumps(summary, indent=2, sort_keys=True) + "\n")
        return run_dir, summary

    dts = dts_path.read_text(encoding="utf-8")
    cpus = extract_cpus(dts)
    ctis = extract_cpu_ctis(dts)
    dbgbase_hints = collect_debugbase_hints(dts)
    cfg = inspect_cfg(cfg_path, EXPECTED_CTIBASE)
    summary.update(
        {
            "cpu_count": len(cpus),
            "cpus": cpus,
            "cpu_cti_count": len(ctis),
            "cpu_ctis": ctis,
            "dbgbase_hint_count": len(dbgbase_hints),
            "dbgbase_hints": dbgbase_hints[:40],
            "trace_hints": collect_trace_hints(dts),
            "cfg_audit": cfg,
        }
    )
    summary["classification"] = classify(cpus, ctis, dbgbase_hints, cfg)
    write_text(run_dir / "summary.json", json.dumps(summary, indent=2, sort_keys=True) + "\n")
    return run_dir, summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--dtb", type=Path, default=DEFAULT_DTB)
    parser.add_argument("--dtc", type=Path)
    parser.add_argument("--cfg", type=Path, default=DEFAULT_CFG)
    parser.add_argument("--require-pass", action="store_true")
    args = parser.parse_args(argv)

    root = repo_root()
    run_dir, summary = build_report(root, args)
    result = summary["classification"]["result"]
    print(
        "S22+ SM8450 OpenOCD target cfg audit: "
        f"{result}; cpus={summary.get('cpu_count', 0)} "
        f"cpu_ctis={summary.get('cpu_cti_count', 0)} "
        f"dbgbase_hints={summary.get('dbgbase_hint_count', 0)} "
        f"cfg={int((summary.get('cfg_audit') or {}).get('checks_passed', False))}; "
        f"log={display_path(run_dir / 'summary.json')}"
    )
    if args.require_pass and result not in ("sm8450_cfg_draft_ready_romtable_dbgbase", "sm8450_cfg_source_has_dbgbase_hints"):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
