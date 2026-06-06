#!/usr/bin/env python3
"""V690 execns helper v115 deploy/preflight wrapper."""

from __future__ import annotations

import sys

import wifi_execns_helper_v112_deploy_preflight as v112


deploy = v112.deploy
deploy.__doc__ = __doc__
deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v690-execns-helper-v115-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v690-execns-helper-v115-build/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "60d8ca3c5e652b4f68c519613f10fb91c582a49cb3187ba301f29d5c7027c2fb"
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.67 (v641)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1850
deploy.HELPER_MARKER = "a90_android_execns_probe v115"
deploy.SERVICE_MODE_TOKEN = "wifi-companion-service74-gated-peripheral-manager-cnss-retry-start-only"
deploy.DEPLOY_LABEL = "v115"
deploy.DEPLOY_NAME = "execns-helper-v115"
deploy.DEPLOY_PLAN_VERSION = "V690"
deploy.DEPLOY_LOG_PREFIX = "v690"
deploy.SUMMARY_TITLE = "v690 Execns Helper v115 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v690 deploy execns helper v115 only; "
    "no daemon start and no Wi-Fi bring-up"
)
deploy.V373_SCRIPT = deploy.Path("scripts/revalidation/native_wifi_peripheral_manager_cnss_retry_v690.py")

v112.v111.v110.v109.v108.v107.v106.v105.v103.v102.v101.v100.v99.v98.v97.v96.v95.v94.v93.v92.v91.v90.v89.v88.v87.v86.v85.v84.v83.v82.v81.v80.v79.v78.v77.v76.v66.v62.v61.v60.v59.v58.v57.v56.v33.V33_TOKENS = (
    "a90_android_execns_probe v115",
    "wifi-companion-service74-gated-peripheral-manager-cnss-retry-start-only",
    "wifi_companion_start.peripheral_manager.enabled=%d",
    "wifi_companion_start.peripheral_manager.per_mgr.ready=%d",
    "wifi_companion_start.peripheral_manager.per_proxy.ready=%d",
    "/vendor/bin/pm-service",
    "/vendor/bin/pm-proxy",
    "wifi_companion_start.supplicant=0",
    "wifi_companion_start.scan_connect_linkup=0",
    "wifi_companion_start.external_ping=0",
    "vendor.peripheral.SDX50M.state",
    "vendor.peripheral.modem.state",
)


def run_v690_preflight(args: deploy.argparse.Namespace, store: deploy.EvidenceStore) -> dict[str, object]:
    out_dir = store.path("v690-helper-v115-peripheral-manager-preflight")
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
    store.write_text("host/v690-helper-v115-peripheral-manager-preflight.txt", output)
    manifest_path = out_dir / "manifest.json"
    manifest: dict[str, object] = {}
    if manifest_path.exists():
        manifest = deploy.json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        "command": " ".join(command),
        "rc": rc,
        "ok": rc == 0,
        "file": "host/v690-helper-v115-peripheral-manager-preflight.txt",
        "manifest": str(manifest_path),
        "decision": manifest.get("decision", "missing"),
        "pass": manifest.get("pass", False),
    }


def decide(args: deploy.argparse.Namespace,
           checks: list[deploy.Check],
           deploy_result: dict[str, object] | None,
           v690_result: dict[str, object] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return f"{deploy.DEPLOY_NAME}-deploy-plan-ready", True, "plan-only; no live command executed", "run V690 helper deploy preflight"
    if args.command == "preflight":
        blockers = deploy.blocking_checks(checks, ignore_deploy=True)
        if blockers:
            return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
        deploy_needed = any(check.severity == "deploy" and check.status != "pass" for check in checks)
        next_step = "deploy helper v115, then run V690 PeripheralManager/CNSS retry proof" if deploy_needed else "run V690 PeripheralManager/CNSS retry proof"
        return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready", True, "preflight complete; helper v115 deploy still requires exact approval", next_step
    blockers = deploy.blocking_checks(checks, ignore_deploy=deploy.approved(args))
    if blockers:
        return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
    if not deploy.approved(args):
        return f"{deploy.DEPLOY_NAME}-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact V690 deploy phrase"
    if deploy_result and not deploy_result["ok"]:
        return f"{deploy.DEPLOY_NAME}-deploy-failed", False, "install command failed", "inspect install transcript and retry after cleanup"
    if v690_result and v690_result.get("decision") not in {
        "v690-peripheral-manager-cnss-retry-preflight-ready",
        "v690-peripheral-manager-cnss-retry-blocked",
    }:
        return f"{deploy.DEPLOY_NAME}-deploy-postflight-review", False, f"helper v115 post-deploy preflight decision={v690_result.get('decision')}", "inspect helper v115 post-deploy preflight output"
    return f"{deploy.DEPLOY_NAME}-deploy-pass", True, "helper v115 deployed or already current; post-deploy V690 preflight was rerun", "run V690 PeripheralManager/CNSS retry proof"


deploy.run_v373_preflight = run_v690_preflight
deploy.decide = decide


if __name__ == "__main__":
    raise SystemExit(deploy.main())
