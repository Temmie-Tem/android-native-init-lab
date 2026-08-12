"""Static closure tests for the A90 H15 read-only UFS handoff."""

from __future__ import annotations

from pathlib import Path
import argparse
import ast
import copy
import hashlib
import json
import sys
import tempfile
import tomllib
import unittest
from unittest import mock

from _loader import load_script


REPO_ROOT = Path(__file__).resolve().parents[1]
NATIVE = REPO_ROOT / "workspace/public/src/native-init"
VERSIONS = (
    REPO_ROOT
    / "workspace/public/src/scripts/revalidation/a90_flat_builder/versions"
)
H15_MANIFEST = VERSIONS / "phase3-minimal-h15/manifest.toml"
H13_MANIFEST = VERSIONS / "phase3-minimal-h13/manifest.toml"
H15_CONTENT = VERSIONS / "phase3-minimal-h14/userdata-content-manifest.json"
H15_F1_RUNNER = (
    REPO_ROOT
    / "workspace/public/src/scripts/server-distro/a90_h15_ufs_f1_runner_v1.py"
)
H15_D1_RUNNER = (
    REPO_ROOT
    / "workspace/public/src/scripts/server-distro/a90_h15_ufs_d1_runner_v1.py"
)
TARGET_CONTRACT = REPO_ROOT / "docs/operations/targets/A90_TARGET_CONTRACT.md"
FLAT_BUILDER = load_script(
    "workspace/public/src/scripts/revalidation/a90_flat_builder/build.py"
)
BUILDLIB = load_script(
    "workspace/public/src/scripts/revalidation/a90_flat_builder/buildlib.py"
)
H15_F1 = load_script(
    "workspace/public/src/scripts/server-distro/a90_h15_ufs_f1_runner_v1.py"
)
H15_D1 = load_script(
    "workspace/public/src/scripts/server-distro/a90_h15_ufs_d1_runner_v1.py"
)


class A90UfsHandoffSourceV1Tests(unittest.TestCase):
    def _manifest(self, path: Path) -> dict[str, object]:
        return BUILDLIB.resolve_manifest(path).data

    def _f1_live_args(self) -> argparse.Namespace:
        return argparse.Namespace(
            operator_attended=True,
            bridge_host="127.0.0.1",
            bridge_port=54321,
            bridge_timeout=180.0,
            remote_timeout=180.0,
            flash_command_timeout=900.0,
            ssh_connect_timeout=8.0,
            poll_interval=3.0,
            transfer_timeout=1200.0,
        )

    def _run_reconcile_fault(
        self,
        records: list[dict[str, object]],
        *,
        candidate_health: object = None,
        starting_health: object = None,
        reconstructed: dict[str, object] | None = None,
    ) -> tuple[list[str], BaseException | None]:
        manifest = {"run_id": "a90-h15-ufs-f1-20260810-99"}
        appended: list[str] = []

        def append_record(
            _journal: Path,
            _manifest: dict[str, object],
            _manifest_sha: str,
            action: str,
            payload: dict[str, object],
        ) -> dict[str, object]:
            value = {"action": action, **payload}
            records.append(value)
            appended.append(action)
            return value

        if isinstance(candidate_health, BaseException):
            candidate_effect = candidate_health
        else:
            candidate_effect = candidate_health or {"candidate": "healthy"}
        if isinstance(starting_health, BaseException):
            starting_effect = starting_health
        else:
            starting_effect = starting_health or {"starting": "healthy"}
        with tempfile.TemporaryDirectory() as raw, mock.patch.multiple(
            H15_F1,
            load_manifest=mock.DEFAULT,
            _spec=mock.DEFAULT,
            _journal_dir=mock.DEFAULT,
            read_journal=mock.DEFAULT,
            require_consumed_approval=mock.DEFAULT,
            append_journal=mock.DEFAULT,
            exact_candidate_health=mock.DEFAULT,
            _reconstructed_flash_record=mock.DEFAULT,
        ) as patched, mock.patch.object(
            H15_F1.staging,
            "require_native_health",
            side_effect=starting_effect
            if isinstance(starting_effect, BaseException)
            else None,
            return_value=None
            if isinstance(starting_effect, BaseException)
            else starting_effect,
        ):
            patched["load_manifest"].return_value = manifest
            patched["_spec"].return_value = object()
            patched["_journal_dir"].return_value = Path(raw) / "journal"
            patched["read_journal"].side_effect = lambda *_args: list(records)
            patched["require_consumed_approval"].return_value = records[0]
            patched["append_journal"].side_effect = append_record
            if isinstance(candidate_effect, BaseException):
                patched["exact_candidate_health"].side_effect = candidate_effect
            else:
                patched["exact_candidate_health"].return_value = candidate_effect
            patched["_reconstructed_flash_record"].return_value = reconstructed or {
                "returncode": -1,
                "phase_classification": {"boot_write_started": True},
            }
            try:
                H15_F1.reconcile_health(
                    Path(raw) / "manifest.json",
                    "a" * 64,
                    self._f1_live_args(),
                )
            except H15_F1.ContractError as exc:
                return appended, exc
        return appended, None

    def test_h15_compiled_binding_is_userdata_v3_without_sd_image(self) -> None:
        h15 = self._manifest(H15_MANIFEST)
        binding = FLAT_BUILDER.normalized_auto_handoff_binding(h15)

        self.assertEqual(
            binding,
            {
                "candidate_version": "0.11.183",
                "candidate_build": (
                    "phase3-minimal-h15-direct-ufs-ro-async-wifi-auto-benchmark"
                ),
                "enable_path": (
                    "/cache/a90-auto-handoff-phase3-minimal-h15.enable"
                ),
                "latch_path": "/cache/a90-auto-handoff-phase3-minimal-h15.done",
                "schema": "a90-compiled-auto-handoff-binding-v3",
                "root_kind": "userdata-ext4-ro-noload",
                "userdata_devname": "sda33",
                "userdata_dev": "259:17",
                "userdata_sectors": "231577432",
                "userdata_label": "A90D4ROOT",
                "userdata_marker": "userdata=appliance-root",
                "userdata_uuid": "300aaf21-412c-4238-9106-56414eaab105",
                "userdata_content_manifest": (
                    "workspace/public/src/scripts/revalidation/a90_flat_builder/"
                    "versions/phase3-minimal-h14/userdata-content-manifest.json"
                ),
                "userdata_content_manifest_file_sha256": (
                    "a878f6dec82bf799c3d2cd43beeda3c5494a8882ce116327f497d822b707d5ce"
                ),
                "userdata_content_manifest_sha256": (
                    "e1950058627446d6bbd487d6a17b80f5766be4956b54cb56659b541dab09f8f6"
                ),
                "binding_sha256": binding["binding_sha256"],
            },
        )
        flags = h15["init"]["cflags"]
        self.assertFalse(any("AUTO_HANDOFF_IMAGE" in flag for flag in flags))
        self.assertFalse(any("SOURCE_RECEIPT_PATH" in flag for flag in flags))

    def test_h15_retains_h13_minimal_and_wifi_components(self) -> None:
        h15 = self._manifest(H15_MANIFEST)
        h13 = self._manifest(H13_MANIFEST)

        self.assertEqual(h15["init"]["sources"], h13["init"]["sources"])
        self.assertEqual(h15["helper"], h13["helper"])
        self.assertEqual(h15["ramdisk"], h13["ramdisk"])
        self.assertFalse(h15["candidate_authority"])
        init_root = REPO_ROOT / h15["init"]["source_root"]
        closure = BUILDLIB.expanded_closure(
            init_root,
            h15["init"]["sources"],
            h15["init"]["closure_globs"],
        )
        # H15 is historical. Later native safety work must invalidate its pin
        # instead of silently requalifying the old candidate.
        self.assertNotEqual(
            BUILDLIB.closure_sha256(init_root, closure),
            h15["init"]["closure_sha256"],
        )

    def test_h15_unarmed_boot_skips_wifi_and_armed_wifi_is_asynchronous(self) -> None:
        main = (NATIVE / "v724/90_main.inc.c").read_text(encoding="utf-8")
        direct = main[
            main.index("int direct_dispatch_state;"):
            main.index("if (a90_reloaded) {", main.index("int direct_dispatch_state;"))
        ]
        self.assertLess(
            direct.index("a90_auto_handoff_dispatch_state()"),
            direct.index("v1393_run_wifi_test_boot_once()"),
        )
        self.assertIn("if (direct_dispatch_state <= 0)", direct)
        self.assertIn("a90_auto_handoff_run_once()", direct)
        self.assertIn("v1393_require_persistent_handoff_started()", direct)
        self.assertIn("v1393_stop_persistent_handoff_helper()", direct)
        self.assertIn('"native_wifi_companion_async_started"', direct)
        self.assertNotIn("v1393_wait_persistent_handoff_ready", main)
        self.assertNotIn("v1393_stop_unready_persistent_helper", main)

        namespace = main[
            main.index("static int v1393_persistent_handoff_mounts_private("):
            main.index("static int v1393_require_persistent_handoff_started(")
        ]
        for required in (
            "waitpid(helper_pid, &status, WNOHANG)",
            '"/proc/%ld/exe"',
            "A90_V1393_WIFI_TEST_HELPER",
            '"/proc/self/ns/mnt"',
            '"/proc/%ld/ns/mnt"',
            '"/proc/self/ns/net"',
            '"/proc/%ld/ns/net"',
            '"/proc/%ld/mountinfo"',
            'strstr(buffer, " shared:")',
            'strstr(buffer, " master:")',
        ):
            self.assertIn(required, namespace)
        require = main[
            main.index("static int v1393_require_persistent_handoff_started("):
            main.index("static void v1393_stop_persistent_handoff_helper(")
        ]
        self.assertIn("started_ms + 5000L", require)
        self.assertIn("v1393_persistent_handoff_namespace_ready(", require)

        auto = (NATIVE / "a90_auto_handoff.c").read_text(encoding="utf-8")
        state = auto[
            auto.index("int a90_auto_handoff_dispatch_state(void)"):
            auto.index("int a90_auto_handoff_arm_cmd(")
        ]
        self.assertLess(
            state.index("a90_auto_handoff_state_path(A90_AUTO_HANDOFF_LATCH_PATH)"),
            state.index("a90_auto_handoff_read_enable("),
        )
        self.assertIn("return enable_state == 1 ? 1 : 0", state)

    def test_h15_replacement_identity_and_h14_rollback_predecessor_are_exact(self) -> None:
        h15 = self._manifest(H15_MANIFEST)
        flags = h15["init"]["cflags"]
        for required in (
            '-DINIT_VERSION="0.11.183"',
            '-DINIT_BUILD="phase3-minimal-h15-direct-ufs-ro-async-wifi-auto-benchmark"',
            '-DA90_AUTO_HANDOFF_ENABLE_PATH="/cache/a90-auto-handoff-phase3-minimal-h15.enable"',
            '-DA90_AUTO_HANDOFF_LATCH_PATH="/cache/a90-auto-handoff-phase3-minimal-h15.done"',
            '-DA90_WIFI_TEST_BOOT_LABEL="v2810"',
        ):
            self.assertIn(required, flags)
        source = H15_F1_RUNNER.read_text(encoding="utf-8")
        for required in (
            'CURRENT_VERSION = "0.9.285"',
            'CURRENT_BUILD = "v2321-usb-clean-identity-rodata"',
            'result.get("schema") != "a90-h14-ufs-f1-result-v1"',
            '"FAILED_CANDIDATE_RECOVERY_ROLLBACK_COMPLETE"',
            'result.get("rollback_transfer_count") != 1',
            'result.get("candidate_transfer_count") is not None',
        ):
            self.assertIn(required, source)

    def test_userdata_binding_rejects_sd_fields_and_identity_drift(self) -> None:
        h15 = self._manifest(H15_MANIFEST)
        with_image = copy.deepcopy(h15)
        with_image["init"]["cflags"].append(
            '-DA90_AUTO_HANDOFF_IMAGE="/mnt/sdext/a90/runtime/forbidden.img"'
        )
        with self.assertRaisesRegex(RuntimeError, "userdata tuple"):
            FLAT_BUILDER.normalized_auto_handoff_binding(with_image)

        drifted = copy.deepcopy(h15)
        flags = drifted["init"]["cflags"]
        index = flags.index('-DA90_AUTO_HANDOFF_USERDATA_DEV="259:17"')
        flags[index] = '-DA90_AUTO_HANDOFF_USERDATA_DEV="259:18"'
        with self.assertRaisesRegex(RuntimeError, "userdata tuple"):
            FLAT_BUILDER.normalized_auto_handoff_binding(drifted)

        for conflicting in (
            "-DA90_AUTO_HANDOFF_USERDATA_ROOT_V1=0",
            "-UA90_AUTO_HANDOFF_USERDATA_ROOT_V1",
            '-DA90_AUTO_HANDOFF_USERDATA_DEV="259:18"',
            "-UA90_AUTO_HANDOFF_USERDATA_DEV",
            '-DA90_AUTO_HANDOFF_USERDATA_UUID="00000000-0000-0000-0000-000000000000"',
            '-DA90_AUTO_HANDOFF_USERDATA_CONTENT_MANIFEST_SHA256="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"',
        ):
            ambiguous = copy.deepcopy(h15)
            ambiguous["init"]["cflags"].append(conflicting)
            with self.subTest(conflicting=conflicting):
                with self.assertRaisesRegex(RuntimeError, "conflicting"):
                    FLAT_BUILDER.normalized_auto_handoff_binding(ambiguous)

    def test_legacy_binding_rejects_hidden_userdata_or_macro_override(self) -> None:
        h13 = self._manifest(H13_MANIFEST)
        for conflicting in (
            "-DA90_AUTO_HANDOFF_BENCHMARK_V1=0",
            "-UA90_AUTO_HANDOFF_BENCHMARK_V1",
            '-DA90_AUTO_HANDOFF_IMAGE="/mnt/sdext/a90/runtime/other.img"',
            '-DA90_AUTO_HANDOFF_USERDATA_DEVNAME="sda33"',
        ):
            ambiguous = copy.deepcopy(h13)
            ambiguous["init"]["cflags"].append(conflicting)
            with self.subTest(conflicting=conflicting):
                with self.assertRaisesRegex(RuntimeError, "conflicting|canonical"):
                    FLAT_BUILDER.normalized_auto_handoff_binding(ambiguous)

    def test_h13_sd_binding_remains_v2(self) -> None:
        binding = FLAT_BUILDER.normalized_auto_handoff_binding(
            self._manifest(H13_MANIFEST)
        )
        self.assertEqual(binding["schema"], "a90-compiled-auto-handoff-binding-v2")
        self.assertIn("image_path", binding)
        self.assertIn("image_sha256", binding)
        self.assertIn("receipt_path", binding)
        self.assertNotIn("root_kind", binding)
        source = (NATIVE / "a90_auto_handoff.c").read_text(encoding="utf-8")
        self.assertIn(
            'A90AUTO state=dispatch-once latch=%s image=%s\\r\\n',
            source,
        )
        self.assertIn(
            'A90AUTO state=dispatch-once latch=%s root=%s\\r\\n',
            source,
        )

    def test_auto_handoff_qualifies_before_arm_and_boot_latch(self) -> None:
        source = (NATIVE / "a90_auto_handoff.c").read_text(encoding="utf-8")
        arm = source[
            source.index("int a90_auto_handoff_arm_cmd("):
            source.index("static int a90_auto_handoff_mkdir_evidence_dir(")
        ]
        run = source[
            source.index("int a90_auto_handoff_run_once(void)"):
            source.index("\n#else\n\nint a90_auto_handoff_status_cmd", source.index("int a90_auto_handoff_run_once(void)"))
        ]

        self.assertLess(
            arm.index("a90_server_distro_userdata_ro_qualify("),
            arm.index("a90_auto_handoff_create_enable("),
        )
        self.assertLess(
            run.index("a90_server_distro_userdata_ro_qualify("),
            run.index("a90_auto_handoff_create_latch("),
        )
        self.assertLess(
            run.index("a90_auto_handoff_create_latch("),
            run.index("a90_server_distro_switch_root_userdata_ro("),
        )
        self.assertIn("root_kind=userdata-ext4-ro-noload", source)
        self.assertIn("a90-auto-handoff-userdata-ro-v1", source)

    def test_qualification_is_exact_read_only_no_replay_and_unmounted(self) -> None:
        source = (NATIVE / "a90_server_distro.c").read_text(encoding="utf-8")
        qualify = source[
            source.index("int a90_server_distro_userdata_ro_qualify("):
            source.index("int a90_server_distro_switch_root_userdata_ro(")
        ]
        static = source[
            source.index("static int d4_userdata_ro_static_preflight("):
            source.index("static int d4_mount_userdata_readonly_no_replay(")
        ]
        mount = source[
            source.index("static int d4_mount_userdata_readonly_no_replay("):
            source.index("static int d4_userdata_ro_check_marker(")
        ]

        for token in (
            "d4_resolve_userdata(&target)",
            "d4_compare_ro_expected(&target",
            "d4_check_ext4_magic_phase(A90_D4_NODE, phase)",
            "d4_check_ext_has_journal(A90_D4_NODE, phase)",
            "d4_check_ext4_clean_no_recovery(A90_D4_NODE, phase)",
            "d4_check_ext4_label(A90_D4_NODE, expected_label, phase)",
            "d4_check_ext4_uuid(A90_D4_NODE, expected_uuid, phase)",
        ):
            self.assertIn(token, static)
        self.assertIn("MS_RDONLY | MS_NOSUID | MS_NODEV", mount)
        self.assertIn('"noload"', mount)
        self.assertIn("(fs.f_flag & ST_RDONLY) == 0", mount)
        self.assertIn("userdata_write=0", mount)
        self.assertLess(
            qualify.index("d4_userdata_ro_check_root(expected_marker,"),
            qualify.index("umount2(A90_D3_ROOT, MNT_DETACH)"),
        )
        self.assertGreaterEqual(
            qualify.count("d4_userdata_ro_static_preflight("),
            2,
        )
        self.assertNotIn("format", qualify)
        self.assertNotIn("populate", qualify)
        self.assertNotIn("fsck", qualify)

    def test_marker_and_content_checks_are_exact_and_secret_safe(self) -> None:
        source = (NATIVE / "a90_server_distro.c").read_text(encoding="utf-8")
        content = json.loads(H15_CONTENT.read_text(encoding="utf-8"))
        encoded = json.dumps(
            content,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        self.assertEqual(
            hashlib.sha256(H15_CONTENT.read_bytes()).hexdigest(),
            "a878f6dec82bf799c3d2cd43beeda3c5494a8882ce116327f497d822b707d5ce",
        )
        self.assertEqual(
            hashlib.sha256(encoded).hexdigest(),
            "e1950058627446d6bbd487d6a17b80f5766be4956b54cb56659b541dab09f8f6",
        )
        self.assertEqual(len(content["files"]), 19)
        marker = source[
            source.index("static int d4_userdata_ro_check_marker("):
            source.index("static int d4_userdata_ro_hash_fd(")
        ]
        checker = source[
            source.index("static int d4_userdata_ro_hash_fd("):
            source.index("int a90_server_distro_userdata_ro_qualify(")
        ]

        self.assertIn("lstat(path, &before)", marker)
        self.assertIn("O_RDONLY | O_CLOEXEC | O_NOFOLLOW", marker)
        self.assertIn("memcmp(content, expected, expected_size) != 0", marker)
        for record in content["files"]:
            self.assertIn(record["path"].lstrip("/"), source)
            self.assertIn(record["sha256"], source)
            if record["kind"] == "symlink":
                self.assertIn(record["link_target"], source)
        self.assertIn("d4_userdata_ro_hash_fd", checker)
        self.assertIn("O_NOFOLLOW", checker)
        self.assertIn("after.st_ino != before.st_ino", checker)
        self.assertIn('"root/.ssh/authorized_keys"', checker)
        self.assertIn("secrets_hashed=0", checker)
        for path in content["absent"]:
            self.assertIn(path.lstrip("/"), checker)

    def test_builder_proves_compiled_content_table_equals_json_semantics(self) -> None:
        content = json.loads(H15_CONTENT.read_text(encoding="utf-8"))
        self.assertEqual(
            FLAT_BUILDER._userdata_runtime_records(REPO_ROOT),
            content["files"],
        )

    def test_ext4_uuid_is_read_from_superblock_and_bound(self) -> None:
        source = (NATIVE / "a90_server_distro.c").read_text(encoding="utf-8")
        check = source[
            source.index("static int d4_check_ext4_uuid("):
            source.index("static int d4_marker_clean(")
        ]
        self.assertIn("A90_D4_EXT_UUID_OFFSET", check)
        self.assertIn("O_RDONLY | O_CLOEXEC | O_NOFOLLOW", check)
        self.assertIn("memcmp(observed, expected, sizeof(observed))", check)
        self.assertIn("300aaf21-412c-4238-9106-56414eaab105", source)

    def test_handoff_revalidates_identity_and_preserves_modern_closure(self) -> None:
        source = (NATIVE / "a90_server_distro.c").read_text(encoding="utf-8")
        handoff = source[
            source.index("int a90_server_distro_switch_root_userdata_ro("):
            source.index("static int d4_dpublic_hud_bind_target(")
        ]
        ordered = (
            '"userdata_identity_initial_done"',
            "d3_handoff_stop_display_owners_strict()",
            '"userdata_identity_post_display_done"',
            "d4_mount_userdata_readonly_no_replay()",
            "d4_userdata_ro_check_root(expected_marker,",
            "d3_mount_writable_set(&writable_mounted)",
            "d3_verify_writable_set()",
            "d3_bind_evidence_dir(&evidence_bound)",
            "d3_bind_wifi_handoff_dir(&wifi_handoff_bound)",
            "d3_move_core_mounts(true,",
            'a90_benchmark_mark("switch_root_exec")',
            "execve(A90_D3_BUSYBOX, switch_argv, newenv)",
        )
        positions = [handoff.index(token) for token in ordered]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("umount2(A90_D3_ROOT, MNT_DETACH)", handoff)
        self.assertIn("int restore_rc = d3_restore_core_mounts(", handoff)
        self.assertIn("cleanup_clean = false;", handoff)
        self.assertIn("rootfs=retained-after-restore-fail", handoff)
        self.assertIn("private_dev=ok userdata_node_exposed=0", source)
        self.assertIn('"dev/block/a90-userdata"', source)
        self.assertIn('"userdata-ro-after-failure"', handoff)
        self.assertIn("userdata_unchanged_after_failure=1 userdata_write=0", handoff)
        self.assertNotIn("d3_attach_loop", handoff)
        self.assertNotIn("d3_verify_source_sha_fd", handoff)
        self.assertNotIn("d4_write_marker", handoff)
        self.assertNotIn("userdata-appliance-format", handoff)
        self.assertNotIn("userdata-appliance-populate", handoff)

    def test_h15_f1_runner_has_no_sd_rootfs_effect_lane(self) -> None:
        source = H15_F1_RUNNER.read_text(encoding="utf-8")
        execute = source[
            source.index("def execute("):
            source.index("def audit(")
        ]
        intent = execute.index('"candidate-intent"')
        flash = execute.index("record = _flash_record(")

        self.assertLess(intent, flash)
        self.assertIn('"candidate_attempt_limit": 1', execute)
        self.assertIn('"candidate_replay": False', execute)
        self.assertIn('"partition": "boot"', execute)
        self.assertIn('"rootfs_payload_count": 0', execute)
        self.assertIn('"sd_stage_count": 0', execute)
        self.assertIn('"userdata_write_count": 0', execute)
        self.assertNotIn("stage_command(", source)
        self.assertNotIn("validate_stage_result(", source)
        self.assertNotIn("execute-approved-stage", source)
        self.assertNotIn("payload-transfer-start", source)
        self.assertIn("candidate_failure_is_definite_pre_session", execute)
        self.assertIn("rollback launch already exists; effect replay refused", source)
        reconciliation = source[
            source.index("def reconcile_health("):
            source.index("def execute(")
        ]
        self.assertIn("never flash again", reconciliation)
        self.assertIn("reconciled_without_effect_replay", reconciliation)
        self.assertNotIn("record = _flash_record(", reconciliation)
        self.assertNotIn("_rollback(", reconciliation)

    def test_h15_f1_runner_binds_reusable_capability_review(self) -> None:
        source = H15_F1_RUNNER.read_text(encoding="utf-8")
        qualification = source[
            source.index("def validate_qualification("):
            source.index("def validate_ufs_inventory(")
        ]
        self.assertIn('value.get("verdict") != "PASS_GO"', qualification)
        self.assertIn(
            'value.get("execution_closure_sha256") != closure["sha256"]',
            qualification,
        )
        self.assertIn('value.get("execution_hashes") != closure["files"]', qualification)
        self.assertIn(
            'value.get("ordinal_requalification_required") is not False',
            qualification,
        )

    def test_h15_f1_closure_covers_transitive_local_imports(self) -> None:
        closure = set(H15_F1.EXECUTION_SOURCE_RELS)
        local_roots = (
            REPO_ROOT / "workspace/public/src/scripts/server-distro",
            REPO_ROOT / "workspace/public/src/scripts/revalidation",
            REPO_ROOT / "workspace/public/src/scripts/revalidation/a90_flat_builder",
        )
        by_module: dict[str, list[str]] = {}
        for root in local_roots:
            for path in root.glob("*.py"):
                relative = str(path.relative_to(REPO_ROOT))
                by_module.setdefault(path.stem, []).append(relative)
        missing: list[tuple[str, str]] = []
        for relative in sorted(item for item in closure if item.endswith(".py")):
            tree = ast.parse((REPO_ROOT / relative).read_text(encoding="utf-8"))
            imported: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported.update(alias.name.split(".", 1)[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported.add(node.module.split(".", 1)[0])
                    imported.update(alias.name for alias in node.names)
            for name in imported:
                candidates = by_module.get(name, [])
                if len(candidates) == 1 and candidates[0] not in closure:
                    missing.append((relative, candidates[0]))
        self.assertEqual(missing, [])

    def test_h15_execution_closure_fails_closed_after_native_lineage_changes(self) -> None:
        with self.assertRaisesRegex(
            H15_F1.ContractError,
            "H15 native transitive closure changed",
        ):
            H15_F1.execution_closure()
        source = H15_F1_RUNNER.read_text(encoding="utf-8")
        self.assertIn("lineage != expected_lineage", source)
        self.assertIn("for path in resolution.lineage", source)

    def test_h15_flash_timeout_quiesces_descendant_process_group(self) -> None:
        manifest = {
            "run_id": "a90-h15-ufs-f1-20260810-99",
            "candidate_boot": {"size": 1, "sha256": "1" * 64},
            "rollback_boot": {"size": 1, "sha256": "2" * 64},
            "flash_runner": {"sha256": "3" * 64},
        }
        manifest_sha = "4" * 64
        args = argparse.Namespace(flash_command_timeout=0.2)
        command = [
            sys.executable,
            "-c",
            (
                "import subprocess,time; "
                "subprocess.Popen(['sleep','30']); time.sleep(30)"
            ),
        ]
        with tempfile.TemporaryDirectory() as raw:
            transaction = Path(raw)
            journal = transaction / "journal"
            with mock.patch.object(
                H15_F1.base,
                "flash_command",
                return_value=command,
            ):
                record = H15_F1._flash_record(  # noqa: SLF001
                    manifest,
                    manifest_sha,
                    None,
                    args,
                    journal,
                    transaction,
                    rollback=False,
                    from_native=True,
                )
            self.assertEqual(record["returncode"], 124)
            self.assertTrue(record["process_group"]["timed_out"])
            self.assertTrue(record["process_group"]["quiesced"])
            pgid = record["process_group"]["pgid"]
            self.assertEqual(H15_F1._process_group_members(pgid), [])  # noqa: SLF001
            records = H15_F1.read_journal(journal, manifest, manifest_sha)
            self.assertEqual([item["action"] for item in records], ["candidate-launch"])
            self.assertEqual(
                records[0]["launch"],
                json.loads(
                    (transaction / "candidate-flash-launch.json").read_text(
                        encoding="utf-8"
                    )
                ),
            )

    def test_h15_f1_load_binds_exact_target_and_recovery_predecessor(self) -> None:
        source = H15_F1_RUNNER.read_text(encoding="utf-8")
        loader = source[
            source.index("def load_manifest("):
            source.index("def _stage_view(")
        ]
        for token in (
            'set(target) != expected_target_keys',
            'target.get("profile") != predecessor_target.get("profile")',
            'target.get("bridge_device") != predecessor_target.get("bridge_device")',
            'target.get("current_version") != CURRENT_VERSION',
            'target.get("recovery_adb_identity_evidence")',
            '!= predecessor_target.get("recovery_adb_identity_evidence")',
        ):
            self.assertIn(token, loader)

    def test_h15_d1_runner_is_one_arm_one_reboot_no_payload(self) -> None:
        source = H15_D1_RUNNER.read_text(encoding="utf-8")
        execute = source[source.index("def execute("):source.index("def finalize_return(")]
        dispatch = source[
            source.index("def _dispatch_and_observe("):
            source.index("def execute(")
        ]
        self.assertLess(
            execute.index('"arm-reboot-intent"'),
            execute.index("_dispatch_and_observe("),
        )
        self.assertLess(dispatch.index("_arm_reboot_once("), dispatch.index('"dispatch-result"'))
        self.assertIn('"arm_reboot_command_dispatch_count_max": 1', execute)
        self.assertIn('"auto-handoff-arm-reboot"', source)
        self.assertIn('"candidate_replay": False', execute)
        self.assertIn('"payload_transfer_count": 0', source)
        self.assertIn('"partition_write_count": 0', source)
        self.assertIn('"flash_count": 0', source)
        self.assertIn('"sd_rootfs_stage_count": 0', source)
        self.assertIn('"userdata_write_count": 0', source)
        self.assertNotIn("stage_command(", source)
        self.assertNotIn("flash_command(", source)
        self.assertNotIn("send_reboot_once", source)
        self.assertIn("no replay; final native health decides safety", source)

    def test_h15_d1_finalize_paths_never_repeat_effects(self) -> None:
        source = H15_D1_RUNNER.read_text(encoding="utf-8")
        finalize = source[
            source.index("def finalize_return("):
            source.index("def reconcile(")
        ]
        self.assertIn("len(records) not in (2, 3, 4)", finalize)
        self.assertIn("result = _finalize(", finalize)
        self.assertIn("require_status(effect_args, enable=0, latch=0)", finalize)
        self.assertIn("require_pre_reboot_observer_binding_current(", finalize)
        self.assertNotIn("_arm_reboot_once(", finalize)
        self.assertNotIn("send_reboot_once", finalize)
        self.assertNotIn("_dispatch_and_observe(", finalize)

    def test_h15_native_combined_arm_reboot_cancels_every_syscall_return(self) -> None:
        source = (NATIVE / "a90_auto_handoff.c").read_text(encoding="utf-8")
        command = source[
            source.index("int a90_auto_handoff_arm_reboot_cmd("):
            source.index("static int a90_auto_handoff_mkdir_evidence_dir(")
        ]
        positions = [
            command.index("a90_auto_handoff_arm_cmd(argv, argc)"),
            command.index("reboot_rc = reboot(RB_AUTOBOOT)"),
            command.index("a90_auto_handoff_cancel_enable(argv[2])"),
        ]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("reboot_rc < 0 && errno != 0 ? errno : EIO", command)
        self.assertNotIn("if (reboot(RB_AUTOBOOT) == 0)", command)
        dispatch = (NATIVE / "v319/80_shell_dispatch.inc.c").read_text(
            encoding="utf-8"
        )
        self.assertIn('"auto-handoff-arm-reboot"', dispatch)
        self.assertIn("CMD_DANGEROUS | CMD_NO_DONE", dispatch)

    def test_h15_authority_binds_agents_and_requires_fresh_approval(self) -> None:
        self.assertIn("AGENTS.md", H15_F1.EXECUTION_SOURCE_RELS)
        f1_source = H15_F1_RUNNER.read_text(encoding="utf-8")
        d1_source = H15_D1_RUNNER.read_text(encoding="utf-8")
        for source, workflow, prefix in (
            (f1_source, "A90_F1_RESIDENT_INSTALL_V1", "A90-H15-F1-APPROVE:"),
            (d1_source, "A90_D1_ATTENDED_SESSION_V1", "A90-H15-D1-APPROVE:"),
        ):
            self.assertIn(workflow, source)
            self.assertIn(prefix, source)
            self.assertIn("trial-retired-fresh-approval-required", source)
            self.assertIn("approval_consumed", source)
            self.assertIn("agents_contract_sha256", source)
        self.assertIn('item.add_argument("--approval", required=True)', f1_source)
        self.assertIn("H15 D1 execute requires fresh exact approval", d1_source)

    def test_h15_f1_and_d1_approval_tokens_round_trip_exact_bindings(self) -> None:
        created = H15_F1.dt.datetime.now(H15_F1.dt.UTC).replace(microsecond=0)
        expires = created + H15_F1.dt.timedelta(seconds=H15_F1.APPROVAL_TTL_SEC)
        created_text = created.strftime("%Y-%m-%dT%H:%M:%SZ")
        expires_text = expires.strftime("%Y-%m-%dT%H:%M:%SZ")
        manifest = {
            "run_id": "a90-h15-ufs-f1-20260810-99",
            "execution_closure": {"sha256": "1" * 64},
            "target": {
                "profile": "galaxy-a90-5g-native-init",
                "bridge_device": H15_F1.EXACT_BRIDGE_DEVICE,
                "bridge_realpath": "/dev/ttyACM0",
                "recovery_adb_identity_evidence": {"exact": True},
            },
            "candidate_boot": {"sha256": "2" * 64, "size": 100},
            "rollback_boot": {"sha256": "3" * 64, "size": 200},
        }
        manifest_sha = "4" * 64
        f1_binding = H15_F1.approval_binding(
            manifest,
            manifest_sha,
            created_utc=created_text,
            expires_utc=expires_text,
        )
        f1_binding_sha = H15_F1.json_sha256(f1_binding)
        f1_token = H15_F1.APPROVAL_PREFIX + f1_binding_sha
        f1_value = {
            "schema": H15_F1.APPROVAL_SCHEMA,
            "run_id": manifest["run_id"],
            "manifest_sha256": manifest_sha,
            "approval_binding": f1_binding,
            "approval_binding_sha256": f1_binding_sha,
            "approval_token": f1_token,
            "device_contact": False,
            "device_write": False,
            "live_authority_from_preparation": False,
        }
        with tempfile.TemporaryDirectory() as raw:
            f1_path = Path(raw) / "f1-approval.json"
            H15_F1.write_json_exclusive(f1_path, f1_value)
            with mock.patch.object(H15_F1, "_approval_path", return_value=f1_path):
                approved = H15_F1.validate_approval(
                    manifest,
                    manifest_sha,
                    f1_token,
                )
            self.assertEqual(approved, f1_value)
            consumed = {
                "action": "approval-consumed",
                "approval_binding": f1_binding,
                "approval_binding_sha256": f1_binding_sha,
                "approval_token_sha256": hashlib.sha256(
                    f1_token.encode("utf-8")
                ).hexdigest(),
                "approval_consumed": True,
            }
            self.assertEqual(
                H15_F1.require_consumed_approval(
                    [consumed],
                    manifest,
                    manifest_sha,
                ),
                consumed,
            )

            d1_args = argparse.Namespace(
                expect_manifest_sha256=manifest_sha,
                expect_install_result_sha256="5" * 64,
                expect_execution_closure_sha256="1" * 64,
                approval=None,
            )
            transaction = Path(raw) / "ordinal-01"
            d1_binding = H15_D1.approval_binding(
                manifest,
                d1_args,
                transaction,
                created_utc=created_text,
                expires_utc=expires_text,
            )
            d1_binding_sha = H15_F1.json_sha256(d1_binding)
            d1_token = H15_D1.APPROVAL_PREFIX + d1_binding_sha
            d1_args.approval = d1_token
            d1_value = {
                "schema": H15_D1.APPROVAL_SCHEMA,
                "approval_binding": d1_binding,
                "approval_binding_sha256": d1_binding_sha,
                "approval_token": d1_token,
                "device_contact": False,
                "device_write": False,
                "live_authority_from_preparation": False,
            }
            d1_path = H15_D1._approval_path(transaction)  # noqa: SLF001
            H15_F1.write_json_exclusive(d1_path, d1_value)
            self.assertEqual(
                H15_D1.validate_approval(manifest, d1_args, transaction),
                d1_value,
            )

    def test_candidate_launch_result_gap_with_write_marker_parks_rollback(self) -> None:
        records: list[dict[str, object]] = [
            {"action": "approval-consumed"},
            {"action": "candidate-intent"},
            {"action": "candidate-launch"},
        ]
        appended, error = self._run_reconcile_fault(
            records,
            candidate_health=H15_F1.ContractError("candidate unavailable"),
            starting_health={"starting": "H11"},
            reconstructed={
                "returncode": -1,
                "phase_classification": {"boot_write_started": True},
            },
        )
        self.assertIsInstance(error, H15_F1.ContractError)
        self.assertEqual(appended, ["candidate-result", "recovery-required"])
        self.assertNotIn("closed", appended)

    def test_durable_uncertain_candidate_result_has_recovery_continuation(self) -> None:
        records: list[dict[str, object]] = [
            {"action": "approval-consumed"},
            {"action": "candidate-intent"},
            {"action": "candidate-launch"},
            {
                "action": "candidate-result",
                "candidate_transfer_count": None,
                "record": {
                    "returncode": -1,
                    "phase_classification": {"boot_write_started": True},
                },
            },
        ]
        appended, error = self._run_reconcile_fault(records)
        self.assertIsInstance(error, H15_F1.ContractError)
        self.assertEqual(appended, ["recovery-required"])
        self.assertNotIn("closed", appended)

    def test_candidate_success_result_health_gap_parks_rollback(self) -> None:
        records: list[dict[str, object]] = [
            {"action": "approval-consumed"},
            {"action": "candidate-intent"},
            {"action": "candidate-launch"},
            {
                "action": "candidate-result",
                "candidate_transfer_count": 1,
                "record": {"returncode": 0},
            },
        ]
        appended, error = self._run_reconcile_fault(
            records,
            candidate_health=H15_F1.ContractError("health unavailable"),
        )
        self.assertIsInstance(error, H15_F1.ContractError)
        self.assertEqual(appended, ["recovery-required"])
        self.assertNotIn("closed", appended)

    def test_rollback_intent_without_launch_never_closes_from_health(self) -> None:
        records: list[dict[str, object]] = [
            {"action": "approval-consumed"},
            {"action": "candidate-intent"},
            {"action": "candidate-launch"},
            {
                "action": "candidate-result",
                "candidate_transfer_count": None,
                "record": {
                    "returncode": -1,
                    "phase_classification": {"boot_write_started": True},
                },
            },
            {"action": "recovery-required"},
            {"action": "rollback-intent"},
        ]
        appended, error = self._run_reconcile_fault(records)
        self.assertIsInstance(error, H15_F1.ContractError)
        self.assertEqual(appended, [])
        self.assertNotIn("rollback-result", [item["action"] for item in records])

    def test_rollback_launch_result_gap_ambiguous_never_health_closes(self) -> None:
        records: list[dict[str, object]] = [
            {"action": "approval-consumed"},
            {"action": "candidate-intent"},
            {"action": "candidate-launch"},
            {
                "action": "candidate-result",
                "candidate_transfer_count": None,
                "record": {
                    "returncode": -1,
                    "phase_classification": {"boot_write_started": True},
                },
            },
            {"action": "recovery-required"},
            {"action": "rollback-intent"},
            {"action": "rollback-launch"},
        ]
        appended, error = self._run_reconcile_fault(
            records,
            reconstructed={
                "returncode": -1,
                "phase_classification": {"boot_write_started": True},
            },
        )
        self.assertIsInstance(error, H15_F1.ContractError)
        self.assertEqual(appended, ["rollback-result"])
        self.assertNotIn("rollback-health", appended)
        self.assertNotIn("closed", appended)

    def test_d1_cancellation_requires_same_intent_post_fsync_log(self) -> None:
        intent = "1" * 64
        opening = {"text": "[1ms] native: opening\n"}
        final = {
            "text": (
                "[1ms] native: opening\n"
                "[9ms] auto-handoff: reboot returned cancellation "
                f"intent_sha256={intent} reboot_errno=5 cancel_rc=0\n"
            )
        }
        with mock.patch.object(
            H15_D1.base,
            "require_exact_f1_command_receipt",
            side_effect=lambda record, *_args: record,
        ):
            proof = H15_D1.require_cancellation_fsync_proof(
                opening,
                final,
                intent,
            )
            self.assertTrue(proof["proof"])
            with self.assertRaisesRegex(
                H15_D1.ContractError,
                "cancellation fsync proof",
            ):
                H15_D1.require_cancellation_fsync_proof(
                    opening,
                    {"text": final["text"].replace("cancel_rc=0", "cancel_rc=-5")},
                    intent,
                )

    def test_d1_native_failure_requires_clean_restore_and_root_unmount(self) -> None:
        opening = {"text": "[1ms] native: opening\n"}
        safe = {
            "text": (
                "[1ms] native: opening\n"
                "[7ms] server-distro: D4 handoff failure cleanup_clean=1 "
                "root_mounted=0 recovery_required=0 userdata_unchanged=1 "
                "userdata_write=0\n"
            )
        }
        unsafe = {
            "text": safe["text"].replace(
                "cleanup_clean=1 root_mounted=0 recovery_required=0",
                "cleanup_clean=0 root_mounted=1 recovery_required=1",
            )
        }
        with mock.patch.object(
            H15_D1.base,
            "require_exact_f1_command_receipt",
            side_effect=lambda record, *_args: record,
        ):
            proof = H15_D1.native_failure_cleanup_disposition(
                opening,
                safe,
                native_handoff_failed=True,
            )
            self.assertTrue(proof["root_unmounted"])
            with self.assertRaisesRegex(
                H15_D1.ContractError,
                "recovery-pending",
            ):
                H15_D1.native_failure_cleanup_disposition(
                    opening,
                    unsafe,
                    native_handoff_failed=True,
                )

    def test_d1_finalize_return_proves_latched_state_before_publication(self) -> None:
        records = [
            {"opening_log": {"text": "opening"}},
            {"pre_reboot_binding": {"exact": True}},
        ]
        args = argparse.Namespace(
            operator_attended=True,
            transaction_dir=Path("/private/ordinal"),
            visible_confirmed="unavailable",
        )
        with mock.patch.multiple(
            H15_D1,
            load_inputs=mock.DEFAULT,
            _require_transaction_dir=mock.DEFAULT,
            _read_records=mock.DEFAULT,
            _validate_records=mock.DEFAULT,
            require_status=mock.DEFAULT,
            _write_record=mock.DEFAULT,
        ) as patched:
            patched["load_inputs"].return_value = ({"run_id": "r"}, object(), {})
            patched["_require_transaction_dir"].return_value = Path("/private/ordinal")
            patched["_read_records"].return_value = records
            patched["_validate_records"].return_value = "1" * 64
            patched["require_status"].side_effect = H15_D1.ContractError(
                "not latched"
            )
            with self.assertRaisesRegex(H15_D1.ContractError, "not latched"):
                H15_D1.finalize_return(args)
            patched["_write_record"].assert_not_called()

    def test_d1_durable_opening_requires_exact_log_receipt(self) -> None:
        args = argparse.Namespace(
            expect_manifest_sha256="1" * 64,
            expect_install_result_sha256="2" * 64,
            expect_execution_closure_sha256="3" * 64,
        )
        binding = {"created_utc": "2026-08-10T00:00:00Z"}
        opening = {
            "manifest_sha256": args.expect_manifest_sha256,
            "install_result_sha256": args.expect_install_result_sha256,
            "execution_closure_sha256": args.expect_execution_closure_sha256,
            "approval_consumed": True,
            "approval_binding": binding,
            "approval_binding_sha256": H15_F1.json_sha256(binding),
            "approval_token_sha256": "4" * 64,
            "candidate_replay": False,
            "payload_transfer_count": 0,
            "partition_write_count": 0,
            "userdata_write_count": 0,
        }
        with self.assertRaisesRegex(
            H15_D1.ContractError,
            "opening log is absent",
        ):
            H15_D1._validate_records(  # noqa: SLF001
                [opening],
                Path("/private/ordinal"),
                args,
                {},
            )

    def test_d1_reconcile_zero_zero_without_cancel_proof_stays_unknown(self) -> None:
        records = [
            {"opening_log": {"text": "opening"}},
            {"pre_reboot_binding": {"exact": True}},
        ]
        args = argparse.Namespace(transaction_dir=Path("/private/ordinal"))
        with mock.patch.multiple(
            H15_D1,
            load_inputs=mock.DEFAULT,
            _require_transaction_dir=mock.DEFAULT,
            _read_records=mock.DEFAULT,
            _validate_records=mock.DEFAULT,
            parse_status=mock.DEFAULT,
            require_cancellation_fsync_proof=mock.DEFAULT,
        ) as patched, mock.patch.object(
            H15_D1.base,
            "run_f1_cmd",
            return_value={"text": "record"},
        ), mock.patch.object(
            H15_D1.base,
            "verify_candidate_health",
            return_value={"healthy": True},
        ), mock.patch.object(
            H15_D1.f1,
            "sha256_file",
            return_value="1" * 64,
        ):
            patched["load_inputs"].return_value = ({"run_id": "r"}, object(), {})
            patched["_require_transaction_dir"].return_value = Path("/private/ordinal")
            patched["_read_records"].return_value = records
            patched["parse_status"].return_value = {
                "binding": 1,
                "enable": 0,
                "latch": 0,
                "build": H15_F1.CANDIDATE_BUILD,
            }
            patched["require_cancellation_fsync_proof"].side_effect = (
                H15_D1.ContractError("proof absent")
            )
            result = H15_D1.reconcile(args)
        self.assertEqual(
            result["terminal"],
            "ARM_REBOOT_DISPATCH_UNKNOWN_NO_REPLAY",
        )

    def test_d1_reconcile_missing_cleanup_evidence_parks_recovery(self) -> None:
        records = [
            {"opening_log": {"text": "opening"}},
            {"pre_reboot_binding": {"exact": True}},
        ]
        args = argparse.Namespace(transaction_dir=Path("/private/ordinal"))
        with mock.patch.multiple(
            H15_D1,
            load_inputs=mock.DEFAULT,
            _require_transaction_dir=mock.DEFAULT,
            _read_records=mock.DEFAULT,
            _validate_records=mock.DEFAULT,
            parse_status=mock.DEFAULT,
        ) as patched, mock.patch.object(
            H15_D1.base,
            "run_f1_cmd",
            return_value={"text": "record"},
        ), mock.patch.object(
            H15_D1.base,
            "verify_candidate_health",
            return_value={"healthy": True},
        ), mock.patch.object(
            H15_D1.legacy,
            "parse_appended_benchmark",
            side_effect=H15_D1.ContractError("cleanup marker absent"),
        ):
            patched["load_inputs"].return_value = ({"run_id": "r"}, object(), {})
            patched["_require_transaction_dir"].return_value = Path("/private/ordinal")
            patched["_read_records"].return_value = records
            patched["parse_status"].return_value = {
                "binding": 1,
                "enable": 1,
                "latch": 1,
                "build": H15_F1.CANDIDATE_BUILD,
            }
            result = H15_D1.reconcile(args)
        self.assertEqual(
            result["terminal"],
            "RECOVERY_PENDING_MOUNT_CLEANUP_NO_REPLAY",
        )

    def test_target_contract_represents_direct_ufs_readonly_lane(self) -> None:
        contract = TARGET_CONTRACT.read_text(encoding="utf-8")
        start = contract.index("`A90_DIRECT_UFS_READONLY_ROOT_V2`")
        lane = contract[start:contract.index("The one-use attended D1", start)]
        for token in (
            "ro,noload,nosuid,nodev",
            "never formats, repairs, replays, populates, copies, stages",
            "private minimal `/dev`",
            "no userdata block node",
            "exact V2321 boot rollback",
            "replay is forbidden",
            "applies to S22+",
            "execution-critical hashes",
            "incident occurs",
        ):
            self.assertIn(token, lane)


if __name__ == "__main__":
    unittest.main()
