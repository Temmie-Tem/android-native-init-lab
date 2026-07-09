#!/usr/bin/env python3
"""Reconstruct the pinned FYG8 Max77705-to-DWC3 USB role path offline."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
SCHEMA = "s22plus_fyg8_usb_role_static_re_v1"

MODULE_DIR = Path(
    "workspace/private/inputs/s22plus_firmware/S906NKSS7FYG8_SKC/"
    "extracted-images/ramdisk-list/vendor/extract/lib/modules"
)
G0Q_DTS_DIR = Path(
    "workspace/private/inputs/s22plus_kernel_source/S906NKSS7FYG8_osrc/Kernel/"
    "kernel_platform/msm-kernel/arch/arm64/boot/dts/samsung/rainbow/g0q"
)
USB_NOTIFY_SOURCE = Path(
    "workspace/private/inputs/s22plus_kernel_source/S906NKSS7FYG8_osrc/Kernel/"
    "kernel_platform/msm-kernel/drivers/usb/notify/usb_notify.c"
)
DTBO_IMAGE = Path(
    "workspace/private/inputs/s22plus_firmware/S906NKSS7FYG8_SKC/"
    "extracted-images/raw/dtbo.img"
)
DEFAULT_OUT = Path("docs/module-map/s22plus-fyg8/deep-usb-re")
LIVE_SIDECARS = {"live-crosscheck.json"}

MODULE_PINS = {
    "dwc3-msm.ko": "8913b050419e88699033e957d927beef86742ed035f531dc5c4729f50cea60f1",
    "pdic_max77705.ko": "27e988788242888dc0c3acaf835a66585c024b034b07741e619b674ee77db3db",
    "usb_typec_manager.ko": "4da0a4d056abfb09e111ffc4f74fe0adbddcf7be0bc172a48c36f55fd0ea52dc",
    "usb_notifier_qcom.ko": "73f937efc9302d5fa8c2758b5e71b80f52063141d72c063bfe73b1583c781ccb",
    "usb_notify_layer.ko": "710d9cc6f523d615e459d22e2d9e3d1ff082514b7efcd6add0f437e890b3d294",
}
USB_NOTIFY_SOURCE_SHA256 = "cdb489a2aecd3dc4c7d00899421d827c2aa64cd865e931b3a6cc6a3aa540d02b"
DTBO_SHA256 = "97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c"
G0Q_DTS_MANIFEST_SHA256 = "8e9c1bd351d08783adae5670d9b4813af8611b12e032959128f58c3289409255"

EXPECTED_CALL_EDGES = (
    ("pdic_max77705.ko", "max77705_usbc_probe", "typec_register_port"),
    ("pdic_max77705.ko", "max77705_notify_dr_status", "max77705_ccic_event_work"),
    ("pdic_max77705.ko", "max77705_ccic_event_work", "typec_set_data_role"),
    ("pdic_max77705.ko", "max77705_ccic_event_work", "typec_set_pwr_role"),
    ("pdic_max77705.ko", "max77705_ccic_event_notifier", "pdic_notifier_notify"),
    ("usb_typec_manager.ko", "init_module", "pdic_notifier_register"),
    ("usb_typec_manager.ko", "manager_handle_pdic_notification", "manager_event_work"),
    ("usb_typec_manager.ko", "manager_event_notify", "blocking_notifier_call_chain"),
    ("usb_typec_manager.ko", "manager_notifier_register", "blocking_notifier_chain_register"),
    ("usb_notifier_qcom.ko", "usb_notifier_probe", "manager_notifier_register"),
    ("usb_notifier_qcom.ko", "ccic_usb_handle_notification", "send_otg_notify"),
    ("usb_notifier_qcom.ko", "qcom_set_host", "dwc_msm_id_event"),
    ("usb_notifier_qcom.ko", "qcom_set_peripheral", "dwc_msm_vbus_event"),
    ("dwc3-msm.ko", "dwc_msm_id_event", "queue_work_on"),
    ("dwc3-msm.ko", "dwc_msm_vbus_event", "queue_work_on"),
    ("dwc3-msm.ko", "dwc3_msm_probe", "usb_role_switch_register"),
    ("dwc3-msm.ko", "dwc3_msm_usb_role_switch_set_role", "dwc3_msm_set_role"),
    ("dwc3-msm.ko", "dwc3_msm_set_role", "dwc3_ext_event_notify"),
    ("dwc3-msm.ko", "dwc3_msm_core_init", "usb_role_switch_find_by_fwnode"),
    ("dwc3-msm.ko", "dwc3_otg_start_host", "usb_role_switch_set_role"),
    ("dwc3-msm.ko", "dwc3_otg_start_peripheral", "usb_role_switch_set_role"),
)

SOURCE_PATTERNS = {
    "vbus_dispatch": r"case NOTIFY_EVENT_VBUS:.*?n->set_peripheral\(true\).*?n->set_peripheral\(false\)",
    "host_dispatch": r"case NOTIFY_EVENT_HOST:.*?n->set_host\(true\).*?n->set_host\(false\)",
    "queued_state_worker": r"otg_notify_work.*?otg_notify_state\(",
    "send_notifier_entry": r"void send_otg_notify\(",
}

DT_PATTERNS = {
    "parent_role_switch": r"fragment@23.*?__overlay__\s*\{\s*usb-role-switch;",
    "child_role_switch": r"fragment@23.*?dwc3@a600000\s*\{\s*usb-role-switch;",
    "otg_mode": r"dwc3@a600000\s*\{.*?dr_mode = \"otg\";",
    "max77705_mfd": r"compatible = \"maxim,max77705\";",
    "max77705_pdic": r"compatible = \"maxim,max77705_pdic\";",
    "pd_role_swap": r"support_pd_role_swap;",
    "samsung_usb_notifier": r"compatible = \"samsung,usb-notifier\";",
    "ucsi_fixup": r"ucsi = \"/fragment@24:target:0\";",
}

WEB_REFERENCES = (
    "https://android.googlesource.com/kernel/common/+/5bad7993b0ff764e1ff37d00e370c0ed85661ea3/drivers/usb/typec/class.c",
    "https://android.googlesource.com/kernel/common/+/9e5737bd0457955690d871b3f4fc66dea40ea141/drivers/usb/dwc3/drd.c",
    "https://android.googlesource.com/kernel/msm/+/53f9955dd5876826f623fb9a1a736cfe36bec176/drivers/usb/dwc3/dwc3-msm.c",
    "https://www.kernel.org/doc/Documentation/devicetree/bindings/usb/usb-drd.yaml",
)


class StaticReError(ValueError):
    pass


def resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_tool(argv: list[str]) -> str:
    try:
        completed = subprocess.run(
            argv,
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=120,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        raise StaticReError(f"tool failed: {argv[0]}: {exc}") from exc
    if completed.returncode != 0:
        raise StaticReError(
            f"tool failed rc={completed.returncode}: {' '.join(argv)}: {completed.stderr}"
        )
    return completed.stdout


def parse_symbols(path: Path) -> tuple[dict[str, dict[str, Any]], dict[int, list[str]]]:
    output = run_tool(["aarch64-linux-gnu-nm", "-S", "-n", str(path)])
    symbols: dict[str, dict[str, Any]] = {}
    by_address: dict[int, list[str]] = {}
    for line in output.splitlines():
        fields = line.split()
        if len(fields) not in {3, 4} or not re.fullmatch(r"[0-9a-fA-F]+", fields[0]):
            continue
        address = int(fields[0], 16)
        if len(fields) == 4:
            size = int(fields[1], 16)
            kind = fields[2]
            name = fields[3]
        else:
            size = 0
            kind = fields[1]
            name = fields[2]
        symbols[name] = {"address": address, "size": size, "kind": kind}
        by_address.setdefault(address, []).append(name)
    return symbols, by_address


def preferred_symbol(names: list[str]) -> str:
    regular = [name for name in names if ".cfi_jt" not in name and not name.startswith("__typeid")]
    return (regular or names)[0]


def normalize_target(target: str, by_address: dict[int, list[str]]) -> str:
    match = re.fullmatch(r"\.text\+0x([0-9a-fA-F]+)", target)
    if not match:
        return target
    names = by_address.get(int(match.group(1), 16))
    return preferred_symbol(names) if names else target


def parse_call_edges(path: Path, by_address: dict[int, list[str]]) -> set[tuple[str, str]]:
    output = run_tool(["aarch64-linux-gnu-objdump", "-dr", str(path)])
    current = ""
    edges: set[tuple[str, str]] = set()
    for line in output.splitlines():
        header = re.match(r"^[0-9a-fA-F]+ <([^>]+)>:$", line)
        if header:
            current = header.group(1)
            continue
        relocation = re.search(
            r"R_AARCH64_(?:CALL|JUMP)26\s+([^\s]+(?:\+0x[0-9a-fA-F]+)?)",
            line,
        )
        if current and relocation:
            edges.add((current, normalize_target(relocation.group(1), by_address)))
    return edges


def parse_undefined(path: Path) -> set[str]:
    output = run_tool(["aarch64-linux-gnu-nm", "-u", str(path)])
    return {line.split()[-1] for line in output.splitlines() if line.split()}


def parse_callback_table(path: Path, symbols: dict[str, dict[str, Any]], by_address: dict[int, list[str]]) -> list[dict[str, Any]]:
    table = symbols.get("sec_otg_notify")
    if not table:
        raise StaticReError("sec_otg_notify symbol missing")
    start = int(table["address"])
    end = start + int(table["size"])
    output = run_tool(["aarch64-linux-gnu-readelf", "-rW", str(path)])
    entries: list[dict[str, Any]] = []
    pattern = re.compile(
        r"^([0-9a-fA-F]+)\s+.*R_AARCH64_ABS64\s+.*\.text \+ ([0-9a-fA-F]+)$"
    )
    for line in output.splitlines():
        match = pattern.match(line.strip())
        if not match:
            continue
        offset = int(match.group(1), 16)
        target = int(match.group(2), 16)
        if start <= offset < end:
            names = by_address.get(target, [])
            entries.append(
                {
                    "table_offset": offset - start,
                    "relocation_offset": offset,
                    "target_address": target,
                    "target": preferred_symbol(names) if names else f".text+0x{target:x}",
                }
            )
    expected = {"qcom_set_host.cfi_jt", "qcom_set_peripheral.cfi_jt"}
    present = {entry["target"] for entry in entries}
    if not expected <= present:
        raise StaticReError(f"sec_otg_notify callback table drifted: missing={sorted(expected - present)}")
    return sorted(entries, key=lambda entry: entry["table_offset"])


def inspect_modules() -> tuple[dict[str, Any], list[dict[str, str]], list[dict[str, Any]]]:
    module_results: dict[str, Any] = {}
    all_edges: dict[str, set[tuple[str, str]]] = {}
    symbol_maps: dict[str, tuple[dict[str, dict[str, Any]], dict[int, list[str]]]] = {}
    for name, expected_hash in MODULE_PINS.items():
        path = resolve(MODULE_DIR / name)
        if not path.is_file():
            raise StaticReError(f"missing module: {rel(path)}")
        actual_hash = sha256(path)
        if actual_hash != expected_hash:
            raise StaticReError(f"module hash mismatch: {name}: {actual_hash}")
        symbols, by_address = parse_symbols(path)
        edges = parse_call_edges(path, by_address)
        undefined = parse_undefined(path)
        symbol_maps[name] = (symbols, by_address)
        all_edges[name] = edges
        module_results[name] = {
            "path": rel(path),
            "sha256": actual_hash,
            "bytes": path.stat().st_size,
            "defined_symbol_count": len(symbols),
            "undefined_symbol_count": len(undefined),
        }

    proved_edges: list[dict[str, str]] = []
    for module, caller, callee in EXPECTED_CALL_EDGES:
        if (caller, callee) not in all_edges[module]:
            raise StaticReError(f"missing call edge: {module}:{caller}->{callee}")
        proved_edges.append(
            {"module": module, "caller": caller, "callee": callee, "evidence": "ELF_CALL_RELOCATION"}
        )

    notifier_symbols, notifier_by_address = symbol_maps["usb_notifier_qcom.ko"]
    callback_table = parse_callback_table(
        resolve(MODULE_DIR / "usb_notifier_qcom.ko"),
        notifier_symbols,
        notifier_by_address,
    )
    return module_results, proved_edges, callback_table


def inspect_source() -> dict[str, Any]:
    path = resolve(USB_NOTIFY_SOURCE)
    actual_hash = sha256(path)
    if actual_hash != USB_NOTIFY_SOURCE_SHA256:
        raise StaticReError(f"usb_notify.c hash mismatch: {actual_hash}")
    text = path.read_text(encoding="utf-8")
    matches = {
        name: bool(re.search(pattern, text, flags=re.DOTALL))
        for name, pattern in SOURCE_PATTERNS.items()
    }
    if not all(matches.values()):
        raise StaticReError(f"usb_notify.c source pattern drift: {matches}")
    return {
        "path": rel(path),
        "sha256": actual_hash,
        "matches": matches,
        "interpretation": (
            "send_otg_notify queues state events; otg_notify_state dispatches VBUS to "
            "set_peripheral and HOST to set_host"
        ),
    }


def dts_manifest(files: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in files:
        file_hash = sha256(path)
        digest.update(path.name.encode("ascii") + b"\0" + file_hash.encode("ascii") + b"\0")
    return digest.hexdigest()


def fragment_for_marker(text: str, marker: str) -> str:
    starts = list(re.finditer(r"(?m)^\s*fragment@([A-Za-z0-9_]+)\s*\{", text))
    for index, match in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(text)
        if marker in text[match.start() : end]:
            return match.group(1)
    raise StaticReError(f"no fragment contains marker: {marker}")


def fixup_has_fragment(text: str, label: str, fragment: str) -> bool:
    match = re.search(rf"(?m)^\s*{re.escape(label)} = \"([^\"]*)\";", text)
    return bool(match and f"/fragment@{fragment}:target:0" in match.group(1))


def inspect_dt() -> dict[str, Any]:
    directory = resolve(G0Q_DTS_DIR)
    files = sorted(directory.glob("*.dts"))
    if len(files) != 11:
        raise StaticReError(f"expected 11 g0q DTS overlays, found {len(files)}")
    manifest = dts_manifest(files)
    if manifest != G0Q_DTS_MANIFEST_SHA256:
        raise StaticReError(f"g0q DTS manifest mismatch: {manifest}")
    overlays: list[dict[str, Any]] = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        matches = {
            name: bool(re.search(pattern, text, flags=re.DOTALL))
            for name, pattern in DT_PATTERNS.items()
        }
        role_fragment = fragment_for_marker(text, "dwc3@a600000 {\n\t\t\t\tusb-role-switch;")
        max77705_fragment = fragment_for_marker(text, "max77705@66 {")
        notifier_fragment = fragment_for_marker(text, 'compatible = "samsung,usb-notifier";')
        matches.update(
            {
                "usb0_fixup": fixup_has_fragment(text, "usb0", role_fragment),
                "max77705_i2c_fixup": fixup_has_fragment(
                    text, "qupv3_se5_i2c", max77705_fragment
                ),
                "usb_notifier_soc_fixup": fixup_has_fragment(
                    text, "soc", notifier_fragment
                ),
            }
        )
        if not all(matches.values()):
            raise StaticReError(f"DTS topology drift in {path.name}: {matches}")
        revision = re.search(r"dtbo-hw_rev = <0x([0-9a-fA-F]+)>;", text)
        revision_end = re.search(r"dtbo-hw_rev_end = <0x([0-9a-fA-F]+)>;", text)
        overlays.append(
            {
                "name": path.name,
                "sha256": sha256(path),
                "bytes": path.stat().st_size,
                "hw_rev": int(revision.group(1), 16) if revision else None,
                "hw_rev_end": int(revision_end.group(1), 16) if revision_end else None,
                "fragment_indices": {
                    "usb_role": role_fragment,
                    "max77705": max77705_fragment,
                    "usb_notifier": notifier_fragment,
                },
                "matches": matches,
                "explicit_extcon_property_count": len(
                    re.findall(r"(?m)^\s*extcon\s*=", text)
                ),
            }
        )
    if any(item["explicit_extcon_property_count"] for item in overlays):
        raise StaticReError("unexpected explicit extcon property in g0q overlays")
    dtbo = resolve(DTBO_IMAGE)
    dtbo_hash = sha256(dtbo)
    if dtbo_hash != DTBO_SHA256:
        raise StaticReError(f"stock DTBO hash mismatch: {dtbo_hash}")
    return {
        "source_dir": rel(directory),
        "source_manifest_sha256": manifest,
        "overlay_count": len(overlays),
        "overlays": overlays,
        "stock_dtbo": {"path": rel(dtbo), "sha256": dtbo_hash, "bytes": dtbo.stat().st_size},
        "common_topology": {
            "usb0_parent_role_switch": True,
            "dwc3_child_role_switch": True,
            "dwc3_dr_mode": "otg",
            "usb0_to_ucsi_graph_endpoints": True,
            "max77705_i2c_parent_fixup": "qupv3_se5_i2c",
            "max77705_pdic_support_pd_role_swap": True,
            "usb_notifier_parent_fixup": "soc",
            "explicit_extcon_property": False,
            "direct_max77705_to_dwc3_phandle": False,
        },
    }


def build_payload() -> dict[str, Any]:
    modules, edges, callback_table = inspect_modules()
    source = inspect_source()
    dt = inspect_dt()
    return {
        "schema": SCHEMA,
        "result": "pass-static-role-path-reconstructed",
        "target": TARGET,
        "safety": {
            "host_only": True,
            "adb": False,
            "device_read": False,
            "device_write": False,
            "flash": False,
            "reboot": False,
            "module_insertion": False,
        },
        "modules": modules,
        "call_edges": edges,
        "sec_otg_notify_callback_table": callback_table,
        "matched_source": source,
        "device_tree": dt,
        "conclusions": {
            "max77705_typec_reporting": "ELF_VERIFIED",
            "pdic_to_typec_manager_notifier": "ELF_VERIFIED",
            "typec_manager_to_usb_notifier": "ELF_VERIFIED",
            "usb_notify_to_qcom_host_peripheral_callbacks": "ELF_PLUS_SOURCE_VERIFIED",
            "qcom_callbacks_to_dwc3_events": "ELF_VERIFIED",
            "dwc3_parent_and_child_role_switches": "ELF_PLUS_DT_VERIFIED",
            "max77705_to_dwc3_transport": "SAMSUNG_NOTIFIER_CHAIN_NOT_DIRECT_EXTCON_PHANDLE",
            "direct_pid1_automatic_role_without_samsung_chain": "NOT_PROVED",
            "forced_peripheral_role_bypass": "PLAUSIBLE_NOT_PROVED",
        },
        "web_primary_references": list(WEB_REFERENCES),
    }


def render_markdown(payload: dict[str, Any]) -> str:
    modules = payload["modules"]
    dt = payload["device_tree"]
    return f"""# FYG8 Deep USB Role RE

## Verdict

`PASS; EXACT ELF CALL PATH + MATCHED SOURCE + 11 DT OVERLAYS VERIFIED`.

This artifact is generated entirely on the host. It performs no ADB command,
device read/write, module insertion, reboot, image build, or flash.

## Exact Inputs

```text
modules={len(modules)}
call_edges={len(payload['call_edges'])}
g0q_overlays={dt['overlay_count']}
g0q_dts_manifest={dt['source_manifest_sha256']}
stock_dtbo_sha256={dt['stock_dtbo']['sha256']}
usb_notify_source_sha256={payload['matched_source']['sha256']}
```

`live-crosscheck.json`, when present, is a separately collected read-only stock
Android sidecar. It is preserved across host-only regeneration and is not an
input to this static verdict.

## Reconstructed Stock Path

```text
pdic_max77705
  max77705_usbc_probe -> typec_register_port
  max77705_ccic_event_work -> typec_set_data_role/typec_set_pwr_role
  max77705_ccic_event_notifier -> pdic_notifier_notify
        |
        v
usb_typec_manager
  pdic_notifier_register -> manager_event_work
  manager_event_notify -> blocking_notifier_call_chain
        |
        v
usb_notifier_qcom
  manager_notifier_register -> ccic_usb_handle_notification
  ccic callback -> send_otg_notify
  sec_otg_notify callback table -> qcom_set_host/qcom_set_peripheral
        |
        v
usb_notify_layer
  otg_notify_state: HOST -> set_host, VBUS -> set_peripheral
        |
        v
dwc3-msm
  qcom_set_host -> dwc_msm_id_event
  qcom_set_peripheral -> dwc_msm_vbus_event
  events -> OTG work -> parent/child USB role switches
```

Every arrow up to the notifier callback table is backed by a relocation in the
exact FYG8 modules. The `send_otg_notify -> otg_notify_state -> set_*` dispatch
is also present in the SHA-pinned Samsung `usb_notify.c` source and has matching
symbols in the exact `usb_notify_layer.ko`.

## Device Tree

All {dt['overlay_count']} g0q revision overlays contain the same relevant shape:

- `usb0` gets `usb-role-switch` and a `dwc3@a600000` child with
  `usb-role-switch` plus `dr_mode = "otg"`.
- Graph endpoints connect the USB controller overlay to the `ucsi` connector.
- `max77705@66/max77705_pdic` is on `qupv3_se5_i2c`, advertises
  `support_pd_role_swap`, and has no direct DWC3 phandle.
- `samsung,usb-notifier` is a separate platform node under `soc`.
- No overlay contains an explicit `extcon = ...` property for this path.

This matches a runtime notifier design, not a direct Max77705-to-DWC3 DT
dependency. DWC3 still imports some extcon APIs for other state/property paths;
that does not make extcon the proven attach transport here.

## Interpretation Boundary

The stock automatic role path requires more than `dwc3-msm.ko`: it includes the
Max77705 PDIC, Samsung Type-C manager, USB notifier, and USB notify layer. This
does not prove that a direct native PID1 implementation must clone the entire
chain. A deliberate fixed peripheral role may bypass automatic cable/role
policy, but that remains `PLAUSIBLE_NOT_PROVED` until a bounded functional gate.

## Web Cross-Check

Primary Linux/Android sources listed in `static-analysis.json` independently
confirm the method: Type-C port drivers report roles with `typec_set_*`, DWC3
uses `usb-role-switch` when that firmware property exists, and otherwise has an
extcon fallback. They validate the APIs and interpretation method; the exact
Samsung chain above comes from the pinned FYG8 binaries and source artifacts.
"""


def artifacts() -> dict[str, str]:
    payload = build_payload()
    return {
        "README.md": render_markdown(payload),
        "static-analysis.json": json.dumps(payload, indent=2, sort_keys=True) + "\n",
    }


def write_artifacts(out_dir: Path, rendered: dict[str, str]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    expected = set(rendered)
    existing = {path.name for path in out_dir.iterdir() if path.is_file()}
    stale = sorted(existing - expected - LIVE_SIDECARS)
    if stale:
        raise StaticReError(f"refusing stale deep-RE files: {stale}")
    for name, content in rendered.items():
        (out_dir / name).write_text(content, encoding="ascii")


def check_artifacts(out_dir: Path, rendered: dict[str, str]) -> None:
    expected = set(rendered)
    existing = {path.name for path in out_dir.iterdir() if path.is_file()} if out_dir.is_dir() else set()
    mismatches = sorted(
        name
        for name, content in rendered.items()
        if not (out_dir / name).is_file()
        or (out_dir / name).read_text(encoding="ascii") != content
    )
    stale = sorted(existing - expected - LIVE_SIDECARS)
    if mismatches or stale:
        raise StaticReError(f"deep-RE drift mismatches={mismatches} stale={stale}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--check", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    out_dir = resolve(args.out)
    rendered = artifacts()
    if args.check:
        check_artifacts(out_dir, rendered)
        mode = "check"
    else:
        write_artifacts(out_dir, rendered)
        mode = "write"
    payload = json.loads(rendered["static-analysis.json"])
    print(
        json.dumps(
            {
                "result": "pass",
                "mode": mode,
                "out": rel(out_dir),
                "modules": len(payload["modules"]),
                "call_edges": len(payload["call_edges"]),
                "g0q_overlays": payload["device_tree"]["overlay_count"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except StaticReError as exc:
        print(f"static RE failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
