#!/usr/bin/env python3
"""A90 NCM host-side preflight and persistent setup template generator.

The script is intentionally non-mutating. It detects likely A90 USB NCM
interfaces, verifies the expected host CIDR, optionally pings the device, and
writes copyable system configuration templates under the evidence directory.
"""

from __future__ import annotations

import argparse
import datetime as dt
import ipaddress
import json
import os
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, ensure_private_dir, write_private_text


DEFAULT_OUT_DIR = Path("tmp/host/a90-ncm-host-preflight")
DEFAULT_DEVICE_IP = "192.168.7.2"
DEFAULT_HOST_IP = "192.168.7.1"
DEFAULT_PREFIX = 24
SAMSUNG_VENDOR_ID = "04e8"
NCM_DRIVER = "cdc_ncm"


@dataclass
class CommandResult:
    command: str
    rc: int
    stdout: str
    stderr: str


@dataclass
class InterfaceInfo:
    name: str
    mac: str
    operstate: str
    driver: str
    usb_vendor: str
    usb_product: str
    usb_manufacturer: str
    usb_product_name: str
    ipv4: list[str]
    candidate: bool
    candidate_reason: str
    has_expected_cidr: bool


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def run_text(command: list[str], *, timeout: float = 10.0) -> CommandResult:
    try:
        result = subprocess.run(
            command,
            cwd=repo_path("."),
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
        return CommandResult(" ".join(command), result.returncode, result.stdout, result.stderr)
    except Exception as exc:  # noqa: BLE001 - host preflight evidence should keep failures
        return CommandResult(" ".join(command), 127, "", str(exc))


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""


def resolve_driver(iface: str) -> str:
    path = Path("/sys/class/net") / iface / "device" / "driver"
    try:
        return path.resolve().name
    except OSError:
        return ""


def usb_attrs(iface: str) -> dict[str, str]:
    current = (Path("/sys/class/net") / iface).resolve()
    attrs = {
        "idVendor": "",
        "idProduct": "",
        "manufacturer": "",
        "product": "",
    }
    for parent in [current, *current.parents]:
        for key in list(attrs):
            if attrs[key]:
                continue
            value = read_text(parent / key)
            if value:
                attrs[key] = value
        if attrs["idVendor"] and attrs["idProduct"]:
            break
    return attrs


def ipv4_addrs() -> dict[str, list[str]]:
    result = run_text(["ip", "-4", "-o", "addr"], timeout=5.0)
    addrs: dict[str, list[str]] = {}
    if result.rc != 0:
        return addrs
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) < 4:
            continue
        ifname = parts[1]
        if parts[2] != "inet":
            continue
        addrs.setdefault(ifname, []).append(parts[3])
    return addrs


def classify_interface(iface: str, cidr: str, ipv4_by_iface: dict[str, list[str]]) -> InterfaceInfo:
    base = Path("/sys/class/net") / iface
    attrs = usb_attrs(iface)
    driver = resolve_driver(iface)
    ipv4 = ipv4_by_iface.get(iface, [])
    reasons: list[str] = []
    if driver == NCM_DRIVER:
        reasons.append(f"driver={NCM_DRIVER}")
    if attrs["idVendor"].lower() == SAMSUNG_VENDOR_ID:
        reasons.append(f"idVendor={SAMSUNG_VENDOR_ID}")
    if iface.startswith("enx"):
        reasons.append("ifname=enx*")
    candidate = driver == NCM_DRIVER or (
        attrs["idVendor"].lower() == SAMSUNG_VENDOR_ID and iface.startswith("enx")
    )
    return InterfaceInfo(
        name=iface,
        mac=read_text(base / "address"),
        operstate=read_text(base / "operstate"),
        driver=driver,
        usb_vendor=attrs["idVendor"],
        usb_product=attrs["idProduct"],
        usb_manufacturer=attrs["manufacturer"],
        usb_product_name=attrs["product"],
        ipv4=ipv4,
        candidate=candidate,
        candidate_reason=", ".join(reasons) if reasons else "",
        has_expected_cidr=cidr in ipv4,
    )


def list_interfaces(cidr: str) -> list[InterfaceInfo]:
    ipv4_by_iface = ipv4_addrs()
    interfaces: list[InterfaceInfo] = []
    for item in sorted(Path("/sys/class/net").iterdir()):
        if item.name == "lo":
            continue
        interfaces.append(classify_interface(item.name, cidr, ipv4_by_iface))
    return interfaces


def valid_ipv4(value: str) -> str:
    try:
        return str(ipaddress.IPv4Address(value))
    except ipaddress.AddressValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def service_state(name: str) -> str:
    result = run_text(["systemctl", "is-active", name], timeout=5.0)
    if result.rc == 0:
        return result.stdout.strip() or "active"
    return result.stdout.strip() or result.stderr.strip() or "unknown"


def ping_device(device_ip: str) -> dict[str, Any]:
    result = run_text(["ping", "-c", "1", "-W", "1", device_ip], timeout=4.0)
    return {
        "command": result.command,
        "rc": result.rc,
        "ok": result.rc == 0,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def render_templates(host_ip: str, prefix: int) -> dict[str, str]:
    cidr = f"{host_ip}/{prefix}"
    return {
        "a90-ncm-up.sh": "\n".join([
            "#!/bin/sh",
            "set -eu",
            'IFACE="${1:-${INTERFACE:-}}"',
            'case "$IFACE" in',
            '  ""|*/*|*..*|*";"*|*" "*|*"\\t"*) exit 2 ;;',
            "esac",
            f"/usr/sbin/ip link set \"$IFACE\" up",
            f"/usr/sbin/ip addr replace {cidr} dev \"$IFACE\"",
            "",
        ]),
        "90-a90-ncm.rules": "\n".join([
            "# Copy to /etc/udev/rules.d/90-a90-ncm.rules after installing a90-ncm-up.sh.",
            "# Uses systemd-run so udev does not block on network setup.",
            (
                'ACTION=="add|change", SUBSYSTEM=="net", DRIVERS=="cdc_ncm", '
                'ATTRS{idVendor}=="04e8", '
                'RUN+="/usr/bin/systemd-run --no-block --property=Type=oneshot '
                '/usr/local/sbin/a90-ncm-up %k"'
            ),
            "",
        ]),
        "90-a90-ncm.network": "\n".join([
            "# Copy to /etc/systemd/network/90-a90-ncm.network only if systemd-networkd manages this host.",
            "[Match]",
            "Driver=cdc_ncm",
            "",
            "[Network]",
            f"Address={cidr}",
            "LinkLocalAddressing=no",
            "IPv6AcceptRA=no",
            "",
        ]),
        "a90-ncm-sudoers": "\n".join([
            "# Optional fallback: copy to /etc/sudoers.d/a90-ncm via visudo -cf first.",
            "# Prefer udev/systemd-run or a NetworkManager profile for persistent operation.",
            f"{os.environ.get('USER', 'temmie')} ALL=(root) NOPASSWD: /usr/local/sbin/a90-ncm-up *",
            "",
        ]),
        "networkmanager-nmcli.txt": "\n".join([
            "# NetworkManager is active on Kubuntu by default. Prefer a dedicated profile",
            "# only if you can bind it to the A90 NCM interface without catching other USB NICs.",
            "sudo nmcli connection add type ethernet con-name a90-ncm ifname '*' \\",
            f"  ipv4.method manual ipv4.addresses {cidr} ipv6.method ignore connection.autoconnect yes",
            "# Then restrict autoconnect to the current A90 NCM interface/MAC if needed:",
            "# sudo nmcli connection modify a90-ncm 802-3-ethernet.mac-address <A90_NCM_HOST_MAC>",
            "",
        ]),
    }


def write_templates(store: EvidenceStore, host_ip: str, prefix: int) -> list[str]:
    written: list[str] = []
    template_dir = store.path("templates")
    ensure_private_dir(template_dir)
    for name, text in render_templates(host_ip, prefix).items():
        path = template_dir / name
        write_private_text(path, text)
        if name.endswith(".sh"):
            path.chmod(0o700)
        written.append(str(path))
    return written


def decide(interfaces: list[InterfaceInfo], cidr: str, ping: dict[str, Any]) -> tuple[str, bool, str, str]:
    candidates = [item for item in interfaces if item.candidate]
    with_cidr = [item for item in interfaces if item.has_expected_cidr]
    candidate_with_cidr = [item for item in candidates if item.has_expected_cidr]
    if candidate_with_cidr and ping["ok"]:
        return "a90-ncm-host-ready", True, "A90 NCM candidate has expected CIDR and device ping passed", "use NCM deploy"
    if candidate_with_cidr:
        return "a90-ncm-host-address-present-ping-failed", False, "A90 NCM CIDR is present but device ping failed", "check device NCM state or cable"
    if with_cidr and ping["ok"]:
        return "a90-ncm-host-ready-addr-only", True, "expected CIDR exists and device ping passed, but interface was not classified as NCM", "review classifier evidence, then use NCM deploy"
    if candidates:
        return "a90-ncm-host-needs-address", False, f"A90 NCM candidate exists but {cidr} is not assigned", "install a persistent host autoconfig option or run ncm_host_setup.py setup"
    return "a90-ncm-host-no-interface", False, "no likely A90 NCM interface detected", "enable device NCM and reconnect USB"


def render_summary(manifest: dict[str, Any]) -> str:
    iface_rows = [
        [
            item["name"],
            item["driver"],
            item["usb_vendor"],
            item["mac"],
            ",".join(item["ipv4"]),
            str(item["candidate"]),
            str(item["has_expected_cidr"]),
        ]
        for item in manifest["interfaces"]
    ]
    service_rows = [[key, value] for key, value in manifest["host_services"].items()]
    return "\n".join([
        "# A90 NCM Host Preflight",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- host_cidr: `{manifest['host_cidr']}`",
        f"- device_ip: `{manifest['device_ip']}`",
        f"- ping_ok: `{manifest['ping']['ok']}`",
        "",
        "## Interfaces",
        "",
        markdown_table(["name", "driver", "vendor", "mac", "ipv4", "candidate", "cidr"], iface_rows),
        "",
        "## Host Services",
        "",
        markdown_table(["service", "state"], service_rows),
        "",
        "## Templates",
        "",
        "\n".join(f"- `{item}`" for item in manifest["templates"]),
        "",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    cidr = f"{args.host_ip}/{args.prefix}"
    interfaces = list_interfaces(cidr)
    ping = ping_device(args.device_ip) if not args.no_ping else {
        "command": "",
        "rc": 0,
        "ok": False,
        "stdout": "",
        "stderr": "skipped",
    }
    templates = write_templates(store, args.host_ip, args.prefix)
    decision, pass_ok, reason, next_step = decide(interfaces, cidr, ping)
    return {
        "generated_at": now_iso(),
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "host_ip": args.host_ip,
        "device_ip": args.device_ip,
        "prefix": args.prefix,
        "host_cidr": cidr,
        "interfaces": [asdict(item) for item in interfaces],
        "host_services": {
            "NetworkManager": service_state("NetworkManager"),
            "systemd-networkd": service_state("systemd-networkd"),
        },
        "ping": ping,
        "templates": templates,
        "device_mutations": False,
        "host_mutations": False,
        "blocked_actions": [
            "writing /etc/udev/rules.d",
            "writing /etc/systemd/network",
            "writing /etc/sudoers.d",
            "running sudo ip addr/link commands",
            "changing NetworkManager profiles",
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host-ip", type=valid_ipv4, default=DEFAULT_HOST_IP)
    parser.add_argument("--device-ip", type=valid_ipv4, default=DEFAULT_DEVICE_IP)
    parser.add_argument("--prefix", type=int, default=DEFAULT_PREFIX)
    parser.add_argument("--no-ping", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("run")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not (1 <= args.prefix <= 32):
        raise SystemExit("--prefix must be 1..32")
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
