#!/usr/bin/env python3
"""Generate a safe Android boot handoff preflight for v297 property capture."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import shlex
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v299-android-capture-handoff")
DEFAULT_NATIVE_IMAGE = Path("stage3/boot_linux_v261.img")
DEFAULT_V297_MANIFEST = Path("tmp/wifi/v297-android-property-capture-preflight/manifest.json")
DEFAULT_V298_MANIFEST = Path("tmp/wifi/v298-property-baseline-compare-waiting/manifest.json")
ANDROID_BOOT_GLOBS = (
    "backups/baseline_*/boot.img",
    "backups/*stock*boot*.img",
    "backups/*android*boot*.img",
)
BOOT_BLOCK_SIZE = 4096
NATIVE_EXPECT_VERSION = "A90 Linux init 0.9.60 (v261)"


@dataclass
class ImageInfo:
    path: str
    present: bool
    size: int
    aligned_4k: bool
    sha256: str
    android_magic: bool
    native_marker: bool
    role_hint: str


@dataclass
class CommandCapture:
    name: str
    command: str
    ok: bool
    rc: int | None
    duration_sec: float
    file: str
    error: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--native-image", type=Path, default=DEFAULT_NATIVE_IMAGE)
    parser.add_argument("--android-boot-image", action="append", type=Path, default=[])
    parser.add_argument("--v297-manifest", type=Path, default=DEFAULT_V297_MANIFEST)
    parser.add_argument("--v298-manifest", type=Path, default=DEFAULT_V298_MANIFEST)
    parser.add_argument("--timeout", type=int, default=15)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("preflight")
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_contains(path: Path, needle: bytes) -> bool:
    if not path.exists():
        return False
    overlap = max(len(needle) - 1, 0)
    previous = b""
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            data = previous + chunk
            if needle in data:
                return True
            previous = data[-overlap:] if overlap else b""
    return False


def inspect_image(path: Path, role_hint: str) -> ImageInfo:
    resolved = repo_path(path)
    if not resolved.exists():
        return ImageInfo(str(resolved), False, 0, False, "", False, False, role_hint)
    size = resolved.stat().st_size
    header = resolved.read_bytes()[:8]
    return ImageInfo(
        path=str(resolved),
        present=True,
        size=size,
        aligned_4k=size > 0 and size % BOOT_BLOCK_SIZE == 0,
        sha256=sha256_file(resolved),
        android_magic=header == b"ANDROID!",
        native_marker=file_contains(resolved, NATIVE_EXPECT_VERSION.encode()),
        role_hint=role_hint,
    )


def discover_android_images(extra: list[Path]) -> list[Path]:
    paths: list[Path] = []
    seen: set[Path] = set()
    for item in extra:
        resolved = repo_path(item)
        if resolved not in seen:
            seen.add(resolved)
            paths.append(item)
    for pattern in ANDROID_BOOT_GLOBS:
        for path in sorted(repo_path(".").glob(pattern)):
            if path not in seen:
                seen.add(path)
                paths.append(path)
    return paths


def load_manifest(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"present": False, "path": str(resolved)}
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    payload["present"] = True
    payload["path"] = str(resolved)
    return payload


def display_command(command: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in command)


def run_process(command: list[str], timeout: int) -> tuple[int | None, str, str, float]:
    started = time.monotonic()
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
        return result.returncode, result.stdout, "", time.monotonic() - started
    except Exception as exc:  # noqa: BLE001 - preflight preserves failure detail
        return None, "", str(exc), time.monotonic() - started


def write_capture(store: EvidenceStore, name: str, command: list[str], text: str, error: str, rc: int | None) -> CommandCapture:
    body = "\n".join([f"$ {display_command(command)}", (text if text else error).rstrip(), f"rc={rc}", ""])
    path = store.write_text(f"commands/{name}.txt", body)
    return CommandCapture(name, display_command(command), rc == 0, rc, 0.0, str(path.relative_to(store.run_dir)), error)


def capture_command(store: EvidenceStore, name: str, command: list[str], timeout: int) -> CommandCapture:
    rc, text, error, duration = run_process(command, timeout)
    capture = write_capture(store, name, command, text, error, rc)
    capture.duration_sec = duration
    return capture


def native_control_captures(store: EvidenceStore, timeout: int) -> list[CommandCapture]:
    return [
        capture_command(store, "native-version", ["python3", "scripts/revalidation/a90ctl.py", "--json", "version"], timeout),
        capture_command(store, "native-status", ["python3", "scripts/revalidation/a90ctl.py", "status"], timeout),
    ]


def choose_android_candidate(images: list[ImageInfo]) -> ImageInfo | None:
    valid = [
        image for image in images
        if image.present and image.aligned_4k and image.android_magic and not image.native_marker
    ]
    if not valid:
        return None
    valid.sort(key=lambda image: (image.size != 64 * 1024 * 1024, image.path))
    return valid[0]


def command_plan(android_image: ImageInfo | None, native_image: ImageInfo) -> list[str]:
    android_path = android_image.path if android_image else "<ANDROID_BOOT_IMAGE>"
    native_path = native_image.path if native_image.present else str(repo_path(DEFAULT_NATIVE_IMAGE))
    android_size = android_image.size if android_image else 0
    count = android_size // BOOT_BLOCK_SIZE if android_size else "<COUNT>"
    return [
        "python3 scripts/revalidation/a90ctl.py --json version",
        "python3 scripts/revalidation/a90ctl.py status",
        "# operator-approved transition to TWRP/recovery is required here",
        "printf '\\nhide\\nrecovery\\n' | nc -w 5 127.0.0.1 54321 || true",
        "adb devices -l  # wait for recovery/TWRP state",
        f"adb push {shlex.quote(android_path)} /tmp/android_boot.img",
        "adb shell 'sha256sum /tmp/android_boot.img 2>/dev/null || toybox sha256sum /tmp/android_boot.img'",
        "adb shell 'dd if=/tmp/android_boot.img of=/dev/block/by-name/boot bs=4M conv=fsync && sync'",
        f"adb shell 'dd if=/dev/block/by-name/boot bs=4096 count={count} 2>/dev/null | sha256sum 2>/dev/null || dd if=/dev/block/by-name/boot bs=4096 count={count} 2>/dev/null | toybox sha256sum'",
        "adb shell 'twrp reboot'",
        "adb wait-for-device",
        "python3 scripts/revalidation/wifi_android_property_capture.py --out-dir tmp/wifi/v297-android-property-capture-android run",
        "python3 scripts/revalidation/wifi_property_baseline_compare.py --out-dir tmp/wifi/v298-property-baseline-compare-android --v297-manifest tmp/wifi/v297-android-property-capture-android/manifest.json run",
        "# rollback to native init after capture",
        "adb reboot recovery",
        f"python3 scripts/revalidation/native_init_flash.py {shlex.quote(native_path)} --expect-version 'A90 Linux init 0.9.60 (v261)' --verify-protocol auto",
    ]


def decide(native_image: ImageInfo,
           android_candidate: ImageInfo | None,
           v297: dict[str, Any],
           v298: dict[str, Any],
           native_captures: list[CommandCapture]) -> tuple[str, bool, str]:
    if not native_image.present or not native_image.native_marker:
        return "android-capture-handoff-missing-native-rollback", False, "native rollback image is missing or does not contain expected version"
    if android_candidate is None:
        return "android-capture-handoff-missing-android-boot", False, "no local Android boot candidate passed preflight checks"
    if native_captures and not all(capture.ok for capture in native_captures):
        return "android-capture-handoff-native-control-unverified", False, "native bridge control did not pass read-only version/status"
    if v297.get("decision") not in {"android-property-capture-waiting-for-android", "android-property-capture-pass"}:
        return "android-capture-handoff-ready-needs-operator", True, f"v297 state is {v297.get('decision', 'missing')}; operator review required"
    if v298.get("decision") not in {"property-baseline-compare-waiting-for-android", "property-baseline-compare-ready"}:
        return "android-capture-handoff-ready-needs-operator", True, f"v298 state is {v298.get('decision', 'missing')}; operator review required"
    return "android-capture-handoff-ready-needs-operator", True, "local images and native control are ready; boot transition still requires operator approval"


def build_manifest(args: argparse.Namespace, store: EvidenceStore, live: bool) -> dict[str, Any]:
    native_image = inspect_image(args.native_image, "native-rollback")
    android_images = [inspect_image(path, "android-candidate") for path in discover_android_images(args.android_boot_image)]
    android_candidate = choose_android_candidate(android_images)
    v297 = load_manifest(args.v297_manifest)
    v298 = load_manifest(args.v298_manifest)
    captures = native_control_captures(store, args.timeout) if live else []
    decision, pass_ok, reason = decide(native_image, android_candidate, v297, v298, captures)
    commands = command_plan(android_candidate, native_image)
    return {
        "generated_at": now_iso(),
        "decision": "android-capture-handoff-plan-ready" if not live else decision,
        "pass": True if not live else pass_ok,
        "reason": "handoff command plan generated; no device mutation performed" if not live else reason,
        "host": collect_host_metadata(),
        "native_image": asdict(native_image),
        "android_images": [asdict(image) for image in android_images],
        "recommended_android_boot_image": asdict(android_candidate) if android_candidate else None,
        "inputs": {
            "v297": {
                "path": v297.get("path"),
                "present": bool(v297.get("present")),
                "decision": v297.get("decision"),
            },
            "v298": {
                "path": v298.get("path"),
                "present": bool(v298.get("present")),
                "decision": v298.get("decision"),
            },
        },
        "native_captures": [asdict(capture) for capture in captures],
        "handoff_commands": commands,
        "guardrails": [
            "no reboot",
            "no recovery transition",
            "no boot partition write",
            "no Android boot image flashing",
            "no property mutation",
            "no service-manager/HAL/Wi-Fi daemon execution",
            "no Wi-Fi scan/connect/link-up/credential/DHCP/routing",
        ],
    }


def render_summary(manifest: dict[str, Any]) -> str:
    image_rows = []
    for image in manifest["android_images"]:
        image_rows.append([
            image["path"],
            str(image["present"]),
            str(image["size"]),
            str(image["android_magic"]),
            str(image["native_marker"]),
            image["sha256"][:16] if image["sha256"] else "",
        ])
    capture_rows = [
        [item["name"], "ok" if item["ok"] else "fail", str(item["rc"]), item["file"]]
        for item in manifest["native_captures"]
    ]
    command_lines = [f"{index}. `{command}`" for index, command in enumerate(manifest["handoff_commands"], start=1)]
    return "\n".join(
        [
            "# v299 Android Capture Handoff Preflight",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- pass: `{manifest['pass']}`",
            f"- decision: `{manifest['decision']}`",
            f"- reason: {manifest['reason']}",
            "",
            "## Native Rollback Image",
            "",
            markdown_table(
                ["path", "present", "size", "android magic", "native marker", "sha256 prefix"],
                [[
                    manifest["native_image"]["path"],
                    str(manifest["native_image"]["present"]),
                    str(manifest["native_image"]["size"]),
                    str(manifest["native_image"]["android_magic"]),
                    str(manifest["native_image"]["native_marker"]),
                    manifest["native_image"]["sha256"][:16] if manifest["native_image"]["sha256"] else "",
                ]],
            ),
            "",
            "## Android Boot Candidates",
            "",
            markdown_table(["path", "present", "size", "android magic", "native marker", "sha256 prefix"], image_rows if image_rows else [["-", "-", "-", "-", "-", "-"]]),
            "",
            "## Native Control Captures",
            "",
            markdown_table(["name", "status", "rc", "file"], capture_rows if capture_rows else [["not-run", "-", "-", "-"]]),
            "",
            "## Handoff Commands",
            "",
            *command_lines,
            "",
            "## Guardrails",
            "",
            *[f"- {item}" for item in manifest["guardrails"]],
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store, live=args.command == "preflight")
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    store.write_text("handoff-commands.md", "\n".join(f"{index}. `{command}`" for index, command in enumerate(manifest["handoff_commands"], start=1)) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"out_dir: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
