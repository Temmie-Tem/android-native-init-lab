import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_r4w1b_elf_audit.py"
)
PATCH_CHECK = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_r4w1b_patch_check.py"
)
CLANG = ROOT / (
    "workspace/private/inputs/toolchains/aosp-clang-android12-release/"
    "clang-r416183b/bin/clang"
)


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S22PlusFyg8R4W1BElfAuditTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module("s22plus_fyg8_r4w1b_elf_tested", SCRIPT)
        cls.patch_check = load_module("s22plus_fyg8_r4w1b_patch_for_elf", PATCH_CHECK)

    def build_fixture(self):
        if not CLANG.is_file():
            self.skipTest("pinned AArch64 clang is unavailable")
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        source = root / "fixture.S"
        elf = root / "fixture.elf"
        marker_bytes = ",".join(str(value) for value in self.patch_check.MARKER.encode("ascii"))
        source.write_text(
            f"""
.section .text
.global kernel_init
.type kernel_init,%function
kernel_init:
    bl run_init_process
    cbnz w0, failure
    adrp x1, init_path
    add x1, x1, :lo12:init_path
    mov x0, x8
    bl strcmp
    cbnz w0, failure
    mrs x8, sp_el0
    ldr w8, [x8, #1480]
    cmp w8, #1
    b.eq witness
failure:
    ret
witness:
    adrp x21, marker
    add x21, x21, :lo12:marker
    ret
.size kernel_init, .-kernel_init

.global run_init_process
.type run_init_process,%function
run_init_process:
    mov w0, wzr
    ret
.size run_init_process, .-run_init_process

.global strcmp
.type strcmp,%function
strcmp:
    mov w0, wzr
    ret
.size strcmp, .-strcmp

.section .rodata
.balign 8
marker:
    .byte {marker_bytes}
init_path:
    .asciz "/init"

.section .data
.balign 8
.global builtime_crypto_hmac
.type builtime_crypto_hmac,%object
builtime_crypto_hmac:
    .byte {','.join(str(value) for value in range(1, 33))}
.size builtime_crypto_hmac, .-builtime_crypto_hmac

.global integrity_crypto_addrs
.type integrity_crypto_addrs,%object
integrity_crypto_addrs:
    .quad 1
    .zero 65528
.size integrity_crypto_addrs, .-integrity_crypto_addrs

.global crypto_buildtime_address
.type crypto_buildtime_address,%object
crypto_buildtime_address:
    .quad crypto_buildtime_address
.size crypto_buildtime_address, .-crypto_buildtime_address
""",
            encoding="ascii",
        )
        completed = subprocess.run(
            [
                str(CLANG),
                "--target=aarch64-linux-gnu",
                "-nostdlib",
                "-fuse-ld=lld",
                "-no-pie",
                "-Wl,--build-id=none",
                "-Wl,-Ttext=0x100000",
                "-o",
                str(elf),
                str(source),
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.addCleanup(temporary.cleanup)
        return elf

    def test_final_elf_contract_accepts_exact_control_flow_and_fips(self):
        elf = self.build_fixture()
        result = self.module.inspect_final_vmlinux(
            elf, self.patch_check.MARKER.encode("ascii")
        )
        self.assertTrue(result["verified"])
        self.assertTrue(result["fips"]["verified"])
        self.assertEqual(result["fips"]["hmac_size"], 32)
        self.assertEqual(result["control_flow"]["success_edge_count"], 1)
        self.assertEqual(result["control_flow"]["marker_count_in_elf"], 1)

    def test_aarch64_decoders_are_fail_closed(self):
        self.assertIsNone(self.module.branch_target(0x1000, 0))
        self.assertIsNone(self.module.compare_branch(0))
        self.assertIsNone(self.module.conditional_branch(0))
        self.assertIsNone(self.module.adrp_target(0x1000, 0))
        self.assertIsNone(self.module.add_immediate(0))
        self.assertIsNone(self.module.compare_w_immediate(0))
        self.assertFalse(self.module.is_mrs_sp_el0(0))


if __name__ == "__main__":
    unittest.main()
