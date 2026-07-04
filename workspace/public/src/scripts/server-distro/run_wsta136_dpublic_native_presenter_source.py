#!/usr/bin/env python3
"""WSTA136 host-only source proof for the native D-public HUD presenter.

WSTA135 proved the Debian side writes only a bounded HUD intent.  WSTA136 adds
the native/root-owned consumer side to native-init source: it validates that the
new command reads the intent file, rejects stale/forbidden/unknown content, and
uses native KMS for presentation without giving Debian direct DRM ownership.

No device action, boot flash, native reboot, Wi-Fi association, DHCP, public
tunnel, packet-filter mutation, userdata write, DRM operation, KMS operation, or
switch-root is performed by this proof.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import prepare_wsta3_sta_rootfs as wsta3  # noqa: E402


REPO_ROOT = wsta3.REPO_ROOT
DEFAULT_RUN_BASE = wsta3.DEFAULT_RUN_BASE
PASS_DECISION = "wsta136-dpublic-native-presenter-source-pass"
RESULT_NAME = "wsta136_dpublic_native_presenter_source.json"
NATIVE_SOURCE = REPO_ROOT / "workspace/public/src/native-init/a90_server_distro.c"
NATIVE_HEADER = REPO_ROOT / "workspace/public/src/native-init/a90_server_distro.h"
DISPATCH_SOURCE = REPO_ROOT / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"
BUILDER_SOURCE = (
    REPO_ROOT
    / "workspace/public/src/scripts/revalidation/build_native_init_boot_v3398_dpublic_hud_presenter.py"
)


def rel(path: Path) -> str:
    return wsta3.rel(path)


def utc_stamp() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def safety() -> dict[str, Any]:
    return {
        "device_action": False,
        "boot_flash": False,
        "native_reboot": False,
        "wifi_connect": False,
        "dhcp": False,
        "public_tunnel": False,
        "public_smoke": False,
        "packet_filter_mutation": False,
        "userdata_touch": False,
        "switch_root": False,
        "drm_open": False,
        "kms_setcrtc": False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def source_contract() -> dict[str, Any]:
    source = NATIVE_SOURCE.read_text(encoding="utf-8")
    header = NATIVE_HEADER.read_text(encoding="utf-8")
    dispatch = DISPATCH_SOURCE.read_text(encoding="utf-8")
    builder = BUILDER_SOURCE.read_text(encoding="utf-8")
    return {
        "native_source": rel(NATIVE_SOURCE),
        "native_header": rel(NATIVE_HEADER),
        "dispatch_source": rel(DISPATCH_SOURCE),
        "builder_source": rel(BUILDER_SOURCE),
        "command_default_intent": 'A90_DPUBLIC_HUD_DEFAULT_INTENT "/run/a90-dpublic/hud-intent.json"' in source,
        "schema_literal": 'A90_DPUBLIC_HUD_SCHEMA "a90-dpublic-hud-intent-v1"' in source,
        "max_intent_bytes_4096": "A90_DPUBLIC_HUD_MAX_INTENT_BYTES 4096U" in source,
        "stale_after_2000ms": "A90_DPUBLIC_HUD_STALE_AFTER_MS 2000ULL" in source,
        "parser_present": "dpublic_hud_parse_intent" in source,
        "regular_file_no_symlink_open": "O_NOFOLLOW" in source and "S_ISREG" in source,
        "forbidden_fields_rejected": "intent.reject=forbidden-key" in source
        and "policy.forbidden_fields=reject" in source,
        "unknown_fields_rejected": "intent.reject=unknown-key" in source
        and "policy.unknown_fields=reject" in source,
        "stale_rejected": "intent.reject=stale" in source
        and "intent.reject=clock-domain" in source,
        "native_owner_marker": "presenter.owner=native-init-root" in source,
        "debian_direct_kms_denied_marker": "presenter.debian_direct_kms=0" in source,
        "native_kms_present": "a90_kms_begin_frame" in source
        and 'a90_kms_present("dpublic-hud-presenter"' in source,
        "no_shell_helpers_in_presenter_source": "system(" not in source and "popen(" not in source,
        "command_exported_in_header": "a90_server_distro_dpublic_hud_presenter_cmd" in header,
        "command_registered": '"dpublic-hud-presenter"' in dispatch
        and "handle_dpublic_hud_presenter" in dispatch
        and "CMD_DISPLAY" in dispatch,
        "v3398_builder_present": "v3398-dpublic-hud-presenter" in builder
        and "A90WSTA136" in builder
        and "dpublic-hud-presenter" in builder,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def evaluate(contract: dict[str, Any]) -> dict[str, Any]:
    bool_items = {
        key: value
        for key, value in contract.items()
        if isinstance(value, bool) and key not in {"public_url_value_logged"}
    }
    failed = [key for key, value in bool_items.items() if not value]
    return {
        "passed": not failed,
        "failed": failed,
        "checked": sorted(bool_items),
    }


def collect(args: argparse.Namespace) -> dict[str, Any]:
    run_id = args.run_id or f"wsta136-dpublic-native-presenter-source-{utc_stamp()}"
    run_dir = args.run_dir or (DEFAULT_RUN_BASE / run_id)
    if not run_dir.is_absolute():
        run_dir = REPO_ROOT / run_dir
    contract = source_contract()
    assessment = evaluate(contract)
    result = {
        "schema": "a90-wsta136-dpublic-native-presenter-source-v1",
        "decision": PASS_DECISION if assessment["passed"] else "wsta136-dpublic-native-presenter-source-fail",
        "ok": assessment["passed"],
        "run_id": run_id,
        "run_dir": rel(run_dir),
        "timestamp_utc": utc_stamp(),
        "safety": safety(),
        "contract": contract,
        "assessment": assessment,
        "next": "source-build V3398, then live-gate with hot-reload or checked boot flash",
    }
    write_json(run_dir / RESULT_NAME, result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    parser.add_argument("--run-dir", type=Path)
    args = parser.parse_args(argv)
    result = collect(args)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
