#!/usr/bin/env python3
"""V411 execns helper v27 deploy/preflight wrapper.

Deploy is limited to `/cache/bin/a90_android_execns_probe` and requires the
exact V411 deploy approval phrase.  It does not start service-manager,
hwservicemanager, Wi-Fi HAL, lshal, or Wi-Fi bring-up.
"""

from __future__ import annotations

import sys

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.__doc__ = __doc__
deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v411-execns-helper-v27-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v411-a90_android_execns_probe-v27/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "0519b557482f347d47962e9da76ee7afcce270bf12df860d37678e9a26bf2c74"
deploy.HELPER_MARKER = "a90_android_execns_probe v27"
deploy.SERVICE_MODE_TOKEN = "wifi-hal-composite-lshal-binderized-list"
deploy.DEPLOY_LABEL = "v27"
deploy.DEPLOY_NAME = "execns-helper-v27"
deploy.DEPLOY_PLAN_VERSION = "V411"
deploy.DEPLOY_LOG_PREFIX = "v411"
deploy.SUMMARY_TITLE = "v411 Execns Helper v27 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v411 deploy execns helper v27 only; "
    "no daemon start and no Wi-Fi bring-up"
)
deploy.V373_SCRIPT = deploy.Path("scripts/revalidation/wifi_hal_binderized_registration_query_v411_runner.py")

QUERY_GUARD_TOKEN = "--allow-hal-service-query"
BINDERIZED_QUERY_TOKENS = ("--types=binderized", "--neat")

_BASE_LOCAL_HELPER_INFO = deploy.local_helper_info
_BASE_BUILD_CHECKS = deploy.build_checks


def local_helper_info(args: deploy.argparse.Namespace) -> dict[str, object]:
    info = _BASE_LOCAL_HELPER_INFO(args)
    info["strings_query_guard"] = False
    info["strings_binderized_query"] = False
    if not info.get("exists"):
        return info
    rc, strings_output = deploy.run_host(["strings", str(deploy.repo_path(args.local_helper))], timeout=10)
    if rc == 0:
        info["strings_query_guard"] = QUERY_GUARD_TOKEN in strings_output
        info["strings_binderized_query"] = all(token in strings_output for token in BINDERIZED_QUERY_TOKENS)
    return info


def build_checks(args: deploy.argparse.Namespace, store: deploy.EvidenceStore,
                 steps: list[deploy.StepResult], local: dict[str, object],
                 ping: dict[str, object] | None) -> list[deploy.Check]:
    checks = _BASE_BUILD_CHECKS(args, store, steps, local, ping)
    local_guard_ok = bool(local.get("strings_query_guard"))
    local_binderized_ok = bool(local.get("strings_binderized_query"))
    deploy.add_check(
        checks,
        "local-helper-v27-query-guard",
        "pass" if local_guard_ok and local_binderized_ok else "blocked",
        "blocker",
        f"query_guard={local_guard_ok} binderized_query={local_binderized_ok}",
        [str(local.get("path", ""))],
        "rebuild helper v27 with --allow-hal-service-query and binderized lshal args before deploy",
    )
    if args.command == "plan":
        return checks
    helper_usage = deploy.capture_text(store, steps, "helper-usage")
    helper_sha = deploy.capture_text(store, steps, "sha-helper")
    remote_guard_ok = (
        args.helper_sha256 in helper_sha
        and deploy.HELPER_MARKER in helper_usage
        and deploy.SERVICE_MODE_TOKEN in helper_usage
        and QUERY_GUARD_TOKEN in helper_usage
        and all(token in helper_usage for token in BINDERIZED_QUERY_TOKENS)
    )
    deploy.add_check(
        checks,
        "remote-helper-v27-query-guard",
        "pass" if remote_guard_ok else "needs-deploy",
        "deploy",
        f"query_guard={remote_guard_ok}",
        [line for line in helper_usage.splitlines() if QUERY_GUARD_TOKEN in line or deploy.SERVICE_MODE_TOKEN in line][:4],
        "approved V411 deploy installs helper v27 with query guard if needed",
    )
    return checks


def run_v411_preflight(args: deploy.argparse.Namespace, store: deploy.EvidenceStore) -> dict[str, object]:
    out_dir = store.path("v411-binderized-registration-query-preflight")
    command = [
        sys.executable,
        str(deploy.repo_path(deploy.V373_SCRIPT)),
        "--out-dir",
        str(out_dir),
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--expect-version",
        args.expect_version,
        "--helper",
        args.remote_helper,
        "--helper-sha256",
        args.helper_sha256,
        "preflight",
    ]
    rc, output = deploy.run_host(command, timeout=180)
    store.write_text("host/v411-binderized-registration-query-preflight.txt", output)
    manifest_path = out_dir / "manifest.json"
    manifest: dict[str, object] = {}
    if manifest_path.exists():
        manifest = deploy.json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        "command": " ".join(command),
        "rc": rc,
        "ok": rc == 0,
        "file": "host/v411-binderized-registration-query-preflight.txt",
        "manifest": str(manifest_path),
        "decision": manifest.get("decision", "missing"),
        "pass": manifest.get("pass", False),
    }


def decide(args: deploy.argparse.Namespace,
           checks: list[deploy.Check],
           deploy_result: dict[str, object] | None,
           v411_result: dict[str, object] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return "execns-helper-v27-deploy-plan-ready", True, "plan-only; no live command executed", "run preflight"
    blockers = deploy.blocking_checks(checks, ignore_deploy=True)
    if blockers:
        return "execns-helper-v27-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
    deploy_needed = any(check.name == "remote-helper-v27" and check.status != "pass" for check in checks)
    if args.command == "preflight":
        if deploy_needed:
            return "execns-helper-v27-deploy-preflight-ready-needs-deploy", True, "preflight complete; helper v27 deploy still requires exact approval", "operator may approve V411 deploy"
        return "execns-helper-v27-deploy-preflight-ready", True, "preflight complete; deploy still requires exact approval", "operator may approve V411 deploy"
    if not deploy.approved(args):
        return "execns-helper-v27-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact phrase if deploy is intended"
    if deploy_result and not deploy_result["ok"]:
        return "execns-helper-v27-deploy-failed", False, "install command failed", "inspect install transcript and retry after cleanup"
    if v411_result and v411_result["decision"] not in (
        "v411-hal-registration-query-preflight-ready",
        "v411-hal-registration-query-blocked",
    ):
        return "execns-helper-v27-deploy-postflight-review", False, f"V411 preflight decision={v411_result['decision']}", "inspect V411 preflight output"
    return "execns-helper-v27-deploy-pass", True, "helper v27 deployed or already current; V411 binderized query preflight was rerun", "next requires separate V411 binderized registration-query approval"


deploy.run_v373_preflight = run_v411_preflight
deploy.decide = decide
deploy.local_helper_info = local_helper_info
deploy.build_checks = build_checks


if __name__ == "__main__":
    raise SystemExit(deploy.main())
