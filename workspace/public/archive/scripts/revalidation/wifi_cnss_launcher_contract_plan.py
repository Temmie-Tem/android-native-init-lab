#!/usr/bin/env python3
"""Build the v243 CNSS launcher contract without starting CNSS daemons."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import REPO_ROOT, collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v243-cnss-launcher-contract-plan")
DEFAULT_V242_MANIFEST = Path("tmp/wifi/v242-cnss-runtime-inventory-live2/manifest.json")
REQUIRED_V242_DECISION = "cnss-runtime-inventory-ready-for-launcher-contract-plan"

AID_MAP = {
    "root": 0,
    "system": 1000,
    "wifi": 1010,
    "sdcard_rw": 1015,
    "media_rw": 1023,
    "diag": 2002,
    "inet": 3003,
    "net_raw": 3004,
    "net_admin": 3005,
}

CAPABILITY_MAP = {
    "NET_ADMIN": "CAP_NET_ADMIN",
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v242-manifest", type=Path, default=DEFAULT_V242_MANIFEST)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    full_path = repo_path(path)
    if not full_path.exists():
        return {"missing": True, "path": str(full_path)}
    data = json.loads(full_path.read_text(encoding="utf-8"))
    data["_manifest_path"] = str(full_path)
    return data


def v242_ready(manifest: dict[str, Any]) -> bool:
    return bool(manifest.get("pass")) and manifest.get("decision") == REQUIRED_V242_DECISION


def service_by_name(v242: dict[str, Any], name: str) -> dict[str, Any]:
    for service in v242.get("runtime_requirements", {}).get("services", []):
        if service.get("name") == name:
            return service
    return {"name": name, "missing": True}


def aid_for(name: str) -> int | None:
    return AID_MAP.get(name)


def numeric_identity(service: dict[str, Any]) -> dict[str, Any]:
    user_name = service.get("user") or "system"
    group_names = list(service.get("groups") or [])
    primary_group = group_names[0] if group_names else user_name
    supplemental_groups = group_names[1:] if group_names else []
    missing_names = [
        name for name in [user_name, primary_group, *supplemental_groups]
        if aid_for(name) is None
    ]
    return {
        "user": {"name": user_name, "uid": aid_for(user_name)},
        "primary_group": {"name": primary_group, "gid": aid_for(primary_group)},
        "supplemental_groups": [
            {"name": name, "gid": aid_for(name)} for name in supplemental_groups
        ],
        "missing_aid_names": sorted(set(missing_names)),
    }


def capability_contract(service: dict[str, Any]) -> dict[str, Any]:
    requested = list(service.get("capabilities") or [])
    linux_caps = [CAPABILITY_MAP.get(name, f"CAP_{name}") for name in requested]
    return {
        "android_capabilities": requested,
        "linux_capabilities": linux_caps,
        "requires_keepcaps_or_ambient": bool(linux_caps),
        "required_sequence_notes": [
            "fork child while still root",
            "enter private Android execution namespace",
            "create process group/session for bounded cleanup",
            "set supplemental groups before dropping gid/uid",
            "preserve required capabilities across uid transition",
            "restore effective/permitted capability set for child",
            "exec target with bounded timeout and captured output",
        ],
        "must_probe_before_start": [
            "kernel supports required capability operations",
            "launcher can retain CAP_NET_ADMIN after dropping to AID_SYSTEM",
            "post-exec child status exposes expected uid/gid/groups/caps on harmless probe binary",
        ],
    }


def build_launcher_contract(v242: dict[str, Any]) -> dict[str, Any]:
    daemon = service_by_name(v242, "cnss-daemon")
    diag = service_by_name(v242, "cnss_diag")
    identity = numeric_identity(daemon)
    return {
        "mode": "bounded-cnss-start-only-contract",
        "daemon_start_allowed_in_v243": False,
        "target": {
            "service": daemon.get("name"),
            "android_executable": daemon.get("executable"),
            "private_namespace_executable": "/vendor/bin/cnss-daemon",
            "argv": ["/vendor/bin/cnss-daemon", *daemon.get("args", [])],
            "args": daemon.get("args", []),
            "source": daemon.get("source"),
        },
        "identity": identity,
        "capabilities": capability_contract(daemon),
        "namespace_requirements": {
            "helper": "/cache/bin/a90_android_execns_probe or successor",
            "null_device_mode": "dev-null",
            "linkerconfig_mode": "copy-real",
            "vndk_apex_alias_mode": "v30-to-current",
            "vendor_source": "private ro,noload vendor mount",
            "system_source": "/mnt/system/system",
            "global_path_alias_allowed": False,
        },
        "runtime_known_gaps": [
            blocker for blocker in v242.get("runtime_requirements", {}).get("start_only_blockers", [])
            if blocker.get("name") != "launcher-identity-contract"
        ],
        "phase2_blocked": {
            "service": diag.get("name"),
            "reason": "diagnostic sidecar remains blocked until /dev/diag and diag group/device contract is understood",
        },
    }


def build_safety_gates(v242: dict[str, Any]) -> dict[str, Any]:
    return {
        "required_prior_decisions": {
            "v241": "android-linker-vndk-apex-alias-cnss-list-pass",
            "v242": REQUIRED_V242_DECISION,
        },
        "required_preflight": [
            "helper exists and hash/version is expected",
            "real linkerconfig is present",
            "private VNDK APEX alias linker-list still passes",
            "harmless identity/capability probe passes before daemon entrypoint",
            "ACM rescue or NCM control path is available before start",
        ],
        "required_runtime_envelope": {
            "timeout_sec": 10,
            "hard_timeout_sec": 30,
            "process_group_cleanup": True,
            "capture_stdout_stderr": True,
            "postflight_selftest": True,
            "postflight_no_stale_process": True,
        },
        "future_start_requires_flags": ["--allow-daemon-start", "--assume-yes"],
        "denied_actions": [
            "cnss_diag start before separate phase2 approval",
            "wpa_supplicant/wificond/HAL/hostapd start",
            "Wi-Fi scan/connect/link-up/credential/DHCP/routing",
            "rfkill write",
            "ICNSS bind/unbind",
            "persistent Android partition write",
            "public network listener exposure",
        ],
        "manual_confirmation_required_for": [
            "first cnss-daemon start-only attempt",
            "any retry after start-only runtime gap",
            "any expansion beyond 10 second start-only window",
        ],
        "v242_blockers": v242.get("runtime_requirements", {}).get("start_only_blockers", []),
    }


def build_implementation_plan(contract: dict[str, Any], gates: dict[str, Any]) -> dict[str, Any]:
    return {
        "next_version_candidate": "v244",
        "recommended_next_step": "non-starting launcher dry-run and harmless identity/capability probe",
        "helper_changes": [
            {
                "name": "a90_android_execns_probe successor mode",
                "detail": "add a mode that prepares the same private namespace as v241 but runs a harmless id/cap probe binary instead of cnss-daemon",
            },
            {
                "name": "identity application",
                "detail": "map Android AID names to numeric uid/gid, call setgroups/setgid/setuid in a tested order",
            },
            {
                "name": "capability application",
                "detail": "prove CAP_NET_ADMIN preservation/restoration on the harmless probe before daemon start is enabled",
            },
            {
                "name": "bounded process lifecycle",
                "detail": "setsid/process group, timeout, SIGTERM/SIGKILL cleanup, and stale process verification",
            },
        ],
        "host_runner_changes": [
            "consume launcher-contract.json and safety-gates.json",
            "refuse daemon start unless explicit opt-in flags are present",
            "record stdout/stderr/status and cleanup evidence in private output directory",
            "keep Wi-Fi scan/connect commands out of allowlist",
        ],
        "still_blocked": [
            "first cnss-daemon start-only attempt",
            "cnss_diag",
            "Wi-Fi HAL/wificond/supplicant/hostapd",
            "scan/connect/link-up/DHCP/routing",
        ],
        "contract_summary": {
            "target": contract["target"],
            "required_preflight_count": len(gates["required_preflight"]),
            "denied_action_count": len(gates["denied_actions"]),
        },
    }


def build_checks(v242: dict[str, Any], contract: dict[str, Any]) -> list[dict[str, Any]]:
    identity = contract["identity"]
    caps = contract["capabilities"]
    return [
        {
            "name": "v242-ready",
            "pass": v242_ready(v242),
            "detail": str(v242.get("decision", "missing")),
        },
        {
            "name": "android-aid-map-complete-for-cnss-daemon",
            "pass": not identity.get("missing_aid_names"),
            "detail": ",".join(identity.get("missing_aid_names", [])) or "complete",
        },
        {
            "name": "net-admin-contract-present",
            "pass": "CAP_NET_ADMIN" in caps.get("linux_capabilities", []),
            "detail": ",".join(caps.get("linux_capabilities", [])),
        },
        {
            "name": "daemon-start-disabled-in-v243",
            "pass": contract.get("daemon_start_allowed_in_v243") is False,
            "detail": "planner only",
        },
    ]


def classify(checks: list[dict[str, Any]]) -> tuple[bool, str, str]:
    if not all(item["pass"] for item in checks):
        return False, "cnss-launcher-contract-gap", "launcher contract has unresolved input or mapping gaps"
    return True, "cnss-launcher-contract-ready", "contract is ready; daemon start remains blocked until implementation and explicit approval"


def write_summary(
    store: EvidenceStore,
    manifest: dict[str, Any],
    contract: dict[str, Any],
    gates: dict[str, Any],
    implementation: dict[str, Any],
) -> None:
    check_rows = [
        [item["name"], "PASS" if item["pass"] else "FAIL", item.get("detail", "")]
        for item in manifest["checks"]
    ]
    identity = contract["identity"]
    id_rows = [
        ["user", identity["user"]["name"], str(identity["user"]["uid"])],
        ["primary_group", identity["primary_group"]["name"], str(identity["primary_group"]["gid"])],
    ] + [
        ["supplemental_group", group["name"], str(group["gid"])]
        for group in identity["supplemental_groups"]
    ]
    denied_rows = [[item] for item in gates["denied_actions"]]
    helper_rows = [[item["name"], item["detail"]] for item in implementation["helper_changes"]]

    lines = [
        "# v243 CNSS Launcher Contract Plan\n\n",
        f"- generated: `{manifest['created']}`\n",
        f"- result: `{'PASS' if manifest['pass'] else 'FAIL'}`\n",
        f"- decision: `{manifest['decision']}`\n",
        f"- reason: `{manifest['reason']}`\n",
        f"- daemon start: `blocked`\n",
        f"- output: `{manifest['out_dir']}`\n\n",
        "## Checks\n\n",
        markdown_table(["check", "result", "detail"], check_rows),
        "\n\n## Identity Contract\n\n",
        markdown_table(["kind", "name", "id"], id_rows),
        "\n\n## Capability Contract\n\n",
        f"- Android capabilities: `{','.join(contract['capabilities']['android_capabilities'])}`\n",
        f"- Linux capabilities: `{','.join(contract['capabilities']['linux_capabilities'])}`\n",
        "- Requires keepcaps/ambient/capset proof before daemon start.\n\n",
        "## Required Preflight\n\n",
        "\n".join(f"- {item}" for item in gates["required_preflight"]),
        "\n\n## Denied Actions\n\n",
        markdown_table(["action"], denied_rows),
        "\n\n## Helper Implementation Requirements\n\n",
        markdown_table(["item", "detail"], helper_rows),
        "\n\n## Interpretation\n\n",
        "- v243 is a contract artifact, not a daemon execution artifact.\n",
        "- v244 should prove identity/capability handling with a harmless probe before `cnss-daemon` can be considered.\n",
        "- Wi-Fi scan/connect/link-up/credential/DHCP/routing remain blocked.\n",
    ]
    store.write_text("summary.md", "".join(lines))


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    v242 = load_json(args.v242_manifest)
    contract = build_launcher_contract(v242)
    gates = build_safety_gates(v242)
    implementation = build_implementation_plan(contract, gates)
    checks = build_checks(v242, contract)
    result_pass, decision, reason = classify(checks)
    manifest = {
        "created": now_iso(),
        "out_dir": str(repo_path(args.out_dir)),
        "pass": result_pass,
        "decision": decision,
        "reason": reason,
        "host_metadata": collect_host_metadata(),
        "inputs": {
            "v242_manifest": v242.get("_manifest_path", v242.get("path", "")),
            "v242_decision": v242.get("decision", "missing"),
        },
        "checks": checks,
        "guardrails": gates["denied_actions"],
        "next": implementation["recommended_next_step"],
    }

    store.write_json("launcher-contract.json", contract)
    store.write_json("safety-gates.json", gates)
    store.write_json("implementation-plan.json", implementation)
    store.write_json("manifest.json", manifest)
    write_summary(store, manifest, contract, gates, implementation)

    print(f"decision: {decision}")
    print(f"pass: {result_pass}")
    print(f"out_dir: {repo_path(args.out_dir)}")
    print(f"next: {implementation['recommended_next_step']}")
    return 0 if result_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())

