#!/usr/bin/env python3

from __future__ import annotations

import ast
import copy
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

from a90_flat_builder import build
from a90_flat_builder import buildlib


HERE = Path(__file__).resolve().parent
REPO_ROOT = build.repo_root()
MANIFEST = (
    HERE / "a90_flat_builder/versions/v3404-effective/manifest.toml"
)
NOOP_MANIFEST = (
    HERE / "a90_flat_builder/versions/flat-builder-v1-noop/manifest.toml"
)
MINIMAL_MANIFEST = (
    HERE / "a90_flat_builder/versions/phase3-minimal-a/manifest.toml"
)
MINIMAL_B_MANIFEST = (
    HERE / "a90_flat_builder/versions/phase3-minimal-b/manifest.toml"
)
MINIMAL_C_MANIFEST = (
    HERE / "a90_flat_builder/versions/phase3-minimal-c/manifest.toml"
)
MINIMAL_D_MANIFEST = (
    HERE / "a90_flat_builder/versions/phase3-minimal-d/manifest.toml"
)
MINIMAL_E_MANIFEST = (
    HERE / "a90_flat_builder/versions/phase3-minimal-e/manifest.toml"
)
MINIMAL_F_MANIFEST = (
    HERE / "a90_flat_builder/versions/phase3-minimal-f/manifest.toml"
)
MINIMAL_G_MANIFEST = (
    HERE / "a90_flat_builder/versions/phase3-minimal-g/manifest.toml"
)
MINIMAL_H_MANIFEST = (
    HERE / "a90_flat_builder/versions/phase3-minimal-h/manifest.toml"
)
MINIMAL_H5_MANIFEST = (
    HERE / "a90_flat_builder/versions/phase3-minimal-h5/manifest.toml"
)
MINIMAL_H6_MANIFEST = (
    HERE / "a90_flat_builder/versions/phase3-minimal-h6/manifest.toml"
)


def newc_archive(entries: dict[str, bytes]) -> bytes:
    result = bytearray()
    for inode, (name, payload) in enumerate(
        [*entries.items(), ("TRAILER!!!", b"")],
        start=1,
    ):
        encoded_name = name.encode("utf-8") + b"\0"
        fields = [
            inode,
            0o100755,
            0,
            0,
            1,
            0,
            len(payload),
            0,
            0,
            0,
            0,
            len(encoded_name),
            0,
        ]
        result.extend(b"070701")
        result.extend("".join(f"{value:08x}" for value in fields).encode("ascii"))
        result.extend(encoded_name)
        result.extend(b"\0" * (-len(result) % 4))
        result.extend(payload)
        result.extend(b"\0" * (-len(result) % 4))
    result.extend(b"\0" * (-len(result) % 512))
    return bytes(result)


class A90FlatBuilderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.resolution = buildlib.resolve_manifest(MANIFEST)
        cls.manifest = cls.resolution.data
        materialized = {
            name: (
                MANIFEST.parent / value["path"]
            ).resolve()
            for name, value in cls.manifest["engine"][
                "materialized_sources"
            ].items()
        }
        cls.inputs = {
            "init_root": (
                REPO_ROOT / cls.manifest["init"]["source_root"]
            ).resolve(),
            "init_sources": cls.manifest["init"]["sources"],
            "doom_sources": cls.manifest["engine"]["doom_sources"],
            "materialized": materialized,
            "materialized_sha256": {
                name: buildlib.sha256_file(path)
                for name, path in materialized.items()
            },
        }

    def test_flat_effective_identity_and_source_counts(self):
        self.assertEqual(
            self.manifest["profile"],
            "v3404-effective-portable-v1",
        )
        self.assertFalse(self.manifest["candidate_authority"])
        self.assertNotIn("extends", self.manifest)
        self.assertEqual(len(self.inputs["init_sources"]), 60)
        self.assertEqual(len(self.inputs["doom_sources"]), 80)
        self.assertEqual(len(self.manifest["init"]["cflags"]), 84)
        self.assertEqual(len(self.manifest["helper"]["cflags"]), 29)
        self.assertTrue(self.manifest["engine"]["enabled"])
        self.assertIn(
            '-DA90_DOOMGENERIC_BRIDGE_ENGINE='
            '"doomgeneric-private-link-v3404-d3-resolved-owner-timeout"',
            self.manifest["init"]["cflags"],
        )

    def test_materialized_sources_match_phase0_pins(self):
        self.assertEqual(
            self.inputs["materialized_sha256"],
            {
                "adapter":
                    "d5bcb088a554cf53278a5d4995bf24768c49964eb6b4159a33eb80b39ab953ca",
                "sfx":
                    "e52f5fef6db417359066aff1c00d0f11f8f3ac3462175093ec4a9eda99a7720f",
                "sdl_mixer_stub":
                    "18bf8a8f46a757399bfea90f7db828534e4b579efbf2e7754c10424dcbe690cd",
            },
        )

    def test_phase3_minimal_a_disables_only_doom_product_surface(self):
        minimal = buildlib.resolve_manifest(MINIMAL_MANIFEST).data
        buildlib.validate_component_selection(minimal)
        self.assertEqual(
            minimal["profile"],
            "phase3-minimal-a-no-doom-engine",
        )
        self.assertFalse(minimal["candidate_authority"])
        self.assertFalse(minimal["engine"]["enabled"])
        self.assertEqual(len(minimal["init"]["sources"]), 60)
        self.assertIn(
            "a90_doomgeneric_bridge.c",
            minimal["init"]["sources"],
        )
        self.assertEqual(len(minimal["init"]["cflags"]), 37)
        self.assertFalse(
            any("DOOMGENERIC" in item for item in minimal["init"]["cflags"])
        )
        engine_path = minimal["engine"]["ramdisk_path"]
        self.assertIn(engine_path, minimal["ramdisk"]["obsolete_engines"])
        self.assertNotIn(engine_path, minimal["ramdisk"]["required_entries"])
        self.assertEqual(minimal["validation"]["engine_strings"], [])
        self.assertNotIn("engine", build.artifact_names(minimal))
        buildlib.validate_ramdisk_component_listing(
            minimal,
            set(minimal["ramdisk"]["required_entries"]),
        )

    def test_phase3_minimal_c_removes_doom_command_and_bridge_sources(self):
        resolution = buildlib.resolve_manifest(MINIMAL_C_MANIFEST)
        minimal = resolution.data
        buildlib.validate_component_selection(minimal)
        self.assertEqual(
            minimal["profile"],
            "phase3-minimal-c-no-doom-command-surface",
        )
        self.assertFalse(minimal["candidate_authority"])
        self.assertFalse(minimal["engine"]["enabled"])
        self.assertEqual(len(minimal["init"]["sources"]), 59)
        self.assertNotIn(
            "a90_doomgeneric_bridge.c",
            minimal["init"]["sources"],
        )
        self.assertNotIn(
            "a90_doomgeneric_bridge_inert.c",
            minimal["init"]["sources"],
        )
        self.assertIn(
            "-DA90_MINIMAL_NO_DOOM_COMMAND_SURFACE=1",
            minimal["init"]["cflags"],
        )
        self.assertIn(
            "video.status.doom_surface=removed",
            minimal["validation"]["init_strings"],
        )
        self.assertIn(
            "video.demo.doom=removed",
            minimal["validation"]["init_strings"],
        )
        buildlib.validate_ramdisk_component_listing(
            minimal,
            set(minimal["ramdisk"]["required_entries"]),
        )

    def test_phase3_minimal_d_removes_boot_write_flash_surface(self):
        resolution = buildlib.resolve_manifest(MINIMAL_D_MANIFEST)
        minimal = resolution.data
        buildlib.validate_component_selection(minimal)
        self.assertEqual(
            minimal["profile"],
            "phase3-minimal-d-no-boot-write-flash-surface",
        )
        self.assertFalse(minimal["candidate_authority"])
        self.assertFalse(minimal["engine"]["enabled"])
        self.assertEqual(len(minimal["init"]["sources"]), 57)
        for source in (
            "a90_doomgeneric_bridge.c",
            "a90_doomgeneric_bridge_inert.c",
            "a90_boot_write_e1.c",
            "a90_boot_write_probe.c",
        ):
            self.assertNotIn(source, minimal["init"]["sources"])
        for flag in (
            "-DA90_MINIMAL_NO_DOOM_COMMAND_SURFACE=1",
            "-DA90_MINIMAL_NO_BOOT_WRITE_FLASH_SURFACE=1",
        ):
            self.assertIn(flag, minimal["init"]["cflags"])
        self.assertIn(
            "safety.boot_write_flash_surface=removed",
            minimal["validation"]["init_strings"],
        )
        buildlib.validate_ramdisk_component_listing(
            minimal,
            set(minimal["ramdisk"]["required_entries"]),
        )

    def test_phase3_minimal_e_removes_dedicated_cpu_stress_surface(self):
        resolution = buildlib.resolve_manifest(MINIMAL_E_MANIFEST)
        minimal = resolution.data
        buildlib.validate_component_selection(minimal)
        self.assertEqual(
            minimal["profile"],
            "phase3-minimal-e-no-dedicated-cpu-stress-surface",
        )
        self.assertFalse(minimal["candidate_authority"])
        self.assertFalse(minimal["engine"]["enabled"])
        self.assertEqual(len(minimal["init"]["sources"]), 56)
        for source in (
            "a90_doomgeneric_bridge.c",
            "a90_doomgeneric_bridge_inert.c",
            "a90_boot_write_e1.c",
            "a90_boot_write_probe.c",
            "a90_app_cpustress.c",
        ):
            self.assertNotIn(source, minimal["init"]["sources"])
        for flag in (
            "-DA90_MINIMAL_NO_DOOM_COMMAND_SURFACE=1",
            "-DA90_MINIMAL_NO_BOOT_WRITE_FLASH_SURFACE=1",
            "-DA90_MINIMAL_NO_DEDICATED_CPU_STRESS_SURFACE=1",
        ):
            self.assertIn(flag, minimal["init"]["cflags"])
        self.assertIn(
            "safety.dedicated_cpu_stress_surface=removed",
            minimal["validation"]["init_strings"],
        )
        buildlib.validate_ramdisk_component_listing(
            minimal,
            set(minimal["ramdisk"]["required_entries"]),
        )

    def test_phase3_minimal_f_keeps_only_power_recovery_physical_ui(self):
        resolution = buildlib.resolve_manifest(MINIMAL_F_MANIFEST)
        minimal = resolution.data
        buildlib.validate_component_selection(minimal)
        self.assertEqual(
            minimal["profile"],
            "phase3-minimal-f-power-recovery-ui",
        )
        self.assertFalse(minimal["candidate_authority"])
        self.assertFalse(minimal["engine"]["enabled"])
        self.assertEqual(len(minimal["init"]["sources"]), 56)
        for flag in (
            "-DA90_MINIMAL_NO_DOOM_COMMAND_SURFACE=1",
            "-DA90_MINIMAL_NO_BOOT_WRITE_FLASH_SURFACE=1",
            "-DA90_MINIMAL_NO_DEDICATED_CPU_STRESS_SURFACE=1",
            "-DA90_MINIMAL_POWER_RECOVERY_UI=1",
        ):
            self.assertIn(flag, minimal["init"]["cflags"])
        for marker in (
            "ui.power_recovery_surface=minimal",
            "SERVER RECOVERY",
            "POWER STORAGE HEALTH",
        ):
            self.assertIn(marker, minimal["validation"]["init_strings"])
        inputs = buildlib.validate_inputs(
            REPO_ROOT,
            resolution,
            minimal,
        )
        self.assertEqual(
            inputs["init_closure_sha256"],
            minimal["init"]["closure_sha256"],
        )
        buildlib.validate_ramdisk_component_listing(
            minimal,
            set(minimal["ramdisk"]["required_entries"]),
        )

    def test_phase3_minimal_g_keeps_server_core_and_removes_legacy_helpers(self):
        resolution = buildlib.resolve_manifest(MINIMAL_G_MANIFEST)
        minimal = resolution.data
        buildlib.validate_component_selection(minimal)
        self.assertEqual(minimal["profile"], "phase3-minimal-g-server-core")
        self.assertFalse(minimal["candidate_authority"])
        self.assertFalse(minimal["engine"]["enabled"])
        self.assertEqual(len(minimal["init"]["sources"]), 49)
        self.assertIn(
            "-DA90_MINIMAL_SERVER_CORE_SURFACE=1",
            minimal["init"]["cflags"],
        )
        for retained in (
            "a90_audio.c",
            "a90_kms.c",
            "a90_wifi.c",
            "a90_server_distro.c",
        ):
            self.assertIn(retained, minimal["init"]["sources"])
        for removed in (
            "a90_app_about.c",
            "a90_app_audio.c",
            "a90_app_log.c",
            "a90_app_network.c",
            "a90_app_wifi.c",
            "a90_init_reload.c",
            "a90_longsoak.c",
        ):
            self.assertNotIn(removed, minimal["init"]["sources"])
        self.assertEqual(
            minimal["ramdisk"]["remove_entries"],
            [
                "bin/a90_cpustress",
                "bin/a90_longsoak",
                "bin/a90_rshell",
                "bin/a90sleep",
            ],
        )
        retained_runtime_entries = {
            "init",
            "bin/a90_android_execns_probe",
            "bin/a90_tcpctl",
            "bin/a90_usbnet",
            "bin/busybox",
            "bin/toybox",
        }
        retained_audio_entries = {
            "a90/audio/manifests/audio-setcal-internal-speaker-safe.manifest",
            "a90/audio/setcal/internal-speaker-safe/00-payload-cal39-core-custom-topologies.bin",
            "a90/audio/setcal/internal-speaker-safe/00-set-arg-cal39-core-custom-topologies.bin",
            "a90/audio/setcal/internal-speaker-safe/01-set-arg-cal20-realhal-01.bin",
            "a90/audio/setcal/internal-speaker-safe/02-set-arg-cal20-realhal-02.bin",
            "a90/audio/setcal/internal-speaker-safe/03-set-arg-cal13.bin",
            "a90/audio/setcal/internal-speaker-safe/04-set-arg-cal09.bin",
            "a90/audio/setcal/internal-speaker-safe/05-payload-cal11.bin",
            "a90/audio/setcal/internal-speaker-safe/05-set-arg-cal11.bin",
            "a90/audio/setcal/internal-speaker-safe/06-set-arg-cal12.bin",
            "a90/audio/setcal/internal-speaker-safe/07-payload-cal15.bin",
            "a90/audio/setcal/internal-speaker-safe/07-set-arg-cal15.bin",
            "a90/audio/setcal/internal-speaker-safe/08-set-arg-cal23.bin",
            "a90/audio/setcal/internal-speaker-safe/09-payload-cal16.bin",
            "a90/audio/setcal/internal-speaker-safe/09-set-arg-cal16.bin",
            "a90/audio/setcal/internal-speaker-safe/10-set-arg-cal21.bin",
        }
        self.assertEqual(
            set(minimal["ramdisk"]["required_entries"]),
            retained_runtime_entries | retained_audio_entries,
        )
        for marker in (
            "surface.server_core=minimal",
            "server_core.wifi=retained",
            "server_core.gpu=retained",
            "server_core.audio_boot_chime=retained",
        ):
            self.assertIn(marker, minimal["validation"]["init_strings"])
        buildlib.validate_ramdisk_component_listing(
            minimal,
            set(minimal["ramdisk"]["required_entries"]),
        )

    def test_phase3_minimal_h_binds_one_shot_auto_handoff_and_benchmark(self):
        resolution = buildlib.resolve_manifest(MINIMAL_H_MANIFEST)
        minimal = resolution.data
        buildlib.validate_component_selection(minimal)
        self.assertEqual(
            minimal["profile"],
            "phase3-minimal-h4-observer-complete-auto-benchmark",
        )
        self.assertFalse(minimal["candidate_authority"])
        self.assertFalse(minimal["engine"]["enabled"])
        self.assertEqual(len(minimal["init"]["sources"]), 51)
        for source in ("a90_auto_handoff.c", "a90_benchmark.c"):
            self.assertIn(source, minimal["init"]["sources"])
        flags = minimal["init"]["cflags"]
        self.assertIn("-DA90_AUTO_HANDOFF_BENCHMARK_V1=1", flags)
        self.assertTrue(
            any(flag.startswith('-DA90_AUTO_HANDOFF_IMAGE="') for flag in flags)
        )
        self.assertTrue(
            any(
                flag.startswith('-DA90_AUTO_HANDOFF_IMAGE_SHA256="')
                for flag in flags
            )
        )
        self.assertTrue(
            any(flag.startswith('-DA90_AUTO_HANDOFF_LATCH_PATH="') for flag in flags)
        )
        self.assertTrue(
            any(flag.startswith('-DA90_AUTO_HANDOFF_ENABLE_PATH="') for flag in flags)
        )
        binding = build.normalized_auto_handoff_binding(minimal)
        self.assertEqual(
            binding,
            {
                "schema": "a90-compiled-auto-handoff-binding-v1",
                "candidate_version": "0.11.172",
                "candidate_build": "phase3-minimal-h4-observer-complete-auto-benchmark",
                "image_path": "/mnt/sdext/a90/runtime/debian-bookworm-arm64-phase2-display-v3406-keyed-20260805-11.img",
                "image_sha256": "8b4bfd99a9324c0a32e76c837e33282afa79739fa32645e3303861e8928a33fa",
                "enable_path": "/cache/a90-auto-handoff-phase3-minimal-h4.enable",
                "latch_path": "/cache/a90-auto-handoff-phase3-minimal-h4.done",
                "binding_sha256": binding["binding_sha256"],
            },
        )
        inputs = buildlib.validate_inputs(REPO_ROOT, resolution, minimal)
        self.assertEqual(
            inputs["init_closure_sha256"],
            minimal["init"]["closure_sha256"],
        )
        for marker in (
            "A90BENCH schema=%s stage=%s boottime_ms=%llu clock_ok=%d telemetry_sampled=%d sample_duration_ms=%llu prior_emit_duration_ms=%llu",
            "a90-boot-benchmark-v1",
            "A90AUTO state=unarmed-stay-native",
            "A90AUTO_ARM armed=1",
            "A90AUTO state=dispatch-once",
            "A90AUTO state=latched-stay-native",
        ):
            self.assertIn(marker, minimal["validation"]["init_strings"])

    def test_phase3_minimal_h_rejects_duplicate_compiled_binding_macro(self):
        minimal = copy.deepcopy(
            buildlib.resolve_manifest(MINIMAL_H_MANIFEST).data
        )
        minimal["init"]["cflags"].append(
            '-DA90_AUTO_HANDOFF_IMAGE="/mnt/sdext/a90/runtime/other.img"'
        )
        with self.assertRaisesRegex(RuntimeError, "missing or duplicated"):
            build.normalized_auto_handoff_binding(minimal)

    def test_phase3_minimal_h5_binds_fresh_rootfs_and_marker_namespace(self):
        h4 = buildlib.resolve_manifest(MINIMAL_H_MANIFEST).data
        resolution = buildlib.resolve_manifest(MINIMAL_H5_MANIFEST)
        h5 = resolution.data
        buildlib.validate_component_selection(h5)
        self.assertEqual(
            h5["profile"],
            "phase3-minimal-h5-fresh-campaign-auto-benchmark",
        )
        self.assertFalse(h5["candidate_authority"])
        self.assertEqual(h5["init"]["sources"], h4["init"]["sources"])
        binding = build.normalized_auto_handoff_binding(h5)
        self.assertEqual(binding["candidate_version"], "0.11.173")
        self.assertEqual(
            binding["candidate_build"],
            "phase3-minimal-h5-fresh-campaign-auto-benchmark",
        )
        self.assertEqual(
            binding["image_path"],
            "/mnt/sdext/a90/runtime/"
            "debian-bookworm-arm64-phase2-display-v3406-keyed-20260805-12.img",
        )
        self.assertEqual(
            binding["image_sha256"],
            "874291801573d96bf7731b2cdc27deca066221450534365eddfa2acf41ab681e",
        )
        self.assertEqual(
            binding["enable_path"],
            "/cache/a90-auto-handoff-phase3-minimal-h5.enable",
        )
        self.assertEqual(
            binding["latch_path"],
            "/cache/a90-auto-handoff-phase3-minimal-h5.done",
        )
        self.assertNotEqual(
            binding["binding_sha256"],
            build.normalized_auto_handoff_binding(h4)["binding_sha256"],
        )
        inputs = buildlib.validate_inputs(REPO_ROOT, resolution, h5)
        self.assertEqual(
            inputs["init_closure_sha256"],
            h5["init"]["closure_sha256"],
        )

    def test_phase3_minimal_h6_binds_non_lto_observer_complete_baseline(self):
        h5 = buildlib.resolve_manifest(MINIMAL_H5_MANIFEST).data
        resolution = buildlib.resolve_manifest(MINIMAL_H6_MANIFEST)
        h6 = resolution.data
        buildlib.validate_component_selection(h6)
        self.assertEqual(
            h6["profile"],
            "phase3-minimal-h6-observer-complete-baseline-auto-benchmark",
        )
        self.assertFalse(h6["candidate_authority"])
        self.assertEqual(h6["init"]["sources"], h5["init"]["sources"])
        self.assertFalse(
            any("lto" in flag.lower() for flag in h6["init"]["cflags"])
        )
        binding = build.normalized_auto_handoff_binding(h6)
        self.assertEqual(binding["candidate_version"], "0.11.174")
        self.assertEqual(
            binding["candidate_build"],
            "phase3-minimal-h6-observer-complete-baseline-auto-benchmark",
        )
        self.assertEqual(
            binding["image_path"],
            "/mnt/sdext/a90/runtime/"
            "debian-bookworm-arm64-phase2-display-v3406-keyed-20260807-03.img",
        )
        self.assertEqual(
            binding["image_sha256"],
            "feea09dd81fc342032c94629f47d06e743788efc9dc7bba9ca0067f346d4d490",
        )
        self.assertEqual(
            binding["enable_path"],
            "/cache/a90-auto-handoff-phase3-minimal-h6.enable",
        )
        self.assertEqual(
            binding["latch_path"],
            "/cache/a90-auto-handoff-phase3-minimal-h6.done",
        )
        self.assertNotEqual(
            binding["binding_sha256"],
            build.normalized_auto_handoff_binding(h5)["binding_sha256"],
        )
        inputs = buildlib.validate_inputs(REPO_ROOT, resolution, h6)
        self.assertEqual(
            inputs["init_closure_sha256"],
            h6["init"]["closure_sha256"],
        )

    def test_phase3_minimal_g_retained_runtime_and_audio_are_fail_closed(self):
        minimal = buildlib.resolve_manifest(MINIMAL_G_MANIFEST).data
        entries = {
            name: b"content"
            for name in minimal["ramdisk"]["required_entries"]
        }
        with tempfile.TemporaryDirectory() as temp_name:
            archive = Path(temp_name) / "ramdisk.cpio"
            archive.write_bytes(newc_archive(entries))
            self.assertEqual(
                build.validate_packed_ramdisk(minimal, archive),
                set(entries),
            )
            for missing in sorted(entries):
                with self.subTest(missing=missing):
                    reduced = dict(entries)
                    del reduced[missing]
                    archive.write_bytes(newc_archive(reduced))
                    with self.assertRaisesRegex(
                        RuntimeError,
                        "ramdisk required entries missing",
                    ):
                        build.validate_packed_ramdisk(minimal, archive)

    def test_phase3_minimal_g_removed_ramdisk_entries_are_fail_closed(self):
        minimal = buildlib.resolve_manifest(MINIMAL_G_MANIFEST).data
        listing = set(minimal["ramdisk"]["required_entries"])
        listing.add("bin/a90_rshell")
        with self.assertRaisesRegex(
            buildlib.ManifestError,
            "packed ramdisk retained removed entries",
        ):
            buildlib.validate_ramdisk_component_listing(minimal, listing)

        cases = {
            "duplicate": ["bin/a90sleep", "bin/a90sleep"],
            "overlap-obsolete": [minimal["engine"]["ramdisk_path"]],
            "traversal": ["bin/../init"],
            "alias": ["bin//a90sleep"],
            "absolute": ["/bin/a90sleep"],
            "protected-init": ["init"],
            "protected-helper": [minimal["ramdisk"]["helper_path"]],
        }
        for name, entries in cases.items():
            with self.subTest(name=name):
                changed = copy.deepcopy(minimal)
                changed["ramdisk"]["remove_entries"] = entries
                with self.assertRaises(buildlib.ManifestError):
                    buildlib.validate_component_selection(changed)

    def test_phase3_minimal_g_preprocessed_command_table_is_server_scoped(self):
        minimal = buildlib.resolve_manifest(MINIMAL_G_MANIFEST).data
        init_root = REPO_ROOT / minimal["init"]["source_root"]
        result = subprocess.run(
            [
                minimal["toolchain"]["cc"],
                *minimal["init"]["cflags"],
                "-E",
                "-P",
                init_root / "init_v724.c",
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        start = result.stdout.index(
            "static const struct shell_command command_table[] = {"
        )
        end = result.stdout.index("\n};", start)
        selected = result.stdout[start:end]
        names = re.findall(r'^\s*\{ "([^"]+)",', selected, re.MULTILINE)
        self.assertEqual(len(names), 99)
        for retained in (
            "audio",
            "gpu",
            "wifi",
            "netservice",
            "server-distro",
            "switch-root-to-distro",
            "recovery",
            "reboot",
            "poweroff",
        ):
            self.assertIn(retained, names)
        for removed in (
            "screenapp",
            "rshell",
            "longsoak",
            "reload",
            "userdata-appliance-preflight",
            "userdata-appliance-formatter-probe",
            "userdata-appliance-format",
            "userdata-appliance-populate",
            "switch-root-to-userdata",
            "dpublic-hud-presenter",
            "dpublic-hud-presenter-service",
        ):
            self.assertNotIn(removed, names)

    def test_phase3_minimal_g_exposure_keeps_netservice_warning(self):
        minimal = buildlib.resolve_manifest(MINIMAL_G_MANIFEST).data
        init_root = REPO_ROOT / minimal["init"]["source_root"]
        result = subprocess.run(
            [
                minimal["toolchain"]["cc"],
                "-DA90_MINIMAL_SERVER_CORE_SURFACE=1",
                "-E",
                "-P",
                init_root / "a90_exposure.c",
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        start = result.stdout.index(
            "\nint a90_exposure_collect(struct a90_exposure_snapshot *out) {"
        )
        end = result.stdout.index(
            "void a90_exposure_summary(",
            start,
        )
        selected = result.stdout[start:end]
        self.assertRegex(
            selected,
            r"if \(out->netservice_enabled && !out->tcpctl_running\)",
        )
        for removed in (
            "out->rshell_enabled",
            "out->rshell_running",
            "out->rshell_token_present",
            "out->rshell_token_owner_only",
        ):
            self.assertNotIn(removed, selected)

    def test_phase3_minimal_f_physical_menu_is_fail_closed(self):
        config = (
            REPO_ROOT / "workspace/public/src/native-init/a90_config.h"
        ).read_text(encoding="utf-8")
        menu = (
            REPO_ROOT / "workspace/public/src/native-init/a90_menu.c"
        ).read_text(encoding="utf-8")
        apps = (
            REPO_ROOT
            / "workspace/public/src/native-init/v319/40_menu_apps.inc.c"
        ).read_text(encoding="utf-8")

        self.assertIn("#define A90_MINIMAL_POWER_RECOVERY_UI 0", config)
        selected_start = menu.index("#if A90_MINIMAL_POWER_RECOVERY_UI")
        selected_end = menu.index("#else", selected_start)
        selected_main = menu[selected_start:selected_end]
        for required in (
            '"STATUS"',
            '"POWER >"',
            '"HIDE MENU"',
        ):
            self.assertIn(required, selected_main)
        for forbidden in (
            '"APPS >"',
            '"DEMO >"',
            '"NETWORK >"',
            "SCREEN_MENU_DEMO_BADAPPLE",
            "SCREEN_MENU_AUDIO_STATUS",
            "SCREEN_MENU_WIFI_SCAN",
        ):
            self.assertNotIn(forbidden, selected_main)
        power_start = menu.index(
            "static const struct screen_menu_item screen_menu_power_items[]"
        )
        power_end = menu.index("\n};", power_start)
        selected_power = menu[power_start:power_end]
        self.assertEqual(
            [
                line.split("SCREEN_MENU_", 1)[1].split(",", 1)[0]
                for line in selected_power.splitlines()
                if "SCREEN_MENU_" in line
            ],
            ["RECOVERY", "REBOOT", "POWEROFF", "BACK"],
        )
        page_guard = (
            "page_id != SCREEN_MENU_PAGE_MAIN &&\n"
            "        page_id != SCREEN_MENU_PAGE_POWER"
        )
        self.assertEqual(menu.count(page_guard), 2)
        app_map_start = menu.index(
            "enum screen_app_id a90_menu_app_from_action"
        )
        app_map_selected = menu[
            menu.index("#if A90_MINIMAL_POWER_RECOVERY_UI", app_map_start):
            menu.index("#else", app_map_start)
        ]
        self.assertIn("return SCREEN_APP_NONE;", app_map_selected)
        self.assertIn(
            "#if A90_MINIMAL_POWER_RECOVERY_UI\n"
            "    state->menu_active = false;",
            apps,
        )
        self.assertIn(
            "#if !A90_MINIMAL_POWER_RECOVERY_UI\n"
            "            a90_hud_draw_hud_log_tail",
            apps,
        )
        self.assertIn(
            "#if !A90_MINIMAL_POWER_RECOVERY_UI\n"
            "    a90_hud_draw_log_tail_panel",
            apps,
        )
        action_start = apps.index("switch (item->action)")
        non_power_start = apps.index(
            "#if !A90_MINIMAL_POWER_RECOVERY_UI", action_start
        )
        non_power_end = apps.index("\n#endif", non_power_start)
        non_power_dispatch = apps[non_power_start:non_power_end]
        for guarded in (
            "case SCREEN_MENU_LOG:",
            "case SCREEN_MENU_NET_STATUS:",
            "case SCREEN_MENU_INPUT_MONITOR:",
            "case SCREEN_MENU_DISPLAY_TEST:",
            "case SCREEN_MENU_DEMO_BADAPPLE:",
            "case SCREEN_MENU_DEMO_NYAN:",
        ):
            self.assertIn(guarded, non_power_dispatch)
        selected_tail = apps[non_power_end:]
        for retained in (
            "case SCREEN_MENU_RECOVERY:",
            "case SCREEN_MENU_REBOOT:",
            "case SCREEN_MENU_POWEROFF:",
        ):
            self.assertIn(retained, selected_tail)

    def test_phase3_minimal_f_selected_preprocessor_has_no_physical_log_tail(self):
        completed = subprocess.run(
            [
                "aarch64-linux-gnu-gcc",
                "-E",
                "-P",
                "-DA90_WIFI_TEST_BOOT=1",
                "-DA90_MINIMAL_NO_DOOM_COMMAND_SURFACE=1",
                "-DA90_MINIMAL_NO_BOOT_WRITE_FLASH_SURFACE=1",
                "-DA90_MINIMAL_NO_DEDICATED_CPU_STRESS_SURFACE=1",
                "-DA90_MINIMAL_POWER_RECOVERY_UI=1",
                "workspace/public/src/native-init/init_v724.c",
            ],
            cwd=REPO_ROOT,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        selected = completed.stdout
        draw_start = selected.index("static void auto_hud_draw_current_screen")
        draw_end = selected.index(
            "static int video_demo_doom_restore_menu_after_exit", draw_start
        )
        hud_draw = selected[draw_start:draw_end]
        self.assertNotIn("a90_hud_draw_hud_log_tail(", hud_draw)

        menu_draw_start = selected.index("static void kms_draw_menu_section")
        menu_draw_end = selected.index(
            "static void print_blind_menu_selection", menu_draw_start
        )
        menu_draw = selected[menu_draw_start:menu_draw_end]
        self.assertNotIn("LIVE LOG TAIL", menu_draw)
        self.assertNotIn("a90_hud_draw_log_tail_panel(", menu_draw)

        action_start = selected.index("switch (item->action)", draw_start)
        action_end = selected.index("static void auto_hud_loop", action_start)
        selected_action = selected[action_start:action_end]
        action_cases = [
            line.strip().removeprefix("case ").removesuffix(":")
            for line in selected_action.splitlines()
            if line.strip().startswith("case SCREEN_MENU_")
        ]
        self.assertEqual(
            action_cases,
            [
                "SCREEN_MENU_RESUME",
                "SCREEN_MENU_SUBMENU",
                "SCREEN_MENU_BACK",
                "SCREEN_MENU_STATUS",
                "SCREEN_MENU_RECOVERY",
                "SCREEN_MENU_REBOOT",
                "SCREEN_MENU_POWEROFF",
            ],
        )

    def test_phase3_minimal_c_rejects_doom_before_shell_effects(self):
        dispatch = (
            REPO_ROOT
            / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"
        ).read_text(encoding="utf-8")
        hud = (
            REPO_ROOT
            / "workspace/public/src/native-init/v319/30_status_hud.inc.c"
        ).read_text(encoding="utf-8")

        early_executor_start = dispatch.index(
            "static int a90_execute_minimal_removed_doom_command("
        )
        early_executor_end = dispatch.index("#endif", early_executor_start)
        early_executor = dispatch[early_executor_start:early_executor_end]
        for forbidden in (
            "stop_auto_hud",
            "a90_logf",
            "a90_reaper",
            "monotonic_millis",
            "fork(",
            "open(",
            "socket(",
        ):
            self.assertNotIn(forbidden, early_executor)

        dispatch_start = dispatch.index("static int execute_shell_command(")
        dispatch_body = dispatch[dispatch_start:]
        early_reject = dispatch_body.index(
            "if (a90_minimal_removed_doom_command(argv, argc))"
        )
        self.assertLess(
            early_reject,
            dispatch_body.index("busy_reason ="),
        )
        self.assertLess(
            early_reject,
            dispatch_body.index('a90_logf("cmd", "start'),
        )
        self.assertLess(
            early_reject,
            dispatch_body.index("stop_auto_hud(false)"),
        )

        reject_start = hud.index("static int video_demo_doom_removed(void)")
        reject_end = hud.index("#endif", reject_start)
        reject_body = hud[reject_start:reject_end]
        for forbidden in (
            "a90_audio",
            "a90_doomgeneric_bridge",
            "a90_kms",
            "a90_logf",
            "fork(",
            "open(",
            "socket(",
            "write(",
        ):
            self.assertNotIn(forbidden, reject_body)

    def test_phase3_minimal_b_replaces_operational_doom_bridge(self):
        minimal = buildlib.resolve_manifest(MINIMAL_B_MANIFEST).data
        buildlib.validate_component_selection(minimal)
        self.assertEqual(
            minimal["profile"],
            "phase3-minimal-b-inert-doom-surface",
        )
        self.assertFalse(minimal["candidate_authority"])
        self.assertFalse(minimal["engine"]["enabled"])
        self.assertEqual(len(minimal["init"]["sources"]), 60)
        self.assertNotIn(
            "a90_doomgeneric_bridge.c",
            minimal["init"]["sources"],
        )
        self.assertIn(
            "a90_doomgeneric_bridge_inert.c",
            minimal["init"]["sources"],
        )
        self.assertEqual(len(minimal["init"]["cflags"]), 37)
        self.assertFalse(
            any("DOOMGENERIC" in item for item in minimal["init"]["cflags"])
        )
        self.assertEqual(minimal["validation"]["engine_strings"], [])
        self.assertNotIn("engine", build.artifact_names(minimal))

    def test_disabled_engine_contract_rejects_ramdisk_reachability(self):
        minimal = buildlib.resolve_manifest(MINIMAL_MANIFEST).data
        cases = {
            "not-obsolete": lambda value: value["ramdisk"][
                "obsolete_engines"
            ].remove(value["engine"]["ramdisk_path"]),
            "still-required": lambda value: value["ramdisk"][
                "required_entries"
            ].append(value["engine"]["ramdisk_path"]),
            "marker-retained": lambda value: value["validation"][
                "engine_strings"
            ].append("stale engine marker"),
        }
        for name, mutate in cases.items():
            with self.subTest(name=name):
                changed = copy.deepcopy(minimal)
                mutate(changed)
                with self.assertRaisesRegex(
                    buildlib.ManifestError,
                    "disabled engine is not removed",
                ):
                    buildlib.validate_component_selection(changed)

    def test_packed_ramdisk_rejects_stale_engine_variants(self):
        minimal = buildlib.resolve_manifest(MINIMAL_MANIFEST).data
        listing = set(minimal["ramdisk"]["required_entries"])
        listing.add("bin/a90_doomgeneric_private_engine_v3368")
        with self.assertRaisesRegex(
            buildlib.ManifestError,
            "packed ramdisk engine selection mismatch",
        ):
            buildlib.validate_ramdisk_component_listing(minimal, listing)

        active = set(self.manifest["ramdisk"]["required_entries"])
        buildlib.validate_ramdisk_component_listing(self.manifest, active)
        active.add("bin/a90_doomgeneric_private_engine_v3383")
        with self.assertRaisesRegex(
            buildlib.ManifestError,
            "packed ramdisk engine selection mismatch",
        ):
            buildlib.validate_ramdisk_component_listing(self.manifest, active)

    def test_actual_packed_archive_is_reopened_for_component_validation(self):
        minimal = buildlib.resolve_manifest(MINIMAL_MANIFEST).data
        entries = {
            name: b"content"
            for name in minimal["ramdisk"]["required_entries"]
        }
        entries["bin/a90_doomgeneric_private_engine_v9999"] = b"stale"
        with tempfile.TemporaryDirectory() as temp_name:
            archive = Path(temp_name) / "ramdisk.cpio"
            archive.write_bytes(newc_archive(entries))
            with self.assertRaisesRegex(
                buildlib.ManifestError,
                "packed ramdisk engine selection mismatch",
            ):
                build.validate_packed_ramdisk(minimal, archive)

            del entries["bin/a90_doomgeneric_private_engine_v9999"]
            archive.write_bytes(newc_archive(entries))
            self.assertEqual(
                build.validate_packed_ramdisk(minimal, archive),
                set(entries),
            )

    def test_builder_source_keys_bind_both_execution_files(self):
        keys = build.builder_source_keys(REPO_ROOT)
        self.assertEqual(
            set(keys),
            {"flat_builder", "flat_builder_library"},
        )
        for value in keys.values():
            path = REPO_ROOT / value["path"]
            self.assertEqual(value["size"], path.stat().st_size)
            self.assertEqual(value["sha256"], buildlib.sha256_file(path))

        changed = copy.deepcopy(keys)
        changed["flat_builder"]["sha256"] = "0" * 64
        resolution = buildlib.resolve_manifest(MINIMAL_F_MANIFEST)
        inputs = buildlib.validate_inputs(
            REPO_ROOT,
            resolution,
            resolution.data,
        )
        with self.assertRaisesRegex(RuntimeError, "source closure changed"):
            build.revalidate_execution_closure(
                REPO_ROOT,
                resolution,
                resolution.data,
                inputs,
                changed,
            )

    def test_newc_parser_rejects_truncated_or_nonzero_trailer_padding(self):
        valid = newc_archive({"init": b"payload"})
        with self.assertRaisesRegex(buildlib.ManifestError, "truncated"):
            buildlib.newc_archive_listing(valid[:100])
        changed = bytearray(valid)
        changed[-1] = 1
        with self.assertRaisesRegex(buildlib.ManifestError, "invalid newc trailer"):
            buildlib.newc_archive_listing(bytes(changed))

    def test_newc_parser_rejects_cpio_canonicalization_aliases(self):
        aliases = (
            "././bin/a90_doomgeneric_private_engine_v9999",
            "bin/./a90_doomgeneric_private_engine_v9999",
            "bin//a90_doomgeneric_private_engine_v9999",
            "./bin/../bin/a90_doomgeneric_private_engine_v9999",
        )
        for alias in aliases:
            with self.subTest(alias=alias):
                with self.assertRaisesRegex(
                    buildlib.ManifestError,
                    "noncanonical",
                ):
                    buildlib.newc_archive_listing(
                        newc_archive({alias: b"stale"})
                    )

    def test_newc_parser_requires_exact_eight_digit_ascii_hex_fields(self):
        valid = newc_archive({"init": b"payload"})
        name_size_offset = 6 + (11 * 8)
        for encoded in (b"+0000005", b" 0000005", b"0000_005"):
            with self.subTest(encoded=encoded):
                changed = bytearray(valid)
                changed[name_size_offset:name_size_offset + 8] = encoded
                with self.assertRaisesRegex(
                    buildlib.ManifestError,
                    "malformed newc header",
                ):
                    buildlib.newc_archive_listing(bytes(changed))

    def test_newc_parser_requires_zero_member_alignment_padding(self):
        valid = newc_archive({"abc": b"x"})
        name_padding = bytearray(valid)
        name_padding[114] = 1
        with self.assertRaisesRegex(
            buildlib.ManifestError,
            "invalid member-name padding",
        ):
            buildlib.newc_archive_listing(bytes(name_padding))

        data_padding = bytearray(valid)
        data_padding[117] = 1
        with self.assertRaisesRegex(
            buildlib.ManifestError,
            "invalid member-data padding",
        ):
            buildlib.newc_archive_listing(bytes(data_padding))

    def test_virtual_prefixes_are_public_and_random_seed_is_fixed(self):
        self.assertEqual(
            self.manifest["init"]["virtual_source_root"],
            "/usr/src/a90/native-init",
        )
        self.assertEqual(
            self.manifest["engine"]["virtual_doom_root"],
            "/usr/src/a90/doomgeneric",
        )
        self.assertEqual(
            self.manifest["random_seed"],
            "a90-v3404-effective-portable-v1",
        )
        flags = buildlib.init_flags(self.manifest, self.inputs)
        self.assertTrue(any(flag.startswith("-ffile-prefix-map=") for flag in flags))
        self.assertTrue(any(flag.endswith("=/usr/src/a90/native-init") for flag in flags))

    def test_pipeline_imports_no_legacy_builder(self):
        for path in (
            HERE / "a90_flat_builder/buildlib.py",
            HERE / "a90_flat_builder/build.py",
        ):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            imported = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported.append(node.module)
            self.assertFalse(
                any(name.startswith("build_native_init") for name in imported),
                path,
            )

    def test_noop_child_resolves_exactly_to_flat_baseline(self):
        child = buildlib.resolve_manifest(NOOP_MANIFEST)
        self.assertEqual(child.data, self.manifest)
        self.assertEqual(
            child.effective_sha256,
            self.resolution.effective_sha256,
        )
        self.assertEqual(
            [path.parent.name for path in child.lineage],
            ["flat-builder-v1-noop", "v3404-effective"],
        )
        self.assertEqual(
            child.origin_for(
                "engine",
                "materialized_sources",
                "adapter",
                "path",
            ),
            MANIFEST.resolve(),
        )
        with self.assertRaisesRegex(
            buildlib.ManifestError,
            "native-init closure changed",
        ):
            buildlib.validate_inputs(REPO_ROOT, child, child.data)

    def test_child_rejects_unknown_top_level_and_nested_keys(self):
        cases = {
            "unknown-top": "surprise = true\n",
            "unknown-nested": "[init]\ntypo_flag = true\n",
        }
        for name, overlay in cases.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                versions = Path(directory) / "versions"
                self._write_manifest_tree(versions)
                child = versions / "child/manifest.toml"
                child.parent.mkdir()
                child.write_text(
                    'schema = "a90-flat-builder-v1"\n'
                    'extends = "base"\n'
                    + overlay,
                    encoding="utf-8",
                )
                with self.assertRaisesRegex(
                    buildlib.ManifestError,
                    "unknown",
                ):
                    buildlib.resolve_manifest(child)

    def test_child_rejects_inherited_value_type_change(self):
        with tempfile.TemporaryDirectory() as directory:
            versions = Path(directory) / "versions"
            self._write_manifest_tree(versions)
            child = versions / "child/manifest.toml"
            child.parent.mkdir()
            child.write_text(
                'schema = "a90-flat-builder-v1"\n'
                'extends = "base"\n'
                "[init]\n"
                'cflags = "not-a-list"\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(buildlib.ManifestError, "changes type"):
                buildlib.resolve_manifest(child)

    def test_child_rejects_cycles_and_deep_lineage(self):
        with tempfile.TemporaryDirectory() as directory:
            versions = Path(directory) / "versions"
            versions.mkdir()
            for name, parent in (("a", "b"), ("b", "a")):
                path = versions / name / "manifest.toml"
                path.parent.mkdir()
                path.write_text(
                    'schema = "a90-flat-builder-v1"\n'
                    f'extends = "{parent}"\n',
                    encoding="utf-8",
                )
            with self.assertRaisesRegex(buildlib.ManifestError, "cycle"):
                buildlib.resolve_manifest(versions / "a/manifest.toml")

        with tempfile.TemporaryDirectory() as directory:
            versions = Path(directory) / "versions"
            self._write_manifest_tree(versions)
            middle = versions / "middle/manifest.toml"
            middle.parent.mkdir()
            middle.write_text(
                'schema = "a90-flat-builder-v1"\n'
                'extends = "base"\n',
                encoding="utf-8",
            )
            child = versions / "child/manifest.toml"
            child.parent.mkdir()
            child.write_text(
                'schema = "a90-flat-builder-v1"\n'
                'extends = "middle"\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(buildlib.ManifestError, "depth"):
                buildlib.resolve_manifest(child)

    def test_child_rejects_path_like_parent_and_authority_escalation(self):
        for parent in ("../base", "/base", "base/other"):
            with self.subTest(parent=parent), tempfile.TemporaryDirectory() as directory:
                child = Path(directory) / "versions/child/manifest.toml"
                child.parent.mkdir(parents=True)
                child.write_text(
                    'schema = "a90-flat-builder-v1"\n'
                    f'extends = "{parent}"\n',
                    encoding="utf-8",
                )
                with self.assertRaisesRegex(buildlib.ManifestError, "invalid extends"):
                    buildlib.resolve_manifest(child)

        with tempfile.TemporaryDirectory() as directory:
            versions = Path(directory) / "versions"
            self._write_manifest_tree(versions)
            child = versions / "child/manifest.toml"
            child.parent.mkdir()
            child.write_text(
                'schema = "a90-flat-builder-v1"\n'
                'extends = "base"\n'
                "candidate_authority = true\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                buildlib.ManifestError,
                "candidate authority",
            ):
                buildlib.resolve_manifest(child)

    def test_manifest_resolution_rejects_file_and_profile_symlinks(self):
        with tempfile.TemporaryDirectory() as directory:
            versions = Path(directory) / "versions"
            self._write_manifest_tree(versions)
            child = versions / "child/manifest.toml"
            child.parent.mkdir()
            child.symlink_to(versions / "base/manifest.toml")
            with self.assertRaisesRegex(buildlib.ManifestError, "symlink"):
                buildlib.resolve_manifest(child)

    def test_manifest_lineage_hashes_detect_post_resolution_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            versions = Path(directory) / "versions"
            self._write_manifest_tree(versions)
            child = versions / "child/manifest.toml"
            child.parent.mkdir()
            child.write_text(
                'schema = "a90-flat-builder-v1"\n'
                'extends = "base"\n',
                encoding="utf-8",
            )
            resolution = buildlib.resolve_manifest(child)
            self.assertEqual(len(resolution.lineage_sha256), 2)
            buildlib.revalidate_manifest_lineage(resolution)
            child.write_text(
                'schema = "a90-flat-builder-v1"\n'
                'extends = "base"\n'
                "# drift\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(buildlib.ManifestError, "changed"):
                buildlib.revalidate_manifest_lineage(resolution)

        with tempfile.TemporaryDirectory() as directory:
            versions = Path(directory) / "versions"
            self._write_manifest_tree(versions)
            alias = versions / "alias"
            alias.symlink_to(versions / "base", target_is_directory=True)
            child = versions / "child/manifest.toml"
            child.parent.mkdir()
            child.write_text(
                'schema = "a90-flat-builder-v1"\n'
                'extends = "alias"\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(buildlib.ManifestError, "symlink"):
                buildlib.resolve_manifest(child)

    def test_output_contract_rejects_outside_private_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(RuntimeError):
                build.output_root(REPO_ROOT, Path(directory) / "flat")

    def test_manifest_argument_is_confined_to_one_profile_directory(self):
        self.assertEqual(build.selected_manifest(MANIFEST), MANIFEST.resolve())
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "must stay below"):
                build.selected_manifest(Path(directory) / "manifest.toml")
        with self.assertRaisesRegex(RuntimeError, "versions/<host-profile>"):
            build.selected_manifest(
                MANIFEST.parent / "nested/manifest.toml"
            )
        with tempfile.TemporaryDirectory(
            dir=MANIFEST.parent.parent,
        ) as directory:
            alias = Path(directory) / "alias"
            alias.symlink_to(MANIFEST.parent, target_is_directory=True)
            with self.assertRaisesRegex(RuntimeError, "symlink"):
                build.selected_manifest(alias / "manifest.toml")

    def test_ramdisk_paths_reject_absolute_and_parent_escape(self):
        root = Path("/tmp/ramdisk")
        self.assertEqual(
            build.safe_ramdisk_path(root, "bin/helper", "test"),
            root / "bin/helper",
        )
        for relative in ("/bin/helper", "../helper", "bin/../../helper"):
            with self.assertRaises(RuntimeError):
                build.safe_ramdisk_path(root, relative, "test")

    @staticmethod
    def _write_manifest_tree(versions: Path) -> None:
        base = versions / "base/manifest.toml"
        base.parent.mkdir(parents=True)
        data = copy.deepcopy(buildlib.resolve_manifest(MANIFEST).data)

        def toml_scalar(value):
            if isinstance(value, bool):
                return "true" if value else "false"
            if isinstance(value, int):
                return str(value)
            if isinstance(value, str):
                return repr(value)
            raise TypeError(value)

        lines = []
        tables: list[tuple[tuple[str, ...], dict]] = [((), data)]
        while tables:
            prefix, table = tables.pop(0)
            if prefix:
                lines.append("[" + ".".join(prefix) + "]")
            for key, value in table.items():
                if isinstance(value, dict):
                    tables.append(((*prefix, key), value))
                elif isinstance(value, list):
                    items = ", ".join(toml_scalar(item) for item in value)
                    lines.append(f"{key} = [{items}]")
                else:
                    lines.append(f"{key} = {toml_scalar(value)}")
            lines.append("")
        base.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
