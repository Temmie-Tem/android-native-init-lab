from __future__ import annotations

import hashlib
import importlib
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SERVER_DISTRO = (
    REPO_ROOT / "workspace/public/src/scripts/server-distro"
)
REVALIDATION = (
    REPO_ROOT / "workspace/public/src/scripts/revalidation"
)
if str(SERVER_DISTRO) not in sys.path:
    sys.path.insert(0, str(SERVER_DISTRO))
if str(REVALIDATION) not in sys.path:
    sys.path.insert(0, str(REVALIDATION))

builder = importlib.import_module("prepare_phase2_display_v1_rootfs")
from a90_flat_builder import buildlib


PRESENTER = (
    REPO_ROOT
    / "workspace/public/src/scripts/server-distro/phase2_display_v1"
    / "a90_debian_display_v1.c"
)
LAUNCHER = PRESENTER.with_name("a90_debian_display_launcher_v1.sh")
INITTAB = PRESENTER.with_name("inittab")
NATIVE_KMS_C = REPO_ROOT / "workspace/public/src/native-init/a90_kms.c"
NATIVE_KMS_H = NATIVE_KMS_C.with_suffix(".h")
NATIVE_DISTRO = NATIVE_KMS_C.with_name("a90_server_distro.c")
FLAT_MANIFEST = (
    REPO_ROOT
    / "workspace/public/src/scripts/revalidation/a90_flat_builder"
    / "versions/phase2-display-v1/manifest.toml"
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class A90Phase2DisplayV1Tests(unittest.TestCase):
    def test_builder_import_has_one_canonical_identity_and_no_side_effect(self) -> None:
        self.assertEqual(
            builder.__name__,
            "prepare_phase2_display_v1_rootfs",
        )
        self.assertEqual(Path(builder.__file__).resolve(), SERVER_DISTRO / (
            "prepare_phase2_display_v1_rootfs.py"
        ))

    def test_rootfs_manifest_pins_complete_source_closure(self) -> None:
        manifest, _ = builder.load_manifest()
        sources = manifest["sources"]
        expected = {
            "presenter",
            "launcher",
            "inittab",
            "stage",
            "draw_c",
            "draw_h",
            "kms_h",
            "builder",
        }

        self.assertEqual(
            {key for key in sources if not key.endswith("_sha256")},
            expected,
        )
        for key in sorted(expected):
            path = builder.resolve_repo_file(sources[key], key)
            self.assertEqual(sha256_file(path), sources[f"{key}_sha256"])
        self.assertIs(manifest["candidate_authority"], False)

    def test_presenter_contract_and_faults(self) -> None:
        source = PRESENTER.read_text(encoding="utf-8")

        self.assertEqual(builder.validate_presenter_source(source), ())
        self.assertTrue(
            builder.validate_presenter_source(
                source.replace(
                    "if (drm_ioctl_retry(kms->fd, "
                    "DRM_IOCTL_SET_MASTER, NULL) < 0)",
                    "if (0)",
                    1,
                )
            )
        )
        self.assertTrue(
            builder.validate_presenter_source(
                source.replace("PR_SET_NO_NEW_PRIVS", "PR_GET_NO_NEW_PRIVS")
            )
        )

    def test_presenter_root_scan_precedes_privilege_drop(self) -> None:
        source = PRESENTER.read_text(encoding="utf-8")
        main = source[source.index("int main(int argc, char **argv)") :]
        release_marker = main.index("validate_native_release_marker()")
        zero_scan = main.index("count_process_state(", release_marker)
        kms_init = main.index("initialize_kms(&kms)", zero_scan)
        owner_scan = main.index("count_process_state(", kms_init)
        pid1_read = main.index('readlink("/proc/1/exe"', owner_scan)
        privilege_drop = main.index("drop_privileges(", pid1_read)
        present = main.index("present(&kms)", privilege_drop)
        ready_marker = main.index("write_ready_marker(", present)

        self.assertLess(
            release_marker,
            zero_scan,
        )
        self.assertLess(zero_scan, kms_init)
        self.assertLess(kms_init, owner_scan)
        self.assertLess(owner_scan, pid1_read)
        self.assertLess(pid1_read, privilege_drop)
        self.assertLess(privilege_drop, present)
        self.assertLess(present, ready_marker)
        self.assertIn('strcmp(pid1_exe, "/usr/sbin/init")', main)
        drop = source[
            source.index("static int drop_privileges(") :
            source.index("static int read_cap_eff(", source.index(
                "static int drop_privileges("
            ))
        ]
        self.assertIn("read_cap_eff(cap_eff, cap_eff_size)", drop)
        self.assertIn('strcmp(out, "0000000000000000")', source)
        self.assertIn("drm_node_major_minor=%u:%u", source)
        self.assertIn(
            "ensure_card0_node(&kms->drm_major, &kms->drm_minor)",
            source,
        )

    def test_launcher_and_inittab_are_bounded_and_network_independent(self) -> None:
        launcher = LAUNCHER.read_text(encoding="utf-8")
        inittab = INITTAB.read_text(encoding="utf-8")

        self.assertEqual(builder.validate_launcher(launcher), ())
        self.assertEqual(builder.validate_inittab(inittab), ())
        self.assertTrue(builder.validate_launcher(launcher + "\nwhile true\n"))
        self.assertTrue(
            builder.validate_launcher(launcher + "\nip link set ncm0 up\n")
        )
        self.assertTrue(
            builder.validate_inittab(
                inittab.replace(":once:", ":respawn:", 1)
            )
        )

    def test_native_release_orders_disable_destroy_drop_close_reset(self) -> None:
        source = NATIVE_KMS_C.read_text(encoding="utf-8")
        header = NATIVE_KMS_H.read_text(encoding="utf-8")
        release = source[source.index(
            "int a90_kms_release_for_handoff("
        ) : source.index(
            "struct a90_fb *a90_kms_framebuffer(",
        )]

        self.assertIn("O_RDWR | O_CLOEXEC", source)
        self.assertIn("F_SETFD, fd_flags | FD_CLOEXEC", source)
        self.assertIn("int disable_crtc_rc;", header)
        positions = (
            release.index("a90_kms_disable_scaled_plane()"),
            release.index("DRM_IOCTL_MODE_SETCRTC"),
            release.index("DRM_IOCTL_MODE_RMFB"),
            release.index("DRM_IOCTL_MODE_DESTROY_DUMB"),
            release.index("DRM_IOCTL_DROP_MASTER"),
            release.index("close(fd)"),
            release.index("kms_reset_after_release()"),
        )
        self.assertEqual(tuple(sorted(positions)), positions)

    def test_strict_handoff_releases_pid1_and_marks_work_root(self) -> None:
        source = NATIVE_DISTRO.read_text(encoding="utf-8")
        cleanup = source[source.index(
            "static int d_handoff_stop_display_owners_mode("
        ) : source.index(
            "static int d_handoff_stop_display_owners(",
        )]
        switch = source[source.index(
            "int a90_server_distro_switch_root_cmd("
        ) :]

        self.assertLess(
            cleanup.index("a90_kms_release_for_handoff(&kms_release)"),
            cleanup.index("d_handoff_count_all_drm_fds("),
        )
        self.assertIn("getpid() != 1", cleanup)
        self.assertIn("kms_release.release_complete", cleanup)
        self.assertIn(
            "d_handoff_stop_display_owners_mode(tag, true, NULL)",
            source,
        )
        self.assertLess(
            switch.index("d3_check_distro_init()"),
            switch.index(
                "d3_write_display_release_marker(&d3_last_display_release)"
            ),
        )
        self.assertLess(
            switch.index(
                "d3_write_display_release_marker(&d3_last_display_release)"
            ),
            switch.index("d3_move_core_mounts("),
        )
        self.assertIn(
            "O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC | O_NOFOLLOW",
            source,
        )

    def test_flat_profile_is_shallow_host_only_schema(self) -> None:
        resolution = buildlib.resolve_manifest(FLAT_MANIFEST)

        self.assertEqual(len(resolution.lineage), 2)
        self.assertEqual(
            tuple(path.parent.name for path in resolution.lineage),
            ("phase2-display-v1", "v3404-effective"),
        )
        self.assertEqual(
            resolution.data["profile"],
            "phase2-display-v1-native-handoff",
        )
        self.assertIs(resolution.data["candidate_authority"], False)
        self.assertEqual(
            resolution.data["init"]["closure_sha256"],
            buildlib.closure_sha256(
                REPO_ROOT / resolution.data["init"]["source_root"],
                buildlib.expanded_closure(
                    REPO_ROOT / resolution.data["init"]["source_root"],
                    resolution.data["init"]["sources"],
                    resolution.data["init"]["closure_globs"],
                ),
            ),
        )
        strings = set(resolution.data["validation"]["init_strings"])
        self.assertIn("A90D3DISPLAY", strings)
        self.assertFalse(any("V3406" in value for value in strings))

    def test_output_root_rejects_unscoped_and_existing_roots(self) -> None:
        with self.assertRaises(builder.ContractError):
            builder.output_root(Path("/tmp/a90-phase2-display-v1"))
        with self.assertRaises(builder.ContractError):
            builder.output_root(builder.PRIVATE_OUTPUTS)


if __name__ == "__main__":
    unittest.main()
