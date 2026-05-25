#!/usr/bin/env python3
"""V837 execns helper v129 deploy/preflight wrapper."""

from __future__ import annotations

import sys

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v837-execns-helper-v129-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v837-execns-helper-v129-build/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "d701affac6d4c57569d8f8a9024e3b4d58b57d7c4b1d825544a11398959a0cec"
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.68 (v724)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1850
deploy.HELPER_MARKER = "a90_android_execns_probe v129"
deploy.SERVICE_MODE_TOKEN = "wifi_companion_service_notifier_listener.timing.close_ms"
deploy.DEPLOY_LABEL = "v129"
deploy.DEPLOY_NAME = "execns-helper-v129"
deploy.DEPLOY_PLAN_VERSION = "V837"
deploy.DEPLOY_LOG_PREFIX = "v837"
deploy.SUMMARY_TITLE = "v837 Execns Helper v129 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v837 deploy execns helper v129 only; "
    "no daemon start and no Wi-Fi bring-up"
)

V837_SCRIPT = deploy.Path("scripts/revalidation/native_wifi_timestamped_servnotif_hold_v837.py")


def run_v837_plan(args: deploy.argparse.Namespace, store: deploy.EvidenceStore) -> dict[str, object]:
    out_dir = store.path("v837-timestamped-servnotif-hold-plan")
    command = [
        sys.executable,
        str(deploy.repo_path(V837_SCRIPT)),
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
    store.write_text("host/v837-timestamped-servnotif-hold-plan.txt", output)
    manifest_path = out_dir / "manifest.json"
    manifest: dict[str, object] = {}
    if manifest_path.exists():
        manifest = deploy.json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        "command": " ".join(command),
        "rc": rc,
        "ok": rc == 0,
        "file": "host/v837-timestamped-servnotif-hold-plan.txt",
        "manifest": str(manifest_path),
        "decision": manifest.get("decision", "missing"),
        "pass": manifest.get("pass", False),
    }


def decide(args: deploy.argparse.Namespace,
           checks: list[deploy.Check],
           deploy_result: dict[str, object] | None,
           v837_result: dict[str, object] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return f"{deploy.DEPLOY_NAME}-deploy-plan-ready", True, "plan-only; no live command executed", "run V837 helper deploy preflight"
    blockers = deploy.blocking_checks(
        checks,
        ignore_deploy=args.command == "preflight" or (args.command == "run" and deploy.approved(args)),
    )
    if blockers:
        return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
    if args.command == "preflight":
        return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready", True, "preflight complete; deploy still requires exact approval", "run approved V837 helper v129 deploy"
    if not deploy.approved(args):
        return f"{deploy.DEPLOY_NAME}-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact V837 deploy phrase"
    if deploy_result and not deploy_result["ok"]:
        return f"{deploy.DEPLOY_NAME}-deploy-failed", False, "install command failed", "inspect install transcript and retry after cleanup"
    if v837_result and v837_result.get("decision") != "v837-timestamped-servnotif-hold-plan-ready":
        return (
            f"{deploy.DEPLOY_NAME}-deploy-postflight-review",
            False,
            f"V837 plan decision={v837_result.get('decision')}",
            "inspect helper v129 post-deploy V837 plan output",
        )
    return f"{deploy.DEPLOY_NAME}-deploy-pass", True, "helper v129 deployed or already current; V837 plan was rerun", "run V837 bounded timestamped listener hold"


deploy.run_v373_preflight = run_v837_plan
deploy.decide = decide


if __name__ == "__main__":
    raise SystemExit(deploy.main())
