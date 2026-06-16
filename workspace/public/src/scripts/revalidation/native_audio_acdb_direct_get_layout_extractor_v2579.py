#!/usr/bin/env python3
"""V2579 host-only ACDB direct-GET request-layout extractor.

The extractor consumes private Thumb disassembly generated from the stock
libacdbloader.so and emits only metadata/report evidence. It does not touch the
phone and does not execute any ACDB command.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

RUN_ID = "V2579"
BUILD_TAG = "v2579-audio-acdb-direct-get-layout-extractor"
ROOT = Path(__file__).resolve().parents[5]
DEFAULT_V2578_DIR = ROOT / "workspace/private/runs/audio/v2578-acdb-lower-get-abi-recon"
DEFAULT_LIBACDBLOADER = ROOT / "workspace/private/runs/audio/v2324-aud0-inventory/vendor_dump/lib/libacdbloader.so"
DEFAULT_OUT_DIR = ROOT / "workspace/private/runs/audio/v2579-acdb-direct-get-layout-extractor"
DEFAULT_REPORT = ROOT / "docs/reports/NATIVE_INIT_V2579_AUDIO_ACDB_DIRECT_GET_LAYOUT_EXTRACTOR_2026-06-16.md"

STORE_FUNC = "acdb_loader_store_get_audio_cal"
ADSP_FUNC = "acdb_loader_adsp_get_audio_cal"
GET_V2_FUNC = "acdb_loader_get_audio_cal_v2"
GET_CAL_FUNC = "acdb_loader_get_calibration"
SEND_V5_FUNC = "acdb_loader_send_audio_cal_v5"

REQUIRED_STORE_PATTERNS = {
    "selector_offset_28": r"ldr\s+r0, \[r5, #28\]",
    "selector_37": r"cmp\s+r0, #37",
    "selector_1": r"cmp\s+r0, #1",
    "selector_0": r"cmp\s+r0, #0",
    "instance_gate_ptr": r"ldr\w*\s+r1, \[r5, #32\]|ldr\s+r1, \[r5, #32\]",
    "instance_gate_len": r"ldrne\s+r2, \[r5, #40\]|ldrne\s+r1, \[r5, #40\]",
    "base_0x13091": r"movw\s+r0, #12433",
    "alt_0x11399": r"movw\s+r0, #5017",
    "plus_466": r"add\.w\s+r0, r0, #466",
    "plus_468": r"add\.w\s+r0, r0, #468",
    "plus_474": r"add\.w\s+r0, r0, #474",
    "out_len_4": r"str\s+r0, \[sp\]",
}

REQUIRED_ADSP_PATTERNS = {
    "selector_offset_28": r"ldr\s+r0, \[r6, #28\]",
    "selector_1": r"cmp\s+r0, #1",
    "fields_12_16": r"ldrd\s+r2, r1, \[r6, #12\]|ldrd\s+r0, r1, \[r6, #16\]",
    "field_20": r"ldr\s+r0, \[r6, #20\]",
    "field_32": r"ldr\s+r0, \[r6, #32\]",
    "field_36": r"ldrh\s+r0, \[r6, #36\]",
    "field_40": r"ldrne\s+r1, \[r6, #40\]",
    "helper_cmd_0x111": r"movw\s+r0, #273",
}

STORE_SCHEMAS = [
    {
        "case": "store_selector_37",
        "selector_req_plus_28": 37,
        "instance_gate": "not used on this branch",
        "command_hex": "0x13091",
        "in_len": 12,
        "out_len": 4,
        "request_fields": ["req+12", "*out_len_io", "out_buf_arg"],
        "evidence_addresses": ["0xe752", "0xe754", "0xe7cc", "0xe7d2", "0xe7d6", "0xe7da", "0xe828"],
        "confidence": "high for size/command/field offsets; indirect payload semantics still require a build-only harness",
    },
    {
        "case": "store_selector_0_no_instance",
        "selector_req_plus_28": 0,
        "instance_gate": "req+32 == 0 or req+40 == 0",
        "command_hex": "0x13265",
        "in_len": 20,
        "out_len": 4,
        "request_fields": ["req+12", "req+16", "req+24", "*out_len_io", "out_buf_arg"],
        "evidence_addresses": ["0xe75c", "0xe786", "0xe7a0", "0xe7a4", "0xe7ae", "0xe7b4"],
        "confidence": "high for selector and ioctl ABI; output is indirect via input struct",
    },
    {
        "case": "store_selector_0_instance",
        "selector_req_plus_28": 0,
        "instance_gate": "req+32 != 0 and req+40 != 0",
        "command_hex": "0x13263",
        "in_len": 32,
        "out_len": 4,
        "request_fields": ["req+12", "req+16", "req+24", "req+36:u16", "req+32", "req+40", "*out_len_io", "out_buf_arg"],
        "evidence_addresses": ["0xe790", "0xe79a", "0xe868", "0xe872", "0xe884", "0xe890"],
        "confidence": "medium-high; branch is instance-specific and still needs cal-type mapping",
    },
    {
        "case": "store_selector_1_no_instance",
        "selector_req_plus_28": 1,
        "instance_gate": "req+32 == 0 or req+40 == 0",
        "command_hex": "0x11399",
        "in_len": 12,
        "out_len": 4,
        "request_fields": ["req+16", "*out_len_io", "out_buf_arg"],
        "evidence_addresses": ["0xe758", "0xe80e", "0xe818", "0xe81c", "0xe828"],
        "confidence": "high for selector and command; output is indirect via input struct",
    },
    {
        "case": "store_selector_1_instance",
        "selector_req_plus_28": 1,
        "instance_gate": "req+32 != 0 and req+40 != 0",
        "command_hex": "0x1326b",
        "in_len": 24,
        "out_len": 4,
        "request_fields": ["req+16", "req+36:u16", "req+32", "req+40", "*out_len_io", "out_buf_arg"],
        "evidence_addresses": ["0xe800", "0xe80c", "0xe89a", "0xe8b6", "0xe8c6"],
        "confidence": "medium-high; branch is instance-specific and still needs cal-type mapping",
    },
]

ADSP_OBSERVATIONS = [
    {
        "case": "adsp_selector_0_or_default",
        "selector_req_plus_28": 0,
        "observed_fields": ["req+12", "req+16", "req+20", "req+32", "req+36", "req+40"],
        "helper_command_literal": "0x111",
        "direct_live_readiness": "blocked: branch calls internal helpers before an indirect-output command; request ABI not yet sufficient for a live direct GET",
        "evidence_addresses": ["0xe96a", "0xe976", "0xe97a", "0xe994", "0xe9fc", "0xea10"],
    },
    {
        "case": "adsp_selector_1",
        "selector_req_plus_28": 1,
        "observed_fields": ["req+12", "req+16", "req+20", "req+32", "req+36", "req+40"],
        "helper_command_literal": "0x111 after selector-specific helper",
        "direct_live_readiness": "blocked: selector-specific helper at 0xe9c0 must be resolved before issuing live commands",
        "evidence_addresses": ["0xe970", "0xe9b8", "0xe9c0", "0xe9cc", "0xea10"],
    },
]


def rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return str(p.relative_to(ROOT))
    except ValueError:
        return str(p)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_function_dump(dump_dir: Path, symbol: str) -> str:
    path = dump_dir / f"{symbol}.thumb-objdump.txt"
    if not path.exists():
        raise FileNotFoundError(f"missing private disassembly dump: {rel(path)}")
    return path.read_text(encoding="utf-8", errors="replace")


def pattern_hits(text: str, patterns: dict[str, str]) -> dict[str, list[dict[str, object]]]:
    lines = text.splitlines()
    output: dict[str, list[dict[str, object]]] = {}
    for name, pattern in patterns.items():
        regex = re.compile(pattern, re.IGNORECASE)
        hits: list[dict[str, object]] = []
        for idx, line in enumerate(lines):
            if regex.search(line):
                hits.append({"line": idx + 1, "text": line.strip()})
        output[name] = hits
    return output


def validate_required_hits(hits: dict[str, list[dict[str, object]]]) -> dict[str, object]:
    missing = [name for name, rows in hits.items() if not rows]
    return {"ok": not missing, "missing": missing}


def command_value(base: int, addend: int = 0) -> str:
    return f"0x{base + addend:05x}"


def build_manifest(args: argparse.Namespace) -> dict[str, object]:
    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    store_text = read_function_dump(args.v2578_dump_dir, STORE_FUNC)
    adsp_text = read_function_dump(args.v2578_dump_dir, ADSP_FUNC)
    get_v2_text = read_function_dump(args.v2578_dump_dir, GET_V2_FUNC)
    get_cal_text = read_function_dump(args.v2578_dump_dir, GET_CAL_FUNC)
    send_v5_text = read_function_dump(args.v2578_dump_dir, SEND_V5_FUNC)

    store_hits = pattern_hits(store_text, REQUIRED_STORE_PATTERNS)
    adsp_hits = pattern_hits(adsp_text, REQUIRED_ADSP_PATTERNS)
    validation = {
        "store_get_audio_cal": validate_required_hits(store_hits),
        "adsp_get_audio_cal": validate_required_hits(adsp_hits),
        "computed_command_checks": {
            "0x13091_plus_466": command_value(0x13091, 466),
            "0x13091_plus_468": command_value(0x13091, 468),
            "0x13091_plus_474": command_value(0x13091, 474),
            "0x11399": command_value(0x11399),
        },
    }

    manifest: dict[str, object] = {
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "host-only static layout extraction; no device action and no ACDB command execution",
        "inputs": {
            "v2578_dump_dir": rel(args.v2578_dump_dir),
            "libacdbloader": {
                "path": rel(args.libacdbloader),
                "exists": args.libacdbloader.exists(),
                "sha256": sha256_file(args.libacdbloader) if args.libacdbloader.exists() else None,
            },
        },
        "validation": validation,
        "store_get_audio_cal": {
            "function_signature_model": "int store_get_audio_cal(req*, out_buf_arg, out_len_io*) inferred from r0/r1/r2 preservation",
            "request_struct_min_size": 44,
            "selector_offset": 28,
            "instance_gate_offsets": [32, 40],
            "schemas": STORE_SCHEMAS,
            "pattern_hits": store_hits,
        },
        "adsp_get_audio_cal": {
            "function_signature_model": "int adsp_get_audio_cal(req*, out_buf_arg, out_len_io*) inferred from r0/r1/r2 preservation",
            "request_struct_min_size": 44,
            "observations": ADSP_OBSERVATIONS,
            "pattern_hits": adsp_hits,
        },
        "get_audio_cal_v2": {
            "wrapper_model": "requires req != NULL, initialized flag true, and *(uint32_t*)req != 0 before tail-calling lower getter path",
            "host_observation": "thin wrapper; useful for future helper only after lower request layout is pinned",
        },
        "get_calibration": {
            "wrapper_model": "requires arg0 != NULL, arg1 == 24, arg2 != NULL before delegating to an internal getter",
            "host_observation": "not the first live path because the 24-byte external struct target is not yet mapped to speaker cal types",
        },
        "send_audio_cal_v5": {
            "host_observation": "continues to show internal request construction, but V2575/V2577 closed public-send reruns as low-information",
            "private_text_sha256": hashlib.sha256(send_v5_text.encode("utf-8", errors="replace")).hexdigest(),
        },
    }
    overall_ok = bool(validation["store_get_audio_cal"]["ok"] and validation["adsp_get_audio_cal"]["ok"])
    manifest["decision"] = "v2579-direct-get-layout-host-extracted" if overall_ok else "v2579-direct-get-layout-host-partial"
    manifest_path = out_dir / "v2579-direct-get-layout.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    manifest["manifest_path"] = rel(manifest_path)
    return manifest


def schema_table(schemas: Iterable[dict[str, object]]) -> str:
    rows = ["| case | selector | gate | command | in_len | out_len | fields | confidence |", "| --- | ---: | --- | ---: | ---: | ---: | --- | --- |"]
    for schema in schemas:
        fields = ", ".join(str(item) for item in schema.get("request_fields", []))
        rows.append(
            f"| `{schema['case']}` | `{schema['selector_req_plus_28']}` | {schema['instance_gate']} | "
            f"`{schema['command_hex']}` | `{schema['in_len']}` | `{schema['out_len']}` | {fields} | {schema['confidence']} |"
        )
    return "\n".join(rows)


def observation_table(observations: Iterable[dict[str, object]]) -> str:
    rows = ["| case | selector | fields | command/helper | live readiness |", "| --- | ---: | --- | --- | --- |"]
    for obs in observations:
        fields = ", ".join(str(item) for item in obs.get("observed_fields", []))
        rows.append(
            f"| `{obs['case']}` | `{obs['selector_req_plus_28']}` | {fields} | `{obs['helper_command_literal']}` | {obs['direct_live_readiness']} |"
        )
    return "\n".join(rows)


def render_report(manifest: dict[str, object]) -> str:
    inputs = manifest.get("inputs", {}) if isinstance(manifest.get("inputs"), dict) else {}
    lib = inputs.get("libacdbloader", {}) if isinstance(inputs.get("libacdbloader"), dict) else {}
    validation = manifest.get("validation", {}) if isinstance(manifest.get("validation"), dict) else {}
    store_validation = validation.get("store_get_audio_cal", {}) if isinstance(validation.get("store_get_audio_cal"), dict) else {}
    adsp_validation = validation.get("adsp_get_audio_cal", {}) if isinstance(validation.get("adsp_get_audio_cal"), dict) else {}
    command_checks = validation.get("computed_command_checks", {}) if isinstance(validation.get("computed_command_checks"), dict) else {}
    return f"""# NATIVE_INIT V2579 — ACDB direct-GET request-layout extractor

## Scope

Host-only static extraction after V2578. No device action, Android handoff, native calibration
ioctl, speaker write, ACDB command execution, or raw payload capture was performed.

## Decision

- decision: `{manifest.get('decision')}`
- private manifest: `{manifest.get('manifest_path')}`
- input libacdbloader sha256: `{lib.get('sha256')}`
- store pattern validation: `{store_validation.get('ok')}` missing `{store_validation.get('missing')}`
- adsp pattern validation: `{adsp_validation.get('ok')}` missing `{adsp_validation.get('missing')}`

## Store Getter Layout

`acdb_loader_store_get_audio_cal` is the first concrete direct-GET candidate. It preserves the
caller arguments as request pointer (`r0`), output buffer argument (`r1`), and output length pointer
(`r2`), branches on `req+28`, uses `req+32`/`req+40` as the instance gate, and issues small
`out_len=4` ACDB queries whose real payload path is indirect through the input struct.

{schema_table(STORE_SCHEMAS)}

Computed command checks:

- `0x13091 + 466 = {command_checks.get('0x13091_plus_466')}`
- `0x13091 + 468 = {command_checks.get('0x13091_plus_468')}`
- `0x13091 + 474 = {command_checks.get('0x13091_plus_474')}`
- alternate literal = `{command_checks.get('0x11399')}`

## ADSP Getter Layout

`acdb_loader_adsp_get_audio_cal` is not ready for live direct GET. It reads the same request-family
offsets, but it goes through selector-specific internal helpers before the final command path.

{observation_table(ADSP_OBSERVATIONS)}

## Wrapper Constraints

- `acdb_loader_get_audio_cal_v2` is only a thin gate: `req != NULL`, initialized flag true, and
  `*(uint32_t *)req != 0` before tail-calling a lower getter. It is not a substitute for request
  layout pinning.
- `acdb_loader_get_calibration` requires a `24`-byte external struct and delegates internally; it is
  not the first speaker-cal live route because that external struct is not yet mapped to the Android
  speaker cal sequence.

## Interpretation

V2579 narrows the next executable path to a build-only helper around the `store_get_audio_cal`
request-family, not another public `send_audio_cal_v5` or common-topology hook rerun. The safe next
step is to generate a future helper that constructs 44-byte request structs for the five store cases,
allocates bounded output buffers privately, and stops after pure-read return/zero-buffer checks.
Live execution is still blocked until that helper has build-only forbidden-symbol checks and an exact
future gate; no `AUDIO_SET_CALIBRATION` or speaker write is permitted here.

## Next Unit

V2580 should be build-only: create the pure-read `store_get_audio_cal` harness with no live default,
cover the five request cases above, reject real SET/ioctl symbols, and preserve the V2530 rule that
success requires `ret==0` plus non-all-zero output rather than requested length alone.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_direct_get_layout_extractor_v2579.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_direct_get_layout_extractor_v2579`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_direct_get_layout_extractor_v2579.py --write-report`
- `git diff --check`
"""


def write_report(path: Path, manifest: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_report(manifest), encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v2578-dump-dir", type=Path, default=DEFAULT_V2578_DIR)
    parser.add_argument("--libacdbloader", type=Path, default=DEFAULT_LIBACDBLOADER)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--write-report", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        manifest = build_manifest(args)
    except FileNotFoundError as error:
        print(json.dumps({"ok": False, "error": str(error)}, indent=2))
        return 2
    if args.write_report:
        write_report(args.report_path, manifest)
    ok = manifest.get("decision") == "v2579-direct-get-layout-host-extracted"
    print(json.dumps({
        "ok": ok,
        "decision": manifest.get("decision"),
        "manifest_path": manifest.get("manifest_path"),
        "report_path": rel(args.report_path) if args.write_report else None,
    }, indent=2, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
