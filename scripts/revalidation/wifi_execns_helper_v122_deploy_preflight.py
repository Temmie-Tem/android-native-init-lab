#!/usr/bin/env python3
"""V742 execns helper v122 deploy/preflight wrapper."""

from __future__ import annotations

import sys

import wifi_execns_helper_v121_deploy_preflight as v121


deploy = v121.deploy
deploy.__doc__ = __doc__
deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v742-execns-helper-v122-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v741-execns-helper-v122-build/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "032fe43041b908577bb1a2e4b3ff7a7dfea24958169723907df5d403f811e989"
deploy.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
deploy.DEFAULT_TRANSFER_METHOD = "auto"
deploy.DEFAULT_SERIAL_CHUNK_SIZE = 1850
deploy.HELPER_MARKER = "a90_android_execns_probe v122"
deploy.SERVICE_MODE_TOKEN = "wifi-companion-service74-gated-mdm-helper-start-only"
deploy.DEPLOY_LABEL = "v122"
deploy.DEPLOY_NAME = "execns-helper-v122"
deploy.DEPLOY_PLAN_VERSION = "V742"
deploy.DEPLOY_LOG_PREFIX = "v742"
deploy.SUMMARY_TITLE = "v742 Execns Helper v122 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v742 deploy execns helper v122 only; "
    "no daemon start and no Wi-Fi bring-up"
)
deploy.V741_SCRIPT = deploy.Path("scripts/revalidation/native_wifi_mdm_helper_gated_live_v741.py")

v121.v120.v119.v118.v117.v116.v112.v111.v110.v109.v108.v107.v106.v105.v103.v102.v101.v100.v99.v98.v97.v96.v95.v94.v93.v92.v91.v90.v89.v88.v87.v86.v85.v84.v83.v82.v81.v80.v79.v78.v77.v76.v66.v62.v61.v60.v59.v58.v57.v56.v33.V33_TOKENS = (
    "a90_android_execns_probe v122",
    "wifi-companion-service74-gated-mdm-helper-start-only",
    "qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon,service74_gate,mdm_helper",
    "/vendor/bin/mdm_helper",
    "wifi_companion_start.mdm_helper_argv=/vendor/bin/mdm_helper",
    "wifi_companion_start.mdm_helper=%d",
    "wifi_companion_start.service74_gate.enabled=%d",
    "wifi_companion_start.child.%s.start_order=%zu",
    "--allow-wifi-companion-start-only",
    "--allow-hal-service-query",
    "wifi_companion_start.scan_connect_linkup=0",
    "wifi_companion_start.external_ping=0",
)

_BASE_BUILD_CHECKS = deploy.build_checks


def build_checks(args: deploy.argparse.Namespace,
                 store: deploy.EvidenceStore,
                 steps: list[deploy.StepResult],
                 local: dict[str, object],
                 ping: dict[str, object] | None) -> list[deploy.Check]:
    checks = _BASE_BUILD_CHECKS(args, store, steps, local, ping)
    if args.command == "plan":
        return checks

    busy_steps = [
        step.name
        for step in steps
        if step.status == "busy" or step.rc == -16
    ]
    required_steps = {"version", "status", "selftest", "ps", "proc-net-dev"}
    missing_or_failed = [
        step.name
        for step in steps
        if step.name in required_steps and not step.ok
    ]
    deploy.add_check(
        checks,
        f"{deploy.DEPLOY_LABEL}-read-only-preflight-complete",
        "pass" if not busy_steps and not missing_or_failed else "blocked",
        "blocker",
        f"busy_steps={busy_steps} missing_or_failed={missing_or_failed}",
        [
            step.file
            for step in steps
            if step.name in set(busy_steps) | set(missing_or_failed)
        ][:8],
        "clear native cmdv1 busy/menu state and rerun preflight before deploy",
    )
    return checks


def run_v741_plan(args: deploy.argparse.Namespace, store: deploy.EvidenceStore) -> dict[str, object]:
    out_dir = store.path("v741-helper-v122-mdm-helper-plan")
    command = [
        sys.executable,
        str(deploy.repo_path(deploy.V741_SCRIPT)),
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
        "plan",
    ]
    rc, output = deploy.run_host(command, timeout=180)
    store.write_text("host/v741-helper-v122-mdm-helper-plan.txt", output)
    manifest_path = out_dir / "manifest.json"
    manifest: dict[str, object] = {}
    if manifest_path.exists():
        manifest = deploy.json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        "command": " ".join(command),
        "rc": rc,
        "ok": rc == 0,
        "file": "host/v741-helper-v122-mdm-helper-plan.txt",
        "manifest": str(manifest_path),
        "decision": manifest.get("decision", "missing"),
        "pass": manifest.get("pass", False),
    }


def decide(args: deploy.argparse.Namespace,
           checks: list[deploy.Check],
           deploy_result: dict[str, object] | None,
           v741_result: dict[str, object] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return f"{deploy.DEPLOY_NAME}-deploy-plan-ready", True, "plan-only; no live command executed", "run V742 helper deploy preflight"
    if args.command == "preflight":
        blockers = deploy.blocking_checks(checks, ignore_deploy=True)
        if blockers:
            return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
        deploy_needed = any(check.severity == "deploy" and check.status != "pass" for check in checks)
        next_step = "deploy helper v122, then run V741 gated mdm_helper proof" if deploy_needed else "run V741 gated mdm_helper proof"
        return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready", True, "preflight complete; helper v122 deploy still requires exact approval", next_step
    blockers = deploy.blocking_checks(checks, ignore_deploy=deploy.approved(args))
    if blockers:
        return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
    if not deploy.approved(args):
        return f"{deploy.DEPLOY_NAME}-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact V742 deploy phrase"
    if deploy_result and not deploy_result["ok"]:
        return f"{deploy.DEPLOY_NAME}-deploy-failed", False, "install command failed", "inspect install transcript and retry after cleanup"
    if v741_result and v741_result.get("decision") != "v741-mdm-helper-gated-live-plan-ready":
        return f"{deploy.DEPLOY_NAME}-deploy-postflight-review", False, f"helper v122 post-deploy V741 plan decision={v741_result.get('decision')}", "inspect helper v122 post-deploy V741 plan output"
    return f"{deploy.DEPLOY_NAME}-deploy-pass", True, "helper v122 deployed or already current; V741 plan was rerun", "run V741 gated mdm_helper live proof"


deploy.run_v373_preflight = run_v741_plan
deploy.build_checks = build_checks
deploy.decide = decide


if __name__ == "__main__":
    raise SystemExit(deploy.main())
