#!/usr/bin/env python3
"""V405 execns helper v23 deploy/preflight wrapper.

Deploy is limited to /cache/bin/a90_android_execns_probe and requires the exact
V405 deploy approval phrase. It does not start service-manager, Wi-Fi HAL, or
Wi-Fi bring-up.
"""

from __future__ import annotations

import sys

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.__doc__ = __doc__
deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v405-execns-helper-v23-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v405-a90_android_execns_probe-v23/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "64c80e73d791b82e0b9f60b05db1df1781bf5033b1ffd76e323cf52ce3dbc520"
deploy.HELPER_MARKER = "a90_android_execns_probe v23"
deploy.SERVICE_MODE_TOKEN = "wifi-hal-composite-start-only"
deploy.DEPLOY_LABEL = "v23"
deploy.DEPLOY_NAME = "execns-helper-v23"
deploy.DEPLOY_PLAN_VERSION = "V405"
deploy.DEPLOY_LOG_PREFIX = "v405"
deploy.SUMMARY_TITLE = "v405 Execns Helper v23 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v405 deploy execns helper v23 only; "
    "no daemon start and no Wi-Fi bring-up"
)
deploy.V373_SCRIPT = deploy.Path("scripts/revalidation/wifi_composite_hal_start_only_v405_runner.py")


def run_v405_preflight(args: deploy.argparse.Namespace, store: deploy.EvidenceStore) -> dict[str, object]:
    out_dir = store.path("v405-composite-hal-preflight")
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
    store.write_text("host/v405-composite-hal-preflight.txt", output)
    manifest_path = out_dir / "manifest.json"
    manifest: dict[str, object] = {}
    if manifest_path.exists():
        manifest = deploy.json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        "command": " ".join(command),
        "rc": rc,
        "ok": rc == 0,
        "file": "host/v405-composite-hal-preflight.txt",
        "manifest": str(manifest_path),
        "decision": manifest.get("decision", "missing"),
        "pass": manifest.get("pass", False),
    }


def decide(args: deploy.argparse.Namespace,
           checks: list[deploy.Check],
           deploy_result: dict[str, object] | None,
           v405_result: dict[str, object] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return "execns-helper-v23-deploy-plan-ready", True, "plan-only; no live command executed", "run preflight"
    blockers = deploy.blocking_checks(checks, ignore_deploy=True)
    if blockers:
        return "execns-helper-v23-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
    deploy_needed = any(check.name == "remote-helper-v23" and check.status != "pass" for check in checks)
    if args.command == "preflight":
        if deploy_needed:
            return "execns-helper-v23-deploy-preflight-ready-needs-deploy", True, "preflight complete; helper v23 deploy still requires exact approval", "operator may approve V405 deploy"
        return "execns-helper-v23-deploy-preflight-ready", True, "preflight complete; deploy still requires exact approval", "operator may approve V405 deploy"
    if not deploy.approved(args):
        return "execns-helper-v23-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact phrase if deploy is intended"
    if deploy_result and not deploy_result["ok"]:
        return "execns-helper-v23-deploy-failed", False, "install command failed", "inspect install transcript and retry after cleanup"
    if v405_result and v405_result["decision"] != "composite-hal-start-only-preflight-ready":
        return "execns-helper-v23-deploy-postflight-blocked", False, f"V405 preflight decision={v405_result['decision']}", "resolve V405 preflight blockers"
    return "execns-helper-v23-deploy-pass", True, "helper v23 deployed or already current; V405 composite HAL preflight is ready", "next requires separate V405 composite HAL approval"


deploy.run_v373_preflight = run_v405_preflight
deploy.decide = decide


if __name__ == "__main__":
    raise SystemExit(deploy.main())
