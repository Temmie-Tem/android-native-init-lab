#!/usr/bin/env python3
"""V705 execns helper v120 deploy/preflight wrapper."""

from __future__ import annotations

import sys

import wifi_execns_helper_v119_deploy_preflight as v119


deploy = v119.deploy
deploy.__doc__ = __doc__
deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v705-execns-helper-v120-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v705-execns-helper-v120-build/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "acc43d21f948c88350099e1a652a26c7a5f4f0352e06396c6d30dd6908d1ba28"
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.67 (v641)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1850
deploy.HELPER_MARKER = "a90_android_execns_probe v120"
deploy.SERVICE_MODE_TOKEN = "wifi-companion-service74-gated-peripheral-manager-vndservice-query-provider-first-cnss-start-only"
deploy.DEPLOY_LABEL = "v120"
deploy.DEPLOY_NAME = "execns-helper-v120"
deploy.DEPLOY_PLAN_VERSION = "V705"
deploy.DEPLOY_LOG_PREFIX = "v705"
deploy.SUMMARY_TITLE = "v705 Execns Helper v120 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v705 deploy execns helper v120 only; "
    "no daemon start and no Wi-Fi bring-up"
)
deploy.V373_SCRIPT = deploy.Path("scripts/revalidation/native_wifi_provider_first_cnss_v700.py")

v119.v118.v117.v116.v112.v111.v110.v109.v108.v107.v106.v105.v103.v102.v101.v100.v99.v98.v97.v96.v95.v94.v93.v92.v91.v90.v89.v88.v87.v86.v85.v84.v83.v82.v81.v80.v79.v78.v77.v76.v66.v62.v61.v60.v59.v58.v57.v56.v33.V33_TOKENS = (
    "a90_android_execns_probe v120",
    "wifi-companion-service74-gated-peripheral-manager-vndservice-query-provider-first-cnss-start-only",
    "capture.%s.stall_snapshot.begin=1",
    "capture.%s.stall_snapshot.syscall_captured=%d",
    "capture.%s.stall_tasks.begin=1",
    "wifi_companion_start.child.%s.stall_snapshot_captured=%d",
    "wifi_vndservice_query.%s.tool=/vendor/bin/vndservice",
    "wifi_companion_start.initial_cnss_daemon.suppressed=%d",
    "wifi_companion_start.vndservice_query.enabled=%d",
    "wifi_companion_start.cnss_retry.enabled=%d",
    "wifi_companion_start.child.%s.start_order=%zu",
    "/vendor/bin/vndservice",
    "/vendor/bin/pm-service",
    "/vendor/bin/pm-proxy",
    "/vendor/bin/cnss-daemon",
    "wifi_companion_start.supplicant=0",
    "wifi_companion_start.scan_connect_linkup=0",
    "wifi_companion_start.external_ping=0",
)


def run_v705_preflight(args: deploy.argparse.Namespace, store: deploy.EvidenceStore) -> dict[str, object]:
    out_dir = store.path("v705-helper-v120-provider-first-cnss-preflight")
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
    store.write_text("host/v705-helper-v120-provider-first-cnss-preflight.txt", output)
    manifest_path = out_dir / "manifest.json"
    manifest: dict[str, object] = {}
    if manifest_path.exists():
        manifest = deploy.json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        "command": " ".join(command),
        "rc": rc,
        "ok": rc == 0,
        "file": "host/v705-helper-v120-provider-first-cnss-preflight.txt",
        "manifest": str(manifest_path),
        "decision": manifest.get("decision", "missing"),
        "pass": manifest.get("pass", False),
    }


def decide(args: deploy.argparse.Namespace,
           checks: list[deploy.Check],
           deploy_result: dict[str, object] | None,
           v705_result: dict[str, object] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return f"{deploy.DEPLOY_NAME}-deploy-plan-ready", True, "plan-only; no live command executed", "run V705 helper deploy preflight"
    if args.command == "preflight":
        blockers = deploy.blocking_checks(checks, ignore_deploy=True)
        if blockers:
            return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
        deploy_needed = any(check.severity == "deploy" and check.status != "pass" for check in checks)
        next_step = "deploy helper v120, then run provider-first CNSS stall capture proof" if deploy_needed else "run provider-first CNSS stall capture proof"
        return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready", True, "preflight complete; helper v120 deploy still requires exact approval", next_step
    blockers = deploy.blocking_checks(checks, ignore_deploy=deploy.approved(args))
    if blockers:
        return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
    if not deploy.approved(args):
        return f"{deploy.DEPLOY_NAME}-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact V705 deploy phrase"
    if deploy_result and not deploy_result["ok"]:
        return f"{deploy.DEPLOY_NAME}-deploy-failed", False, "install command failed", "inspect install transcript and retry after cleanup"
    if v705_result and v705_result.get("decision") not in {
        "v700-provider-first-cnss-preflight-ready",
        "v700-provider-first-cnss-blocked",
    }:
        return f"{deploy.DEPLOY_NAME}-deploy-postflight-review", False, f"helper v120 post-deploy preflight decision={v705_result.get('decision')}", "inspect helper v120 post-deploy preflight output"
    return f"{deploy.DEPLOY_NAME}-deploy-pass", True, "helper v120 deployed or already current; post-deploy preflight was rerun", "run provider-first CNSS stall capture proof"


deploy.run_v373_preflight = run_v705_preflight
deploy.decide = decide


if __name__ == "__main__":
    raise SystemExit(deploy.main())
