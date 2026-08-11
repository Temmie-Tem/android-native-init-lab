#!/usr/bin/env python3
"""Reparse the exact P3.15 USB sidecar as the P3.16 positive control."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any


SCHEMA = "s22plus_fyg8_p316_sidecar_positive_control_v1"
VERDICT = "PASS_P316_USB_SIDECAR_POSITIVE_CONTROL_HOST_ONLY"
RUN_ROOT = Path(
    "workspace/private/runs/device-action-f1-live-v2/"
    "p315-ready1-prepared-20260811-1/p300-usb-trace"
)
EXPECTED = {
    "result.json": (2481, "a075c7014e9d0524fd0b7f18fe14a263639ad27ced386a4801e4c9856caf19fa"),
    "udev.log": (45396, "f539150e56f5e33332131f0c9a2a14354691d41869a2c3deb54dbba6f8a60c9a"),
    "kernel.log": (1438, "26fab51e531789d692ae3179944e2f553758fb033b5409d3ccaa6b81841c6a9c"),
    "armed.json": (734, "e39c758db42de5d345c742b6452c66fa0f2fab584b5c2c236f5f1d21a4d0ec7a"),
}
ANDROID_PRODUCT = "4e8/6860/504"
DOWNLOAD_PRODUCT = "4e8/685d/100"


class SidecarControlError(ValueError):
    pass


def _stable(path: Path, expected: tuple[int, str], label: str) -> bytes:
    try:
        before = path.stat(follow_symlinks=False)
        if path.is_symlink() or not path.is_file() or before.st_size != expected[0]:
            raise SidecarControlError(f"{label} is not the exact regular file")
        payload = path.read_bytes()
        after = path.stat(follow_symlinks=False)
    except OSError as exc:
        raise SidecarControlError(f"{label} is unavailable") from exc
    if (
        len(payload) != before.st_size
        or hashlib.sha256(payload).hexdigest() != expected[1]
        or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
        != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    ):
        raise SidecarControlError(f"{label} changed or differs")
    return payload


def _event_counts(payload: bytes) -> Counter[tuple[str, str]]:
    try:
        text = payload.decode("utf-8")
    except UnicodeError as exc:
        raise SidecarControlError("P3.15 udev capture is not UTF-8") from exc
    blocks: list[list[str]] = []
    current: list[str] = []
    for raw in text.splitlines():
        line = raw.split(" source=udev ", 1)[1] if " source=udev " in raw else raw
        if not line:
            if current:
                blocks.append(current)
                current = []
        else:
            current.append(line)
    if current:
        blocks.append(current)
    counts: Counter[tuple[str, str]] = Counter()
    for block in blocks:
        fields = {
            line.split("=", 1)[0]: line.split("=", 1)[1]
            for line in block
            if "=" in line and not line.startswith(("KERNEL[", "UDEV  ["))
        }
        action = fields.get("ACTION")
        product = fields.get("PRODUCT")
        if fields.get("DEVTYPE") == "usb_device" and action and product:
            counts[(action, product)] += 1
    return counts


def audit(root: Path | None = None) -> dict[str, Any]:
    root = (root or Path(__file__).resolve().parents[5]).resolve()
    base = root / RUN_ROOT
    payloads = {
        name: _stable(base / name, expected, f"P3.15 sidecar {name}")
        for name, expected in EXPECTED.items()
    }
    try:
        result = json.loads(payloads["result.json"].decode("ascii"))
        armed = json.loads(payloads["armed.json"].decode("ascii"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise SidecarControlError("P3.15 sidecar JSON is invalid") from exc
    sources = result.get("sources", {})
    if (
        result.get("schema") != "device_action_usb_trace_sidecar_v1"
        or result.get("phase") != "complete"
        or result.get("device_actions") is not False
        or result.get("non_authoritative") is not True
        or result.get("opens_candidate_acm") is not False
        or result.get("stop_reason") != "signal:SIGTERM"
        or set(sources) != {"kernel", "udev"}
        or any(
            source.get("alive_at_arm") is not True
            or source.get("alive_before_stop") is not True
            or source.get("truncated") is not False
            or source.get("error_type") is not None
            for source in sources.values()
        )
        or armed.get("phase") != "armed"
    ):
        raise SidecarControlError("P3.15 sidecar integrity contract differs")
    counts = _event_counts(payloads["udev.log"])
    required = {
        ("remove", ANDROID_PRODUCT): 2,
        ("add", DOWNLOAD_PRODUCT): 2,
        ("remove", DOWNLOAD_PRODUCT): 2,
    }
    if any(counts.get(key) != value for key, value in required.items()):
        raise SidecarControlError("P3.15 sidecar positive-control events differ")
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "source_run": "P3.15",
        "capture_integrity_clean": True,
        "android_departure_observed": True,
        "download_arrival_observed": True,
        "download_departure_observed": True,
        "kernel_capture_nonempty": len(payloads["kernel.log"]) > 0,
        "udev_capture_nonempty": len(payloads["udev.log"]) > 0,
        "exact_receipts": {
            name: {"size": expected[0], "sha256": expected[1]}
            for name, expected in EXPECTED.items()
        },
        "device_contact": False,
        "verified": True,
    }


def main() -> int:
    try:
        result = audit()
    except (OSError, SidecarControlError, ValueError) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
