#!/usr/bin/env python3
"""V767 bounded ICNSS/QCACLD instrumented kernel build gate.

V766 proved that the A90V765 patch applies and defconfig passes. V767 prepares
the compatible Android/Samsung toolchain inside the disposable V766 source tree
and runs a bounded kernel build. It does not mutate kernel_build, write a boot
image, flash, or talk to the device.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v767-icnss-qcacld-full-build")
DEFAULT_V766_MANIFEST = Path("tmp/wifi/v766-icnss-qcacld-patch-apply-build/manifest.json")
DEFAULT_SOURCE_ROOT = Path("tmp/wifi/v766-icnss-qcacld-patch-apply-build/source")
DEFAULT_LLVM_DIR = Path("toolchains/llvm-arm-toolchain-ship-10.0")
DEFAULT_GCC_DIR = Path("toolchains/aarch64-linux-android-4.9")
DEFAULT_COMPAT_LIB_DIR = Path("toolchains/compat-libs")
DEFAULT_MAKE_BIN = Path("toolchains/make-4.3/bin/make")
DEFAULT_OPENSSL_SYSROOT = Path("toolchains/sysroots/libssl-dev")
PATCH_PREFIX = "A90V765"
DEFCONFIG = "r3q_kor_single_defconfig"


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    severity: str
    detail: str
    next_step: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v766-manifest", type=Path, default=DEFAULT_V766_MANIFEST)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--llvm-dir", type=Path, default=DEFAULT_LLVM_DIR)
    parser.add_argument("--gcc-dir", type=Path, default=DEFAULT_GCC_DIR)
    parser.add_argument("--compat-lib-dir", type=Path, default=DEFAULT_COMPAT_LIB_DIR)
    parser.add_argument("--make-bin", type=Path, default=DEFAULT_MAKE_BIN)
    parser.add_argument("--openssl-sysroot", type=Path, default=DEFAULT_OPENSSL_SYSROOT)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--build-timeout", type=float, default=1800.0)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def resolve_path(path: Path) -> Path:
    return path.expanduser() if path.is_absolute() else repo_path(path)


def load_json(path: Path) -> dict[str, Any]:
    resolved = resolve_path(path)
    if not resolved.exists():
        return {}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def file_info(path: Path) -> dict[str, Any]:
    resolved = resolve_path(path)
    if not resolved.exists():
        return {"path": str(resolved), "exists": False}
    return {
        "path": str(resolved),
        "exists": True,
        "is_file": resolved.is_file(),
        "is_dir": resolved.is_dir(),
        "size": resolved.stat().st_size if resolved.is_file() else None,
    }


def run_command(command: list[str],
                cwd: Path,
                timeout: float,
                output_file: Path,
                env: dict[str, str] | None = None) -> dict[str, Any]:
    started = dt.datetime.now(dt.timezone.utc)
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
        output_file.write_text(result.stdout, encoding="utf-8", errors="replace")
        return {
            "command": command,
            "cwd": str(cwd),
            "rc": result.returncode,
            "timeout": False,
            "output_file": str(output_file),
            "started_at": started.isoformat(),
        }
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout or ""
        if isinstance(output, bytes):
            output = output.decode("utf-8", errors="replace")
        output_file.write_text(output + "\n[TIMEOUT]\n", encoding="utf-8", errors="replace")
        return {
            "command": command,
            "cwd": str(cwd),
            "rc": None,
            "timeout": True,
            "output_file": str(output_file),
            "started_at": started.isoformat(),
        }


def ensure_compat_lib(compat_dir: Path) -> dict[str, Any]:
    compat_dir.mkdir(parents=True, mode=0o700, exist_ok=True)
    target = compat_dir / "libtinfo.so.5"
    candidates = (
        Path("/lib/x86_64-linux-gnu/libtinfo.so.6"),
        Path("/usr/lib/x86_64-linux-gnu/libtinfo.so.6"),
    )
    selected = next((candidate for candidate in candidates if candidate.exists()), None)
    if selected and not target.exists():
        target.symlink_to(selected)
    return {
        "compat_dir": str(compat_dir),
        "libtinfo5": str(target),
        "libtinfo5_exists": target.exists(),
        "selected_system_libtinfo": str(selected) if selected else "",
    }


def patch_python_shebangs(root: Path) -> list[str]:
    patched: list[str] = []
    bin_dir = root / "bin"
    for path in bin_dir.glob("aarch64-linux-android-*"):
        if not path.is_file() or path.is_symlink():
            continue
        data = path.read_bytes()
        if data.startswith(b"#!/usr/bin/python\n"):
            path.write_bytes(b"#!/usr/bin/env python3\n" + data.split(b"\n", 1)[1])
            patched.append(str(path))
    return patched


def patch_kernel_gcc_wrapper(source_root: Path) -> dict[str, Any]:
    path = source_root / "scripts/gcc-wrapper.py"
    result = {
        "path": str(path),
        "exists": path.exists(),
        "patched": False,
    }
    if not path.exists():
        return result
    text = path.read_text(encoding="utf-8", errors="replace")
    original = text
    text = text.replace("#! /usr/bin/env python2", "#!/usr/bin/env python3", 1)
    text = text.replace('print >> sys.stderr, "error, forbidden warning:", m.group(2)',
                        'print("error, forbidden warning:", m.group(2), file=sys.stderr)')
    text = text.replace("proc = subprocess.Popen(args, stderr=subprocess.PIPE)",
                        "proc = subprocess.Popen(args, stderr=subprocess.PIPE, universal_newlines=True)")
    text = text.replace("print >> sys.stderr, line,",
                        'print(line, end="", file=sys.stderr)')
    text = text.replace("print >> sys.stderr, args[0] + ':',e.strerror",
                        'print(args[0] + ":", e.strerror, file=sys.stderr)')
    text = text.replace("print >> sys.stderr, 'Is your PATH set correctly?'",
                        'print("Is your PATH set correctly?", file=sys.stderr)')
    text = text.replace("print >> sys.stderr, ' '.join(args), str(e)",
                        'print(" ".join(args), str(e), file=sys.stderr)')
    if text != original:
        path.write_text(text, encoding="utf-8")
        path.chmod(0o755)
        result["patched"] = True
    return result


def prepare_compat_bin(bin_dir: Path) -> dict[str, Any]:
    bin_dir.mkdir(parents=True, mode=0o700, exist_ok=True)
    python3 = shutil.which("python3") or "/usr/bin/python3"
    python_script = f"#!/bin/sh\nexec {python3} \"$@\"\n"
    for name in ("python", "python2"):
        path = bin_dir / name
        path.write_text(python_script, encoding="utf-8")
        path.chmod(0o700)
    secgetspf = bin_dir / "secgetspf"
    secgetspf.write_text(
        "#!/bin/sh\n"
        "case \"$1\" in\n"
        "  *FINGERPRINT_TZ*) echo false ;;\n"
        "  *) ;;\n"
        "esac\n",
        encoding="utf-8",
    )
    secgetspf.chmod(0o700)
    return {
        "bin_dir": str(bin_dir),
        "python3": python3,
        "python": str(bin_dir / "python"),
        "python2": str(bin_dir / "python2"),
        "secgetspf": str(secgetspf),
    }


def normalize_kbuild_line_endings(source_root: Path) -> list[str]:
    normalized: list[str] = []
    candidates = [
        source_root / "scripts/Makefile.lib",
        source_root / "drivers/input/wacom/Makefile",
        source_root / "drivers/gpu/drm/msm/samsung_lego/SELF_DISPLAY/Makefile",
    ]
    for path in candidates:
        if not path.exists():
            continue
        data = path.read_bytes()
        if b"\r\n" in data:
            path.write_bytes(data.replace(b"\r\n", b"\n"))
            normalized.append(str(path))
    return normalized


def patch_makefile_lib_make44(source_root: Path) -> dict[str, Any]:
    path = source_root / "scripts/Makefile.lib"
    result = {
        "path": str(path),
        "exists": path.exists(),
        "patched": False,
    }
    if not path.exists():
        return result
    text = path.read_text(encoding="utf-8", errors="replace")
    if "size_append = { \\" in text:
        return result
    start = text.find("size_append = printf $(shell")
    end_marker = "\n)\n\nquiet_cmd_bzip2"
    end = text.find(end_marker, start)
    if start < 0 or end < 0:
        result["error"] = "size_append block not found"
        return result
    replacement = "\n".join([
        "size_append = { \\",
        "\tdec_size=0; \\",
        "\tfor F in $1; do \\",
        "\t\tfsize=$$(stat -c \"%s\" $$F); \\",
        "\t\tdec_size=$$(expr $$dec_size + $$fsize); \\",
        "\tdone; \\",
        "\tprintf \"%08x\\n\" $$dec_size | sed 's/\\(..\\)/\\1 /g' | { \\",
        "\t\tread ch0 ch1 ch2 ch3; \\",
        "\t\tfor ch in $$ch3 $$ch2 $$ch1 $$ch0; do \\",
        "\t\t\tprintf '%s%03o' '\\\\' $$((0x$$ch)); \\",
        "\t\tdone; \\",
        "\t}; \\",
        "}",
    ])
    text = text[:start] + replacement + text[end + 3:]
    path.write_text(text, encoding="utf-8")
    result["patched"] = True
    return result


def prepare_ion_uapi_headers(source_root: Path) -> dict[str, Any]:
    source_dir = source_root / "drivers/staging/android/uapi"
    target_dir = source_root / "include/uapi/linux"
    copied: list[str] = []
    missing: list[str] = []
    target_dir.mkdir(parents=True, exist_ok=True)
    for name in ("ion.h", "msm_ion.h"):
        source = source_dir / name
        target = target_dir / name
        if not source.exists():
            missing.append(str(source))
            continue
        if not target.exists() or target.read_bytes() != source.read_bytes():
            shutil.copy2(source, target)
            copied.append(str(target))
    return {
        "source_dir": str(source_dir),
        "target_dir": str(target_dir),
        "copied": copied,
        "missing": missing,
    }


def prepare_audio_kernel_build_paths(source_root: Path) -> dict[str, Any]:
    audio_root = source_root / "techpack/audio"
    out_root = source_root / "out/kernel"
    linked: list[str] = []
    if not audio_root.exists():
        return {
            "audio_root": str(audio_root),
            "linked": linked,
            "missing": [str(audio_root)],
        }
    for kernel_dir in ("msm-4.14", "msm-4.19"):
        target = out_root / kernel_dir / "techpack/audio"
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() or target.is_symlink():
            if target.is_symlink() or target.is_file():
                target.unlink()
            else:
                shutil.rmtree(target)
        target.symlink_to(audio_root)
        linked.append(str(target))
    return {
        "audio_root": str(audio_root),
        "linked": linked,
        "missing": [],
    }


def prepare_audio_soc_headers(source_root: Path) -> dict[str, Any]:
    source_dir = source_root / "techpack/audio/4.0/soc"
    target_dir = source_root / "techpack/audio/soc"
    copied: list[str] = []
    missing: list[str] = []
    for name in ("core.h", "pinctrl-utils.h", "wcd-spi-ac.c", "wcd_spi_ctl_v01.c", "wcd_spi_ctl_v01.h"):
        source = source_dir / name
        target = target_dir / name
        if not source.exists():
            missing.append(str(source))
            continue
        if not target.exists() or target.read_bytes() != source.read_bytes():
            shutil.copy2(source, target)
            copied.append(str(target))
    return {
        "source_dir": str(source_dir),
        "target_dir": str(target_dir),
        "copied": copied,
        "missing": missing,
    }


def prepare_audio_include_headers(source_root: Path) -> dict[str, Any]:
    source_root_dir = source_root / "techpack/audio/4.0/include"
    target_root_dir = source_root / "techpack/audio/include"
    copied: list[str] = []
    missing: list[str] = []
    for subdir in ("soc", "dsp", "ipc", "uapi", "asoc"):
        source_dir = source_root_dir / subdir
        target_dir = target_root_dir / subdir
        if not source_dir.exists():
            missing.append(str(source_dir))
            continue
        target_dir.mkdir(parents=True, exist_ok=True)
        for source in source_dir.rglob("*"):
            if not source.is_file():
                continue
            target = target_dir / source.relative_to(source_dir)
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                shutil.copy2(source, target)
                copied.append(str(target))
    return {
        "source_root": str(source_root_dir),
        "target_root": str(target_root_dir),
        "copied": copied,
        "missing": missing,
    }


def prepare_toolchain_tree(source_root: Path, llvm_dir: Path, gcc_dir: Path) -> dict[str, Any]:
    gcc_dest = source_root / "toolchain/gcc/linux-x86/aarch64/aarch64-linux-android-4.9"
    llvm_dest = source_root / "toolchain/llvm-arm-toolchain-ship/10.0"
    gcc_dest.parent.mkdir(parents=True, exist_ok=True)
    llvm_dest.parent.mkdir(parents=True, exist_ok=True)
    if gcc_dest.exists() or gcc_dest.is_symlink():
        if gcc_dest.is_symlink() or gcc_dest.is_file():
            gcc_dest.unlink()
        else:
            shutil.rmtree(gcc_dest)
    shutil.copytree(gcc_dir, gcc_dest, symlinks=True)
    patched_shebangs = patch_python_shebangs(gcc_dest)
    if llvm_dest.exists() or llvm_dest.is_symlink():
        if llvm_dest.is_symlink() or llvm_dest.is_file():
            llvm_dest.unlink()
        else:
            shutil.rmtree(llvm_dest)
    llvm_dest.symlink_to(llvm_dir)
    return {
        "gcc_dest": str(gcc_dest),
        "llvm_dest": str(llvm_dest),
        "patched_shebangs": patched_shebangs,
        "cross_compile": str(gcc_dest / "bin/aarch64-linux-android-"),
        "real_cc": str(llvm_dest / "bin/clang"),
    }


def count_markers(source_root: Path) -> int:
    total = 0
    for path in (
        source_root / "drivers/soc/qcom/icnss_qmi.c",
        source_root / "drivers/soc/qcom/icnss.c",
        source_root / "drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0/core/pld/src/pld_snoc.c",
        source_root / "drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0/core/hdd/src/wlan_hdd_main.c",
        source_root / "drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0/core/hdd/src/wlan_hdd_driver_ops.c",
    ):
        if path.exists():
            total += path.read_text(encoding="utf-8", errors="replace").count(PATCH_PREFIX)
    return total


def add_check(checks: list[Check], name: str, status: str, severity: str, detail: str, next_step: str) -> None:
    checks.append(Check(name, status, severity, detail, next_step))


def build_checks(manifest: dict[str, Any]) -> list[Check]:
    analysis = manifest["analysis"]
    checks: list[Check] = []
    v766 = analysis["inputs"]["v766"]
    toolchain = analysis.get("toolchain", {})
    build = analysis.get("build", {})
    add_check(
        checks,
        "v766-input",
        "pass" if v766.get("decision") == "v766-patch-applied-defconfig-pass-toolchain-incomplete" and v766.get("pass") else "blocked",
        "blocker",
        f"decision={v766.get('decision')} pass={v766.get('pass')}",
        "rerun/fix V766 before V767",
    )
    add_check(
        checks,
        "source-root",
        "pass" if analysis["paths"]["source_root"].get("exists") and analysis["paths"]["source_root"].get("is_dir") else "blocked",
        "blocker",
        f"path={analysis['paths']['source_root'].get('path')} exists={analysis['paths']['source_root'].get('exists')}",
        "restore V766 disposable source root",
    )
    add_check(
        checks,
        "patch-markers",
        "pass" if analysis.get("patch_marker_count") == 19 else "blocked",
        "blocker",
        f"count={analysis.get('patch_marker_count')}",
        "rerun V766 patch apply before build",
    )
    add_check(
        checks,
        "llvm-clang",
        "pass" if toolchain.get("clang_version", {}).get("rc") == 0 else "blocked",
        "blocker",
        f"rc={toolchain.get('clang_version', {}).get('rc')} timeout={toolchain.get('clang_version', {}).get('timeout')}",
        "fix clang/libtinfo compatibility before build",
    )
    add_check(
        checks,
        "gcc-wrapper",
        "pass" if toolchain.get("gcc_version", {}).get("rc") == 0 else "blocked",
        "blocker",
        f"rc={toolchain.get('gcc_version', {}).get('rc')} timeout={toolchain.get('gcc_version', {}).get('timeout')}",
        "fix GCC wrapper/python compatibility before build",
    )
    if manifest["command"] == "plan":
        return checks
    add_check(
        checks,
        "kernel-build",
        "pass" if build.get("rc") == 0 else "warn",
        "warn",
        f"rc={build.get('rc')} timeout={build.get('timeout')} image={analysis.get('artifacts', {}).get('image_exists')} first_error={analysis.get('build_failure', {}).get('first_error', '')}",
        "inspect build log and fix the first compile/link blocker",
    )
    return checks


def blocking(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def decide(command: str, checks: list[Check], analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v767-toolchain-full-build-plan-ready",
            True,
            "plan-only; no toolchain copy, build, boot image write, or device action executed",
            "run V767 bounded full build gate",
        )
    blockers = blocking(checks)
    if blockers:
        return (
            "v767-toolchain-full-build-blocked",
            False,
            "blocked by " + ", ".join(blockers),
            "fix toolchain prerequisites before kernel build",
        )
    build = analysis.get("build", {})
    artifacts = analysis.get("artifacts", {})
    if build.get("rc") == 0 and artifacts.get("image_exists"):
        return (
            "v767-instrumented-kernel-build-pass",
            True,
            "instrumented kernel build produced Image in disposable source tree",
            "V768 should package boot image or run mdm3/esoc parallel classifier; no flash yet",
        )
    instrumented_objects = analysis.get("instrumented_objects", {})
    build_failure = analysis.get("build_failure", {})
    if instrumented_objects.get("all_exist") and instrumented_objects.get("marker_total", 0) > 0:
        if "SyntaxError" in build_failure.get("first_error", "") or "instrument.py" in " ".join(build_failure.get("errors", [])):
            return (
                "v767-instrumented-objects-built-rkp-cfp-python2-blocked",
                True,
                "ICNSS/QCACLD instrumented objects built; final Image blocked by Python2-only RKP_CFP post-link step",
                "treat V765 patch compile as proven; decide between RKP_CFP compatibility work and mdm3/esoc classifier branch",
            )
        return (
            "v767-instrumented-objects-built-postlink-blocked",
            True,
            "ICNSS/QCACLD instrumented objects built; final Image blocked after Wi-Fi object compilation",
            "inspect post-object build failure before packaging",
        )
    return (
        "v767-instrumented-kernel-build-failed-classified",
        True,
        "toolchain prerequisites passed but bounded kernel build failed; evidence captured",
        "inspect V767 build log and fix first build blocker before packaging",
    )


def build_env(args: argparse.Namespace, compat: dict[str, Any], prepared: dict[str, Any]) -> dict[str, str]:
    env = os.environ.copy()
    env["ARCH"] = "arm64"
    env["SUBARCH"] = "arm64"
    env["CROSS_COMPILE"] = prepared["cross_compile"]
    env["REAL_CC"] = prepared["real_cc"]
    env["CLANG_TRIPLE"] = "aarch64-linux-gnu-"
    env["PYTHON"] = "python3"
    env["LD_LIBRARY_PATH"] = str(resolve_path(args.compat_lib_dir)) + (
        os.pathsep + env["LD_LIBRARY_PATH"] if env.get("LD_LIBRARY_PATH") else ""
    )
    openssl_sysroot = resolve_path(args.openssl_sysroot)
    openssl_include = openssl_sysroot / "usr/include"
    openssl_multiarch_include = openssl_sysroot / "usr/include/x86_64-linux-gnu"
    openssl_lib = openssl_sysroot / "usr/lib/x86_64-linux-gnu"
    if openssl_include.exists():
        cpath_entries = [str(openssl_include)]
        if openssl_multiarch_include.exists():
            cpath_entries.append(str(openssl_multiarch_include))
        env["CPATH"] = os.pathsep.join(cpath_entries) + (
            os.pathsep + env["CPATH"] if env.get("CPATH") else ""
        )
        env["HOSTCFLAGS"] = f"-I{openssl_include}" + (
            " " + env["HOSTCFLAGS"] if env.get("HOSTCFLAGS") else ""
        )
    if openssl_lib.exists():
        env["LIBRARY_PATH"] = str(openssl_lib) + (
            os.pathsep + env["LIBRARY_PATH"] if env.get("LIBRARY_PATH") else ""
        )
        env["HOSTLDFLAGS"] = f"-L{openssl_lib}" + (
            " " + env["HOSTLDFLAGS"] if env.get("HOSTLDFLAGS") else ""
        )
    compat_bin = prepared.get("compat_bin", "")
    if compat_bin:
        env["PATH"] = compat_bin + os.pathsep + env.get("PATH", "")
    return env


def extract_build_failure(output_file: str) -> dict[str, Any]:
    path = Path(output_file) if output_file else Path()
    result: dict[str, Any] = {
        "output_file": output_file,
        "first_error": "",
        "errors": [],
    }
    if not output_file or not path.exists():
        return result
    patterns = (
        "fatal error:",
        " error:",
        "No such file",
        "No such",
        "not found",
        "undefined reference",
        "SyntaxError",
        "Error ",
        "오류",
    )
    errors: list[str] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if any(pattern in line for pattern in patterns):
            errors.append(line.strip())
            if len(errors) >= 20:
                break
    result["errors"] = errors
    result["first_error"] = errors[0] if errors else ""
    return result


def collect_instrumented_objects(source_root: Path) -> dict[str, Any]:
    object_paths = [
        source_root / "out/drivers/soc/qcom/icnss_qmi.o",
        source_root / "out/drivers/soc/qcom/icnss.o",
        source_root / "out/drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0/core/pld/src/pld_snoc.o",
        source_root / "out/drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0/core/hdd/src/wlan_hdd_main.o",
        source_root / "out/drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0/core/hdd/src/wlan_hdd_driver_ops.o",
    ]
    objects: list[dict[str, Any]] = []
    marker_total = 0
    for path in object_paths:
        info = file_info(path)
        marker_count = path.read_bytes().count(PATCH_PREFIX.encode("ascii")) if path.exists() else 0
        marker_total += marker_count
        info["a90v765_marker_count"] = marker_count
        info["relative_path"] = str(path.relative_to(source_root))
        objects.append(info)
    return {
        "objects": objects,
        "all_exist": all(item.get("exists") for item in objects),
        "marker_total": marker_total,
        "objects_with_markers": sum(1 for item in objects if item.get("a90v765_marker_count", 0) > 0),
    }


def build_analysis(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    source_root = resolve_path(args.source_root)
    llvm_dir = resolve_path(args.llvm_dir)
    gcc_dir = resolve_path(args.gcc_dir)
    compat_dir = resolve_path(args.compat_lib_dir)
    make_bin = resolve_path(args.make_bin)
    v766 = load_json(args.v766_manifest)
    analysis: dict[str, Any] = {
        "inputs": {
            "v766": {
                "manifest": str(resolve_path(args.v766_manifest)),
                "decision": v766.get("decision", ""),
                "pass": bool(v766.get("pass")),
            },
        },
        "paths": {
            "source_root": file_info(args.source_root),
            "llvm_dir": file_info(args.llvm_dir),
            "gcc_dir": file_info(args.gcc_dir),
            "compat_lib_dir": file_info(args.compat_lib_dir),
            "make_bin": file_info(args.make_bin),
            "openssl_sysroot": file_info(args.openssl_sysroot),
        },
        "patch_marker_count": count_markers(source_root) if source_root.exists() else 0,
        "source_mutation_scope": "tmp/wifi disposable source tree only",
        "kernel_build_executed": False,
        "boot_image_write_executed": False,
        "device_commands_executed": False,
    }
    logs = store.run_dir / "logs"
    logs.mkdir(parents=True, mode=0o700, exist_ok=True)
    if args.command == "plan":
        return analysis
    compat_bin = prepare_compat_bin(store.run_dir / "bin")
    compat = ensure_compat_lib(compat_dir)
    prepared = prepare_toolchain_tree(source_root, llvm_dir, gcc_dir)
    prepared["compat_bin"] = compat_bin["bin_dir"]
    gcc_wrapper = patch_kernel_gcc_wrapper(source_root)
    normalized_makefiles = normalize_kbuild_line_endings(source_root)
    makefile_lib = patch_makefile_lib_make44(source_root)
    ion_uapi_headers = prepare_ion_uapi_headers(source_root)
    audio_kernel_build_paths = prepare_audio_kernel_build_paths(source_root)
    audio_soc_headers = prepare_audio_soc_headers(source_root)
    audio_include_headers = prepare_audio_include_headers(source_root)
    env = build_env(args, compat, prepared)
    clang_version = run_command([prepared["real_cc"], "--version"], source_root, 30.0, logs / "clang-version.txt", env)
    gcc_version = run_command([prepared["cross_compile"] + "gcc", "--version"], source_root, 30.0, logs / "gcc-version.txt", env)
    analysis["toolchain"] = {
        "compat": compat,
        "compat_bin": compat_bin,
        "prepared": prepared,
        "kernel_gcc_wrapper": gcc_wrapper,
        "normalized_makefiles": normalized_makefiles,
        "makefile_lib_make44": makefile_lib,
        "ion_uapi_headers": ion_uapi_headers,
        "audio_kernel_build_paths": audio_kernel_build_paths,
        "audio_soc_headers": audio_soc_headers,
        "audio_include_headers": audio_include_headers,
        "clang_version": clang_version,
        "gcc_version": gcc_version,
    }
    if clang_version["rc"] == 0 and gcc_version["rc"] == 0:
        command = [
            str(make_bin),
            f"-j{max(1, args.jobs)}",
            f"O={source_root / 'out'}",
            f"DTC_EXT={source_root / 'tools/dtc'}",
            "CONFIG_BUILD_ARM64_DT_OVERLAY=y",
            "ARCH=arm64",
            f"CROSS_COMPILE={prepared['cross_compile']}",
            f"REAL_CC={prepared['real_cc']}",
            "CLANG_TRIPLE=aarch64-linux-gnu-",
            "PYTHON=python3",
        ]
        build = run_command(command, source_root, args.build_timeout, logs / "kernel-build.txt", env)
        analysis["kernel_build_executed"] = True
    else:
        build = {"command": [], "cwd": str(source_root), "rc": None, "timeout": False, "output_file": ""}
    image = source_root / "out/arch/arm64/boot/Image"
    image_dtb = source_root / "out/arch/arm64/boot/Image-dtb"
    image_gz = source_root / "out/arch/arm64/boot/Image.gz"
    analysis["build"] = build
    analysis["build_failure"] = extract_build_failure(str(build.get("output_file", "")))
    analysis["instrumented_objects"] = collect_instrumented_objects(source_root)
    analysis["artifacts"] = {
        "image": file_info(image),
        "image_exists": image.exists(),
        "image_dtb": file_info(image_dtb),
        "image_dtb_exists": image_dtb.exists(),
        "image_gz": file_info(image_gz),
        "image_gz_exists": image_gz.exists(),
    }
    return analysis


def render_summary(manifest: dict[str, Any]) -> str:
    checks = manifest.get("checks") or []
    analysis = manifest.get("analysis") or {}
    return "\n".join([
        "# V767 ICNSS/QCACLD Instrumented Kernel Build",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- kernel_build_executed: `{manifest['kernel_build_executed']}`",
        f"- boot_image_write_executed: `{manifest['boot_image_write_executed']}`",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], [
            [check["name"], check["status"], check["severity"], check["detail"], check["next_step"]]
            for check in checks
        ]) if checks else "- none",
        "",
        "## Artifacts",
        "",
        markdown_table(["signal", "value"], [
            [key, value] for key, value in (analysis.get("artifacts") or {}).items()
        ]) if analysis.get("artifacts") else "- not run",
        "",
        "## Instrumented Objects",
        "",
        markdown_table(["relative_path", "exists", "markers"], [
            [item.get("relative_path"), item.get("exists"), item.get("a90v765_marker_count")]
            for item in (analysis.get("instrumented_objects") or {}).get("objects", [])
        ]) if analysis.get("instrumented_objects") else "- not run",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    analysis = build_analysis(args, store)
    manifest: dict[str, Any] = {
        "cycle": "v767",
        "generated_at": now_iso(),
        "command": args.command,
        "analysis": analysis,
        "kernel_build_executed": bool(analysis.get("kernel_build_executed")),
        "boot_image_write_executed": False,
        "partition_write_executed": False,
        "device_commands_executed": False,
        "device_mutations": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "host": collect_host_metadata(),
    }
    checks = build_checks(manifest)
    decision, ok, reason, next_step = decide(args.command, checks, analysis)
    manifest.update({
        "checks": [asdict(check) for check in checks],
        "decision": decision,
        "pass": ok,
        "reason": reason,
        "next_step": next_step,
    })
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    return manifest


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    latest = repo_path("tmp/wifi/latest-v767-icnss-qcacld-full-build.txt")
    write_private_text(latest, str(store.run_dir.relative_to(repo_path(Path(".")))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"kernel_build_executed: {manifest['kernel_build_executed']}")
    print(f"boot_image_write_executed: {manifest['boot_image_write_executed']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
