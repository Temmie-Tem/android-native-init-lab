from __future__ import annotations

import unittest

from _loader import REPO_ROOT, load_script


runner = load_script("workspace/public/src/scripts/revalidation/native_doom_drm_plane_scaling_probe_v3107.py")


class NativeDoomDrmPlaneScalingProbeV3107Tests(unittest.TestCase):
    def test_contract_pins_v3107_probe_paths(self) -> None:
        self.assertEqual(runner.RUN_ID, "V3107")
        self.assertEqual(runner.REMOTE_HELPER, "/cache/bin/a90_drm_plane_probe_v3107")
        self.assertEqual(
            runner.HELPER_SOURCE,
            REPO_ROOT / "workspace/public/src/native-init/helpers/a90_drm_plane_probe_v3107.c",
        )
        self.assertEqual(
            runner.REPORT_PATH,
            REPO_ROOT / "docs/reports/NATIVE_INIT_V3107_DOOM_DRM_PLANE_SCALING_PROBE_2026-06-23.md",
        )
        self.assertTrue(callable(runner.install_helper))

    def test_helper_source_is_read_only_plane_inventory(self) -> None:
        source = runner.HELPER_SOURCE.read_text(encoding="utf-8")

        self.assertIn("DRM_IOCTL_MODE_GETPLANERESOURCES", source)
        self.assertIn("DRM_IOCTL_MODE_GETPLANE", source)
        self.assertIn("DRM_IOCTL_MODE_OBJ_GETPROPERTIES", source)
        self.assertIn("DRM_CLIENT_CAP_UNIVERSAL_PLANES", source)
        self.assertIn("infer_active_crtc_from_planes", source)
        self.assertIn("probe.active.source", source)
        self.assertIn("probe.hw_scale_candidate_count", source)
        self.assertIn("probe.hw_scale.exposed", source)
        self.assertNotIn("DRM_IOCTL_MODE_SETPLANE", source)
        self.assertNotIn("DRM_IOCTL_MODE_PAGE_FLIP", source)
        self.assertNotIn("DRM_IOCTL_MODE_SETCRTC", source)
        self.assertNotIn("DRM_IOCTL_MODE_DIRTYFB", source)
        self.assertNotIn(".".join(("192", "168")), runner.Path(runner.__file__).read_text(encoding="utf-8"))

    def test_parse_probe_stdout_extracts_candidate_summary(self) -> None:
        text = "\n".join(
            [
                "probe.version=1",
                "probe.planes.count=2",
                "probe.active.source=current-plane",
                "probe.active.connector_scan.rc=-19",
                "probe.active.fallback.current_plane.rc=0",
                "probe.active.connector_id=0 encoder_id=0 crtc_id=133 crtc_index=0 current_plane_id=31 current_plane_index=0",
                "plane.0.id=31 current_crtc=0 current_fb=0 possible_crtcs=0x1 compatible_active_crtc=1 formats=3 has_xbgr8888=1 has_xrgb8888=0 props_rc=0 props_count=9 rect_props=1 candidate=1",
                "plane.0.props.fb_id=1 crtc_id=1 crtc_rect=1 src_rect=1 type=1",
                "plane.0.formats.sample=XB24,XR24",
                "plane.1.id=32 current_crtc=0 current_fb=0 possible_crtcs=0x2 compatible_active_crtc=0 formats=1 has_xbgr8888=0 has_xrgb8888=1 props_rc=0 props_count=9 rect_props=1 candidate=0",
                "probe.compatible_plane_count=1",
                "probe.rect_props_plane_count=2",
                "probe.hw_scale_candidate_count=1",
                "probe.hw_scale.exposed=1",
                "probe.result=v3107-drm-plane-scaling-candidate",
            ]
        )

        parsed = runner.parse_probe_stdout(text)

        self.assertEqual(parsed["plane_count"], 2)
        self.assertEqual(parsed["compatible_plane_count"], 1)
        self.assertEqual(parsed["rect_props_plane_count"], 2)
        self.assertEqual(parsed["candidate_count"], 1)
        self.assertTrue(parsed["hw_scale_exposed"])
        self.assertEqual(parsed["planes"]["0"]["id"], "31")
        self.assertEqual(parsed["planes"]["0"]["candidate"], "1")
        self.assertEqual(parsed["planes"]["0"]["formats_sample"], "XB24,XR24")
        self.assertEqual(parsed["values"]["probe.active.source"], "current-plane")
        self.assertEqual(parsed["values"]["probe.active.crtc_id"], "133")
        self.assertEqual(parsed["values"]["probe.active.current_plane_id"], "31")

    def test_report_template_records_next_branch(self) -> None:
        summary = {
            "decision": runner.DECISION_PASS,
            "version_ok": True,
            "pre_selftest_fail0": True,
            "post_selftest_fail0": True,
            "build": {"helper_sha256": "abc", "helper_size": 123},
            "install_path": "tcpctl",
            "probe": {
                "hw_scale_exposed": True,
                "plane_count": 1,
                "compatible_plane_count": 1,
                "rect_props_plane_count": 1,
                "candidate_count": 1,
                "values": {
                    "probe.node": "/dev/dri/card0",
                    "probe.client_cap.universal_planes.rc": "0",
                    "probe.client_cap.atomic.rc": "0",
                    "probe.resources.crtcs": "3",
                    "probe.active.source": "current-plane",
                    "probe.active.connector_scan.rc": "-19",
                    "probe.active.fallback.current_plane.rc": "0",
                    "probe.active.connector_id": "28",
                    "probe.active.encoder_id": "27",
                    "probe.active.crtc_id": "133",
                    "probe.active.crtc_index": "0",
                    "probe.active.current_plane_id": "31",
                },
                "planes": {
                    "0": {
                        "id": "31",
                        "compatible_active_crtc": "1",
                        "rect_props": "1",
                        "has_xbgr8888": "1",
                        "has_xrgb8888": "0",
                        "candidate": "1",
                        "formats_sample": "XB24",
                    }
                },
            },
        }

        report = runner.render_report(summary)

        self.assertIn("Native Init V3107 DOOM DRM Plane Scaling Probe", report)
        self.assertIn("Hardware scale exposed: `1`", report)
        self.assertIn("Install path: `tcpctl`", report)
        self.assertIn("Active source: `current-plane`", report)
        self.assertIn("bounded V3108 plane-scaling", report)
        self.assertIn("No boot", report)


if __name__ == "__main__":
    unittest.main()
