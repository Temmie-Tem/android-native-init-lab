"""Adversarial H0 tests for the isolated-Debian content manifest and builder."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from _loader import load_script


REPO = Path(__file__).resolve().parents[1]
MANIFEST = REPO / (
    "workspace/public/src/scripts/revalidation/a90_flat_builder/versions/"
    "isolated-debian-minimal-content-v2/userdata-content-manifest.json"
)
H14 = REPO / (
    "workspace/public/src/scripts/revalidation/a90_flat_builder/versions/"
    "phase3-minimal-h14/userdata-content-manifest.json"
)
RECIPE = load_script(
    "workspace/public/src/scripts/server-distro/build_a90_isolated_debian_content_v2.py"
)


class IsolatedDebianManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.value = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_schema_is_new_and_h14_is_unchanged_and_separate(self) -> None:
        old = json.loads(H14.read_text(encoding="utf-8"))
        self.assertEqual(old["schema"], "a90-h14-ufs-content-manifest-v1")
        self.assertEqual(len(old["files"]), 19)
        self.assertEqual(self.value["schema"], RECIPE.SCHEMA)
        self.assertNotEqual(self.value["schema"], old["schema"])
        self.assertNotEqual(self.value["files"], old["files"])
        RECIPE.validate_manifest(self.value)

    def test_legacy_consumers_remain_bound_to_h14(self) -> None:
        h14_relative = "phase3-minimal-h14/userdata-content-manifest.json"
        build_source = (
            REPO / "workspace/public/src/scripts/revalidation/a90_flat_builder/build.py"
        ).read_text(encoding="utf-8")
        self.assertIn("a90-h14-ufs-content-manifest-v1", build_source)
        self.assertIn("len(content[\"files\"]) != 19", build_source)
        runner_paths = sorted(
            list(
                (REPO / "workspace/public/src/scripts/server-distro").glob(
                    "a90_h1*_ufs_f1_runner_v1.py"
                )
            )
            + [
                REPO
                / "workspace/public/src/scripts/server-distro/a90_h24_ufs_f1_runner_v1.py"
            ]
        )
        self.assertGreaterEqual(len(runner_paths), 5)
        for path in runner_paths:
            self.assertIn(h14_relative, path.read_text(encoding="utf-8"), str(path))
        self.assertNotIn("isolated-debian-minimal-content-v2", build_source)

    def test_authority_is_explicitly_h0_only(self) -> None:
        self.assertFalse(self.value["candidate_eligible"])
        self.assertFalse(self.value["device_install_authorized"])
        self.assertEqual(self.value["status"], "h0-specification-deferred")
        self.assertEqual(self.value["selected_closure"], "NESTED_PID_NAMESPACE_ISOLATION")
        self.assertEqual(self.value["pid1"]["historical_sysvinit_assumed"], False)
        self.assertTrue(self.value["toolchain"]["trace"]["output_is_candidate_superset"])
        self.assertTrue(self.value["toolchain"]["trace"]["later_on_device_negative_testing_required"])

    def test_absent_list_requires_the_forbidden_paths(self) -> None:
        required = {
            "/etc/a90-d3-firstboot",
            "/root/.ssh/authorized_keys",
            "/usr/bin/ip",
            "/usr/sbin/iw",
            "/usr/local/bin/a90-dpublic-smoke-httpd",
            "/usr/local/bin/a90-dpublic-hud-intent",
            "/usr/local/bin/a90-dpublic-hud-presenter",
            "/usr/local/bin/a90-dpublic-wifi-sta",
            "/dev/console",
            "/dev/ttyGS0",
            "/dev/ptmx",
            "/dev/pts",
            "/dev/shm",
        }
        self.assertTrue(required.issubset(set(self.value["absent"])))
        bad = copy.deepcopy(self.value)
        bad["absent"].remove("/usr/sbin/iw")
        with self.assertRaises(RECIPE.ContentError):
            RECIPE.validate_manifest(bad)

    def test_absent_and_present_cannot_overlap(self) -> None:
        bad = copy.deepcopy(self.value)
        record = copy.deepcopy(bad["files"][0])
        record["path"] = "/usr/sbin/iw"
        record["sha256"] = "0" * 64
        record.pop("source", None)
        bad["files"].append(record)
        with self.assertRaises(RECIPE.ContentError):
            RECIPE.validate_manifest(bad)

    def test_account_database_is_exact_and_adversarial_duplicate_fails(self) -> None:
        RECIPE.validate_accounts(self.value)
        self.assertEqual(
            RECIPE.STATIC_TEXT["/etc/passwd"].count(b"\n"),
            self.value["accounts"]["exact_identity_count"] + 1,
        )
        bad = copy.deepcopy(self.value)
        bad["accounts"]["ssh_key_daemon"]["uid"] = 3301
        with self.assertRaises(RECIPE.ContentError):
            RECIPE.validate_accounts(bad)
        bad = copy.deepcopy(self.value)
        bad["accounts"]["nss"]["account_sources"] = ["files", "ldap"]
        with self.assertRaises(RECIPE.ContentError):
            RECIPE.validate_accounts(bad)

    def test_authorized_keys_grammar_is_one_redacted_restrictive_line(self) -> None:
        RECIPE.validate_authorized_keys(self.value)
        bad = copy.deepcopy(self.value)
        bad["authorized_keys"]["grammar"]["options"].remove("no-pty")
        with self.assertRaises(RECIPE.ContentError):
            RECIPE.validate_authorized_keys(bad)
        bad = copy.deepcopy(self.value)
        bad["authorized_keys"]["grammar"]["line_template"] += "comment\n"
        with self.assertRaises(RECIPE.ContentError):
            RECIPE.validate_authorized_keys(bad)
        template = self.value["authorized_keys"]["grammar"]["line_template"]
        self.assertEqual(template.count("\n"), 1)
        self.assertIn("ssh-ed25519 <redacted-unbound>\n", template)
        self.assertNotIn("ssh-ed25519 AAA", template)

    def test_dropbear_feature_matrix_and_argv_are_bound(self) -> None:
        RECIPE.validate_dropbear(self.value)
        prohibited = tuple(RECIPE.validate_dropbear.__code__.co_consts)  # smoke that validator is real code
        self.assertTrue(prohibited)
        for name in (
            "DROPBEAR_SVR_PASSWORD_AUTH",
            "DROPBEAR_SVR_PAM_AUTH",
            "DROPBEAR_SVR_AGENTFWD",
            "DROPBEAR_SVR_X11FWD",
            "DROPBEAR_SVR_LOCALTCPFWD",
            "DROPBEAR_SVR_REMOTETCPFWD",
            "DROPBEAR_SVR_PTY",
        ):
            bad = copy.deepcopy(self.value)
            bad["dropbear"]["build"]["feature_macros"][name] = True
            with self.subTest(name=name):
                with self.assertRaises(RECIPE.ContentError):
                    RECIPE.validate_dropbear(bad)
        bad = copy.deepcopy(self.value)
        bad["dropbear"]["argv"][9] = "22"
        with self.assertRaises(RECIPE.ContentError):
            RECIPE.validate_dropbear(bad)

    def test_deferred_dropbear_cannot_be_presented_as_an_exact_hash(self) -> None:
        self.assertIsNone(self.value["dropbear"]["binary_sha256"])
        self.assertFalse(self.value["candidate_eligible"])
        self.assertTrue(
            any(item["item"] == "dropbear-feature-removed-binary" for item in self.value["deferred"])
        )
        self.assertFalse(RECIPE.audit(RECIPE.parse_args(["--manifest", str(MANIFEST)]))["dropbear_hash_bound"])

    def test_forbidden_content_assertions_are_all_closed(self) -> None:
        RECIPE.validate_manifest(self.value)
        self.assertTrue(all(value is False for value in self.value["forbidden_content"].values()))
        bad = copy.deepcopy(self.value)
        bad["forbidden_content"]["general_ip"] = True
        with self.assertRaises(RECIPE.ContentError):
            RECIPE.validate_manifest(bad)
        bad = copy.deepcopy(self.value)
        bad["files"][0]["mode"] = "4755"
        with self.assertRaises(RECIPE.ContentError):
            RECIPE.validate_manifest(bad)

    def test_static_components_cross_compile_to_pinned_arm64_artifacts(self) -> None:
        if shutil.which("aarch64-linux-gnu-gcc") is None:
            self.skipTest("cross-compiler unavailable")
        with tempfile.TemporaryDirectory(prefix="a90-content-components-") as temporary:
            outputs = RECIPE.compile_components(Path(temporary) / "build", self.value)
            self.assertEqual(set(outputs), set(RECIPE.COMPONENTS))
            for path, output in outputs.items():
                self.assertEqual(output.stat().st_size, RECIPE._manifest_files(self.value)[path]["size"])
                self.assertEqual(
                    RECIPE.sha256_file(output),
                    RECIPE._manifest_files(self.value)[path]["sha256"],
                )

    def test_builder_missing_private_dropbear_is_deferred_without_output(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="a90-content-deferred-", dir=RECIPE.PRIVATE_ROOT
        ) as temporary:
            output = Path(temporary) / "output"
            args = RECIPE.parse_args(
                [
                    "--manifest",
                    str(MANIFEST),
                    "--dropbear-source",
                    str(Path(temporary) / "missing-dropbear-source"),
                    "--output",
                    str(output),
                ]
            )
            with self.assertRaises(RECIPE.DeferredInput):
                RECIPE.build(args)
            self.assertFalse(output.exists())

    def test_materialized_tree_is_exact_and_has_no_forbidden_regular_files(self) -> None:
        value = copy.deepcopy(self.value)
        fake_dropbear = b"private-test-only-dropbear\n"
        fake_hash = RECIPE.sha256_bytes(fake_dropbear)
        value["dropbear"]["binary_sha256"] = fake_hash
        value["dropbear"]["binary_state"] = "materialized-private-not-authorized"
        value["dropbear"]["build"]["source_sha256"] = "0" * 64
        value["dropbear"]["build"]["configuration_semantics_sha256"] = "1" * 64
        value["source_inputs"]["dropbear"]["sha256"] = "0" * 64
        value["source_inputs"]["dropbear"]["state"] = "materialized-private"
        for item in value["files"]:
            if item["path"] == "/usr/sbin/dropbear":
                item["sha256"] = fake_hash
                item["size"] = len(fake_dropbear)
                item.pop("artifact_state", None)
        RECIPE.validate_manifest(value)
        with tempfile.TemporaryDirectory(prefix="a90-content-tree-") as temporary:
            temp_root = Path(temporary)
            component_outputs = RECIPE.compile_components(temp_root / "components", value)
            dropbear = temp_root / "dropbear"
            dropbear.write_bytes(fake_dropbear)
            output = temp_root / "output"
            files = RECIPE._manifest_files(value)
            rootfs = RECIPE.materialize_tree(value, files, component_outputs, dropbear, output)
            RECIPE.validate_tree(rootfs, files, value)
            RECIPE.deterministic_tar(rootfs, output / "content.tar", value)
            self.assertTrue((output / "content.tar").is_file())
            self.assertFalse((rootfs / "root/.ssh/authorized_keys").exists())
            self.assertFalse((rootfs / "usr/bin/ip").exists())


if __name__ == "__main__":
    unittest.main()
