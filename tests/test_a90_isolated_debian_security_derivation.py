"""H0 tests for the A90 static/dynamic security derivation and reconciliation."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from _loader import load_script


REPO = Path(__file__).resolve().parents[1]
MANIFEST = REPO / (
    "workspace/public/src/scripts/revalidation/a90_flat_builder/versions/"
    "isolated-debian-minimal-content-v2/userdata-content-manifest.json"
)
DERIVATION = load_script(
    "workspace/public/src/scripts/server-distro/a90_isolated_debian_security_derivation.py"
)
TRACE = REPO / (
    "workspace/private/outputs/a90-isolated-debian-trace-2026-08-15/"
    "session_strace.txt"
)
RECIPE = load_script(
    "workspace/public/src/scripts/server-distro/build_a90_isolated_debian_content_v2.py"
)


class A90SecurityDerivationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_static_dropbear_measurement_reproduces_bound_numbers(self) -> None:
        binaries = DERIVATION.binary_paths(DERIVATION.DEFAULT_BINARY_ROOT)
        result = DERIVATION.derive_static(self.manifest, binaries)
        dropbear = result["binaries"]["dropbear"]
        self.assertEqual(dropbear["svc_site_count"], 194)
        self.assertEqual(dropbear["resolved_site_count"], 185)
        self.assertEqual(dropbear["unresolved_site_count"], 9)
        self.assertEqual(
            dropbear["resolved_syscall_numbers"],
            [
                17, 24, 25, 29, 35, 37, 46, 48, 49, 50, 53, 54, 56, 57, 59,
                61, 62, 63, 64, 66, 67, 78, 79, 80, 93, 94, 95, 96, 98, 99,
                103, 113, 118, 119, 120, 121, 123, 125, 126, 129, 131, 134,
                135, 144, 146, 147, 149, 154, 155, 157, 159, 160, 166, 167,
                169, 172, 174, 175, 176, 178, 179, 198, 200, 201, 204, 205,
                208, 209, 210, 214, 215, 216, 220, 221, 222, 226, 233, 261,
                278, 281, 293, 435, 436,
            ],
        )
        self.assertEqual(
            {
                item["address_hex"] for item in dropbear["unresolved_sites"]
            },
            {
                "0x40520",
                "0x4fac4",
                "0x50da8",
                "0x54ef0",
                "0x63940",
                "0x63b44",
                "0x65164",
                "0x9c604",
                "0x9c950",
            },
        )
        self.assertEqual(result["union_resolved_syscall_count"], 84)

    def test_reconciliation_fails_when_a_traced_syscall_is_missing(self) -> None:
        static = {"union_resolved_syscall_numbers": [17, 56, 222]}
        dynamic = {"observed_syscall_numbers": [56, 222]}
        passing = DERIVATION.reconcile(static, dynamic, [17, 56, 222])
        self.assertEqual(passing["traced_missing_from_allowlist"], [])
        self.assertTrue(passing["regression_pass"])

        failing = DERIVATION.reconcile(static, dynamic, [17, 56])
        self.assertEqual(failing["traced_missing_from_allowlist"], [222])
        self.assertFalse(failing["regression_pass"])

    def test_authoritative_header_mapping_resolves_aarch64_aliases(self) -> None:
        mapping = DERIVATION.parse_syscall_header()
        self.assertEqual(
            {name: mapping[name] for name in [
                "fcntl", "fstat", "fstatat", "lseek", "mmap", "newfstatat",
            ]},
            {
                "fcntl": 25,
                "fstat": 80,
                "fstatat": 79,
                "lseek": 62,
                "mmap": 222,
                "newfstatat": 79,
            },
        )

    def test_preserved_trace_is_covered_by_derived_candidate_allowlist(self) -> None:
        dynamic = DERIVATION.ingest_trace(TRACE)
        static = DERIVATION.derive_static(
            self.manifest, DERIVATION.binary_paths(DERIVATION.DEFAULT_BINARY_ROOT)
        )
        candidate = self.manifest["security_derivation"]["static"][
            "candidate_allowlist_numbers"
        ]
        reconciliation = DERIVATION.reconcile(static, dynamic, candidate)

        self.assertEqual(len(dynamic["observed_syscall_names"]), 48)
        self.assertEqual(len(dynamic["observed_syscall_numbers"]), 48)
        self.assertEqual(reconciliation["traced_missing_from_allowlist"], [])
        self.assertTrue(reconciliation["regression_pass"])
        self.assertEqual(
            reconciliation["traced_outside_static_set"], [72, 139, 202, 203, 260]
        )
        self.assertFalse(reconciliation["static_upper_bound_claim"]["survives"])

        gaps = {
            item["syscall_name"]: item
            for item in reconciliation["static_analysis_gaps"]
        }
        self.assertEqual(
            {
                name: gaps[name]["classification"]
                for name in gaps
            },
            {
                "accept": "unresolved-register-sourced-site",
                "connect": "unresolved-register-sourced-site",
                "pselect6": "unresolved-register-sourced-site",
                "rt_sigreturn": "signal-trampoline-entry",
                "wait4": "unresolved-register-sourced-site",
            },
        )
        self.assertTrue(
            all(gaps[name]["evidence"].get("callers") for name in
                ["accept", "connect", "pselect6", "wait4"])
        )

        capability = DERIVATION.derive_capabilities(
            DERIVATION.DEFAULT_DROPBEAR_SOURCE, dynamic
        )
        self.assertEqual(
            capability["profiles"]["key_daemon"]["dynamic_auth_transition_proof"],
            "observed-borrowed-identity-exact-3302-to-3301-transition-unproved",
        )

    def test_dynamic_observation_is_two_sided_lower_bound(self) -> None:
        trace = self.manifest["toolchain"]["trace"]
        self.assertTrue(trace["observed_trace_is_lower_bound_only"])
        self.assertTrue(trace["allowlist_must_cover_observed_union"])
        self.assertIn("strict subset", trace["interpretation"])
        self.assertIn("missing syscall", trace["interpretation"])
        self.assertNotIn("output_is_" + "candidate" + "_superset", trace)

        bad = copy.deepcopy(self.manifest)
        bad["toolchain"]["trace"]["observed_trace_is_lower_bound_only"] = False
        with self.assertRaises(RECIPE.ContentError):
            RECIPE.validate_manifest(bad)

        bad = copy.deepcopy(self.manifest)
        bad["security_derivation"]["dynamic"]["observed_syscall_numbers"].append(999)
        with self.assertRaises(RECIPE.ContentError):
            RECIPE.validate_manifest(bad)

    def test_capability_and_proc_derivations_remain_explicitly_scoped(self) -> None:
        capability_result = DERIVATION.derive_capabilities()
        self.assertTrue(capability_result["source_checks"]["dropbear"]["source_verified"])
        capabilities = capability_result["profiles"]
        self.assertEqual(capabilities["pid1"]["minimum"], [])
        self.assertEqual(capabilities["dispatcher"]["minimum"], [])
        self.assertEqual(capabilities["workload"]["minimum"], [])
        self.assertEqual(
            capabilities["key_daemon"]["minimum"], ["CAP_SETGID", "CAP_SETUID"]
        )
        self.assertEqual(
            capabilities["key_daemon"]["dynamic_auth_transition_proof"],
            "deferred-unexercised",
        )
        proc = DERIVATION.derive_proc({}, {"observed_proc_paths": ["/proc/self/exe"]})
        self.assertEqual(proc["finite_global_scalar_allowlist"], [])
        self.assertEqual(proc["observed_global_read_only_scalars"], [])
        self.assertEqual(proc["non_scalar_per_task_paths"], ["/proc/self/exe"])


if __name__ == "__main__":
    unittest.main()
