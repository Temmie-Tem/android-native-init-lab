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
                "decision": "ACCEPT_TRANSACTIONS",
                "frames": 1,
                "transitions": 1,
                "error": None,
                "failure_signature": None,
            },
        )
        nested = raw.replace(b"cmd=switch-root-to-distro ", b"cmd=status ", 1)
        replay = corpus._replay_a90p1(nested)
        self.assertEqual(replay["status"], "REJECT")
        self.assertIn("nested BEGIN is ambiguous", replay["error"])
        self.assertEqual(replay["decision"], "REJECT_TRANSCRIPT")
        self.assertEqual(
            replay["failure_signature"]["failure_class"],
            "FRAME_CONTRACT_REJECT",
        )

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
                "historical_atomic_result",
                "expected_failure_signature",
                "corrections",
            },
        )
        self.assertNotIn(private_token, json.dumps(fixture, sort_keys=True))
        self.assertEqual(fixture["expected_atomic_result"], "NO_PROOF")
        self.assertEqual(
            fixture["expected_facts"],
            {
                "bounded_return": "REFUTED",
                "debian_pid1": "PROVEN",
                "display_acquisition": "REFUTED",
                "dropbear": "PROVEN",
                "native_release": "PROVEN",
            },
        )
        replay = corpus.replay_redacted_fixture(fixture)
        self.assertEqual(replay["status"], "PASS")
        self.assertEqual(
            replay["actual"]["failure_signature"]["phase"],
            "DISPLAY_ACQUISITION",
        )

    def test_replay_fails_on_expected_signature_drift(self) -> None:
        fixture = json.loads(
            (corpus.PUBLIC_FIXTURES / "v3406_display_no_proof_redacted.json")
            .read_text(encoding="utf-8")
        )
        fixture["expected_failure_signature"]["last_proven_boundary"] = "FORGED"
        with self.assertRaisesRegex(corpus.CorpusError, "signature changed"):
            corpus.replay_redacted_fixture(fixture)

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

    def test_v3_migration_and_replay_compare_decision_signature(self) -> None:
        raw = (
            b"A90P1 BEGIN seq=1 cmd=status argc=1 flags=0x0\r\n"
            b"A90P1 END seq=1 cmd=status rc=0 errno=0 duration_ms=1 "
            b"flags=0x0 status=ok\r\n"
        )
        with tempfile.TemporaryDirectory(
            prefix="a90-observation-labeled-",
            dir=corpus.PRIVATE_RUNS,
        ) as temporary:
            root = Path(temporary)
            source = root / "known.raw.log"
            source.write_bytes(raw)
            legacy = {
                "schema": "a90-private-observation-corpus-v3",
                "entries": [
                    {
                        "path": str(source.relative_to(corpus.PRIVATE_RUNS)),
                        "sha256": corpus.sha256_bytes(raw),
                        "a90p1_replay": {
                            "status": "PASS",
                            "frames": 1,
                            "transitions": 0,
                            "error": None,
                        },
                    }
                ],
            }
            expectations = corpus.migrate_v3_expectations(legacy)
            result = corpus.verify_private_replay_expectations(
                expectations,
                root=root,
            )
            self.assertTrue(result["decision_and_signature_match"])
            expectations["entries"][0]["expected_decision"] = "REJECT_TRANSCRIPT"
            with self.assertRaisesRegex(corpus.CorpusError, "decision changed"):
                corpus.verify_private_replay_expectations(
                    expectations,
                    root=root,
                )

            expectations["entries"][0].update(
                {
                    "expected_decision": "UNAVAILABLE_SOURCE_MUTATED",
                    "expected_failure_signature": {
                        "workflow": "A90P1_REPLAY",
                        "phase": "IMMUTABLE_CAPTURE",
                        "failure_class": "SOURCE_BYTES_CHANGED",
                        "effect_started": False,
                        "last_proven_boundary": "CATALOG_V3_METADATA",
                    },
                }
            )
            source.write_bytes(raw + raw)
            unavailable = corpus.verify_private_replay_expectations(
                expectations,
                root=root,
            )
            self.assertEqual(unavailable["exact_replays"], 0)
            self.assertEqual(unavailable["unavailable_source_mutated"], 1)


if __name__ == "__main__":
    unittest.main()
