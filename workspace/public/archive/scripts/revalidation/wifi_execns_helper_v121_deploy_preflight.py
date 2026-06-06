#!/usr/bin/env python3
"""V712 execns helper v121 deploy/preflight wrapper."""

from __future__ import annotations

import sys

import wifi_execns_helper_v120_deploy_preflight as v120


deploy = v120.deploy
deploy.__doc__ = __doc__
deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v712-execns-helper-v121-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v712-execns-helper-v121-build/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "547232ddb352740bb7a7f1d0f9116162584e34a536b9d9b77869ed8d838e7c89"
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.67 (v641)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1850
deploy.HELPER_MARKER = "a90_android_execns_probe v121"
deploy.SERVICE_MODE_TOKEN = "wifi-companion-service74-gated-peripheral-manager-vndservice-query-provider-first-cnss-start-only"
deploy.DEPLOY_LABEL = "v121"
deploy.DEPLOY_NAME = "execns-helper-v121"
deploy.DEPLOY_PLAN_VERSION = "V712"
deploy.DEPLOY_LOG_PREFIX = "v712"
deploy.SUMMARY_TITLE = "v712 Execns Helper v121 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v712 deploy execns helper v121 only; "
    "no daemon start and no Wi-Fi bring-up"
)
deploy.V373_SCRIPT = deploy.Path("scripts/revalidation/native_wifi_provider_first_icnss_edge_v712.py")

v120.v119.v118.v117.v116.v112.v111.v110.v109.v108.v107.v106.v105.v103.v102.v101.v100.v99.v98.v97.v96.v95.v94.v93.v92.v91.v90.v89.v88.v87.v86.v85.v84.v83.v82.v81.v80.v79.v78.v77.v76.v66.v62.v61.v60.v59.v58.v57.v56.v33.V33_TOKENS = (
    "a90_android_execns_probe v121",
    "wifi-companion-service74-gated-peripheral-manager-vndservice-query-provider-first-cnss-start-only",
    "wifi_companion_start.icnss_edge_%s.begin=1",
    "icnss_driver_link",
    "qca6390_driver_link",
    "wifi_companion_start.cnss2_focus_%s.icnss_edge_captured=1",
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


def run_v712_preflight(args: deploy.argparse.Namespace, store: deploy.EvidenceStore) -> dict[str, object]:
    out_dir = store.path("v712-helper-v121-provider-first-icnss-edge-preflight")
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
    store.write_text("host/v712-helper-v121-provider-first-icnss-edge-preflight.txt", output)
    manifest_path = out_dir / "manifest.json"
    manifest: dict[str, object] = {}
    if manifest_path.exists():
        manifest = deploy.json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        "command": " ".join(command),
        "rc": rc,
        "ok": rc == 0,
        "file": "host/v712-helper-v121-provider-first-icnss-edge-preflight.txt",
        "manifest": str(manifest_path),
        "decision": manifest.get("decision", "missing"),
        "pass": manifest.get("pass", False),
    }


def decide(args: deploy.argparse.Namespace,
           checks: list[deploy.Check],
           deploy_result: dict[str, object] | None,
           v712_result: dict[str, object] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return f"{deploy.DEPLOY_NAME}-deploy-plan-ready", True, "plan-only; no live command executed", "run V712 helper deploy preflight"
    if args.command == "preflight":
        blockers = deploy.blocking_checks(checks, ignore_deploy=True)
        if blockers:
            return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
        deploy_needed = any(check.severity == "deploy" and check.status != "pass" for check in checks)
        next_step = "deploy helper v121, then run V712 provider-first ICNSS edge proof" if deploy_needed else "run V712 provider-first ICNSS edge proof"
        return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready", True, "preflight complete; helper v121 deploy still requires exact approval", next_step
    blockers = deploy.blocking_checks(checks, ignore_deploy=deploy.approved(args))
    if blockers:
        return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
    if not deploy.approved(args):
        return f"{deploy.DEPLOY_NAME}-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact V712 deploy phrase"
    if deploy_result and not deploy_result["ok"]:
        return f"{deploy.DEPLOY_NAME}-deploy-failed", False, "install command failed", "inspect install transcript and retry after cleanup"
    if v712_result and v712_result.get("decision") not in {
        "v712-provider-first-cnss-preflight-ready",
        "v712-provider-first-cnss-blocked",
    }:
        return f"{deploy.DEPLOY_NAME}-deploy-postflight-review", False, f"helper v121 post-deploy preflight decision={v712_result.get('decision')}", "inspect helper v121 post-deploy preflight output"
    return f"{deploy.DEPLOY_NAME}-deploy-pass", True, "helper v121 deployed or already current; post-deploy preflight was rerun", "run V712 provider-first ICNSS edge proof"


deploy.run_v373_preflight = run_v712_preflight
deploy.decide = decide


if __name__ == "__main__":
    raise SystemExit(deploy.main())
