#!/usr/bin/env python3
"""Build V2274 combined workqueue + codeword sampler test boot.

This source/build wrapper keeps the V2237 Wi-Fi route and packages both the
workqueue function-pointer sampler and the perf-regs/codeword sampler in the
same post-FWREADY boot_wlan / firmware_class fallback window.
"""

from __future__ import annotations

import hashlib
import json
import shlex
import subprocess
from pathlib import Path
from typing import Any

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

import build_native_init_boot_v2237_supplicant_terminate_poll as v2237
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path


OUT_DIR = workspace_private_build_path("native-init", "v2274-workqueue-codeword-combined")
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2274_WORKQUEUE_CODEWORD_COMBINED_SOURCE_BUILD_2026-06-12.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v2274_workqueue_codeword_combined.img", legacy_fallback=False
)
INIT_BINARY = OUT_DIR / "init_v2274_workqueue_codeword_combined"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v2274_workqueue_codeword_combined.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v432_workqueue_codeword_combined"
BPF_HELPER_BINARY = OUT_DIR / "a90_bpf_workqueue_func_sample_ring"
BPF_HELPER_SOURCE = REPO_ROOT / "workspace/public/src/native-init/helpers/a90_bpf_workqueue_func_sample_ring.c"
BPF_HELPER_RAMDISK_PATH = "bin/a90_bpf_workqueue_func_sample_ring"
BPF_HELPER_RUNTIME_PATH = "/bin/a90_bpf_workqueue_func_sample_ring"
TAIL_BPF_HELPER_BINARY = OUT_DIR / "a90_bpf_perf_regs_codeword_sample_ring"
TAIL_BPF_HELPER_SOURCE = REPO_ROOT / "workspace/public/src/native-init/helpers/a90_bpf_perf_regs_codeword_sample_ring.c"
TAIL_BPF_HELPER_RAMDISK_PATH = "bin/a90_bpf_perf_regs_codeword_sample_ring"
TAIL_BPF_HELPER_RUNTIME_PATH = "/bin/a90_bpf_perf_regs_codeword_sample_ring"
REMOTE_PROPERTY_ROOT = v2237.REMOTE_PROPERTY_ROOT
EXPECTED_HELPER_MARKER = "a90_android_execns_probe v432"
EXTRA_INIT_FLAGS = v2237.EXTRA_INIT_FLAGS
HELPER_MODE = v2237.HELPER_MODE
HELPER_RUNTIME_MODE = v2237.HELPER_RUNTIME_MODE
WORKQUEUE_LOG_PATH = "/cache/native-init-v2274-workqueue-fwclass.log"
WORKQUEUE_DURATION_MS = 45000
WORKQUEUE_PRINT_LIMIT = 2048
WORKQUEUE_WAIT_MS = 60000
TAIL_LOG_PATH = "/cache/native-init-v2274-tail-perf-regs-codeword.log"
TAIL_DURATION_MS = 45000
TAIL_PERIOD_NS = 1000000
TAIL_PRINT_LIMIT = 1024
TAIL_WAIT_MS = 60000
TAIL_SAMPLER_FLAGS = (
    "-DA90_WIFI_TEST_BOOT_TAIL_PERF_REGS_CODEWORD_SAMPLER=1",
    f"-DA90_WIFI_TEST_BOOT_TAIL_PERF_REGS_CODEWORD_DURATION_MS={TAIL_DURATION_MS}",
    f"-DA90_WIFI_TEST_BOOT_TAIL_PERF_REGS_CODEWORD_PERIOD_NS={TAIL_PERIOD_NS}",
    f"-DA90_WIFI_TEST_BOOT_TAIL_PERF_REGS_CODEWORD_PRINT_LIMIT={TAIL_PRINT_LIMIT}",
    f"-DA90_WIFI_TEST_BOOT_TAIL_PERF_REGS_CODEWORD_WAIT_MS={TAIL_WAIT_MS}",
    f'-DA90_WIFI_TEST_BOOT_TAIL_PERF_REGS_CODEWORD_OUTPUT_PATH="{TAIL_LOG_PATH}"',
    f'-DA90_WIFI_TEST_BOOT_TAIL_PERF_REGS_CODEWORD_HELPER_PATH="{TAIL_BPF_HELPER_RUNTIME_PATH}"',
)
WORKQUEUE_SAMPLER_FLAGS = (
    "-DA90_WIFI_TEST_BOOT_WORKQUEUE_FWCLASS_FUNC_SAMPLER=1",
    f"-DA90_WIFI_TEST_BOOT_WORKQUEUE_FWCLASS_FUNC_DURATION_MS={WORKQUEUE_DURATION_MS}",
    f"-DA90_WIFI_TEST_BOOT_WORKQUEUE_FWCLASS_FUNC_PRINT_LIMIT={WORKQUEUE_PRINT_LIMIT}",
    f"-DA90_WIFI_TEST_BOOT_WORKQUEUE_FWCLASS_FUNC_WAIT_MS={WORKQUEUE_WAIT_MS}",
    f'-DA90_WIFI_TEST_BOOT_WORKQUEUE_FWCLASS_FUNC_OUTPUT_PATH="{WORKQUEUE_LOG_PATH}"',
    f'-DA90_WIFI_TEST_BOOT_WORKQUEUE_FWCLASS_FUNC_HELPER_PATH="{BPF_HELPER_RUNTIME_PATH}"',
)


def base_module():
    return v2237.base_module()


def helper_chain():
    return v2237.helper_chain()


def helper_builder_module():
    return v2237.helper_builder_module()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(command: list[str | Path]) -> subprocess.CompletedProcess[str]:
    print("+ " + shlex.join(str(item) for item in command), flush=True)
    return subprocess.run([str(item) for item in command], check=True, text=True)


def with_workqueue_flags(flags: tuple[str, ...]) -> tuple[str, ...]:
    merged = v2237.with_bridge_flag(flags)
    for flag in (*TAIL_SAMPLER_FLAGS, *WORKQUEUE_SAMPLER_FLAGS):
        merged = (*tuple(item for item in merged if item != flag), flag)
    return merged


def configure_helper_flags() -> tuple[str, ...]:
    prev2137 = helper_chain()
    helper_flags = with_workqueue_flags(prev2137.HELPER_FLAGS)
    prev2137.HELPER_FLAGS = helper_flags
    prev2137.prev2135.HELPER_FLAGS = helper_flags
    prev2137.prev2135.prev2133.prev2131.HELPER_FLAGS = helper_flags
    helper_builder_module().HELPER_FLAGS = helper_flags
    return helper_flags


def configure_base() -> tuple[str, ...]:
    v2237.OUT_DIR = OUT_DIR
    v2237.REPORT_PATH = REPORT_PATH
    v2237.BOOT_IMAGE = BOOT_IMAGE
    v2237.INIT_BINARY = INIT_BINARY
    v2237.RAMDISK_CPIO = RAMDISK_CPIO
    v2237.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    v2237.configure_base()
    helper_flags = configure_helper_flags()

    base = base_module()
    args = list(base.DEFAULT_ARGS)
    replacements = {
        "--cycle": "V2274",
        "--decision": "v2274-workqueue-codeword-combined-source-build-pass",
        "--cycle-label": "v2274",
        "--init-version": "0.9.274",
        "--init-build": "v2274-workqueue-codeword-combined",
        "--out-dir": str(OUT_DIR),
        "--init-binary": str(INIT_BINARY),
        "--helper-binary": str(HELPER_BINARY),
        "--ramdisk-cpio": str(RAMDISK_CPIO),
        "--boot-image": str(BOOT_IMAGE),
        "--wifi-test-klog-prefix": "A90v2274",
        "--wifi-test-disable": "/cache/native-init-wifi-test-boot-v2274.disable",
        "--wifi-test-log": "/cache/native-init-wifi-test-boot-v2274.log",
        "--wifi-test-summary": "/cache/native-init-wifi-test-boot-v2274.summary",
        "--wifi-test-helper-result": "/cache/native-init-wifi-test-boot-v2274-helper.result",
        "--wifi-test-pid": "/cache/native-init-wifi-test-boot-v2274.pid",
        "--wifi-test-watcher-pid": "/cache/native-init-wifi-test-boot-v2274-supervisor.pid",
        "--wifi-test-property-root": REMOTE_PROPERTY_ROOT,
        "--wifi-test-helper-mode": HELPER_MODE,
        "--wifi-test-watch-sec": "190",
        "--wifi-test-supervisor-timeout-sec": "245",
    }
    for key, value in replacements.items():
        v2237.v2230.v2189.v2188.v2187.v2182.v2178.v2176.v2174.v2169.v726.set_arg(args, key, value)
    base.DEFAULT_ARGS = args
    base.base.EXTRA_INIT_FLAGS = EXTRA_INIT_FLAGS
    return helper_flags


def build_static_helper(source: Path, output: Path) -> str:
    output.parent.mkdir(parents=True, exist_ok=True)
    run([
        "aarch64-linux-gnu-gcc",
        "-static",
        "-Os",
        "-Wall",
        "-Wextra",
        "-o",
        output,
        source,
    ])
    run(["aarch64-linux-gnu-strip", output])
    return sha256(output)


def build_bpf_helpers() -> dict[str, str]:
    return {
        "workqueue": build_static_helper(BPF_HELPER_SOURCE, BPF_HELPER_BINARY),
        "codeword": build_static_helper(TAIL_BPF_HELPER_SOURCE, TAIL_BPF_HELPER_BINARY),
    }

def patch_ramdisk_helpers(base_wrapper: Any) -> None:
    original_ramdisk_helpers = base_wrapper.base.ramdisk_helpers

    def ramdisk_helpers_with_workqueue_sampler(args: Any) -> dict[str, Path]:
        helpers = dict(original_ramdisk_helpers(args))
        helpers[BPF_HELPER_RAMDISK_PATH] = BPF_HELPER_BINARY
        helpers[TAIL_BPF_HELPER_RAMDISK_PATH] = TAIL_BPF_HELPER_BINARY
        return helpers

    base_wrapper.base.ramdisk_helpers = ramdisk_helpers_with_workqueue_sampler


def patch_helper_builder(base_wrapper: Any, helper_flags: tuple[str, ...]) -> None:
    build_base = base_wrapper.base

    def build_helper(args: Any) -> None:
        args.out_dir.mkdir(parents=True, exist_ok=True)
        command: list[object] = [
            "env",
            "A90_EXECNS_PROBE_CFLAGS=" + " ".join(helper_flags),
            "bash",
            build_base.HELPER_BUILD_SCRIPT,
            args.helper_binary,
        ]
        build_base.run(command)
        args.helper_binary.chmod(0o600)
        strings = build_base.run(["strings", args.helper_binary], capture=True).stdout
        if EXPECTED_HELPER_MARKER not in strings:
            raise RuntimeError(f"missing helper marker: {EXPECTED_HELPER_MARKER}")

    build_base.build_helper = build_helper


def render_report(manifest: dict[str, object], helper_flags: tuple[str, ...], helper_shas: dict[str, str]) -> str:
    wifi = manifest["wifi_test"]
    helper_flag_lines = [f"- `{flag}`" for flag in helper_flags]
    return "\n".join([
        "# Native Init V2274 Workqueue Codeword Combined Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V2274`",
        "- Type: source/build-only rollbackable post-FWREADY workqueue function-pointer oracle test boot.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: V2273 packaged the workqueue oracle but left same-boot slide evidence implicit. V2274 packages the workqueue function-pointer sampler and the perf-regs/codeword sampler together so V2275 can classify workqueue functions with same-boot exact-slide evidence.",
        "- Manifest: `workspace/private/builds/native-init/v2274-workqueue-codeword-combined/manifest.json`",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        f"- Helper marker: `{EXPECTED_HELPER_MARKER}` (binary marker string: `{manifest['helper_marker']}`)",
        f"- Helper SHA256: `{manifest['helper_sha256']}`",
        f"- Workqueue sampler ramdisk path: `{BPF_HELPER_RUNTIME_PATH}`",
        f"- Workqueue sampler SHA256: `{helper_shas['workqueue']}`",
        f"- Codeword sampler ramdisk path: `{TAIL_BPF_HELPER_RUNTIME_PATH}`",
        f"- Codeword sampler SHA256: `{helper_shas['codeword']}`",
        "",
        "## Route",
        "",
        f"- Helper runtime mode: `{wifi['helper_runtime_mode']}`",
        f"- Helper timeout: `{wifi['helper_timeout_sec']}`",
        f"- Property root: `{REMOTE_PROPERTY_ROOT}`",
        "- Kept from V2237: service-object-visible route, post-FWREADY `boot_wlan`, firmware_class feeder, and strict supplicant terminate polling.",
        "- Added for this build only: `A90_WIFI_TEST_BOOT_WORKQUEUE_FWCLASS_FUNC_SAMPLER=1`, `A90_WIFI_TEST_BOOT_TAIL_PERF_REGS_CODEWORD_SAMPLER=1`, and ramdisk-local workqueue/codeword BPF helpers.",
        f"- Capture contract: start both samplers before `append_post_fw_ready_boot_wlan_trigger`; observe `workqueue_queue_work`/`workqueue_execute_start` for {WORKQUEUE_DURATION_MS} ms into `{WORKQUEUE_LOG_PATH}`, and sample perf regs/codewords for {TAIL_DURATION_MS} ms into `{TAIL_LOG_PATH}`. V2275 classifies workqueue functions with the same-boot codeword slide.",
        "- Next live use: V2275 should flash this image, collect the helper result plus the workqueue log, roll back to the selected baseline, verify selftest `FAIL=0`, and classify function pointers against the same-boot exact slide/codeword evidence.",
        "",
        "## Helper Flags",
        "",
        *helper_flag_lines,
        "",
        "## Safety Scope",
        "",
        "This build script performed host-side source/build work only. The new combined route attaches read-only BPF tracepoint programs to workqueue events and read-only BPF perf-event programs for codeword sampling; both store scalar evidence in BPF maps. It does not write tracefs controls, execute `probe_write_user`, scan/connect Wi-Fi, use credentials, configure DHCP/routes, ping externally, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.",
        "",
    ])


def main() -> int:
    helper_flags = configure_base()
    helper_shas = build_bpf_helpers()
    helper_builder = helper_builder_module()
    helper_builder.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    base = base_module()
    base.base.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    patch_helper_builder(base, helper_flags)
    patch_ramdisk_helpers(base)
    v2237.patch_mkbootimg_tools(base)
    base.render_report = lambda manifest: render_report(manifest, helper_flags, helper_shas)
    rc = base.main()
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["candidate_tag"] = "v2274-workqueue-codeword-combined"
    manifest["parent_baseline"] = "v2237-supplicant-terminate-poll"
    manifest["rollback_baseline"] = "v2237-supplicant-terminate-poll"
    manifest["promoted_baseline"] = False
    manifest["helper_flags"] = list(helper_flags)
    manifest["workqueue_sampler"] = {
        "source": str(BPF_HELPER_SOURCE.relative_to(REPO_ROOT)),
        "ramdisk_path": BPF_HELPER_RUNTIME_PATH,
        "sha256": helper_shas["workqueue"],
        "output_path": WORKQUEUE_LOG_PATH,
        "duration_ms": WORKQUEUE_DURATION_MS,
        "print_limit": WORKQUEUE_PRINT_LIMIT,
        "wait_ms": WORKQUEUE_WAIT_MS,
        "events": ["workqueue:workqueue_queue_work", "workqueue:workqueue_execute_start"],
        "tracepoint_fields": ["work", "function", "workqueue", "req_cpu", "cpu"],
    }
    manifest["codeword_sampler"] = {
        "source": str(TAIL_BPF_HELPER_SOURCE.relative_to(REPO_ROOT)),
        "ramdisk_path": TAIL_BPF_HELPER_RUNTIME_PATH,
        "sha256": helper_shas["codeword"],
        "output_path": TAIL_LOG_PATH,
        "duration_ms": TAIL_DURATION_MS,
        "period_ns": TAIL_PERIOD_NS,
        "print_limit": TAIL_PRINT_LIMIT,
        "wait_ms": TAIL_WAIT_MS,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    live_candidate_path = OUT_DIR / "live-candidate.json"
    live_candidate_path.write_text(json.dumps({
        "candidate_tag": "v2274-workqueue-codeword-combined",
        "boot_image": str(BOOT_IMAGE.relative_to(REPO_ROOT)),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "helper_sha256": manifest["helper_sha256"],
        "workqueue_sampler_sha256": helper_shas["workqueue"],
        "codeword_sampler_sha256": helper_shas["codeword"],
        "source_report": str(REPORT_PATH.relative_to(REPO_ROOT)),
        "next_live_cycle": "V2275",
        "note": "V2274 keeps the V2237 WLAN route and adds read-only workqueue function-pointer and codeword samplers around the post-FWREADY boot_wlan/firmware_class window.",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
