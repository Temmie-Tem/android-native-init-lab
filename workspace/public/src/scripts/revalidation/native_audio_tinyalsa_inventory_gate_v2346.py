#!/usr/bin/env python3
"""V2346 host-only planner for post-materialization tinyalsa inventory.

This script intentionally does not touch the device.  It verifies the private
V2345 tinyalsa tool bundle and emits the exact bounded command plan for the
future read-only tinyalsa inventory gate after AUD-3 /dev/snd materialization
has passed.  It must not be used for playback, mixer writes, or PCM writes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RUN_ID = "V2346"
BUILD_TAG = "v2346-audio-tinyalsa-inventory-gate"
REQUIRED_APPROVAL_PHRASE = (
    "AUD-3C-tinyalsa-inventory go: read-only tinyalsa mixer/PCM inventory on "
    "materialized V2334, no mixer set, no tinyplay/playback, rollback to V2321"
)
TINYALSA_COMMIT = "e14bf1479ebaaabf60bc4472ce8d304f72f03c32"
EXPECTED_TOOL_HASHES = {
    "tinymix": "747b19a5a263a3f2f02223ba2bad2aa0e34f9e8a3948093d612d57e3ada15411",
    "tinypcminfo": "f1c370e6088cf6acca129c1c1f4a77a1d11d51526c3ba25721991505cbf4929e",
}
PROHIBITED_TOOLS = {"tinyplay"}
PROHIBITED_COMMAND_TOKENS = {
    "tinyplay",
    "aplay",
    "speaker-test",
    "pcm_write",
    "pcm_open",
    "BC_FREE_BUFFER",
}
REMOTE_DIR = "/cache/a90-audio/v2346-tinyalsa-inventory"
REMOTE_TOOLS = {
    "tinymix": f"{REMOTE_DIR}/tinymix",
    "tinypcminfo": f"{REMOTE_DIR}/tinypcminfo",
}


def repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "GOAL.md").exists() and (parent / "workspace").exists():
            return parent
    raise RuntimeError("could not locate repository root")


ROOT = repo_root()
MANIFEST = ROOT / "workspace/private/builds/audio/v2345-audio-tinyalsa-tools/manifest.json"
V2335_RUNNER = ROOT / "workspace/public/src/scripts/revalidation/native_audio_snd_nodes_preflight_handoff_v2335.py"
V2345_BUILDER = ROOT / "workspace/public/src/scripts/revalidation/build_audio_tinyalsa_tools_v2345.py"


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest(path: Path = MANIFEST) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def tool_record(manifest: dict[str, Any], tool: str) -> dict[str, Any]:
    try:
        record = manifest["build"]["tools"][tool]
    except KeyError as exc:
        raise RuntimeError(f"missing tinyalsa tool record: {tool}") from exc
    return record


def verify_tool(manifest: dict[str, Any], tool: str) -> dict[str, Any]:
    record = tool_record(manifest, tool)
    path = ROOT / str(record.get("path", ""))
    expected = EXPECTED_TOOL_HASHES[tool]
    exists = path.exists()
    actual = sha256_file(path) if exists else ""
    file_text = str(record.get("file", ""))
    return {
        "tool": tool,
        "path": rel(path),
        "exists": exists,
        "sha256": actual,
        "expected_sha256": expected,
        "sha256_ok": bool(exists and actual == expected == record.get("sha256")),
        "manifest_sha256": record.get("sha256", ""),
        "file": file_text,
        "file_ok": "ARM aarch64" in file_text and "statically linked" in file_text and "stripped" in file_text,
    }


def verify_manifest(path: Path = MANIFEST) -> dict[str, Any]:
    exists = path.exists()
    if not exists:
        return {"exists": False, "path": rel(path), "ok": False, "reason": "manifest missing"}
    manifest = load_manifest(path)
    source = manifest.get("source", {})
    tools = {tool: verify_tool(manifest, tool) for tool in EXPECTED_TOOL_HASHES}
    prohibited = {}
    for tool in PROHIBITED_TOOLS:
        try:
            record = tool_record(manifest, tool)
        except RuntimeError:
            prohibited[tool] = {"present_in_manifest": False, "used_by_v2346": False}
        else:
            prohibited[tool] = {
                "present_in_manifest": True,
                "path": record.get("path", ""),
                "used_by_v2346": False,
            }
    ok = bool(
        source.get("commit") == TINYALSA_COMMIT
        and all(item["sha256_ok"] and item["file_ok"] for item in tools.values())
        and V2335_RUNNER.exists()
        and V2345_BUILDER.exists()
    )
    return {
        "exists": True,
        "path": rel(path),
        "ok": ok,
        "source_commit": source.get("commit", ""),
        "expected_source_commit": TINYALSA_COMMIT,
        "tools": tools,
        "prohibited_tools": prohibited,
        "prerequisite_scripts": {
            "snd_materialization_runner": rel(V2335_RUNNER),
            "tinyalsa_builder": rel(V2345_BUILDER),
            "present": V2335_RUNNER.exists() and V2345_BUILDER.exists(),
        },
    }


def planned_inventory_commands(card: int = 0, pcm_devices: tuple[int, ...] = (0,)) -> list[dict[str, Any]]:
    commands: list[dict[str, Any]] = [
        {
            "name": "tinymix-list-card0",
            "kind": "mixer-list",
            "mutates_audio_state": False,
            "opens_alsa": True,
            "argv": [REMOTE_TOOLS["tinymix"], "-D", str(card)],
            "reason": "tinymix with no control/value arguments lists mixer controls only",
        },
        {
            "name": "tinymix-list-card0-all-values",
            "kind": "mixer-list-detail",
            "mutates_audio_state": False,
            "opens_alsa": True,
            "argv": [REMOTE_TOOLS["tinymix"], "-D", str(card), "--all-values"],
            "reason": "--all-values expands enum/range reporting without setting any control",
        },
    ]
    for device in pcm_devices:
        commands.append(
            {
                "name": f"tinypcminfo-card{card}-device{device}",
                "kind": "pcm-params-query",
                "mutates_audio_state": False,
                "opens_alsa": True,
                "argv": [REMOTE_TOOLS["tinypcminfo"], "-D", str(card), "-d", str(device)],
                "reason": "tinypcminfo calls pcm_params_get for capability query; no PCM playback/write",
            }
        )
    return commands


def command_safety(commands: list[dict[str, Any]]) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    for command in commands:
        argv = [str(part) for part in command.get("argv", [])]
        tail = argv[1:]
        for token in PROHIBITED_COMMAND_TOKENS:
            if any(token in part for part in argv):
                findings.append({"command": command.get("name"), "prohibited_token": token, "argv": argv})
        if argv and argv[0].endswith("tinymix") and len(tail) > 3:
            findings.append({
                "command": command.get("name"),
                "reason": "tinymix command has extra operands that may set a mixer control",
                "argv": argv,
            })
        if argv and argv[0].endswith("tinypcminfo") and ("-D" not in argv or "-d" not in argv):
            findings.append({
                "command": command.get("name"),
                "reason": "tinypcminfo command must be explicit about card and device",
                "argv": argv,
            })
    return {
        "ok": not findings,
        "findings": findings,
        "allowed_tools": sorted(EXPECTED_TOOL_HASHES),
        "excluded_tools": sorted(PROHIBITED_TOOLS),
        "boundaries": [
            "no live execution in V2346",
            "future live run requires exact AUD-3C approval phrase",
            "requires AUD-3 /dev/snd materialization to have already passed",
            "no mixer set: tinymix must have no value operands",
            "no tinyplay, no PCM playback/write",
            "no audio HAL, no adsprpc invoke/ioctl",
            "rollback target remains V2321 after any future live run",
        ],
    }


def dry_run_payload(args: argparse.Namespace) -> dict[str, Any]:
    manifest_state = verify_manifest(args.manifest)
    commands = planned_inventory_commands(args.card, tuple(args.pcm_device))
    safety = command_safety(commands)
    ok = bool(manifest_state["ok"] and safety["ok"])
    return {
        "decision": "v2346-audio-tinyalsa-inventory-gate-dry-run" if ok else "v2346-audio-tinyalsa-inventory-gate-blocked",
        "ok": ok,
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "created_at": now_iso(),
        "host_only": True,
        "device_action": "none",
        "approval_phrase_required_for_future_live": REQUIRED_APPROVAL_PHRASE,
        "requires_prior_materialization": {
            "runner": rel(V2335_RUNNER),
            "expected_materialized_nodes": ["/dev/snd/controlC0", "/dev/snd/pcmC0D0p or another pcmC*D*p node"],
            "note": "V2346 is not a substitute for the pending AUD-3 /dev/snd materialization gate.",
        },
        "manifest": manifest_state,
        "remote_layout": {
            "dir": REMOTE_DIR,
            "tools": REMOTE_TOOLS,
            "private_source": "workspace/private/builds/audio/v2345-audio-tinyalsa-tools/bin/",
        },
        "planned_commands": commands,
        "command_safety": safety,
        "result_handling": {
            "capture_stdout_stderr": True,
            "redact_device_identifiers": True,
            "commit_policy": "commit only metadata/report; never commit tool binaries or raw device logs",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="verify host artifacts and print future live plan")
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--card", type=int, default=0)
    parser.add_argument("--pcm-device", type=int, action="append", default=[0])
    args = parser.parse_args()
    if not args.dry_run:
        parser.error("V2346 is host-only; pass --dry-run. Future live inventory requires a separate gated runner.")
    payload = dry_run_payload(args)
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if payload["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
