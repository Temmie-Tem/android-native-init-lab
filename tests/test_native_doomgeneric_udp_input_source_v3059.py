from __future__ import annotations

import unittest

from _loader import REPO_ROOT, load_script


runner = load_script("workspace/public/src/scripts/revalidation/build_native_init_boot_v3059_doomgeneric_udp_input.py")


class NativeDoomgenericUdpInputSourceV3059Tests(unittest.TestCase):
    def test_builder_contract_pins_v3059_udp_input_candidate(self) -> None:
        self.assertEqual(runner.CYCLE, "V3059")
        self.assertEqual(runner.INIT_VERSION, "0.10.87")
        self.assertEqual(runner.INIT_BUILD, "v3059-doomgeneric-udp-input")
        self.assertEqual(runner.ENGINE_RAMDISK_PATH, "bin/a90_doomgeneric_private_engine_v3059")
        self.assertEqual(runner.ENGINE_NAME, "doomgeneric-private-link-v3059-udp-input")
        self.assertEqual(runner.FRAME_PATH, "/tmp/a90-doomgeneric-v3059-udp-input-frame.xbgr8888")
        self.assertEqual(runner.INPUT_STATE_PATH, "/tmp/a90-doomgeneric-v3059-input.state")
        self.assertEqual(runner.INPUT_SOCKET_PATH, "/tmp/a90-doomgeneric-v3059-input.sock")
        self.assertEqual(runner.INPUT_UDP_PORT, 30570)
        self.assertIn(
            b"a90.doomgeneric.v3059.input=udp-ncm-state-with-unix-dgram-fallback",
            runner.REQUIRED_STRINGS,
        )
        self.assertIn(b"--input-udp", runner.REQUIRED_STRINGS)
        self.assertIn(b"video.demo.input.udp_port=", runner.REQUIRED_STRINGS)

    def test_adapter_source_adds_nonblocking_udp_listener_and_state_mirror(self) -> None:
        source = runner.v3059_adapter_source()

        self.assertIn("#include <arpa/inet.h>", source)
        self.assertIn("a90.doomgeneric.v3059.input=udp-ncm-state-with-unix-dgram-fallback", source)
        self.assertIn("a90_doomgeneric_open_input_udp", source)
        self.assertIn("socket(AF_INET, SOCK_DGRAM, 0)", source)
        self.assertIn("addr.sin_addr.s_addr = htonl(INADDR_ANY)", source)
        self.assertIn("bind(fd, (const struct sockaddr *)&addr, sizeof(addr))", source)
        self.assertIn("a90_doomgeneric_write_input_state_mask", source)
        self.assertIn("a90_doomgeneric_drain_input_fd(input_udp_fd, input_state_path)", source)
        self.assertIn("a90_doomgeneric_drain_input_fd(input_socket_fd, input_state_path)", source)
        self.assertIn("--input-udp", source)
        self.assertIn("input_udp_port = (unsigned int)a90_doomgeneric_parse_positive_int", source)
        self.assertIn("input_socket_path, input_udp_port, frame_ms", source)

    def test_native_bridge_hud_and_host_keyboard_expose_udp_transport(self) -> None:
        bridge_source = (REPO_ROOT / "workspace/public/src/native-init/a90_doomgeneric_bridge.c").read_text(encoding="utf-8")
        bridge_header = (REPO_ROOT / "workspace/public/src/native-init/a90_doomgeneric_bridge.h").read_text(encoding="utf-8")
        hud_source = (REPO_ROOT / "workspace/public/src/native-init/v319/30_status_hud.inc.c").read_text(encoding="utf-8")
        base_builder = (
            REPO_ROOT
            / "workspace/public/src/scripts/revalidation/build_native_init_boot_v3033_doomgeneric_visible_loop.py"
        ).read_text(encoding="utf-8")
        host_keyboard = (
            REPO_ROOT
            / "workspace/public/src/scripts/revalidation/host_doompad_keyboard_v3033.py"
        ).read_text(encoding="utf-8")

        self.assertIn("input_udp_port", bridge_header)
        self.assertIn("A90_DOOMGENERIC_BRIDGE_INPUT_UDP_PORT", bridge_source)
        self.assertIn('"--input-udp"', bridge_source)
        self.assertIn("status.input_udp_port", bridge_source)
        self.assertIn("video.demo.input.udp_port=%u", hud_source)
        self.assertIn("INPUT_UDP_PORT = 0", base_builder)
        self.assertIn("A90_DOOMGENERIC_BRIDGE_INPUT_UDP_PORT", base_builder)
        self.assertIn("--input-transport", host_keyboard)
        self.assertIn("UdpInputSender", host_keyboard)
        self.assertIn("DEFAULT_UDP_HOST", host_keyboard)

    def test_report_template_records_v3060_live_gate(self) -> None:
        manifest = {
            "decision": runner.DECISION,
            "boot_image": "workspace/private/inputs/boot_images/boot_linux_v3059.img",
            "boot_sha256": "boot-sha",
            "init_version": runner.INIT_VERSION,
            "init_build": runner.INIT_BUILD,
            "doomgeneric_visible_loop": {
                "runtime_wad_path": runner.RUNTIME_WAD_PATH,
                "expected_wad_sha256": runner.EXPECTED_WAD_SHA256,
                "input_path": "udp-ncm-to-DG_GetKey-with-serial-doompad-fallback",
                "input_udp_port": runner.INPUT_UDP_PORT,
                "input_socket_path": runner.INPUT_SOCKET_PATH,
                "input_state_path": runner.INPUT_STATE_PATH,
                "frame_path": runner.FRAME_PATH,
                "helper_loop_command": "helper --input-udp 30570",
            },
            "v3033_marker_strings": [
                "v3059-doomgeneric-udp-input",
                "a90.doomgeneric.v3059.input=udp-ncm-state-with-unix-dgram-fallback",
            ],
        }

        report = runner.render_report(manifest, ("helper-flag",), ("init-flag",))

        self.assertIn("Native Init V3059 DOOMGENERIC UDP Input Source Build", report)
        self.assertIn("non-blocking UDP listener", report)
        self.assertIn("Run ID: `V3060`", report)
        self.assertIn("--input-transport udp", report)


if __name__ == "__main__":
    unittest.main()
