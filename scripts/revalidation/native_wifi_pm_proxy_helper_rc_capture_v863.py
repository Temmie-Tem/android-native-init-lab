#!/usr/bin/env python3
"""V863 read-only capture/classifier for /vendor/etc/init/pm_proxy_helper.rc.

The live path temporarily mounts the current sda29 vendor partition as ext4
`ro,noload` under /tmp, captures only the target init rc, then unmounts and
removes the temporary node/path. It does not start daemons, mdm_helper, ks,
Wi-Fi HAL, scan/connect, credentials, DHCP, external ping, raw eSoC ioctl,
GPIO/sysfs/debugfs/subsystem writes, module load, boot image writes, or
partition writes.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, repo_path, run_capture, strip_cmdv1_text
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v863-pm-proxy-helper-rc-capture")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 30.0
DEFAULT_TOYBOX = "/cache/bin/toybox"
TARGET_REL = "etc/init/pm_proxy_helper.rc"
SECRET_RE = re.compile(r"(made by|creator: made by) [^\r\n]+", re.IGNORECASE)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", "--bridge-host", dest="host", default=DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--toybox", default=DEFAULT_TOYBOX)
    parser.add_argument("--run-id", default="")
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def redact(text: str) -> str:
    text = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", text)
    return SECRET_RE.sub(r"\1 [redacted]", text)


def safe_name(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)).strip("-") or "capture"


def make_run_id(value: str) -> str:
    run_id = value or dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if not re.fullmatch(r"[A-Za-z0-9_.+-]{1,64}", run_id):
        raise RuntimeError(f"unsafe run id: {run_id!r}")
    return run_id


def run_device(
    args: argparse.Namespace,
    store: EvidenceStore,
    steps: list[dict[str, Any]],
    name: str,
    command: list[str],
    timeout: float | None = None,
    ok_statuses: set[str] | None = None,
) -> dict[str, Any]:
    capture = run_capture(args, name, command, timeout=timeout or args.timeout)
    payload = strip_cmdv1_text(capture.text) if capture.text else capture.error + "\n"
    payload = redact(payload)
    ok = capture.ok or (ok_statuses is not None and capture.status in ok_statuses)
    item = {
        "name": name,
        "command": " ".join(command[:5]) + (" ..." if len(command) > 5 else ""),
        "ok": ok,
        "rc": capture.rc,
        "status": capture.status,
        "duration_sec": round(capture.duration_sec, 3),
        "error": redact(capture.error),
        "file": f"native/{safe_name(name)}.txt",
        "payload": payload[:8192] + ("\n[truncated]\n" if len(payload) > 8192 else ""),
    }
    store.write_text(item["file"], payload.rstrip() + "\n")
    steps.append(item)
    return item


def parse_block_dev(text: str) -> tuple[str, str]:
    for line in text.splitlines():
        match = re.fullmatch(r"\s*(\d+):(\d+)\s*", line)
        if match:
            return match.group(1), match.group(2)
    raise RuntimeError(f"could not parse sda29 dev from {text!r}")


def parse_service_block(text: str) -> dict[str, Any]:
    service: dict[str, Any] = {
        "name": "",
        "path": "",
        "args": "",
        "options": [],
        "class": [],
        "user": "",
        "group": [],
        "disabled": False,
        "oneshot": False,
        "capabilities": [],
        "ioprio": "",
        "shutdown": [],
        "socket": [],
        "file": [],
    }
    current = False
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        service_match = re.match(r"^service\s+(\S+)\s+(\S+)(?:\s+(.*))?$", stripped)
        if service_match:
            current = service_match.group(1) == "vendor.per_proxy_helper"
            if current:
                service["name"], service["path"], args = service_match.groups()
                service["args"] = args or ""
            continue
        if not current:
            continue
        if not raw_line[:1].isspace() and re.match(r"^(service|on|import)\b", stripped):
            break
        service["options"].append(stripped)
        parts = stripped.split()
        if not parts:
            continue
        key = parts[0]
        if key == "class":
            service["class"].extend(parts[1:])
        elif key == "user" and len(parts) > 1:
            service["user"] = parts[1]
        elif key == "group":
            service["group"].extend(parts[1:])
        elif key == "disabled":
            service["disabled"] = True
        elif key == "oneshot":
            service["oneshot"] = True
        elif key == "capabilities":
            service["capabilities"].extend(parts[1:])
        elif key == "ioprio":
            service["ioprio"] = " ".join(parts[1:])
        elif key == "shutdown":
            service["shutdown"].extend(parts[1:])
        elif key == "socket":
            service["socket"].append(" ".join(parts[1:]))
        elif key == "file":
            service["file"].append(" ".join(parts[1:]))
    return service


def decide(service: dict[str, Any], cleanup_ok: bool) -> tuple[str, bool, str, str]:
    if not cleanup_ok:
        return (
            "v863-cleanup-review-required",
            False,
            "temporary vendor mount cleanup did not prove clean",
            "manually inspect /proc/mounts and /tmp before continuing",
        )
    if not service.get("name"):
        return (
            "v863-pm-proxy-helper-service-missing",
            True,
            "pm_proxy_helper.rc captured but vendor.per_proxy_helper service block was not found",
            "compare Android dmesg start name with rc content before modelling helper",
        )
    return (
        "v863-pm-proxy-helper-contract-captured",
        True,
        "pm_proxy_helper.rc read-only capture parsed vendor.per_proxy_helper",
        "classify helper support for this init contract before any service start",
    )


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    run_id = make_run_id(args.run_id)
    base = f"/tmp/a90-v863-{run_id}"
    vendor = f"{base}/vendor"
    node = f"{base}/sda29"
    target = f"{vendor}/{TARGET_REL}"
    steps: list[dict[str, Any]] = []
    mounted = False

    manifest: dict[str, Any] = {
        "generated_at": now_iso(),
        "command": args.command,
        "run_id": run_id,
        "base": base,
        "target": target,
        "host": collect_host_metadata(),
        "steps": steps,
        "device_commands_executed": args.command == "run",
        "hard_gates": {
            "daemon_start_executed": False,
            "mdm_helper_start_executed": False,
            "ks_start_executed": False,
            "wifi_hal_start_executed": False,
            "scan_connect_executed": False,
            "credential_use_executed": False,
            "dhcp_route_executed": False,
            "external_ping_executed": False,
            "raw_esoc_ioctl_executed": False,
            "gpio_write_executed": False,
            "sysfs_write_executed": False,
            "debugfs_write_executed": False,
            "subsystem_write_executed": False,
            "module_load_unload_executed": False,
            "boot_or_partition_write_executed": False,
        },
    }
    if args.command == "plan":
        manifest.update({
            "decision": "v863-pm-proxy-helper-rc-capture-plan-ready",
            "pass": True,
            "reason": "plan-only; no device command executed",
            "next_step": "run V863 read-only temporary vendor mount capture",
        })
        return manifest

    cleanup_ok = False
    service: dict[str, Any] = {}
    try:
        run_device(args, store, steps, "pre-selftest", ["selftest"], timeout=10.0)
        pre_mounts = run_device(args, store, steps, "pre-mounts", ["cat", "/proc/mounts"], timeout=10.0)
        dev = run_device(args, store, steps, "sda29-dev", ["cat", "/sys/class/block/sda29/dev"], timeout=10.0)
        major, minor = parse_block_dev(dev["payload"])
        manifest["sda29_dev"] = f"{major}:{minor}"
        run_device(args, store, steps, "mkdir-base", ["mkdir", base], timeout=10.0)
        run_device(args, store, steps, "mkdir-vendor", ["mkdir", vendor], timeout=10.0)
        run_device(args, store, steps, "mknodb-sda29", ["mknodb", node, major, minor], timeout=10.0)
        mount_step = run_device(
            args,
            store,
            steps,
            "mount-vendor-ro-noload",
            ["run", args.toybox, "mount", "-t", "ext4", "-o", "ro,noload", node, vendor],
            timeout=20.0,
        )
        mounted = bool(mount_step["ok"])
        if not mounted:
            raise RuntimeError("temporary read-only vendor mount failed")
        ls_step = run_device(args, store, steps, "ls-target", ["run", args.toybox, "ls", "-l", target], timeout=10.0)
        cat_step = run_device(args, store, steps, "cat-target", ["run", args.toybox, "cat", target], timeout=10.0)
        run_device(args, store, steps, "mounts-during", ["run", args.toybox, "grep", base, "/proc/mounts"], timeout=10.0)
        service = parse_service_block(cat_step["payload"])
        manifest["target_ls_ok"] = bool(ls_step["ok"])
        manifest["target_cat_ok"] = bool(cat_step["ok"])
        manifest["captured_text_file"] = cat_step["file"]
        manifest["service_contract"] = service
        manifest["pre_mounts_had_base"] = base in pre_mounts["payload"]
    except Exception as exc:  # noqa: BLE001 - evidence bundle records failure path
        manifest["exception"] = str(exc)
    finally:
        if mounted:
            run_device(args, store, steps, "umount-vendor", ["umount", vendor], timeout=10.0)
        run_device(args, store, steps, "cleanup-base", ["run", args.toybox, "rm", "-rf", base], timeout=10.0)
        post_mounts = run_device(
            args,
            store,
            steps,
            "post-cleanup-mounts",
            ["run", args.toybox, "grep", base, "/proc/mounts"],
            timeout=10.0,
            ok_statuses={"error"},
        )
        run_device(args, store, steps, "post-selftest", ["selftest"], timeout=10.0)
        cleanup_ok = base not in post_mounts["payload"]

    if manifest.get("exception"):
        decision = "v863-manual-review-required"
        pass_ok = False
        reason = str(manifest["exception"])
        next_step = "inspect V863 evidence before continuing"
    else:
        decision, pass_ok, reason, next_step = decide(service, cleanup_ok)
    manifest.update({
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "cleanup_ok": cleanup_ok,
    })
    return manifest


def write_outputs(out_dir: Path, manifest: dict[str, Any]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    service = manifest.get("service_contract") or {}
    lines = [
        "# V863 pm_proxy_helper.rc Capture",
        "",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next: {manifest['next_step']}",
        f"- cleanup_ok: `{manifest.get('cleanup_ok', False)}`",
        "",
        "## Service Contract",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| name | `{service.get('name', '')}` |",
        f"| path | `{service.get('path', '')}` |",
        f"| args | `{service.get('args', '')}` |",
        f"| class | `{','.join(service.get('class', []))}` |",
        f"| user | `{service.get('user', '')}` |",
        f"| group | `{','.join(service.get('group', []))}` |",
        f"| disabled | `{service.get('disabled', '')}` |",
        f"| oneshot | `{service.get('oneshot', '')}` |",
        f"| capabilities | `{','.join(service.get('capabilities', []))}` |",
        f"| ioprio | `{service.get('ioprio', '')}` |",
        f"| shutdown | `{','.join(service.get('shutdown', []))}` |",
        "",
        "## Guardrails",
        "",
    ]
    for name, value in (manifest.get("hard_gates") or {}).items():
        lines.append(f"- `{name}`: `{value}`")
    lines.extend([
        "",
        "## Evidence",
        "",
        f"- manifest: `{out_dir / 'manifest.json'}`",
        f"- captured text: `{manifest.get('captured_text_file', '')}`",
    ])
    (out_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    out_dir = repo_path(args.out_dir)
    store = EvidenceStore(out_dir)
    manifest = build_manifest(args, store)
    write_outputs(out_dir, manifest)
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"summary: {out_dir / 'summary.md'}")
    print(f"manifest: {out_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
