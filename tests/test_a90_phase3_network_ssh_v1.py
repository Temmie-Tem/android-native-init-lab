from __future__ import annotations

import hashlib
import importlib
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SERVER_DISTRO = REPO_ROOT / "workspace/public/src/scripts/server-distro"
if str(SERVER_DISTRO) not in sys.path:
    sys.path.insert(0, str(SERVER_DISTRO))

builder = importlib.import_module("prepare_phase3_network_ssh_v1_rootfs")

PROFILE_DIR = SERVER_DISTRO / "phase3_network_ssh_v1"
FIRSTBOOT = PROFILE_DIR / "a90_debian_return_arm_v1.sh"
SERVICE = PROFILE_DIR / "a90_debian_network_ssh_v1.sh"
INITTAB = PROFILE_DIR / "inittab"
STAGE = PROFILE_DIR / "a90-server-distro-stage"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class A90Phase3NetworkSshV1Tests(unittest.TestCase):
    def test_import_is_canonical_and_has_no_side_effect(self) -> None:
        self.assertEqual(
            Path(builder.__file__).resolve(),
            SERVER_DISTRO / "prepare_phase3_network_ssh_v1_rootfs.py",
        )
        self.assertFalse(
            (builder.PRIVATE_OUTPUTS / "phase3-network-ssh-v1-import").exists()
        )

    def test_manifest_pins_complete_source_closure(self) -> None:
        manifest, _ = builder.load_manifest()
        sources = manifest["sources"]
        expected = {
            "firstboot",
            "service",
            "inittab",
            "stage",
            "builder",
            "phase2_builder",
            "return_builder",
            "return_supervisor_source",
        }
        self.assertEqual(
            {key for key in sources if not key.endswith("_sha256")},
            expected,
        )
        for key in sorted(expected):
            path = builder.resolve_repo_file(sources[key], key)
            self.assertEqual(sha256_file(path), sources[f"{key}_sha256"])
        self.assertIs(manifest["candidate_authority"], False)

    def test_return_arm_is_first_and_service_free(self) -> None:
        source = FIRSTBOOT.read_text(encoding="utf-8")
        self.assertEqual(builder.validate_firstboot(source), ())
        self.assertTrue(
            builder.validate_firstboot(
                source.replace("--arm 120 20", "--arm 121 20", 1)
            )
        )
        self.assertTrue(builder.validate_firstboot(source + "\nip link set ncm0 up\n"))
        self.assertTrue(builder.validate_firstboot(source + "\n/usr/sbin/dropbear\n"))
        self.assertLess(
            source.index('RETURN_SUPERVISOR_PID=$("$RETURN_SUPERVISOR"'),
            source.index("PID1_EXE=$(readlink"),
        )

    def test_network_ssh_service_contract_and_faults(self) -> None:
        source = SERVICE.read_text(encoding="utf-8")
        self.assertEqual(builder.validate_service(source), ())
        mutations = (
            source.replace("addr replace", "addr add", 1),
            source.replace("route replace", "route add", 1),
            source.replace("-s -j -k", "-s -j", 1),
            source.replace("dropbear -F -E", "dropbear -E", 1),
            source.replace("-H -ltnp", "-H -ltn"),
            source.replace(
                'LISTENER_OWNER="\\\"dropbear\\\",pid=$STARTED_PID,"',
                "LISTENER_OWNER=unbound",
                1,
            ),
            source.replace("while [ \"$poll\" -lt \"$MAX_PID_POLLS\" ]", "while true", 1),
            source.replace('kill "$STARTED_PID" 2>/dev/null || true', ":", 1),
            source.replace('kill -KILL "$STARTED_PID" 2>/dev/null || true', ":", 1),
            source.replace('route del "$NCM_PEER" dev "$IFACE"', "route show", 1),
            source.replace('addr del "$NCM_ADDR" dev "$IFACE"', "addr show", 1),
            source.replace('link set "$IFACE" down', 'link set "$IFACE" up', 1),
            source.replace(
                'if cleanup_route=$("$TIMEOUT" 10 "$IP" route show exact',
                'cleanup_route=$("$TIMEOUT" 10 "$IP" route show exact',
                1,
            ),
            source.replace(
                'if cleanup_addr=$("$TIMEOUT" 10 "$IP" -o -4 addr show',
                'cleanup_addr=$("$TIMEOUT" 10 "$IP" -o -4 addr show',
                1,
            ),
            source.replace(
                'if cleanup_link=$("$TIMEOUT" 10 "$IP" -o link show',
                'cleanup_link=$("$TIMEOUT" 10 "$IP" -o link show',
                1,
            ),
            source.replace(
                'if ! listener_snapshot=$("$TIMEOUT" 5 "$SS" -H -ltnp',
                'listener_snapshot=$("$TIMEOUT" 5 "$SS" -H -ltnp',
                1,
            ),
            source.replace("*) return 3 ;;", "*) return 1 ;;", 1),
            source.replace("PID1_EXE=$(readlink", "PID1_EXE=$(printf", 1),
            source.replace("schema=a90-debian-network-ssh-v1-ready", "schema=wrong", 1),
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation[:80]):
                self.assertTrue(builder.validate_service(mutation))

    def test_shell_sources_parse_with_dash(self) -> None:
        for path in (FIRSTBOOT, SERVICE):
            with self.subTest(path=path.name):
                result = subprocess.run(
                    ["/bin/sh", "-n", str(path)],
                    cwd=REPO_ROOT,
                    check=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=10.0,
                )
                self.assertEqual(result.returncode, 0, result.stderr.decode())

    def test_inittab_serializes_return_services_and_display(self) -> None:
        source = INITTAB.read_text(encoding="utf-8")
        self.assertEqual(builder.validate_inittab(source), ())
        self.assertTrue(
            builder.validate_inittab(source.replace(":wait:", ":respawn:", 1))
        )
        self.assertTrue(
            builder.validate_inittab(
                source.replace("ns:2:wait:", "ns:2:once:", 1)
            )
        )

    def test_stage_names_debian_owners_and_no_authority(self) -> None:
        source = STAGE.read_text(encoding="utf-8")
        self.assertEqual(builder.validate_stage(source), ())
        self.assertTrue(
            builder.validate_stage(
                source.replace("candidate-authority=none", "candidate-authority=f1")
            )
        )

    def test_current_private_base_audits_when_present(self) -> None:
        manifest, _ = builder.load_manifest()
        base = REPO_ROOT / manifest["base"]["image"]
        if not base.is_file():
            self.skipTest("private pinned Phase 2 base is not present")
        state = builder.audit()
        self.assertEqual(state["manifest"]["profile"], builder.PROFILE)
        self.assertEqual(
            sha256_file(state["base_image"]),
            manifest["base"]["image_sha256"],
        )

    def test_output_root_is_private_and_absent_only(self) -> None:
        with self.assertRaises(builder.ContractError):
            builder.output_root(Path("/tmp/a90-phase3-network-ssh-v1"))
        with self.assertRaises(builder.ContractError):
            builder.output_root(builder.PRIVATE_OUTPUTS)


if __name__ == "__main__":
    unittest.main()
