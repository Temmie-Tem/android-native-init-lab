#!/usr/bin/env python3
"""V410 host-only arg-budget contract linter.

The V410 live query command intentionally omits ``--data-wifi-mode`` to stay
within the native shell argument limit.  This linter proves the omission is safe
only because helper v26 defaults ``wifi-hal-composite-lshal-list`` to
``private-empty`` before validation and because the runner records that implicit
contract in its plan manifest.

It executes no device commands.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path


HELPER_SOURCE = Path("stage3/linux_init/helpers/a90_android_execns_probe.c")
RUNNER_SOURCE = Path("scripts/revalidation/wifi_hal_registration_query_v410_runner.py")
DEPLOY_SOURCE = Path("scripts/revalidation/wifi_execns_helper_v26_deploy_preflight.py")
DEFAULT_APPROVED_PLAN = Path("tmp/wifi/v410-registration-query-approved-plan-argcheck-20260520-104923/manifest.json")
DEFAULT_OUT_PARENT = Path("tmp/wifi")
EXPECTED_SHA256 = "daf1b59e2475c0db28fb99eb83f8be02a46f695d8c4e435c47e68f45370a7caa"


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


def load_json(path: Path) -> dict[str, object]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} is not a JSON object")
    return data


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approved-plan", type=Path, default=DEFAULT_APPROVED_PLAN)
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


def main() -> int:
    args = parse_args()
    out_dir = args.out_dir or DEFAULT_OUT_PARENT / f"v410-arg-budget-linter-{now_stamp()}"
    ensure_private_dir(out_dir)

    helper = read_text(HELPER_SOURCE)
    runner = read_text(RUNNER_SOURCE)
    deploy = read_text(DEPLOY_SOURCE)
    approved = load_json(args.approved_plan)
    plan = approved.get("plan") if isinstance(approved.get("plan"), dict) else {}
    command = plan.get("command") if isinstance(plan.get("command"), list) else []

    helper_compact = " ".join(helper.split())
    default_contract = (
        'if (streq(cfg->mode, "wifi-hal-composite-lshal-list") && '
        'streq(cfg->data_wifi_mode, "none")) { '
        'cfg->data_wifi_mode = "private-empty"; }'
    )
    validation_contract = (
        '!(streq(cfg->data_wifi_mode, "none") || '
        'streq(cfg->data_wifi_mode, "private-empty"))'
    )

    checks: list[Check] = []
    add_check(
        checks,
        "helper-v26-version",
        '#define EXECNS_VERSION "a90_android_execns_probe v26"' in helper,
        "helper source must advertise v26",
        [str(HELPER_SOURCE)],
    )
    add_check(
        checks,
        "helper-implicit-data-wifi-default",
        default_contract in helper_compact,
        "wifi-hal-composite-lshal-list must default data_wifi_mode none to private-empty",
        [str(HELPER_SOURCE)],
    )
    add_check(
        checks,
        "helper-data-wifi-allowlist",
        validation_contract in helper_compact,
        "data_wifi_mode validation must still allow only none/private-empty",
        [str(HELPER_SOURCE)],
    )
    add_check(
        checks,
        "runner-v26-sha",
        EXPECTED_SHA256 in runner and "v26" in runner,
        "runner must expect helper v26 SHA",
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
        "deploy-v26-sha-and-guard",
        EXPECTED_SHA256 in deploy and "local-helper-v26-query-guard" in deploy,
        "deploy wrapper must verify v26 helper and query guard",
        [str(DEPLOY_SOURCE), EXPECTED_SHA256],
    )
    add_check(
        checks,
        "approved-command-arg-budget",
        len(command) <= 30,
        f"approved command length={len(command)}",
        [" ".join(str(part) for part in command)],
    )
    add_check(
        checks,
        "approved-command-query-guard",
        "--allow-hal-service-query" in command,
        "approved command must include query guard",
        [" ".join(str(part) for part in command)],
    )
    add_check(
        checks,
        "approved-command-uses-implicit-data-wifi",
        "--data-wifi-mode" not in command and plan.get("helper_implicit_data_wifi_mode") == "private-empty",
        "approved command may omit data-wifi arg only when plan records helper implicit private-empty",
        [f"helper_implicit_data_wifi_mode={plan.get('helper_implicit_data_wifi_mode')}"],
    )
    add_check(
        checks,
        "approved-plan-no-device-command",
        approved.get("device_commands_executed") is False and approved.get("wifi_bringup_executed") is False,
        "argcheck source manifest must be host-only",
        [str(args.approved_plan)],
    )

    blocked = [check.name for check in checks if check.status != "pass"]
    manifest = {
        "generated_at": dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds"),
        "decision": "v410-arg-budget-contract-pass" if not blocked else "v410-arg-budget-contract-blocked",
        "pass": not blocked,
        "reason": "all V410 arg-budget contract checks passed" if not blocked else "blocked by " + ", ".join(blocked),
        "approved_plan": str(args.approved_plan),
        "checks": [asdict(check) for check in checks],
        "device_commands_executed": False,
        "device_mutations": False,
        "wifi_bringup_executed": False,
    }
    safe_write_text(out_dir / "manifest.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    safe_write_text(
        out_dir / "README.md",
        "# V410 Arg-Budget Contract Linter\n\n"
        f"- decision: `{manifest['decision']}`\n"
        f"- pass: `{manifest['pass']}`\n"
        f"- reason: {manifest['reason']}\n"
        "- device_commands_executed: `False`\n"
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
