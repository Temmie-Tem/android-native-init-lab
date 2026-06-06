#!/usr/bin/env python3
"""V679 execns helper v112 deploy/preflight wrapper."""

from __future__ import annotations

import sys

import wifi_execns_helper_v111_deploy_preflight as v111


deploy = v111.deploy
deploy.__doc__ = __doc__
deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v679-execns-helper-v112-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v679-execns-helper-v112-build/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "a2c72c4157f6ddf089a40b2a5310288f3f0390ceced1f423519dcb8c1a8cc643"
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.67 (v641)"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1850
deploy.HELPER_MARKER = "a90_android_execns_probe v112"
deploy.SERVICE_MODE_TOKEN = "wifi-companion-service74-gated-android-userspace-cnss-retry-registry-snapshot-start-only"
deploy.DEPLOY_LABEL = "v112"
deploy.DEPLOY_NAME = "execns-helper-v112"
deploy.DEPLOY_PLAN_VERSION = "V679"
deploy.DEPLOY_LOG_PREFIX = "v679"
deploy.SUMMARY_TITLE = "v679 Execns Helper v112 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v679 deploy execns helper v112 only; "
    "no daemon start and no Wi-Fi bring-up"
)
deploy.V373_SCRIPT = deploy.Path("scripts/revalidation/native_wifi_v535_binder_registry_snapshot_v679.py")

v111.v110.v109.v108.v107.v106.v105.v103.v102.v101.v100.v99.v98.v97.v96.v95.v94.v93.v92.v91.v90.v89.v88.v87.v86.v85.v84.v83.v82.v81.v80.v79.v78.v77.v76.v66.v62.v61.v60.v59.v58.v57.v56.v33.V33_TOKENS = (
    "a90_android_execns_probe v112",
    "wifi-companion-service74-gated-android-userspace-cnss-retry-registry-snapshot-start-only",
    "wifi_companion_start.registry_snapshot.enabled=%d",
    "wifi_registry_snapshot.%s.files_captured=%d",
    "after_cnss_retry_spawn",
    "wifi_companion_start.supplicant=0",
    "wifi_companion_start.scan_connect_linkup=0",
    "wifi_companion_start.external_ping=0",
)


def run_v679_preflight(args: deploy.argparse.Namespace, store: deploy.EvidenceStore) -> dict[str, object]:
    out_dir = store.path("v679-helper-v112-binder-registry-snapshot-preflight")
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
    store.write_text("host/v679-helper-v112-binder-registry-snapshot-preflight.txt", output)
    manifest_path = out_dir / "manifest.json"
    manifest: dict[str, object] = {}
    if manifest_path.exists():
        manifest = deploy.json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        "command": " ".join(command),
        "rc": rc,
        "ok": rc == 0,
        "file": "host/v679-helper-v112-binder-registry-snapshot-preflight.txt",
        "manifest": str(manifest_path),
        "decision": manifest.get("decision", "missing"),
        "pass": manifest.get("pass", False),
    }


def decide(args: deploy.argparse.Namespace,
           checks: list[deploy.Check],
           deploy_result: dict[str, object] | None,
           v679_result: dict[str, object] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return f"{deploy.DEPLOY_NAME}-deploy-plan-ready", True, "plan-only; no live command executed", "run V679 helper deploy preflight"
    if args.command == "preflight":
        blockers = deploy.blocking_checks(checks, ignore_deploy=True)
        if blockers:
            return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
        deploy_needed = any(check.severity == "deploy" and check.status != "pass" for check in checks)
        next_step = "deploy helper v112, then run V679 Binder registry snapshot proof" if deploy_needed else "run V679 Binder registry snapshot proof"
        return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready", True, "preflight complete; helper v112 deploy still requires exact approval", next_step
    blockers = deploy.blocking_checks(checks, ignore_deploy=deploy.approved(args))
    if blockers:
        return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
    if not deploy.approved(args):
        return f"{deploy.DEPLOY_NAME}-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact V679 deploy phrase"
    if deploy_result and not deploy_result["ok"]:
        return f"{deploy.DEPLOY_NAME}-deploy-failed", False, "install command failed", "inspect install transcript and retry after cleanup"
    if v679_result and v679_result.get("decision") not in {
        "v679-v535-binder-registry-snapshot-preflight-ready",
        "v679-binder-registry-snapshot-blocked",
    }:
        return f"{deploy.DEPLOY_NAME}-deploy-postflight-review", False, f"helper v112 post-deploy preflight decision={v679_result.get('decision')}", "inspect helper v112 post-deploy preflight output"
    return f"{deploy.DEPLOY_NAME}-deploy-pass", True, "helper v112 deployed or already current; post-deploy V679 preflight was rerun", "run V679 Binder registry snapshot proof"


deploy.run_v373_preflight = run_v679_preflight
deploy.decide = decide


if __name__ == "__main__":
    raise SystemExit(deploy.main())
