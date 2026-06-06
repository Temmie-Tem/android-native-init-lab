#!/usr/bin/env python3
"""V665 execns helper v109 deploy/preflight wrapper."""

from __future__ import annotations

import sys

import wifi_execns_helper_v108_deploy_preflight as v108


deploy = v108.deploy
deploy.__doc__ = __doc__
deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v665-execns-helper-v109-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v665-execns-helper-v109-build/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "eda3e88405d15cfa2b12ef3252cef3ff25ba23aae69aeb5075700fa147150030"
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.67 (v641)"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1850
deploy.HELPER_MARKER = "a90_android_execns_probe v109"
deploy.SERVICE_MODE_TOKEN = "wifi-companion-service74-gated-vnd-service-manager-registry-snapshot-start-only"
deploy.DEPLOY_LABEL = "v109"
deploy.DEPLOY_NAME = "execns-helper-v109"
deploy.DEPLOY_PLAN_VERSION = "V665"
deploy.DEPLOY_LOG_PREFIX = "v665"
deploy.SUMMARY_TITLE = "v665 Execns Helper v109 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v665 deploy execns helper v109 only; "
    "no daemon start and no Wi-Fi bring-up"
)
deploy.V373_SCRIPT = deploy.Path("scripts/revalidation/native_wifi_private_registry_snapshot_path_repair_v665.py")

v108.v107.v106.v105.v103.v102.v101.v100.v99.v98.v97.v96.v95.v94.v93.v92.v91.v90.v89.v88.v87.v86.v85.v84.v83.v82.v81.v80.v79.v78.v77.v76.v66.v62.v61.v60.v59.v58.v57.v56.v33.V33_TOKENS = (
    "a90_android_execns_probe v109",
    "wifi-companion-service74-gated-vnd-service-manager-registry-snapshot-start-only",
    "wifi_registry_snapshot.%s.begin=1",
    "wifi_registry_snapshot.%s.dev_properties_capture_path=%s",
    "wifi_registry_snapshot.%s.dev_socket_capture_path=%s",
    "wifi_registry_snapshot.%s.end=1",
    "wifi_companion_start.registry_snapshot.enabled=%d",
    "wifi_companion_start.scan_connect_linkup=0",
    "wifi_companion_start.external_ping=0",
)


def run_v665_preflight(args: deploy.argparse.Namespace, store: deploy.EvidenceStore) -> dict[str, object]:
    out_dir = store.path("v665-helper-v109-private-registry-snapshot-path-repair-preflight")
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
    store.write_text("host/v665-helper-v109-private-registry-snapshot-path-repair-preflight.txt", output)
    manifest_path = out_dir / "manifest.json"
    manifest: dict[str, object] = {}
    if manifest_path.exists():
        manifest = deploy.json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        "command": " ".join(command),
        "rc": rc,
        "ok": rc == 0,
        "file": "host/v665-helper-v109-private-registry-snapshot-path-repair-preflight.txt",
        "manifest": str(manifest_path),
        "decision": manifest.get("decision", "missing"),
        "pass": manifest.get("pass", False),
    }


def decide(args: deploy.argparse.Namespace,
           checks: list[deploy.Check],
           deploy_result: dict[str, object] | None,
           v665_result: dict[str, object] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return f"{deploy.DEPLOY_NAME}-deploy-plan-ready", True, "plan-only; no live command executed", "run V665 helper deploy preflight"
    if args.command == "preflight":
        blockers = deploy.blocking_checks(checks, ignore_deploy=True)
        if blockers:
            return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
        deploy_needed = any(check.severity == "deploy" and check.status != "pass" for check in checks)
        next_step = "deploy helper v109, then run private registry snapshot path repair proof" if deploy_needed else "run private registry snapshot path repair proof"
        return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready", True, "preflight complete; helper v109 deploy still requires exact approval", next_step
    blockers = deploy.blocking_checks(checks, ignore_deploy=deploy.approved(args))
    if blockers:
        return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
    if not deploy.approved(args):
        return f"{deploy.DEPLOY_NAME}-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact V665 deploy phrase"
    if deploy_result and not deploy_result["ok"]:
        return f"{deploy.DEPLOY_NAME}-deploy-failed", False, "install command failed", "inspect install transcript and retry after cleanup"
    if v665_result and v665_result.get("decision") != "v665-private-registry-snapshot-path-repair-preflight-ready":
        return f"{deploy.DEPLOY_NAME}-deploy-postflight-review", False, f"helper v109 post-deploy preflight decision={v665_result.get('decision')}", "inspect helper v109 post-deploy preflight output"
    return f"{deploy.DEPLOY_NAME}-deploy-pass", True, "helper v109 deployed or already current; post-deploy V665 preflight was rerun", "run private registry snapshot path repair proof"


deploy.run_v373_preflight = run_v665_preflight
deploy.decide = decide


if __name__ == "__main__":
    raise SystemExit(deploy.main())
