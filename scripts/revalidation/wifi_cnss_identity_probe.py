#!/usr/bin/env python3
"""Run the v244 non-starting CNSS launcher identity/capability probe."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from a90_kernel_tools import REPO_ROOT, capture_to_manifest, collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v244-cnss-identity-probe")
DEFAULT_V243_MANIFEST = Path("tmp/wifi/v243-cnss-launcher-contract-plan/manifest.json")
DEFAULT_HELPER = Path("stage3/linux_init/helpers/a90_android_execns_probe")
DEFAULT_REMOTE_HELPER = "/cache/bin/a90_android_execns_probe"
DEFAULT_TOYBOX = "/cache/bin/toybox"
REQUIRED_V243_DECISION = "cnss-launcher-contract-ready"


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", nargs="?", choices=("probe", "dry-run"), default="probe")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--v243-manifest", type=Path, default=DEFAULT_V243_MANIFEST)
    parser.add_argument("--helper", type=Path, default=DEFAULT_HELPER)
    parser.add_argument("--remote-helper", default=DEFAULT_REMOTE_HELPER)
    parser.add_argument("--toybox", default=DEFAULT_TOYBOX)
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--skip-deploy", action="store_true")
    parser.add_argument("--transfer-port", type=int, default=18086)
    parser.add_argument("--transfer-timeout", type=float, default=120.0)
    parser.add_argument("--helper-timeout-sec", type=int, default=10)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    full_path = repo_path(path)
    if not full_path.exists():
        return {"missing": True, "path": str(full_path)}
    data = json.loads(full_path.read_text(encoding="utf-8"))
    data["_manifest_path"] = str(full_path)
    return data


def run_host(store: EvidenceStore, name: str, command: list[str], timeout: float = 60.0) -> dict[str, Any]:
    started = dt.datetime.now(dt.timezone.utc)
    try:
        result = subprocess.run(
            command,
            cwd=REPO_ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )
        text = result.stdout
        rc = result.returncode
        error = ""
    except Exception as exc:  # noqa: BLE001 - evidence collection preserves failures
        text = str(exc) + "\n"
        rc = None
        error = str(exc)
    store.write_text(f"host-{safe_name(name)}.txt", text)
    return {
        "name": name,
        "command": command,
        "rc": rc,
        "ok": rc == 0,
        "error": error,
        "started": started.isoformat(),
        "file": str(store.path(f"host-{safe_name(name)}.txt")),
        "text": text[:4096],
    }


def safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)
    return re.sub(r"-+", "-", cleaned).strip("-") or "capture"


def build_helper_command(args: argparse.Namespace) -> list[str]:
    return [
        sys.executable,
        "scripts/revalidation/tcpctl_host.py",
        "--device-binary",
        args.remote_helper,
        "--toybox",
        args.toybox,
        "install",
        "--local-binary",
        str(repo_path(args.helper)),
        "--transfer-port",
        str(args.transfer_port),
        "--transfer-timeout",
        str(args.transfer_timeout),
    ]


def identity_probe_command(args: argparse.Namespace) -> list[str]:
    return [
        "run",
        args.remote_helper,
        "--system-root",
        "/mnt/system/system",
        "--vendor-block",
        "/dev/block/sda29",
        "--vendor-fstype",
        "ext4",
        "--mode",
        "identity-probe",
        "--null-device-mode",
        "dev-null",
        "--vndk-apex-alias-mode",
        "v30-to-current",
        "--linkerconfig-mode",
        "copy-real",
        "--linkerconfig-source",
        "/cache/bin/a90_real_ld.config.txt",
        "--apex-libraries-source",
        "/cache/bin/a90_real_apex.libraries.config.txt",
        "--timeout-sec",
        str(args.helper_timeout_sec),
    ]


def parse_key_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in strip_cmdv1_text(text).splitlines():
        line = raw_line.strip()
        if not line or "=" not in line:
            if line.startswith("Uid:"):
                parts = line.split()
                if len(parts) >= 5:
                    values["postexec.uid.real"] = parts[1]
                    values["postexec.uid.effective"] = parts[2]
                    values["postexec.uid.saved"] = parts[3]
                    values["postexec.uid.fs"] = parts[4]
            elif line.startswith("Gid:"):
                parts = line.split()
                if len(parts) >= 5:
                    values["postexec.gid.real"] = parts[1]
                    values["postexec.gid.effective"] = parts[2]
                    values["postexec.gid.saved"] = parts[3]
                    values["postexec.gid.fs"] = parts[4]
            elif line.startswith("Groups:"):
                values["postexec.groups.values"] = ",".join(line.split()[1:])
            elif line.startswith("CapEff:"):
                values["postexec.cap.effective_hex"] = line.split()[1]
            elif line.startswith("CapPrm:"):
                values["postexec.cap.permitted_hex"] = line.split()[1]
            elif line.startswith("CapInh:"):
                values["postexec.cap.inheritable_hex"] = line.split()[1]
            elif line.startswith("CapAmb:"):
                values["postexec.cap.ambient_hex"] = line.split()[1]
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def cap_hex_has(value: str | None, bit: int) -> bool:
    if not value:
        return False
    try:
        return (int(value, 16) & (1 << bit)) != 0
    except ValueError:
        return False


def group_values_have(values: dict[str, str], group: str) -> bool:
    groups = {item.strip() for item in values.get("postexec.groups.values", "").split(",") if item.strip()}
    return group in groups


def classify_probe(
    v243: dict[str, Any],
    setup_ok: bool,
    setup_detail: str,
    helper_capture: dict[str, Any] | None,
    values: dict[str, str],
) -> tuple[bool, str, str, list[dict[str, Any]]]:
    checks = [
        {
            "name": "v243-contract-ready",
            "pass": bool(v243.get("pass")) and v243.get("decision") == REQUIRED_V243_DECISION,
            "detail": str(v243.get("decision", "missing")),
        },
        {
            "name": "build-deploy-ready",
            "pass": setup_ok,
            "detail": setup_detail,
        }
    ]
    if helper_capture is None:
        checks.append({"name": "identity-probe-ran", "pass": False, "detail": "not-run" if not setup_ok else "dry-run"})
    else:
        checks.extend(
            [
                {"name": "helper-cmdv1-ok", "pass": bool(helper_capture.get("ok")), "detail": helper_capture.get("error", "")},
                {"name": "preexec-status-pass", "pass": values.get("identity_probe.preexec_status") == "pass", "detail": values.get("identity_probe.preexec_status", "")},
                {"name": "child-exit-zero", "pass": values.get("child_exit_code") == "0", "detail": values.get("child_exit_code", "")},
                {"name": "uid-system", "pass": values.get("identity.after.uid.effective") == "1000", "detail": values.get("identity.after.uid.effective", "")},
                {"name": "gid-system", "pass": values.get("identity.after.gid.effective") == "1000", "detail": values.get("identity.after.gid.effective", "")},
                {"name": "group-inet", "pass": values.get("identity.after.groups.has_inet") == "1", "detail": values.get("identity.after.groups.values", "")},
                {"name": "group-net-admin", "pass": values.get("identity.after.groups.has_net_admin") == "1", "detail": values.get("identity.after.groups.values", "")},
                {"name": "group-wifi", "pass": values.get("identity.after.groups.has_wifi") == "1", "detail": values.get("identity.after.groups.values", "")},
                {"name": "cap-net-admin-effective", "pass": values.get("identity.after.cap.net_admin.effective") == "1", "detail": values.get("identity.after.cap.net_admin.effective", "")},
                {"name": "cap-net-admin-permitted", "pass": values.get("identity.after.cap.net_admin.permitted") == "1", "detail": values.get("identity.after.cap.net_admin.permitted", "")},
                {"name": "cap-net-admin-inheritable", "pass": values.get("identity.after.cap.net_admin.inheritable") == "1", "detail": values.get("identity.after.cap.net_admin.inheritable", "")},
                {"name": "ambient-net-admin-raised", "pass": values.get("identity_probe.ambient_raise.ok") == "1", "detail": values.get("identity_probe.ambient_raise.error", "")},
                {"name": "postexec-uid-system", "pass": values.get("postexec.uid.effective") == "1000", "detail": values.get("postexec.uid.effective", "")},
                {"name": "postexec-gid-system", "pass": values.get("postexec.gid.effective") == "1000", "detail": values.get("postexec.gid.effective", "")},
                {"name": "postexec-group-inet", "pass": group_values_have(values, "3003"), "detail": values.get("postexec.groups.values", "")},
                {"name": "postexec-group-net-admin", "pass": group_values_have(values, "3005"), "detail": values.get("postexec.groups.values", "")},
                {"name": "postexec-group-wifi", "pass": group_values_have(values, "1010"), "detail": values.get("postexec.groups.values", "")},
                {"name": "postexec-cap-net-admin-effective", "pass": cap_hex_has(values.get("postexec.cap.effective_hex"), 12), "detail": values.get("postexec.cap.effective_hex", "")},
                {"name": "postexec-cap-net-admin-permitted", "pass": cap_hex_has(values.get("postexec.cap.permitted_hex"), 12), "detail": values.get("postexec.cap.permitted_hex", "")},
                {"name": "postexec-cap-net-admin-ambient", "pass": cap_hex_has(values.get("postexec.cap.ambient_hex"), 12), "detail": values.get("postexec.cap.ambient_hex", "")},
            ]
        )
    if not all(item["pass"] for item in checks):
        return False, "cnss-identity-probe-gap", "identity/capability probe did not satisfy every required check", checks
    return True, "cnss-identity-probe-pass", "harmless child satisfied uid/gid/groups/CAP_NET_ADMIN contract inside private namespace", checks


def write_summary(store: EvidenceStore, manifest: dict[str, Any], values: dict[str, str]) -> None:
    rows = [[item["name"], "PASS" if item["pass"] else "FAIL", item.get("detail", "")] for item in manifest["checks"]]
    key_rows = [
        ["uid", values.get("identity.after.uid.effective", "")],
        ["gid", values.get("identity.after.gid.effective", "")],
        ["groups", values.get("identity.after.groups.values", "")],
        ["cap effective", values.get("identity.after.cap.net_admin.effective", "")],
        ["cap permitted", values.get("identity.after.cap.net_admin.permitted", "")],
        ["cap inheritable", values.get("identity.after.cap.net_admin.inheritable", "")],
        ["ambient", values.get("identity_probe.ambient_raise.ok", values.get("identity_probe.ambient_raise.error", ""))],
        ["postexec uid", values.get("postexec.uid.effective", "")],
        ["postexec gid", values.get("postexec.gid.effective", "")],
        ["postexec groups", values.get("postexec.groups.values", "")],
        ["postexec cap effective", values.get("postexec.cap.effective_hex", "")],
        ["postexec cap permitted", values.get("postexec.cap.permitted_hex", "")],
        ["postexec cap ambient", values.get("postexec.cap.ambient_hex", "")],
    ]
    lines = [
        "# v244 CNSS Identity Probe\n\n",
        f"- generated: `{manifest['created']}`\n",
        f"- result: `{'PASS' if manifest['pass'] else 'FAIL'}`\n",
        f"- decision: `{manifest['decision']}`\n",
        f"- reason: `{manifest['reason']}`\n",
        f"- daemon start: `not executed`\n",
        f"- output: `{manifest['out_dir']}`\n\n",
        "## Checks\n\n",
        markdown_table(["check", "result", "detail"], rows),
        "\n\n## Observed Identity\n\n",
        markdown_table(["field", "value"], key_rows),
        "\n\n## Interpretation\n\n",
        "- v244 proves the launcher identity/capability contract on a harmless child and harmless `/system/bin/toybox cat /proc/self/status` exec only.\n",
        "- `cnss-daemon` start-only remains blocked until a separate explicit runner is implemented and approved.\n",
        "- Wi-Fi scan/connect/link-up/credential/DHCP/routing remain blocked.\n",
    ]
    store.write_text("summary.md", "".join(lines))


def run_probe(args: argparse.Namespace) -> int:
    store = EvidenceStore(repo_path(args.out_dir))
    v243 = load_json(args.v243_manifest)
    host_captures: list[dict[str, Any]] = []
    helper_capture: dict[str, Any] | None = None
    values: dict[str, str] = {}
    setup_ok = True
    setup_detail = "ready"

    if args.command != "dry-run":
        if not args.skip_build:
            build_capture = run_host(store, "build-helper", ["scripts/revalidation/build_android_execns_probe_helper.sh"], timeout=120.0)
            host_captures.append(build_capture)
            if not build_capture["ok"]:
                setup_ok = False
                setup_detail = "build-helper failed"
        if not args.skip_deploy:
            deploy_capture = run_host(store, "deploy-helper", build_helper_command(args), timeout=args.transfer_timeout + 30.0)
            host_captures.append(deploy_capture)
            if not deploy_capture["ok"]:
                setup_ok = False
                setup_detail = "deploy-helper failed"
        if setup_ok:
            capture = run_capture(args, "identity-probe", identity_probe_command(args), timeout=args.helper_timeout_sec + 30.0)
            store.write_text("identity-probe.txt", capture.text if capture.text else capture.error + "\n")
            helper_capture = capture_to_manifest(capture)
            values = parse_key_values(capture.text)

    result_pass, decision, reason, checks = classify_probe(v243, setup_ok, setup_detail, helper_capture, values)
    manifest = {
        "created": now_iso(),
        "out_dir": str(repo_path(args.out_dir)),
        "pass": result_pass,
        "decision": decision,
        "reason": reason,
        "host_metadata": collect_host_metadata(),
        "inputs": {
            "v243_manifest": v243.get("_manifest_path", v243.get("path", "")),
            "v243_decision": v243.get("decision", "missing"),
        },
        "helper": {
            "local": str(repo_path(args.helper)),
            "remote": args.remote_helper,
        },
        "checks": checks,
        "host_captures": host_captures,
        "helper_capture": helper_capture,
        "parsed_values": values,
        "guardrails": [
            "no cnss-daemon execution",
            "no cnss_diag execution",
            "no Wi-Fi scan/connect/link-up/credential/DHCP/routing",
            "no rfkill write",
            "no ICNSS bind/unbind",
            "private/no-follow host evidence output",
        ],
    }
    store.write_json("manifest.json", manifest)
    store.write_json("identity-values.json", values)
    write_summary(store, manifest, values)

    print(f"decision: {decision}")
    print(f"pass: {result_pass}")
    print(f"out_dir: {repo_path(args.out_dir)}")
    return 0 if result_pass else 1


def main() -> int:
    args = parse_args()
    return run_probe(args)


if __name__ == "__main__":
    raise SystemExit(main())
