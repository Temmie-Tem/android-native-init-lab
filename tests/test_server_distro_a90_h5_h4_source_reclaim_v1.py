"""Host-only tests for one-shot H4 source reclaim from healthy H5."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import load_script


reclaim = load_script(
    "workspace/public/src/scripts/server-distro/a90_h5_h4_source_reclaim_v1.py"
)


class H5H4SourceReclaimTests(unittest.TestCase):
    def image(self, *, selected: bool) -> object:
        fixed = reclaim.SELECTED_FIXED if selected else reclaim.PROTECTED_FIXED
        return reclaim.gc.ImageRecord(
            role=fixed.role,
            device_path=fixed.device_path,
            size=reclaim.gc.IMAGE_SIZE,
            blocks=4194312,
            mode=reclaim.gc.IMAGE_MODE,
            nlink=1,
            st_dev=45825,
            st_ino=1054074 if selected else 1054075,
            sha256=fixed.sha256,
            host_preservation=(
                reclaim.legacy.BoundFile(
                    path=Path("/private/h4.img"),
                    size=reclaim.gc.IMAGE_SIZE,
                    sha256=reclaim.SELECTED_SHA256,
                )
                if selected
                else None
            ),
        )

    def spec(self, base: Path) -> object:
        run_id = "a90-h5-h4-source-reclaim-20260806-01"
        (base / run_id).mkdir(parents=True)
        return reclaim.Spec(
            manifest_path=base / run_id / "manifest.json",
            manifest_sha256="1" * 64,
            run_id=run_id,
            inventory=reclaim.legacy.BoundFile(
                base / run_id / "inventory.json", 1, "2" * 64
            ),
            bridge_realpath="/dev/ttyACM1",
            bridge_process={"generation": 1},
            selected=(self.image(selected=True),),
            protected=(self.image(selected=False),),
            source_closure={},
            evidence={},
            rollback=reclaim.legacy.BoundFile(
                Path("/private/rollback.img"),
                reclaim.ROLLBACK_SIZE,
                reclaim.ROLLBACK_SHA256,
            ),
            capability_dispatch_path=(
                base / reclaim.CAPABILITY_STATE_DIR / "dispatch-started.json"
            ),
            capability_expires_utc=reclaim.CAPABILITY_EXPIRES_UTC,
        )

    def test_fixed_scope_selects_h4_and_protects_h5(self) -> None:
        self.assertEqual(reclaim.SELECTED_RUN_ID[-2:], "11")
        self.assertEqual(reclaim.PROTECTED_RUN_ID[-2:], "12")
        self.assertNotEqual(reclaim.SELECTED_PATH, reclaim.PROTECTED_PATH)
        self.assertNotEqual(reclaim.SELECTED_SHA256, reclaim.PROTECTED_SHA256)
        self.assertEqual(reclaim.engine.PASS_OUTCOME, reclaim.PASS_OUTCOME)
        self.assertEqual(reclaim.engine.RESULT_SCHEMA, reclaim.RESULT_SCHEMA)

    def test_isolated_engine_preserves_original_h3_defaults(self) -> None:
        original = load_script(
            "workspace/public/src/scripts/server-distro/"
            "a90_v2321_h3_source_reclaim_v1.py"
        )
        self.assertEqual(original.PASS_OUTCOME, "PASS_H3_SOURCE_RECLAIMED")
        self.assertEqual(
            original.SELECTED_RUN_ID,
            "a90-v3406-debian-display-f1-20260805-10",
        )

    def test_cleanup_selector_round_trips_only_h4(self) -> None:
        selected = self.image(selected=True)
        protected = self.image(selected=False)
        selector = reclaim.gc._cleanup_selector(selected)
        self.assertEqual(
            reclaim.gc._cleanup_selector_path(selector), reclaim.SELECTED_PATH
        )
        command = reclaim.gc._cleanup_command(
            mock.Mock(selected=(selected,), protected=(protected,))
        )
        self.assertLessEqual(
            reclaim.gc._command_wire_bytes(command),
            reclaim.gc.MAX_CMDV1X_WIRE_BYTES,
        )
        self.assertNotIn(reclaim.PROTECTED_PATH, command[-1])

    def test_health_requires_exact_h5_and_latched_auto_state(self) -> None:
        spec = mock.Mock()
        args = mock.Mock()
        status_record = {"command": ["auto-handoff-status"]}
        status = {
            "binding": 1,
            "enable": 1,
            "latch": 1,
            "build": reclaim.EXPECTED_BUILD,
        }
        with (
            mock.patch.object(reclaim.resident, "load_spec", return_value=spec),
            mock.patch.object(reclaim.auto, "_effect_args", return_value=args),
            mock.patch.object(reclaim.auto, "_f1_spec", return_value="f1"),
            mock.patch.object(
                reclaim.resident,
                "verify_resident_health_exact",
                return_value={"exact_bridge": True},
            ) as health,
            mock.patch.object(
                reclaim.auto,
                "require_auto_status",
                return_value=(status_record, status),
            ) as auto_status,
        ):
            value = reclaim._health()
        health.assert_called_once_with(spec, "f1", args)
        auto_status.assert_called_once_with(args, enable=1, latch=1)
        self.assertTrue(value["proven"])
        self.assertEqual(value["version"], reclaim.EXPECTED_VERSION)
        self.assertEqual(value["auto_handoff_status"], status)

    def inventory_health(self) -> dict:
        status = {
            "binding": 1,
            "enable": 1,
            "latch": 1,
            "build": reclaim.EXPECTED_BUILD,
        }
        return {
            "version": reclaim.EXPECTED_VERSION,
            "build": reclaim.EXPECTED_BUILD,
            "proven": True,
            "resident_health": {
                "exact_bridge": True,
                "selected_realpath": "/dev/ttyACM1",
                "version": {"command": ["version"]},
                "status": {"command": ["status"]},
                "selftest": {"command": ["selftest"]},
                "facts": {"fail": 0, "pstore_entries": 0},
            },
            "auto_handoff_status_record": {
                "command": ["auto-handoff-status"]
            },
            "auto_handoff_status": status,
        }

    def test_inventory_health_rejects_missing_or_drifted_auto_state(self) -> None:
        value = self.inventory_health()
        required = value["auto_handoff_status"]
        with (
            mock.patch.object(
                reclaim.engine,
                "_default_validate_inventory_health",
                return_value=value,
            ),
            mock.patch.object(
                reclaim.resident.staging,
                "validate_native_health_receipts",
                return_value=value["resident_health"]["facts"],
            ),
            mock.patch.object(
                reclaim.auto.base,
                "require_exact_f1_command_receipt",
                return_value=value["auto_handoff_status_record"],
            ),
            mock.patch.object(
                reclaim.auto, "parse_auto_status", return_value=required
            ),
        ):
            self.assertIs(reclaim._validate_inventory_health(value), value)
            missing = dict(value)
            missing.pop("auto_handoff_status")
            with self.assertRaises(reclaim.ContractError):
                reclaim._validate_inventory_health(missing)
            drifted = dict(value)
            drifted["auto_handoff_status"] = dict(required, latch=0)
            with self.assertRaisesRegex(reclaim.ContractError, "auto-handoff"):
                reclaim._validate_inventory_health(drifted)

    def test_inventory_health_rejects_receipt_fact_or_bridge_drift(self) -> None:
        value = self.inventory_health()
        with (
            mock.patch.object(
                reclaim.engine,
                "_default_validate_inventory_health",
                return_value=value,
            ),
            mock.patch.object(
                reclaim.resident.staging,
                "validate_native_health_receipts",
                return_value={"fail": 1, "pstore_entries": 0},
            ),
            mock.patch.object(
                reclaim.auto.base,
                "require_exact_f1_command_receipt",
                return_value=value["auto_handoff_status_record"],
            ),
            mock.patch.object(
                reclaim.auto,
                "parse_auto_status",
                return_value=value["auto_handoff_status"],
            ),
            self.assertRaisesRegex(reclaim.ContractError, "facts"),
        ):
            reclaim._validate_inventory_health(value)
        with self.assertRaisesRegex(reclaim.ContractError, "bridge"):
            reclaim._validate_inventory_target_health(
                value,
                {"bridge_realpath": "/dev/ttyACM0"},
            )

    def test_inventory_filesystem_capacity_is_exact_and_bounded(self) -> None:
        valid = {"blocks": 100, "used": 80, "available": 15}
        self.assertEqual(
            reclaim.engine._validate_inventory_filesystem(valid), valid
        )
        for invalid in (
            {"blocks": 100, "used": 80},
            {"blocks": 100, "used": -1, "available": 15},
            {"blocks": 100, "used": 80, "available": 30},
            {"blocks": True, "used": 0, "available": 0},
        ):
            with self.subTest(invalid=invalid), self.assertRaises(
                reclaim.ContractError
            ):
                reclaim.engine._validate_inventory_filesystem(invalid)

    def _execute(self, base: Path, dispatch: object) -> tuple[dict, mock.Mock]:
        spec = self.spec(base)
        run = mock.Mock()
        if isinstance(dispatch, BaseException):
            run.side_effect = dispatch
        else:
            run.return_value = dispatch
        reconciliation = {
            "selected": ["absent"],
            "protected": "exact",
            "work": "absent",
            "filesystem_kib": {
                "blocks": 61408048,
                "used": 52322400,
                "available": 5961000,
            },
        }
        with (
            mock.patch.object(reclaim.engine, "PRIVATE_BASE", base),
            mock.patch.object(reclaim.engine, "_inventory_age"),
            mock.patch.object(reclaim.engine, "_revalidate_host"),
            mock.patch.object(
                reclaim.engine,
                "_live_target",
                return_value=("/dev/ttyACM1", {"generation": 1}),
            ),
            mock.patch.object(
                reclaim.engine,
                "_health",
                side_effect=(
                    {"proven": True},
                    {"proven": True},
                    {"proven": True},
                ),
            ),
            mock.patch.object(
                reclaim.gc,
                "_read_cleanup_preflight",
                return_value={
                    "blocks": 61408048,
                    "used": 54419528,
                    "available": 3862508,
                },
            ),
            mock.patch.object(
                reclaim.gc, "_cleanup_command", return_value=["run", "fixed"]
            ),
            mock.patch.object(reclaim.gc, "_cleanup_script", return_value="fixed"),
            mock.patch.object(
                reclaim.gc,
                "_cleanup_args",
                return_value=("45825", "6:20260805-11:1054074"),
            ),
            mock.patch.object(reclaim.gc, "_run_script", run),
            mock.patch.object(
                reclaim.gc, "_free_gain_bounds", return_value=(2030000, 2160000)
            ),
            mock.patch.object(
                reclaim.gc, "_read_reconciliation", return_value=reconciliation
            ),
        ):
            result = reclaim.execute(
                spec,
                base / spec.run_id / "live",
                operator_attended=True,
            )
        return result, run

    def test_exact_response_dispatches_once_and_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result, run = self._execute(
                Path(tmp), "A90CLEAN_UNLINKED exact=1 selected_absent=1"
            )
        self.assertEqual(result["outcome"], reclaim.PASS_OUTCOME)
        self.assertEqual(result["dispatch_count"], 1)
        self.assertFalse(result["cleanup_retransmitted"])
        self.assertTrue(result["device_write"])
        run.assert_called_once()

    def test_ambiguous_response_reconciles_without_retransmit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result, run = self._execute(Path(tmp), TimeoutError("lost response"))
        self.assertEqual(result["outcome"], reclaim.PASS_AMBIGUOUS_OUTCOME)
        self.assertEqual(result["dispatch_count"], 1)
        self.assertFalse(result["cleanup_retransmitted"])
        run.assert_called_once()

    def test_attendance_stops_before_live_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            spec = self.spec(base)
            with (
                mock.patch.object(reclaim.engine, "_live_target") as target,
                self.assertRaisesRegex(reclaim.ContractError, "attended-only"),
            ):
                reclaim.execute(spec, base / spec.run_id / "live", False)
        target.assert_not_called()

    def test_source_closure_binds_adapter_and_engine(self) -> None:
        paths = reclaim._source_paths()
        self.assertEqual(paths["runner"], reclaim.RUNNER)
        self.assertEqual(
            paths["one_shot_reclaim_engine"], reclaim.ENGINE_PATH.resolve()
        )
        self.assertEqual(paths["h5_resident_health"], Path(reclaim.resident.__file__))


if __name__ == "__main__":
    unittest.main()
