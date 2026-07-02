"""Regression tests for V3368 hot-reload autohud H5 source build."""

from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_revalidation


builder = load_revalidation("build_native_init_boot_v3368_hot_reload_autohud")


class BuildNativeInitBootV3368HotReloadAutohudTests(unittest.TestCase):
    def test_identity_and_required_markers(self) -> None:
        self.assertEqual(builder.CYCLE, "V3368")
        self.assertEqual(builder.INIT_VERSION, "0.11.129")
        self.assertEqual(builder.INIT_BUILD, "v3368-hot-reload-autohud")

        required = b"\n".join(builder.REQUIRED_STRINGS)
        self.assertIn(b"v3368-hot-reload-autohud", required)
        self.assertIn(b"reload: preserving autohud for DRM-master handoff", required)
        self.assertIn(b"Hot-reload: autohud adopted", required)
        self.assertIn(b"hotreload-autohud", required)
        self.assertIn(b"SETCRTC retry blocked by H5 guard", required)
        self.assertIn(b"Hot-reload: rshell ready", required)
        self.assertIn(b"hotreload-rshell", required)
        self.assertIn(b"Hot-reload: selftest/guard refreshed", required)
        self.assertIn(b"kms adopted by autohud", required)
        self.assertIn(b"display: adopted-autohud", required)
        self.assertNotIn(b"skipping autohud/rshell re-init", required)
        self.assertNotIn(b"skip autohud/rshell re-init", required)

    def test_reload_preserves_tmp_and_skips_boot_kms_present(self) -> None:
        boot_services = builder._rewrite_v3368_text(
            Path("workspace/public/src/native-init/v319/50_boot_services.inc.c").read_text(
                encoding="utf-8"
            )
        )
        menu_apps = builder._rewrite_v3368_text(
            Path("workspace/public/src/native-init/v319/40_menu_apps.inc.c").read_text(
                encoding="utf-8"
            )
        )

        self.assertIn('if (getenv("A90_RELOADED") == NULL) {', boot_services)
        self.assertIn('mount("tmpfs", "/tmp", "tmpfs", 0, "mode=1777");', boot_services)
        self.assertIn(
            'static void boot_auto_frame(void) {\n'
            '    if (getenv("A90_RELOADED") != NULL) {\n'
            '        return;\n'
            '    }',
            menu_apps,
        )

    def test_reload_handler_does_not_stop_existing_hud(self) -> None:
        dispatch = builder._rewrite_v3368_text(
            Path("workspace/public/src/native-init/v319/80_shell_dispatch.inc.c").read_text(
                encoding="utf-8"
            )
        )
        start = dispatch.index("static int handle_init_reload")
        block = dispatch[start:dispatch.index("\n}", start) + 2]

        self.assertIn("reload: preserving autohud for DRM-master handoff", block)
        self.assertIn("a90_init_reload_cmd(argv, argc);", block)
        self.assertNotIn("stop_auto_hud(false);", block)

    def test_reloaded_main_adopts_autohud_and_refreshes_rshell(self) -> None:
        main = builder._rewrite_v3368_text(
            Path("workspace/public/src/native-init/v724/90_main.inc.c").read_text(
                encoding="utf-8"
            )
        )
        start = main.index('if (a90_reloaded) {\n            pid_t hud_pid;')
        block = main[start:main.index("\n        } else {", start)]

        self.assertIn("hud_pid = auto_hud_adopt_pidfile();", block)
        self.assertIn('a90_controller_set_menu_active(true);', block)
        self.assertIn('"hotreload-autohud"', block)
        self.assertIn("SETCRTC retry blocked by H5 guard", block)
        self.assertIn("rshell_rc = rshell_start_service(false);", block)
        self.assertIn('"hotreload-rshell"', block)
        self.assertIn("a90_selftest_run_boot(&selftest_hooks, NULL);", block)
        self.assertIn("Hot-reload: selftest/guard refreshed", block)
        self.assertNotIn("skipping autohud/rshell re-init", block)

    def test_reloaded_selftest_accepts_adopted_hud_display(self) -> None:
        selftest = Path("workspace/public/src/native-init/a90_selftest.c").read_text(
            encoding="utf-8"
        )
        status = builder._rewrite_v3368_text(
            Path("workspace/public/src/native-init/v319/60_shell_basic_commands.inc.c").read_text(
                encoding="utf-8"
            )
        )

        self.assertIn('getenv("A90_RELOADED") != NULL && hud_pid > 0', selftest)
        self.assertIn("kms adopted by autohud pid=%ld", selftest)
        self.assertIn("display: adopted-autohud pid=%ld", status)


if __name__ == "__main__":
    unittest.main()
