#!/usr/bin/env python3
"""V659 execns helper v107 deploy/preflight wrapper."""

from __future__ import annotations

import sys

import wifi_execns_helper_v106_deploy_preflight as v106


deploy = v106.deploy
deploy.__doc__ = __doc__
deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v659-execns-helper-v107-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v659-execns-helper-v107-build/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "67776f512c47eb048147c312d5a0a618ff30b4a3bbab7e60af790ce727940995"
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.67 (v641)"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1850
deploy.HELPER_MARKER = "a90_android_execns_probe v107"
deploy.SERVICE_MODE_TOKEN = "wifi-companion-service74-gated-vnd-service-manager-readiness-start-only"
deploy.DEPLOY_LABEL = "v107"
deploy.DEPLOY_NAME = "execns-helper-v107"
deploy.DEPLOY_PLAN_VERSION = "V659"
deploy.DEPLOY_LOG_PREFIX = "v659"
deploy.SUMMARY_TITLE = "v659 Execns Helper v107 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v659 deploy execns helper v107 only; "
    "no daemon start and no Wi-Fi bring-up"
)
deploy.V373_SCRIPT = deploy.Path("scripts/revalidation/native_wifi_vndservicemanager_readiness_only_v659.py")

v106.v105.v103.v102.v101.v100.v99.v98.v97.v96.v95.v94.v93.v92.v91.v90.v89.v88.v87.v86.v85.v84.v83.v82.v81.v80.v79.v78.v77.v76.v66.v62.v61.v60.v59.v58.v57.v56.v33.V33_TOKENS = (
    "a90_android_execns_probe v107",
    "wifi-companion-service74-gated-vnd-service-manager-readiness-start-only",
    "wifi_companion_start.order=%s",
    "qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon,service74_gate,servicemanager,hwservicemanager,vndservicemanager,vndservicemanager_ready",
    "wifi_companion_start.vndservicemanager_readiness.ready=%d",
    "wifi_companion_start.initial_cnss_daemon.cleanup_safe=%d",
    "wifi_companion_start.cnss_retry.enabled=%d",
    "wifi_companion_start.scan_connect_linkup=0",
    "wifi_companion_start.external_ping=0",
)


def run_v659_preflight(args: deploy.argparse.Namespace, store: deploy.EvidenceStore) -> dict[str, object]:
    out_dir = store.path("v659-helper-v107-vndservicemanager-readiness-only-preflight")
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
        "--helper-marker",
        deploy.HELPER_MARKER,
        "preflight",
    ]
    rc, output = deploy.run_host(command, timeout=180)
    store.write_text("host/v659-helper-v107-vndservicemanager-readiness-only-preflight.txt", output)
    manifest_path = out_dir / "manifest.json"
    manifest: dict[str, object] = {}
    if manifest_path.exists():
        manifest = deploy.json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        "command": " ".join(command),
        "rc": rc,
        "ok": rc == 0,
        "file": "host/v659-helper-v107-vndservicemanager-readiness-only-preflight.txt",
        "manifest": str(manifest_path),
        "decision": manifest.get("decision", "missing"),
        "pass": manifest.get("pass", False),
    }


def decide(args: deploy.argparse.Namespace,
           checks: list[deploy.Check],
           deploy_result: dict[str, object] | None,
           v659_result: dict[str, object] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return f"{deploy.DEPLOY_NAME}-deploy-plan-ready", True, "plan-only; no live command executed", "run V659 helper deploy preflight"
    if args.command == "preflight":
        blockers = deploy.blocking_checks(checks, ignore_deploy=True)
        if blockers:
            return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
        deploy_needed = any(check.severity == "deploy" and check.status != "pass" for check in checks)
        next_step = "deploy helper v107, then run vndservicemanager-readiness-only proof" if deploy_needed else "run vndservicemanager-readiness-only proof"
        return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready", True, "preflight complete; helper v107 deploy still requires exact approval", next_step
    blockers = deploy.blocking_checks(checks, ignore_deploy=deploy.approved(args))
    if blockers:
        return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
    if not deploy.approved(args):
        return f"{deploy.DEPLOY_NAME}-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact V659 deploy phrase"
    if deploy_result and not deploy_result["ok"]:
        return f"{deploy.DEPLOY_NAME}-deploy-failed", False, "install command failed", "inspect install transcript and retry after cleanup"
    if v659_result and v659_result.get("decision") != "v659-vndservicemanager-readiness-only-preflight-ready":
        return f"{deploy.DEPLOY_NAME}-deploy-postflight-review", False, f"helper v107 post-deploy preflight decision={v659_result.get('decision')}", "inspect helper v107 post-deploy preflight output"
    return f"{deploy.DEPLOY_NAME}-deploy-pass", True, "helper v107 deployed or already current; post-deploy V659 preflight was rerun", "run vndservicemanager-readiness-only proof"


deploy.run_v373_preflight = run_v659_preflight
deploy.decide = decide


if __name__ == "__main__":
    raise SystemExit(deploy.main())
