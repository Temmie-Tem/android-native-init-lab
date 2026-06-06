#!/usr/bin/env python3
"""v272 host-only QMI service object ID extractor.

This extractor parses exported QMI IDL service object symbols from vendor ELF
files and reads the service id field directly from the object data. It does not
execute Android code, open QRTR sockets, send QRTR nameservice packets, or send
QMI payloads.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import struct
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path  # noqa: E402
from a90harness.evidence import EvidenceStore  # noqa: E402


DEFAULT_OUT_DIR = Path("tmp/wifi/v272-qmi-service-object-extractor")
DEFAULT_VENDOR_ROOT = Path("tmp/wifi/v226-vendor-root-live-export/vendor-source")
DEFAULT_V271_MANIFEST = Path("tmp/wifi/v271-qrtr-service-selector/manifest.json")

ELF_MAGIC = b"\x7fELF"
SHT_SYMTAB = 2
SHT_DYNSYM = 11
PT_LOAD = 1
STT_OBJECT = 1
SERVICE_OBJECT_MIN_SIZE = 64
SERVICE_OBJECT_READ_SIZE = 72


@dataclass(frozen=True)
class ProgramHeader:
    p_type: int
    p_offset: int
    p_vaddr: int
    p_filesz: int


@dataclass(frozen=True)
class SectionHeader:
    name: str
    sh_type: int
    sh_offset: int
    sh_size: int
    sh_entsize: int
    sh_link: int


@dataclass(frozen=True)
class Symbol:
    name: str
    st_info: int
    st_shndx: int
    st_value: int
    st_size: int
    table: str

    @property
    def sym_type(self) -> int:
        return self.st_info & 0x0F


class Elf64LE:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.data = path.read_bytes()
        if len(self.data) < 64 or self.data[:4] != ELF_MAGIC:
            raise ValueError(f"not an ELF file: {path}")
        if self.data[4] != 2 or self.data[5] != 1:
            raise ValueError(f"expected ELF64 little-endian: {path}")
        header = struct.unpack_from("<16sHHIQQQIHHHHHH", self.data, 0)
        self.e_phoff = header[5]
        self.e_shoff = header[6]
        self.e_phentsize = header[9]
        self.e_phnum = header[10]
        self.e_shentsize = header[11]
        self.e_shnum = header[12]
        self.e_shstrndx = header[13]
        self.program_headers = self._read_program_headers()
        self.sections = self._read_sections()

    def _read_program_headers(self) -> list[ProgramHeader]:
        headers: list[ProgramHeader] = []
        for index in range(self.e_phnum):
            off = self.e_phoff + index * self.e_phentsize
            if off + 56 > len(self.data):
                raise ValueError(f"program header outside file: {self.path}")
            values = struct.unpack_from("<IIQQQQQQ", self.data, off)
            headers.append(
                ProgramHeader(
                    p_type=values[0],
                    p_offset=values[2],
                    p_vaddr=values[3],
                    p_filesz=values[5],
                )
            )
        return headers

    def _raw_section_headers(self) -> list[tuple[int, int, int, int, int, int, int]]:
        headers: list[tuple[int, int, int, int, int, int, int]] = []
        for index in range(self.e_shnum):
            off = self.e_shoff + index * self.e_shentsize
            if off + 64 > len(self.data):
                raise ValueError(f"section header outside file: {self.path}")
            sh_name, sh_type, _flags, _addr, sh_offset, sh_size, sh_link, _info, _addralign, sh_entsize = struct.unpack_from(
                "<IIQQQQIIQQ", self.data, off
            )
            headers.append((sh_name, sh_type, sh_offset, sh_size, sh_link, sh_entsize, index))
        return headers

    def _read_sections(self) -> list[SectionHeader]:
        raw = self._raw_section_headers()
        if self.e_shstrndx >= len(raw):
            raise ValueError(f"invalid shstrndx: {self.path}")
        shstr = self.slice(raw[self.e_shstrndx][2], raw[self.e_shstrndx][3])
        sections: list[SectionHeader] = []
        for sh_name, sh_type, sh_offset, sh_size, sh_link, sh_entsize, _index in raw:
            sections.append(
                SectionHeader(
                    name=self.read_c_string(shstr, sh_name),
                    sh_type=sh_type,
                    sh_offset=sh_offset,
                    sh_size=sh_size,
                    sh_entsize=sh_entsize,
                    sh_link=sh_link,
                )
            )
        return sections

    def slice(self, offset: int, size: int) -> bytes:
        if offset < 0 or size < 0 or offset + size > len(self.data):
            raise ValueError(f"file range outside ELF: {self.path} offset={offset} size={size}")
        return self.data[offset:offset + size]

    @staticmethod
    def read_c_string(table: bytes, offset: int) -> str:
        if offset < 0 or offset >= len(table):
            return ""
        end = table.find(b"\0", offset)
        if end < 0:
            end = len(table)
        return table[offset:end].decode("utf-8", errors="replace")

    def vaddr_to_offset(self, vaddr: int, size: int) -> int:
        for header in self.program_headers:
            if header.p_type != PT_LOAD:
                continue
            if header.p_vaddr <= vaddr and vaddr + size <= header.p_vaddr + header.p_filesz:
                return header.p_offset + (vaddr - header.p_vaddr)
        raise ValueError(f"cannot map vaddr 0x{vaddr:x} size={size} in {self.path}")

    def symbols(self) -> list[Symbol]:
        out: list[Symbol] = []
        for section in self.sections:
            if section.sh_type not in {SHT_DYNSYM, SHT_SYMTAB}:
                continue
            if section.sh_entsize == 0 or section.sh_link >= len(self.sections):
                continue
            strings = self.sections[section.sh_link]
            string_table = self.slice(strings.sh_offset, strings.sh_size)
            count = section.sh_size // section.sh_entsize
            for index in range(count):
                off = section.sh_offset + index * section.sh_entsize
                if off + 24 > len(self.data):
                    continue
                st_name, st_info, _st_other, st_shndx, st_value, st_size = struct.unpack_from("<IBBHQQ", self.data, off)
                name = self.read_c_string(string_table, st_name)
                if name:
                    out.append(Symbol(name, st_info, st_shndx, st_value, st_size, section.name))
        return out


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as file_obj:
        payload = json.load(file_obj)
    return payload if isinstance(payload, dict) else {}


def run_host_command(command: list[str], timeout: int = 30) -> dict[str, Any]:
    try:
        result = subprocess.run(
            command,
            cwd=repo_path("."),
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )
        return {"command": command, "rc": result.returncode, "ok": result.returncode == 0, "text": result.stdout, "error": ""}
    except Exception as exc:  # noqa: BLE001 - evidence preserves exact host failure
        return {"command": command, "rc": None, "ok": False, "text": "", "error": str(exc)}


def service_name_from_symbol(symbol: str) -> str:
    for suffix in ("_qmi_idl_service_object_v01", "_qmi_idl_service_object_v02"):
        if symbol.endswith(suffix):
            return symbol[: -len(suffix)]
    return symbol


def parse_service_object_bytes(blob: bytes) -> dict[str, Any]:
    if len(blob) < SERVICE_OBJECT_READ_SIZE:
        raise ValueError("short service object")
    lib_version, idl_major, service_id, max_message_len = struct.unpack_from("<IIII", blob, 0)
    command_count, response_count, indication_count, _reserved = struct.unpack_from("<HHHH", blob, 16)
    command_table, response_table, indication_table, type_table = struct.unpack_from("<QQQQ", blob, 24)
    max_message_id = struct.unpack_from("<I", blob, 56)[0]
    return {
        "idl_library_version": lib_version,
        "idl_major_version": idl_major,
        "service_id": service_id,
        "max_message_len": max_message_len,
        "command_count": command_count,
        "response_count": response_count,
        "indication_count": indication_count,
        "command_table_vaddr": command_table,
        "response_table_vaddr": response_table,
        "indication_table_vaddr": indication_table,
        "type_table_vaddr": type_table,
        "max_message_id": max_message_id,
    }


def extract_from_elf(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    elf = Elf64LE(path)
    objects: list[dict[str, Any]] = []
    errors: list[str] = []
    for symbol in elf.symbols():
        if "_qmi_idl_service_object_v" not in symbol.name:
            continue
        if symbol.sym_type != STT_OBJECT and symbol.st_size < SERVICE_OBJECT_MIN_SIZE:
            continue
        if symbol.st_size < SERVICE_OBJECT_MIN_SIZE:
            continue
        try:
            file_offset = elf.vaddr_to_offset(symbol.st_value, min(symbol.st_size, SERVICE_OBJECT_READ_SIZE))
            blob = elf.slice(file_offset, min(symbol.st_size, SERVICE_OBJECT_READ_SIZE))
            parsed = parse_service_object_bytes(blob)
        except Exception as exc:  # noqa: BLE001 - keep bad symbol evidence
            errors.append(f"{symbol.name}: {exc}")
            continue
        objects.append(
            {
                "elf": str(path),
                "symbol": symbol.name,
                "service_name": service_name_from_symbol(symbol.name),
                "symbol_table": symbol.table,
                "vaddr": f"0x{symbol.st_value:x}",
                "file_offset": f"0x{file_offset:x}",
                "size": symbol.st_size,
                **parsed,
            }
        )
    return sorted(objects, key=lambda item: (item["service_id"], item["service_name"], item["symbol"])), {
        "path": str(path),
        "errors": errors,
    }


def add_check(checks: list[dict[str, Any]], name: str, passed: bool, detail: str, *, severity: str = "critical") -> None:
    checks.append({"name": name, "pass": passed, "severity": severity, "detail": detail})


def by_service_name(objects: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for item in objects:
        out.setdefault(str(item["service_name"]), item)
    return out


def by_service_id(objects: list[dict[str, Any]]) -> dict[int, list[dict[str, Any]]]:
    out: dict[int, list[dict[str, Any]]] = {}
    for item in objects:
        out.setdefault(int(item["service_id"]), []).append(item)
    return out


def render_summary(manifest: dict[str, Any]) -> str:
    rows = [
        [
            str(item["service_name"]),
            str(item["service_id"]),
            str(item["idl_library_version"]),
            str(item["idl_major_version"]),
            str(item["max_message_len"]),
            str(item["max_message_id"]),
            str(item["symbol"]),
        ]
        for item in manifest["service_objects"]
    ]
    candidate_rows = [
        [
            str(item["candidate"]),
            str(item["status"]),
            str(item["service_id"]),
            str(item["evidence"]),
            str(item["next_action"]),
        ]
        for item in manifest["candidate_resolution"]
    ]
    lines = [
        "# QMI Service Object Extractor\n\n",
        f"- decision: `{manifest['decision']}`\n",
        f"- pass: `{manifest['pass']}`\n",
        f"- reason: {manifest['reason']}\n\n",
        "## Checks\n\n",
    ]
    for item in manifest["checks"]:
        lines.append(f"- {'PASS' if item['pass'] else 'FAIL'} `{item['name']}` ({item['severity']}): {item['detail']}\n")
    lines.extend(
        [
            "\n## Candidate Resolution\n\n",
            markdown_table(["candidate", "status", "service_id", "evidence", "next action"], candidate_rows),
            "\n\n## Extracted Service Objects\n\n",
            markdown_table(
                ["service", "service_id", "lib", "idl_major", "max_msg_len", "max_msg_id", "symbol"],
                rows,
            ),
            "\n\n## Guardrails\n\n",
        ]
    )
    for item in manifest["guardrails"]:
        lines.append(f"- {item}\n")
    return "".join(lines)


def analyze(args: argparse.Namespace) -> dict[str, Any]:
    out_dir = repo_path(args.out_dir)
    store = EvidenceStore(out_dir)
    store.mkdir("captures")

    vendor_root = repo_path(args.vendor_root)
    libqmiservices = vendor_root / "lib64/libqmiservices.so"
    cnss_daemon = vendor_root / "bin/cnss-daemon"
    qmi_cci = vendor_root / "lib64/libqmi_cci.so"
    v271_manifest_path = repo_path(args.v271_manifest)
    v271_manifest = load_json(v271_manifest_path)

    service_objects: list[dict[str, Any]] = []
    extract_errors: list[dict[str, Any]] = []
    for elf_path in (libqmiservices, cnss_daemon):
        if not elf_path.exists():
            extract_errors.append({"path": str(elf_path), "errors": ["missing"]})
            continue
        extracted, meta = extract_from_elf(elf_path)
        service_objects.extend(extracted)
        extract_errors.append(meta)

    for name, path in (
        ("libqmiservices-readelf-symbols", libqmiservices),
        ("cnss-readelf-symbols", cnss_daemon),
        ("qmi-cci-readelf-symbols", qmi_cci),
    ):
        capture = run_host_command(["readelf", "-Ws", str(path)], timeout=args.host_timeout)
        store.write_text(f"captures/{name}.txt", str(capture.get("text") or capture.get("error") or ""))

    objects_by_name = by_service_name(service_objects)
    objects_by_id = by_service_id(service_objects)
    dms = objects_by_name.get("dms")
    wds_for_id1 = objects_by_id.get(1, [])
    wlfw = objects_by_name.get("wlfw")
    wlan = objects_by_name.get("wlan")

    checks: list[dict[str, Any]] = []
    add_check(checks, "v271-ready", v271_manifest.get("decision") == "qrtr-service-selector-ready" and v271_manifest.get("pass") is True, f"decision={v271_manifest.get('decision')} pass={v271_manifest.get('pass')}")
    add_check(checks, "libqmiservices-exists", libqmiservices.exists(), str(libqmiservices))
    add_check(checks, "cnss-daemon-exists", cnss_daemon.exists(), str(cnss_daemon))
    add_check(checks, "service-objects-extracted", len(service_objects) > 0, f"count={len(service_objects)}")
    add_check(checks, "dms-service-id-extracted", dms is not None and int(dms["service_id"]) == 2, json.dumps(dms, sort_keys=True) if dms else "missing")
    add_check(checks, "service-id-1-maps-to-wds", any(item["service_name"] == "wds" for item in wds_for_id1), json.dumps(wds_for_id1[:3], sort_keys=True))
    add_check(checks, "wlfw-service-object-absent", wlfw is None, "expected unresolved in current libqmiservices evidence", severity="warning")

    candidate_resolution = [
        {
            "candidate": "service=1 instance=1",
            "status": "deprioritized",
            "service_id": 1,
            "evidence": "service id 1 maps to WDS in libqmiservices; v270 readback returned zero events",
            "next_action": "do not reuse service=1 as Wi-Fi firmware control guess",
        },
        {
            "candidate": "dms",
            "status": "resolved",
            "service_id": int(dms["service_id"]) if dms else None,
            "evidence": "DMS service object extracted from libqmiservices",
            "next_action": "eligible for explicit-approval QRTR nameservice readback matrix, no QMI payload",
        },
        {
            "candidate": "wlfw",
            "status": "unresolved",
            "service_id": int(wlfw["service_id"]) if wlfw else None,
            "evidence": "cnss-daemon strings indicate WLFW, but no exported wlfw service object was extracted",
            "next_action": "locate WLFW object source/symbol before packet-based lookup",
        },
        {
            "candidate": "wlan",
            "status": "unresolved" if wlan is None else "resolved",
            "service_id": int(wlan["service_id"]) if wlan else None,
            "evidence": "cnss-daemon strings indicate WLAN service naming; exported object not proven",
            "next_action": "keep secondary until WLFW/DMS path is exhausted",
        },
    ]

    critical_pass = all(item["pass"] for item in checks if item["severity"] == "critical")
    decision = "qmi-service-object-ids-extracted" if critical_pass else "qmi-service-object-extractor-incomplete"
    reason = (
        "DMS service id extracted as 2 and service id 1 mapped to WDS; WLFW remains unresolved"
        if critical_pass
        else "critical service object extraction prerequisite failed"
    )
    manifest = {
        "created": dt.datetime.now(dt.timezone.utc).isoformat(),
        "mode": "qmi-service-object-extractor",
        "decision": decision,
        "pass": critical_pass,
        "reason": reason,
        "out_dir": str(out_dir),
        "inputs": {
            "vendor_root": str(vendor_root),
            "libqmiservices": str(libqmiservices),
            "cnss_daemon": str(cnss_daemon),
            "qmi_cci": str(qmi_cci),
            "v271_manifest": str(v271_manifest_path),
        },
        "host_metadata": collect_host_metadata(),
        "checks": checks,
        "service_objects": service_objects,
        "extract_errors": extract_errors,
        "candidate_resolution": candidate_resolution,
        "next_candidates": [
            "v273 explicit-approval QRTR nameservice readback matrix for DMS service id 2 and selected known service ids, no QMI payload",
            "WLFW service object locator from Android source or additional vendor blobs",
            "Do not send QMI request payloads until service visibility is proven and a separate payload contract exists",
        ],
        "guardrails": [
            "host-only ELF parsing",
            "no Android code execution",
            "no device command executed",
            "no QRTR socket opened",
            "no QRTR nameservice packet sent",
            "no QMI payload sent",
            "no Wi-Fi scan/connect/link-up/credential/DHCP/routing",
        ],
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--vendor-root", type=Path, default=DEFAULT_VENDOR_ROOT)
    parser.add_argument("--v271-manifest", type=Path, default=DEFAULT_V271_MANIFEST)
    parser.add_argument("--host-timeout", type=int, default=30)
    parser.add_argument("command", choices=("analyze",), nargs="?", default="analyze")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = analyze(args)
    print(json.dumps({"decision": manifest["decision"], "pass": manifest["pass"], "out_dir": manifest["out_dir"]}, ensure_ascii=False, sort_keys=True))
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
