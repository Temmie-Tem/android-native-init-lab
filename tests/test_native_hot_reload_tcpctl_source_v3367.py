import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "workspace" / "public" / "src" / "scripts" / "revalidation"))

import build_native_init_boot_v3367_hot_reload_tcpctl as runner  # noqa: E402


class NativeHotReloadTcpctlSourceV3367Test(unittest.TestCase):
    def test_required_strings_cover_h4_tcpctl_contract(self) -> None:
        required = b"\n".join(runner.REQUIRED_STRINGS)
        self.assertIn(b"0.11.128", required)
        self.assertIn(b"v3367-hot-reload-tcpctl", required)
        self.assertIn(b"A90RELOAD", required)
        self.assertIn(b"INIT-RELOAD-EXECVE", required)
        self.assertIn(b"hot-reload fast-path (A90_RELOADED set)", required)
        self.assertIn(b"storage-adopt", required)
        self.assertIn(b"sd already mounted rw", required)
        self.assertIn(b"/cache already mounted rw", required)
        self.assertIn(b"tcpctl-adopt", required)
        self.assertIn(b"Hot-reload: tcpctl ready", required)
        self.assertIn(b"refreshing tcpctl on existing NCM", required)

    def test_storage_source_adopts_existing_rw_mounts(self) -> None:
        source = (
            ROOT
            / "workspace"
            / "public"
            / "src"
            / "native-init"
            / "a90_storage.c"
        ).read_text(encoding="utf-8")
        self.assertIn("storage_finish_sd_rw_ready", source)
        self.assertIn("saved_errno == EBUSY", source)
        self.assertIn("mount_line_for_path(CACHE_STORAGE_ROOT", source)
        self.assertIn('"cache-adopt"', source)
        self.assertIn('"storage-adopt"', source)
        self.assertIn('"[ SD     ] ADOPT RW MOUNT"', source)
        self.assertIn("return storage_finish_sd_rw_ready(hooks, ctx, false);", source)
        self.assertIn("return storage_finish_sd_rw_ready(hooks, ctx, true);", source)

    def test_tcpctl_source_adopts_existing_listener(self) -> None:
        source = (
            ROOT
            / "workspace"
            / "public"
            / "src"
            / "native-init"
            / "a90_netservice.c"
        ).read_text(encoding="utf-8")
        self.assertIn("netservice_find_existing_tcpctl_listener", source)
        self.assertIn('"/proc/%ld/cmdline"', source)
        self.assertIn("NETSERVICE_TCPCTL_HELPER", source)
        self.assertIn("NETSERVICE_TCP_BIND_ADDR", source)
        self.assertIn("NETSERVICE_TCP_PORT", source)
        self.assertIn("NETSERVICE_TCP_TOKEN_PATH", source)
        self.assertIn('"tcpctl-adopt"', source)
        self.assertIn("a90_service_set_pid(A90_SERVICE_TCPCTL, pid)", source)

    def test_report_states_source_build_not_live_h4(self) -> None:
        manifest = {
            "boot_image": "workspace/private/inputs/boot_images/boot_linux_v3367_hot_reload_tcpctl.img",
            "boot_sha256": "0" * 64,
            "helper_sha256": "1" * 64,
        }
        report = runner.render_report(manifest, ("flag-a",), ("flag-b",))
        self.assertIn("Decision: `v3367-hot-reload-tcpctl-source-build`", report)
        self.assertIn("H4 cleanup candidate", report)
        self.assertIn("refresh tcpctl after PID1 hot-reload", report)
        self.assertIn("tcpctl=running", report)
        self.assertIn("No live H4 reload result is claimed", report)

    def test_reload_command_and_fast_path_are_preserved(self) -> None:
        dispatch = (
            ROOT
            / "workspace"
            / "public"
            / "src"
            / "native-init"
            / "v319"
            / "80_shell_dispatch.inc.c"
        ).read_text(encoding="utf-8")
        self.assertIn(
            '{ "reload", handle_init_reload, '
            '"reload <token> <staged-init-path> <expected-sha256>",',
            dispatch,
        )
        self.assertIn("CMD_DANGEROUS | CMD_NO_DONE", dispatch)

        main_source = (
            ROOT
            / "workspace"
            / "public"
            / "src"
            / "native-init"
            / "v724"
            / "90_main.inc.c"
        ).read_text(encoding="utf-8")
        self.assertIn('getenv("A90_RELOADED")', main_source)
        self.assertIn(
            "Hot-reload: skipping autohud/rshell re-init; refreshing tcpctl only.",
            main_source,
        )
        self.assertIn("refreshing tcpctl on existing NCM", main_source)
        self.assertIn("a90_netservice_start();", main_source)
        self.assertIn("Hot-reload: tcpctl ready", main_source)


if __name__ == "__main__":
    unittest.main()
