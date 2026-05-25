#!/usr/bin/env python3
"""V831 execns helper v128 deploy/preflight wrapper."""

from __future__ import annotations

import sys

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v831-execns-helper-v128-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v831-execns-helper-v128-build/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "30a509d500a8c887c1fb43c506c86aa2bf3b450bb770043d91a38a9d11dddfb8"
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.68 (v724)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1850
deploy.HELPER_MARKER = "a90_android_execns_probe v128"
deploy.SERVICE_MODE_TOKEN = "--allow-service-notifier-listener-probe"
deploy.DEPLOY_LABEL = "v128"
deploy.DEPLOY_NAME = "execns-helper-v128"
deploy.DEPLOY_PLAN_VERSION = "V831"
deploy.DEPLOY_LOG_PREFIX = "v831"
deploy.SUMMARY_TITLE = "v831 Execns Helper v128 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v831 deploy execns helper v128 only; "
    "no daemon start and no Wi-Fi bring-up"
)

V831_SCRIPT = deploy.Path("scripts/revalidation/native_wifi_service_notifier_early_listener_probe_v831.py")


def run_v831_plan(args: deploy.argparse.Namespace, store: deploy.EvidenceStore) -> dict[str, object]:
    out_dir = store.path("v831-service-notifier-early-listener-plan")
    command = [
        sys.executable,
        str(deploy.repo_path(V831_SCRIPT)),
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
    store.write_text("host/v831-service-notifier-early-listener-plan.txt", output)
    manifest_path = out_dir / "manifest.json"
    manifest: dict[str, object] = {}
    if manifest_path.exists():
        manifest = deploy.json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        "command": " ".join(command),
        "rc": rc,
        "ok": rc == 0,
        "file": "host/v831-service-notifier-early-listener-plan.txt",
        "manifest": str(manifest_path),
        "decision": manifest.get("decision", "missing"),
        "pass": manifest.get("pass", False),
    }


def decide(args: deploy.argparse.Namespace,
           checks: list[deploy.Check],
           deploy_result: dict[str, object] | None,
           v831_result: dict[str, object] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return f"{deploy.DEPLOY_NAME}-deploy-plan-ready", True, "plan-only; no live command executed", "run V831 helper deploy preflight"
    blockers = deploy.blocking_checks(
        checks,
        ignore_deploy=args.command == "preflight" or (args.command == "run" and deploy.approved(args)),
    )
    if blockers:
        return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
    if args.command == "preflight":
        return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready", True, "preflight complete; deploy still requires exact approval", "run approved V831 helper v128 deploy"
    if not deploy.approved(args):
        return f"{deploy.DEPLOY_NAME}-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact V831 deploy phrase"
    if deploy_result and not deploy_result["ok"]:
        return f"{deploy.DEPLOY_NAME}-deploy-failed", False, "install command failed", "inspect install transcript and retry after cleanup"
    if v831_result and v831_result.get("decision") != "v831-service-notifier-early-listener-plan-ready":
        return (
            f"{deploy.DEPLOY_NAME}-deploy-postflight-review",
            False,
            f"V831 plan decision={v831_result.get('decision')}",
            "inspect helper v128 post-deploy V831 plan output",
        )
    return f"{deploy.DEPLOY_NAME}-deploy-pass", True, "helper v128 deployed or already current; V831 plan was rerun", "run V831 bounded early service-notifier listener probe"


deploy.run_v373_preflight = run_v831_plan
deploy.decide = decide


if __name__ == "__main__":
    raise SystemExit(deploy.main())
