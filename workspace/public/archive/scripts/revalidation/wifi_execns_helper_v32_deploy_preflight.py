#!/usr/bin/env python3
"""V466 execns helper v32 deploy/preflight wrapper.

Deploy is limited to `/cache/bin/a90_android_execns_probe` and requires the
exact V466 deploy approval phrase. It does not start service-manager,
hwservicemanager, Wi-Fi HAL, CNSS, scan/connect, or Wi-Fi bring-up.
"""

from __future__ import annotations

import sys

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.__doc__ = __doc__
deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v466-execns-helper-v32-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v466-a90_android_execns_probe-v32/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "29ce77fa7215287b3f3948fe19a3667330df52156d2fa8750220fb971d5fb685"
deploy.HELPER_MARKER = "a90_android_execns_probe v32"
deploy.SERVICE_MODE_TOKEN = "wifi-iwifi-start-surface"
deploy.DEPLOY_LABEL = "v32"
deploy.DEPLOY_NAME = "execns-helper-v32"
deploy.DEPLOY_PLAN_VERSION = "V466"
deploy.DEPLOY_LOG_PREFIX = "v466"
deploy.SUMMARY_TITLE = "v466 Execns Helper v32 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v466 deploy execns helper v32 only; "
    "no daemon start and no Wi-Fi bring-up"
)
deploy.V373_SCRIPT = deploy.Path("scripts/revalidation/native_iwifi_start_surface_v466.py")

V32_TOKENS = (
    "a90_android_execns_probe v32",
    "wifi-iwifi-start-surface",
    "--allow-iwifi-start-only",
    "iwifi_start.begin",
    "android.hardware.wifi@1.0::IWifi",
)

_BASE_LOCAL_HELPER_INFO = deploy.local_helper_info
_BASE_BUILD_CHECKS = deploy.build_checks


def local_helper_info(args: deploy.argparse.Namespace) -> dict[str, object]:
    info = _BASE_LOCAL_HELPER_INFO(args)
    info["strings_v32_tokens"] = False
    if not info.get("exists"):
        return info
    rc, strings_output = deploy.run_host(["strings", str(deploy.repo_path(args.local_helper))], timeout=10)
    if rc == 0:
        info["strings_v32_tokens"] = all(token in strings_output for token in V32_TOKENS)
    return info


def build_checks(args: deploy.argparse.Namespace, store: deploy.EvidenceStore,
                 steps: list[deploy.StepResult], local: dict[str, object],
                 ping: dict[str, object] | None) -> list[deploy.Check]:
    checks = _BASE_BUILD_CHECKS(args, store, steps, local, ping)
    local_v32_ok = bool(local.get("strings_v32_tokens"))
    deploy.add_check(
        checks,
        "local-helper-v32-iwifi-guards",
        "pass" if local_v32_ok else "blocked",
        "blocker",
        f"v32_tokens={local_v32_ok}",
        [str(local.get("path", ""))],
        "rebuild helper v32 with raw hwbinder IWifi mode before deploy",
    )
    if args.command == "plan":
        return checks
    helper_usage = deploy.capture_text(store, steps, "helper-usage")
    helper_sha = deploy.capture_text(store, steps, "sha-helper")
    remote_v32_ok = (
        args.helper_sha256 in helper_sha
        and deploy.HELPER_MARKER in helper_usage
        and deploy.SERVICE_MODE_TOKEN in helper_usage
        and "--allow-iwifi-start-only" in helper_usage
    )
    deploy.add_check(
        checks,
        "remote-helper-v32-iwifi-guards",
        "pass" if remote_v32_ok else "needs-deploy",
        "deploy",
        f"iwifi_guard={remote_v32_ok}",
        [line for line in helper_usage.splitlines() if deploy.SERVICE_MODE_TOKEN in line or "--allow-iwifi-start-only" in line][:4],
        "approved V466 deploy installs helper v32 with raw hwbinder IWifi support if needed",
    )
    return checks


def run_v466_preflight(args: deploy.argparse.Namespace, store: deploy.EvidenceStore) -> dict[str, object]:
    out_dir = store.path("v466-iwifi-start-preflight")
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
    store.write_text("host/v466-iwifi-start-preflight.txt", output)
    manifest_path = out_dir / "manifest.json"
    manifest: dict[str, object] = {}
    if manifest_path.exists():
        manifest = deploy.json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        "command": " ".join(command),
        "rc": rc,
        "ok": rc == 0,
        "file": "host/v466-iwifi-start-preflight.txt",
        "manifest": str(manifest_path),
        "decision": manifest.get("decision", "missing"),
        "pass": manifest.get("pass", False),
    }


def decide(args: deploy.argparse.Namespace,
           checks: list[deploy.Check],
           deploy_result: dict[str, object] | None,
           v466_result: dict[str, object] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return "execns-helper-v32-deploy-plan-ready", True, "plan-only; no live command executed", "run preflight"
    blockers = deploy.blocking_checks(checks, ignore_deploy=True)
    if blockers:
        return "execns-helper-v32-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
    deploy_needed = any(check.name == "remote-helper-v32" and check.status != "pass" for check in checks)
    if args.command == "preflight":
        if deploy_needed:
            return "execns-helper-v32-deploy-preflight-ready-needs-deploy", True, "preflight complete; helper v32 deploy still requires exact approval", "operator may approve V466 deploy"
        return "execns-helper-v32-deploy-preflight-ready", True, "preflight complete; deploy still requires exact approval", "operator may approve V466 deploy"
    if not deploy.approved(args):
        return "execns-helper-v32-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact phrase if deploy is intended"
    if deploy_result and not deploy_result["ok"]:
        return "execns-helper-v32-deploy-failed", False, "install command failed", "inspect install transcript and retry after cleanup"
    if v466_result and v466_result["decision"] not in {
        "v466-raw-hwbinder-iwifi-start-preflight-ready",
        "v466-raw-hwbinder-iwifi-start-blocked",
    }:
        return "execns-helper-v32-deploy-postflight-review", False, f"V466 preflight decision={v466_result['decision']}", "inspect V466 preflight output"
    return "execns-helper-v32-deploy-pass", True, "helper v32 deployed or already current; V466 preflight was rerun", "next requires separate V466 live IWifi.start approval"


deploy.run_v373_preflight = run_v466_preflight
deploy.decide = decide
deploy.local_helper_info = local_helper_info
deploy.build_checks = build_checks


if __name__ == "__main__":
    raise SystemExit(deploy.main())
