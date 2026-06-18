#!/usr/bin/env python3
"""Build the V2758 native audio SET-cal private manifest.

The generated manifest is intentionally line-oriented so native init can verify
it without a JSON parser.  It contains remote runtime paths, sizes, and SHA-256
digests only; raw ACDB bytes and local private source paths are never emitted.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from native_audio_speaker_profiles_v2749 import (
    DEFAULT_SETCAL_MANIFEST_PATH,
    INTERNAL_SPEAKER_SAFE,
)


DEFAULT_DEPLOY_PLAN = Path(
    "workspace/private/builds/audio/"
    "v2725-audio-acdb-corrected-core39-ioctl-result-deploy-plan/deploy-plan.json"
)
DEFAULT_REMOTE_ROOT = "/cache/a90-runtime/pkg/audio/setcal/internal-speaker-safe"


def _remote_under_root(path: str, remote_root: str) -> str:
    name = Path(path).name
    if not name or name in {".", ".."}:
        raise ValueError(f"bad remote filename from {path!r}")
    return f"{remote_root.rstrip('/')}/{name}"


def _file_index(deploy_plan: dict[str, Any], remote_root: str) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for file_entry in deploy_plan.get("files", []):
        if not isinstance(file_entry, dict):
            continue
        remote_path = file_entry.get("remote_path")
        local = file_entry.get("local", {})
        if not isinstance(remote_path, str) or not isinstance(local, dict):
            continue
        remapped = _remote_under_root(remote_path, remote_root)
        indexed[remote_path] = {
            "remote_path": remapped,
            "size": int(local["size"]),
            "sha256": str(local["sha256"]),
        }
    return indexed


def build_manifest_lines(
    deploy_plan: dict[str, Any],
    *,
    profile_id: str = INTERNAL_SPEAKER_SAFE.profile_id,
    remote_root: str = DEFAULT_REMOTE_ROOT,
) -> list[str]:
    """Return native-init line-format manifest lines."""

    expected_order = list(INTERNAL_SPEAKER_SAFE.acdb_set_order)
    replay_entries = deploy_plan.get("replay_entries", [])
    if len(replay_entries) != len(expected_order):
        raise ValueError(f"expected {len(expected_order)} replay entries, got {len(replay_entries)}")

    files = _file_index(deploy_plan, remote_root)
    lines = [
        "# A90 native-init audio SET-cal private manifest v1",
        f"# install_path {DEFAULT_SETCAL_MANIFEST_PATH}",
        "version 1",
        f"profile {profile_id}",
        f"entry_count {len(expected_order)}",
    ]
    for index, entry in enumerate(replay_entries):
        if not isinstance(entry, dict):
            raise ValueError(f"entry {index} is not an object")
        sequence = int(entry["sequence"])
        cal_type = int(entry["cal_type"])
        role = str(entry["role"])
        dmabuf_expected = bool(entry["dmabuf_expected"])
        if sequence != index:
            raise ValueError(f"entry {index} sequence mismatch: {sequence}")
        if cal_type != expected_order[index]:
            raise ValueError(f"entry {index} cal_type mismatch: {cal_type} != {expected_order[index]}")
        if cal_type in INTERNAL_SPEAKER_SAFE.forbidden_stale_cal_types:
            raise ValueError(f"entry {index} contains forbidden stale cal_type {cal_type}")

        arg_remote = str(entry["arg_remote"])
        arg_file = files[arg_remote]
        payload_remote = entry.get("payload_remote")
        if dmabuf_expected:
            if not isinstance(payload_remote, str):
                raise ValueError(f"entry {index} needs payload_remote")
            payload_file = files[payload_remote]
            payload_path = payload_file["remote_path"]
            payload_size = payload_file["size"]
            payload_sha = payload_file["sha256"]
        else:
            if payload_remote is not None:
                raise ValueError(f"entry {index} unexpectedly has payload_remote")
            payload_path = "-"
            payload_size = 0
            payload_sha = "-"

        lines.append(
            "entry "
            f"{sequence} {cal_type} {role} {1 if dmabuf_expected else 0} "
            f"{arg_file['remote_path']} {arg_file['size']} {arg_file['sha256']} "
            f"{payload_path} {payload_size} {payload_sha}"
        )
    return lines


def load_deploy_plan(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deploy-plan", type=Path, default=DEFAULT_DEPLOY_PLAN)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--remote-root", default=DEFAULT_REMOTE_ROOT)
    args = parser.parse_args()

    manifest = "\n".join(
        build_manifest_lines(load_deploy_plan(args.deploy_plan), remote_root=args.remote_root)
    ) + "\n"
    if args.output is None:
        print(manifest, end="")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(manifest, encoding="utf-8")
        print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
