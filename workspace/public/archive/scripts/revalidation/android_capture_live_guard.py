#!/usr/bin/env python3
"""Host-only go/no-go guard for Android capture live handoff."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v304-android-capture-live-guard")
DEFAULT_V302_MANIFEST = Path("tmp/wifi/v302-android-capture-approval-packet/manifest.json")
DEFAULT_V303_MANIFEST = Path("tmp/wifi/v303-android-capture-postprocess-waiting/manifest.json")
EXPECTED_NATIVE_VERSION = "A90 Linux init 0.9.60 (v261)"
EXPECTED_V303_DECISION = "android-capture-postprocess-waiting-for-live"


@dataclass
class GuardCheck:
    name: str
    status: str
    severity: str
    detail: str


@dataclass
class CommandCapture:
    name: str
    command: str
    ok: bool
    rc: int | None
    duration_sec: float
    file: str
    text: str
    error: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v302-manifest", type=Path, default=DEFAULT_V302_MANIFEST)
    parser.add_argument("--v303-manifest", type=Path, default=DEFAULT_V303_MANIFEST)
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--allow-dirty-repo", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("run")
    return parser.parse_args()


def load_manifest(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"present": False, "path": str(resolved)}
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    payload["present"] = True
    payload["path"] = str(resolved)
    return payload


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
    except Exception as exc:  # noqa: BLE001 - guard evidence preserves failure detail
        return None, "", str(exc), time.monotonic() - started


def capture_command(store: EvidenceStore, name: str, command: list[str], timeout: int) -> CommandCapture:
    rc, text, error, duration = run_process(command, timeout)
    body = "\n".join(["$ " + " ".join(command), text.rstrip() if text else error.rstrip(), f"rc={rc}", ""])
    path = store.write_text(f"commands/{name}.txt", body)
    return CommandCapture(name, " ".join(command), rc == 0, rc, duration, str(path.relative_to(store.run_dir)), text[:8192], error)


def check_image(role: str, image: dict[str, Any]) -> GuardCheck:
    path_text = str(image.get("path") or "")
    expected_sha = str(image.get("sha256") or "")
    if not path_text or not expected_sha:
        return GuardCheck(f"{role}-image", "fail", "blocker", "image path or sha256 missing from v302")
    path = Path(path_text)
    if not path.exists():
        return GuardCheck(f"{role}-image", "fail", "blocker", f"missing: {path}")
    actual_sha = file_sha256(path)
    if actual_sha != expected_sha:
        return GuardCheck(f"{role}-image", "fail", "blocker", f"sha mismatch expected={expected_sha[:16]} actual={actual_sha[:16]}")
    size = path.stat().st_size
    expected_size = int(image.get("size") or 0)
    if expected_size and size != expected_size:
        return GuardCheck(f"{role}-image", "fail", "blocker", f"size mismatch expected={expected_size} actual={size}")
    return GuardCheck(f"{role}-image", "pass", "blocker", f"path={path} sha={actual_sha[:16]} size={size}")


def approval_checks(v302: dict[str, Any]) -> list[GuardCheck]:
    checks: list[GuardCheck] = []
    checks.append(GuardCheck(
        "v302-approval",
        "pass" if v302.get("present") and v302.get("decision") == "android-capture-approval-ready" and bool(v302.get("pass")) else "fail",
        "blocker",
        f"decision={v302.get('decision')} pass={v302.get('pass')}",
    ))
    target = next((item for item in v302.get("checks", []) if isinstance(item, dict) and item.get("name") == "v300-target-propagation"), None)
    checks.append(GuardCheck(
        "v300-target-propagation",
        "pass" if target and target.get("status") == "pass" else "fail",
        "blocker",
        str(target.get("detail") if target else "missing target propagation check"),
    ))
    live_command = str(v302.get("live_command") or "")
    required_flags = ["--allow-android-boot-flash", "--assume-yes", "--i-understand-native-rollback"]
    missing_flags = [flag for flag in required_flags if flag not in live_command]
    checks.append(GuardCheck(
        "live-command-flags",
        "pass" if live_command and not missing_flags else "fail",
        "blocker",
        "all approval flags present" if not missing_flags else "missing flags: " + ", ".join(missing_flags),
    ))
    if v302.get("recommended_android_boot_image"):
        checks.append(check_image("android-boot", v302["recommended_android_boot_image"]))
    else:
        checks.append(GuardCheck("android-boot-image", "fail", "blocker", "missing recommended Android boot image in v302"))
    if v302.get("native_rollback_image"):
        checks.append(check_image("native-rollback", v302["native_rollback_image"]))
    else:
        checks.append(GuardCheck("native-rollback-image", "fail", "blocker", "missing native rollback image in v302"))
    return checks


def postprocess_checks(v303: dict[str, Any]) -> list[GuardCheck]:
    return [GuardCheck(
        "v303-postprocess-state",
        "pass" if v303.get("present") and v303.get("decision") == EXPECTED_V303_DECISION and bool(v303.get("pass")) else "fail",
        "blocker",
        f"decision={v303.get('decision')} pass={v303.get('pass')}",
    )]


def native_checks(captures: list[CommandCapture]) -> list[GuardCheck]:
    version = next((capture for capture in captures if capture.name == "native-version"), None)
    status = next((capture for capture in captures if capture.name == "native-status"), None)
    version_ok = bool(version and version.ok and EXPECTED_NATIVE_VERSION in version.text)
    status_ok = bool(status and status.ok and "netservice: disabled" in status.text and "storage: backend=sd" in status.text)
    return [
        GuardCheck("native-version", "pass" if version_ok else "fail", "blocker", f"expected={EXPECTED_NATIVE_VERSION} ok={version_ok}"),
        GuardCheck("native-status", "pass" if status_ok else "fail", "blocker", f"netservice_disabled_and_sd_storage={status_ok}"),
    ]


def repo_check(allow_dirty: bool) -> GuardCheck:
    rc, text, error, _ = run_process(["git", "status", "--short"], 10)
    dirty = bool(text.strip()) if rc == 0 else True
    if dirty and not allow_dirty:
        return GuardCheck("repo-clean", "warn", "warning", "uncommitted changes exist; commit guard artifacts before live handoff")
    if dirty:
        return GuardCheck("repo-clean", "warn", "warning", "dirty repo allowed by flag")
    return GuardCheck("repo-clean", "pass", "warning", "clean")


def decide(checks: list[GuardCheck]) -> tuple[str, bool, str]:
    blockers = [check for check in checks if check.severity == "blocker" and check.status != "pass"]
    if blockers:
        return "android-capture-live-guard-blocked", False, "blocked checks: " + ", ".join(check.name for check in blockers)
    return "android-capture-live-guard-go", True, "all blocker checks passed; live handoff still requires explicit operator approval"


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [[item["name"], item["status"], item["severity"], item["detail"]] for item in manifest["checks"]]
    capture_rows = [[item["name"], "ok" if item["ok"] else "fail", str(item["rc"]), f"{item['duration_sec']:.3f}s", item["file"]] for item in manifest["captures"]]
    lines = [
        "# v304 Android Capture Live Guard",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- pass: `{manifest['pass']}`",
        f"- decision: `{manifest['decision']}`",
        f"- reason: {manifest['reason']}",
        "",
        "## Checks",
        "",
        markdown_table(["check", "status", "severity", "detail"], check_rows),
        "",
        "## Captures",
        "",
        markdown_table(["capture", "status", "rc", "duration", "file"], capture_rows),
        "",
        "## Live Command",
        "",
    ]
    if manifest.get("live_command"):
        lines.extend(["```bash", manifest["live_command"], "```", ""])
    else:
        lines.extend(["- unavailable until guard is GO", ""])
    lines.extend([
        "## Safety Boundary",
        "",
        "- This guard does not execute the live command.",
        "- The live command writes the boot partition and still requires explicit operator approval.",
        "- Wi-Fi scan/connect/link-up/credential/DHCP/routing remain blocked.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    v302 = load_manifest(args.v302_manifest)
    v303 = load_manifest(args.v303_manifest)
    captures = [
        capture_command(store, "native-version", ["python3", "scripts/revalidation/a90ctl.py", "--json", "version"], args.timeout),
        capture_command(store, "native-status", ["python3", "scripts/revalidation/a90ctl.py", "status"], args.timeout),
    ]
    checks = approval_checks(v302) + postprocess_checks(v303) + native_checks(captures) + [repo_check(args.allow_dirty_repo)]
    decision, pass_ok, reason = decide(checks)
    live_command = str(v302.get("live_command") or "") if pass_ok else ""
    manifest = {
        "generated_at": now_iso(),
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "host": collect_host_metadata(),
        "inputs": {
            "v302": {"path": v302.get("path"), "present": bool(v302.get("present")), "decision": v302.get("decision"), "pass": v302.get("pass")},
            "v303": {"path": v303.get("path"), "present": bool(v303.get("present")), "decision": v303.get("decision"), "pass": v303.get("pass")},
        },
        "checks": [asdict(check) for check in checks],
        "captures": [asdict(capture) for capture in captures],
        "live_command": live_command,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    if live_command:
        store.write_text("live-command.txt", live_command + "\n")
    print(f"decision: {decision}")
    print(f"pass: {pass_ok}")
    print(f"out_dir: {store.run_dir}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
