#!/usr/bin/env python3
"""WSTA91 read-only netfilter/iptables/nftables inventory.

This is the live read-only unit requested by WSTA89/WSTA90 before selecting a
packet-filter default-drop backend.  It observes kernel config, procfs
netfilter surfaces, and userspace tool presence.  It does not run iptables/nft,
does not change rules, and does not require a boot artifact.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[5]
REVAL_DIR = REPO_ROOT / "workspace/public/src/scripts/revalidation"
for _path in (SCRIPT_DIR, REVAL_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import a90ctl  # noqa: E402
import run_wsta90_service_hardening_manifest as wsta90  # noqa: E402


PRIVATE_ROOT = wsta90.PRIVATE_ROOT
DEFAULT_RUN_BASE = wsta90.DEFAULT_RUN_BASE
PASS_DECISION = "wsta91-netfilter-inventory-readonly-live-pass"


@dataclass(frozen=True)
class Observation:
    name: str
    command: str
    why: str


OBSERVATIONS = (
    Observation(
        "kernel_config_netfilter",
        "(/bin/busybox zcat /proc/config.gz 2>/dev/null || zcat /proc/config.gz 2>/dev/null || true) "
        "| /bin/busybox grep -E 'NETFILTER|NF_TABLES|NFT|IP_TABLES|IP6_NF|IP_NF|X_TABLES|XT_|CONNTRACK|BRIDGE_NF' || true",
        "CONFIG evidence for nftables, legacy iptables, x_tables, and conntrack",
    ),
    Observation(
        "proc_netfilter_surfaces",
        "for p in /proc/net/ip_tables_names /proc/net/ip6_tables_names /proc/net/arp_tables_names "
        "/proc/net/nf_conntrack /proc/net/stat/nf_conntrack /proc/net/netfilter/nf_log "
        "/proc/sys/net/netfilter; do "
        "echo __A90_WSTA91_PATH__=$p; "
        "if [ -d \"$p\" ]; then echo __A90_WSTA91_DIR__; ls -la \"$p\"; "
        "elif [ -r \"$p\" ]; then echo __A90_WSTA91_READABLE__; cat \"$p\"; "
        "else echo __A90_WSTA91_MISSING__; fi; "
        "done",
        "Procfs/runtime surfaces indicating loaded tables and netfilter sysctls",
    ),
    Observation(
        "userspace_filter_tools",
        "echo __A90_WSTA91_BUSYBOX__; /bin/busybox --list | "
        "/bin/busybox grep -E '^(iptables|ip6tables|nft|modprobe|lsmod)$' || true; "
        "echo __A90_WSTA91_PATHS__; "
        "for p in /sbin/iptables /usr/sbin/iptables /bin/iptables /usr/bin/iptables "
        "/sbin/ip6tables /usr/sbin/ip6tables /usr/sbin/nft /usr/bin/nft; do "
        "[ -e \"$p\" ] && ls -l \"$p\"; done",
        "Userspace command availability without executing packet-filter tools",
    ),
)


def rel(path: Path) -> str:
    return wsta90.rel(path)


def utc_stamp() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else REPO_ROOT / path


def is_under(path: Path, root: Path) -> bool:
    return wsta90.is_under(path, root)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def safety_flags(live: bool) -> dict[str, Any]:
    return {
        "device_action": live,
        "boot_flash": False,
        "native_reboot": False,
        "wifi_connect": False,
        "dhcp": False,
        "public_tunnel": False,
        "public_smoke": False,
        "userdata_touch": False,
        "switch_root": False,
        "packet_filter_mutation": False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def shell_command(command: str) -> list[str]:
    return ["run", "/bin/busybox", "sh", "-c", command]


def run_cmd(args: argparse.Namespace, command: list[str], *, retry_unsafe: bool = False) -> dict[str, Any]:
    result = a90ctl.run_cmdv1_command(
        args.bridge_host,
        args.bridge_port,
        args.timeout,
        command,
        retry_unsafe=retry_unsafe,
        require_prompt_after_end=True,
    )
    return {
        "command": command,
        "rc": result.rc,
        "status": result.status,
        "begin": result.begin,
        "end": result.end,
        "text": result.text,
    }


def clean_text(text: str) -> str:
    lines: list[str] = []
    for raw in text.splitlines():
        line = raw.strip("\r")
        if not line or line.startswith("A90P1 BEGIN ") or line.startswith("A90P1 END "):
            continue
        if line.startswith("a90:/#") or line.startswith("cmdv1 ") or line.startswith("cmdv1x "):
            continue
        lines.append(line)
    return "\n".join(lines)


def parse_config(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in clean_text(text).splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("# ") and " is not set" in line:
            key = line[2:].split(" is not set", 1)[0].strip()
            out[key] = "n"
        elif line.startswith("CONFIG_") and "=" in line:
            key, value = line.split("=", 1)
            out[key.strip()] = value.strip()
    return out


def parse_tool_presence(text: str) -> dict[str, bool]:
    cleaned = clean_text(text)
    tools = {name: False for name in ("iptables", "ip6tables", "nft", "modprobe", "lsmod")}
    for name in tools:
        if re.search(rf"(^|\s|/){re.escape(name)}(\s|$)", cleaned, re.MULTILINE):
            tools[name] = True
    return tools


def surface_present(text: str, marker: str) -> bool:
    cleaned = clean_text(text)
    block = ""
    capture = False
    for line in cleaned.splitlines():
        if line.startswith("__A90_WSTA91_PATH__="):
            capture = line == f"__A90_WSTA91_PATH__={marker}"
            continue
        if capture:
            if line.startswith("__A90_WSTA91_PATH__="):
                break
            block += line + "\n"
    return (
        ("__A90_WSTA91_DIR__" in block or "__A90_WSTA91_READABLE__" in block)
        and "__A90_WSTA91_MISSING__" not in block
    )


def classify_inventory(raw: dict[str, Any]) -> dict[str, Any]:
    records = {item["name"]: item for item in raw.get("observations", []) if isinstance(item, dict)}
    config = parse_config(str(records.get("kernel_config_netfilter", {}).get("text", "")))
    tools = parse_tool_presence(str(records.get("userspace_filter_tools", {}).get("text", "")))
    proc_text = str(records.get("proc_netfilter_surfaces", {}).get("text", ""))
    nft_ready = config.get("CONFIG_NF_TABLES") == "y" and tools.get("nft")
    legacy_ready = (
        config.get("CONFIG_NETFILTER") == "y"
        and config.get("CONFIG_IP_NF_IPTABLES") == "y"
        and tools.get("iptables")
    )
    proc_surfaces = {
        "ip_tables_names": surface_present(proc_text, "/proc/net/ip_tables_names"),
        "ip6_tables_names": surface_present(proc_text, "/proc/net/ip6_tables_names"),
        "nf_conntrack": surface_present(proc_text, "/proc/net/nf_conntrack"),
        "netfilter_sysctl": surface_present(proc_text, "/proc/sys/net/netfilter"),
    }
    if nft_ready:
        backend = "nftables"
    elif legacy_ready:
        backend = "legacy-iptables"
    else:
        backend = "not-proven"
    return {
        "decision": PASS_DECISION,
        "read_only": True,
        "packet_filter_mutation": False,
        "config": {
            key: config.get(key, "missing")
            for key in (
                "CONFIG_NETFILTER",
                "CONFIG_NF_TABLES",
                "CONFIG_NF_CONNTRACK",
                "CONFIG_IP_NF_IPTABLES",
                "CONFIG_IP6_NF_IPTABLES",
                "CONFIG_NETFILTER_XTABLES",
            )
        },
        "tools": tools,
        "proc_surfaces": proc_surfaces,
        "backend_recommendation": backend,
        "default_drop_ready_for_source": backend in {"nftables", "legacy-iptables"},
        "next_action": (
            "prototype default-drop rules with selected backend"
            if backend != "not-proven"
            else "stage or choose a packet-filter backend before always-on public posture"
        ),
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def public_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": result.get("decision"),
        "run_dir": result.get("run_dir"),
        "checks": result.get("checks", {}),
        "inventory": result.get("inventory", {}),
        "safety": result.get("safety", {}),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = utc_stamp()
    run_id = args.run_id or f"wsta91-netfilter-inventory-{ts}"
    run_dir = resolve_path(args.run_dir or (DEFAULT_RUN_BASE / run_id))
    result: dict[str, Any] = {
        "scope": "WSTA91 read-only netfilter/iptables/nftables inventory",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "decision": "wsta91-blocked",
        "safety": safety_flags(args.live_readonly_netfilter_inventory),
    }
    if not is_under(run_dir, PRIVATE_ROOT):
        result["decision"] = "wsta91-blocked-nonprivate-run-dir"
        return result
    run_dir.mkdir(parents=True, exist_ok=True)
    out_json = run_dir / "wsta91_netfilter_inventory.json"
    raw_json = run_dir / "wsta91_netfilter_inventory_private.json"

    if not args.live_readonly_netfilter_inventory:
        result["decision"] = "wsta91-blocked-live-readonly-netfilter-inventory-required"
        result["checks"] = {"device_action": False, "packet_filter_mutation": False}
        write_json(out_json, result)
        return result

    health_before = run_cmd(args, ["selftest"], retry_unsafe=True)
    result["health_before"] = {"rc": health_before.get("rc"), "status": health_before.get("status")}
    if "fail=0" not in str(health_before.get("text", "")):
        result["decision"] = "wsta91-blocked-pre-selftest"
        write_json(out_json, result)
        return result

    observations: list[dict[str, Any]] = []
    for obs in OBSERVATIONS:
        record = run_cmd(args, shell_command(obs.command), retry_unsafe=True)
        record["name"] = obs.name
        record["why"] = obs.why
        record["read_only"] = True
        observations.append(record)
        write_json(raw_json, {"observations": observations})

    raw = {"observations": observations}
    inventory = classify_inventory(raw)
    health_after = run_cmd(args, ["selftest"], retry_unsafe=True)
    result["health_after"] = {"rc": health_after.get("rc"), "status": health_after.get("status")}
    result["inventory"] = inventory
    result["checks"] = {
        "pre_selftest_fail_zero": "fail=0" in str(health_before.get("text", "")),
        "post_selftest_fail_zero": "fail=0" in str(health_after.get("text", "")),
        "observations_read_only": True,
        "packet_filter_mutation": False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }
    result["decision"] = PASS_DECISION if result["checks"]["post_selftest_fail_zero"] else "wsta91-blocked-post-selftest"
    result["ended_utc"] = utc_stamp()
    write_json(raw_json, raw)
    write_json(out_json, public_summary(result))
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--live-readonly-netfilter-inventory", action="store_true")
    parser.add_argument("--bridge-host", default="127.0.0.1")
    parser.add_argument("--bridge-port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--print-full-json", action="store_true")
    return parser


def main_with_args(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    try:
        result = run(args)
    except Exception as exc:  # noqa: BLE001
        payload = {"decision": "wsta91-runner-error", "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1
    payload = result if args.print_full_json else public_summary(result)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if result.get("decision") == PASS_DECISION else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
