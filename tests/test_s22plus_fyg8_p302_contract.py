import argparse
import hashlib
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "workspace/public/src/scripts/revalidation"

import sys

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import s22plus_fyg8_p301_telemetry_generator as parent_generator  # noqa: E402
import s22plus_fyg8_p302_binary_carrier as binary_carrier  # noqa: E402
import s22plus_fyg8_p302_candidate_contract as candidate_contract  # noqa: E402
import s22plus_fyg8_p302_carrier_generator as generator  # noqa: E402
import s22plus_fyg8_p302_overlay_contract as contract  # noqa: E402
import s22plus_fyg8_p302_overlay_intent as intent  # noqa: E402
import s22plus_fyg8_p302_userspace_build as userspace  # noqa: E402


P301_INIT = ROOT / "workspace/private/outputs/s22plus_fyg8_p301_r1/userspace/init"
P301_CHILD = (
    ROOT / "workspace/private/outputs/s22plus_fyg8_p301_r1/userspace/s22-e1-child"
)
P301_INIT_SHA256 = "17eae28ae1e8fa0abcd47b05c3b57cfa5c54124db0192137b208a3f85978ee35"
P301_CHILD_SHA256 = "9a57b30aa3fb08ee0aab4d045d2805dd36875bb80bcba7b0b6606f619df71639"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_section(path: Path, output: Path) -> bytes:
    subprocess.run(
        [
            "aarch64-linux-gnu-objcopy",
            "--dump-section",
            f".text={output}",
            path,
        ],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return output.read_bytes()


def carried_copy(directory: Path) -> Path:
    path = directory / "carried.init"
    path.write_bytes(P301_INIT.read_bytes())
    path.chmod(0o755)
    binary_carrier.apply(path)
    return path


class P302ContractTests(unittest.TestCase):
    def test_source_routes_parent_and_fixed_image_are_pinned(self):
        self.assertEqual(set(contract.SOURCE_PATHS), contract.SOURCE_KEYS)
        self.assertEqual(len(contract.SOURCE_KEYS), 8)
        self.assertTrue(
            all((ROOT / path).is_file() for path in contract.SOURCE_PATHS.values())
        )
        parent = contract.verify_parent(ROOT)
        self.assertEqual(parent["run_id"], "e324abaec60286102e4c9eb19fd80600")
        self.assertEqual(
            parent["userspace_overlay_contract_id"],
            contract.PARENT_OVERLAY_CONTRACT_ID,
        )
        self.assertEqual(
            contract.EXPECTED_IMAGE["sha256"],
            "01457240881b432f725b0f2d795813c38ef7cca4365633f9b0fc7c3a62744a3f",
        )

    def test_generator_changes_only_runtime_include(self):
        parent = contract.verify_parent(ROOT)
        kwargs = {
            "run_id": bytes.fromhex(parent["run_id"]),
            "unsat_tag": bytes.fromhex(parent["unsat_tag_hex"]),
            "profile": parent["profile"],
        }
        baseline = parent_generator.generate_bytes(ROOT, **kwargs)
        carried = generator.generate_bytes(ROOT, **kwargs)
        self.assertEqual(carried, baseline)

    def test_overlay_userspace_and_text_identity_are_reproducible(self):
        self.assertEqual(sha256(P301_INIT), P301_INIT_SHA256)
        self.assertEqual(sha256(P301_CHILD), P301_CHILD_SHA256)
        with tempfile.TemporaryDirectory(prefix="p302-contract-") as temporary:
            directory = Path(temporary)
            intent_dir = directory / "intent"
            value = intent.create(ROOT, intent_dir)
            exact = candidate_contract.verify(
                ROOT,
                ROOT / contract.PARENT_SOURCE,
                intent_dir / "overlay-intent.json",
                ROOT / contract.PARENT_PATCH,
            )
            self.assertEqual(value["run_id"], exact["run_id"])
            self.assertEqual(exact["carrier"]["id"], binary_carrier.CARRIER_ID)
            output = directory / "userspace"
            result = userspace.build_userspace(
                argparse.Namespace(
                    source=contract.PARENT_SOURCE,
                    intent=intent_dir / "overlay-intent.json",
                    patch=contract.PARENT_PATCH,
                    out=output,
                )
            )
            init = output / "init"
            child = output / "s22-e1-child"
            self.assertEqual(result["verdict"], userspace.VERDICT)
            self.assertTrue(result["two_build_byte_identical"])
            self.assertNotEqual(init.read_bytes(), P301_INIT.read_bytes())
            self.assertEqual(child.read_bytes(), P301_CHILD.read_bytes())
            self.assertEqual(
                init.read_bytes().count(binary_carrier.CARRIER_ID.encode("ascii")), 1
            )
            self.assertEqual(
                text_section(init, directory / "p302.text"),
                text_section(P301_INIT, directory / "p301.text"),
            )

    def test_binary_verifier_rejects_program_and_section_metadata_tamper(self):
        with tempfile.TemporaryDirectory(prefix="p302-tamper-") as temporary:
            directory = Path(temporary)

            stack = carried_copy(directory)
            stack_data = bytearray(stack.read_bytes())
            phoff = struct.unpack_from("<Q", stack_data, 32)[0]
            phentsize = struct.unpack_from("<H", stack_data, 54)[0]
            phnum = struct.unpack_from("<H", stack_data, 56)[0]
            stack_index = None
            for index in range(phnum):
                offset = phoff + index * phentsize
                if struct.unpack_from("<I", stack_data, offset)[0] == 0x6474E551:
                    stack_index = index
                    struct.pack_into("<I", stack_data, offset + 4, 7)
                    break
            self.assertIsNotNone(stack_index)
            stack.write_bytes(stack_data)
            with self.assertRaisesRegex(
                binary_carrier.BinaryCarrierError, "program headers"
            ):
                binary_carrier.verify(stack, P301_INIT)

            flags = carried_copy(directory)
            flags_data = bytearray(flags.read_bytes())
            parsed = binary_carrier._elf(bytes(flags_data), "test")  # noqa: SLF001
            identity_index = next(
                index
                for index, row in enumerate(parsed["sections"])
                if row["name"] == binary_carrier.SECTION
            )
            shoff = struct.unpack_from("<Q", flags_data, 40)[0]
            shentsize = struct.unpack_from("<H", flags_data, 58)[0]
            struct.pack_into(
                "<Q", flags_data, shoff + identity_index * shentsize + 8, 1
            )
            flags.write_bytes(flags_data)
            with self.assertRaisesRegex(
                binary_carrier.BinaryCarrierError, "identity section contract"
            ):
                binary_carrier.verify(flags, P301_INIT)

            alloc_flags = carried_copy(directory)
            alloc_flags_data = bytearray(alloc_flags.read_bytes())
            parsed = binary_carrier._elf(  # noqa: SLF001
                bytes(alloc_flags_data), "test"
            )
            identity_index = next(
                index
                for index, row in enumerate(parsed["sections"])
                if row["name"] == binary_carrier.SECTION
            )
            shoff = struct.unpack_from("<Q", alloc_flags_data, 40)[0]
            shentsize = struct.unpack_from("<H", alloc_flags_data, 58)[0]
            struct.pack_into(
                "<Q", alloc_flags_data, shoff + identity_index * shentsize + 8, 3
            )
            alloc_flags.write_bytes(alloc_flags_data)
            with self.assertRaisesRegex(
                binary_carrier.BinaryCarrierError, "SHF_ALLOC section closure"
            ):
                binary_carrier.verify(alloc_flags, P301_INIT)

            comment = carried_copy(directory)
            comment_data = bytearray(comment.read_bytes())
            parsed = binary_carrier._elf(bytes(comment_data), "test")  # noqa: SLF001
            comment_row = next(
                row for row in parsed["sections"] if row["name"] == ".comment"
            )
            comment_data[comment_row["offset"]] ^= 1
            comment.write_bytes(comment_data)
            with self.assertRaisesRegex(
                binary_carrier.BinaryCarrierError, "existing ELF section"
            ):
                binary_carrier.verify(comment, P301_INIT)

            gap = carried_copy(directory)
            gap_data = bytearray(gap.read_bytes())
            gap_offset = 51000
            parsed = binary_carrier._elf(bytes(gap_data), "test")  # noqa: SLF001
            self.assertFalse(
                any(
                    row[5] > 0 and row[2] <= gap_offset < row[2] + row[5]
                    for row in parsed["program_headers"]
                )
            )
            self.assertFalse(
                any(
                    row["content"] is not None
                    and row["offset"] <= gap_offset < row["offset"] + row["size"]
                    for row in parsed["sections"]
                )
            )
            gap_data[gap_offset] ^= 0x41
            gap.write_bytes(gap_data)
            with self.assertRaisesRegex(
                binary_carrier.BinaryCarrierError, "file bytes or padding"
            ):
                binary_carrier.verify(gap, P301_INIT)

            bss = carried_copy(directory)
            bss_data = bytearray(bss.read_bytes())
            parsed = binary_carrier._elf(bytes(bss_data), "test")  # noqa: SLF001
            bss_index = next(
                index
                for index, row in enumerate(parsed["sections"])
                if row["name"] == ".bss"
            )
            shoff = struct.unpack_from("<Q", bss_data, 40)[0]
            shentsize = struct.unpack_from("<H", bss_data, 58)[0]
            size_offset = shoff + bss_index * shentsize + 32
            size = struct.unpack_from("<Q", bss_data, size_offset)[0]
            struct.pack_into("<Q", bss_data, size_offset, size + 1)
            bss.write_bytes(bss_data)
            with self.assertRaisesRegex(
                binary_carrier.BinaryCarrierError, "SHF_ALLOC section closure"
            ):
                binary_carrier.verify(bss, P301_INIT)


if __name__ == "__main__":
    unittest.main()
