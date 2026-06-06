#!/usr/bin/env python3
"""V592 execns helper v100 deploy/preflight wrapper."""

from __future__ import annotations

import sys

import wifi_execns_helper_v99_deploy_preflight as v99


deploy = v99.deploy
deploy.__doc__ = __doc__
deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v592-execns-helper-v100-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v592-a90_android_execns_probe-v100/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "916b5c68a3357c79604db4532b457e30fcb9a70c99aaabb6f95519af138abd29"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1850
deploy.HELPER_MARKER = "a90_android_execns_probe v100"
deploy.SERVICE_MODE_TOKEN = "subsys-hold-open-proof"
deploy.DEPLOY_LABEL = "v100"
deploy.DEPLOY_NAME = "execns-helper-v100"
deploy.DEPLOY_PLAN_VERSION = "V592"
deploy.DEPLOY_LOG_PREFIX = "v592"
deploy.SUMMARY_TITLE = "v592 Execns Helper v100 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v592 deploy execns helper v100 only; "
    "no daemon start and no Wi-Fi bring-up"
)
deploy.V373_SCRIPT = deploy.Path("scripts/revalidation/native_wifi_subsys_hold_open_v592.py")

v99.v98.v97.v96.v95.v94.v93.v92.v91.v90.v89.v88.v87.v86.v85.v84.v83.v82.v81.v80.v79.v78.v77.v76.v66.v62.v61.v60.v59.v58.v57.v56.v33.V33_TOKENS = (
    "a90_android_execns_probe v100",
    "subsys-hold-open-proof",
    "wifi_companion_start.mode=subsys-hold-open-proof",
    "wifi_companion_start.subsys_hold.%s_node_ready=1",
    "wifi_companion_start.subsys_hold.%s_opened=1",
    "wifi_companion_start.subsys_hold.%s.mss_state=%s",
    "wifi_companion_start.subsys_hold.%s.rpmsg_ipcrtr_present=%d",
    "wifi_companion_start.result=subsys-hold-window-pass",
    "wifi_companion_start.scan_connect_linkup=0",
    "wifi_companion_start.external_ping=0",
)


def run_v592_preflight(args: deploy.argparse.Namespace, store: deploy.EvidenceStore) -> dict[str, object]:
    out_dir = store.path("v592-subsys-hold-open-preflight")
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
    store.write_text("host/v592-subsys-hold-open-preflight.txt", output)
    manifest_path = out_dir / "manifest.json"
    manifest: dict[str, object] = {}
    if manifest_path.exists():
        manifest = deploy.json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        "command": " ".join(command),
        "rc": rc,
        "ok": rc == 0,
        "file": "host/v592-subsys-hold-open-preflight.txt",
        "manifest": str(manifest_path),
        "decision": manifest.get("decision", "missing"),
        "pass": manifest.get("pass", False),
    }


def decide(args: deploy.argparse.Namespace,
           checks: list[deploy.Check],
           deploy_result: dict[str, object] | None,
           v592_result: dict[str, object] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return f"{deploy.DEPLOY_NAME}-deploy-plan-ready", True, "plan-only; no live command executed", "run preflight"
    if args.command == "preflight":
        blockers = deploy.blocking_checks(checks, ignore_deploy=True)
        if blockers:
            return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
        deploy_needed = any(check.severity == "deploy" and check.status != "pass" for check in checks)
        next_step = "deploy helper v100, then run V592 subsystem hold-open proof" if deploy_needed else "run V592 subsystem hold-open proof"
        return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready", True, "preflight complete; helper v100 deploy still requires exact approval", next_step
    blockers = deploy.blocking_checks(checks, ignore_deploy=deploy.approved(args))
    if blockers:
        return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
    if not deploy.approved(args):
        return f"{deploy.DEPLOY_NAME}-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact V592 deploy phrase"
    if deploy_result and not deploy_result["ok"]:
        return f"{deploy.DEPLOY_NAME}-deploy-failed", False, "install command failed", "inspect install transcript and retry after cleanup"
    if v592_result and v592_result.get("decision") != "v592-subsys-hold-open-preflight-ready":
        return f"{deploy.DEPLOY_NAME}-deploy-postflight-review", False, f"V592 preflight decision={v592_result.get('decision')}", "inspect V592 post-deploy preflight output"
    return f"{deploy.DEPLOY_NAME}-deploy-pass", True, "helper v100 deployed or already current; V592 preflight was rerun", "run V592 subsystem hold-open proof"


deploy.run_v373_preflight = run_v592_preflight
deploy.decide = decide


if __name__ == "__main__":
    raise SystemExit(deploy.main())
