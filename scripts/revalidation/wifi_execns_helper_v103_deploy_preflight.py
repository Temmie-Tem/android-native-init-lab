#!/usr/bin/env python3
"""V609 execns helper v103 deploy/preflight wrapper."""

from __future__ import annotations

import sys

import wifi_execns_helper_v102_deploy_preflight as v102


deploy = v102.deploy
deploy.__doc__ = __doc__
deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v609-execns-helper-v103-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v609-execns-helper-v103-build/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "a63758a4cd10a4d0b227e2b85516ecc65575cca30fe863d332b802fabae4f57e"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1850
deploy.HELPER_MARKER = "a90_android_execns_probe v103"
deploy.SERVICE_MODE_TOKEN = "wifi-companion-post-sysmon-observer-start-only"
deploy.DEPLOY_LABEL = "v103"
deploy.DEPLOY_NAME = "execns-helper-v103"
deploy.DEPLOY_PLAN_VERSION = "V609"
deploy.DEPLOY_LOG_PREFIX = "v609"
deploy.SUMMARY_TITLE = "v609 Execns Helper v103 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v609 deploy execns helper v103 only; "
    "no daemon start and no Wi-Fi bring-up"
)
deploy.V373_SCRIPT = deploy.Path("scripts/revalidation/native_wifi_post_sysmon_observer_v609.py")

v102.v101.v100.v99.v98.v97.v96.v95.v94.v93.v92.v91.v90.v89.v88.v87.v86.v85.v84.v83.v82.v81.v80.v79.v78.v77.v76.v66.v62.v61.v60.v59.v58.v57.v56.v33.V33_TOKENS = (
    "a90_android_execns_probe v103",
    "wifi-companion-post-sysmon-observer-start-only",
    "wifi_companion_start.order=%s",
    "qrtr_ns,rmt_storage,tftp_server,pd_mapper",
    "wifi_companion_start.scan_connect_linkup=0",
    "wifi_companion_start.external_ping=0",
)


def run_v609_preflight(args: deploy.argparse.Namespace, store: deploy.EvidenceStore) -> dict[str, object]:
    out_dir = store.path("v609-helper-v103-observer-preflight")
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
    store.write_text("host/v609-helper-v103-observer-preflight.txt", output)
    manifest_path = out_dir / "manifest.json"
    manifest: dict[str, object] = {}
    if manifest_path.exists():
        manifest = deploy.json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        "command": " ".join(command),
        "rc": rc,
        "ok": rc == 0,
        "file": "host/v609-helper-v103-observer-preflight.txt",
        "manifest": str(manifest_path),
        "decision": manifest.get("decision", "missing"),
        "pass": manifest.get("pass", False),
    }


def decide(args: deploy.argparse.Namespace,
           checks: list[deploy.Check],
           deploy_result: dict[str, object] | None,
           v609_result: dict[str, object] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return f"{deploy.DEPLOY_NAME}-deploy-plan-ready", True, "plan-only; no live command executed", "run V609 helper deploy preflight"
    if args.command == "preflight":
        blockers = deploy.blocking_checks(checks, ignore_deploy=True)
        if blockers:
            return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
        deploy_needed = any(check.severity == "deploy" and check.status != "pass" for check in checks)
        next_step = "deploy helper v103, then run post-sysmon observer proof" if deploy_needed else "run post-sysmon observer proof"
        return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready", True, "preflight complete; helper v103 deploy still requires exact approval", next_step
    blockers = deploy.blocking_checks(checks, ignore_deploy=deploy.approved(args))
    if blockers:
        return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
    if not deploy.approved(args):
        return f"{deploy.DEPLOY_NAME}-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact V609 deploy phrase"
    if deploy_result and not deploy_result["ok"]:
        return f"{deploy.DEPLOY_NAME}-deploy-failed", False, "install command failed", "inspect install transcript and retry after cleanup"
    if v609_result and v609_result.get("decision") != "v609-post-sysmon-observer-preflight-ready":
        return f"{deploy.DEPLOY_NAME}-deploy-postflight-review", False, f"helper v103 post-deploy preflight decision={v609_result.get('decision')}", "inspect helper v103 post-deploy preflight output"
    return f"{deploy.DEPLOY_NAME}-deploy-pass", True, "helper v103 deployed or already current; post-deploy observer preflight was rerun", "run post-sysmon observer proof"


deploy.run_v373_preflight = run_v609_preflight
deploy.decide = decide


if __name__ == "__main__":
    raise SystemExit(deploy.main())
