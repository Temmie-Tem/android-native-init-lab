#!/usr/bin/env python3
"""V830 execns helper v127 deploy/preflight wrapper."""

from __future__ import annotations

import sys

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v830-execns-helper-v127-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v830-execns-helper-v127-build/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "e2ba21fc7f00afc433fa23358d05780dcc0e5288bfc7db7d015e87c61d3e36d7"
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1850
deploy.HELPER_MARKER = "a90_android_execns_probe v127"
deploy.SERVICE_MODE_TOKEN = "--allow-service-notifier-listener-probe"
deploy.DEPLOY_LABEL = "v127"
deploy.DEPLOY_NAME = "execns-helper-v127"
deploy.DEPLOY_PLAN_VERSION = "V830"
deploy.DEPLOY_LOG_PREFIX = "v830"
deploy.SUMMARY_TITLE = "v830 Execns Helper v127 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v830 deploy execns helper v127 only; "
    "no daemon start and no Wi-Fi bring-up"
)

V830_SCRIPT = deploy.Path("scripts/revalidation/native_wifi_service_notifier_listener_probe_v830.py")


def run_v830_plan(args: deploy.argparse.Namespace, store: deploy.EvidenceStore) -> dict[str, object]:
    out_dir = store.path("v830-service-notifier-listener-plan")
    command = [
        sys.executable,
        str(deploy.repo_path(V830_SCRIPT)),
        "--out-dir",
        str(out_dir),
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--timeout",
        str(args.timeout),
        "--expect-version",
        args.expect_version,
        "--helper",
        args.remote_helper,
        "--helper-sha256",
        args.helper_sha256,
        "--helper-marker",
        deploy.HELPER_MARKER,
        "--local-helper",
        str(args.local_helper),
        "plan",
    ]
    rc, output = deploy.run_host(command, timeout=180)
    store.write_text("host/v830-service-notifier-listener-plan.txt", output)
    manifest_path = out_dir / "manifest.json"
    manifest: dict[str, object] = {}
    if manifest_path.exists():
        manifest = deploy.json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        "command": " ".join(command),
        "rc": rc,
        "ok": rc == 0,
        "file": "host/v830-service-notifier-listener-plan.txt",
        "manifest": str(manifest_path),
        "decision": manifest.get("decision", "missing"),
        "pass": manifest.get("pass", False),
    }


def decide(args: deploy.argparse.Namespace,
           checks: list[deploy.Check],
           deploy_result: dict[str, object] | None,
           v830_result: dict[str, object] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return f"{deploy.DEPLOY_NAME}-deploy-plan-ready", True, "plan-only; no live command executed", "run V830 helper deploy preflight"
    blockers = deploy.blocking_checks(
        checks,
        ignore_deploy=args.command == "preflight" or (args.command == "run" and deploy.approved(args)),
    )
    if blockers:
        return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
    if args.command == "preflight":
        return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready", True, "preflight complete; deploy still requires exact approval", "run approved V830 helper v127 deploy"
    if not deploy.approved(args):
        return f"{deploy.DEPLOY_NAME}-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact V830 deploy phrase"
    if deploy_result and not deploy_result["ok"]:
        return f"{deploy.DEPLOY_NAME}-deploy-failed", False, "install command failed", "inspect install transcript and retry after cleanup"
    if v830_result and v830_result.get("decision") != "v830-service-notifier-listener-plan-ready":
        return (
            f"{deploy.DEPLOY_NAME}-deploy-postflight-review",
            False,
            f"V830 plan decision={v830_result.get('decision')}",
            "inspect helper v127 post-deploy V830 plan output",
        )
    return f"{deploy.DEPLOY_NAME}-deploy-pass", True, "helper v127 deployed or already current; V830 plan was rerun", "run V830 bounded service-notifier listener probe"


deploy.run_v373_preflight = run_v830_plan
deploy.decide = decide


if __name__ == "__main__":
    raise SystemExit(deploy.main())
