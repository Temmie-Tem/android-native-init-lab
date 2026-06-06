#!/usr/bin/env python3
"""V821 execns helper v125 deploy/preflight wrapper."""

from __future__ import annotations

import sys

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v821-execns-helper-v125-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v821-execns-helper-v125-build/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "49194d47fc251d3201f6af65ff78909087f4734584383f1d600a5daab29d30da"
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1850
deploy.HELPER_MARKER = "a90_android_execns_probe v125"
deploy.SERVICE_MODE_TOKEN = "--qrtr-readback-matrix"
deploy.DEPLOY_LABEL = "v125"
deploy.DEPLOY_NAME = "execns-helper-v125"
deploy.DEPLOY_PLAN_VERSION = "V821"
deploy.DEPLOY_LOG_PREFIX = "v821"
deploy.SUMMARY_TITLE = "v821 Execns Helper v125 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v821 deploy execns helper v125 only; "
    "no daemon start and no Wi-Fi bring-up"
)

V821_SCRIPT = deploy.Path("scripts/revalidation/native_wifi_qrtr_nameservice_matrix_v821.py")


def run_v821_plan(args: deploy.argparse.Namespace, store: deploy.EvidenceStore) -> dict[str, object]:
    out_dir = store.path("v821-helper-v125-nameservice-plan")
    command = [
        sys.executable,
        str(deploy.repo_path(V821_SCRIPT)),
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
        "plan",
    ]
    rc, output = deploy.run_host(command, timeout=180)
    store.write_text("host/v821-helper-v125-nameservice-plan.txt", output)
    manifest_path = out_dir / "manifest.json"
    manifest: dict[str, object] = {}
    if manifest_path.exists():
        manifest = deploy.json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        "command": " ".join(command),
        "rc": rc,
        "ok": rc == 0,
        "file": "host/v821-helper-v125-nameservice-plan.txt",
        "manifest": str(manifest_path),
        "decision": manifest.get("decision", "missing"),
        "pass": manifest.get("pass", False),
    }


def decide(args: deploy.argparse.Namespace,
           checks: list[deploy.Check],
           deploy_result: dict[str, object] | None,
           v821_result: dict[str, object] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return f"{deploy.DEPLOY_NAME}-deploy-plan-ready", True, "plan-only; no live command executed", "run V821 helper deploy preflight"
    blockers = deploy.blocking_checks(
        checks,
        ignore_deploy=args.command == "preflight" or (args.command == "run" and deploy.approved(args)),
    )
    if blockers:
        return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
    if args.command == "preflight":
        return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready", True, "preflight complete; deploy still requires exact approval", "run approved V821 helper v125 deploy"
    if not deploy.approved(args):
        return f"{deploy.DEPLOY_NAME}-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact V821 deploy phrase"
    if deploy_result and not deploy_result["ok"]:
        return f"{deploy.DEPLOY_NAME}-deploy-failed", False, "install command failed", "inspect install transcript and retry after cleanup"
    if v821_result and v821_result.get("decision") != "v821-qrtr-nameservice-matrix-plan-ready":
        return (
            f"{deploy.DEPLOY_NAME}-deploy-postflight-review",
            False,
            f"V821 plan decision={v821_result.get('decision')}",
            "inspect helper v125 post-deploy V821 plan output",
        )
    return f"{deploy.DEPLOY_NAME}-deploy-pass", True, "helper v125 deployed or already current; V821 plan was rerun", "run V821 nameservice matrix live gate"


deploy.run_v373_preflight = run_v821_plan
deploy.decide = decide


if __name__ == "__main__":
    raise SystemExit(deploy.main())
