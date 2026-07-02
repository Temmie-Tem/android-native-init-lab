import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "workspace" / "public" / "src" / "scripts" / "revalidation"))

import build_native_init_boot_v3365_hot_reload_delta as runner  # noqa: E402


class NativeHotReloadDeltaSourceV3365Test(unittest.TestCase):
    def test_required_strings_cover_h2_delta_contract(self) -> None:
        required = b"\n".join(runner.REQUIRED_STRINGS)
        self.assertIn(b"0.11.126", required)
        self.assertIn(b"v3365-hot-reload-delta", required)
        self.assertIn(b"A90RELOAD", required)
        self.assertIn(b"INIT-RELOAD-EXECVE", required)
        self.assertIn(b"reload <token> <staged-init-path> <expected-sha256>", required)
        self.assertIn(b"host_note=serial-persists-no-reboot", required)
        self.assertIn(b"hot-reload fast-path (A90_RELOADED set)", required)
        self.assertIn(b"Hot-reload: skipping autohud/netservice/rshell re-init", required)

    def test_report_states_source_build_not_live_h2(self) -> None:
        manifest = {
            "boot_image": "workspace/private/inputs/boot_images/boot_linux_v3365_hot_reload_delta.img",
            "boot_sha256": "0" * 64,
            "helper_sha256": "1" * 64,
        }
        report = runner.render_report(manifest, ("flag-a",), ("flag-b",))
        self.assertIn("Decision: `v3365-hot-reload-delta-source-build`", report)
        self.assertIn("H2 delta candidate", report)
        self.assertIn("V3364 as the resident", report)
        self.assertIn("version` reports `0.11.126` / `v3365-hot-reload-delta`", report)
        self.assertIn("No live H2 reload result is claimed", report)

    def test_reload_command_stays_token_gated_and_no_done(self) -> None:
        dispatch = (
            ROOT
            / "workspace"
            / "public"
            / "src"
            / "native-init"
            / "v319"
            / "80_shell_dispatch.inc.c"
        ).read_text(encoding="utf-8")
        self.assertIn("static int handle_init_reload", dispatch)
        self.assertIn(
            '{ "reload", handle_init_reload, '
            '"reload <token> <staged-init-path> <expected-sha256>",',
            dispatch,
        )
        self.assertIn("CMD_DANGEROUS | CMD_NO_DONE", dispatch)

        source = (
            ROOT
            / "workspace"
            / "public"
            / "src"
            / "native-init"
            / "a90_init_reload.c"
        ).read_text(encoding="utf-8")
        self.assertIn('A90_RELOAD_TOKEN "INIT-RELOAD-EXECVE"', source)
        self.assertIn('A90_RELOAD_STAGE_ROOT "/mnt/sdext/a90/flash-staging/"', source)
        self.assertIn('"A90_RELOADED=1"', source)
        self.assertEqual(source.count("execve(path, newargv, newenv);"), 1)

    def test_main_fast_path_guard_is_preserved(self) -> None:
        source = (
            ROOT
            / "workspace"
            / "public"
            / "src"
            / "native-init"
            / "v724"
            / "90_main.inc.c"
        ).read_text(encoding="utf-8")
        self.assertIn('getenv("A90_RELOADED")', source)
        self.assertIn("hot-reload fast-path (A90_RELOADED set)", source)
        self.assertIn("Hot-reload: skipping autohud/netservice/rshell re-init", source)


if __name__ == "__main__":
    unittest.main()
