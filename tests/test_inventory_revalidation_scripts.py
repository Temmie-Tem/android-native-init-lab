from __future__ import annotations

import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import load_script


inventory_mod = load_script("workspace/public/src/scripts/revalidation/inventory_revalidation_scripts.py")


class InventoryRevalidationScriptsTests(unittest.TestCase):
    def test_classify_known_active_module_utility_and_delete_review_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            active = root / "a90ctl.py"
            module = root / "_workspace_bootstrap.py"
            cleanup = root / "cleanup_tmp_artifacts.py"
            todo = root / "scratch.py"
            pattern = root / "native_kernel_probe.py"
            scripted = root / "manual_live.py"
            non_file = root / "scratch_dir"
            for path in (active, module, cleanup, todo, pattern, scripted):
                path.write_text("", encoding="utf-8")
            todo.write_text("# TODO remove me\n", encoding="utf-8")
            scripted.write_text("python3 native_init_flash.py\n", encoding="utf-8")
            non_file.mkdir()

            self.assertEqual(inventory_mod.classify(active, ""), ("active", "cmdv1 operator/client entrypoint"))
            self.assertEqual(inventory_mod.classify(module, "")[0], "module")
            self.assertEqual(inventory_mod.classify(cleanup, "")[0], "active")
            self.assertEqual(inventory_mod.classify(todo, todo.read_text())[0], "delete-review")
            self.assertEqual(inventory_mod.classify(pattern, "")[0], "active")
            self.assertEqual(inventory_mod.classify(scripted, scripted.read_text())[0], "active")
            self.assertEqual(inventory_mod.classify(non_file, ""), ("delete-review", "non-file entry in script root"))

    def test_requires_live_device_honors_host_only_and_live_tokens(self) -> None:
        self.assertFalse(inventory_mod.requires_live_device(Path("a90_kernel_v999_host.py"), "a90ctl.py"))
        self.assertFalse(inventory_mod.requires_live_device(Path("build_native_init_boot_v999.py"), "reboot"))
        self.assertFalse(inventory_mod.requires_live_device(Path("inventory_revalidation_scripts.py"), "a90ctl.py"))
        self.assertTrue(inventory_mod.requires_live_device(Path("a90ctl.py"), ""))
        self.assertTrue(inventory_mod.requires_live_device(Path("native_wifi_probe.py"), "run_cmdv1_command"))
        self.assertTrue(inventory_mod.requires_live_device(Path("observer.py"), "FastTransferSession"))

    def test_imports_module_matches_import_and_from_forms_only(self) -> None:
        text = "import a90_transport\nfrom a90_transport import phase\n# import json\n"
        self.assertTrue(inventory_mod.imports_module(text, "a90_transport"))
        self.assertFalse(inventory_mod.imports_module("x = 'import a90_transport'\n", "a90_transport"))
        self.assertFalse(inventory_mod.imports_module(text, "a90ctl"))

    def test_direct_a90ctl_candidate_groups_sort_and_preserve_actionability(self) -> None:
        groups = inventory_mod.direct_a90ctl_candidate_groups([
            "native_kernel_timer_start_context_v2200.py",
            "native_wifi_detail_surface_handoff_v2255.py",
            "unknown_runner.py",
        ])

        self.assertEqual([group["group"] for group in groups], [
            "current_baseline_wifi_surface",
            "legacy_bpf_anchor_runners",
            "ungrouped_direct_a90ctl_reference",
        ])
        self.assertTrue(groups[0]["actionable_now"])
        self.assertEqual(groups[0]["names"], ["native_wifi_detail_surface_handoff_v2255.py"])
        self.assertFalse(groups[1]["actionable_now"])

    def test_consolidation_signals_counts_actionable_review_exempt_and_secret_rows(self) -> None:
        entries = [
            self._entry(
                "native_wifi_detail_surface_handoff_v2255.py",
                mentions_a90ctl_subprocess=True,
                live_device_required=True,
            ),
            self._entry(
                "native_kernel_timer_start_context_v2200.py",
                mentions_a90ctl_subprocess=True,
                live_device_required=True,
                has_phase_timer=True,
                has_residual_state=True,
            ),
            self._entry("ncm_host_setup.py", live_device_required=True),
            self._entry("secret_probe.py", has_secret_redaction=True),
            self._entry("old.py", label="delete-review"),
            self._entry("a90ctl.py", mentions_a90ctl_subprocess=True, live_device_required=True),
        ]

        signals = inventory_mod.consolidation_signals(entries)

        self.assertEqual(signals["direct_a90ctl_reference_count"], 2)
        self.assertEqual(signals["direct_a90ctl_actionable_now_names"], ["native_wifi_detail_surface_handoff_v2255.py"])
        self.assertEqual(signals["direct_a90ctl_review_only_names"], ["native_kernel_timer_start_context_v2200.py"])
        self.assertEqual(signals["live_without_phase_timer_names"], ["native_wifi_detail_surface_handoff_v2255.py"])
        self.assertEqual(signals["live_phase_timer_exempt_names"], ["ncm_host_setup.py"])
        self.assertEqual(signals["live_without_residual_state_names"], ["native_wifi_detail_surface_handoff_v2255.py"])
        self.assertEqual(signals["live_residual_state_exempt_names"], ["ncm_host_setup.py"])
        self.assertEqual(signals["secret_handling_names"], ["secret_probe.py"])
        self.assertEqual(signals["source_delete_review_names"], ["old.py"])
        self.assertFalse(signals["active_live_phase_residual_backlog_closed"])

    def test_inventory_builds_entries_summary_flags_and_skips_generated_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script_root = root / "scripts"
            script_root.mkdir()
            (script_root / "__pycache__").mkdir()
            (script_root / "ignored.pyc").write_bytes(b"cache")
            self._write(script_root / "a90ctl.py", "", executable=True)
            self._write(script_root / "_workspace_bootstrap.py", "")
            self._write(script_root / "native_kernel_probe.py", "phase_timer residual_state redact")
            self._write(script_root / "legacy.py", "# deprecated\n")
            self._write(script_root / "direct.py", "import a90_transport\npython3 a90ctl.py\n")

            with mock.patch.object(inventory_mod, "REPO_ROOT", root), \
                    mock.patch.object(inventory_mod, "repo_reference_count", side_effect=lambda name: len(name)):
                data = inventory_mod.inventory(script_root)

        names = [entry["name"] for entry in data["entries"]]
        by_name = {entry["name"]: entry for entry in data["entries"]}
        self.assertEqual(names, ["_workspace_bootstrap.py", "a90ctl.py", "direct.py", "legacy.py", "native_kernel_probe.py"])
        self.assertEqual(data["summary"], {"module": 1, "active": 3, "delete-review": 1})
        self.assertTrue(by_name["a90ctl.py"]["executable"])
        self.assertTrue(by_name["direct.py"]["imports_a90_transport"])
        self.assertTrue(by_name["direct.py"]["mentions_a90ctl_subprocess"])
        self.assertEqual(by_name["direct.py"]["label"], "active")
        self.assertTrue(by_name["native_kernel_probe.py"]["has_phase_timer"])
        self.assertTrue(by_name["native_kernel_probe.py"]["has_residual_state"])
        self.assertTrue(by_name["native_kernel_probe.py"]["has_secret_redaction"])
        self.assertEqual(by_name["legacy.py"]["label"], "delete-review")
        self.assertEqual(by_name["a90ctl.py"]["repo_reference_count"], len("a90ctl.py"))

    def test_render_markdown_includes_summary_table_entries_and_consolidation_signals(self) -> None:
        entries = [
            self._entry(
                "native_wifi_detail_surface_handoff_v2255.py",
                label="active",
                reason="current V2254 baseline live-surface validator",
                mentions_a90ctl_subprocess=True,
                live_device_required=True,
            ),
            self._entry("old.py", label="delete-review", reason="requires manual review before keeping"),
        ]
        data = {
            "generated_at": "2026-06-13T00:00:00+00:00",
            "root": "workspace/public/src/scripts/revalidation",
            "summary": {"active": 1, "delete-review": 1},
            "entries": entries,
            "consolidation_signals": inventory_mod.consolidation_signals(entries),
        }

        rendered = inventory_mod.render_markdown(data)

        self.assertIn("# Revalidation Script Inventory", rendered)
        self.assertIn("| `active` | 1 |", rendered)
        self.assertIn("| `delete-review` | 1 |", rendered)
        self.assertIn("`native_wifi_detail_surface_handoff_v2255.py`", rendered)
        self.assertIn("Direct `a90ctl.py` actionable-now count: `1`", rendered)
        self.assertIn("No current source-root archive candidates remain", rendered)

    @staticmethod
    def _entry(
        name: str,
        *,
        label: str = "active",
        reason: str = "test reason",
        mentions_a90ctl_subprocess: bool = False,
        live_device_required: bool = False,
        has_phase_timer: bool = False,
        has_residual_state: bool = False,
        has_secret_redaction: bool = False,
    ) -> dict[str, object]:
        return {
            "path": f"workspace/public/src/scripts/revalidation/{name}",
            "name": name,
            "type": "file",
            "label": label,
            "reason": reason,
            "executable": False,
            "imports_a90_transport": False,
            "mentions_a90_bridge": False,
            "mentions_serial_tcp_bridge": False,
            "mentions_a90ctl_subprocess": mentions_a90ctl_subprocess,
            "has_phase_timer": has_phase_timer,
            "has_residual_state": has_residual_state,
            "has_secret_redaction": has_secret_redaction,
            "live_device_required": live_device_required,
            "repo_reference_count": 0,
        }

    @staticmethod
    def _write(path: Path, text: str, *, executable: bool = False) -> None:
        path.write_text(text, encoding="utf-8")
        if executable:
            path.chmod(path.stat().st_mode | stat.S_IXUSR)


if __name__ == "__main__":
    unittest.main()
