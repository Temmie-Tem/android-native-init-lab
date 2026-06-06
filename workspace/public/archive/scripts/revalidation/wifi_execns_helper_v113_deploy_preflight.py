#!/usr/bin/env python3
"""V687 execns helper v113 deploy/preflight wrapper."""

from __future__ import annotations

import sys

import wifi_execns_helper_v112_deploy_preflight as v112


deploy = v112.deploy
deploy.__doc__ = __doc__
deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v687-execns-helper-v113-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v686-execns-helper-v113-build/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "60ed7a14d3b33b2f700fb644fd1ccd7a037ac8d9c50db082fa0dea7646965ce9"
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.67 (v641)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1850
deploy.HELPER_MARKER = "a90_android_execns_probe v113"
deploy.SERVICE_MODE_TOKEN = "wifi-companion-service74-gated-peripheral-manager-cnss-retry-start-only"
deploy.DEPLOY_LABEL = "v113"
deploy.DEPLOY_NAME = "execns-helper-v113"
deploy.DEPLOY_PLAN_VERSION = "V687"
deploy.DEPLOY_LOG_PREFIX = "v687"
deploy.SUMMARY_TITLE = "v687 Execns Helper v113 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v687 deploy execns helper v113 only; "
    "no daemon start and no Wi-Fi bring-up"
)
deploy.V373_SCRIPT = deploy.Path("scripts/revalidation/native_wifi_peripheral_manager_cnss_retry_v687.py")

v112.v111.v110.v109.v108.v107.v106.v105.v103.v102.v101.v100.v99.v98.v97.v96.v95.v94.v93.v92.v91.v90.v89.v88.v87.v86.v85.v84.v83.v82.v81.v80.v79.v78.v77.v76.v66.v62.v61.v60.v59.v58.v57.v56.v33.V33_TOKENS = (
    "a90_android_execns_probe v113",
    "wifi-companion-service74-gated-peripheral-manager-cnss-retry-start-only",
    "wifi_companion_start.peripheral_manager.enabled=%d",
    "wifi_companion_start.peripheral_manager.per_mgr.ready=%d",
    "wifi_companion_start.peripheral_manager.per_proxy.ready=%d",
    "/vendor/bin/pm-service",
    "/vendor/bin/pm-proxy",
    "wifi_companion_start.supplicant=0",
    "wifi_companion_start.scan_connect_linkup=0",
    "wifi_companion_start.external_ping=0",
)


def run_v687_preflight(args: deploy.argparse.Namespace, store: deploy.EvidenceStore) -> dict[str, object]:
    out_dir = store.path("v687-helper-v113-peripheral-manager-preflight")
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
    store.write_text("host/v687-helper-v113-peripheral-manager-preflight.txt", output)
    manifest_path = out_dir / "manifest.json"
    manifest: dict[str, object] = {}
    if manifest_path.exists():
        manifest = deploy.json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        "command": " ".join(command),
        "rc": rc,
        "ok": rc == 0,
        "file": "host/v687-helper-v113-peripheral-manager-preflight.txt",
        "manifest": str(manifest_path),
        "decision": manifest.get("decision", "missing"),
        "pass": manifest.get("pass", False),
    }


def decide(args: deploy.argparse.Namespace,
           checks: list[deploy.Check],
           deploy_result: dict[str, object] | None,
           v687_result: dict[str, object] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return f"{deploy.DEPLOY_NAME}-deploy-plan-ready", True, "plan-only; no live command executed", "run V687 helper deploy preflight"
    if args.command == "preflight":
        blockers = deploy.blocking_checks(checks, ignore_deploy=True)
        if blockers:
            return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
        deploy_needed = any(check.severity == "deploy" and check.status != "pass" for check in checks)
        next_step = "deploy helper v113, then run V687 PeripheralManager/CNSS retry proof" if deploy_needed else "run V687 PeripheralManager/CNSS retry proof"
        return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready", True, "preflight complete; helper v113 deploy still requires exact approval", next_step
    blockers = deploy.blocking_checks(checks, ignore_deploy=deploy.approved(args))
    if blockers:
        return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
    if not deploy.approved(args):
        return f"{deploy.DEPLOY_NAME}-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact V687 deploy phrase"
    if deploy_result and not deploy_result["ok"]:
        return f"{deploy.DEPLOY_NAME}-deploy-failed", False, "install command failed", "inspect install transcript and retry after cleanup"
    if v687_result and v687_result.get("decision") not in {
        "v687-peripheral-manager-cnss-retry-preflight-ready",
        "v687-peripheral-manager-cnss-retry-blocked",
    }:
        return f"{deploy.DEPLOY_NAME}-deploy-postflight-review", False, f"helper v113 post-deploy preflight decision={v687_result.get('decision')}", "inspect helper v113 post-deploy preflight output"
    return f"{deploy.DEPLOY_NAME}-deploy-pass", True, "helper v113 deployed or already current; post-deploy V687 preflight was rerun", "run V687 PeripheralManager/CNSS retry proof"


deploy.run_v373_preflight = run_v687_preflight
deploy.decide = decide


if __name__ == "__main__":
    raise SystemExit(deploy.main())
