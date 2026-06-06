#!/usr/bin/env python3
"""V467 execns helper v33 deploy/preflight wrapper.

Deploy is limited to `/cache/bin/a90_android_execns_probe` and requires the
exact V467 deploy approval phrase. It does not start service-manager,
hwservicemanager, Wi-Fi HAL, CNSS, scan/connect, or Wi-Fi bring-up.
"""

from __future__ import annotations

import sys

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.__doc__ = __doc__
deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v467-execns-helper-v33-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v467-a90_android_execns_probe-v33/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "93b93cade7ce1698c2c4b2f5351ab36f5d9032c8167629aa7ae59bb71b0d53aa"
deploy.HELPER_MARKER = "a90_android_execns_probe v33"
deploy.SERVICE_MODE_TOKEN = "wifi-surface-composite-lshal-wait-iwifi"
deploy.DEPLOY_LABEL = "v33"
deploy.DEPLOY_NAME = "execns-helper-v33"
deploy.DEPLOY_PLAN_VERSION = "V467"
deploy.DEPLOY_LOG_PREFIX = "v467"
deploy.SUMMARY_TITLE = "v467 Execns Helper v33 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v467 deploy execns helper v33 only; "
    "no daemon start and no Wi-Fi bring-up"
)
deploy.V373_SCRIPT = deploy.Path("scripts/revalidation/native_iwifi_registration_v467.py")

V33_TOKENS = (
    "a90_android_execns_probe v33",
    "wifi-surface-composite-lshal-wait-iwifi",
    "--allow-hal-service-query",
    "lshal wait <fqinstance>",
    "android.hardware.wifi@1.0::IWifi/default",
)

_BASE_LOCAL_HELPER_INFO = deploy.local_helper_info
_BASE_BUILD_CHECKS = deploy.build_checks


def local_helper_info(args: deploy.argparse.Namespace) -> dict[str, object]:
    info = _BASE_LOCAL_HELPER_INFO(args)
    info["strings_v33_tokens"] = False
    if not info.get("exists"):
        return info
    rc, strings_output = deploy.run_host(["strings", str(deploy.repo_path(args.local_helper))], timeout=10)
    if rc == 0:
        info["strings_v33_tokens"] = all(token in strings_output for token in V33_TOKENS)
    return info


def build_checks(args: deploy.argparse.Namespace, store: deploy.EvidenceStore,
                 steps: list[deploy.StepResult], local: dict[str, object],
                 ping: dict[str, object] | None) -> list[deploy.Check]:
    checks = _BASE_BUILD_CHECKS(args, store, steps, local, ping)
    local_v33_ok = bool(local.get("strings_v33_tokens"))
    deploy.add_check(
        checks,
        f"local-helper-{deploy.DEPLOY_LABEL}-registration-guards",
        "pass" if local_v33_ok else "blocked",
        "blocker",
        f"v33_tokens={local_v33_ok}",
        [str(local.get("path", ""))],
        "rebuild helper v33 with IWifi/default lshal-wait mode before deploy",
    )
    if args.command == "plan":
        return checks

    helper_usage = deploy.capture_text(store, steps, "helper-usage")
    helper_sha = deploy.capture_text(store, steps, "sha-helper")
    remote_v33_ok = (
        args.helper_sha256 in helper_sha
        and deploy.HELPER_MARKER in helper_usage
        and deploy.SERVICE_MODE_TOKEN in helper_usage
        and "--allow-hal-service-query" in helper_usage
    )
    deploy.add_check(
        checks,
        f"remote-helper-{deploy.DEPLOY_LABEL}-registration-guards",
        "pass" if remote_v33_ok else "needs-deploy",
        "deploy",
        f"registration_guard={remote_v33_ok}",
        [line for line in helper_usage.splitlines() if deploy.SERVICE_MODE_TOKEN in line or "--allow-hal-service-query" in line][:4],
        "approved V467 deploy installs helper v33 with IWifi/default registration support if needed",
    )
    return checks


def run_v467_preflight(args: deploy.argparse.Namespace, store: deploy.EvidenceStore) -> dict[str, object]:
    out_dir = store.path("v467-iwifi-registration-preflight")
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
        "preflight",
    ]
    rc, output = deploy.run_host(command, timeout=180)
    store.write_text("host/v467-iwifi-registration-preflight.txt", output)
    manifest_path = out_dir / "manifest.json"
    manifest: dict[str, object] = {}
    if manifest_path.exists():
        manifest = deploy.json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        "command": " ".join(command),
        "rc": rc,
        "ok": rc == 0,
        "file": "host/v467-iwifi-registration-preflight.txt",
        "manifest": str(manifest_path),
        "decision": manifest.get("decision", "missing"),
        "pass": manifest.get("pass", False),
    }


def decide(args: deploy.argparse.Namespace,
           checks: list[deploy.Check],
           deploy_result: dict[str, object] | None,
    v467_result: dict[str, object] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return f"{deploy.DEPLOY_NAME}-deploy-plan-ready", True, "plan-only; no live command executed", "run preflight"
    blockers = deploy.blocking_checks(checks, ignore_deploy=True)
    if blockers:
        return f"{deploy.DEPLOY_NAME}-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
    deploy_needed = any(
        check.name.startswith(f"remote-helper-{deploy.DEPLOY_LABEL}") and check.status != "pass"
        for check in checks
    )
    if args.command == "preflight":
        if deploy_needed:
            return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready-needs-deploy", True, f"preflight complete; helper {deploy.DEPLOY_LABEL} deploy still requires exact approval", f"operator may approve {deploy.DEPLOY_PLAN_VERSION} deploy"
        return f"{deploy.DEPLOY_NAME}-deploy-preflight-ready", True, "preflight complete; deploy still requires exact approval", f"operator may approve {deploy.DEPLOY_PLAN_VERSION} deploy"
    if not deploy.approved(args):
        return f"{deploy.DEPLOY_NAME}-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact phrase if deploy is intended"
    if deploy_result and not deploy_result["ok"]:
        return f"{deploy.DEPLOY_NAME}-deploy-failed", False, "install command failed", "inspect install transcript and retry after cleanup"
    if v467_result and v467_result["decision"] not in {
        "v467-iwifi-registration-preflight-ready",
        "v467-iwifi-registration-blocked",
    }:
        return f"{deploy.DEPLOY_NAME}-deploy-postflight-review", False, f"{deploy.DEPLOY_PLAN_VERSION} preflight decision={v467_result['decision']}", f"inspect {deploy.DEPLOY_PLAN_VERSION} preflight output"
    return f"{deploy.DEPLOY_NAME}-deploy-pass", True, f"helper {deploy.DEPLOY_LABEL} deployed or already current; {deploy.DEPLOY_PLAN_VERSION} preflight was rerun", f"next requires separate {deploy.DEPLOY_PLAN_VERSION} live IWifi/default registration approval"


deploy.run_v373_preflight = run_v467_preflight
deploy.decide = decide
deploy.local_helper_info = local_helper_info
deploy.build_checks = build_checks


if __name__ == "__main__":
    raise SystemExit(deploy.main())
