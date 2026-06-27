#!/usr/bin/env python3
"""Run V3322 GPU Z0 zero-copy DRM modifier reconnaissance.

This is a no-flash, read-only DRM inventory pass. It builds a small static
AArch64 helper, installs it under /cache/bin, enumerates KMS plane formats and
IN_FORMATS modifiers on /dev/dri/card0, and writes a public feasibility report
for the zero-copy KMS/dmabuf scanout rung.
"""

from __future__ import annotations

import argparse
import base64
import json
import lzma
import os
import re
import shlex
import sys
import time
from pathlib import Path
from typing import Any

import native_kernel_timer_object_histogram_v2202 as live_base


REPO_ROOT = Path(__file__).resolve().parents[5]
SCRIPT_DIR = REPO_ROOT / "workspace/public/src/scripts/revalidation"
HELPER_SOURCE = REPO_ROOT / "workspace/public/src/native-init/helpers/a90_drm_modifier_probe_z0.c"
GPU_SOURCE = REPO_ROOT / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"
MESA_FD6_RESOURCE = Path("/tmp/a90-mesa-gpu-src/src/gallium/drivers/freedreno/a6xx/fd6_resource.cc")
MESA_DRM_FOURCC = Path("/tmp/a90-mesa-gpu-src/include/drm-uapi/drm_fourcc.h")
PRIVATE_RUNS = REPO_ROOT / "workspace/private/runs/gpu"
REPORT_PATH = REPO_ROOT / "docs/reports/NATIVE_INIT_V3322_GPU_Z0_ZERO_COPY_MODIFIER_RECON_2026-06-27.md"
REMOTE_HELPER = "/cache/bin/a90_drm_modifier_probe_z0"
DEFAULT_TOYBOX = "/bin/busybox"
RUN_ID = "V3322"
DECISION_DRY_RUN = "v3322-gpu-z0-modifier-recon-dry-run"
DECISION_LINEAR = "v3322-z0-linear-zero-copy-feasible-pending-shared-buffer-proof"
DECISION_IMPLICIT_LINEAR = "v3322-z0-implicit-linear-scanout-feasible-pending-shared-buffer-proof"
DECISION_TILED3 = "v3322-z0-tiled3-zero-copy-feasible-pending-render-target-switch"
DECISION_COMPRESSED = "v3322-z0-compressed-zero-copy-possible-but-high-risk"
DECISION_NONE = "v3322-z0-no-matching-scanout-modifier"
DECISION_FAILED = "v3322-z0-modifier-recon-failed"

KEY_VALUE_RE = re.compile(r"^(?P<key>[A-Za-z0-9_.]+)=(?P<value>.*)$", re.MULTILINE)
PLANE_LINE_RE = re.compile(r"^plane\.(?P<index>\d+)\.(?P<body>.+)$")


def rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def now_label() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


def parse_tokens(body: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for token in body.split():
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        result[key] = value
    return result


def parse_count(values: dict[str, str], key: str) -> int:
    value = values.get(key, "0").strip()
    if not value:
        return 0
    if value.startswith(("0x", "0X")):
        return int(value, 16)
    return int(value, 10)


def clean_resident_version(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("version: "):
            return line.strip()
    for line in text.splitlines():
        if line.startswith("A90 Linux init "):
            return line.strip()
    return text.strip().splitlines()[0] if text.strip() else ""


def parse_probe_stdout(text: str) -> dict[str, Any]:
    values = {match.group("key"): match.group("value") for match in KEY_VALUE_RE.finditer(text)}
    planes: dict[str, dict[str, str]] = {}
    active_line = values.get("probe.active.connector_id")
    if active_line:
        values.update({
            f"probe.active.{key}": value
            for key, value in parse_tokens(f"connector_id={active_line}").items()
        })

    for line in text.splitlines():
        match = PLANE_LINE_RE.match(line)
        if not match:
            continue
        index = match.group("index")
        body = match.group("body")
        plane = planes.setdefault(index, {})
        if body.startswith("id="):
            plane.update(parse_tokens(body))
        elif body.startswith("props."):
            fields = parse_tokens(body.replace("props.", "props_", 1))
            plane.update(fields)
        elif body.startswith("formats.sample="):
            plane["formats_sample"] = body.split("=", 1)[1]
        elif body.startswith("in_formats.has="):
            fields = parse_tokens(body)
            plane.update({f"in_formats_{key}": value for key, value in fields.items()})
        elif body.startswith("modifiers.any "):
            fields = parse_tokens(body[len("modifiers.any "):])
            plane.update({f"modifier_any_{key}": value for key, value in fields.items()})
        elif body.startswith("modifiers.XB24 "):
            fields = parse_tokens(body[len("modifiers.XB24 "):])
            plane.update({f"xb24_{key}": value for key, value in fields.items()})
        elif body.startswith("modifiers.XR24 "):
            fields = parse_tokens(body[len("modifiers.XR24 "):])
            plane.update({f"xr24_{key}": value for key, value in fields.items()})
        elif body.startswith("modifiers.names="):
            plane["modifiers_names"] = body.split("=", 1)[1].lstrip(",")

    prime_fields = parse_tokens("prime=" + values.get("probe.cap.prime", "")) if "probe.cap.prime" in values else {}
    linear_count = parse_count(values, "probe.candidate.linear_count")
    implicit_linear_count = parse_count(values, "probe.candidate.implicit_linear_count")
    tiled3_count = parse_count(values, "probe.candidate.qcom_tiled3_count")
    compressed_count = parse_count(values, "probe.candidate.qcom_compressed_count")
    if linear_count > 0:
        decision = DECISION_LINEAR
        recipe = "linear-xbgr8888"
    elif implicit_linear_count > 0:
        decision = DECISION_IMPLICIT_LINEAR
        recipe = "implicit-linear-xbgr8888"
    elif tiled3_count > 0:
        decision = DECISION_TILED3
        recipe = "qcom-tiled3-xbgr8888"
    elif compressed_count > 0:
        decision = DECISION_COMPRESSED
        recipe = "qcom-compressed-xbgr8888"
    else:
        decision = DECISION_NONE
        recipe = "none"

    return {
        "values": values,
        "planes": planes,
        "plane_count": parse_count(values, "probe.planes.count"),
        "compatible_plane_count": parse_count(values, "probe.compatible_plane_count"),
        "rect_props_plane_count": parse_count(values, "probe.rect_props_plane_count"),
        "xbgr_linear_plane_count": parse_count(values, "probe.xbgr8888.linear_plane_count"),
        "xbgr_tiled3_plane_count": parse_count(values, "probe.xbgr8888.qcom_tiled3_plane_count"),
        "xbgr_compressed_plane_count": parse_count(values, "probe.xbgr8888.qcom_compressed_plane_count"),
        "candidate_linear_count": linear_count,
        "candidate_implicit_linear_count": implicit_linear_count,
        "candidate_tiled3_count": tiled3_count,
        "candidate_compressed_count": compressed_count,
        "addfb2_modifiers": parse_count(values, "probe.cap.addfb2_modifiers"),
        "prime": prime_fields,
        "result": values.get("probe.result", ""),
        "decision": decision,
        "recipe": recipe,
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def serial_base64_install_helper(args: argparse.Namespace,
                                 out_dir: Path,
                                 steps: list[live_base.StepResult],
                                 local_binary: Path,
                                 summary: dict[str, Any]) -> None:
    target_dir = str(Path(REMOTE_HELPER).parent).replace("\\", "/")
    target_name = Path(REMOTE_HELPER).name
    tmp_target = f"{target_dir}/.{target_name}.serial-tmp.{os.getpid()}.{int(time.time())}"
    tmp_archive = f"{tmp_target}.xz"
    compressed = lzma.compress(local_binary.read_bytes(), preset=9 | lzma.PRESET_EXTREME)
    encoded = base64.b64encode(compressed).decode("ascii")
    local_hash = live_base.sha256_file(local_binary)
    chunk_size = args.serial_base64_chunk_chars
    if chunk_size <= 0 or chunk_size % 4 != 0:
        raise RuntimeError("--serial-base64-chunk-chars must be a positive multiple of 4")

    live_base.a90ctl(args, out_dir, steps, "install-z0-modifier-probe-serial-mkdir", ["mkdir", target_dir], timeout=30, allow_error=True)
    live_base.a90ctl(args, out_dir, steps, "install-z0-modifier-probe-serial-cleanup", ["run", args.toybox, "rm", "-f", tmp_target, tmp_archive], timeout=30, allow_error=True)
    for index, offset in enumerate(range(0, len(encoded), chunk_size)):
        chunk = encoded[offset:offset + chunk_size]
        script = (
            f"printf %s {shlex.quote(chunk)} | "
            f"{shlex.quote(args.toybox)} base64 -d >> {shlex.quote(tmp_archive)}"
        )
        live_base.a90ctl(
            args,
            out_dir,
            steps,
            f"install-z0-modifier-probe-serial-chunk-{index:04d}",
            ["run", args.toybox, "sh", "-c", script],
            timeout=args.serial_chunk_timeout,
        )
    live_base.a90ctl(
        args,
        out_dir,
        steps,
        "install-z0-modifier-probe-serial-xzcat",
        ["run", args.toybox, "sh", "-c", f"{shlex.quote(args.toybox)} xzcat {shlex.quote(tmp_archive)} > {shlex.quote(tmp_target)}"],
        timeout=60,
    )
    live_base.a90ctl(args, out_dir, steps, "install-z0-modifier-probe-serial-chmod", ["run", args.toybox, "chmod", "755", tmp_target], timeout=30)
    sha_output = live_base.a90ctl(args, out_dir, steps, "install-z0-modifier-probe-serial-sha", ["run", args.toybox, "sha256sum", tmp_target], timeout=60)
    if local_hash not in sha_output:
        raise RuntimeError(f"serial upload sha mismatch local={local_hash}\n{sha_output}")
    live_base.a90ctl(args, out_dir, steps, "install-z0-modifier-probe-serial-mv", ["run", args.toybox, "mv", "-f", tmp_target, REMOTE_HELPER], timeout=30)
    live_base.a90ctl(args, out_dir, steps, "install-z0-modifier-probe-serial-clean-archive", ["run", args.toybox, "rm", "-f", tmp_archive], timeout=30, allow_error=True)
    summary["install_path"] = "serial-base64"
    summary["serial_base64_chunks"] = (len(encoded) + chunk_size - 1) // chunk_size
    summary["serial_compressed_bytes"] = len(compressed)


def install_helper(args: argparse.Namespace,
                   out_dir: Path,
                   steps: list[live_base.StepResult],
                   local_binary: Path,
                   summary: dict[str, Any]) -> None:
    if args.device_ip:
        try:
            live_base.install_helper(args, out_dir, steps, "gpu-z0-modifier-probe", local_binary, REMOTE_HELPER)
            summary["install_path"] = "bridge-nc"
            return
        except Exception as exc:  # noqa: BLE001 - serial fallback keeps the read-only run usable
            summary["bridge_nc_install_error"] = str(exc)
    else:
        summary["bridge_nc_install_error"] = "skipped: --device-ip not set"
    serial_base64_install_helper(args, out_dir, steps, local_binary, summary)


def selected_candidate_planes(probe: dict[str, Any]) -> list[tuple[str, dict[str, str]]]:
    planes = probe.get("planes") or {}
    selected: list[tuple[str, dict[str, str]]] = []
    for index in sorted(planes, key=lambda value: int(value)):
        plane = planes[index]
        if plane.get("compatible_active_crtc") == "1" and plane.get("rect_props") == "1":
            implicit_linear = plane.get("has_xbgr8888") == "1" and plane.get("in_formats_in_formats.has") == "0"
            if (implicit_linear or
                    plane.get("xb24_linear") == "1" or
                    plane.get("xb24_qcom_tiled3") == "1" or
                    plane.get("xb24_qcom_compressed") == "1"):
                selected.append((index, plane))
    return selected


def render_report(summary: dict[str, Any]) -> str:
    probe = summary.get("probe") or {}
    values = probe.get("values") or {}
    build = summary.get("build") or {}
    decision = summary.get("decision", probe.get("decision", DECISION_DRY_RUN))
    recipe = probe.get("recipe", "none")
    candidates = selected_candidate_planes(probe)

    lines = [
        "# Native Init V3322 GPU Z0 Zero-Copy Modifier Recon",
        "",
        "- Date: 2026-06-27",
        f"- Cycle: `{RUN_ID}`",
        "- Track: GPU rung ④ zero-copy KMS/dmabuf scanout.",
        f"- Decision: `{decision}`",
        "",
        "## Scope",
        "",
        "This was a no-flash Z0 reconnaissance pass. It built a temporary static",
        "AArch64 helper, installed it under `/cache/bin`, and queried `/dev/dri/card0`",
        "for real plane formats plus atomic `IN_FORMATS` modifier blobs. The helper",
        "does not modeset, page-flip, present, write panel controls, or touch power",
        "domains.",
        "",
        "## Safety",
        "",
        "- Flash/reboot: `0`",
        "- Partition/firmware writes: `0`",
        "- Display mutation: `0`",
        "- PMIC/GDSC/regulator/GPIO/backlight writes: `0`",
        "- Probe scope: DRM resource/property/blob inventory only.",
        "",
        "## Build",
        "",
        f"- Helper source: `{rel(HELPER_SOURCE)}`",
        f"- Helper SHA-256: `{build.get('helper_sha256', '')}`",
        f"- Helper size: `{build.get('helper_size', 0)}` bytes",
        f"- Install path: `{summary.get('install_path', '')}`",
        "",
        "## Live Result",
        "",
        f"- Resident version: `{clean_resident_version(summary.get('resident_version', ''))}`",
        f"- Pre selftest fail=0: `{summary.get('pre_selftest_fail0', False)}`",
        f"- Post selftest fail=0: `{summary.get('post_selftest_fail0', False)}`",
        f"- DRM node: `{values.get('probe.node', '/dev/dri/card0')}`",
        f"- Universal planes cap rc: `{values.get('probe.client_cap.universal_planes.rc', '')}`",
        f"- Atomic client cap rc: `{values.get('probe.client_cap.atomic.rc', '')}`",
        f"- ADD_FB2 modifiers cap: `{probe.get('addfb2_modifiers', 0)}`",
        f"- PRIME cap: `{values.get('probe.cap.prime', '')}`",
        f"- Resources: `{values.get('probe.resources.crtcs', '')}`",
        f"- Active path: `{values.get('probe.active.source', '')}` connector=`{values.get('probe.active.connector_id', '')}` "
        f"crtc=`{values.get('probe.active.crtc_id', '')}` current_plane=`{values.get('probe.active.current_plane_id', '')}`",
        f"- Plane count: `{probe.get('plane_count', 0)}`",
        f"- Compatible active-CRTC planes: `{probe.get('compatible_plane_count', 0)}`",
        f"- Planes with src/dst rectangle properties: `{probe.get('rect_props_plane_count', 0)}`",
        f"- XBGR8888 LINEAR planes: `{probe.get('xbgr_linear_plane_count', 0)}`",
        f"- XBGR8888 QCOM_TILED3 planes: `{probe.get('xbgr_tiled3_plane_count', 0)}`",
        f"- XBGR8888 QCOM_COMPRESSED planes: `{probe.get('xbgr_compressed_plane_count', 0)}`",
        f"- Candidate LINEAR planes: `{probe.get('candidate_linear_count', 0)}`",
        f"- Candidate implicit-LINEAR planes: `{probe.get('candidate_implicit_linear_count', 0)}`",
        f"- Candidate QCOM_TILED3 planes: `{probe.get('candidate_tiled3_count', 0)}`",
        f"- Candidate QCOM_COMPRESSED planes: `{probe.get('candidate_compressed_count', 0)}`",
        f"- Helper result: `{probe.get('result', '')}`",
        "",
        "## Candidate Planes",
        "",
    ]
    if candidates:
        for index, plane in candidates:
            implicit_linear = "1" if plane.get("has_xbgr8888") == "1" and plane.get("in_formats_in_formats.has") == "0" else "0"
            lines.append(
                f"- plane {index}: id=`{plane.get('id', '')}` "
                f"formats=`{plane.get('formats_sample', '')}` "
                f"modifiers=`{plane.get('modifiers_names', '')}` "
                f"implicit_linear=`{implicit_linear}` "
                f"XB24 linear=`{plane.get('xb24_linear', '')}` "
                f"tiled3=`{plane.get('xb24_qcom_tiled3', '')}` "
                f"compressed=`{plane.get('xb24_qcom_compressed', '')}`"
            )
    else:
        lines.append("- no active-CRTC-compatible XBGR8888 plane/modifier candidate was found")

    lines.extend([
        "",
        "## Freedreno / Layout Grounding",
        "",
        f"- Mesa reference: `{MESA_FD6_RESOURCE}` maps `DRM_FORMAT_MOD_LINEAR` to `TILE6_LINEAR`,",
        "  `DRM_FORMAT_MOD_QCOM_TILED3` to `TILE6_3`, and `DRM_FORMAT_MOD_QCOM_COMPRESSED` to",
        "  UBWC plus `TILE6_3`.",
        f"- DRM UAPI reference: `{MESA_DRM_FOURCC}` defines the Qualcomm compressed, tiled3, and tiled2",
        "  modifiers used by the helper.",
        f"- Current A90 GPU present path: `{rel(GPU_SOURCE)}` renders into KGSL BO `session->linear`,",
        "  syncs it from GPU, then `memcpy`s each line into the KMS framebuffer. That CPU copy is the",
        "  step Z1/Z2 must remove.",
        "",
        "## Feasibility Decision",
        "",
    ])
    if decision == DECISION_LINEAR:
        lines.extend([
            "Zero-copy is feasible enough to proceed, with the lowest-risk route being a shared",
            "linear `XBGR8888` scanout target. The display plane accepts a compatible LINEAR",
            "modifier and the current GPU shader path already emits a `TILE6_LINEAR` final target.",
            "",
            "Exact Z1 recipe:",
            "",
            "- Format: `DRM_FORMAT_XBGR8888` (`XB24`).",
            "- Modifier: `DRM_FORMAT_MOD_LINEAR`.",
            "- Size/stride: keep the existing 960x720 GPU output, `stride=3840`, `bytes=2764800`.",
            "- Allocate a scanout-shareable buffer, import/export it as a dma-buf/GEM handle, bind its",
            "  GPU iova into the shared KGSL helper, and create the KMS FB with `ADDFB2` + modifier.",
            "- Keep the existing CPU-copy present path as fallback until the shared-buffer proof passes.",
        ])
    elif decision == DECISION_IMPLICIT_LINEAR:
        lines.extend([
            "Zero-copy is feasible enough to investigate, but only through legacy/implicit linear",
            "scanout. The display driver exposes RGB plane formats and `ADDFB2_MODIFIERS`, but no",
            "plane has an `IN_FORMATS` modifier blob, so Z0 cannot use an explicit tiled/UBWC",
            "modifier contract. The already-live KMS path proves implicit linear scanout through",
            "dumb/GEM framebuffers; zero-copy must therefore start from a scanout-shareable linear",
            "buffer, not from a KGSL-only tiled/compressed render target.",
            "",
            "Exact Z1 recipe:",
            "",
            "- Format: `DRM_FORMAT_XBGR8888` (`XB24`).",
            "- Modifier: implicit/legacy linear, not an explicit `IN_FORMATS` modifier.",
            "- Size/stride: keep the existing 960x720 GPU output, `stride=3840`, `bytes=2764800`.",
            "- First prove a shared linear allocation path. Preferred probe: allocate `msm` DRM GEM",
            "  with `MSM_BO_SCANOUT | MSM_BO_WC`, get `MSM_INFO_GET_IOVA`/mmap metadata, create the",
            "  KMS FB, and verify whether the existing GPU submit path can target the same memory.",
            "- If KGSL cannot import or target that GEM/dma-buf, do not force this through KGSL;",
            "  either pivot the submit path to DRM `msm` for this rung or close zero-copy as not",
            "  feasible on the current KGSL path.",
            "- Keep the existing CPU-copy present path as fallback until the shared-buffer proof passes.",
        ])
    elif decision == DECISION_TILED3:
        lines.extend([
            "A zero-copy path may be feasible through `QCOM_TILED3`, but it requires switching the",
            "final GPU render target from the current linear target to `TILE6_3` and proving KMS",
            "can scan the same tiled layout. This is higher risk than the linear path.",
        ])
    elif decision == DECISION_COMPRESSED:
        lines.extend([
            "A matching compressed modifier exists, but UBWC needs flag-buffer and metadata handling.",
            "Treat this as a later optimization, not the first Z1 implementation route.",
        ])
    else:
        lines.extend([
            "The live plane inventory did not expose a matching active-CRTC-compatible modifier for",
            "the current GPU output. Keep the CPU-copy KMS path and do not spend a Z1 flash on",
            "zero-copy until new display-plane evidence appears.",
        ])
    lines.extend([
        "",
        "## Remaining Z1 Proof",
        "",
        "Z0 proves the display-side modifier choice. It does not yet prove the allocator bridge.",
        "The next source unit must prove one shared allocation path before presenting it: either",
        "`msm` DRM GEM with `MSM_BO_SCANOUT` exported/imported to the GPU path, or KGSL memory",
        "exported/imported to DRM. If the available KGSL UAPI cannot import a dma-buf directly,",
        "pivot to the MSM DRM submit path for the shared scanout BO or stop zero-copy at Z0.",
        "",
        "## Validation",
        "",
        f"- Runner: `{rel(REPO_ROOT / 'workspace/public/src/scripts/revalidation/native_gpu_z0_modifier_recon.py')}`",
        f"- Private summary: `{summary.get('out_dir', '')}/summary.json`",
        f"- Pass: `{summary.get('pass', False)}`",
        "",
    ])
    return "\n".join(lines)


def run_live(args: argparse.Namespace) -> dict[str, Any]:
    out_dir = PRIVATE_RUNS / f"v3322-gpu-z0-modifier-recon-{now_label()}"
    out_dir.mkdir(parents=True, exist_ok=True)
    steps: list[live_base.StepResult] = []
    summary: dict[str, Any] = {
        "run_id": RUN_ID,
        "out_dir": str(out_dir.relative_to(REPO_ROOT)),
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "helper_source": rel(HELPER_SOURCE),
        "remote_helper": REMOTE_HELPER,
        "safety": {
            "flash_reboot": False,
            "partition_or_firmware_write": False,
            "display_mutation": False,
            "power_write": False,
            "drm_read_only_inventory": True,
        },
    }
    try:
        os.environ.setdefault("A90CTL_INPUT_CHAR_DELAY_SEC", "0.25")
        live_base.run_host(out_dir, steps, "bridge-status", [
            sys.executable,
            str(SCRIPT_DIR / "a90_bridge.py"),
            "status",
            "--json",
        ], timeout=30, allow_error=True)
        version = live_base.a90ctl(args, out_dir, steps, "resident-version", ["version"], timeout=90, allow_error=True)
        live_base.a90ctl(args, out_dir, steps, "resident-status", ["status"], timeout=90, allow_error=True)
        pre_selftest = live_base.a90ctl(args, out_dir, steps, "resident-selftest", ["selftest"], timeout=90, allow_error=True)
        summary["resident_version"] = version.strip()
        summary["version_ok"] = "A90 Linux init" in version
        summary["pre_selftest_fail0"] = "fail=0" in pre_selftest

        build_dir = out_dir / "build"
        build_dir.mkdir(parents=True, exist_ok=True)
        helper_bin = live_base.build_helper(
            build_dir,
            steps,
            source=HELPER_SOURCE,
            output_name="a90_drm_modifier_probe_z0",
            cc=args.cc,
            strip=args.strip,
        )
        summary["build"] = {
            "helper_local": str(helper_bin.relative_to(REPO_ROOT)),
            "helper_sha256": live_base.sha256_file(helper_bin),
            "helper_size": helper_bin.stat().st_size,
        }
        if not args.skip_install:
            install_helper(args, out_dir, steps, helper_bin, summary)

        probe_stdout = live_base.tcpctl_run(
            args,
            out_dir,
            steps,
            "gpu-z0-modifier-probe",
            [REMOTE_HELPER],
            timeout=60,
        )
        probe = parse_probe_stdout(probe_stdout)
        summary["probe"] = probe
        post_selftest = live_base.a90ctl(args, out_dir, steps, "post-selftest", ["selftest"], timeout=90, allow_error=True)
        summary["post_selftest_fail0"] = "fail=0" in post_selftest
        summary["decision"] = probe["decision"]
        summary["pass"] = bool(summary["post_selftest_fail0"] and probe.get("result"))
    except Exception as exc:
        summary["decision"] = DECISION_FAILED
        summary["pass"] = False
        summary["error"] = str(exc)
    finally:
        summary["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        summary["steps"] = [
            {
                "name": step.name,
                "returncode": step.returncode,
                "ok": step.ok,
                "elapsed_sec": step.elapsed_sec,
                "stdout_path": step.stdout_path,
                "stderr_path": step.stderr_path,
            }
            for step in steps
        ]
        write_json(out_dir / "summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bridge-host", default="127.0.0.1")
    parser.add_argument("--bridge-port", type=int, default=54321)
    parser.add_argument("--transfer-timeout", type=float, default=120.0)
    parser.add_argument("--transfer-port", type=int, default=18192)
    parser.add_argument("--transfer-delay", type=float, default=1.0)
    parser.add_argument("--connect-timeout", type=float, default=5.0)
    parser.add_argument("--device-ip", default=os.environ.get("A90_NCM_DEVICE_IP", ""))
    parser.add_argument("--toybox", default=DEFAULT_TOYBOX)
    parser.add_argument("--cc", default="aarch64-linux-gnu-gcc")
    parser.add_argument("--strip", default="aarch64-linux-gnu-strip")
    parser.add_argument("--skip-install", action="store_true")
    parser.add_argument("--serial-base64-chunk-chars", type=int, default=1024)
    parser.add_argument("--serial-chunk-timeout", type=float, default=45.0)
    parser.add_argument("--run-live", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()

    if args.run_live:
        summary = run_live(args)
    else:
        summary = {
            "run_id": RUN_ID,
            "decision": DECISION_DRY_RUN,
            "helper_source": rel(HELPER_SOURCE),
            "remote_helper": REMOTE_HELPER,
            "probe": {},
            "build": {},
            "pass": False,
        }

    if args.write_report:
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(render_report(summary), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary.get("pass") or not args.run_live else 1


if __name__ == "__main__":
    raise SystemExit(main())
