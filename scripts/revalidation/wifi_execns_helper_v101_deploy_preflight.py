#!/usr/bin/env python3
"""V603 execns helper v101 deploy/preflight wrapper."""

from __future__ import annotations

import sys

import wifi_execns_helper_v100_deploy_preflight as v100


deploy = v100.deploy
deploy.__doc__ = __doc__
deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v603-execns-helper-v101-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v603-execns-helper-v101-build/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "a2a089110106a9c2eb6b33eb2c5f0c382fb4fda0e0c7f32e80dbabb9dd281372"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1850
deploy.HELPER_MARKER = "a90_android_execns_probe v101"
deploy.SERVICE_MODE_TOKEN = "wifi-companion-qrtr-first-vnd-service-manager-start-only"
deploy.DEPLOY_LABEL = "v101"
deploy.DEPLOY_NAME = "execns-helper-v101"
deploy.DEPLOY_PLAN_VERSION = "V603"
deploy.DEPLOY_LOG_PREFIX = "v603"
deploy.SUMMARY_TITLE = "v603 Execns Helper v101 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v603 deploy execns helper v101 only; "
    "no daemon start and no Wi-Fi bring-up"
)
deploy.V373_SCRIPT = deploy.Path("scripts/revalidation/native_wifi_subsys_hold_open_v592.py")

v100.v99.v98.v97.v96.v95.v94.v93.v92.v91.v90.v89.v88.v87.v86.v85.v84.v83.v82.v81.v80.v79.v78.v77.v76.v66.v62.v61.v60.v59.v58.v57.v56.v33.V33_TOKENS = (
    "a90_android_execns_probe v101",
    "subsys-hold-open-proof",
    "wifi-companion-qrtr-first-vnd-service-manager-start-only",
    "wifi_companion_start.order=%s",
    "qrtr_ns,rmt_storage,tftp_server,pd_mapper,servicemanager,hwservicemanager,vndservicemanager,cnss_diag,cnss_daemon",
    "wifi_companion_start.scan_connect_linkup=0",
    "wifi_companion_start.external_ping=0",
)


def run_v603_preflight(args: deploy.argparse.Namespace, store: deploy.EvidenceStore) -> dict[str, object]:
    out_dir = store.path("v603-helper-v101-subsys-hold-preflight")
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
    store.write_text("host/v603-helper-v101-subsys-hold-preflight.txt", output)
    manifest_path = out_dir / "manifest.json"
    manifest: dict[str, object] = {}
    if manifest_path.exists():
        manifest = deploy.json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        "command": " ".join(command),
        "rc": rc,
        "ok": rc == 0,
        "file": "host/v603-helper-v101-subsys-hold-preflight.txt",
        "manifest": str(manifest_path),
        "decision": manifest.get("decision", "missing"),
        "pass": manifest.get("pass", False),
    }


def decide(args: deploy.argparse.Namespace,
           checks: list[deploy.Check],
           deploy_result: dict[str, object] | None,
           v603_result: dict[str, object] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return f"{deploy.DEPLOY_NAME}-deploy-plan-ready", True, "plan-only; no live command executed", "run V603 helper deploy preflight"
    if args.command == "preflight":
        blockers = deploy.blocking_checks(checks, ignore_deploy=True)
        if blockers:
            return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
        deploy_needed = any(check.severity == "deploy" and check.status != "pass" for check in checks)
        next_step = "deploy helper v101, then run qrtr-first service-manager proof" if deploy_needed else "run qrtr-first service-manager proof"
        return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready", True, "preflight complete; helper v101 deploy still requires exact approval", next_step
    blockers = deploy.blocking_checks(checks, ignore_deploy=deploy.approved(args))
    if blockers:
        return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
    if not deploy.approved(args):
        return f"{deploy.DEPLOY_NAME}-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact V603 deploy phrase"
    if deploy_result and not deploy_result["ok"]:
        return f"{deploy.DEPLOY_NAME}-deploy-failed", False, "install command failed", "inspect install transcript and retry after cleanup"
    if v603_result and v603_result.get("decision") != "v592-subsys-hold-open-preflight-ready":
        return f"{deploy.DEPLOY_NAME}-deploy-postflight-review", False, f"helper v101 post-deploy preflight decision={v603_result.get('decision')}", "inspect helper v101 post-deploy preflight output"
    return f"{deploy.DEPLOY_NAME}-deploy-pass", True, "helper v101 deployed or already current; post-deploy helper preflight was rerun", "run qrtr-first service-manager proof"


deploy.run_v373_preflight = run_v603_preflight
deploy.decide = decide


if __name__ == "__main__":
    raise SystemExit(deploy.main())
