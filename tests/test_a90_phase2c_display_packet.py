from __future__ import annotations

import importlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
SERVER_DISTRO = REPO_ROOT / "workspace/public/src/scripts/server-distro"
if str(SERVER_DISTRO) not in sys.path:
    sys.path.insert(0, str(SERVER_DISTRO))

packet = importlib.import_module("a90_phase2c_display_packet")


NATIVE_LOG = "\n".join(
    (
        "A90D3DISPLAY native_kms_release rc=0 fd_before=7 "
        "disable_plane_rc=0 disable_crtc_rc=0 "
        "munmap_failures=0 rmfb_failures=0 destroy_dumb_failures=0 "
        "drop_master_rc=0 close_rc=0 release_complete=1",
        "A90D3DISPLAY native_pid1_drm_fd_count=0 observed=0",
        "A90D3DISPLAY other_drm_fd_count=0 observed=0",
        "A90D3DISPLAY native_kms_initialized=0 observed=0",
        "A90D3DISPLAY display_services_restart_blocked=1 "
        "corridor=synchronous-handoff",
        "",
    )
)
NATIVE_MARKER = "\n".join(
    (
        "schema=a90-native-display-release-v1",
        "native_pid1_drm_fd_count=0",
        "other_drm_fd_count=0",
        "native_kms_initialized=0",
        "display_services_restart_blocked=1",
        "release_complete=1",
        "",
    )
)
READY_MARKER = "\n".join(
    (
        "schema=a90-debian-display-v1",
        "pid1_exe=/usr/sbin/init",
        "presenter_pid=42",
        "presenter_uid=3904",
        "presenter_gid=3904",
        "presenter_cap_eff=0000000000000000",
        "no_new_privs=1",
        "controlling_vt=none",
        "drm_node=/dev/dri/card0",
        "drm_node_major_minor=226:0",
        "drm_master=1",
        "connector_id=31",
        "crtc_id=77",
        "mode=1080x2400@60",
        "setcrtc_rc=0",
        "native_pid1_drm_fd_count=0",
        "other_native_drm_fd_count=0",
        "presenter_self_drm_fd_count=1",
        "other_process_drm_fd_count=0",
        "native_init_process_count=0",
        "",
    )
)


class A90Phase2CDisplayPacketTests(unittest.TestCase):
    def test_contract_and_runtime_surface_are_host_only(self) -> None:
        contract = packet.load_contract()
        source = Path(packet.__file__).read_text(encoding="utf-8")

        self.assertIs(contract["candidate_authority"], False)
        self.assertIs(contract["device_action"], False)
        self.assertIs(contract["live_authority"], False)
        self.assertEqual(source.count("subprocess.run("), 1)
        debugfs = packet.function_slice(
            source,
            "def debugfs_path_absent(",
            "\ndef read_ext4_identity(",
        )
        self.assertIn('["debugfs", "-R", f"stat {target}", str(image)]', debugfs)

    def test_full_host_packet_binds_profiles_without_authority(self) -> None:
        result = packet.build_packet()

        self.assertEqual(result["schema"], packet.PACKET_SCHEMA)
        self.assertEqual(result["decision"], packet.DECISION)
        self.assertTrue(result["host_profiles_bound"])
        self.assertFalse(result["ready_for_live_candidate"])
        self.assertEqual(
            {item["code"] for item in result["blockers"]},
            {
                "FINAL_KEYED_ROOTFS_NOT_MATERIALIZED",
                "FRESH_D0_MANIFEST_APPROVAL_ABSENT",
            },
        )
        self.assertEqual(
            result["native"]["artifacts"]["boot"],
            "3d3e66535654a62f83c5772caba27624acc160911307190de458154acaefdabb",
        )
        self.assertEqual(
            set(result["native"]["verified_pairs"]),
            {"boot", "ramdisk", "init", "helper", "engine"},
        )
        for pair in result["native"]["verified_pairs"].values():
            self.assertEqual(pair["A"]["sha256"], pair["B"]["sha256"])
        self.assertEqual(
            result["debian"]["image_sha256"],
            "cf2cf17d5c706123f85b21d4f2479fc348329cdc09e48fe6406874328e3977c8",
        )
        self.assertEqual(
            result["debian"]["presenters"]["A"]["sha256"],
            result["debian"]["presenters"]["B"]["sha256"],
        )
        self.assertFalse(result["debian"]["observer_key_materialized"])
        self.assertTrue(
            result["machinery"]["checked_boot_only_coupled_route"]
        )
        self.assertTrue(
            result["machinery"]["display_observation_integrated"]
        )
        self.assertTrue(
            result["machinery"]["phase2_profile_supported_for_live_staging"]
        )
        self.assertEqual(
            result["safety"],
            {
                "host_only": True,
                "candidate_identity_created": False,
                "candidate_authority": False,
                "live_authority": False,
                "device_contact": False,
                "device_write": False,
                "rootfs_staged": False,
                "flash": False,
                "reboot": False,
            },
        )

    def test_native_release_validator_rejects_partial_cleanup(self) -> None:
        packet.validate_native_release_evidence(NATIVE_LOG, NATIVE_MARKER)
        with self.assertRaises(packet.ContractError):
            packet.validate_native_release_evidence(
                NATIVE_LOG.replace("disable_crtc_rc=0", "disable_crtc_rc=-16"),
                NATIVE_MARKER,
            )
        with self.assertRaises(packet.ContractError):
            packet.validate_native_release_evidence(
                NATIVE_LOG,
                NATIVE_MARKER.replace(
                    "other_drm_fd_count=0",
                    "other_drm_fd_count=1",
                ),
            )

    def test_ready_validator_requires_sole_unprivileged_drm_owner(self) -> None:
        value = packet.validate_debian_ready_marker(READY_MARKER)
        self.assertEqual(value["drm_master"], "1")
        self.assertEqual(value["presenter_uid"], "3904")
        for old, new in (
            ("presenter_cap_eff=0000000000000000", "presenter_cap_eff=1"),
            ("presenter_self_drm_fd_count=1", "presenter_self_drm_fd_count=2"),
            ("other_process_drm_fd_count=0", "other_process_drm_fd_count=1"),
            ("mode=1080x2400@60", "mode=0x2400@60"),
        ):
            with self.subTest(new=new):
                with self.assertRaises(packet.ContractError):
                    packet.validate_debian_ready_marker(
                        READY_MARKER.replace(old, new)
                    )

    def test_failure_validator_accepts_only_terminal_third_attempt(self) -> None:
        terminal = (
            "schema=a90-debian-display-v1-failure\n"
            "attempt=3\n"
            "rc=19\n"
        )
        value = packet.validate_bounded_failure_marker(
            terminal,
            ready_absent=True,
        )
        self.assertEqual(value["attempt"], "3")
        for text, ready_absent in (
            (terminal.replace("attempt=3", "attempt=2"), True),
            (terminal.replace("rc=19", "rc=0"), True),
            (terminal, False),
        ):
            with self.subTest(text=text, ready_absent=ready_absent):
                with self.assertRaises(packet.ContractError):
                    packet.validate_bounded_failure_marker(
                        text,
                        ready_absent=ready_absent,
                    )

    def test_packet_write_is_exclusive_private_and_fsynced(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            private_outputs = Path(temporary)
            destination = private_outputs / "packet-01"
            with mock.patch.object(packet, "PRIVATE_OUTPUTS", private_outputs):
                path = packet.write_packet(destination, {"schema": "test"})
                self.assertEqual(
                    json.loads(path.read_text(encoding="utf-8")),
                    {"schema": "test"},
                )
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)
                with self.assertRaises(packet.ContractError):
                    packet.write_packet(destination, {"schema": "test"})
                with self.assertRaises(packet.ContractError):
                    packet.write_packet(
                        private_outputs / "nested" / "packet-02",
                        {"schema": "test"},
                    )


if __name__ == "__main__":
    unittest.main()
