#!/usr/bin/env python3
"""V550 bounded vndservicemanager companion replay with real linkerconfig.

V549 proved `vndservicemanager /dev/vndbinder` exits early under the synthetic
minimal-vendor linkerconfig because it cannot resolve a libbinder symbol. V550
keeps the same no-HAL/no-scan/no-connect bounded contract and switches only the
private linkerconfig materialization to the Android-captured copy-real files.
"""

from __future__ import annotations

from typing import Any

import native_wifi_companion_vnd_service_manager_replay_v549 as v549


base = v549.base
base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = base.Path("tmp/wifi/v550-companion-vnd-service-manager-copyreal")
base.PROOF_VERSION = "V550"
base.PROOF_SLUG = "v550-companion-vnd-service-manager-copyreal"
base.LIVE_HELPER_STEP_NAME = "v550-helper-run"
base.APPROVAL_PHRASE = (
    "approve v550 companion vnd service-manager copy-real replay only; "
    "no Wi-Fi HAL start, no scan/connect/link-up and no external ping"
)

REAL_LD_CONFIG = "/cache/bin/a90_real_ld.config.txt"
REAL_APEX_LIBRARIES = "/cache/bin/a90_real_apex.libraries.config.txt"
MAX_CMDV1_COMMAND_ARGS = 30

_orig_preflight_steps = base.preflight_steps
_orig_build_checks = base.build_checks
_orig_helper_command = base.helper_command
_orig_classify = base.classify


def remove_option_with_value(command: list[str], option: str) -> None:
    while True:
        try:
            option_index = command.index(option)
        except ValueError:
            return
        del command[option_index:option_index + 2]


def preflight_steps(args: base.argparse.Namespace, store: base.EvidenceStore) -> list[dict[str, Any]]:
    steps = _orig_preflight_steps(args, store)
    if args.command != "plan":
        steps.append(base.run_step(args, store, "stat-real-ld-config", ["stat", REAL_LD_CONFIG], 10.0))
        steps.append(base.run_step(args, store, "stat-real-apex-libraries", ["stat", REAL_APEX_LIBRARIES], 10.0))
    return steps


def build_checks(args: base.argparse.Namespace,
                 steps: list[dict[str, Any]],
                 v490: dict[str, Any],
                 v525: dict[str, Any]) -> list[base.Check]:
    checks = _orig_build_checks(args, steps, v490, v525)
    if args.command == "plan":
        return checks
    ld_text = base.step_payload(steps, "stat-real-ld-config")
    apex_text = base.step_payload(steps, "stat-real-apex-libraries")
    base.add_check(
        checks,
        "real-linkerconfig-present",
        "pass" if "size=134256" in ld_text else "blocked",
        "blocker",
        f"path={REAL_LD_CONFIG}",
        [line for line in ld_text.splitlines() if "size=" in line or REAL_LD_CONFIG in line][:4],
        "restore Android-captured ld.config.txt before V550",
    )
    base.add_check(
        checks,
        "real-apex-libraries-present",
        "pass" if "size=366" in apex_text else "blocked",
        "blocker",
        f"path={REAL_APEX_LIBRARIES}",
        [line for line in apex_text.splitlines() if "size=" in line or REAL_APEX_LIBRARIES in line][:4],
        "restore Android-captured apex.libraries.config.txt before V550",
    )
    return checks


def helper_command(args: base.argparse.Namespace) -> list[str]:
    command = _orig_helper_command(args)
    remove_option_with_value(command, "--capture-mode")
    try:
        index = command.index("--linkerconfig-mode")
    except ValueError:
        command.extend(["--linkerconfig-mode", "copy-real"])
    else:
        command[index + 1] = "copy-real"
    command.extend([
        "--linkerconfig-source", REAL_LD_CONFIG,
        "--apex-libraries-source", REAL_APEX_LIBRARIES,
    ])
    if len(command) > MAX_CMDV1_COMMAND_ARGS:
        raise RuntimeError(
            f"V550 helper command has {len(command)} args; cmdv1 safely carries "
            f"at most {MAX_CMDV1_COMMAND_ARGS} command args"
        )
    return command


def classify(args: base.argparse.Namespace,
             checks: list[base.Check],
             live_result: dict[str, Any] | None,
             dmesg: dict[str, Any]) -> tuple[str, bool, str, str, bool]:
    decision, pass_ok, reason, next_step, live_executed = _orig_classify(args, checks, live_result, dmesg)
    if args.command != "run" or not live_result:
        return decision, pass_ok, reason, next_step, live_executed
    stderr_tail = "\n".join(live_result.get("helper_stderr_tail") or [])
    if "cannot locate symbol" in stderr_tail and "vndservicemanager" in stderr_tail:
        return (
            "v550-companion-vnd-service-manager-copyreal-linker-gap-persists",
            True,
            "copy-real linkerconfig still leaves vndservicemanager with an unresolved libbinder symbol",
            "compare vndservicemanager dependency namespace against Android boot and adjust permitted library source",
            live_executed,
        )
    if decision.startswith("v549-"):
        return decision.replace("v549-", "v550-", 1), pass_ok, reason, next_step, live_executed
    return decision, pass_ok, reason, next_step, live_executed


base.preflight_steps = preflight_steps
base.build_checks = build_checks
base.helper_command = helper_command
base.classify = classify


if __name__ == "__main__":
    raise SystemExit(base.main())
