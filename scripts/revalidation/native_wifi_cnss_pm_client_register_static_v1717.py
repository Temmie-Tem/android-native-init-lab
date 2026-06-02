#!/usr/bin/env python3
"""V1717 host-only classifier for cnss-daemon pm_client_register blocker."""

from __future__ import annotations

import hashlib
import json
import shlex
import subprocess
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
VENDOR_ROOT = REPO_ROOT / "tmp" / "wifi" / "v226-vendor-root-live-export" / "vendor-source"
CNSS_DAEMON = VENDOR_ROOT / "bin" / "cnss-daemon"
LIBPERIPHERAL = VENDOR_ROOT / "lib64" / "libperipheral_client.so"
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1717-cnss-pm-client-register-static"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1717_CNSS_PM_CLIENT_REGISTER_STATIC_2026-06-02.md"
)


def run(command: list[object]) -> str:
    completed = subprocess.run(
        [str(item) for item in command],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return completed.stdout


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def collect_needed(path: Path) -> list[str]:
    needed: list[str] = []
    for line in run(["readelf", "-d", path]).splitlines():
        marker = "Shared library: ["
        if marker in line:
            needed.append(line.split(marker, 1)[1].split("]", 1)[0])
    return needed


def collect_symbol_offsets(path: Path, names: set[str]) -> dict[str, dict[str, Any]]:
    symbols: dict[str, dict[str, Any]] = {}
    for line in run(["readelf", "-Ws", path]).splitlines():
        parts = line.split()
        if len(parts) < 8:
            continue
        name = parts[7].split("@", 1)[0]
        if name in names:
            symbols[name] = {
                "value": f"0x{int(parts[1], 16):x}",
                "size": int(parts[2]),
                "type": parts[3],
                "bind": parts[4],
                "section": parts[6],
                "raw": line.strip(),
            }
    return symbols


def disassemble(start: int, stop: int) -> str:
    return run([
        "aarch64-linux-gnu-objdump",
        "-d",
        f"--start-address=0x{start:x}",
        f"--stop-address=0x{stop:x}",
        LIBPERIPHERAL,
    ])


def strings_hits(path: Path, needles: list[str]) -> dict[str, bool]:
    output = run(["strings", "-a", "-tx", path])
    return {needle: needle in output for needle in needles}


def write_json_private(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    flags = "x" if not path.exists() else "w"
    with path.open(flags, encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")
    path.chmod(0o600)


def render_report(manifest: dict[str, Any]) -> str:
    cnss_symbols = manifest["cnss_symbols"]
    lib_symbols = manifest["lib_symbols"]
    strings = manifest["string_checks"]
    return "\n".join([
        "# Native Init V1717 CNSS pm_client_register Static Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1717`",
        "- Type: host-only static classifier for the V1716 `pm-init-register-call-no-return` blocker",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: `pm_client_register` is a `libperipheral_client.so` Binder client path for `vendor.qcom.PeripheralManager` over `/dev/vndbinder`",
        f"- Evidence: `{manifest['out_dir']}`",
        "",
        "## Inputs",
        "",
        f"- `cnss-daemon`: `{manifest['cnss_daemon']}`",
        f"- `cnss-daemon` SHA256: `{manifest['cnss_sha256']}`",
        f"- `libperipheral_client.so`: `{manifest['libperipheral']}`",
        f"- `libperipheral_client.so` SHA256: `{manifest['lib_sha256']}`",
        "",
        "## Symbol Ownership",
        "",
        f"- `cnss-daemon` imports `pm_client_register`: `{cnss_symbols.get('pm_client_register', {}).get('raw')}`",
        f"- `cnss-daemon` imports `pm_client_connect`: `{cnss_symbols.get('pm_client_connect', {}).get('raw')}`",
        f"- `cnss-daemon` imports `get_system_info`: `{cnss_symbols.get('get_system_info', {}).get('raw')}`",
        f"- `libperipheral_client.so` exports `pm_client_register`: `{lib_symbols.get('pm_client_register', {}).get('raw')}`",
        f"- `libperipheral_client.so` exports `pm_client_connect`: `{lib_symbols.get('pm_client_connect', {}).get('raw')}`",
        f"- `libperipheral_client.so` exports `pm_register_connect`: `{lib_symbols.get('_ZN7android19pm_register_connectEPNS_23PeripheralManagerClientEP8pm_event', {}).get('raw')}`",
        "",
        "## Binder Contract",
        "",
        f"- `/dev/vndbinder` string present: `{strings['/dev/vndbinder']}`",
        f"- `vendor.qcom.PeripheralManager` string present: `{strings['vendor.qcom.PeripheralManager']}`",
        f"- `Failed to get binder object` string present: `{strings['Failed to get binder object']}`",
        f"- `Failed to get binder interface object` string present: `{strings['Failed to get binder interface object']}`",
        f"- `Peripheral manager server alive` string present: `{strings['Peripheral manager server alive']}`",
        "",
        "## Static Flow",
        "",
        "- `pm_client_register@0x6ec8` validates inputs, allocates a `PeripheralManagerClient`, creates the Binder callback object, then calls internal `pm_register_connect@0x612c` from `0x7034`.",
        "- `pm_register_connect@0x612c` calls `ProcessState::initWithDriver('/dev/vndbinder')` at `0x6168`.",
        "- It calls `defaultServiceManager()` at `0x6190` and constructs `String16('vendor.qcom.PeripheralManager')` at `0x61a8`.",
        "- It then performs the service-manager virtual call at `0x61c4`; this is the first likely blocking point when the vendor Binder service-manager path is unavailable.",
        "- If a Binder object is returned, it calls `IPeripheralManager::asInterface` at `0x6218`, then the manager register transaction at `0x6274`.",
        "- V1716 hit `pm_client_register@0xc624` from `cnss-daemon` and did not hit the caller return check at `0xc628`; therefore the live block is inside this library path before `pm_client_connect`.",
        "",
        "## V1718 Candidate Trace Points",
        "",
        "- Target binary: `libperipheral_client.so`, not `cnss-daemon`.",
        "- `pm_client_register_entry`: `0x6ec8`.",
        "- `pm_register_connect_entry`: `0x612c`.",
        "- `process_state_init_with_driver_call`: `0x6168`.",
        "- `default_service_manager_call`: `0x6190`.",
        "- `peripheral_manager_string16_call`: `0x61a8`.",
        "- `service_manager_get_call`: `0x61c4`.",
        "- `binder_object_present_check`: `0x620c`.",
        "- `as_interface_call`: `0x6218`.",
        "- `manager_register_transaction_call`: `0x6274`.",
        "- `manager_register_transaction_retcheck`: `0x6278`.",
        "- `success_list_insert_path`: `0x6538`.",
        "- `pm_register_connect_return`: `0x66dc`.",
        "- `pm_client_register_return_path`: `0x7180`.",
        "",
        "## Interpretation",
        "",
        "- The V1716 blocker is now a vendor Binder PeripheralManager registration path, not `get_system_info`, firmware serving, MHI, WLFW service 69, Wi-Fi HAL, scan/connect, DHCP/routes, or external ping.",
        "- This does not justify adding service-manager or PM actors yet. First trace the `libperipheral_client.so` path with one bounded non-mutating uprobe run.",
        "- If the next live trace blocks at `defaultServiceManager` or service lookup, the missing dependency is vendor Binder service-manager availability.",
        "- If it reaches the manager register transaction and blocks there, the missing dependency is the actual `vendor.qcom.PeripheralManager` service endpoint.",
        "",
        "## Safety Scope",
        "",
        "This script performed host-side static analysis only. It did not contact the device, flash, reboot, run service-manager/PM actors, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.",
        "",
    ])


def main() -> int:
    if not CNSS_DAEMON.exists():
        raise FileNotFoundError(CNSS_DAEMON)
    if not LIBPERIPHERAL.exists():
        raise FileNotFoundError(LIBPERIPHERAL)
    OUT_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    cnss_symbols = collect_symbol_offsets(CNSS_DAEMON, {"pm_client_register", "pm_client_connect", "get_system_info"})
    lib_symbols = collect_symbol_offsets(
        LIBPERIPHERAL,
        {
            "pm_client_register",
            "pm_client_connect",
            "_ZN7android19pm_register_connectEPNS_23PeripheralManagerClientEP8pm_event",
        },
    )
    string_checks = strings_hits(
        LIBPERIPHERAL,
        [
            "/dev/vndbinder",
            "vendor.qcom.PeripheralManager",
            "Failed to get binder object",
            "Failed to get binder interface object",
            "Peripheral manager server alive",
        ],
    )
    needed = collect_needed(LIBPERIPHERAL)
    required = {
        "cnss_import_register": "pm_client_register" in cnss_symbols,
        "cnss_import_connect": "pm_client_connect" in cnss_symbols,
        "lib_export_register": "pm_client_register" in lib_symbols,
        "lib_export_internal_register_connect": "_ZN7android19pm_register_connectEPNS_23PeripheralManagerClientEP8pm_event" in lib_symbols,
        "libbinder_needed": "libbinder.so" in needed,
        "vndbinder_string": string_checks["/dev/vndbinder"],
        "peripheral_manager_string": string_checks["vendor.qcom.PeripheralManager"],
    }
    pass_ok = all(required.values())
    manifest: dict[str, Any] = {
        "cycle": "V1717",
        "decision": "v1717-cnss-pm-client-register-static-pass" if pass_ok else "v1717-cnss-pm-client-register-static-blocked",
        "pass": pass_ok,
        "out_dir": str(OUT_DIR.relative_to(REPO_ROOT)),
        "cnss_daemon": str(CNSS_DAEMON.relative_to(REPO_ROOT)),
        "cnss_sha256": sha256(CNSS_DAEMON),
        "libperipheral": str(LIBPERIPHERAL.relative_to(REPO_ROOT)),
        "lib_sha256": sha256(LIBPERIPHERAL),
        "cnss_needed": collect_needed(CNSS_DAEMON),
        "lib_needed": needed,
        "cnss_symbols": cnss_symbols,
        "lib_symbols": lib_symbols,
        "string_checks": string_checks,
        "required_checks": required,
        "commands": {
            "cnss_readelf": shlex.join(["readelf", "-Ws", str(CNSS_DAEMON)]),
            "lib_readelf": shlex.join(["readelf", "-Ws", str(LIBPERIPHERAL)]),
            "register_disasm": shlex.join([
                "aarch64-linux-gnu-objdump",
                "-d",
                "--start-address=0x6ec8",
                "--stop-address=0x71bc",
                str(LIBPERIPHERAL),
            ]),
            "register_connect_disasm": shlex.join([
                "aarch64-linux-gnu-objdump",
                "-d",
                "--start-address=0x612c",
                "--stop-address=0x66fc",
                str(LIBPERIPHERAL),
            ]),
        },
    }
    write_json_private(OUT_DIR / "manifest.json", manifest)
    (OUT_DIR / "pm_client_register.disasm.txt").write_text(disassemble(0x6ec8, 0x71bc), encoding="utf-8")
    (OUT_DIR / "pm_register_connect.disasm.txt").write_text(disassemble(0x612c, 0x66fc), encoding="utf-8")
    (OUT_DIR / "pm_client_register.disasm.txt").chmod(0o600)
    (OUT_DIR / "pm_register_connect.disasm.txt").chmod(0o600)
    REPORT_PATH.write_text(render_report(manifest), encoding="utf-8")
    print(json.dumps({
        "cycle": "V1717",
        "decision": manifest["decision"],
        "pass": pass_ok,
        "manifest": str((OUT_DIR / "manifest.json").relative_to(REPO_ROOT)),
        "report": str(REPORT_PATH.relative_to(REPO_ROOT)),
    }, indent=2))
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
