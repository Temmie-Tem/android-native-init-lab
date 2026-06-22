from __future__ import annotations

import unittest

from _loader import REPO_ROOT, load_script


runner = load_script("workspace/public/src/scripts/revalidation/build_native_init_boot_v3081_doomgeneric_shared_frame.py")


class NativeDoomgenericSharedFrameSourceV3081Tests(unittest.TestCase):
    def test_builder_contract_pins_v3081_shared_frame_candidate(self) -> None:
        self.assertEqual(runner.CYCLE, "V3081")
        self.assertEqual(runner.INIT_VERSION, "0.10.97")
        self.assertEqual(runner.INIT_BUILD, "v3081-doomgeneric-shared-frame")
        self.assertEqual(runner.ENGINE_RAMDISK_PATH, "bin/a90_doomgeneric_private_engine_v3081")
        self.assertEqual(runner.ENGINE_NAME, "doomgeneric-private-link-v3081-shared-frame")
        self.assertEqual(runner.FRAME_PATH, "/tmp/a90-doomgeneric-v3081-raw-fallback-frame.xbgr8888")
        self.assertEqual(runner.SHARED_FRAME_PATH, "/tmp/a90-doomgeneric-v3081-shared-frame.bin")
        self.assertEqual(runner.INPUT_STATE_PATH, "/tmp/a90-doomgeneric-v3081-input.state")
        self.assertEqual(runner.INPUT_SOCKET_PATH, "/tmp/a90-doomgeneric-v3081-input.sock")
        self.assertEqual(runner.PACE_SOCKET_PATH, "/tmp/a90-doomgeneric-v3081-pace.sock")
        self.assertEqual(runner.LOOP_FRAME_MS, 28)
        self.assertEqual(runner.NATIVE_DASHBOARD_MINIMAL, 1)
        self.assertEqual(runner.NATIVE_DOOM_PRESENT_PAGEFLIP, 1)
        self.assertEqual(runner.REUSE_FRAME_BUFFER, 1)
        self.assertEqual(runner.FRAME_TIMING_PROBE, 1)
        self.assertIn(b"a90.doomgeneric.v3081.frame_ipc=shared-mmap-seq", runner.REQUIRED_STRINGS)
        self.assertIn(b"--shared-frame", runner.REQUIRED_STRINGS)
        self.assertIn(b"shared-mmap-copy", runner.REQUIRED_STRINGS)

    def test_base_builder_exposes_disabled_shared_frame_compile_flag(self) -> None:
        base_source = (
            REPO_ROOT
            / "workspace/public/src/scripts/revalidation/build_native_init_boot_v3033_doomgeneric_visible_loop.py"
        ).read_text(encoding="utf-8")

        self.assertIn('SHARED_FRAME_PATH = ""', base_source)
        self.assertIn("A90_DOOMGENERIC_BRIDGE_SHARED_FRAME_PATH", base_source)

    def test_native_bridge_and_hud_expose_shared_frame_reader(self) -> None:
        header = (REPO_ROOT / "workspace/public/src/native-init/a90_doomgeneric_bridge.h").read_text(encoding="utf-8")
        bridge = (REPO_ROOT / "workspace/public/src/native-init/a90_doomgeneric_bridge.c").read_text(encoding="utf-8")
        hud = (REPO_ROOT / "workspace/public/src/native-init/v319/30_status_hud.inc.c").read_text(encoding="utf-8")

        self.assertIn("A90_DOOMGENERIC_SHARED_FRAME_MAGIC", header)
        self.assertIn("struct a90_doomgeneric_shared_frame_header", header)
        self.assertIn("shared_frame_path", bridge)
        self.assertIn("doomgeneric_fill_shared_frame_render", bridge)
        self.assertIn('"--shared-frame"', bridge)
        self.assertIn("video_demo_doom_frame_reader_copy_shared", hud)
        self.assertIn("mmap(NULL, required_size, PROT_READ, MAP_SHARED", hud)
        self.assertIn("shared-mmap-seq", hud)
        self.assertIn("shared-mmap-copy", hud)

    def test_helper_adapter_adds_shared_frame_mmap_with_raw_fallback(self) -> None:
        source = runner.v3081_adapter_source()

        self.assertIn("a90.doomgeneric.v3081.frame_ipc=shared-mmap-seq", source)
        self.assertIn("#include <sys/mman.h>", source)
        self.assertIn("struct a90_dg_shared_frame_header", source)
        self.assertIn("a90_doomgeneric_open_shared_frame", source)
        self.assertIn("a90_doomgeneric_write_shared_frame", source)
        self.assertIn("a90_doomgeneric_close_shared_frame", source)
        self.assertIn("shared->header->sequence = sequence - 1U;", source)
        self.assertIn("shared->header->sequence = sequence;", source)
        close_fragment = source.split("static void a90_doomgeneric_close_shared_frame", 1)[1]
        self.assertNotIn("(void)unlink(shared->path)", close_fragment.split("static int", 1)[0])
        self.assertIn("rc = a90_doomgeneric_write_shared_frame(&shared_frame);", source)
        self.assertIn("rc = a90_doomgeneric_dump_frame_xbgr8888_atomic(output_path);", source)
        self.assertIn("argc == 11 || argc == 13 || argc == 15 || argc == 17 || argc == 19", source)
        self.assertIn("strcmp(argv[arg_index], \"--shared-frame\") == 0", source)
        self.assertIn(
            "a90_doomgeneric_run_wad_frame_loop(argv[2], frames, argv[6], argv[8], "
            "input_socket_path, input_udp_port, pace_socket_path, shared_frame_path, frame_ms)",
            source,
        )

    def test_v3081_mutates_v3079_build_surface_and_base_shared_path(self) -> None:
        runner.apply_v3081_globals()
        v3033 = runner.v3033_module()
        v3059 = runner.V3059

        self.assertEqual(runner.v3079.v3077.v3074.v3071.CYCLE, runner.CYCLE)
        self.assertEqual(runner.v3079.v3077.v3074.v3071.INIT_VERSION, runner.INIT_VERSION)
        self.assertEqual(runner.v3079.v3077.v3074.v3071.INIT_BUILD, runner.INIT_BUILD)
        self.assertEqual(v3033.SHARED_FRAME_PATH, runner.SHARED_FRAME_PATH)
        self.assertEqual(v3033.PACE_SOCKET_PATH, runner.PACE_SOCKET_PATH)
        self.assertIs(v3059.v3059_adapter_source, runner.v3081_adapter_source)

    def test_report_template_records_v3082_live_gate(self) -> None:
        manifest = {
            "decision": runner.DECISION,
            "boot_image": "workspace/private/inputs/boot_images/boot_linux_v3081.img",
            "boot_sha256": "boot-sha",
            "init_version": runner.INIT_VERSION,
            "init_build": runner.INIT_BUILD,
            "doomgeneric_visible_loop": {
                "runtime_wad_path": runner.RUNTIME_WAD_PATH,
                "expected_wad_sha256": runner.EXPECTED_WAD_SHA256,
                "helper_loop_command": "helper --shared-frame /tmp/a90-doomgeneric-v3081-shared-frame.bin",
            },
            "v3033_marker_strings": [
                "v3081-doomgeneric-shared-frame",
                "a90.doomgeneric.v3081.frame_ipc=shared-mmap-seq",
            ],
        }

        report = runner.render_report(manifest, ("helper-flag",), ("init-flag",))

        self.assertIn("Native Init V3081 DOOMGENERIC Shared Frame Source Build", report)
        self.assertIn("Baseline frame IPC: `raw-frame-file-rename-open-read`", report)
        self.assertIn("Candidate frame IPC: `shared-mmap-seq-copy`", report)
        self.assertIn("Run ID: `V3082`", report)
        self.assertIn("native_init_flash.py", report)


if __name__ == "__main__":
    unittest.main()
