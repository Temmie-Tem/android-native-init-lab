#!/usr/bin/env python3
"""V761 host-only source download/staging handoff packet.

V760 provides a verifier, but the official Samsung source download still needs
manual browser interaction. V761 generates an operator handoff packet and a
local shell helper that never stores secrets, never touches the device, and only
copies a manually downloaded OSRC archive into the ignored kernel_build staging
area before rerunning V760.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shlex
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v761-source-download-handoff")
DEFAULT_V759_MANIFEST = Path("tmp/wifi/v759-source-acquisition/manifest.json")
DEFAULT_V760_MANIFEST = Path("tmp/wifi/v760-source-staging/manifest.json")
EXPECTED_FILENAME = "SM-A908N_KOR_12_Opensource.zip"
OSRC_URL = "https://opensource.samsung.com/uploadSearch?searchValue=A908NKSU5EWA3"


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    severity: str
    detail: str
    evidence: str
    next_step: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v759-manifest", type=Path, default=DEFAULT_V759_MANIFEST)
    parser.add_argument("--v760-manifest", type=Path, default=DEFAULT_V760_MANIFEST)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"present": False, "path": str(resolved)}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"present": True, "path": str(resolved), "decision": "invalid-json", "pass": False, "error": str(exc)}
    if isinstance(data, dict):
        data["present"] = True
        data["path"] = str(resolved)
        return data
    return {"present": True, "path": str(resolved), "decision": "invalid-json-type", "pass": False}


def shell_quote(value: str | Path) -> str:
    return shlex.quote(str(value))


def build_shell_script(repo_root: Path) -> str:
    return f"""#!/usr/bin/env bash
set -euo pipefail
umask 077

REPO_ROOT={shell_quote(repo_root)}
EXPECTED={shell_quote(EXPECTED_FILENAME)}
OSRC_URL={shell_quote(OSRC_URL)}

cd "$REPO_ROOT"
mkdir -p kernel_build/source kernel_build/downloads

cat <<MSG
V761 source download handoff

1. Open the Samsung OSRC URL:
   $OSRC_URL
2. Complete the browser human-verification flow.
3. Download: $EXPECTED
4. Put it in one of:
   - $REPO_ROOT/kernel_build/$EXPECTED
   - $REPO_ROOT/kernel_build/downloads/$EXPECTED
   - $HOME/Downloads/$EXPECTED

Set V761_OPEN_BROWSER=1 when running this script if you want it to call xdg-open.
MSG

if [[ "${{V761_OPEN_BROWSER:-0}}" == "1" ]]; then
  if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$OSRC_URL" >/dev/null 2>&1 || true
  else
    echo "xdg-open not found; open the URL manually."
  fi
fi

target="kernel_build/$EXPECTED"
candidates=(
  "$target"
  "kernel_build/downloads/$EXPECTED"
  "$HOME/Downloads/$EXPECTED"
  "$REPO_ROOT/$EXPECTED"
)
for candidate in "${{candidates[@]}}"; do
  if [[ -f "$candidate" ]]; then
    if [[ "$candidate" != "$target" ]]; then
      cp -n "$candidate" "$target"
    fi
    break
  fi
done

python3 scripts/revalidation/native_wifi_source_staging_v760.py run
"""


def build_handoff_md(manifest: dict[str, Any]) -> str:
    checks = manifest.get("checks") or []
    packet = manifest.get("packet") or {}
    return "\n".join([
        "# V761 Source Download Handoff",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        "## Command",
        "",
        "```sh",
        str(packet.get("operator_command", "")),
        "```",
        "",
        "Optional browser launch:",
        "",
        "```sh",
        "V761_OPEN_BROWSER=1 " + str(packet.get("operator_command", "")),
        "```",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "evidence"], [
            [check["name"], check["status"], check["severity"], check["detail"], check["evidence"]]
            for check in checks
        ]),
        "",
        "## Scope",
        "",
        "- Opens no browser unless the operator sets `V761_OPEN_BROWSER=1`.",
        "- Copies only a manually downloaded official archive into ignored `kernel_build/`.",
        "- Runs V760 source staging verification after the copy attempt.",
        "- Does not patch source, build a kernel, flash a boot image, touch the device, or use Wi-Fi credentials.",
    ])


def add_check(
    checks: list[Check],
    name: str,
    status: str,
    severity: str,
    detail: str,
    evidence: str,
    next_step: str,
) -> None:
    checks.append(Check(name, status, severity, detail, evidence, next_step))


def build_checks(v759: dict[str, Any], v760: dict[str, Any]) -> list[Check]:
    checks: list[Check] = []
    add_check(
        checks,
        "v759-source-identified",
        "pass" if v759.get("present") and v759.get("decision") == "v759-official-source-identified-manual-download-gated" and v759.get("pass") is True else "blocked",
        "blocker",
        f"decision={v759.get('decision')} pass={v759.get('pass')}",
        str(v759.get("path", "")),
        "complete V759 source acquisition before handoff",
    )
    add_check(
        checks,
        "v760-staging-verifier",
        "pass" if v760.get("present") and v760.get("decision") in {"v760-source-stage-missing", "v760-source-archive-present-extract-required", "v760-source-targets-verified"} and v760.get("pass") is True else "blocked",
        "blocker",
        f"decision={v760.get('decision')} pass={v760.get('pass')}",
        str(v760.get("path", "")),
        "complete V760 verifier before handoff",
    )
    add_check(
        checks,
        "source-stage-current",
        "review" if v760.get("decision") == "v760-source-stage-missing" else "pass",
        "finding",
        f"decision={v760.get('decision')}",
        str(v760.get("path", "")),
        "download and stage official source if current state is missing",
    )
    return checks


def blocking(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def decide(command: str, checks: list[Check], v760: dict[str, Any]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v761-source-download-handoff-plan-ready",
            True,
            "plan-only; no browser, copy, or device command executed",
            "run V761 to generate operator handoff packet",
        )
    blockers = blocking(checks)
    if blockers:
        return (
            "v761-source-download-handoff-blocked",
            False,
            "blocked by " + ", ".join(blockers),
            "repair prerequisites before generating handoff",
        )
    if v760.get("decision") == "v760-source-targets-verified":
        return (
            "v761-source-download-handoff-not-needed",
            True,
            "source targets are already verified",
            "proceed to V761/V762 kernel instrumentation planning instead of handoff",
        )
    return (
        "v761-source-download-handoff-ready",
        True,
        "operator handoff packet generated for manual OSRC download and V760 rerun",
        "run generated handoff script after completing the Samsung OSRC browser download",
    )


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v759 = load_json(args.v759_manifest)
    v760 = load_json(args.v760_manifest)
    checks = build_checks(v759, v760)
    decision, ok, reason, next_step = decide(args.command, checks, v760)
    repo_root = repo_path(".")
    script_path = store.run_dir / "run-v761-source-download-handoff.sh"
    handoff_path = store.run_dir / "handoff.md"
    operator_command = f"bash {shell_quote(script_path)}"
    manifest: dict[str, Any] = {
        "cycle": "v761",
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": ok,
        "reason": reason,
        "next_step": next_step,
        "checks": [asdict(check) for check in checks],
        "packet": {
            "osrc_url": OSRC_URL,
            "expected_filename": EXPECTED_FILENAME,
            "operator_command": operator_command,
            "handoff_path": str(handoff_path),
            "script_path": str(script_path),
            "stage_paths": [
                "kernel_build/SM-A908N_KOR_12_Opensource.zip",
                "kernel_build/downloads/SM-A908N_KOR_12_Opensource.zip",
                "kernel_build/source/SM-A908N_KOR_12_Opensource/",
            ],
            "post_stage_verifier": "python3 scripts/revalidation/native_wifi_source_staging_v760.py run",
        },
        "host": collect_host_metadata(),
        "browser_open_executed": False,
        "file_copy_executed": False,
        "device_commands_executed": False,
        "device_mutations": False,
        "boot_image_write_executed": False,
        "partition_write_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", build_handoff_md(manifest))
    write_private_text(script_path, build_shell_script(repo_root))
    os.chmod(script_path, 0o700)
    write_private_text(handoff_path, build_handoff_md(manifest))
    return manifest


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"operator_command: {manifest['packet']['operator_command']}")
    print(f"browser_open_executed: {manifest['browser_open_executed']}")
    print(f"file_copy_executed: {manifest['file_copy_executed']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
