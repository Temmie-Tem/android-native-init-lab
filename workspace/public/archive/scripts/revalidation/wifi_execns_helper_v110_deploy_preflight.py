#!/usr/bin/env python3
"""V668 execns helper v110 deploy/preflight wrapper."""

from __future__ import annotations

import sys

import wifi_execns_helper_v109_deploy_preflight as v109


deploy = v109.deploy
deploy.__doc__ = __doc__
deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v668-execns-helper-v110-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v668-execns-helper-v110-build/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "a9e2d9dd414389f676f3055725c7203a9d47ce708b0abbb60010935074768549"
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.67 (v641)"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1850
deploy.HELPER_MARKER = "a90_android_execns_probe v110"
deploy.SERVICE_MODE_TOKEN = "wifi-companion-service74-gated-vnd-service-manager-cnss-retry-start-only"
deploy.DEPLOY_LABEL = "v110"
deploy.DEPLOY_NAME = "execns-helper-v110"
deploy.DEPLOY_PLAN_VERSION = "V668"
deploy.DEPLOY_LOG_PREFIX = "v668"
deploy.SUMMARY_TITLE = "v668 Execns Helper v110 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v668 deploy execns helper v110 only; "
    "no daemon start and no Wi-Fi bring-up"
)
deploy.V373_SCRIPT = deploy.Path("scripts/revalidation/native_wifi_cnss2_focused_capture_v668.py")

v109.v108.v107.v106.v105.v103.v102.v101.v100.v99.v98.v97.v96.v95.v94.v93.v92.v91.v90.v89.v88.v87.v86.v85.v84.v83.v82.v81.v80.v79.v78.v77.v76.v66.v62.v61.v60.v59.v58.v57.v56.v33.V33_TOKENS = (
    "a90_android_execns_probe v110",
    "wifi_companion_start.cnss2_focus_%s.begin=1",
    "wifi_cnss2_focus_icnss_device",
    "wifi_cnss2_focus_qca6390_device",
    "wifi_cnss2_focus_wlan0",
    "wifi-companion-service74-gated-vnd-service-manager-cnss-retry-start-only",
    "wifi_companion_start.scan_connect_linkup=0",
    "wifi_companion_start.external_ping=0",
)


def run_v668_preflight(args: deploy.argparse.Namespace, store: deploy.EvidenceStore) -> dict[str, object]:
    out_dir = store.path("v668-helper-v110-cnss2-focused-capture-preflight")
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
    store.write_text("host/v668-helper-v110-cnss2-focused-capture-preflight.txt", output)
    manifest_path = out_dir / "manifest.json"
    manifest: dict[str, object] = {}
    if manifest_path.exists():
        manifest = deploy.json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        "command": " ".join(command),
        "rc": rc,
        "ok": rc == 0,
        "file": "host/v668-helper-v110-cnss2-focused-capture-preflight.txt",
        "manifest": str(manifest_path),
        "decision": manifest.get("decision", "missing"),
        "pass": manifest.get("pass", False),
    }


def decide(args: deploy.argparse.Namespace,
           checks: list[deploy.Check],
           deploy_result: dict[str, object] | None,
           v668_result: dict[str, object] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return f"{deploy.DEPLOY_NAME}-deploy-plan-ready", True, "plan-only; no live command executed", "run V668 helper deploy preflight"
    if args.command == "preflight":
        blockers = deploy.blocking_checks(checks, ignore_deploy=True)
        if blockers:
            return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
        deploy_needed = any(check.severity == "deploy" and check.status != "pass" for check in checks)
        next_step = "deploy helper v110, then run cnss2 focused capture proof" if deploy_needed else "run cnss2 focused capture proof"
        return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready", True, "preflight complete; helper v110 deploy still requires exact approval", next_step
    blockers = deploy.blocking_checks(checks, ignore_deploy=deploy.approved(args))
    if blockers:
        return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
    if not deploy.approved(args):
        return f"{deploy.DEPLOY_NAME}-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact V668 deploy phrase"
    if deploy_result and not deploy_result["ok"]:
        return f"{deploy.DEPLOY_NAME}-deploy-failed", False, "install command failed", "inspect install transcript and retry after cleanup"
    if v668_result and v668_result.get("decision") not in {
        "v668-cnss2-focused-capture-preflight-ready",
        "v668-cnss2-focused-capture-blocked",
    }:
        return f"{deploy.DEPLOY_NAME}-deploy-postflight-review", False, f"helper v110 post-deploy preflight decision={v668_result.get('decision')}", "inspect helper v110 post-deploy preflight output"
    return f"{deploy.DEPLOY_NAME}-deploy-pass", True, "helper v110 deployed or already current; post-deploy V668 preflight was rerun", "run cnss2 focused capture proof"


deploy.run_v373_preflight = run_v668_preflight
deploy.decide = decide


if __name__ == "__main__":
    raise SystemExit(deploy.main())
