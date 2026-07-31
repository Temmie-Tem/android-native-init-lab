from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
REVAL_DIR = REPO_ROOT / "workspace" / "public" / "src" / "scripts" / "revalidation"
if str(REVAL_DIR) not in sys.path:
    sys.path.insert(0, str(REVAL_DIR))

import a90_observation_pipeline as pipeline  # noqa: E402


FIXTURE = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "a90_observation"
    / "v3406_display_no_proof_redacted.json"
)


BEGIN = b"A90P1 BEGIN seq=41 cmd=status argc=1 flags=0x0\r\n"
END = (
    b"A90P1 END seq=41 cmd=status rc=0 errno=0 duration_ms=7 "
    b"flags=0x0 status=ok\r\n"
)
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


class A90ObservationPipelineTests(unittest.TestCase):
    def test_line_codec_preserves_lf_crlf_and_offsets(self) -> None:
        decoded = pipeline.decode_lines(b"one\r\ntwo\n")
        self.assertEqual([line.text for line in decoded.lines], ["one", "two"])
        self.assertEqual(
            [line.ending.value for line in decoded.lines],
            ["CRLF", "LF"],
        )
        self.assertEqual(
            [
                (line.byte_start, line.content_end, line.byte_end)
                for line in decoded.lines
            ],
            [(0, 3, 5), (5, 8, 9)],
        )
        self.assertEqual(decoded.canonical_text(), "one\ntwo\n")

    def test_line_codec_rejects_bare_cr_nul_invalid_utf8_and_truncation(self) -> None:
        for value, message in (
            (b"bad\rline\n", "bare CR"),
            (b"bad\x00line\n", "NUL"),
            (b"bad\xff\n", "UTF-8"),
            (b"unterminated", "newline terminated"),
        ):
            with self.subTest(message=message):
                with self.assertRaisesRegex(
                    pipeline.ObservationContractError,
                    message,
                ):
                    pipeline.decode_lines(value)

    def test_strict_frame_accepts_exact_crlf_and_all_chunk_splits(self) -> None:
        raw = b"prefix\n" + BEGIN + b"body\r\n" + END + b"a90:/# "
        full = pipeline.parse_a90p1_transcript(
            raw,
            expected_command="status",
        )
        self.assertEqual(len(full.frames), 1)
        self.assertEqual(full.frames[0].begin["seq"], "41")
        self.assertEqual(full.frames[0].end["rc"], "0")
        self.assertEqual([line.text for line in full.outside], ["prefix", "a90:/# "])
        for split in range(len(raw) + 1):
            replay = pipeline.parse_a90p1_chunks(
                (raw[:split], raw[split:]),
                expected_command="status",
            )
            self.assertEqual(replay.frames, full.frames)

    def test_strict_frame_segments_multiple_transactions(self) -> None:
        second_begin = BEGIN.replace(b"seq=41", b"seq=42")
        second_end = END.replace(b"seq=41", b"seq=42")
        transcript = pipeline.parse_a90p1_transcript(
            BEGIN + END + second_begin + second_end,
            expected_command="status",
        )
        self.assertEqual(
            [frame.end["seq"] for frame in transcript.frames],
            ["41", "42"],
        )

    def test_one_way_exec_is_explicit_transition_without_weakening_nested_gate(
        self,
    ) -> None:
        switch_begin = (
            b"A90P1 BEGIN seq=14 cmd=switch-root-to-distro "
            b"argc=1 flags=0x0\r\n"
        )
        next_boot = BEGIN.replace(b"seq=41", b"seq=1") + END.replace(
            b"seq=41",
            b"seq=1",
        )
        raw = switch_begin + b"exec switch_root\r\n" + next_boot
        with self.assertRaisesRegex(
            pipeline.ObservationContractError,
            "nested BEGIN is ambiguous",
        ):
            pipeline.parse_a90p1_transcript(raw)

        transcript = pipeline.parse_a90p1_transcript(
            raw,
            one_way_commands=frozenset({"switch-root-to-distro"}),
        )
        self.assertEqual(len(transcript.transitions), 1)
        self.assertEqual(
            transcript.transitions[0].begin["cmd"],
            "switch-root-to-distro",
        )
        self.assertEqual(
            transcript.transitions[0].reason,
            pipeline.TransitionReason.ONE_WAY_EXEC_DISCONTINUITY,
        )
        self.assertEqual(transcript.transitions[0].byte_end, len(switch_begin) + 18)
        self.assertEqual([frame.end["seq"] for frame in transcript.frames], ["1"])

        terminal = pipeline.parse_a90p1_transcript(
            switch_begin + b"exec switch_root\r\n",
            require_frames=False,
            one_way_commands=frozenset({"switch-root-to-distro"}),
        )
        self.assertEqual(len(terminal.frames), 0)
        self.assertEqual(len(terminal.transitions), 1)
        with self.assertRaisesRegex(
            pipeline.ObservationContractError,
            "BEGIN is not newline terminated",
        ):
            pipeline.parse_a90p1_transcript(
                switch_begin.rstrip(b"\r\n"),
                require_frames=False,
                one_way_commands=frozenset({"switch-root-to-distro"}),
            )

    def test_canonical_nonzero_result_triplets(self) -> None:
        for rc, errno, status in (
            (127, 0, "error"),
            (-16, 16, "busy"),
            (-2, 2, "unknown"),
        ):
            with self.subTest(rc=rc, status=status):
                end = (
                    f"A90P1 END seq=41 cmd=status rc={rc} errno={errno} "
                    f"duration_ms=7 flags=0x0 status={status}\r\n"
                ).encode()
                transcript = pipeline.parse_a90p1_transcript(BEGIN + end)
                self.assertEqual(transcript.frames[0].end["status"], status)

        for replacement in (
            b"rc=22 errno=999 duration_ms=7 flags=0x0 status=error",
            b"rc=-5 errno=5 duration_ms=7 flags=0x0 status=forged",
            b"rc=-2 errno=2 duration_ms=7 flags=0x0 status=busy",
            b"rc=-16 errno=16 duration_ms=7 flags=0x0 status=unknown",
        ):
            with self.assertRaises(pipeline.ObservationContractError):
                pipeline.parse_a90p1_transcript(
                    BEGIN
                    + END.replace(
                        b"rc=0 errno=0 duration_ms=7 flags=0x0 status=ok",
                        replacement,
                    )
                )

    def test_exact_v1_forgery_remains_structural_only(self) -> None:
        forged = BEGIN + END + b"a90:/# "
        transcript = pipeline.parse_a90p1_transcript(
            forged,
            expected_command="status",
        )
        self.assertEqual(
            transcript.frames[0].trust,
            pipeline.FrameTrust.STRUCTURAL_ONLY,
        )

    def test_strict_frame_rejects_f016_and_field_mutations(self) -> None:
        cases = {
            "lacks BEGIN": END,
            "BEGIN/END seq mismatch": BEGIN + END.replace(b"seq=41", b"seq=42"),
            "fields must be unique": BEGIN + END.replace(b"rc=0", b"rc=7 rc=0"),
            "field set is not exact": BEGIN + END.replace(b"seq=41 ", b""),
            "field order is not exact": BEGIN
            + END.replace(
                b"seq=41 cmd=status",
                b"cmd=status seq=41",
            ),
            "malformed field": BEGIN + END.replace(b"cmd=status", b"junk cmd=status"),
            "BEGIN/END cmd mismatch": BEGIN
            + END.replace(b"cmd=status", b"cmd=wifi"),
            "coherence": BEGIN
            + END.replace(b"rc=0 errno=0", b"rc=22 errno=999"),
            "field value is not exact": BEGIN
            + END.replace(b"status=ok", b"status=forged"),
            "not newline terminated": BEGIN + END.rstrip(b"\r\n"),
        }
        for message, raw in cases.items():
            with self.subTest(message=message):
                with self.assertRaisesRegex(
                    pipeline.ObservationContractError,
                    message,
                ):
                    pipeline.parse_a90p1_transcript(
                        raw,
                        expected_command="status",
                    )

    def test_native_release_accepts_crlf_and_fact_states_are_independent(self) -> None:
        pipeline.validate_native_release_evidence(
            NATIVE_LOG_CRLF,
            NATIVE_MARKER,
        )
        facts = pipeline.classify_phase2_display_facts(
            handoff_log=NATIVE_LOG_CRLF,
            native_release_marker=NATIVE_MARKER,
            pid1_comm_init=True,
            proc1_exe_init=True,
            dropbear_started=True,
            display_status="bounded-failure",
        )
        self.assertEqual(facts["native_release"].state, pipeline.FactState.PROVEN)
        self.assertEqual(facts["debian_pid1"].state, pipeline.FactState.PROVEN)
        self.assertEqual(facts["dropbear"].state, pipeline.FactState.PROVEN)
        self.assertEqual(
            facts["display_acquisition"].state,
            pipeline.FactState.REFUTED,
        )

        damaged = pipeline.classify_phase2_display_facts(
            handoff_log=NATIVE_LOG_CRLF.replace("close_rc=0", "close_rc=-5"),
            native_release_marker=NATIVE_MARKER,
            pid1_comm_init=True,
            proc1_exe_init=True,
            dropbear_started=True,
            display_status="bounded-failure",
        )
        self.assertEqual(
            damaged["native_release"].state,
            pipeline.FactState.UNKNOWN,
        )
        self.assertEqual(
            damaged["debian_pid1"].state,
            pipeline.FactState.PROVEN,
        )
        self.assertEqual(
            damaged["display_acquisition"].state,
            pipeline.FactState.REFUTED,
        )

        unavailable = pipeline.classify_phase2_display_facts(
            handoff_log="",
            native_release_marker="",
            pid1_comm_init=None,
            proc1_exe_init=None,
            dropbear_started=None,
            display_status="unknown",
        )
        self.assertTrue(
            all(fact.state is pipeline.FactState.UNKNOWN for fact in unavailable.values())
        )

    def test_redacted_v3406_fixture_replays_exact_fact_boundary(self) -> None:
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        facts = pipeline.classify_phase2_display_run(
            handoff_log=fixture["native_release_log"],
            native_release_marker=fixture["native_release_marker"],
            pid1_comm_init=fixture["ssh_facts"]["pid1_comm_init"],
            proc1_exe_init=fixture["ssh_facts"]["proc1_exe_init"],
            dropbear_started=fixture["ssh_facts"]["dropbear_started"],
            display_status=fixture["ssh_facts"]["display_status"],
            candidate_return_present=fixture["candidate_return_present"],
        )
        self.assertEqual(
            {name: fact.state.value for name, fact in facts.items()},
            fixture["expected_facts"],
        )
        self.assertFalse(fixture["candidate_return_present"])
        self.assertEqual(fixture["expected_atomic_result"], "NO_PROOF")
        decision = pipeline.decide_phase2_display_run(facts)
        self.assertEqual(decision.decision, pipeline.AtomicDecision.NO_PROOF)
        self.assertEqual(
            decision.signature.to_dict(),
            fixture["expected_failure_signature"],
        )

    def test_atomic_decision_uses_first_nonproven_boundary(self) -> None:
        facts = pipeline.classify_phase2_display_run(
            handoff_log=NATIVE_LOG_CRLF,
            native_release_marker=NATIVE_MARKER,
            pid1_comm_init=True,
            proc1_exe_init=True,
            dropbear_started=True,
            display_status="ready",
            candidate_return_present=False,
        )
        decision = pipeline.decide_phase2_display_run(facts)
        self.assertEqual(
            decision.signature.to_dict(),
            {
                "workflow": "F1_V3406_DISPLAY",
                "phase": "RETURN_OBSERVATION",
                "failure_class": "BOUNDED_RETURN_REFUTED",
                "effect_started": True,
                "last_proven_boundary": "DISPLAY_ACQUISITION_PROVEN",
            },
        )


if __name__ == "__main__":
    unittest.main()
