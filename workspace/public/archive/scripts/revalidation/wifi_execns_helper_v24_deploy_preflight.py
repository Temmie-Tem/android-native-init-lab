#!/usr/bin/env python3
"""V406 execns helper v24 deploy/preflight wrapper.

Deploy is limited to /cache/bin/a90_android_execns_probe and requires the exact
V406 deploy approval phrase. It does not start service-manager, Wi-Fi HAL, or
Wi-Fi bring-up.
"""

from __future__ import annotations

import sys

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.__doc__ = __doc__
deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v406-execns-helper-v24-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v406-a90_android_execns_probe-v24/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "7ec11d95085f1c3dc370884725b080b44150bf8b0a5f7d897df048188a815063"
deploy.HELPER_MARKER = "a90_android_execns_probe v24"
deploy.SERVICE_MODE_TOKEN = "v30-to-system-ext-v30"
deploy.DEPLOY_LABEL = "v24"
deploy.DEPLOY_NAME = "execns-helper-v24"
deploy.DEPLOY_PLAN_VERSION = "V406"
deploy.DEPLOY_LOG_PREFIX = "v406"
deploy.SUMMARY_TITLE = "v406 Execns Helper v24 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v406 deploy execns helper v24 only; "
    "no daemon start and no Wi-Fi bring-up"
)
deploy.V373_SCRIPT = deploy.Path("scripts/revalidation/wifi_system_ext_vndk_apex_v406_runner.py")


def run_v406_preflight(args: deploy.argparse.Namespace, store: deploy.EvidenceStore) -> dict[str, object]:
    out_dir = store.path("v406-system-ext-vndk-preflight")
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
    store.write_text("host/v406-system-ext-vndk-preflight.txt", output)
    manifest_path = out_dir / "manifest.json"
    manifest: dict[str, object] = {}
    if manifest_path.exists():
        manifest = deploy.json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        "command": " ".join(command),
        "rc": rc,
        "ok": rc == 0,
        "file": "host/v406-system-ext-vndk-preflight.txt",
        "manifest": str(manifest_path),
        "decision": manifest.get("decision", "missing"),
        "pass": manifest.get("pass", False),
    }


def decide(args: deploy.argparse.Namespace,
           checks: list[deploy.Check],
           deploy_result: dict[str, object] | None,
           v406_result: dict[str, object] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return "execns-helper-v24-deploy-plan-ready", True, "plan-only; no live command executed", "run preflight"
    blockers = deploy.blocking_checks(checks, ignore_deploy=True)
    if blockers:
        return "execns-helper-v24-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
    deploy_needed = any(check.name == "remote-helper-v24" and check.status != "pass" for check in checks)
    if args.command == "preflight":
        if deploy_needed:
            return "execns-helper-v24-deploy-preflight-ready-needs-deploy", True, "preflight complete; helper v24 deploy still requires exact approval", "operator may approve V406 deploy"
        return "execns-helper-v24-deploy-preflight-ready", True, "preflight complete; deploy still requires exact approval", "operator may approve V406 deploy"
    if not deploy.approved(args):
        return "execns-helper-v24-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact phrase if deploy is intended"
    if deploy_result and not deploy_result["ok"]:
        return "execns-helper-v24-deploy-failed", False, "install command failed", "inspect install transcript and retry after cleanup"
    if v406_result and v406_result["decision"] != "system-ext-vndk-linker-list-preflight-ready":
        return "execns-helper-v24-deploy-postflight-blocked", False, f"V406 preflight decision={v406_result['decision']}", "resolve V406 preflight blockers"
    return "execns-helper-v24-deploy-pass", True, "helper v24 deployed or already current; V406 system_ext VNDK linker-list preflight is ready", "next requires separate V406 linker-list approval"


deploy.run_v373_preflight = run_v406_preflight
deploy.decide = decide


if __name__ == "__main__":
    raise SystemExit(deploy.main())
