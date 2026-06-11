#!/usr/bin/env python3
"""Run V2218 WLAN-adjacent tracepoint catalog and idle attach proof.

This is a read-only observer:
- reads tracefs available_events and selected format/id files;
- optionally attaches an already-installed a90_bpf_trace_extract helper for a
  bounded idle window;
- does not write tracefs controls, trigger Wi-Fi, scan/connect, change network
  routes, reboot, flash, or write partitions.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[5]
SCRIPT_DIR = REPO_ROOT / "workspace/public/src/scripts/revalidation"
PRIVATE_RUNS = REPO_ROOT / "workspace/private/runs/kernel"
REMOTE_TOYBOX = "/cache/bin/busybox"
REMOTE_EXTRACT = "/cache/bin/a90_bpf_trace_extract"
EXACT_SLIDE = 0x84EF4
DEFAULT_SYSTEM_MAP = REPO_ROOT / "workspace/private/runs/kernel/v2197-stock-kallsyms/System.map"

CONTROL_LINE_RE = re.compile(
    r"^(a90:/#|A90P1 BEGIN|A90P1 END|\[done\]|\[exit |run: pid=|cmdv1x )"
)
LINKER_WARNING_RE = re.compile(r"^(WARNING: )?linker: Warning: failed to find generated linker configuration")
FIELD_RE = re.compile(
    r"field:(?P<type>[^;]+?)\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*(?:\[[^\]]+\])?);"
    r"\s*offset:(?P<offset>\d+);\s*size:(?P<size>\d+);\s*signed:(?P<signed>[01]);"
)
COUNT_RE = re.compile(r"^count=(?P<count>\d+)$", re.MULTILINE)
LAST_RE = re.compile(r"^last=(?P<last>\d+)$", re.MULTILINE)

IMPORTANT_EVENTS = [
    "a90cnss:wlfw_start",
    "a90cnss:wlfw_service_request",
    "a90cnss:wlfw_ind_register_qmi",
    "a90cnss:wlfw_cap_qmi",
    "a90cnss:wlfw_bdf_entry",
    "a90cnss:wlfw_bdf_send_ret",
    "a90cnss:wlfw_qmi_ind_cb_entry",
    "a90cnss:wlfw_handle_ind_type",
    "a90cnss:dms_service_request",
    "a90cnss:dms_get_wlan_address_entry",
    "a90cnss:pm_init_pm_client_register_call",
    "a90cnss:pm_init_pm_client_connect_call",
    "a90pmsrv:pm_service_post_ack_qmi_restart_ind_call",
    "a90libqmi:libqmi_client_init_instance_entry",
    "a90libqmi:libqmi_get_service_list_lookup_call",
    "msm_pil_event:pil_notif",
    "msm_pil_event:pil_event",
    "dfc:dfc_qmi_tc",
    "cfg80211:rdev_scan",
    "cfg80211:rdev_return_int",
]

UPROBE_ATTACH_EVENTS = [
    "a90cnss:wlfw_start",
    "a90cnss:wlfw_service_request",
    "a90cnss:wlfw_cap_qmi",
    "a90cnss:wlfw_bdf_entry",
]

STOCK_IDLE_ATTACH_FIELDS = [
    ("msm_pil_event:pil_notif", "code"),
    ("cfg80211:rdev_return_int", "ret"),
]


@dataclass
class StepResult:
    name: str
    command: list[str]
    returncode: int
    elapsed_sec: float
    stdout_path: str
    stderr_path: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


def now_label() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


def run_host(
    out_dir: Path,
    steps: list[StepResult],
    name: str,
    command: list[str],
    *,
    timeout: float = 60.0,
    allow_error: bool = False,
) -> str:
    started = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )
    elapsed = time.monotonic() - started
    stdout_path = out_dir / f"{name}.stdout.txt"
    stderr_path = out_dir / f"{name}.stderr.txt"
    stdout_path.write_text(completed.stdout)
    stderr_path.write_text(completed.stderr)
    result = StepResult(
        name=name,
        command=command,
        returncode=completed.returncode,
        elapsed_sec=round(elapsed, 3),
        stdout_path=str(stdout_path.relative_to(REPO_ROOT)),
        stderr_path=str(stderr_path.relative_to(REPO_ROOT)),
    )
    steps.append(result)
    if completed.returncode != 0 and not allow_error:
        raise RuntimeError(
            f"{name} failed rc={completed.returncode}\n"
            f"stdout={stdout_path}\nstderr={stderr_path}\n{completed.stdout}\n{completed.stderr}"
        )
    return completed.stdout


def a90ctl(
    args: argparse.Namespace,
    out_dir: Path,
    steps: list[StepResult],
    name: str,
    argv: list[str],
    *,
    timeout: float = 60.0,
    allow_error: bool = False,
) -> str:
    command = [
        sys.executable,
        str(SCRIPT_DIR / "a90ctl.py"),
        "--host",
        args.bridge_host,
        "--port",
        str(args.bridge_port),
        "--timeout",
        str(timeout),
    ]
    if allow_error:
        command.append("--allow-error")
    command.extend(argv)
    return run_host(out_dir, steps, name, command, timeout=timeout + 10, allow_error=allow_error)


def run_device_shell(
    args: argparse.Namespace,
    out_dir: Path,
    steps: list[StepResult],
    name: str,
    script: str,
    *,
    timeout: float = 60.0,
    allow_error: bool = False,
) -> str:
    return a90ctl(
        args,
        out_dir,
        steps,
        name,
        ["run", args.toybox, "sh", "-c", script],
        timeout=timeout,
        allow_error=allow_error,
    )


def clean_cmdv1_text(text: str) -> str:
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip("\r")
        if CONTROL_LINE_RE.match(line):
            continue
        if LINKER_WARNING_RE.match(line):
            continue
        if not line:
            continue
        lines.append(line)
    return "\n".join(lines) + ("\n" if lines else "")


def parse_events(text: str) -> list[str]:
    events = []
    for line in text.splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        group, event = line.split(":", 1)
        if group and event:
            events.append(f"{group}:{event}")
    return events


def category_for(event: str) -> str | None:
    group, name = event.split(":", 1)
    token = event.lower()
    if group in {"a90cnss"}:
        return "a90cnss_wlfw"
    if group in {"a90libqmi", "a90pmsrv"}:
        return "a90_qmi_pm"
    if "cfg80211" in token or "mac80211" in token or "wlan" in token or "cnss" in token or "icnss" in token:
        return "wifi_kernel"
    if group == "msm_pil_event" or "pil" in name or "subsys" in token:
        return "pil_subsys"
    if "qmi" in token or "qrtr" in token or group == "dfc":
        return "qmi_transport"
    if group in {"net", "skb", "napi", "sock", "udp", "tcp"}:
        return "net_stack"
    if group in {"sched", "workqueue", "irq", "timer"}:
        return "scheduler_context"
    if group in {"clk", "regulator", "rpmh", "power"} or any(word in token for word in ("clk", "regulator", "rpmh")):
        return "power_clock"
    return None


def parse_format(format_text: str) -> dict[str, Any]:
    fields = []
    for match in FIELD_RE.finditer(format_text):
        name = match.group("name")
        if "[" in name:
            name = name.split("[", 1)[0]
        fields.append(
            {
                "type": " ".join(match.group("type").split()),
                "name": name,
                "offset": int(match.group("offset"), 10),
                "size": int(match.group("size"), 10),
                "signed": match.group("signed") == "1",
            }
        )
    event_fields = [field for field in fields if not field["name"].startswith("common_")]
    return {
        "fields": fields,
        "event_fields": event_fields,
        "has_probe_ip": any(field["name"] == "__probe_ip" for field in fields),
        "field_names": [field["name"] for field in fields],
    }


def load_system_map(path: Path) -> list[dict[str, Any]]:
    symbols = []
    if not path.exists():
        return symbols
    for line in path.read_text(errors="replace").splitlines():
        parts = line.split(None, 2)
        if len(parts) < 3:
            continue
        try:
            address = int(parts[0], 16)
        except ValueError:
            continue
        sym_type = parts[1]
        name = parts[2]
        if sym_type.lower() == "a":
            continue
        symbols.append({"address": address, "type": sym_type, "name": name})
    symbols.sort(key=lambda item: item["address"])
    return symbols


def symbolize(value: int, symbols: list[dict[str, Any]], slide: int) -> dict[str, Any] | None:
    static = value - slide
    lo = 0
    hi = len(symbols)
    while lo < hi:
        mid = (lo + hi) // 2
        if symbols[mid]["address"] <= static:
            lo = mid + 1
        else:
            hi = mid
    idx = lo - 1
    if idx < 0:
        return None
    symbol = symbols[idx]
    return {
        "runtime": f"0x{value:016x}",
        "static": f"0x{static:016x}",
        "symbol": symbol["name"],
        "offset": static - int(symbol["address"]),
    }


def parse_extract_output(text: str, symbols: list[dict[str, Any]], slide: int) -> dict[str, Any]:
    cleaned = clean_cmdv1_text(text)
    count_match = COUNT_RE.search(cleaned)
    last_match = LAST_RE.search(cleaned)
    count = int(count_match.group("count"), 10) if count_match else 0
    last = int(last_match.group("last"), 10) if last_match else 0
    return {
        "count": count,
        "last": f"0x{last:016x}" if last else "0x0000000000000000",
        "result": next((line.split("=", 1)[1] for line in cleaned.splitlines() if line.startswith("result=")), ""),
        "attach_attempted": "attach_attempted=1" in cleaned,
        "symbolized_last": symbolize(last, symbols, slide) if last else None,
        "cleaned_stdout": cleaned,
    }


def sample_event(
    args: argparse.Namespace,
    out_dir: Path,
    steps: list[StepResult],
    event: str,
    field: str,
    duration: int,
    *,
    allow_error: bool = False,
) -> dict[str, Any]:
    stdout = a90ctl(
        args,
        out_dir,
        steps,
        f"sample-{event.replace(':', '-')}-{field}",
        [
            "run",
            args.extract,
            "--event",
            event,
            "--field",
            field,
            "--mode",
            "sample",
            "--duration-sec",
            str(duration),
            "--allow-attach",
        ],
        timeout=duration + 60,
        allow_error=allow_error,
    )
    return {"event": event, "field": field, "stdout": stdout}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", default="v2218-wlan-tracepoint-catalog")
    parser.add_argument("--bridge-host", default="127.0.0.1")
    parser.add_argument("--bridge-port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=45.0)
    parser.add_argument("--toybox", default=REMOTE_TOYBOX)
    parser.add_argument("--extract", default=REMOTE_EXTRACT)
    parser.add_argument("--system-map", type=Path, default=DEFAULT_SYSTEM_MAP)
    parser.add_argument("--exact-slide", default=f"0x{EXACT_SLIDE:x}")
    parser.add_argument("--idle-duration", type=int, default=2)
    parser.add_argument("--skip-idle-attach", action="store_true")
    args = parser.parse_args()

    out_dir = PRIVATE_RUNS / f"{args.label}-{now_label()}"
    out_dir.mkdir(parents=True, exist_ok=True)
    steps: list[StepResult] = []
    summary: dict[str, Any] = {
        "label": args.label,
        "out_dir": str(out_dir.relative_to(REPO_ROOT)),
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "safety": {
            "tracefs_control_write": False,
            "bpf_tracepoint_attach": not args.skip_idle_attach,
            "probe_write_user_executed": False,
            "wifi_scan_connect": False,
            "network_route_change": False,
            "flash_reboot": False,
            "partition_write": False,
        },
        "exact_slide": args.exact_slide,
    }

    try:
        run_host(
            out_dir,
            steps,
            "bridge-status",
            [
                sys.executable,
                str(SCRIPT_DIR / "a90_bridge.py"),
                "status",
                "--json",
            ],
            timeout=30,
            allow_error=True,
        )
        a90ctl(args, out_dir, steps, "pre-status", ["status"], timeout=args.timeout, allow_error=True)

        tracefs_probe = run_device_shell(
            args,
            out_dir,
            steps,
            "tracefs-probe",
            (
                "for p in /sys/kernel/tracing /sys/kernel/debug/tracing; do "
                "echo TRACEFS=$p; test -r $p/available_events && echo READABLE=1 && wc -l $p/available_events; "
                "done"
            ),
            timeout=args.timeout,
        )
        summary["tracefs_probe_clean"] = clean_cmdv1_text(tracefs_probe)

        available_raw = run_device_shell(
            args,
            out_dir,
            steps,
            "available-events",
            "cat /sys/kernel/tracing/available_events",
            timeout=args.timeout,
        )
        available_clean = clean_cmdv1_text(available_raw)
        (out_dir / "available_events.txt").write_text(available_clean)
        events = parse_events(available_clean)
        categories: dict[str, list[str]] = {}
        for event in events:
            category = category_for(event)
            if category:
                categories.setdefault(category, []).append(event)

        selected_events = []
        for event in IMPORTANT_EVENTS:
            if event in events and event not in selected_events:
                selected_events.append(event)
        for category in ("a90cnss_wlfw", "a90_qmi_pm", "pil_subsys", "qmi_transport", "wifi_kernel"):
            for event in categories.get(category, []):
                if event not in selected_events and len(selected_events) < 80:
                    selected_events.append(event)

        formats: dict[str, Any] = {}
        for event in selected_events:
            group, name = event.split(":", 1)
            stdout = run_device_shell(
                args,
                out_dir,
                steps,
                f"format-{event.replace(':', '-')}",
                f"cat /sys/kernel/tracing/events/{group}/{name}/id; cat /sys/kernel/tracing/events/{group}/{name}/format",
                timeout=args.timeout,
                allow_error=True,
            )
            clean = clean_cmdv1_text(stdout)
            event_path = out_dir / "formats" / group
            event_path.mkdir(parents=True, exist_ok=True)
            (event_path / f"{name}.txt").write_text(clean)
            parsed = parse_format(clean)
            id_line = next((line.strip() for line in clean.splitlines() if line.strip().isdigit()), "")
            formats[event] = {
                "id": int(id_line, 10) if id_line else None,
                **parsed,
                "format_path": str((event_path / f"{name}.txt").relative_to(REPO_ROOT)),
            }

        symbols = load_system_map(args.system_map)
        uprobe_samples: list[dict[str, Any]] = []
        stock_idle_samples: list[dict[str, Any]] = []
        positive_control: dict[str, Any] | None = None
        if not args.skip_idle_attach:
            extract_check = run_device_shell(
                args,
                out_dir,
                steps,
                "extract-helper-check",
                f"test -x {args.extract} && {args.extract} --event a90cnss:wlfw_start --field __probe_ip --check-only",
                timeout=args.timeout,
            )
            summary["extract_helper_check_clean"] = clean_cmdv1_text(extract_check)
            control_raw = sample_event(args, out_dir, steps, "timer:timer_start", "function", 1, allow_error=True)
            positive_control = parse_extract_output(control_raw["stdout"], symbols, int(args.exact_slide, 0))
            for event, field in STOCK_IDLE_ATTACH_FIELDS:
                if event not in formats:
                    continue
                raw = sample_event(args, out_dir, steps, event, field, args.idle_duration, allow_error=True)
                parsed = parse_extract_output(raw["stdout"], symbols, int(args.exact_slide, 0))
                stock_idle_samples.append({"event": event, "field": field, **parsed})
            for event in UPROBE_ATTACH_EVENTS:
                if event not in formats or not formats[event]["has_probe_ip"]:
                    continue
                raw = sample_event(args, out_dir, steps, event, "__probe_ip", args.idle_duration, allow_error=True)
                parsed = parse_extract_output(raw["stdout"], symbols, int(args.exact_slide, 0))
                uprobe_samples.append({"event": event, "field": "__probe_ip", **parsed})

        selftest = a90ctl(args, out_dir, steps, "post-selftest", ["selftest"], timeout=90, allow_error=True)

        wlan_hits = [sample for sample in uprobe_samples if sample.get("count", 0) > 0]
        uprobe_attach_failures = [
            sample for sample in uprobe_samples
            if sample.get("result") == "attach-failed" or not sample.get("attach_attempted")
        ]
        stock_attach_ok = [
            sample for sample in stock_idle_samples
            if sample.get("result") == "extract-pass" and sample.get("attach_attempted")
        ]
        if wlan_hits:
            decision = "v2218-wlan-uprobe-exact-ip-captured"
        elif uprobe_attach_failures and stock_attach_ok:
            decision = "v2218-a90-uprobes-cataloged-bpf-attach-blocked-stock-tracepoints-ok"
        else:
            decision = "v2218-wlan-tracepoints-cataloged-idle-nohit"
        summary.update(
            {
                "decision": decision,
                "pass": bool(events) and (args.skip_idle_attach or bool(positive_control and positive_control["count"] > 0)),
                "available_events_total": len(events),
                "category_counts": {key: len(value) for key, value in sorted(categories.items())},
                "category_samples": {key: value[:20] for key, value in sorted(categories.items())},
                "selected_events": selected_events,
                "formats": formats,
                "positive_control": positive_control,
                "uprobe_samples": uprobe_samples,
                "uprobe_attach_failures": uprobe_attach_failures,
                "stock_idle_samples": stock_idle_samples,
                "wlan_idle_hits": wlan_hits,
                "tracepoint_exact_source": "__probe_ip field in a90 trace_uprobe records",
                "tracepoint_ctx_regs_feasible": False,
                "tracepoint_ctx_regs_reason": (
                    "BPF_PROG_TYPE_TRACEPOINT ctx exposes the trace record; this kernel only special-cases "
                    "pt_regs for helpers such as bpf_get_stackid/perf_event_output, not direct ctx->regs reads."
                ),
                "a90_custom_events_are_trace_uprobes": True,
                "a90_uprobe_attach_interpretation": (
                    "a90cnss/a90libqmi/a90pmsrv are trace_uprobe events created by a90_android_execns_probe; "
                    "they are readable through tracefs format/id, but this v2192 BPF perf-event attach path returns EINTR "
                    "on them while stock timer/msm_pil_event/cfg80211 tracepoints attach normally."
                ),
                "selftest_fail0": "fail=0" in selftest,
            }
        )
        summary["pass"] = bool(summary["pass"]) and summary["selftest_fail0"]
    except Exception as exc:  # noqa: BLE001 - preserve evidence and classify
        summary["decision"] = "v2218-wlan-tracepoint-catalog-failed"
        summary["pass"] = False
        summary["error"] = str(exc)
    finally:
        summary["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        summary["steps"] = [
            {
                "name": step.name,
                "command": step.command,
                "returncode": step.returncode,
                "ok": step.ok,
                "elapsed_sec": step.elapsed_sec,
                "stdout_path": step.stdout_path,
                "stderr_path": step.stderr_path,
            }
            for step in steps
        ]
        (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
        print(
            json.dumps(
                {
                    "decision": summary.get("decision"),
                    "pass": summary.get("pass"),
                    "out_dir": summary.get("out_dir"),
                    "available_events_total": summary.get("available_events_total"),
                    "category_counts": summary.get("category_counts"),
                    "positive_control_count": (summary.get("positive_control") or {}).get("count"),
                    "stock_idle_ok": len(
                        [
                            sample
                            for sample in summary.get("stock_idle_samples") or []
                            if sample.get("result") == "extract-pass" and sample.get("attach_attempted")
                        ]
                    ),
                    "uprobe_attach_failures": len(summary.get("uprobe_attach_failures") or []),
                    "wlan_idle_hits": len(summary.get("wlan_idle_hits") or []),
                    "selftest_fail0": summary.get("selftest_fail0"),
                    "error": summary.get("error"),
                },
                indent=2,
                sort_keys=True,
            )
        )
    return 0 if summary.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
