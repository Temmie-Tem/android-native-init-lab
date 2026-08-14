"""Adversarial H0 tests for the isolated-Debian content manifest and builder."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import shutil
import subprocess
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
        # The manifest has exactly two lawful lifecycle states: specified with
        # the Dropbear input still absent, and materialized from a private
        # build. Neither grants authority, so both are bound here exactly
        # rather than the set being widened to "any status".
        self.assertIn(
            self.value["status"],
            ("h0-specification-deferred", "h0-materialized-private"),
        )
        self.assertEqual(self.value["selected_closure"], "NESTED_PID_NAMESPACE_ISOLATION")
        self.assertEqual(self.value["pid1"]["historical_sysvinit_assumed"], False)
        trace = self.value["toolchain"]["trace"]
        self.assertTrue(trace["observed_trace_is_lower_bound_only"])
        self.assertTrue(trace["allowlist_must_cover_observed_union"])
        self.assertIn("strict subset", trace["interpretation"])
        self.assertIn("missing syscall", trace["interpretation"])
        self.assertNotIn("output_is_" + "candidate" + "_superset", trace)
        self.assertTrue(trace["later_on_device_negative_testing_required"])
        security = self.value["security_derivation"]
        self.assertFalse(security["authority"]["candidate_eligible"])
        self.assertFalse(security["authority"]["device_install_authorized"])
        self.assertEqual(
            security["static"]["candidate_allowlist_numbers"],
            security["static"]["union_resolved_syscall_numbers"],
        )
        self.assertEqual(security["reconciliation"]["traced_missing_from_candidate_allowlist"], [])

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
        # Address the port by value, not by index: removing -a shifted every
        # position after it, and an index-based edit silently started testing
        # a different token than the one this case is named for.
        bad = copy.deepcopy(self.value)
        argv = bad["dropbear"]["argv"]
        argv[argv.index("-p") + 1] = "22"
        with self.assertRaises(RECIPE.ContentError):
            RECIPE.validate_dropbear(bad)

    def test_dropbear_hash_state_and_deferral_stay_coupled(self) -> None:
        """A hash may never appear while the input is still declared absent.

        The invariant is the coupling, not the null: an unbound hash must be
        accompanied by the deferral and by an unbound audit, and a bound hash
        must be exact hex and must have retired that deferral. Asserting only
        `is None` pinned the pre-source moment and would have to be relaxed
        the first time the build succeeded.
        """
        value = self.value["dropbear"]
        deferred = {item["item"] for item in self.value["deferred"]}
        bound = RECIPE.audit(RECIPE.parse_args(["--manifest", str(MANIFEST)]))["dropbear_hash_bound"]
        self.assertFalse(self.value["candidate_eligible"])
        if value["binary_sha256"] is None:
            self.assertEqual(value["binary_state"], "deferred-missing-private-source")
            self.assertIn("dropbear-feature-removed-binary", deferred)
            self.assertIsNone(value["build"]["source_sha256"])
            self.assertFalse(bound)
        else:
            self.assertEqual(value["binary_state"], "materialized-private-not-authorized")
            self.assertNotIn("dropbear-feature-removed-binary", deferred)
            for digest in (
                value["binary_sha256"],
                value["build"]["source_sha256"],
                value["build"]["configuration_semantics_sha256"],
            ):
                self.assertRegex(digest, r"^[0-9a-f]{64}$")
            self.assertTrue(bound)
        self.assertFalse(self.value["device_install_authorized"])

    def test_configuration_semantics_digest_excludes_itself(self) -> None:
        """Otherwise each build hashes the previous build's result.

        That self-reference kept the manifest from ever reaching a fixed
        point, so every rebuild produced a spurious diff against the reviewed
        value while the built artifact was in fact byte-identical.
        """
        build = self.value["dropbear"]["build"]
        if build["configuration_semantics_sha256"] is None:
            self.skipTest("configuration digest is unbound until a private build exists")
        expected = RECIPE.sha256_bytes(
            json.dumps(
                {k: v for k, v in build.items() if k != "configuration_semantics_sha256"},
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        )
        self.assertEqual(build["configuration_semantics_sha256"], expected)

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


class DropbearArgvSemanticsTests(unittest.TestCase):
    """A bound flag whose case label was compiled out is fatal, not ignored.

    Dropbear's option parser ends in a default branch that prints usage and
    calls exit(EXIT_FAILURE). Feature removal deletes case labels, and only
    some of them have an ignore-the-flag #else. `-a` had none, so the
    originally bound argv would have stopped the server from ever starting
    while every other health signal looked normal.
    """

    def setUp(self) -> None:
        self.value = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.dropbear = self.value["dropbear"]

    def test_every_bound_flag_has_derived_semantics(self) -> None:
        semantics = self.dropbear["argv_semantics"]["flags"]
        argv = self.dropbear["argv"]
        flags = [token for token in argv[1:] if token.startswith("-")]
        self.assertEqual(sorted(flags), sorted(semantics))
        for flag, record in semantics.items():
            self.assertTrue(record["present_in_this_build"], flag)
            self.assertTrue(record["effect"], flag)

    def test_flags_whose_case_label_is_removed_are_rejected(self) -> None:
        rejected = self.dropbear["argv_semantics"]["rejected"]
        self.assertIn("-a", rejected)
        for flag, record in rejected.items():
            self.assertNotIn(flag, self.dropbear["argv"])
            self.assertFalse(record["present_in_this_build"], flag)

    def test_a_flag_may_not_be_reintroduced_without_its_case_label(self) -> None:
        bad = copy.deepcopy(self.value)
        bad["dropbear"]["argv"].insert(7, "-a")
        with self.assertRaises(RECIPE.ContentError):
            RECIPE.validate_dropbear(bad["dropbear"])

    def test_bound_argv_is_accepted_by_the_built_binary(self) -> None:
        """Executed against the real binary when a private build is present.

        Reading the parser proves what the source says; only running it proves
        what this build does.
        """
        built = (
            RECIPE.PRIVATE_ROOT
            / "outputs/a90-isolated-debian-content-v2/dropbear-build/dropbear"
        )
        if not built.is_file():
            self.skipTest("no private Dropbear build present")
        if shutil.which("qemu-aarch64") is None:
            self.skipTest("qemu-aarch64 is unavailable")
        argv = list(self.dropbear["argv"][1:])
        argv[argv.index("-r") + 1] = "/nonexistent-host-key"
        completed = subprocess.run(
            ["qemu-aarch64", str(built), *argv],
            capture_output=True,
            text=True,
            timeout=120,
        )
        output = completed.stdout + completed.stderr
        self.assertNotIn("Invalid option", output)
        self.assertNotIn("Usage:", output)
        # Reaching host-key loading proves the whole option sequence parsed.
        self.assertIn("hostkey", output.lower())


if __name__ == "__main__":
    unittest.main()
