#!/usr/bin/env python3
"""V409 execns helper v25 deploy/preflight wrapper.

Deploy is limited to `/cache/bin/a90_android_execns_probe` and requires the
exact V409 deploy approval phrase.  It does not start service-manager,
hwservicemanager, Wi-Fi HAL, lshal, or Wi-Fi bring-up.
"""

from __future__ import annotations

import sys

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.__doc__ = __doc__
deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v409-execns-helper-v25-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v409-a90_android_execns_probe-v25/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "e90639d55dacc5486c998c4d1470235a6c72e4759cc63ebd1f07cf90c5852b37"
deploy.HELPER_MARKER = "a90_android_execns_probe v25"
deploy.SERVICE_MODE_TOKEN = "wifi-hal-composite-lshal-list"
deploy.DEPLOY_LABEL = "v25"
deploy.DEPLOY_NAME = "execns-helper-v25"
deploy.DEPLOY_PLAN_VERSION = "V409"
deploy.DEPLOY_LOG_PREFIX = "v409"
deploy.SUMMARY_TITLE = "v409 Execns Helper v25 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v409 deploy execns helper v25 only; "
    "no daemon start and no Wi-Fi bring-up"
)
deploy.V373_SCRIPT = deploy.Path("scripts/revalidation/wifi_hal_registration_query_v409_runner.py")

QUERY_GUARD_TOKEN = "--allow-hal-service-query"

_BASE_LOCAL_HELPER_INFO = deploy.local_helper_info
_BASE_BUILD_CHECKS = deploy.build_checks


def local_helper_info(args: deploy.argparse.Namespace) -> dict[str, object]:
    info = _BASE_LOCAL_HELPER_INFO(args)
    info["strings_query_guard"] = False
    if not info.get("exists"):
        return info
    rc, strings_output = deploy.run_host(["strings", str(deploy.repo_path(args.local_helper))], timeout=10)
    if rc == 0:
        info["strings_query_guard"] = QUERY_GUARD_TOKEN in strings_output
    return info


def build_checks(args: deploy.argparse.Namespace, store: deploy.EvidenceStore,
                 steps: list[deploy.StepResult], local: dict[str, object],
                 ping: dict[str, object] | None) -> list[deploy.Check]:
    checks = _BASE_BUILD_CHECKS(args, store, steps, local, ping)
    local_guard_ok = bool(local.get("strings_query_guard"))
    deploy.add_check(
        checks,
        "local-helper-v25-query-guard",
        "pass" if local_guard_ok else "blocked",
        "blocker",
        f"query_guard={local_guard_ok}",
        [str(local.get("path", ""))],
        "rebuild helper v25 with --allow-hal-service-query guard before deploy",
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
    )
    deploy.add_check(
        checks,
        "remote-helper-v25-query-guard",
        "pass" if remote_guard_ok else "needs-deploy",
        "deploy",
        f"query_guard={remote_guard_ok}",
        [line for line in helper_usage.splitlines() if QUERY_GUARD_TOKEN in line or deploy.SERVICE_MODE_TOKEN in line][:4],
        "approved V409 deploy installs helper v25 with query guard if needed",
    )
    return checks


def run_v409_preflight(args: deploy.argparse.Namespace, store: deploy.EvidenceStore) -> dict[str, object]:
    out_dir = store.path("v409-registration-query-preflight")
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
    store.write_text("host/v409-registration-query-preflight.txt", output)
    manifest_path = out_dir / "manifest.json"
    manifest: dict[str, object] = {}
    if manifest_path.exists():
        manifest = deploy.json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        "command": " ".join(command),
        "rc": rc,
        "ok": rc == 0,
        "file": "host/v409-registration-query-preflight.txt",
        "manifest": str(manifest_path),
        "decision": manifest.get("decision", "missing"),
        "pass": manifest.get("pass", False),
    }


def decide(args: deploy.argparse.Namespace,
           checks: list[deploy.Check],
           deploy_result: dict[str, object] | None,
           v409_result: dict[str, object] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return "execns-helper-v25-deploy-plan-ready", True, "plan-only; no live command executed", "run preflight"
    blockers = deploy.blocking_checks(checks, ignore_deploy=True)
    if blockers:
        return "execns-helper-v25-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
    deploy_needed = any(check.name == "remote-helper-v25" and check.status != "pass" for check in checks)
    if args.command == "preflight":
        if deploy_needed:
            return "execns-helper-v25-deploy-preflight-ready-needs-deploy", True, "preflight complete; helper v25 deploy still requires exact approval", "operator may approve V409 deploy"
        return "execns-helper-v25-deploy-preflight-ready", True, "preflight complete; deploy still requires exact approval", "operator may approve V409 deploy"
    if not deploy.approved(args):
        return "execns-helper-v25-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact phrase if deploy is intended"
    if deploy_result and not deploy_result["ok"]:
        return "execns-helper-v25-deploy-failed", False, "install command failed", "inspect install transcript and retry after cleanup"
    if v409_result and v409_result["decision"] not in (
        "v409-hal-registration-query-preflight-ready",
        "v409-hal-registration-query-blocked",
    ):
        return "execns-helper-v25-deploy-postflight-review", False, f"V409 preflight decision={v409_result['decision']}", "inspect V409 preflight output"
    return "execns-helper-v25-deploy-pass", True, "helper v25 deployed or already current; V409 query preflight was rerun", "next requires separate V409 registration-query approval"


deploy.run_v373_preflight = run_v409_preflight
deploy.decide = decide
deploy.local_helper_info = local_helper_info
deploy.build_checks = build_checks


if __name__ == "__main__":
    raise SystemExit(deploy.main())
