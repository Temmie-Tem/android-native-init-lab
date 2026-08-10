"""Static checks for native server-distro display-owner handoff cleanup."""

from __future__ import annotations

import unittest
from pathlib import Path


SERVER_DISTRO = Path("workspace/public/src/native-init/a90_server_distro.c")


class ServerDistroNativeHandoffCleanupTests(unittest.TestCase):
    def test_switch_root_module_stops_tracked_hud_and_scans_drm_holders(self) -> None:
        source = SERVER_DISTRO.read_text(encoding="utf-8")
        self.assertIn('#include "a90_service.h"', source)
        self.assertIn("a90_service_stop(A90_SERVICE_HUD, A90_D_HANDOFF_HUD_TIMEOUT_MS)", source)
        self.assertIn('opendir("/proc")', source)
        self.assertIn('strcmp(target, "/init") == 0', source)
        self.assertIn("d_handoff_pid_has_drm_fd", source)
        self.assertIn("d_handoff_path_is_drm_target", source)
        self.assertIn("SIGTERM", source)
        self.assertIn("SIGKILL", source)
        self.assertIn("handoff_display=done", source)

    def test_d3_strict_cleanup_runs_before_source_recheck_and_ro_mount(self) -> None:
        source = SERVER_DISTRO.read_text(encoding="utf-8")
        d3_command = source.index("a90_server_distro_switch_root_cmd")
        d3_cleanup = source.index("rc = d3_handoff_stop_display_owners_strict();", d3_command)
        d3_rehash = source.index(
            "d3_verify_source_sha_fd(",
            d3_cleanup,
        )
        d3_attach = source.index(
            "d3_attach_loop(image, &source, &loop_attached)",
            d3_rehash,
        )
        d3_mount = source.index("rc = d3_mount_root();", d3_attach)
        d3_check = source.index("rc = d3_check_distro_init();", d3_mount)
        d3_move = source.index("rc = d3_move_core_mounts(")
        self.assertLess(d3_cleanup, d3_rehash)
        self.assertLess(d3_rehash, d3_attach)
        self.assertLess(d3_attach, d3_mount)
        self.assertLess(d3_mount, d3_check)
        self.assertLess(d3_cleanup, d3_move)

    def test_d4_cleanup_still_runs_after_root_validation_before_mount_moves(self) -> None:
        source = SERVER_DISTRO.read_text(encoding="utf-8")
        d4_check = source.index("rc = d4_check_userdata_init();", source.index("a90_server_distro_switch_root_userdata_cmd"))
        d4_cleanup = source.index("rc = d_handoff_stop_display_owners(A90_D4_TAG);")
        d4_move = source.index("rc = d4_move_core_mounts(")
        self.assertLess(d4_check, d4_cleanup)
        self.assertLess(d4_cleanup, d4_move)

    def test_cleanup_failures_stop_before_switch_root_exec(self) -> None:
        source = SERVER_DISTRO.read_text(encoding="utf-8")
        self.assertIn("stop=handoff-display-owner", source)
        d3_cleanup_fail = source.index("stop=handoff-display-owner", source.index("a90_server_distro_switch_root_cmd"))
        d3_exec = source.index("execve(A90_D3_BUSYBOX, switch_argv, newenv);")
        self.assertLess(d3_cleanup_fail, d3_exec)

        d4_cleanup_fail = source.index("stop=handoff-display-owner", source.index("a90_server_distro_switch_root_userdata_cmd"))
        d4_exec = source.index("execve(A90_D4_BUSYBOX, switch_argv, newenv);")
        self.assertLess(d4_cleanup_fail, d4_exec)


if __name__ == "__main__":
    unittest.main()
