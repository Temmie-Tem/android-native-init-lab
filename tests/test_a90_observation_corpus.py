from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
REVAL_DIR = REPO_ROOT / "workspace" / "public" / "src" / "scripts" / "revalidation"
if str(REVAL_DIR) not in sys.path:
    sys.path.insert(0, str(REVAL_DIR))

import a90_observation_corpus as corpus  # noqa: E402


NATIVE_LOG_CRLF = (
    "A90D3DISPLAY native_kms_release rc=0 fd_before=3 "
    "disable_plane_rc=0 disable_crtc_rc=0 "
    "munmap_failures=0 rmfb_failures=0 destroy_dumb_failures=0 "
    "drop_master_rc=0 close_rc=0 release_complete=1\r\n"
    "A90D3DISPLAY native_pid1_drm_fd_count=0 observed=0\r\n"
    "A90D3DISPLAY other_drm_fd_count=0 observed=0\r\n"
    "A90D3DISPLAY native_kms_initialized=0 observed=0\r\n"
    "A90D3DISPLAY display_services_restart_blocked=1 "
    "corridor=synchronous-handoff\r\n"
)
NATIVE_MARKER = (
    "schema=a90-native-display-release-v1\n"
    "native_pid1_drm_fd_count=0\n"
    "other_drm_fd_count=0\n"
    "native_kms_initialized=0\n"
    "display_services_restart_blocked=1\n"
    "release_complete=1\n"
)
FAILURE_MARKER = (
    "schema=a90-debian-display-v1-failure\n"
    "attempt=3\n"
    "rc=1\n"
)


class A90ObservationCorpusTests(unittest.TestCase):
    def test_raw_replay_accepts_only_explicit_one_way_discontinuity(self) -> None:
        raw = (
            b"A90P1 BEGIN seq=14 cmd=switch-root-to-distro "
            b"argc=1 flags=0x0\r\n"
            b"exec switch_root\r\n"
            b"A90P1 BEGIN seq=1 cmd=status argc=1 flags=0x0\r\n"
            b"A90P1 END seq=1 cmd=status rc=0 errno=0 duration_ms=1 "
            b"flags=0x0 status=ok\r\n"
        )
        self.assertEqual(
            corpus._replay_a90p1(raw),
            {
                "status": "PASS",
                "frames": 1,
                "transitions": 1,
                "error": None,
            },
        )
        nested = raw.replace(b"cmd=switch-root-to-distro ", b"cmd=status ", 1)
        replay = corpus._replay_a90p1(nested)
        self.assertEqual(replay["status"], "REJECT")
        self.assertIn("nested BEGIN is ambiguous", replay["error"])

    def test_redacted_extractor_emits_allowlist_only(self) -> None:
        private_token = "DO_NOT_LEAK_TARGET_OR_ADDRESS"
        source_value = {
            "target_serial": private_token,
            "handoff": {"text": "prefix\r\n" + NATIVE_LOG_CRLF},
            "ssh": {
                "native_release_marker_text": NATIVE_MARKER,
                "display_marker_text": FAILURE_MARKER,
                "pid1_comm_init": True,
                "proc1_exe_init": True,
                "dropbear_started": True,
                "display_status": "bounded-failure",
                "private_address": private_token,
            },
        }
        with tempfile.TemporaryDirectory(
            prefix="a90-observation-corpus-test-",
            dir=corpus.PRIVATE_RUNS,
        ) as temporary:
            source = Path(temporary) / "observation.json"
            source.write_text(
                json.dumps(source_value, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            fixture = corpus.extract_v3406_redacted_fixture(source)

        self.assertEqual(
            set(fixture),
            {
                "schema",
                "redaction",
                "source",
                "native_release_log",
                "native_release_marker",
                "ssh_facts",
                "candidate_return_present",
                "expected_facts",
                "expected_atomic_result",
            },
        )
        self.assertNotIn(private_token, json.dumps(fixture, sort_keys=True))
        self.assertEqual(fixture["expected_atomic_result"], "NO_PROOF")
        self.assertEqual(
            fixture["expected_facts"],
            {
                "debian_pid1": "PROVEN",
                "display_acquisition": "REFUTED",
                "dropbear": "PROVEN",
                "native_release": "PROVEN",
            },
        )

    def test_public_output_cannot_escape_fixture_root(self) -> None:
        outside = REPO_ROOT / "tests" / "outside-redacted-fixture.json"
        with self.assertRaisesRegex(corpus.CorpusError, "escapes"):
            corpus._output_path(outside, private=False)

    def test_private_source_symlink_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="a90-observation-corpus-symlink-",
            dir=corpus.PRIVATE_RUNS,
        ) as temporary:
            root = Path(temporary)
            target = root / "target.json"
            target.write_text("{}\n", encoding="utf-8")
            link = root / "link.json"
            link.symlink_to(target)
            with self.assertRaisesRegex(corpus.CorpusError, "non-symlink"):
                corpus.require_private_source(link)


if __name__ == "__main__":
    unittest.main()
