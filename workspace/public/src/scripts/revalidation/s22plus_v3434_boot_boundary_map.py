#!/usr/bin/env python3
"""Build the host-only S22+ V3434 boot-boundary and observer map.

This unit reads pinned local source, firmware, and prior live evidence. It never
contacts a device, builds or flashes an image, or authorizes live work.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import struct
import subprocess
import tarfile
import tempfile
from pathlib import Path
from typing import Any


SCHEMA = "s22plus_v3434_boot_boundary_map_v1"
TARGET = "SM-S906N/g0q/S906NKSS7FYG8"

SOURCE_ARCHIVE = Path(
    "workspace/private/inputs/s22plus_kernel_source/"
    "SM-S906N_15_base_osrc/Kernel.tar.gz"
)
MAGISK_KERNEL = Path(
    "workspace/private/outputs/s22plus_native_init/"
    "v3432_pid1_keystone_v0_1/magiskboot-work/kernel"
)
STOCK_BOOT = Path(
    "workspace/private/inputs/s22plus_firmware/S906NKSS7FYG8_SKC/"
    "extracted-images/raw/boot.img"
)
STOCK_VENDOR_BOOT = Path(
    "workspace/private/inputs/s22plus_firmware/S906NKSS7FYG8_SKC/"
    "extracted-images/raw/vendor_boot.img"
)
VENDOR_BOOTCONFIG = Path(
    "workspace/private/inputs/s22plus_firmware/S906NKSS7FYG8_SKC/"
    "extracted-images/unpack-vendor-boot/bootconfig"
)
LIVE_CMDLINE = Path(
    "workspace/private/runs/"
    "s22plus_o3r1_native_retained_sysrq_live_gate_20260709T220014Z/"
    "sec_debug_state/pre_o3r1/proc__cmdline.txt"
)
LIVE_BOOTCONFIG = LIVE_CMDLINE.with_name("proc__bootconfig.txt")
V3433_LAST_KMSG = Path(
    "workspace/private/runs/"
    "s22plus_v3433_pid1_keystone_20260710T205924Z/"
    "first_boot_last_kmsg_1.bin"
)
MODULE_MAP = Path("docs/module-map/s22plus-fyg8/manifest.json")
RETENTION_MAP = Path("docs/module-map/s22plus-fyg8/subsystem-retention.md")
MODULES_LOAD = Path(
    "workspace/private/inputs/s22plus_firmware/S906NKSS7FYG8_SKC/"
    "extracted-images/ramdisk-list/vendor/extract/lib/modules/modules.load"
)
BL_TAR = Path(
    "workspace/private/inputs/firmware/"
    "SAMFW.COM_SM-S906N_SKC_S906NKSS7FYG8_fac/"
    "BL_S906NKSS7FYG8_S906NKSS7FYG8_MQB99315260_REV00_user_low_ship_"
    "MULTI_CERT.tar.md5"
)
MAGISKBOOT = Path("workspace/private/tools/magisk-v30.7/magiskboot")

REPORTS = {
    "o11_control_pass": Path(
        "docs/reports/NATIVE_INIT_V3409_S22PLUS_O11_LIVE_PASS_2026-07-10.md"
    ),
    "m31b_watchdog_pass": Path(
        "docs/reports/S22PLUS_NATIVE_INIT_M31B_WDT_MANAGED_PARK_LIVE_RESULT_"
        "2026-07-09.md"
    ),
    "pmic_pon_analysis": Path(
        "docs/reports/S22PLUS_PMIC_PON_ABNORMAL_RESET_IS_THE_WALL_2026-07-09.md"
    ),
    "v3433_no_proof": Path(
        "docs/reports/NATIVE_INIT_V3433_S22PLUS_V3432_PID1_KEYSTONE_"
        "LIVE_NO_PROOF_2026-07-11.md"
    ),
}

PINS = {
    SOURCE_ARCHIVE: "86e2f73412c65fadff0b15bbf0eac9140610f70250514ac0bddbf3b53fb5f7bf",
    MAGISK_KERNEL: "bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff",
    STOCK_BOOT: "4150b962314e6136acba61b20f471d6ee1c418b83cf8c3ee4d9cf7c91a3640ae",
    STOCK_VENDOR_BOOT: "096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7",
    VENDOR_BOOTCONFIG: "5ddbc37b0c55315477c35d7801b00d001a08e274dd2c0e44530900c68b1f5420",
    LIVE_CMDLINE: "a27cc8f2a1fbfecb5b38b28b5678f76f937c2f346421b1fc6a758814572e75c8",
    LIVE_BOOTCONFIG: "7f8709ef32d6a1cfa637ecdeba069583435a2405b1bf73d0a90614eccca86ca7",
    V3433_LAST_KMSG: "ea9030d4f9d8b5f781079a98db8f77b818f95a1b2fb78b90a09b8e15eeb8239f",
    MODULE_MAP: "be2d03388cfe9b5d7a17fa63e296eb10ee48f91f081fc0160ea821ab00df61aa",
    RETENTION_MAP: "e3729435cacaf0b0d9d156169f941f2c09bae48d9aa7bc6773200dead42dfa70",
    MODULES_LOAD: "8491b842e6e05cfba42694ad003301a6598e8d152ec10cc8f0cc6fb17f10e232",
    BL_TAR: "e5aeb59de4ed16c21111945900aeda4743b717361b0919084e9d284d08e4e0ba",
    REPORTS["o11_control_pass"]: "6cb9792eae3a17e5c17f05f121671452c5dd692566f3e04508a4292df0ee9395",
    REPORTS["m31b_watchdog_pass"]: "7e2a866ddc49c9f472fe4a04a25b4be83e2376b29fec8fb2f84b138ca72971db",
    REPORTS["pmic_pon_analysis"]: "11dc629eed478540e3a1af0abb74a1a31047286ad8f414e01ba8842694f564b0",
    REPORTS["v3433_no_proof"]: "ecf20e75bfaf0af392dcf218b9c68c638c9c1fc77de9264ea152a14d4d231f6d",
}

MAIN_SOURCE = "kernel_platform/common/init/main.c"
INITRAMFS_SOURCE = "kernel_platform/common/init/initramfs.c"
EXIT_SOURCE = "kernel_platform/common/kernel/exit.c"
WATCHDOG_SOURCE = "kernel_platform/common/drivers/watchdog/watchdog_dev.c"
SEC_LOG_BUF_SOURCE = (
    "kernel_platform/msm-kernel/drivers/samsung/debug/log_buf/"
    "sec_log_buf_main.c"
)
SEC_DEBUG_SOURCE = (
    "kernel_platform/msm-kernel/drivers/samsung/debug/common/sec_debug_main.c"
)

OUTPUT = Path("docs/plans/s22plus-v3434-boot-boundary-map.json")


class MapError(RuntimeError):
    pass


def repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".git").is_dir():
            return parent
    raise MapError("repository root not found")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else root / path


def verify_pins(root: Path) -> dict[str, str]:
    verified: dict[str, str] = {}
    for relative, expected in PINS.items():
        path = resolve(root, relative)
        if not path.is_file():
            raise MapError(f"missing pinned input: {relative}")
        actual = sha256_file(path)
        if actual != expected:
            raise MapError(f"pin mismatch for {relative}: {actual} != {expected}")
        verified[str(relative)] = actual
    return verified


def tar_texts(archive: Path, members: tuple[str, ...]) -> dict[str, str]:
    pending = set(members)
    output: dict[str, str] = {}
    with tarfile.open(archive, "r:gz") as tar:
        for info in tar:
            if info.name not in pending:
                continue
            extracted = tar.extractfile(info)
            if extracted is None:
                raise MapError(f"could not extract source member: {info.name}")
            output[info.name] = extracted.read().decode("utf-8")
            pending.remove(info.name)
            if not pending:
                break
    if pending:
        raise MapError(f"missing source members: {sorted(pending)}")
    return output


def require(text: str, needle: str, label: str) -> int:
    if needle not in text:
        raise MapError(f"missing {label}: {needle}")
    return text[: text.index(needle)].count("\n") + 1


def extract_ikconfig(kernel: Path) -> dict[str, str]:
    blob = kernel.read_bytes()
    start = blob.find(b"IKCFG_ST")
    end = blob.find(b"IKCFG_ED", start + 8)
    if start < 0 or end < 0:
        raise MapError("kernel IKCONFIG payload not found")
    text = gzip.decompress(blob[start + 8 : end]).decode("utf-8")
    values: dict[str, str] = {}
    for line in text.splitlines():
        if line.startswith("CONFIG_") and "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
        elif line.startswith("# CONFIG_") and line.endswith(" is not set"):
            values[line[2 : line.index(" is not set")]] = "n"
    return values


def decode_os_version(value: int) -> dict[str, str]:
    version = ".".join(
        str(part)
        for part in ((value >> 25) & 0x7F, (value >> 18) & 0x7F, (value >> 11) & 0x7F)
    )
    patch = f"{((value >> 4) & 0x7F) + 2000:04d}-{value & 0xF:02d}"
    return {"os_version": version, "os_patch_level": patch}


def parse_boot_header(path: Path) -> dict[str, Any]:
    data = path.read_bytes()[:4096]
    if data[:8] != b"ANDROID!":
        raise MapError("stock boot magic mismatch")
    kernel_size, ramdisk_size, os_version, header_size = struct.unpack_from(
        "<4I", data, 8
    )
    header_version = struct.unpack_from("<I", data, 40)[0]
    cmdline = data[44:1580].split(b"\0", 1)[0].decode("ascii")
    signature_size = struct.unpack_from("<I", data, 1580)[0]
    return {
        "magic": "ANDROID!",
        "header_version": header_version,
        "header_size": header_size,
        "kernel_size": kernel_size,
        "ramdisk_size": ramdisk_size,
        "signature_size": signature_size,
        "cmdline": cmdline,
        **decode_os_version(os_version),
    }


def parse_vendor_boot_header(path: Path) -> dict[str, Any]:
    data = path.read_bytes()[:4096]
    if data[:8] != b"VNDRBOOT":
        raise MapError("stock vendor_boot magic mismatch")
    header_version, page_size, kernel_addr, ramdisk_addr, ramdisk_size = (
        struct.unpack_from("<5I", data, 8)
    )
    cmdline = data[28:2076].split(b"\0", 1)[0].decode("ascii")
    tags_addr = struct.unpack_from("<I", data, 2076)[0]
    product_name = data[2080:2096].split(b"\0", 1)[0].decode("ascii")
    header_size, dtb_size = struct.unpack_from("<2I", data, 2096)
    dtb_addr = struct.unpack_from("<Q", data, 2104)[0]
    table_size, table_entries, table_entry_size, bootconfig_size = (
        struct.unpack_from("<4I", data, 2112)
    )
    return {
        "magic": "VNDRBOOT",
        "header_version": header_version,
        "page_size": page_size,
        "kernel_load_address": f"0x{kernel_addr:08x}",
        "ramdisk_load_address": f"0x{ramdisk_addr:08x}",
        "vendor_ramdisk_size": ramdisk_size,
        "cmdline": cmdline,
        "tags_load_address": f"0x{tags_addr:08x}",
        "product_name": product_name,
        "header_size": header_size,
        "dtb_size": dtb_size,
        "dtb_load_address": f"0x{dtb_addr:016x}",
        "vendor_ramdisk_table_size": table_size,
        "vendor_ramdisk_table_entries": table_entries,
        "vendor_ramdisk_table_entry_size": table_entry_size,
        "bootconfig_size": bootconfig_size,
    }


def parse_abl(root: Path) -> dict[str, Any]:
    bl_tar = resolve(root, BL_TAR)
    magiskboot = resolve(root, MAGISKBOOT)
    if not magiskboot.is_file():
        raise MapError("magiskboot decompressor missing")
    with tempfile.TemporaryDirectory(prefix="s22-v3434-abl-") as temp:
        temp_dir = Path(temp)
        compressed = temp_dir / "abl.elf.lz4"
        elf = temp_dir / "abl.elf"
        with tarfile.open(bl_tar, "r:") as tar:
            member = tar.extractfile("abl.elf.lz4")
            if member is None:
                raise MapError("BL tar lacks abl.elf.lz4")
            compressed.write_bytes(member.read())
        result = subprocess.run(
            [str(magiskboot), "decompress", str(compressed), str(elf)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise MapError(f"ABL decompression failed: {result.stdout.strip()}")
        data = elf.read_bytes()
        if data[:4] != b"\x7fELF" or data[4] != 1 or data[5] != 1:
            raise MapError("ABL payload is not ELF32 little-endian")
        machine = struct.unpack_from("<H", data, 18)[0]
        entry = struct.unpack_from("<I", data, 24)[0]
        if machine != 40:
            raise MapError(f"unexpected ABL ELF machine: {machine}")
        return {
            "compressed_sha256": sha256_file(compressed),
            "elf_sha256": sha256_file(elf),
            "elf_size": len(data),
            "elf_class": "ELF32",
            "elf_machine": "ARM",
            "entry_point": f"0x{entry:08x}",
            "inner_firmware_volume_offset": data.find(b"_FVH"),
            "source_availability": "PROPRIETARY_BINARY_ONLY",
            "analysis_scope": "header_and_retained_behavioral_evidence_only",
        }


def report_proofs(root: Path) -> dict[str, dict[str, Any]]:
    required = {
        "o11_control_pass": [
            "requested=128",
            "completed=128",
            "payload_equality=true",
            "sequence_continuity=true",
            "latency_ms_p50=0.286844",
        ],
        "m31b_watchdog_pass": [
            "no bootloop during the full 120 second park window",
            "m31b_survival_window_pass=1",
            "qcom_wdt_core.ko",
            "gh_virt_wdt.ko",
        ],
        "pmic_pon_analysis": [
            "CONFIG_WATCHDOG_HANDLE_BOOT_ENABLED=y",
            "CONFIG_WATCHDOG_OPEN_TIMEOUT=0",
            "PMIC abnormal reset",
        ],
        "v3433_no_proof": [
            "NO_PROOF_PID1_VS_OBSERVER_UNRESOLVED_STOP",
            "Device is unlocked, Skipping boot verification",
        ],
    }
    output: dict[str, dict[str, Any]] = {}
    for name, markers in required.items():
        path = resolve(root, REPORTS[name])
        text = path.read_text(encoding="utf-8")
        missing = [marker for marker in markers if marker not in text]
        if missing:
            raise MapError(f"report proof markers missing in {path}: {missing}")
        output[name] = {"path": str(REPORTS[name]), "markers": markers}
    return output


def build_map(root: Path) -> dict[str, Any]:
    verified_pins = verify_pins(root)
    archive = resolve(root, SOURCE_ARCHIVE)
    sources = tar_texts(
        archive,
        (
            MAIN_SOURCE,
            INITRAMFS_SOURCE,
            EXIT_SOURCE,
            WATCHDOG_SOURCE,
            SEC_LOG_BUF_SOURCE,
            SEC_DEBUG_SOURCE,
        ),
    )
    main = sources[MAIN_SOURCE]
    initramfs = sources[INITRAMFS_SOURCE]
    exit_source = sources[EXIT_SOURCE]
    watchdog = sources[WATCHDOG_SOURCE]
    sec_log = sources[SEC_LOG_BUF_SOURCE]
    sec_debug = sources[SEC_DEBUG_SOURCE]

    source_lines = {
        "start_kernel": require(
            main,
            "asmlinkage __visible void __init __no_sanitize_address start_kernel(void)",
            "start_kernel",
        ),
        "rest_init_bridge": require(
            main, "void __init __weak arch_call_rest_init", "rest-init bridge"
        ),
        "start_kernel_calls_rest": require(main, "arch_call_rest_init();", "start-kernel rest call"),
        "rest_init": require(main, "noinline void __ref rest_init", "rest_init"),
        "pid1_creation": require(main, "pid = kernel_thread(kernel_init, NULL, CLONE_FS);", "PID1 creation"),
        "kernel_init_freeable": require(
            main,
            "static noinline void __init kernel_init_freeable(void)\n{",
            "kernel_init_freeable",
        ),
        "init_eaccess": require(main, "if (init_eaccess(ramdisk_execute_command) != 0)", "init access gate"),
        "kernel_init": require(main, "static int __ref kernel_init(void *unused)", "kernel_init"),
        "run_init_process": require(main, "static int run_init_process", "run_init_process"),
        "default_init": require(main, 'static char *ramdisk_execute_command = "/init";', "default /init"),
        "rdinit_override": require(main, '__setup("rdinit=", rdinit_setup);', "rdinit override"),
        "initramfs_unpack": require(initramfs, "static int __init populate_rootfs(void)", "populate_rootfs"),
        "initramfs_initcall": require(initramfs, "rootfs_initcall(populate_rootfs);", "rootfs initcall"),
        "pid1_death_panic": require(exit_source, 'panic("Attempted to kill init!', "PID1 death panic"),
        "watchdog_boot_handler": require(watchdog, "static bool handle_boot_enabled", "watchdog boot handler"),
        "watchdog_open_timeout": require(watchdog, "static unsigned open_timeout", "watchdog open timeout"),
        "watchdog_immediate_ping": require(watchdog, "if (handle_boot_enabled)\n\t\t\thrtimer_start", "watchdog immediate ping"),
        "sec_log_driver": require(sec_log, "platform_driver_register(&sec_log_buf_driver)", "sec_log_buf driver"),
        "sec_log_initcall": require(sec_log, "subsys_initcall_sync(sec_log_buf_init);", "sec_log_buf initcall"),
        "sec_debug_panic_notifier": require(sec_debug, "atomic_notifier_chain_register(&panic_notifier_list, nb)", "sec_debug panic notifier"),
        "sec_debug_initcall": require(sec_debug, "core_initcall(sec_debug_init);", "sec_debug initcall"),
    }

    config = extract_ikconfig(resolve(root, MAGISK_KERNEL))
    expected_config = {
        "CONFIG_BLK_DEV_INITRD": "y",
        "CONFIG_DEVTMPFS": "n",
        "CONFIG_IKCONFIG": "y",
        "CONFIG_PANIC_ON_OOPS": "y",
        "CONFIG_PANIC_TIMEOUT": "-1",
        "CONFIG_PSTORE": "y",
        "CONFIG_PSTORE_CONSOLE": "y",
        "CONFIG_PSTORE_PMSG": "y",
        "CONFIG_PSTORE_RAM": "y",
        "CONFIG_RKP": "y",
        "CONFIG_SECURITY_DEFEX": "y",
        "CONFIG_SECURITY_SELINUX": "y",
        "CONFIG_SERIAL_EARLYCON": "y",
        "CONFIG_WATCHDOG": "y",
        "CONFIG_WATCHDOG_CORE": "y",
        "CONFIG_WATCHDOG_HANDLE_BOOT_ENABLED": "y",
        "CONFIG_WATCHDOG_OPEN_TIMEOUT": "0",
    }
    for key, value in expected_config.items():
        if config.get(key) != value:
            raise MapError(f"kernel config mismatch {key}: {config.get(key)} != {value}")

    cmdline = resolve(root, LIVE_CMDLINE).read_text(encoding="utf-8")
    live_bootconfig = resolve(root, LIVE_BOOTCONFIG).read_text(encoding="utf-8")
    if "console=null" not in cmdline or "nohyp_uart" not in cmdline:
        raise MapError("live cmdline no longer proves UART suppression")
    if "watchdog.stop_on_reboot=0" not in cmdline:
        raise MapError("live cmdline lacks watchdog stop policy")
    if 'androidboot.init_fatal_panic = "true"' not in live_bootconfig:
        raise MapError("live bootconfig lacks init_fatal_panic")

    module_map = json.loads(resolve(root, MODULE_MAP).read_text(encoding="utf-8"))
    retention = module_map.get("retention", {})
    if retention.get("sec_log_buf.ko", {}).get("runtime_status") != "LIVE_BOUND":
        raise MapError("sec_log_buf live-bound evidence drift")
    if retention.get("sec_debug.ko", {}).get("runtime_status") != "LIVE_BOUND":
        raise MapError("sec_debug live-bound evidence drift")
    modules_load = [
        line.strip()
        for line in resolve(root, MODULES_LOAD).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if modules_load.index("sec_log_buf.ko") + 1 != 2:
        raise MapError("sec_log_buf stock order drift")
    if modules_load.index("sec_debug.ko") + 1 != 105:
        raise MapError("sec_debug stock order drift")
    if modules_load.index("gh_virt_wdt.ko") + 1 != 5:
        raise MapError("gh_virt_wdt stock order drift")
    if modules_load.index("qcom_wdt_core.ko") + 1 != 6:
        raise MapError("qcom_wdt_core stock order drift")

    retained = resolve(root, V3433_LAST_KMSG).read_bytes()
    retained_markers = [
        b"(Booting) AUTHENTICATE fail but allow Kernel binary: boot",
        b"[AuthSignatureOnBoot] Custom binary(boot) by verifystatus(2)",
        b"Device is unlocked, Skipping boot verification",
        b"Hyp version: 1",
        b"Memory Base Address: 0x80000000",
        b"Shutting Down UEFI Boot Services:",
        b"reboot_reason = 0x9",
    ]
    missing_retained = [value.decode() for value in retained_markers if value not in retained]
    if missing_retained:
        raise MapError(f"retained ABL markers missing: {missing_retained}")

    boot = parse_boot_header(resolve(root, STOCK_BOOT))
    vendor_boot = parse_vendor_boot_header(resolve(root, STOCK_VENDOR_BOOT))
    if boot["header_version"] != 4 or vendor_boot["header_version"] != 4:
        raise MapError("expected boot/vendor_boot header v4")
    vendor_bootconfig = resolve(root, VENDOR_BOOTCONFIG).read_text(encoding="utf-8")
    if len(vendor_bootconfig.encode("utf-8")) != vendor_boot["bootconfig_size"]:
        raise MapError("vendor bootconfig size mismatch")

    report_evidence = report_proofs(root)
    abl = parse_abl(root)
    if abl["compressed_sha256"] != "ced0a21ee5deab2ef84503149f45723ea1d09018d158e0aee82cfc644ba0d5f5":
        raise MapError("ABL compressed member drift")
    if abl["elf_sha256"] != "b828dffa4ea63eeaeb5d374db96daee9e1f696487f724d18aecbbc61ed993a24":
        raise MapError("ABL ELF drift")

    return {
        "schema": SCHEMA,
        "target": TARGET,
        "verdict": "HOST_STATIC_MAP_PASS_NO_LIVE",
        "safety": {
            "host_only": True,
            "device_contact": False,
            "image_build": False,
            "flash": False,
            "live_authorized": False,
        },
        "evidence": {
            "pins": verified_pins,
            "source_lines": source_lines,
            "reports": report_evidence,
            "kernel_config": expected_config,
        },
        "boot_images": {
            "boot_v4": boot,
            "vendor_boot_v4": vendor_boot,
            "vendor_bootconfig": [line for line in vendor_bootconfig.splitlines() if line],
            "ownership": {
                "boot": ["kernel", "generic_ramdisk", "boot_signature"],
                "vendor_boot": [
                    "load_addresses",
                    "vendor_ramdisk",
                    "vendor_cmdline",
                    "dtb",
                    "bootconfig",
                ],
            },
        },
        "kernel_boot_boundary": {
            "ordered_flow": [
                "ABL selects boot/vendor_boot/dtb and prepares handoff",
                "arm64 kernel entry",
                "start_kernel",
                "arch_call_rest_init",
                "rest_init creates kernel_init as PID 1",
                "kernel_init_freeable waits for kthreadd and runs initcalls",
                "rootfs_initcall populate_rootfs unpacks built-in and external initramfs",
                "init_eaccess(/init) selects initramfs or prepare_namespace fallback",
                "kernel_init finalizes init memory and calls run_init_process",
                "kernel_execve replaces PID 1 with /init",
            ],
            "init_selection": {
                "default": "/init",
                "rdinit_override": "rdinit= replaces ramdisk_execute_command",
                "missing_or_inaccessible_init": "clear ramdisk command and prepare_namespace",
                "requested_init_override": "init= is attempted after ramdisk init failure",
                "fallback_order": ["CONFIG_DEFAULT_INIT", "/sbin/init", "/etc/init", "/bin/init", "/bin/sh"],
            },
            "pid1_failure": {
                "ramdisk_exec_failure": "log error, then continue to requested/default fallback",
                "explicit_init_exec_failure": "kernel panic",
                "no_working_init": "kernel panic",
                "post_exec_pid1_exit": "panic: Attempted to kill init",
                "v3432_gap": "first retained marker was gated behind module insert and platform probe",
            },
            "pre_exec_security_steps": [
                "do_basic_setup/initcalls",
                "integrity_load_keys",
                "DEFEX rule load when CONFIG_SECURITY_DEFEX",
                "free init memory and mark read-only",
            ],
        },
        "watchdog": {
            "hardware_state": "pre-armed before stock userspace; PMIC/PON abnormal reset near 30 s when unmanaged",
            "kernel_core": "built-in watchdog core auto-pings a registered running watchdog",
            "stock_first_stage": {
                "gh_virt_wdt_modules_load_position": 5,
                "qcom_wdt_core_modules_load_position": 6,
                "open_timeout_seconds": 0,
                "open_timeout_meaning": "infinite kernel care until userspace takeover",
            },
            "live_discriminator": "M31B loaded stock watchdog closure and survived 120 seconds",
            "direct_pid1_requirement": "load proven watchdog closure before any unbounded park, or remain under stock init ownership",
        },
        "observation_channels": [
            {
                "name": "earlycon_uart",
                "earliest_stage": "kernel entry before normal console init",
                "activation": "built-in support plus bootargs earlycon/console and routed UART",
                "fyg8_state": "UNAVAILABLE_DEFAULT",
                "evidence": "CONFIG_SERIAL_EARLYCON=y but live cmdline has console=null and nohyp_uart",
                "claim_limit": "absence of UART output proves nothing while disabled",
            },
            {
                "name": "ramoops_pstore",
                "earliest_stage": "after pstore backend platform probe",
                "activation": "CONFIG_PSTORE_RAM plus enabled ramoops reserved-memory DT node",
                "fyg8_state": "UNAVAILABLE_DEFAULT",
                "evidence": "pstore is built-in but live ramoops_region status is disabled",
                "claim_limit": "empty pstore is not kernel/PID1 non-entry proof",
            },
            {
                "name": "sec_log_buf",
                "earliest_stage": "stock first-stage PID1 module load position 2 and successful platform probe",
                "activation": "exact module ABI, samsung,kernel_log_buf DT match, reserved memory, procfs",
                "fyg8_state": "AVAILABLE_AFTER_STOCK_PID1_LOAD",
                "evidence": "source verified, live bound, creates /proc/last_kmsg and /proc/ap_klog",
                "claim_limit": "cannot witness kernel entry or PID1 code before module load/probe",
            },
            {
                "name": "sec_debug",
                "earliest_stage": "stock first-stage PID1 module load position 105 and successful platform probe",
                "activation": "samsung,sec_debug DT match, MID/debug parameters, panic notifier registration",
                "fyg8_state": "AVAILABLE_LATE_FIRST_STAGE",
                "evidence": "source verified, live bound, sysrq panic positive control",
                "claim_limit": "not the retained printk-ring owner and unavailable before its module load",
            },
            {
                "name": "pmic_pon_reset_reason",
                "earliest_stage": "reset latch consumed by XBL/ABL before Linux",
                "activation": "PMIC/PON hardware reset state and bootloader RDX classifier",
                "fyg8_state": "AVAILABLE_PRE_KERNEL_AS_RESET_CLASS",
                "evidence": "operator RDX PMIC abnormal reset plus reset_reason=MPON/reboot_reason records",
                "claim_limit": "classifies reset cause; does not identify the last Linux instruction or prove PID1",
            },
            {
                "name": "stock_usb_tty_control",
                "earliest_stage": "after stock first-stage modules, gadget, and sys.usb.configured",
                "activation": "O1.1 Magisk overlay service with bounded DR-daemon handoff",
                "fyg8_state": "LIVE_PROVEN",
                "evidence": "128/128 payload-equal sequence-continuous roundtrip, p50 0.286844 ms",
                "claim_limit": "proves stock-first-stage control, not direct-PID1 USB",
            },
        ],
        "abl_targeted_boundary": {
            "binary": abl,
            "handoff_result": "FIRMWARE_EXIT_BOOT_SERVICES_BOUNDARY_REACHED",
            "kernel_entry_result": "UNVERIFIED_AFTER_EXIT_BOOT_SERVICES",
            "verified": [
                "boot and vendor_boot header v4 are parsed from pinned stock images",
                "vendor_boot carries load addresses, DTB, vendor ramdisk, cmdline, and bootconfig",
                "retained ABL log says authentication failed but custom kernel binary is allowed",
                "retained ABL log says unlocked device skips boot verification",
                "ABL proceeds to hypervisor and DT selection messages after the warning",
                "the same retained ABL boot reaches Shutting Down UEFI Boot Services after the warning",
                "ABL records reboot_reason values consumed on the next boot",
            ],
            "unverified": [
                "final branch into the candidate kernel entry point",
                "candidate kernel decompression completion",
                "kernel reaching start_kernel",
                "kernel reaching run_init_process or /init",
            ],
            "decision": "do not widen ABL reverse engineering until a header/handoff contradiction appears",
        },
        "selected_architecture": {
            "name": "stock_global_pid1_with_namespaced_native_handoff",
            "priority": "PRIMARY",
            "global_pid1": "retain stock Android init as hardware/watchdog/recovery owner",
            "native_runtime": "launch a native supervisor after a device-reported prerequisite bundle",
            "debian_root": "new mount/PID namespace plus pivot_root; not chroot",
            "control_plane": "retain O1.1-proven ttyGS0 framed channel outside Debian namespace",
            "handoff_gates": [
                "sec_log_buf driver bound and both proc nodes present",
                "watchdog modules registered and kernel pet path alive",
                "stock UDC/gadget configured and framed USB roundtrip passes",
                "Debian rootfs identity and read-only preflight pass",
                "DRM/input/audio ownership transition plan is explicit and reversible",
            ],
            "failure_behavior": "return control to stock init and keep USB recovery channel",
            "direct_pid1_track": "research-only until a pre-userspace witness exists",
        },
        "next_host_units": [
            "design the stock-init native supervisor service and prerequisite bundle",
            "design namespace plus pivot_root Debian handoff with reversible device ownership",
            "separately evaluate a kernel-entry witness without reusing direct-PID1 retained-marker live gates",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--out", type=Path, default=OUTPUT)
    args = parser.parse_args()
    root = repo_root()
    result = build_map(root)
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.write:
        output = resolve(root, args.out)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
        print(output.relative_to(root))
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
