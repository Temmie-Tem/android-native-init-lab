import hashlib
import importlib.util
import inspect
import json
import os
from pathlib import Path
import re
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "workspace/public/src/scripts/revalidation/"
    "s20plus_g986n_autonomous_research_coordinator_h0.py"
)
REPORT = (
    ROOT
    / "docs/reports/"
    "S20PLUS_G986N_AUTONOMOUS_RESEARCH_COORDINATOR_H0_2026-08-21.md"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "s20plus_g986n_autonomous_research_coordinator_h0_tested", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class S20PlusAutonomousResearchCoordinatorH0Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.old_active = self.module.COORDINATOR_ACTIVE
        self.old_live_authority = self.module.LIVE_AUTHORITY
        self.module.COORDINATOR_ACTIVE = True
        self.module.LIVE_AUTHORITY = True
        self.addCleanup(self._restore_authority)
        self.old_now = self.module._now
        self.module._now = lambda: 101
        self.addCleanup(self._restore_now)
        self.old_root = self.module.PRIVATE_RUN_ROOT
        self.old_guard = self.module.CAMPAIGN_GUARD_PATH
        self.old_campaigns = self.module.CAMPAIGNS_ROOT
        self.root = Path(self.tmp.name) / "runs"
        self.module.PRIVATE_RUN_ROOT = self.root
        self.module.CAMPAIGN_GUARD_PATH = self.root / "active-campaign.json"
        self.module.CAMPAIGNS_ROOT = self.root / "campaigns"
        self.addCleanup(self._restore_roots)

    def _restore_authority(self):
        self.module.COORDINATOR_ACTIVE = self.old_active
        self.module.LIVE_AUTHORITY = self.old_live_authority

    def _restore_now(self):
        self.module._now = self.old_now

    def set_now(self, value):
        self.module._now = lambda: value

    def _restore_roots(self):
        self.module.PRIVATE_RUN_ROOT = self.old_root
        self.module.CAMPAIGN_GUARD_PATH = self.old_guard
        self.module.CAMPAIGNS_ROOT = self.old_campaigns

    def identity(self):
        return {
            "target": self.module.TARGET,
            "serial_sha256": "1" * 64,
            "topology_sha256": "2" * 64,
            "boot_id_sha256": "3" * 64,
            "healthy_android": True,
            "foreign_guard_present": False,
        }

    def health_identity(self, base, boot="7"):
        observed = dict(base)
        observed["boot_id_sha256"] = boot * 64
        return observed

    def download_topology(self):
        return sorted(self.module.EXPECTED_DOWNLOAD_TOPOLOGY_SHA256)[0]

    def fixture(self, opened_at=100):
        model = self.module.model_campaign_opening(self.identity(), opened_at)
        session = (
            self.root
            / "campaigns"
            / model["campaign_id"]
            / "session"
        )
        self.module.publish_campaign_opening(model)
        return model, session

    def publish_entry_arrival_return(self, model, session):
        current_now = self.module._now()
        context = self.module.validate_chain(now=current_now)
        baseline, entry = self.module.model_roundtrip_pair(context)
        self.module.durable_json(session / "baseline-000001.json", baseline)
        self.module.durable_json(session / "entry-000001.json", entry)
        context = self.module.validate_chain(now=current_now)
        endpoint = {
            "path_sha256": "4" * 64,
            "identity_sha256": "5" * 64,
            "topology_sha256": self.download_topology(),
            "product": "SM8250",
        }
        arrival = self.module.model_arrival_node(context, endpoint)
        self.module.durable_json(session / "arrival-000001.json", arrival)
        context = self.module.validate_chain(now=current_now)
        returned = self.module.model_return_node(context)
        self.module.durable_json(session / "return-000001.json", returned)
        context = self.module.validate_chain(now=current_now)
        health = self.module.model_return_health_node(
            context, self.health_identity(context["source_identity"])
        )
        self.module.durable_json(session / "return-health-000001.json", health)
        return self.module.validate_chain(now=current_now)

    def test_render_is_dormant_and_has_no_effect_surface(self):
        self.module.COORDINATOR_ACTIVE = False
        self.module.LIVE_AUTHORITY = False
        try:
            plan = self.module.render_plan()
        finally:
            self.module.COORDINATOR_ACTIVE = True
            self.module.LIVE_AUTHORITY = True
        self.assertFalse(plan["active"])
        self.assertFalse(plan["live_authority"])
        self.assertFalse(plan["mechanically_activatable"])
        self.assertFalse(plan["live_action_integration"])
        self.assertTrue(plan["journal_candidate_only"])
        self.assertIn("exact-empty-download-listing-producer", plan["binding"]["live_integration_required"])
        self.assertEqual(
            plan["status"],
            "H0_AUTONOMOUS_RESEARCH_COORDINATOR_PASS_GO_NOT_ACTIVE",
        )
        self.assertEqual(plan["cli"], ["--render-plan"])
        for key in (
            "device_commands",
            "root_commands",
            "device_effects",
            "partition_transfers",
            "odin_payloads",
        ):
            self.assertEqual(plan[key], [])

    def test_exact_sources_and_binding_are_current(self):
        plan = self.module.render_plan()
        self.assertEqual(plan["binding_sha256"], self.module.binding_digest())
        self.assertEqual(
            set(plan["binding"]["sources"]),
            {
                "coordinator",
                "policy_owner",
                "inventory",
                "routine_d0",
                "routine_actions",
                "download_exit",
            },
        )
        self.assertEqual(
            plan["binding"]["sources"]["coordinator"]["normalized_sha256"],
            self.module.EXPECTED_COORDINATOR_NORMALIZED_SHA256,
        )
        self.assertTrue(plan["binding"]["privacy"]["caller_callback"] is False)

    def test_direct_helpers_gate_before_input_or_filesystem_effect(self):
        coordinator = self.module.Coordinator()
        methods = (
            coordinator.open_campaign,
            coordinator.begin_named_action,
            coordinator.begin_entry,
            coordinator.record_arrival,
            coordinator.begin_return,
            coordinator.prepare_f1_readiness,
        )
        self.module.COORDINATOR_ACTIVE = False
        self.module.LIVE_AUTHORITY = False
        try:
            for method in methods:
                with self.subTest(method=method.__name__), self.assertRaisesRegex(
                    self.module.CoordinatorError, "dormant"
                ):
                    method({"action": "shell", "path": "/foreign"})
            with self.assertRaisesRegex(
                self.module.CoordinatorError, "private coordinator filesystem"
            ):
                self.module.read_json(self.root / "missing.json")
            with self.assertRaisesRegex(
                self.module.CoordinatorError, "private coordinator filesystem"
            ):
                self.module.durable_json(self.root / "missing.json", {"x": 1})
        finally:
            self.module.COORDINATOR_ACTIVE = True
            self.module.LIVE_AUTHORITY = True
        self.assertFalse(self.root.exists())
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("_HOST_TEST_CONTEXT", source)
        self.assertNotIn("test_only_host_context", source)
        self.assertNotIn("callback", str(inspect.signature(coordinator.begin_entry)))

    def test_every_direct_private_fs_classifier_is_dormant_before_context(self):
        self.module.COORDINATOR_ACTIVE = False
        self.module.LIVE_AUTHORITY = False
        model = self.module.model_campaign_opening(self.identity(), 100)
        calls = (
            (self.module.atomic_publish, (self.root / "x.json", b"{}\n")),
            (self.module.durable_json, (self.root / "x.json", {"x": 1})),
            (self.module.read_exact_json, (self.root / "x.json",)),
            (self.module.read_json, (self.root / "x.json",)),
            (self.module._read_bounded, (self.root / "x.json", "x")),
            (self.module._ensure_private_dir, (self.root / "x",)),
            (self.module._open_directory, (self.root,)),
            (self.module._open_managed_directory, (self.root,)),
            (self.module._managed_path, (self.root / "x",)),
            (self.module._allowed_final_name, ("opening.json",)),
            (self.module._allowed_node_names, ()),
            (self.module._campaign_dir, ("1" * 32,)),
            (self.module._session_dir, ("1" * 32,)),
            (self.module.validate_chain, ()),
            (self.module.current_context, ()),
            (self.module.validate_current_guard, ()),
            (self.module.validate_full_chain, ()),
            (self.module.terminal_guard_state, ()),
            (self.module.recovery_authority, ()),
            (self.module.reconcile_opening_cut, ()),
            (self.module.publish_campaign_opening, (model,)),
        )
        try:
            for function, args in calls:
                with self.subTest(function=function.__name__), self.assertRaisesRegex(
                    self.module.CoordinatorError, "private coordinator filesystem"
                ):
                    function(*args)
        finally:
            self.module.COORDINATOR_ACTIVE = True
            self.module.LIVE_AUTHORITY = True
        self.assertFalse(self.root.exists())

    def test_named_request_and_typed_identity_reject_callers(self):
        for value in (
            {},
            {"action": "public-health", "path": "/data"},
            {"action": "public-health", "shell": "id"},
            {"action": True},
            {"action": "shell"},
            ["public-health"],
        ):
            with self.subTest(value=value), self.assertRaises(
                self.module.CoordinatorError
            ):
                self.module.validate_named_request(value)
        good = self.module.validate_named_request({"action": "public-health"})
        self.assertEqual(good, "public-health")
        bad = dict(self.identity())
        bad["healthy_android"] = 1
        with self.assertRaises(self.module.CoordinatorError):
            self.module.validate_identity(bad)

    def test_opening_chain_is_guard_first_and_current(self):
        model, _ = self.fixture()
        context = self.module.validate_chain(now=101)
        self.assertEqual(context["campaign_id"], model["campaign_id"])
        self.assertEqual(context["session_id"], model["session_id"])
        self.assertEqual(context["current_ordinal"], 0)
        self.assertTrue(context["no_replay"])

    def test_download_baseline_is_exact_empty_and_precedes_entry(self):
        model, session = self.fixture()
        context = self.module.validate_chain(now=101)
        baseline, entry = self.module.model_roundtrip_pair(context)
        self.assertEqual(baseline["ordinal"], 1)
        self.assertEqual(baseline["baseline"]["endpoint_count"], 0)
        self.assertEqual(
            baseline["baseline"]["listing_sha256"],
            self.module.EMPTY_DOWNLOAD_LISTING_SHA256,
        )
        self.assertEqual(
            baseline["baseline"]["listing_grammar"],
            self.module.EMPTY_DOWNLOAD_LISTING_GRAMMAR,
        )
        self.assertEqual(
            entry["baseline_sha256"],
            hashlib.sha256(self.module.canonical_bytes(baseline)).hexdigest(),
        )
        self.module.durable_json(session / "baseline-000001.json", baseline)
        baseline_context = self.module.validate_chain(now=101)
        self.assertEqual(baseline_context["phase"], "download-baseline-ready")
        self.assertFalse(
            self.module.recovery_authority(
                now=model["guard"]["expires_at"]
            )["authority"]
        )
        with self.assertRaisesRegex(self.module.CoordinatorError, "baseline-only"):
            self.module.model_entry_node(baseline_context)
        self.module.durable_json(session / "entry-000001.json", entry)
        self.assertEqual(
            self.module.validate_chain(now=101)["phase"],
            "download-entry-pending",
        )

    def test_baseline_hostile_nonempty_stale_reuse_missing_and_forged_hash_stop(self):
        model, session = self.fixture()
        context = self.module.validate_chain(now=101)
        baseline, entry = self.module.model_roundtrip_pair(context)
        baseline["baseline"]["endpoint_count"] = 1
        self.module.durable_json(session / "baseline-000001.json", baseline)
        with self.assertRaisesRegex(self.module.CoordinatorError, "nonempty"):
            self.module.validate_chain(now=101)

        self._restore_roots()
        self.setUp()
        model, session = self.fixture()
        context = self.module.validate_chain(now=101)
        baseline, entry = self.module.model_roundtrip_pair(context)
        baseline["ordinal"] = 2
        self.module.durable_json(session / "baseline-000001.json", baseline)
        with self.assertRaisesRegex(self.module.CoordinatorError, "ordinal"):
            self.module.validate_chain(now=101)

        self._restore_roots()
        self.setUp()
        model, session = self.fixture()
        context = self.module.validate_chain(now=101)
        baseline, entry = self.module.model_roundtrip_pair(context)
        entry["baseline_sha256"] = "f" * 64
        self.module.durable_json(session / "baseline-000001.json", baseline)
        self.module.durable_json(session / "entry-000001.json", entry)
        with self.assertRaisesRegex(self.module.CoordinatorError, "baseline"):
            self.module.validate_chain(now=101)

        self._restore_roots()
        self.setUp()
        model, session = self.fixture()
        context = self.module.validate_chain(now=101)
        baseline, entry = self.module.model_roundtrip_pair(context)
        self.module.durable_json(session / "entry-000001.json", entry)
        with self.assertRaisesRegex(self.module.CoordinatorError, "unreachable|old"):
            self.module.validate_chain(now=101)

        self._restore_roots()
        self.setUp()
        model, session = self.fixture()
        context = self.module.validate_chain(now=101)
        baseline, entry = self.module.model_roundtrip_pair(context)
        self.module.durable_json(session / "baseline-000001.json", baseline)
        self.module.durable_json(session / "entry-000001.json", entry)
        reused = dict(baseline)
        reused["ordinal"] = 2
        reused["predecessor_sha256"] = hashlib.sha256(
            self.module.canonical_bytes(entry)
        ).hexdigest()
        self.module.durable_json(session / "baseline-000002.json", reused)
        with self.assertRaisesRegex(self.module.CoordinatorError, "baseline|healthy"):
            self.module.validate_chain(now=101)

    def test_entry_without_baseline_is_rejected(self):
        model, session = self.fixture()
        context = self.module.validate_chain(now=101)
        _, entry = self.module.model_roundtrip_pair(context)
        self.module.durable_json(session / "entry-000001.json", entry)
        with self.assertRaisesRegex(self.module.CoordinatorError, "unreachable|old"):
            self.module.validate_chain(now=101)

    def test_third_download_topology_is_rejected(self):
        endpoint = {
            "path_sha256": "4" * 64,
            "identity_sha256": "5" * 64,
            "topology_sha256": "6" * 64,
            "product": "SM8250",
        }
        with self.assertRaisesRegex(self.module.CoordinatorError, "allowlisted"):
            self.module.validate_endpoint(endpoint)

    def test_opening_cut_keeps_guard_and_reconciles_exact_missing_nodes(self):
        model = self.module.model_campaign_opening(self.identity(), 100)
        original = self.module.durable_json

        def cut(path, value):
            if Path(path).name == "opening.json":
                raise self.module.CoordinatorError("modeled opening publication cut")
            return original(path, value)

        self.module.durable_json = cut
        try:
            with self.assertRaisesRegex(self.module.CoordinatorError, "opening publication cut"):
                self.module.publish_campaign_opening(model)
        finally:
            self.module.durable_json = original
        self.assertTrue(self.module.CAMPAIGN_GUARD_PATH.exists())
        result = self.module.reconcile_opening_cut()
        self.assertTrue(result["guard_present"])
        self.assertTrue(result["reconciled"])
        session = self.root / "campaigns" / model["campaign_id"] / "session"
        self.assertTrue((session / "opening.json").exists())
        self.assertTrue((session / "session-opening.json").exists())
        self.assertEqual(self.module.validate_chain(now=101)["phase"], "healthy-normal")

    def test_closed_path_grammar_rejects_traversal_before_filesystem_access(self):
        outside = Path(self.tmp.name) / "outside"
        original_open = self.module.os.open

        def unexpected_open(*_args, **_kwargs):
            raise AssertionError("path rejection opened a filesystem component")

        self.module.os.open = unexpected_open
        try:
            for path in (
                self.root / "campaigns" / ".." / "outside",
                self.root / "campaigns" / ("1" * 31) / "session" / "opening.json",
                self.root / "campaigns" / ("1" * 32) / "session" / "extra" / "opening.json",
                self.root / "campaigns" / ("1" * 32) / "session" / "active-campaign.json",
                outside / "active-campaign.json",
            ):
                with self.subTest(path=path), self.assertRaises(
                    self.module.CoordinatorError
                ):
                    self.module._managed_path(path)
            with self.assertRaises(self.module.CoordinatorError):
                self.module._open_managed_directory(
                    self.root / "campaigns" / ".."
                )
        finally:
            self.module.os.open = original_open
        self.assertFalse(outside.exists())

    def test_intermediate_ancestor_symlink_is_rejected_without_outside_read(self):
        outside = Path(self.tmp.name) / "outside"
        outside.mkdir(mode=0o700)
        sentinel = outside / "opening.json"
        sentinel.write_bytes(b"outside\n")
        os.chmod(sentinel, 0o400)
        self.module._ensure_private_dir(self.root)
        os.symlink(outside, self.module.CAMPAIGNS_ROOT)
        with self.assertRaisesRegex(self.module.CoordinatorError, "indirect|unavailable"):
            self.module._open_managed_directory(self.module.CAMPAIGNS_ROOT)
        with self.assertRaises(self.module.CoordinatorError):
            self.module._read_bounded(
                self.root / "campaigns" / ("1" * 32) / "session" / "opening.json",
                "symlink parent",
            )
        self.assertEqual(sentinel.read_bytes(), b"outside\n")

    def test_parent_swap_is_pinned_and_cannot_redirect_read(self):
        _model, session = self.fixture()
        outside = Path(self.tmp.name) / "outside"
        outside.mkdir(mode=0o700)
        sentinel = outside / "sentinel"
        sentinel.write_bytes(b"outside\n")
        os.chmod(sentinel, 0o400)
        old_session = session.with_name("session-old")
        session.rename(old_session)
        os.symlink(outside, session)
        try:
            with self.assertRaises(self.module.CoordinatorError):
                self.module._read_bounded(session / "opening.json", "swapped parent")
            self.assertEqual(sentinel.read_bytes(), b"outside\n")
        finally:
            session.unlink()
            old_session.rename(session)

    def test_no_direct_unlink_or_rmdir_helper_surface_remains(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("def _remove_owned_final", source)
        self.assertNotIn("def _remove_empty_owned_dir", source)
        self.assertNotIn("os.unlink(", source)
        self.assertNotIn("os.rmdir(", source)

    def test_journal_final_owner_and_group_match_private_parent(self):
        _model, session = self.fixture()
        path = session / "opening.json"
        parent_stat = os.stat(session)
        original = os.stat(path)
        self.assertEqual(original.st_uid, parent_stat.st_uid)
        self.assertEqual(original.st_gid, parent_stat.st_gid)
        alternate_groups = [
            gid for gid in os.getgroups() if gid != parent_stat.st_gid
        ]
        if not alternate_groups:
            self.skipTest("platform has no different supplementary gid")
        alternate_gid = alternate_groups[0]
        changed = False
        try:
            try:
                os.chown(path, original.st_uid, alternate_gid)
                changed = True
            except OSError as exc:
                self.skipTest(f"platform cannot chgrp journal final: {exc}")
            with self.assertRaisesRegex(self.module.CoordinatorError, "owned by its parent"):
                self.module.read_exact_json(path, "wrong group")
        finally:
            if changed:
                os.chown(path, original.st_uid, original.st_gid)

    def test_guardless_foreign_0400_file_is_retained_and_blocks_opening(self):
        self.module._ensure_private_dir(self.root)
        self.module._ensure_private_dir(self.module.CAMPAIGNS_ROOT)
        foreign = self.root / "foreign-guardless.json"
        foreign.write_bytes(b"foreign\n")
        os.chmod(foreign, 0o400)
        model = self.module.model_campaign_opening(self.identity(), 100)
        with self.assertRaisesRegex(self.module.CoordinatorError, "foreign"):
            self.module.publish_campaign_opening(model)
        result = self.module.reconcile_opening_cut()
        self.assertFalse(result["guard_present"])
        self.assertEqual(foreign.read_bytes(), b"foreign\n")
        self.assertFalse(self.module.CAMPAIGN_GUARD_PATH.exists())

    def test_concurrent_opening_fails_under_no_replace_guard(self):
        first = self.module.model_campaign_opening(self.identity(), 100)
        second = self.module.model_campaign_opening(self.identity(), 100)
        self.module.publish_campaign_opening(first)
        with self.assertRaisesRegex(self.module.CoordinatorError, "concurrent"):
            self.module.publish_campaign_opening(second)
        with self.assertRaisesRegex(self.module.CoordinatorError, "already owns"):
            self.module.publish_campaign_opening(first)
        self.assertEqual(
            self.module.validate_chain(now=101)["campaign_id"], first["campaign_id"]
        )

    def test_guard_first_link_fsync_and_between_node_cuts_leave_exact_recovery(self):
        model = self.module.model_campaign_opening(self.identity(), 100)
        original_link = self.module._link_tmpfile

        def link_cut(_descriptor, _parent, name):
            if name == "opening.json":
                raise OSError("modeled link cut after guard")
            return original_link(_descriptor, _parent, name)

        self.module._link_tmpfile = link_cut
        try:
            with self.assertRaisesRegex(self.module.CoordinatorError, "publication"):
                self.module.publish_campaign_opening(model)
        finally:
            self.module._link_tmpfile = original_link
        self.assertTrue(self.module.CAMPAIGN_GUARD_PATH.exists())
        self.assertTrue(self.module.reconcile_opening_cut()["reconciled"])

        self._restore_roots()
        self.setUp()
        model = self.module.model_campaign_opening(self.identity(), 100)
        original_durable = self.module.durable_json
        original_fsync = self.module.os.fsync
        state = {"guard": False}

        def fsync_cut(fd):
            if state["guard"]:
                raise OSError("modeled fsync cut after guard")
            return original_fsync(fd)

        def between_nodes(path, value):
            if Path(path).name == "session-opening.json":
                raise self.module.CoordinatorError("modeled node cut after opening")
            result = original_durable(path, value)
            if Path(path).name == "active-campaign.json":
                state["guard"] = True
            return result

        self.module.os.fsync = fsync_cut
        self.module.durable_json = between_nodes
        try:
            with self.assertRaisesRegex(self.module.CoordinatorError, "fsync"):
                self.module.publish_campaign_opening(model)
        finally:
            self.module.os.fsync = original_fsync
            self.module.durable_json = original_durable
        self.assertTrue(self.module.CAMPAIGN_GUARD_PATH.exists())

        self._restore_roots()
        self.setUp()
        model = self.module.model_campaign_opening(self.identity(), 100)
        original_durable = self.module.durable_json

        def between_nodes(path, value):
            if Path(path).name == "session-opening.json":
                raise self.module.CoordinatorError("modeled write cut between nodes")
            return original_durable(path, value)

        self.module.durable_json = between_nodes
        try:
            with self.assertRaisesRegex(self.module.CoordinatorError, "between nodes"):
                self.module.publish_campaign_opening(model)
        finally:
            self.module.durable_json = original_durable
        session = self.root / "campaigns" / model["campaign_id"] / "session"
        self.assertTrue(self.module.CAMPAIGN_GUARD_PATH.exists())
        self.assertTrue((session / "opening.json").exists())
        self.assertTrue(self.module.reconcile_opening_cut()["reconciled"])

    def test_full_entry_arrival_return_chain_and_counter_snapshots(self):
        model, session = self.fixture()
        context = self.publish_entry_arrival_return(model, session)
        self.assertEqual(context["phase"], "healthy-normal")
        self.assertEqual(context["current_ordinal"], 1)
        self.assertEqual(context["campaign_counters"]["roundtrip_returns"], 1)
        self.assertEqual(context["campaign_counters"]["component_effects_consumed"], 2)
        self.assertEqual(context["campaign_counters"]["component_effects_reserved"], 0)
        for name in ("entry-000001.json", "return-000001.json"):
            node, _ = self.module.read_exact_json(session / name, name)
            self.assertIn("child_counters", node)
            self.assertIn("campaign_counters", node)
            self.assertIn("predecessor_sha256", node)
        entry, entry_bytes = self.module.read_exact_json(
            session / "entry-000001.json", "entry"
        )
        arrival, _ = self.module.read_exact_json(
            session / "arrival-000001.json", "arrival"
        )
        self.assertEqual(
            arrival["predecessor_sha256"], hashlib.sha256(entry_bytes).hexdigest()
        )

    def test_reboot_requires_fresh_health_observation_before_next_control_or_terminal(self):
        model, session = self.fixture()
        context = self.module.validate_chain(now=101)
        reboot = self.module.model_entry_node(context, "reboot-system")
        self.module.durable_json(session / "reboot-000001.json", reboot)
        context = self.module.validate_chain(now=101)
        self.assertEqual(context["phase"], "reboot-health-pending")
        with self.assertRaises(self.module.CoordinatorError):
            self.module.model_entry_node(context, "reboot-system")
        with self.assertRaises(self.module.CoordinatorError):
            self.module.model_terminal_node(context)
        recovery = self.module.recovery_authority(now=model["guard"]["expires_at"])
        self.assertEqual(recovery["allowed_actions"], ["observe-reboot-health"])
        with self.assertRaises(self.module.CoordinatorError):
            self.module.model_reboot_health_node(context, context["source_identity"])
        foreign = self.health_identity(context["source_identity"], "7")
        foreign["serial_sha256"] = "f" * 64
        with self.assertRaises(self.module.CoordinatorError):
            self.module.model_reboot_health_node(context, foreign)
        health = self.module.model_reboot_health_node(
            context, self.health_identity(context["source_identity"], "7")
        )
        self.module.durable_json(session / "reboot-health-000001.json", health)
        context = self.module.validate_chain(now=101)
        self.assertEqual(context["phase"], "healthy-normal")
        self.assertEqual(
            context["source_identity"]["boot_id_sha256"], "7" * 64
        )
        reboot_two = self.module.model_entry_node(context, "reboot-system")
        self.module.durable_json(session / "reboot-000002.json", reboot_two)
        context = self.module.validate_chain(now=101)
        stale = self.health_identity(context["source_identity"], "3")
        self.module.durable_json(
            session / "reboot-health-000002.json",
            self.module.model_reboot_health_node(context, stale),
        )
        with self.assertRaisesRegex(self.module.CoordinatorError, "reused"):
            self.module.validate_chain(now=101)

    def test_return_derives_endpoint_and_never_accepts_caller_endpoint(self):
        model, session = self.fixture()
        context = self.module.validate_chain(now=101)
        baseline, entry = self.module.model_roundtrip_pair(context)
        self.module.durable_json(session / "baseline-000001.json", baseline)
        self.module.durable_json(session / "entry-000001.json", entry)
        context = self.module.validate_chain(now=101)
        endpoint = {
            "path_sha256": "4" * 64,
            "identity_sha256": "5" * 64,
            "topology_sha256": self.download_topology(),
            "product": "SM8250",
        }
        self.module.durable_json(
            session / "arrival-000001.json",
            self.module.model_arrival_node(context, endpoint),
        )
        context = self.module.validate_chain(now=101)
        # model_return_node intentionally has no endpoint parameter; it derives
        # the endpoint from the validated current context.
        self.assertEqual(
            inspect.signature(self.module.model_return_node).parameters.keys(),
            {"context"},
        )
        returned = self.module.model_return_node(context)
        returned["endpoint"]["path_sha256"] = "f" * 64
        self.module.durable_json(session / "return-000001.json", returned)
        with self.assertRaises(self.module.CoordinatorError):
            self.module.validate_chain(now=101)

    def test_old_ordinal_foreign_source_and_predecessor_are_rejected(self):
        model, session = self.fixture()
        context = self.module.validate_chain(now=101)
        baseline, entry = self.module.model_roundtrip_pair(context)
        entry["ordinal"] = 2
        self.module.durable_json(session / "baseline-000001.json", baseline)
        self.module.durable_json(session / "entry-000001.json", entry)
        with self.assertRaisesRegex(self.module.CoordinatorError, "ordinal"):
            self.module.validate_chain(now=101)

        # Rebuild a clean fixture and exercise actual predecessor bytes.
        self._restore_roots()
        self.setUp()
        model, session = self.fixture()
        context = self.module.validate_chain(now=101)
        baseline, entry = self.module.model_roundtrip_pair(context)
        entry["predecessor_sha256"] = "a" * 64
        self.module.durable_json(session / "baseline-000001.json", baseline)
        self.module.durable_json(session / "entry-000001.json", entry)
        with self.assertRaisesRegex(self.module.CoordinatorError, "old|chain"):
            self.module.validate_chain(now=101)

    def test_partial_scope_duplicate_noncanonical_nonfinite_and_extra_nodes_stop(self):
        model, session = self.fixture()
        context = self.module.validate_chain(now=101)
        baseline, entry = self.module.model_roundtrip_pair(context)
        entry.pop("child_counters")
        self.module.durable_json(session / "baseline-000001.json", baseline)
        self.module.durable_json(session / "entry-000001.json", entry)
        with self.assertRaises(self.module.CoordinatorError):
            self.module.validate_chain(now=101)

        # A fresh fixture is used for each namespace/encoding cut.
        self._restore_roots()
        self.setUp()
        model, session = self.fixture()
        with open(session / "unexpected.partial.json", "wb") as handle:
            handle.write(b"{}\n")
        os.chmod(session / "unexpected.partial.json", 0o400)
        with self.assertRaisesRegex(self.module.CoordinatorError, "unknown|partial"):
            self.module.validate_chain(now=101)

    def test_symlink_and_hardlink_final_names_are_rejected(self):
        model, session = self.fixture()
        link = session / "entry-000001.json"
        os.symlink(self.module.CAMPAIGN_GUARD_PATH, link)
        with self.assertRaises(self.module.CoordinatorError):
            self.module.validate_chain(now=101)

        self._restore_roots()
        self.setUp()
        model, session = self.fixture()
        source = session / "foreign.json"
        source.write_bytes(b"{}\n")
        os.chmod(source, 0o400)
        os.link(source, session / "entry-000001.json")
        with self.assertRaises(self.module.CoordinatorError):
            self.module.validate_chain(now=101)

    def test_noncanonical_duplicate_and_nonfinite_json_are_rejected(self):
        model, session = self.fixture()
        path = session / "opening.json"
        value = {
            "schema": self.module.SCHEMA,
            "kind": "campaign-opening",
        }
        path.unlink()
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(descriptor)
        with open(path, "wb") as handle:
            handle.write(b'{"a":1,"a":2}\n')
        os.chmod(path, 0o400)
        with self.assertRaisesRegex(self.module.CoordinatorError, "duplicate"):
            self.module.read_exact_json(path, "duplicate")
        path.unlink()
        with open(path, "wb") as handle:
            handle.write(b'{"a":NaN}\n')
        os.chmod(path, 0o400)
        with self.assertRaisesRegex(self.module.CoordinatorError, "malformed"):
            self.module.read_exact_json(path, "nonfinite")
        path.unlink()
        with open(path, "wb") as handle:
            handle.write(b'{"a": 1}\n')
        os.chmod(path, 0o400)
        with self.assertRaisesRegex(self.module.CoordinatorError, "non-canonical"):
            self.module.read_exact_json(path, "noncanonical")

    def test_atomic_publication_is_no_replace_and_cut_leaves_no_final_name(self):
        _model, session = self.fixture()
        final = session / "terminal.json"
        payload = self.module.canonical_bytes({"x": 1})
        self.module.atomic_publish(final, payload)
        with self.assertRaisesRegex(self.module.CoordinatorError, "already exists"):
            self.module.atomic_publish(final, payload)
        self.assertEqual(final.read_bytes(), payload)

        cut = session / "entry-000001.json"
        original = self.module._link_tmpfile
        self.module._link_tmpfile = lambda *_args: (_ for _ in ()).throw(
            OSError("modeled link cut")
        )
        try:
            with self.assertRaisesRegex(self.module.CoordinatorError, "publication"):
                self.module.atomic_publish(cut, payload)
        finally:
            self.module._link_tmpfile = original
        self.assertFalse(cut.exists())

    def test_expiry_recovery_is_only_for_current_unmatched_reserved_return(self):
        model, session = self.fixture()
        context = self.module.validate_chain(now=101)
        baseline, entry = self.module.model_roundtrip_pair(context)
        self.module.durable_json(session / "baseline-000001.json", baseline)
        self.module.durable_json(session / "entry-000001.json", entry)
        recovery = self.module.recovery_authority(now=model["guard"]["expires_at"])
        self.assertTrue(recovery["authority"])
        self.assertEqual(recovery["allowed_actions"], ["observe-bound-arrival"])
        self.assertTrue(recovery["no_new_baseline"])
        self.assertTrue(recovery["no_new_entry"])
        self.assertTrue(recovery["no_new_transaction"])

        context = self.module.validate_chain(now=101)
        endpoint = {
            "path_sha256": "4" * 64,
            "identity_sha256": "5" * 64,
            "topology_sha256": self.download_topology(),
            "product": "SM8250",
        }
        self.module.durable_json(
            session / "arrival-000001.json",
            self.module.model_arrival_node(context, endpoint),
        )
        recovery = self.module.recovery_authority(now=model["guard"]["expires_at"])
        self.assertEqual(recovery["allowed_actions"], ["payload-free-return"])

        context = self.module.validate_chain(now=101)
        self.module.durable_json(
            session / "return-000001.json", self.module.model_return_node(context)
        )
        recovery = self.module.recovery_authority(now=model["guard"]["expires_at"])
        self.assertTrue(recovery["authority"])
        self.assertEqual(
            recovery["allowed_actions"], ["observe-return-health", "final-health"]
        )
        context = self.module.validate_chain(now=101)
        self.module.durable_json(
            session / "return-health-000001.json",
            self.module.model_return_health_node(
                context, self.health_identity(context["source_identity"])
            ),
        )
        recovery = self.module.recovery_authority(now=model["guard"]["expires_at"])
        self.assertFalse(recovery["authority"])

    def test_expiry_boundary_blocks_new_nodes_and_keeps_typed_context_current(self):
        model, session = self.fixture()
        session_expiry = model["session"]["expires_at"]
        campaign_expiry = model["guard"]["expires_at"]
        preexpiry = session_expiry - 1
        self.set_now(preexpiry)
        context = self.module.validate_chain(now=preexpiry)
        self.assertEqual(context["current_time"], preexpiry)
        self.assertEqual(context["session_expires_at"], session_expiry)
        baseline = self.module.model_baseline_node(context)
        self.assertEqual(baseline["issued_at"], preexpiry)
        self.set_now(session_expiry)
        with self.assertRaisesRegex(self.module.CoordinatorError, "expiry"):
            self.module.model_baseline_node(
                self.module.validate_chain(now=session_expiry)
            )
        with self.assertRaisesRegex(self.module.CoordinatorError, "expiry"):
            self.set_now(campaign_expiry)
            self.module.model_baseline_node(
                self.module.validate_chain(now=campaign_expiry)
            )
        with self.assertRaisesRegex(self.module.CoordinatorError, "expiry"):
            self.set_now(session_expiry)
            self.module.model_entry_node(
                self.module.validate_chain(now=session_expiry), "reboot-system"
            )
        with self.assertRaisesRegex(self.module.CoordinatorError, "expiry"):
            self.set_now(session_expiry)
            self.module.model_terminal_node(
                self.module.validate_chain(now=session_expiry)
            )
        forged = dict(context)
        forged["current_time"] = "not-a-timestamp"
        with self.assertRaises(self.module.CoordinatorError):
            self.module.model_baseline_node(forged)

    def test_preexpiry_roundtrip_allows_postexpiry_arrival_return_and_health(self):
        model, session = self.fixture()
        preexpiry = model["session"]["expires_at"] - 1
        postexpiry = model["session"]["expires_at"] + 1
        self.set_now(preexpiry)
        context = self.module.validate_chain(now=preexpiry)
        baseline, entry = self.module.model_roundtrip_pair(context)
        self.assertEqual(baseline["issued_at"], entry["issued_at"])
        self.module.durable_json(session / "baseline-000001.json", baseline)
        self.module.durable_json(session / "entry-000001.json", entry)
        context = self.module.validate_chain(now=preexpiry)
        endpoint = {
            "path_sha256": "4" * 64,
            "identity_sha256": "5" * 64,
            "topology_sha256": self.download_topology(),
            "product": "SM8250",
        }
        arrival = self.module.model_arrival_node(context, endpoint)
        self.assertEqual(arrival["issued_at"], preexpiry)
        self.module.durable_json(session / "arrival-000001.json", arrival)
        self.set_now(postexpiry)
        context = self.module.validate_chain(now=postexpiry)
        returned = self.module.model_return_node(context)
        self.assertEqual(returned["issued_at"], postexpiry)
        self.module.durable_json(session / "return-000001.json", returned)
        context = self.module.validate_chain(now=postexpiry)
        health = self.module.model_return_health_node(
            context, self.health_identity(context["source_identity"], "8")
        )
        self.assertEqual(health["issued_at"], postexpiry)
        self.module.durable_json(session / "return-health-000001.json", health)
        final = self.module.validate_chain(now=postexpiry)
        self.assertEqual(final["phase"], "healthy-normal")

    def test_preexpiry_reboot_allows_only_postexpiry_health_completion(self):
        model, session = self.fixture()
        preexpiry = model["session"]["expires_at"] - 1
        postexpiry = model["session"]["expires_at"] + 1
        self.set_now(preexpiry)
        context = self.module.validate_chain(now=preexpiry)
        reboot = self.module.model_entry_node(context, "reboot-system")
        self.assertLessEqual(reboot["issued_at"], model["session"]["expires_at"])
        self.module.durable_json(session / "reboot-000001.json", reboot)
        self.set_now(postexpiry)
        context = self.module.validate_chain(now=postexpiry)
        with self.assertRaises(self.module.CoordinatorError):
            self.module.model_entry_node(context, "reboot-system")
        health = self.module.model_reboot_health_node(
            context, self.health_identity(context["source_identity"], "8")
        )
        self.assertEqual(health["issued_at"], postexpiry)
        self.module.durable_json(session / "reboot-health-000001.json", health)
        self.assertEqual(
            self.module.validate_chain(now=postexpiry)["phase"], "healthy-normal"
        )

    def test_persisted_postexpiry_new_nodes_reject_before_recovery_authority(self):
        model, session = self.fixture()
        preexpiry = model["session"]["expires_at"] - 1
        postexpiry = model["session"]["expires_at"] + 1
        self.set_now(preexpiry)
        context = self.module.validate_chain(now=preexpiry)
        reboot = self.module.model_entry_node(context, "reboot-system")
        reboot["issued_at"] = postexpiry
        self.module.durable_json(session / "reboot-000001.json", reboot)
        self.set_now(postexpiry)
        with self.assertRaisesRegex(self.module.CoordinatorError, "after expiry"):
            self.module.validate_chain(now=postexpiry)
        with self.assertRaisesRegex(self.module.CoordinatorError, "after expiry"):
            self.module.recovery_authority(now=postexpiry)

        self._restore_roots()
        self.setUp()
        model, session = self.fixture()
        self.set_now(preexpiry)
        context = self.module.validate_chain(now=preexpiry)
        baseline, _entry = self.module.model_roundtrip_pair(context)
        baseline["issued_at"] = postexpiry
        self.module.durable_json(session / "baseline-000001.json", baseline)
        self.set_now(postexpiry)
        with self.assertRaisesRegex(self.module.CoordinatorError, "after expiry"):
            self.module.validate_chain(now=postexpiry)

        self._restore_roots()
        self.setUp()
        model, session = self.fixture()
        self.set_now(preexpiry)
        context = self.module.validate_chain(now=preexpiry)
        baseline, entry = self.module.model_roundtrip_pair(context)
        self.module.durable_json(session / "baseline-000001.json", baseline)
        entry["issued_at"] = postexpiry
        self.module.durable_json(session / "entry-000001.json", entry)
        self.set_now(postexpiry)
        with self.assertRaisesRegex(self.module.CoordinatorError, "after expiry"):
            self.module.validate_chain(now=postexpiry)

        self._restore_roots()
        self.setUp()
        model, session = self.fixture()
        self.set_now(preexpiry)
        self.publish_entry_arrival_return(model, session)
        terminal = self.module.model_terminal_node(
            self.module.validate_chain(now=preexpiry)
        )
        terminal["issued_at"] = postexpiry
        self.module.durable_json(session / "terminal.json", terminal)
        self.set_now(postexpiry)
        with self.assertRaisesRegex(self.module.CoordinatorError, "after expiry"):
            self.module.validate_chain(now=postexpiry)

    def test_persisted_new_nodes_at_exact_session_expiry_reject(self):
        boundary_cases = ("baseline", "entry", "reboot", "terminal")
        for case in boundary_cases:
            with self.subTest(case=case):
                self._restore_roots()
                self.setUp()
                model, session = self.fixture()
                boundary = model["session"]["expires_at"]
                preexpiry = boundary - 1
                self.set_now(preexpiry)
                context = self.module.validate_chain(now=preexpiry)
                if case == "baseline":
                    baseline, _entry = self.module.model_roundtrip_pair(context)
                    baseline["issued_at"] = boundary
                    self.module.durable_json(
                        session / "baseline-000001.json", baseline
                    )
                elif case == "entry":
                    baseline, entry = self.module.model_roundtrip_pair(context)
                    self.module.durable_json(
                        session / "baseline-000001.json", baseline
                    )
                    entry["issued_at"] = boundary
                    self.module.durable_json(session / "entry-000001.json", entry)
                elif case == "reboot":
                    reboot = self.module.model_entry_node(context, "reboot-system")
                    reboot["issued_at"] = boundary
                    self.module.durable_json(session / "reboot-000001.json", reboot)
                else:
                    self.publish_entry_arrival_return(model, session)
                    terminal = self.module.model_terminal_node(
                        self.module.validate_chain(now=preexpiry)
                    )
                    terminal["issued_at"] = boundary
                    self.module.durable_json(session / "terminal.json", terminal)
                with self.assertRaisesRegex(
                    self.module.CoordinatorError, "after expiry"
                ):
                    self.set_now(boundary)
                    self.module.validate_chain(now=boundary)

    def test_terminal_cut_is_pre_f1_only(self):
        model, session = self.fixture()
        context = self.publish_entry_arrival_return(model, session)
        self.module.durable_json(session / "terminal.json", self.module.model_terminal_node(context))
        terminal = self.module.validate_chain(now=101)
        self.assertEqual(terminal["phase"], "READY_FOR_ATTENDED_F1")
        self.assertFalse(terminal["f1_intent"])
        self.assertFalse(terminal["approval_consumed"])
        self.assertFalse(terminal["partition_transfer"])
        self.module.CAMPAIGN_GUARD_PATH.unlink()
        cut = self.module.terminal_guard_state()
        self.assertTrue(cut["terminal_present"])
        self.assertFalse(cut["guard_present"])
        self.assertFalse(cut["authority"])
        self.assertFalse(cut["terminal_certified"])
        self.assertTrue(cut["no_device_commands"])

        # A forged standalone terminal is still only presence, never a
        # certified readiness result once the guard is gone.
        terminal_path = session / "terminal.json"
        terminal_path.unlink()
        terminal_path.write_bytes(b'{"verdict":"READY_FOR_ATTENDED_F1"}\n')
        os.chmod(terminal_path, 0o400)
        forged_cut = self.module.terminal_guard_state()
        self.assertTrue(forged_cut["terminal_present"])
        self.assertFalse(forged_cut["terminal_certified"])
        self.assertFalse(forged_cut["authority"])

    def test_budget_edge_reserves_return_and_blocks_reboot(self):
        cases = (
            (self.module.LIMITS, 8, 7, 7, 8),
            (self.module.CAMPAIGN_LIMITS, 32, 31, 31, 32),
        )
        for limits, reject_roundtrips, reject_reboots, roundtrips, reboots in cases:
            counters = {
                "control_transactions": reject_roundtrips + reject_reboots,
                "component_effects_consumed": reject_roundtrips * 2 + reject_reboots,
                "component_effects_reserved": 0,
                "normal_reboots": reject_reboots,
                "download_roundtrips": reject_roundtrips,
                "roundtrip_entries": reject_roundtrips,
                "roundtrip_returns": reject_roundtrips,
            }
            with self.assertRaisesRegex(self.module.CoordinatorError, "budget"):
                self.module.debit_before_intent(
                    counters, "download-roundtrip", "entry", limits
                )
            counters = {
                "control_transactions": roundtrips + reboots,
                "component_effects_consumed": roundtrips * 2 + reboots,
                "component_effects_reserved": 0,
                "normal_reboots": reboots,
                "download_roundtrips": roundtrips,
                "roundtrip_entries": roundtrips,
                "roundtrip_returns": roundtrips,
            }
            entry = self.module.debit_before_intent(
                counters, "download-roundtrip", "entry", limits
            )
            with self.assertRaisesRegex(self.module.CoordinatorError, "unresolved"):
                self.module.debit_before_intent(
                    entry, "reboot-system", "reboot", limits
                )
            returned = self.module.debit_before_intent(
                entry, "download-roundtrip", "return", limits
            )
            self.assertEqual(returned["component_effects_reserved"], 0)

    def test_source_drift_and_foreign_guard_are_fail_closed(self):
        model, _ = self.fixture()
        guard, _ = self.module.read_exact_json(
            self.module.CAMPAIGN_GUARD_PATH, "guard"
        )
        guard["policy_binding_sha256"] = "f" * 64
        self.module.CAMPAIGN_GUARD_PATH.unlink()
        self.module.durable_json(self.module.CAMPAIGN_GUARD_PATH, guard)
        with self.assertRaisesRegex(self.module.CoordinatorError, "foreign|stale"):
            self.module.validate_chain(now=101)

    def test_foreign_guard_or_campaign_namespace_has_zero_authority(self):
        model, _ = self.fixture()
        foreign_guard = self.root / "foreign-guard.json"
        foreign_guard.write_bytes(b"{}\n")
        os.chmod(foreign_guard, 0o400)
        with self.assertRaisesRegex(self.module.CoordinatorError, "foreign"):
            self.module.validate_chain(now=101)

        foreign_guard.unlink()
        foreign_campaign = self.root / "campaigns" / ("f" * 32)
        foreign_campaign.mkdir()
        os.chmod(foreign_campaign, 0o700)
        with self.assertRaisesRegex(self.module.CoordinatorError, "foreign"):
            self.module.validate_chain(now=101)

    def test_report_records_inactive_h0_boundary(self):
        report = REPORT.read_text(encoding="utf-8")
        self.assertIn("H0 PASS_GO_NOT_ACTIVE", report)
        self.assertIn("not a mechanically activatable", report)
        self.assertIn("fixed reboot/return backend", report)
        self.assertIn("53/53", report)
        self.assertIn("strict integer `issued_at`", report)
        self.assertIn("cached-context backdating", report)
        self.assertIn("clock/chain check immediately before atomic", report)
        self.assertIn("immutable", report)
        self.assertIn("Guardless opening files", report)
        self.assertIn("COORDINATOR_ACTIVE=False", report)
        self.assertIn(
            "opening -> session -> baseline-N -> entry-N -> arrival-N -> return-N",
            report,
        )
        self.assertIn(str(SCRIPT.relative_to(ROOT)), report)


if __name__ == "__main__":
    unittest.main()
