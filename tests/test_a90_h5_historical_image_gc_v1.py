"""Host-only tests for the fixed H5 historical-image cleanup capability."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "workspace/public/src/scripts/server-distro/"
    "a90_h5_historical_image_gc_v1.py"
)
SPEC = importlib.util.spec_from_file_location("a90_h5_historical_image_gc_v1_test", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
gc = importlib.util.module_from_spec(SPEC)
import sys

sys.modules[SPEC.name] = gc
SPEC.loader.exec_module(gc)


class HistoricalImageGcTests(unittest.TestCase):
    def records(self):
        return tuple(
            gc.ArtifactRecord(
                item.token,
                item.path,
                item.size,
                item.size // 512,
                item.mode,
                1,
                45825,
                1000 + index,
                f"{index + 1:064x}",
            )
            for index, item in enumerate(gc.SELECTED_FIXED)
        )

    def test_selection_is_closed_and_protects_current_h5(self):
        self.assertEqual(len(gc.SELECTED_FIXED), 20)
        self.assertEqual(len({item.token for item in gc.SELECTED_FIXED}), 20)
        self.assertEqual(len({item.path for item in gc.SELECTED_FIXED}), 20)
        self.assertNotIn(gc.PROTECTED_PATH, {item.path for item in gc.SELECTED_FIXED})
        self.assertEqual(
            sum(item.size for item in gc.SELECTED_FIXED),
            38 * 1024**3 + 512 * 1024**2,
        )
        self.assertEqual(
            [item.size for item in gc.SELECTED_FIXED].count(gc.GIB15),
            3,
        )
        self.assertEqual(len(gc.STAGED_HOST_RUNS), 12)
        self.assertEqual(len(gc.MISSING_HOST_TOKENS), 8)
        self.assertEqual(
            set(gc.STAGED_HOST_RUNS) | set(gc.MISSING_HOST_TOKENS),
            {item.token for item in gc.SELECTED_FIXED},
        )

    def test_every_selector_round_trips_to_one_fixed_path(self):
        for item in gc.SELECTED_FIXED:
            self.assertEqual(gc._selector_path(item.token), item.path)
        with self.assertRaises(gc.ContractError):
            gc._selector_path("21")

    def test_health_is_cross_bound_to_exact_bridge_realpath(self):
        spec = SimpleNamespace(bridge_realpath="/dev/ttyACM1")
        matching = {
            "proven": True,
            "resident_health": {"selected_realpath": "/dev/ttyACM1"},
        }
        drifted = {
            "proven": True,
            "resident_health": {"selected_realpath": "/dev/ttyACM0"},
        }
        with mock.patch.object(
            gc.h5, "_validate_inventory_health", side_effect=lambda value: value
        ):
            self.assertIs(gc._validate_health_for_target(matching, spec), matching)
            with self.assertRaises(gc.ContractError):
                gc._validate_health_for_target(drifted, spec)

    def test_single_effect_frame_is_bounded_and_nonrecursive(self):
        spec = SimpleNamespace(selected=self.records())
        command = gc.effect_command(spec)
        script = gc._effect_script()
        self.assertLessEqual(gc.gc._command_wire_bytes(command), 3800)
        self.assertEqual(script.count('/bin/busybox rm -- "$@"'), 1)
        self.assertNotIn("rm -r", script)
        self.assertNotIn("dd ", script)
        self.assertNotIn("flash", script)
        self.assertNotIn(gc.PROTECTED_PATH, script)

    def test_execution_records_one_dispatch_and_never_retransmits_on_error(self):
        with tempfile.TemporaryDirectory() as temporary:
            private_base = Path(temporary)
            run_id = "a90-h5-historical-image-gc-20260806-01"
            selected = self.records()
            protected = gc.ArtifactRecord(
                "P",
                gc.PROTECTED_PATH,
                gc.PROTECTED_SIZE,
                gc.PROTECTED_SIZE // 512,
                gc.PROTECTED_MODE,
                1,
                45825,
                9999,
                gc.PROTECTED_SHA256,
            )
            spec = SimpleNamespace(
                run_id=run_id,
                manifest_sha256="a" * 64,
                bridge_realpath="/dev/ttyACM1",
                bridge_process={"pid": 1},
                selected=selected,
                protected=protected,
                rollback=SimpleNamespace(sha256="b" * 64),
                capability_dispatch_path=(
                    private_base
                    / gc.CAPABILITY_STATE_DIR
                    / "dispatch-started.json"
                ),
            )
            transaction = private_base / run_id / "live"
            transaction.parent.mkdir(mode=0o700)
            remote = mock.Mock(side_effect=RuntimeError("ambiguous response"))
            order = []
            with (
                mock.patch.object(gc, "PRIVATE_BASE", private_base),
                mock.patch.object(gc, "PRIVATE_ROOT", private_base),
                mock.patch.object(gc, "_require_not_expired"),
                mock.patch.object(gc, "_require_unconsumed"),
                mock.patch.object(
                    gc, "_inventory_age",
                    side_effect=lambda _spec: order.append("inventory-age"),
                ),
                mock.patch.object(
                    gc, "_revalidate_host",
                    side_effect=lambda _spec: order.append("host-revalidation"),
                ),
                mock.patch.object(
                    gc, "_live_target",
                    side_effect=lambda *_args, **_kwargs: (
                        order.append("live-target") or {"pid": 1}
                    ),
                ),
                mock.patch.object(
                    gc.h5, "_health",
                    side_effect=lambda: order.append("health") or {"proven": True},
                ),
                mock.patch.object(
                    gc.h5, "_validate_inventory_health",
                    side_effect=lambda value: value,
                ),
                mock.patch.object(gc.h5, "_validate_inventory_target_health"),
                mock.patch.object(
                    gc,
                    "_preflight",
                    side_effect=lambda _spec: (
                        order.append("device-preflight")
                        or {"blocks": 100, "used": 90, "available": 10}
                    ),
                ),
                mock.patch.object(gc.gc, "_run_script", remote),
                mock.patch.object(
                    gc,
                    "_result",
                    return_value={
                        "schema": gc.RESULT_SCHEMA,
                        "outcome": "RECOVERY_PENDING_PARKED_NO_RETRY",
                        "cleanup_retransmitted": False,
                    },
                ),
            ):
                result = gc.execute(spec, transaction, True)
            self.assertEqual(remote.call_count, 1)
            self.assertFalse(result["cleanup_retransmitted"])
            self.assertTrue(spec.capability_dispatch_path.is_file())
            self.assertEqual(
                order,
                [
                    "host-revalidation",
                    "inventory-age",
                    "live-target",
                    "health",
                    "device-preflight",
                    "live-target",
                    "health",
                ],
            )

    def test_expiry_after_durable_receipts_stops_before_unlink(self):
        with tempfile.TemporaryDirectory() as temporary:
            private_base = Path(temporary)
            run_id = "a90-h5-historical-image-gc-20260806-02"
            selected = self.records()
            spec = SimpleNamespace(
                run_id=run_id,
                manifest_sha256="a" * 64,
                bridge_realpath="/dev/ttyACM1",
                bridge_process={"pid": 1},
                selected=selected,
                protected=gc.ArtifactRecord(
                    "P", gc.PROTECTED_PATH, gc.PROTECTED_SIZE,
                    gc.PROTECTED_SIZE // 512, gc.PROTECTED_MODE, 1,
                    45825, 9999, gc.PROTECTED_SHA256,
                ),
                rollback=SimpleNamespace(sha256="b" * 64),
                capability_dispatch_path=(
                    private_base / gc.CAPABILITY_STATE_DIR / "dispatch-started.json"
                ),
            )
            transaction = private_base / run_id / "live"
            transaction.parent.mkdir(mode=0o700)
            expiry = [None, None, None, None, gc.ContractError("expired")]
            remote = mock.Mock()
            with (
                mock.patch.object(gc, "PRIVATE_BASE", private_base),
                mock.patch.object(gc, "PRIVATE_ROOT", private_base),
                mock.patch.object(gc, "_require_not_expired", side_effect=expiry),
                mock.patch.object(gc, "_require_unconsumed"),
                mock.patch.object(gc, "_inventory_age"),
                mock.patch.object(gc, "_revalidate_host"),
                mock.patch.object(gc, "_live_target", return_value={"pid": 1}),
                mock.patch.object(gc.h5, "_health", return_value={"proven": True}),
                mock.patch.object(
                    gc.h5, "_validate_inventory_health",
                    side_effect=lambda value: value,
                ),
                mock.patch.object(gc.h5, "_validate_inventory_target_health"),
                mock.patch.object(
                    gc, "_preflight",
                    return_value={"blocks": 100, "used": 90, "available": 10},
                ),
                mock.patch.object(gc.gc, "_run_script", remote),
            ):
                result = gc.execute(spec, transaction, True)
            self.assertEqual(remote.call_count, 0)
            self.assertEqual(
                result["outcome"],
                "CAPABILITY_CONSUMED_EXPIRED_BEFORE_UNLINK",
            )
            self.assertEqual(result["dispatch_count"], 0)
            self.assertFalse(result["device_write"])
            self.assertTrue((transaction / "effect-not-started.json").is_file())

    def test_capacity_and_result_shape_reject_weak_or_forged_evidence(self):
        with self.assertRaises(gc.ContractError):
            gc._validate_filesystem(
                {"blocks": 100, "used": 80, "available": 30},
                "fixture",
            )
        with self.assertRaises(gc.ContractError):
            gc._validate_filesystem(
                {"blocks": 100, "used": True, "available": 1},
                "fixture",
            )
        spec = SimpleNamespace(
            run_id="a90-h5-historical-image-gc-20260806-03",
            manifest_sha256="a" * 64,
            selected=self.records(),
        )
        with self.assertRaises(gc.ContractError):
            gc._validate_result(
                {
                    "schema": gc.RESULT_SCHEMA,
                    "manifest_sha256": spec.manifest_sha256,
                    "outcome": gc.PASS_OUTCOME,
                    "cleanup_retransmitted": False,
                },
                spec,
                "b" * 64,
                "c" * 64,
            )

    def test_contract_names_hazard_scope_and_one_shot_closure(self):
        text = (ROOT / "docs/operations/targets/A90_TARGET_CONTRACT.md").read_text(
            encoding="utf-8"
        )
        self.assertIn(gc.CAPABILITY, text)
        self.assertIn(gc.HAZARD, text)
        self.assertIn("twenty", text)
        self.assertIn("one nonrecursive unlink dispatch", text)
        self.assertIn("host-preserved", text)


if __name__ == "__main__":
    unittest.main()
