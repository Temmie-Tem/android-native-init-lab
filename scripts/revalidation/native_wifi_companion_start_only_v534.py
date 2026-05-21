#!/usr/bin/env python3
"""V534 bounded native Wi-Fi companion start-only proof.

This is the v66-helper successor to V527/V528. It keeps the same bounded
contract: QRTR/rmt/tftp/pd-mapper/CNSS companion services only, no
service-manager, no Wi-Fi HAL, no scan/connect/link-up, no DHCP, and no
external ping. V534 also requires the V533 rmt_storage-only window proof before
allowing the broader companion replay.
"""

from __future__ import annotations

import re
from dataclasses import asdict
from pathlib import Path
from typing import Any

import native_wifi_companion_start_only_v527 as base


DEFAULT_V533_MANIFEST = Path("tmp/wifi/v533-rmt-storage-start-only/manifest.json")

base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = Path("tmp/wifi/v534-companion-start-only")
base.DEFAULT_HELPER_SHA256 = "d64f389601783d8826f2821febc681c1b12e9bd7cd6a3e2fae9d77461331faa5"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v66"
base.PROOF_VERSION = "V534"
base.PROOF_SLUG = "v534-companion-start-only"
base.LIVE_HELPER_STEP_NAME = "v534-helper-run"
base.APPROVAL_PHRASE = (
    "approve v534 companion start-only proof only; "
    "no service-manager, no Wi-Fi HAL start, no scan/connect/link-up and no external ping"
)

_orig_build_checks = base.build_checks
_orig_build_manifest = base.build_manifest
_orig_render_summary = base.render_summary
_orig_run_live = base.run_live


SECTION_RE = re.compile(r"^A90_EXECNS_(STDOUT|STDERR)_BEGIN\n(.*?)^A90_EXECNS_\1_END .*$", re.MULTILINE | re.DOTALL)


def _section(text: str, name: str) -> str:
    for match in SECTION_RE.finditer(text):
        if match.group(1) == name:
            return match.group(2).strip()
    return ""


def _tail(text: str, limit: int) -> list[str]:
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    return lines[-limit:]


def _focus_keys(keys: dict[str, str]) -> list[list[str]]:
    prefixes = (
        "wifi_companion_start.",
        "wifi_hal_composite_child.qrtr_ns.",
        "wifi_hal_composite_child.rmt_storage.",
        "wifi_hal_composite_child.tftp_server.",
        "wifi_hal_composite_child.pd_mapper.",
        "wifi_hal_composite_child.cnss_diag.",
        "wifi_hal_composite_child.cnss_daemon.",
    )
    rows: list[list[str]] = []
    for key in sorted(keys):
        if key.startswith(prefixes):
            rows.append([key, keys[key]])
    return rows


def _v533_manifest() -> dict[str, Any]:
    manifest = base.load_manifest(DEFAULT_V533_MANIFEST)
    if not manifest.get("exists"):
        manifest["path"] = str(base.repo_path(DEFAULT_V533_MANIFEST))
    return manifest


def build_checks(args: base.argparse.Namespace,
                 steps: list[dict[str, Any]],
                 v490: dict[str, Any],
                 v525: dict[str, Any]) -> list[base.Check]:
    checks = _orig_build_checks(args, steps, v490, v525)
    if args.command == "plan":
        return checks
    v533 = _v533_manifest()
    base.add_check(
        checks,
        "v533-rmt-storage-window-proof",
        "pass" if v533.get("decision") == "v533-rmt-storage-window-pass" and v533.get("pass") is True else "blocked",
        "blocker",
        f"decision={v533.get('decision')} pass={v533.get('pass')} live={bool(v533.get('live_result'))}",
        [str(v533.get("path"))],
        "run approved V533 rmt_storage start-only proof before broader companion replay",
    )
    return checks


def run_live(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    result = _orig_run_live(args, store)
    live_text = base.step_payload([result["live"]], base.LIVE_HELPER_STEP_NAME)
    stdout_section = _section(live_text, "STDOUT")
    stderr_section = _section(live_text, "STDERR")
    base.write_capture(store, "helper-stdout-section", stdout_section or "<empty>")
    base.write_capture(store, "helper-stderr-section", stderr_section or "<empty>")
    result["focus_keys"] = _focus_keys(result.get("keys") or {})
    result["helper_stdout_tail"] = _tail(stdout_section, 80)
    result["helper_stderr_tail"] = _tail(stderr_section, 80)
    return result


def render_summary(manifest: dict[str, Any]) -> str:
    text = _orig_render_summary(manifest)
    live = manifest.get("live_result") or {}
    focus_rows = live.get("focus_keys") or []
    stdout_tail = "\n".join(live.get("helper_stdout_tail") or [])
    stderr_tail = "\n".join(live.get("helper_stderr_tail") or [])
    extra = "\n".join([
        "## Companion Focus Keys",
        "",
        base.markdown_table(["key", "value"], focus_rows[:120]) if focus_rows else "- none",
        "",
        "## Helper STDERR Tail",
        "",
        "```text",
        stderr_tail or "<empty>",
        "```",
        "",
        "## Helper STDOUT Tail",
        "",
        "```text",
        stdout_tail or "<empty>",
        "```",
        "",
    ])
    return text.replace("## Evidence\n\n", extra + "## Evidence\n\n")


def build_manifest(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    manifest = _orig_build_manifest(args, store)
    v533 = _v533_manifest()
    manifest["v533_manifest"] = {
        "exists": v533.get("exists"),
        "path": v533.get("path"),
        "decision": v533.get("decision"),
        "pass": v533.get("pass"),
    }
    manifest["checks"] = [asdict(check) if hasattr(check, "name") else check for check in manifest["checks"]]
    return manifest


base.build_checks = build_checks
base.run_live = run_live
base.render_summary = render_summary
base.build_manifest = build_manifest


if __name__ == "__main__":
    raise SystemExit(base.main())
