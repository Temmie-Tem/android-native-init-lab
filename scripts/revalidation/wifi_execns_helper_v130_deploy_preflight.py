#!/usr/bin/env python3
"""V838 execns helper v130 deploy/preflight wrapper."""

from __future__ import annotations

import sys

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v838-execns-helper-v130-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v838-execns-helper-v130-build/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "5c605f4b848f7d4897091d4f0cf901350a34acb685cbc75cea81e9880be8c3df"
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.68 (v724)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1850
deploy.HELPER_MARKER = "a90_android_execns_probe v130"
deploy.SERVICE_MODE_TOKEN = "service-notifier-listener-only"
deploy.DEPLOY_LABEL = "v130"
deploy.DEPLOY_NAME = "execns-helper-v130"
deploy.DEPLOY_PLAN_VERSION = "V838"
deploy.DEPLOY_LOG_PREFIX = "v838"
deploy.SUMMARY_TITLE = "v838 Execns Helper v130 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v838 deploy execns helper v130 only; "
    "no daemon start and no Wi-Fi bring-up"
)

V838_SCRIPT = deploy.Path("scripts/revalidation/native_wifi_concurrent_servnotif_listener_v838.py")


def run_v838_plan(args: deploy.argparse.Namespace, store: deploy.EvidenceStore) -> dict[str, object]:
    out_dir = store.path("v838-concurrent-servnotif-listener-plan")
    command = [
        sys.executable,
        str(deploy.repo_path(V838_SCRIPT)),
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
    store.write_text("host/v838-concurrent-servnotif-listener-plan.txt", output)
    manifest_path = out_dir / "manifest.json"
    manifest: dict[str, object] = {}
    if manifest_path.exists():
        manifest = deploy.json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        "command": " ".join(command),
        "rc": rc,
        "ok": rc == 0,
        "file": "host/v838-concurrent-servnotif-listener-plan.txt",
        "manifest": str(manifest_path),
        "decision": manifest.get("decision", "missing"),
        "pass": manifest.get("pass", False),
    }


def decide(args: deploy.argparse.Namespace,
           checks: list[deploy.Check],
           deploy_result: dict[str, object] | None,
           v838_result: dict[str, object] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return f"{deploy.DEPLOY_NAME}-deploy-plan-ready", True, "plan-only; no live command executed", "run V838 helper deploy preflight"
    blockers = deploy.blocking_checks(
        checks,
        ignore_deploy=args.command == "preflight" or (args.command == "run" and deploy.approved(args)),
    )
    if blockers:
        return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
    if args.command == "preflight":
        return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready", True, "preflight complete; deploy still requires exact approval", "run approved V838 helper v130 deploy"
    if not deploy.approved(args):
        return f"{deploy.DEPLOY_NAME}-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact V838 deploy phrase"
    if deploy_result and not deploy_result["ok"]:
        return f"{deploy.DEPLOY_NAME}-deploy-failed", False, "install command failed", "inspect install transcript and retry after cleanup"
    if v838_result and v838_result.get("decision") != "v838-concurrent-servnotif-listener-plan-ready":
        return (
            f"{deploy.DEPLOY_NAME}-deploy-postflight-review",
            False,
            f"V838 plan decision={v838_result.get('decision')}",
            "inspect helper v130 post-deploy V838 plan output",
        )
    return f"{deploy.DEPLOY_NAME}-deploy-pass", True, "helper v130 deployed or already current; V838 plan was rerun", "run V838 concurrent listener proof"


deploy.run_v373_preflight = run_v838_plan
deploy.decide = decide


if __name__ == "__main__":
    raise SystemExit(deploy.main())
