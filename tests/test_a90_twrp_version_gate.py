"""Host-only tests for the exact A90 TWRP System-return version gate."""

from __future__ import annotations

import unittest

from _loader import load_revalidation


flash = load_revalidation("native_init_flash")


class A90TwrpVersionGateTests(unittest.TestCase):
    EXPECTED_BANNER = (
        "TWRP openrecoveryscript command line tool, TWRP version 3.7.0_12-0"
    )

    def _command_for_output(self, output: str) -> str:
        """Model the one-terminal-newline output bound by shell substitution."""
        if (
            not output.endswith("\n")
            or output.endswith("\n\n")
            or output[:-1] != self.EXPECTED_BANNER
        ):
            return ""
        return flash.TWRP_SYSTEM_REBOOT_COMMAND.replace(
            f"'{flash.TWRP_SYSTEM_VERSION_BANNER}'",
            f"'{output[:-1]}'",
            1,
        )

    def test_exact_full_banner_with_one_terminal_newline_is_accepted(self) -> None:
        raw = self.EXPECTED_BANNER + "\n"
        command = self._command_for_output(raw)
        expected_prefix = (
            f"test \"$(twrp --version)\" = '{self.EXPECTED_BANNER}' && "
        )
        self.assertEqual(flash.TWRP_SYSTEM_VERSION_BANNER, self.EXPECTED_BANNER)
        self.assertTrue(command.startswith(expected_prefix))
        self.assertIn("test ! -L /system/bin/rebootsystem.sh &&", command)
        self.assertIn("exec twrp reboot", command)

    def test_bare_wrong_prefix_suffix_and_multiline_outputs_are_rejected(self) -> None:
        rejected = (
            "3.7.0_12-0\n",
            "3.7.0_11-0\n",
            "prefix " + self.EXPECTED_BANNER + "\n",
            self.EXPECTED_BANNER + " suffix\n",
            self.EXPECTED_BANNER + "\nextra\n",
            self.EXPECTED_BANNER + "\n\n",
            self.EXPECTED_BANNER,
        )
        for raw in rejected:
            with self.subTest(raw=raw):
                self.assertEqual(self._command_for_output(raw), "")

    def test_gate_is_full_literal_not_substring_or_regex(self) -> None:
        command = flash.TWRP_SYSTEM_REBOOT_COMMAND
        self.assertIn(
            f"test \"$(twrp --version)\" = '{self.EXPECTED_BANNER}' && ",
            command,
        )
        self.assertNotIn("grep", command)
        self.assertNotIn("regex", command.lower())
        self.assertNotIn("case ", command)


if __name__ == "__main__":
    unittest.main()
