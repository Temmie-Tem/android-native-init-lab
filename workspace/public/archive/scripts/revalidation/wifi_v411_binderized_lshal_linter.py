#!/usr/bin/env python3
"""V411 host-only binderized-lshal contract linter.

V411 narrows the V410 default ``lshal`` query to
``lshal list --types=binderized --neat``.  This linter proves the helper,
runner, deploy wrapper, and generated approval manifests all agree on that
contract before any helper deploy or live query is allowed.

It executes no device commands.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


HELPER_SOURCE = Path("stage3/linux_init/helpers/a90_android_execns_probe.c")
RUNNER_SOURCE = Path("scripts/revalidation/wifi_hal_binderized_registration_query_v411_runner.py")
DEPLOY_SOURCE = Path("scripts/revalidation/wifi_execns_helper_v27_deploy_preflight.py")
DEFAULT_APPROVED_PLAN = Path("tmp/wifi/v411-binderized-query-approved-plan-20260520-112814/manifest.json")
DEFAULT_NOAPPROVAL = Path("tmp/wifi/v411-binderized-query-noapproval-20260520-112815/manifest.json")
DEFAULT_DEPLOY_PLAN = Path("tmp/wifi/v411-helper-v27-deploy-plan-20260520-112815/manifest.json")
DEFAULT_QUERY_PREFLIGHT = Path("tmp/wifi/v411-binderized-query-readonly-preflight-20260520-112815/manifest.json")
DEFAULT_OUT_PARENT = Path("tmp/wifi")
EXPECTED_SHA256 = "0519b557482f347d47962e9da76ee7afcce270bf12df860d37678e9a26bf2c74"
MODE = "wifi-hal-composite-lshal-binderized-list"
APPROVAL_PHRASE = (
    "approve v411 bounded binderized lshal registration query only; "
    "no scan/connect/link-up and no Wi-Fi bring-up"
)


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str
    evidence: list[str]


def now_stamp() -> str:
    return dt.datetime.now(dt.timezone.utc).astimezone().strftime("%Y%m%d-%H%M%S")


def add_check(checks: list[Check], name: str, passed: bool, detail: str, evidence: list[str]) -> None:
    checks.append(Check(name, "pass" if passed else "blocked", detail, evidence))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} is not a JSON object")
    return data


def command_from(manifest: dict[str, Any]) -> list[Any]:
    plan = manifest.get("plan") if isinstance(manifest.get("plan"), dict) else {}
    command = plan.get("command") if isinstance(plan.get("command"), list) else []
    return command


def plan_from(manifest: dict[str, Any]) -> dict[str, Any]:
    return manifest.get("plan") if isinstance(manifest.get("plan"), dict) else {}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approved-plan", type=Path, default=DEFAULT_APPROVED_PLAN)
    parser.add_argument("--noapproval", type=Path, default=DEFAULT_NOAPPROVAL)
    parser.add_argument("--deploy-plan", type=Path, default=DEFAULT_DEPLOY_PLAN)
    parser.add_argument("--query-preflight", type=Path, default=DEFAULT_QUERY_PREFLIGHT)
    parser.add_argument("--out-dir", type=Path, default=None)
    return parser.parse_args()


def ensure_private_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    os.mkdir(path, 0o700)
    os.chmod(path, 0o700)


def safe_write_text(path: Path, text: str) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(text)


def check_status(manifest: dict[str, Any], name: str) -> str:
    checks = manifest.get("checks") if isinstance(manifest.get("checks"), list) else []
    for check in checks:
        if isinstance(check, dict) and check.get("name") == name:
            status = check.get("status")
            return str(status) if status is not None else ""
    return ""


def main() -> int:
    args = parse_args()
    out_dir = args.out_dir or DEFAULT_OUT_PARENT / f"v411-binderized-lshal-linter-{now_stamp()}"
    ensure_private_dir(out_dir)

    helper = read_text(HELPER_SOURCE)
    runner = read_text(RUNNER_SOURCE)
    deploy = read_text(DEPLOY_SOURCE)
    approved = load_json(args.approved_plan)
    noapproval = load_json(args.noapproval)
    deploy_plan = load_json(args.deploy_plan)
    query_preflight = load_json(args.query_preflight)
    approved_plan = plan_from(approved)
    approved_command = command_from(approved)
    noapproval_command = command_from(noapproval)

    helper_compact = " ".join(helper.split())
    implicit_contract = (
        'streq(cfg->mode, "wifi-hal-composite-lshal-binderized-list")) && '
        'streq(cfg->data_wifi_mode, "none")) { cfg->data_wifi_mode = "private-empty"; }'
    )

    checks: list[Check] = []
    add_check(
        checks,
        "helper-v27-version",
        '#define EXECNS_VERSION "a90_android_execns_probe v27"' in helper,
        "helper source must advertise v27",
        [str(HELPER_SOURCE)],
    )
    add_check(
        checks,
        "helper-binderized-mode-allowlisted",
        MODE in helper and MODE in helper_compact,
        "helper source must expose and allowlist binderized lshal mode",
        [str(HELPER_SOURCE), MODE],
    )
    add_check(
        checks,
        "helper-implicit-data-wifi-default",
        implicit_contract in helper_compact,
        "binderized lshal mode must default data_wifi_mode none to private-empty",
        [str(HELPER_SOURCE)],
    )
    add_check(
        checks,
        "helper-binderized-lshal-argv",
        '"/system/bin/lshal"' in helper and '"list"' in helper and '"--types=binderized"' in helper and '"--neat"' in helper,
        "helper query child must execute lshal list --types=binderized --neat",
        [str(HELPER_SOURCE)],
    )
    add_check(
        checks,
        "runner-v27-sha-mode-approval",
        EXPECTED_SHA256 in runner
        and MODE in runner
        and "approve v411 bounded binderized lshal registration query only; " in runner
        and "no scan/connect/link-up and no Wi-Fi bring-up" in runner,
        "runner must expect helper v27 SHA, binderized mode, and V411 approval phrase",
        [str(RUNNER_SOURCE), EXPECTED_SHA256],
    )
    add_check(
        checks,
        "runner-records-implicit-contract",
        'plan["helper_implicit_data_wifi_mode"] = "private-empty"' in runner,
        "runner plan must record implicit private-empty contract",
        [str(RUNNER_SOURCE)],
    )
    add_check(
        checks,
        "runner-checks-binderized-helper-strings",
        '"--types=binderized" in helper_usage' in runner and '"--neat" in helper_usage' in runner,
        "runner preflight must require remote helper to advertise binderized lshal args",
        [str(RUNNER_SOURCE)],
    )
    add_check(
        checks,
        "deploy-v27-sha-mode-and-guard",
        EXPECTED_SHA256 in deploy and MODE in deploy and "local-helper-v27-query-guard" in deploy,
        "deploy wrapper must verify helper v27 SHA, mode, and query guard",
        [str(DEPLOY_SOURCE), EXPECTED_SHA256],
    )
    add_check(
        checks,
        "deploy-checks-binderized-helper-strings",
        "BINDERIZED_QUERY_TOKENS" in deploy and "--types=binderized" in deploy and "--neat" in deploy,
        "deploy wrapper must require local/remote helper to advertise binderized lshal args",
        [str(DEPLOY_SOURCE)],
    )
    add_check(
        checks,
        "approved-command-arg-budget",
        len(approved_command) <= 30,
        f"approved command length={len(approved_command)}",
        [" ".join(str(part) for part in approved_command)],
    )
    add_check(
        checks,
        "approved-command-mode",
        "--mode" in approved_command and MODE in approved_command,
        "approved command must target binderized lshal mode",
        [" ".join(str(part) for part in approved_command)],
    )
    add_check(
        checks,
        "approved-command-query-guard",
        "--allow-hal-service-query" in approved_command,
        "approved command must include query guard",
        [" ".join(str(part) for part in approved_command)],
    )
    add_check(
        checks,
        "approved-command-uses-implicit-data-wifi",
        "--data-wifi-mode" not in approved_command and approved_plan.get("helper_implicit_data_wifi_mode") == "private-empty",
        "approved command may omit data-wifi arg only when plan records helper implicit private-empty",
        [f"helper_implicit_data_wifi_mode={approved_plan.get('helper_implicit_data_wifi_mode')}"],
    )
    add_check(
        checks,
        "approved-plan-host-only",
        approved.get("device_commands_executed") is False and approved.get("wifi_bringup_executed") is False,
        "approved-plan manifest must execute no device command",
        [str(args.approved_plan)],
    )
    add_check(
        checks,
        "noapproval-no-device-command",
        noapproval.get("decision") == "v411-hal-registration-query-approval-required"
        and noapproval.get("device_commands_executed") is False
        and noapproval.get("wifi_bringup_executed") is False
        and "--allow-hal-service-query" not in noapproval_command,
        "query run without exact approval must execute no device command and omit live query guards",
        [str(args.noapproval)],
    )
    add_check(
        checks,
        "deploy-plan-local-helper-pass",
        deploy_plan.get("decision") == "execns-helper-v27-deploy-plan-ready"
        and check_status(deploy_plan, "local-helper-v27") == "pass"
        and check_status(deploy_plan, "local-helper-v27-query-guard") == "pass"
        and deploy_plan.get("device_mutations") is False,
        "deploy plan must verify local v27 helper and remain host-only",
        [str(args.deploy_plan)],
    )
    add_check(
        checks,
        "query-preflight-expected-helper-blocker",
        query_preflight.get("decision") == "v411-hal-registration-query-blocked"
        and check_status(query_preflight, "helper-v27") == "blocked"
        and check_status(query_preflight, "lshal-binary") == "pass"
        and check_status(query_preflight, "process-surface-clean") == "pass"
        and check_status(query_preflight, "wifi-link-clean") == "pass"
        and query_preflight.get("device_mutations") is False
        and query_preflight.get("wifi_bringup_executed") is False,
        "read-only preflight before deploy must be blocked only by remote helper v27 while surfaces stay clean",
        [str(args.query_preflight)],
    )

    blocked = [check.name for check in checks if check.status != "pass"]
    manifest = {
        "generated_at": dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds"),
        "decision": "v411-binderized-lshal-contract-pass" if not blocked else "v411-binderized-lshal-contract-blocked",
        "pass": not blocked,
        "reason": "all V411 binderized-lshal contract checks passed" if not blocked else "blocked by " + ", ".join(blocked),
        "approved_plan": str(args.approved_plan),
        "noapproval": str(args.noapproval),
        "deploy_plan": str(args.deploy_plan),
        "query_preflight": str(args.query_preflight),
        "checks": [asdict(check) for check in checks],
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "wifi_bringup_executed": False,
    }
    safe_write_text(out_dir / "manifest.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    safe_write_text(
        out_dir / "README.md",
        "# V411 Binderized lshal Contract Linter\n\n"
        f"- decision: `{manifest['decision']}`\n"
        f"- pass: `{manifest['pass']}`\n"
        f"- reason: {manifest['reason']}\n"
        "- device_commands_executed: `False`\n"
        "- daemon_start_executed: `False`\n"
        "- wifi_hal_start_executed: `False`\n"
        "- wifi_bringup_executed: `False`\n",
    )
    print(json.dumps({
        "decision": manifest["decision"],
        "pass": manifest["pass"],
        "reason": manifest["reason"],
        "out_dir": str(out_dir),
        "device_commands_executed": False,
        "wifi_bringup_executed": False,
    }, indent=2, sort_keys=True))
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
