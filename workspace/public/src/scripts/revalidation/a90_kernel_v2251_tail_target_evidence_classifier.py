#!/usr/bin/env python3
"""V2251 post-FWREADY tail target evidence classifier.

Host-only postprocessor for a V2250-style helper result. It compares the
helper's deterministic `/proc/*/stack` and firmware_class feeder evidence with
the generic CPU-clock PC/LR scorer result, so a zero generic-sampler target hit
is not misread as proof that the firmware_class/qcacld-HDD path never executed.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from collections import Counter
from pathlib import Path
from typing import Any

from a90_kernel_v2241_user_uprobe_offset_base_map import PRIVATE_RUNS, rel

DEFAULT_RUN_DIR = PRIVATE_RUNS / "v2250-tail-perf-sampler-full-print-live-20260612-124426"
DEFAULT_SCORER_SUMMARY = DEFAULT_RUN_DIR / "v2250-tail-pc-lr-score-reanalyzed/summary.json"

TARGET_SYMBOLS = [
    "_request_firmware",
    "request_firmware",
    "qdf_file_read",
    "qdf_ini_parse",
    "cfg_parse",
    "hdd_context_create",
    "wlan_hdd_pld_probe",
]

STACK_PREFIX_RE = re.compile(
    r"^icnss_register_probe_stack_sampler\.after_boot_wlan_trigger\.sample_(?P<sample>\d+)\."
    r"(?P<key>[^=]+)=(?P<value>.*)$"
)
FEEDER_RE = re.compile(
    r"^qcacld_firmware_class_fallback_feeder\.after_boot_wlan_trigger\."
    r"(?P<key>[^=]+)=(?P<value>.*)$"
)
BOOT_WLAN_RE = re.compile(r"^post_fw_ready_boot_wlan_trigger\.(?P<key>[^=]+)=(?P<value>.*)$")


def now_label() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


def read_text_lossy(path: Path) -> str:
    return path.read_bytes().replace(b"\0", b"\n").decode("utf-8", errors="replace")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def parse_int(value: Any) -> int | None:
    if value is None:
        return None
    text = str(value)
    if text == "":
        return None
    try:
        return int(text, 0)
    except ValueError:
        return None


def extract_stack_symbol(line: str) -> str | None:
    marker = "] "
    if marker not in line:
        return None
    tail = line.split(marker, 1)[1]
    return tail.split("+", 1)[0].strip() or None


def parse_helper(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    boot_wlan: dict[str, str] = {}
    feeder: dict[str, str] = {}
    samples: dict[str, dict[str, Any]] = {}
    token_counts: Counter[str] = Counter()

    for line in read_text_lossy(path).splitlines():
        for symbol in TARGET_SYMBOLS:
            if symbol in line:
                token_counts[symbol] += 1
        boot_match = BOOT_WLAN_RE.match(line)
        if boot_match:
            boot_wlan[boot_match.group("key")] = boot_match.group("value")
            continue
        feeder_match = FEEDER_RE.match(line)
        if feeder_match:
            feeder[feeder_match.group("key")] = feeder_match.group("value")
            continue
        stack_match = STACK_PREFIX_RE.match(line)
        if not stack_match:
            continue
        sample_id = stack_match.group("sample")
        key = stack_match.group("key")
        value = stack_match.group("value")
        sample = samples.setdefault(sample_id, {"sample": sample_id, "stack_lines": [], "stack_symbols": []})
        if key.startswith("stack_"):
            sample["stack_lines"].append(value)
            symbol = extract_stack_symbol(value)
            if symbol:
                sample["stack_symbols"].append(symbol)
        else:
            sample[key] = value

    stack_rows = []
    for sample in sorted(samples.values(), key=lambda row: int(str(row["sample"]))):
        symbols = list(dict.fromkeys(sample.get("stack_symbols") or []))
        present = [symbol for symbol in TARGET_SYMBOLS if symbol in symbols]
        stack_rows.append({
            "sample": sample["sample"],
            "comm": sample.get("comm"),
            "wchan": sample.get("wchan"),
            "target": sample.get("target") == "1",
            "stack_depth": len(sample.get("stack_lines") or []),
            "target_symbols_present": present,
            "target_symbol_count": len(present),
            "all_targets_present": len(present) == len(TARGET_SYMBOLS),
            "public_stack_preview": [
                line for line in (sample.get("stack_lines") or [])
                if any(symbol in line for symbol in TARGET_SYMBOLS)
            ][:12],
        })

    return {
        "boot_wlan": boot_wlan,
        "feeder": feeder,
        "stack_samples": stack_rows,
        "target_token_counts": dict(sorted(token_counts.items())),
    }


def summarize_feeder(feeder: dict[str, str]) -> dict[str, Any]:
    request0_prefix = "request_0."
    request0 = {
        key[len(request0_prefix):]: value
        for key, value in feeder.items()
        if key.startswith(request0_prefix)
    }
    return {
        "begin": feeder.get("begin") == "1",
        "request_count": parse_int(feeder.get("request_count")),
        "seen_count": parse_int(feeder.get("seen_count")),
        "fed_count": parse_int(feeder.get("fed_count")),
        "timed_out": feeder.get("timed_out") == "1",
        "request0_label": request0.get("label"),
        "request0_firmware": request0.get("firmware"),
        "request0_seen": request0.get("seen") == "1",
        "request0_fed": request0.get("fed") == "1",
        "request0_source_bytes": parse_int(request0.get("source_bytes")),
        "request0_data_rc": parse_int(request0.get("data_rc")),
        "request0_loading_done_rc": parse_int(request0.get("loading_done_rc")),
    }


def summarize_scorer(summary: dict[str, Any]) -> dict[str, Any]:
    scoring = summary.get("scoring") or {}
    exact_slide = summary.get("exact_slide") or {}
    return {
        "present": bool(summary),
        "decision": summary.get("decision"),
        "pass": summary.get("pass"),
        "sample_count": scoring.get("sample_count"),
        "hit_count": scoring.get("hit_count"),
        "target_count": summary.get("target_count"),
        "accepted_exact_codeword_slide": exact_slide.get("accepted_exact_codeword_slide"),
        "accepted_symbolization_slide": exact_slide.get("accepted_symbolization_slide"),
        "acceptance_reason": exact_slide.get("acceptance_reason"),
        "slide_hex": exact_slide.get("slide_hex"),
    }


def build_summary(args: argparse.Namespace, out_dir: Path) -> dict[str, Any]:
    helper_path = args.run_dir / "helper.result.cmdv1.txt"
    parsed = parse_helper(helper_path)
    scorer = summarize_scorer(read_json(args.scorer_summary))
    feeder = summarize_feeder(parsed["feeder"])
    stack_samples = parsed["stack_samples"]
    target_samples = [row for row in stack_samples if row["target"]]
    full_target_samples = [row for row in stack_samples if row["all_targets_present"]]
    boot_wlan = parsed["boot_wlan"]

    boot_wlan_executed = boot_wlan.get("executed") == "1" and boot_wlan.get("write_rc") == "0"
    feeder_confirmed = bool(
        feeder["begin"]
        and (feeder["fed_count"] or 0) >= 1
        and feeder["request0_firmware"] == "wlan/qca_cld/WCNSS_qcom_cfg.ini"
        and feeder["request0_fed"]
        and (feeder["request0_source_bytes"] or 0) > 0
        and feeder["request0_data_rc"] == 0
        and feeder["request0_loading_done_rc"] == 0
    )
    stack_confirmed = bool(full_target_samples)
    generic_zero = scorer.get("hit_count") == 0 and (scorer.get("sample_count") or 0) > 0

    if boot_wlan_executed and feeder_confirmed and stack_confirmed and generic_zero:
        decision = "v2251-tail-target-evidence-generic-sampler-miss-confirmed"
    elif boot_wlan_executed and feeder_confirmed and stack_confirmed:
        decision = "v2251-tail-target-evidence-confirmed"
    else:
        decision = "v2251-tail-target-evidence-review-needed"

    evidence_path = out_dir / "tail_target_evidence.json"
    evidence_path.write_text(json.dumps({
        "warning": "Public-safe derived metadata. Raw helper output remains under workspace/private.",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "target_symbols": TARGET_SYMBOLS,
        "boot_wlan": {
            "executed": boot_wlan.get("executed"),
            "write_rc": boot_wlan.get("write_rc"),
            "reason": boot_wlan.get("reason"),
        },
        "feeder": feeder,
        "scorer": scorer,
        "stack_samples": stack_samples,
        "target_token_counts": parsed["target_token_counts"],
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    return {
        "label": args.label,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "decision": decision,
        "pass": decision.endswith("confirmed"),
        "out_dir": rel(out_dir),
        "safety": {
            "host_only": True,
            "device_io": False,
            "bpf_attach": False,
            "tracefs_control_write": False,
            "probe_write_user_executed": False,
            "wifi_scan_connect": False,
            "network_route_change": False,
            "flash_reboot": False,
            "partition_write": False,
            "private_raw_log_copied_to_public": False,
        },
        "inputs": {
            "run_dir": rel(args.run_dir),
            "helper_result": rel(helper_path),
            "scorer_summary": rel(args.scorer_summary),
        },
        "target_symbols": TARGET_SYMBOLS,
        "boot_wlan_executed": boot_wlan_executed,
        "feeder_confirmed": feeder_confirmed,
        "stack_confirmed": stack_confirmed,
        "generic_sampler_zero_hits": generic_zero,
        "full_target_stack_sample_count": len(full_target_samples),
        "target_stack_sample_count": len(target_samples),
        "stack_sample_count": len(stack_samples),
        "feeder": feeder,
        "scorer": scorer,
        "full_target_stack_samples": full_target_samples,
        "private_evidence": {
            "path": rel(evidence_path),
            "contains_raw_runtime_addresses": False,
            "contains_private_helper_excerpt": False,
        },
        "interpretation": {
            "result": (
                "The post-FWREADY firmware_class/qcacld-HDD target stack executed in the V2250 boot; "
                "the generic CPU-clock PC/LR zero-hit result is therefore a sampler miss, not function absence."
                if stack_confirmed and generic_zero else
                "Review target evidence before drawing a tail-execution conclusion."
            ),
            "next_unit": (
                "Stop generic CPU-clock retries for this tail. If finer timing is needed, instrument the already-confirmed helper-owned "
                "boundary or sample /proc stack at more deterministic points around the firmware_class feeder."
            ),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", default="v2251-tail-target-evidence-classifier")
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument("--scorer-summary", type=Path, default=DEFAULT_SCORER_SUMMARY)
    parser.add_argument("--out-dir", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = args.out_dir or PRIVATE_RUNS / f"{args.label}-{now_label()}"
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = build_summary(args, out_dir)
    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "decision": summary["decision"],
        "pass": summary["pass"],
        "out_dir": summary["out_dir"],
        "summary": rel(summary_path),
        "full_target_stack_sample_count": summary["full_target_stack_sample_count"],
        "generic_sampler_zero_hits": summary["generic_sampler_zero_hits"],
    }, indent=2, sort_keys=True))
    return 0 if summary["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
