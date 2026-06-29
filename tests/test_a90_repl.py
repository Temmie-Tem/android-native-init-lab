"""Host-only tests for the Tier-2 runtime kernel REPL driver (a90_repl.py).

Covers the pure command-buffer / parsing helpers, System.map resolution, the
static-image cross-check math, and the live-op math (slide/peek/call) with a
faked serial transport. Touches no device.
"""

from __future__ import annotations

import struct
import unittest
import hashlib
from pathlib import Path

from _loader import load_script


repl = load_script("workspace/public/src/scripts/revalidation/a90_repl.py")

REPO_ROOT = Path(__file__).resolve().parents[1]
MAP_PATH = REPO_ROOT / "workspace/private/runs/kernel/v2a1-repl-driver/System.map"
IMAGE_PATH = REPO_ROOT / "workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img"
C2B_PADDING_MAP_PATH = (
    REPO_ROOT / "workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map"
)
KERNEL_SOURCE_ROOT = (
    REPO_ROOT / "workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel"
)


def decode_printf_octal(text: str) -> bytes:
    out = bytearray()
    i = 0
    while i < len(text):
        if text[i] != "\\":
            raise AssertionError(f"unexpected char at {i}: {text[i]!r}")
        out.append(int(text[i + 1 : i + 4], 8))
        i += 4
    return bytes(out)


class CommandBufferTests(unittest.TestCase):
    def test_buffer_layout(self) -> None:
        buf = repl.build_cmd_buffer(repl.OP_CALL, (0xAABB, 0x11, 0x22, 0x33))
        self.assertEqual(len(buf), repl.CMD_BUF_LEN)
        self.assertEqual(struct.unpack_from("<Q", buf, 0x00)[0], repl.REPL_MAGIC)
        self.assertEqual(buf[0x08], repl.OP_CALL)
        self.assertEqual(struct.unpack_from("<Q", buf, 0x10)[0], 0xAABB)  # target
        self.assertEqual(struct.unpack_from("<Q", buf, 0x18)[0], 0x11)    # x0
        self.assertEqual(struct.unpack_from("<Q", buf, 0x20)[0], 0x22)    # x1
        self.assertEqual(struct.unpack_from("<Q", buf, 0x28)[0], 0x33)    # x2

    def test_buffer_truncates_to_64bit(self) -> None:
        buf = repl.build_cmd_buffer(repl.OP_PEEK, ((1 << 70) | 0xDEAD, 8))
        self.assertEqual(struct.unpack_from("<Q", buf, 0x10)[0], 0xDEAD & repl.MASK64)

    def test_poke_buffer_layout(self) -> None:
        buf = repl.build_cmd_buffer(repl.OP_POKE, (0xFFFFFFC012300000, 0xAABBCCDD, 4))
        self.assertEqual(buf[0x08], repl.OP_POKE)
        self.assertEqual(struct.unpack_from("<Q", buf, 0x10)[0], 0xFFFFFFC012300000)
        self.assertEqual(struct.unpack_from("<Q", buf, 0x18)[0], 0xAABBCCDD)
        self.assertEqual(struct.unpack_from("<Q", buf, 0x20)[0], 4)

    def test_too_many_args_rejected(self) -> None:
        with self.assertRaises(ValueError):
            repl.build_cmd_buffer(repl.OP_CALL, tuple(range(10)))

    def test_printf_octal_roundtrips(self) -> None:
        buf = repl.build_cmd_buffer(repl.OP_SLIDE, ())
        self.assertEqual(decode_printf_octal(repl.printf_octal(buf)), buf)

    def test_write_node_sh_uses_node_and_redirect(self) -> None:
        sh = repl.write_node_sh(b"\x00\xff")
        self.assertIn(repl.NODE, sh)
        self.assertIn("> ", sh)
        self.assertTrue(sh.startswith("printf '"))

    def test_parse_a90r_values(self) -> None:
        text = "junk\nA90R108000\nmore\nA90Rcafe1234\n"
        self.assertEqual(repl.parse_a90r_values(text), [0x108000, 0xCAFE1234])
        self.assertEqual(repl.parse_a90r_values("nothing here"), [])


class ConstantTests(unittest.TestCase):
    def test_entry_and_slide_anchors(self) -> None:
        # Pinned against the v1-repl build + live validation report.
        self.assertEqual(repl.ENTRY_VADDR, 0xFFFFFF80089273B4)
        self.assertEqual(repl.ADR_SELF_LINK_VADDR, 0xFFFFFF80089273F0)
        self.assertEqual(repl.REPL_MAGIC, 0xA90C0DE5DEADBEEF)
        self.assertEqual(repl.JOPP_MAGIC, 0x00BE7BAD)

    def test_gfp_kernel_derives_from_private_kernel_header(self) -> None:
        value, components = repl.derive_gfp_kernel_value()
        self.assertEqual(components["___GFP_IO"], 0x40)
        self.assertEqual(components["___GFP_FS"], 0x80)
        self.assertEqual(components["___GFP_DIRECT_RECLAIM"], 0x400000)
        self.assertEqual(components["___GFP_KSWAPD_RECLAIM"], 0x1000000)
        self.assertEqual(value, 0x14000C0)

    def test_lowmem_pointer_gate(self) -> None:
        self.assertTrue(repl.is_kernel_lowmem_pointer(0xFFFFFFC012300000))
        self.assertFalse(repl.is_kernel_lowmem_pointer(0))
        self.assertFalse(repl.is_kernel_lowmem_pointer(repl.ENTRY_VADDR))
        self.assertFalse(repl.is_kernel_lowmem_pointer(0xFFFFFFC012300003))


class FakeTransport:
    """Records sh strings sent and returns scripted dmesg output."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.sent: list[str] = []

    def run_serial_command(self, argv, *, host, port, timeout):
        # argv == ["run", busybox, "sh", "-c", sh_str]
        sh_str = argv[-1]
        self.sent.append(sh_str)
        # An op invocation writes the node and reads A90R back in one shell.
        if "grep -a A90R" in sh_str:
            out = self.responses.pop(0) if self.responses else ""
            return {"ok": True, "rc": 0, "stdout": out, "stderr": ""}
        # write-only / panic_on_oops / echo: no captured output
        return {"ok": True, "rc": 0, "stdout": "", "stderr": ""}


class LiveMathTests(unittest.TestCase):
    def _session(self, responses, **config_kwargs):
        fake = FakeTransport(responses)
        session = repl.ReplSession(repl.ReplConfig(settle_sec=0.0, **config_kwargs))
        session_transport = repl.transport
        self._orig = session_transport.run_serial_command
        session_transport.run_serial_command = fake.run_serial_command
        self.addCleanup(self._restore, session_transport)
        return session, fake

    def _restore(self, t):
        t.run_serial_command = self._orig

    def test_slide_math(self) -> None:
        # runtime pc = adr_self_link + slide; pick a page-granular slide.
        slide = 0x108000
        runtime_pc = repl.ADR_SELF_LINK_VADDR + slide
        session, _ = self._session([f"A90R{runtime_pc:x}\n"])
        self.assertEqual(session.slide(), slide)

    def test_peek_emits_addr_and_returns_qword(self) -> None:
        session, fake = self._session(["A90Rdeadbeef\n"])
        got = session.peek_runtime(0xFFFFFF8008080000, 8)
        self.assertEqual(got, 0xDEADBEEF)
        # the write before the dmesg read must encode op=1 + the addr
        write_sh = fake.sent[0]
        buf = decode_printf_octal(write_sh[len("printf '") : write_sh.index("'", len("printf '"))])
        self.assertEqual(buf[0x08], repl.OP_PEEK)
        self.assertEqual(struct.unpack_from("<Q", buf, 0x10)[0], 0xFFFFFF8008080000)
        self.assertEqual(struct.unpack_from("<Q", buf, 0x18)[0], 8)

    def test_peek_len_bounds(self) -> None:
        session, _ = self._session([])
        with self.assertRaises(ValueError):
            session.peek_runtime(0x1000, 9)

    def test_call_encodes_target_and_args(self) -> None:
        session, fake = self._session(["A90Rc\n"])
        ret = session.call_runtime(0xFFFFFF800813D8CC, (0x1234, 0x5678))
        self.assertEqual(ret, 0xC)
        write_sh = fake.sent[0]
        buf = decode_printf_octal(write_sh[len("printf '") : write_sh.index("'", len("printf '"))])
        self.assertEqual(buf[0x08], repl.OP_CALL)
        self.assertEqual(struct.unpack_from("<Q", buf, 0x10)[0], 0xFFFFFF800813D8CC)  # target
        self.assertEqual(struct.unpack_from("<Q", buf, 0x18)[0], 0x1234)  # x0
        self.assertEqual(struct.unpack_from("<Q", buf, 0x20)[0], 0x5678)  # x1

    def test_no_output_raises(self) -> None:
        session, _ = self._session([""], safe_op_retries=0)
        with self.assertRaises(repl.ReplTransientNoiseError):
            session.slide()

    def test_slide_retries_transient_noise_for_replay_safe_op(self) -> None:
        slide = 0x108000
        runtime_pc = repl.ADR_SELF_LINK_VADDR + slide
        session, fake = self._session(
            ["ATAT\n", f"A90R{runtime_pc:x}\n"],
            safe_op_retries=1,
            retry_delay_sec=0.0,
        )
        self.assertEqual(session.slide(), slide)
        self.assertEqual(len(fake.sent), 2)

    def test_call_noise_is_not_replayed_by_default(self) -> None:
        session, fake = self._session(
            ["ATAT\n", "A90Rc\n"],
            safe_op_retries=3,
            retry_delay_sec=0.0,
        )
        with self.assertRaises(repl.ReplTransientNoiseError):
            session.call_runtime(0xFFFFFF800813D8CC, (0x1234,))
        self.assertEqual(len(fake.sent), 1)

    def test_call_runtime_values_can_replay_when_explicitly_safe(self) -> None:
        session, fake = self._session(
            ["ATAT\n", "A90Rc\n"],
            safe_op_retries=1,
            retry_delay_sec=0.0,
        )
        self.assertEqual(
            session.call_runtime_values(0xFFFFFF800813D8CC, (0x1234,), replay_safe=True),
            [0xC],
        )
        self.assertEqual(len(fake.sent), 2)


@unittest.skipUnless(MAP_PATH.is_file(), "v2a1 System.map not generated")
class SystemMapTests(unittest.TestCase):
    def setUp(self) -> None:
        self.symbols = repl.load_system_map(MAP_PATH)

    def test_known_symbols_resolve(self) -> None:
        self.assertEqual(repl.resolve_link(self.symbols, "printk"), 0xFFFFFF800813D8CC)
        self.assertEqual(
            repl.resolve_link(self.symbols, "kgsl_pwrctrl_force_no_nap_store"),
            0xFFFFFF80089273B4,
        )
        self.assertEqual(repl.resolve_link(self.symbols, "__kmalloc"), 0xFFFFFF80082724BC)

    def test_missing_symbol_raises(self) -> None:
        with self.assertRaises(RuntimeError):
            repl.resolve_link(self.symbols, "this_symbol_does_not_exist_zzz")


@unittest.skipUnless(
    MAP_PATH.is_file() and IMAGE_PATH.is_file(),
    "v1-repl image and/or System.map not present",
)
class StaticImageCrossCheckTests(unittest.TestCase):
    def setUp(self) -> None:
        self.symbols = repl.load_system_map(MAP_PATH)
        self.image = repl.load_static_image(IMAGE_PATH)

    def test_force_no_nap_store_first_qword_is_live_proven_value(self) -> None:
        link = repl.resolve_link(self.symbols, "kgsl_pwrctrl_force_no_nap_store")
        # This is exactly what v1-repl live validation peeked (A90Ra9be47f0ca1103d0).
        self.assertEqual(self.image.u64_at_vaddr(link), 0xA9BE47F0CA1103D0)

    def test_call_targets_are_jopp_entries(self) -> None:
        for name in ("kallsyms_lookup_name", "printk", "__kmalloc", "kfree"):
            link = repl.resolve_link(self.symbols, name)
            repl.assert_jopp_entry(self.image, link, name)  # raises on failure

    def test_kmalloc_direct_scalar_abi_is_rejected(self) -> None:
        link = repl.resolve_link(self.symbols, "__kmalloc")
        with self.assertRaisesRegex(repl.ReplError, "dereferences x0"):
            repl.assert_no_precall_x0_pointer_deref(self.image, link, "__kmalloc")

    def test_printk_direct_scalar_abi_has_no_precall_x0_deref(self) -> None:
        link = repl.resolve_link(self.symbols, "printk")
        repl.assert_no_precall_x0_pointer_deref(self.image, link, "printk")

    def test_allocator_abi_audit_finds_no_live_ready_scalar(self) -> None:
        audit = repl.run_allocator_abi_audit(self.symbols, self.image)
        self.assertTrue(audit["ok"], audit)
        self.assertEqual(
            audit["decision"],
            "a90-repl-v2a2r-allocator-abi-audit-no-live-ready-scalar",
        )
        self.assertEqual(audit["live_ready_candidates"], [])
        rows = {row["symbol"]: row for row in audit["rows"]}
        self.assertIn("precall-x0-deref", rows["__kmalloc"]["blocked_reasons"][0])
        self.assertTrue(all(row["status"] == "rejected" for row in rows.values()))

    def test_allocator_export_recovery_finds_ground_truth_addresses(self) -> None:
        recovery = repl.recover_allocator_export_addresses(self.symbols, self.image)
        self.assertTrue(recovery["ok"], recovery)
        self.assertEqual(
            recovery["decision"],
            "a90-repl-v2a2rp-allocator-export-recovery-pass",
        )
        self.assertEqual(
            recovery["recovered"],
            {
                "__kmalloc": "0xffffff800826ae34",
                "kfree": "0xffffff800826b354",
                "kmalloc_order": "0xffffff8008238444",
                "kmalloc_order_trace": "0xffffff8008238484",
            },
        )
        rows = {row["symbol"]: row for row in recovery["rows"]}
        self.assertTrue(rows["__kmalloc"]["map_mismatch"])
        self.assertTrue(rows["kfree"]["map_mismatch"])
        self.assertEqual(rows["__kmalloc"]["map_ksymtab_first_qword"], "0x0")
        self.assertEqual(rows["kfree"]["map_ksymtab_first_qword"], "0x0")
        self.assertIsNone(rows["__kmalloc"]["selected_precall_x0_deref"])
        self.assertIsNone(rows["kfree"]["selected_precall_x0_deref"])
        self.assertGreater(rows["__kmalloc"]["selected_direct_bl_xref_count"], 1000)
        self.assertGreater(rows["kfree"]["selected_direct_bl_xref_count"], 10000)

    def test_resolve_verified_allocator_uses_recovered_exports(self) -> None:
        kmalloc = repl.resolve_verified(self.symbols, self.image, "__kmalloc", purpose="call")
        kfree = repl.resolve_verified(self.symbols, self.image, "kfree", purpose="call")

        self.assertTrue(kmalloc.verified, kmalloc.public_dict())
        self.assertTrue(kfree.verified, kfree.public_dict())
        self.assertEqual(kmalloc.method, "export-recovery")
        self.assertEqual(kfree.method, "export-recovery")
        self.assertEqual(kmalloc.link_vaddr, 0xFFFFFF800826AE34)
        self.assertEqual(kfree.link_vaddr, 0xFFFFFF800826B354)
        self.assertTrue(kmalloc.evidence["map_agrees_with_export"] is False)
        self.assertTrue(kfree.evidence["map_agrees_with_export"] is False)

    def test_resolve_verified_printk_uses_export_xref_ground_truth(self) -> None:
        resolution = repl.resolve_verified(self.symbols, self.image, "printk", purpose="call")

        self.assertTrue(resolution.verified, resolution.public_dict())
        self.assertEqual(resolution.method, "export-recovery")
        self.assertEqual(resolution.link_vaddr, 0xFFFFFF800813ADFC)
        self.assertEqual(resolution.evidence["export_selected_direct_bl_xref_count"], 44694)
        self.assertFalse(resolution.evidence["map_agrees_with_export"])

    def test_resolve_verified_blocks_known_unsafe_call(self) -> None:
        resolution = repl.resolve_verified(self.symbols, self.image, "kallsyms_lookup_name", purpose="call")

        self.assertFalse(resolution.verified, resolution.public_dict())
        self.assertEqual(resolution.method, "blocked-known-unsafe")
        self.assertIn("known-unsafe-live-call", resolution.evidence["blocked_reasons"][0])

    def test_resolve_verified_peek_surfaces_unverified_map_use(self) -> None:
        resolution = repl.resolve_verified(
            self.symbols,
            self.image,
            "kgsl_pwrctrl_force_no_nap_store",
            purpose="peek",
        )

        self.assertFalse(resolution.verified, resolution.public_dict())
        self.assertEqual(resolution.method, "System.map-read-only-unverified")
        self.assertEqual(resolution.link_vaddr, 0xFFFFFF80089273B4)

    def test_map_audit_uses_high_confidence_anchor_oracle(self) -> None:
        audit = repl.run_map_audit(self.symbols, self.image, row_limit=8)

        self.assertTrue(audit["ok"], audit)
        self.assertEqual(
            audit["decision"],
            "a90-repl-v2c-c2c-high-confidence-map-audit-host-pass",
        )
        self.assertEqual(audit["audited_symbol_count"], 3)
        self.assertEqual(audit["counts"]["map_match"], 0)
        self.assertEqual(audit["counts"]["map_mismatch"], 3)
        self.assertEqual(audit["counts"]["unknown"], 0)

        focus = audit["focus_rows"]
        self.assertEqual(focus["printk"]["status"], "map-mismatch")
        self.assertEqual(focus["printk"]["truth_link_vaddr"], "0xffffff800813adfc")
        self.assertEqual(focus["printk"]["map_link_vaddr"], "0xffffff800813d8cc")
        self.assertIn("stage-c-printk-signature-disagrees-with-map", focus["printk"]["map_wrong_evidence"])
        self.assertEqual(focus["__kmalloc"]["status"], "map-mismatch")
        self.assertEqual(focus["__kmalloc"]["truth_link_vaddr"], "0xffffff800826ae34")
        self.assertEqual(focus["__kmalloc"]["map_link_vaddr"], "0xffffff80082724bc")
        self.assertEqual(focus["__kmalloc"]["passing_candidate_count"], 1)
        self.assertEqual(focus["__kmalloc"]["map_direct_bl_xref_count"], 0)
        self.assertIn("map-address-independently-refuted", focus["__kmalloc"]["high_confidence_reasons"])
        self.assertEqual(focus["kfree"]["status"], "map-mismatch")
        self.assertEqual(focus["kfree"]["truth_link_vaddr"], "0xffffff800826b354")
        self.assertEqual(focus["kfree"]["map_link_vaddr"], "0xffffff800827276c")
        self.assertEqual(focus["kfree"]["passing_candidate_count"], 1)
        self.assertEqual(focus["kfree"]["map_direct_bl_xref_count"], 0)

    def test_ksymtab_abi_audit_fences_noisy_403_table(self) -> None:
        audit = repl.run_ksymtab_abi_audit(self.symbols, self.image)

        self.assertTrue(audit["ok"], audit)
        self.assertEqual(audit["decision"], "a90-repl-v2c-c2d-ksymtab-abi-audit-fenced")
        self.assertEqual(audit["source_abi_record_size"], 16)
        top_run = audit["noisy_403_table_runs"][0]
        self.assertGreater(top_run["record_count"], 100000)
        self.assertEqual(top_run["record_size"], 24)
        self.assertEqual(top_run["flags_qword"], "0x403")

        rows = audit["focus_rows"]
        for name in ("printk", "__kmalloc", "kfree"):
            self.assertEqual(rows[name]["absolute_kernel_symbol_pair_candidate_count"], 0)
            self.assertEqual(rows[name]["status"], "no-parseable-source-abi-ksymtab-row")
            self.assertGreaterEqual(rows[name]["noisy_403_candidate_count"], 1)
            self.assertTrue(rows[name]["noisy_403_candidates"][0]["inside_403_run"])
            self.assertEqual(
                rows[name]["noisy_403_candidates"][0]["classification"],
                "noisy-24-byte-0x403-record-table-not-kernel_symbol-pair",
            )

    def test_ksymtab_ground_truth_oracle_reconstructs_relocated_exports(self) -> None:
        compare_maps = {}
        if C2B_PADDING_MAP_PATH.is_file():
            compare_maps["c2b-padding"] = repl.load_system_map(C2B_PADDING_MAP_PATH)
        audit = repl.run_ksymtab_ground_truth_audit(
            self.symbols,
            self.image,
            compare_symbol_maps=compare_maps,
        )

        self.assertTrue(audit["ok"], audit)
        self.assertEqual(
            audit["decision"],
            "a90-repl-v2c-c2e-ksymtab-ground-truth-oracle-host-pass",
        )
        self.assertEqual(
            audit["oracle"]["layout"],
            "24-byte-0x403-relocation-records-reconstruct-zeroed-16-byte-ksymtab-pairs",
        )
        self.assertEqual(audit["oracle"]["selected_export_row_count"], 12518)
        self.assertEqual(audit["oracle"]["selected_unique_name_count"], 12518)
        self.assertEqual(audit["oracle"]["target_start_vaddr"], "0xffffff800a562d60")
        self.assertEqual(audit["oracle"]["target_end_vaddr"], "0xffffff800a594270")

        anchors = audit["anchor_results"]
        self.assertEqual(anchors["__kmalloc"]["status"], "anchor-match")
        self.assertEqual(anchors["__kmalloc"]["truth_link_vaddr"], "0xffffff800826ae34")
        self.assertEqual(anchors["kfree"]["status"], "anchor-match")
        self.assertEqual(anchors["kfree"]["truth_link_vaddr"], "0xffffff800826b354")
        self.assertEqual(anchors["kgsl_pwrctrl_force_no_nap_store"]["status"], "anchor-match")
        self.assertEqual(
            anchors["kgsl_pwrctrl_force_no_nap_store"]["ksymtab_scope"],
            "not-exported",
        )
        self.assertEqual(anchors["printk"]["status"], "anchor-match")
        self.assertEqual(anchors["printk"]["truth_link_vaddr"], "0xffffff800813adfc")
        self.assertEqual(anchors["printk"]["export_row_link_vaddr"], "0xffffff800813adfc")
        self.assertFalse(anchors["printk"]["export_row_conflicts_with_semantic_anchor"])

        self.assertEqual(
            audit["current_map_drift"]["counts"],
            {"map_match": 0, "map_mismatch": 12518, "missing_map_symbol": 0},
        )
        if compare_maps:
            self.assertEqual(
                audit["compare_map_drift"]["c2b-padding"]["counts"],
                {"map_match": 12515, "map_mismatch": 3, "missing_map_symbol": 0},
            )
            c2b_mismatches = {
                row["symbol"]
                for row in audit["compare_map_drift"]["c2b-padding"]["sample_rows"]
            }
            self.assertEqual(
                c2b_mismatches,
                {
                    "ehci_reset",
                    "iio_read_channel_ext_info",
                    "iio_write_channel_ext_info",
                },
            )

    def test_assert_jopp_entry_rejects_non_entry(self) -> None:
        link = repl.resolve_link(self.symbols, "printk")
        with self.assertRaises(repl.ReplError):
            repl.assert_jopp_entry(self.image, link + 8, "printk+8")

    def test_symbol_strings_are_nul_bounded(self) -> None:
        for name in ("printk", "__kmalloc", "kallsyms_lookup_name"):
            vaddr = self.image.find_symbol_string_vaddr(name)
            off = self.image.kernel_off + (vaddr - repl.stage_c.KERNEL_FILE_VADDR_BASE)
            data = self.image.data
            self.assertEqual(data[off : off + len(name)], name.encode("ascii"))
            self.assertEqual(data[off + len(name)], 0)  # trailing NUL


@unittest.skipUnless(
    C2B_PADDING_MAP_PATH.is_file() and IMAGE_PATH.is_file(),
    "promoted v2c System.map and/or v1-repl image not present",
)
class CallSafetyClassificationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.symbols = repl.load_system_map(C2B_PADDING_MAP_PATH)
        self.image = repl.load_static_image(IMAGE_PATH)

    def _row(self, name: str):
        return repl.classify_call_safety(
            self.symbols,
            self.image,
            name,
            include_objdump=False,
        )

    def test_proven_live_call_targets_stay_safe(self) -> None:
        printk = self._row("printk")
        self.assertEqual(printk["tier"], repl.CALL_SAFETY_SAFE_WITH_VALID_PTR)
        self.assertTrue(printk["safe_group"])
        self.assertEqual(printk["resolution"]["link_vaddr"], "0xffffff800813adfc")
        self.assertNotEqual(printk["resolution"]["link_vaddr"], "0xffffff800813d8cc")
        self.assertEqual(printk["required_valid_pointer_args"], {"0": "fmt"})
        self.assertGreater(
            printk["signals"]["direct_bl_xref_count"],
            1000,
        )
        self.assertTrue(printk["signals"]["variadic_prologue_matches_printk"])

        kmalloc = self._row("__kmalloc")
        self.assertEqual(kmalloc["tier"], repl.CALL_SAFETY_SAFE_SCALAR)
        self.assertTrue(kmalloc["safe_group"])
        self.assertEqual(kmalloc["resolution"]["link_vaddr"], "0xffffff800826ae34")
        self.assertEqual(kmalloc["signals"]["arg_pointer_derefs_before_first_bl_or_ret"], [])
        self.assertTrue(
            kmalloc["signals"]["arg_taint_flow"]["safe_scalar_positive_no_arg_memory_base_flow"]
        )

        kfree = self._row("kfree")
        self.assertEqual(kfree["tier"], repl.CALL_SAFETY_SAFE_WITH_VALID_PTR)
        self.assertTrue(kfree["safe_group"])
        self.assertEqual(kfree["resolution"]["link_vaddr"], "0xffffff800826b354")
        self.assertEqual(
            kfree["required_valid_pointer_args"],
            {"0": "kmalloc-object-or-NULL"},
        )
        self.assertFalse(
            kfree["signals"]["arg_taint_flow"]["safe_scalar_positive_no_arg_memory_base_flow"]
        )
        self.assertGreater(
            kfree["signals"]["arg_taint_flow"]["arg_memory_base_use_count"],
            0,
        )

    def test_known_unsafe_and_behavior_changing_anchors(self) -> None:
        kallsyms = self._row("kallsyms_lookup_name")
        self.assertEqual(kallsyms["tier"], repl.CALL_SAFETY_DENY)
        self.assertFalse(kallsyms["safe_group"])
        self.assertEqual(kallsyms["resolution"]["method"], "blocked-known-unsafe")
        self.assertIn("known-unsafe-live-call", " ".join(kallsyms["reasons"]))

        commit_creds = self._row("commit_creds")
        self.assertEqual(commit_creds["tier"], repl.CALL_SAFETY_BEHAVIOR_CHANGING)
        self.assertFalse(commit_creds["safe_group"])
        self.assertTrue(commit_creds["resolution"]["verified"])

    def test_safe_with_valid_pointer_seed_records_required_args(self) -> None:
        kernel_read = self._row("kernel_read")
        self.assertEqual(kernel_read["tier"], repl.CALL_SAFETY_SAFE_WITH_VALID_PTR)
        self.assertEqual(
            kernel_read["required_valid_pointer_args"],
            {"0": "struct-file", "1": "buffer", "3": "loff_t-pos"},
        )
        self.assertTrue(kernel_read["resolution"]["verified"])

        strnlen = self._row("strnlen")
        self.assertEqual(strnlen["tier"], repl.CALL_SAFETY_SAFE_WITH_VALID_PTR)
        self.assertEqual(strnlen["required_valid_pointer_args"], {"0": "string-buffer"})
        self.assertTrue(strnlen["resolution"]["verified"])
        self.assertEqual(strnlen["resolution"]["method"], "leaf-map-disasm+xref")
        self.assertGreaterEqual(strnlen["signals"]["direct_bl_xref_count"], 100)
        self.assertTrue(strnlen["signals"]["leaf"])

        strlen = self._row("strlen")
        self.assertEqual(strlen["tier"], repl.CALL_SAFETY_SAFE_WITH_VALID_PTR)
        self.assertEqual(strlen["required_valid_pointer_args"], {"0": "string-buffer"})
        self.assertTrue(strlen["resolution"]["verified"])
        self.assertEqual(strlen["resolution"]["method"], "leaf-map-disasm+xref")
        self.assertGreaterEqual(strlen["signals"]["direct_bl_xref_count"], 1000)
        self.assertTrue(strlen["signals"]["leaf"])

        strscpy = self._row("strscpy")
        self.assertEqual(strscpy["tier"], repl.CALL_SAFETY_SAFE_WITH_VALID_PTR)
        self.assertEqual(
            strscpy["required_valid_pointer_args"],
            {"0": "destination-buffer", "1": "source-string-buffer"},
        )
        self.assertTrue(strscpy["resolution"]["verified"])
        self.assertEqual(strscpy["resolution"]["method"], "export-recovery")
        self.assertGreaterEqual(strscpy["signals"]["direct_bl_xref_count"], 8)
        self.assertTrue(strscpy["signals"]["leaf"])

        strlcpy = self._row("strlcpy")
        self.assertEqual(strlcpy["tier"], repl.CALL_SAFETY_SAFE_WITH_VALID_PTR)
        self.assertEqual(
            strlcpy["required_valid_pointer_args"],
            {"0": "destination-buffer", "1": "source-string-buffer"},
        )
        self.assertTrue(strlcpy["resolution"]["verified"])
        self.assertEqual(strlcpy["resolution"]["method"], "export-recovery")
        self.assertGreaterEqual(strlcpy["signals"]["direct_bl_xref_count"], 900)
        self.assertFalse(strlcpy["signals"]["leaf"])

        strncpy = self._row("strncpy")
        self.assertEqual(strncpy["tier"], repl.CALL_SAFETY_SAFE_WITH_VALID_PTR)
        self.assertEqual(
            strncpy["required_valid_pointer_args"],
            {"0": "destination-buffer", "1": "source-string-buffer"},
        )
        self.assertTrue(strncpy["resolution"]["verified"])
        self.assertEqual(strncpy["resolution"]["method"], "export-recovery")
        self.assertGreaterEqual(strncpy["signals"]["direct_bl_xref_count"], 100)
        self.assertTrue(strncpy["signals"]["leaf"])

        memcmp = self._row("memcmp")
        self.assertEqual(memcmp["tier"], repl.CALL_SAFETY_SAFE_WITH_VALID_PTR)
        self.assertEqual(
            memcmp["required_valid_pointer_args"],
            {"0": "left-buffer", "1": "right-buffer"},
        )
        self.assertTrue(memcmp["resolution"]["verified"])
        self.assertEqual(memcmp["resolution"]["method"], "leaf-map-disasm+xref")
        self.assertGreaterEqual(memcmp["signals"]["direct_bl_xref_count"], 500)
        self.assertTrue(memcmp["signals"]["leaf"])

        strrchr = self._row("strrchr")
        self.assertEqual(strrchr["tier"], repl.CALL_SAFETY_SAFE_WITH_VALID_PTR)
        self.assertEqual(strrchr["required_valid_pointer_args"], {"0": "string-buffer"})
        self.assertTrue(strrchr["resolution"]["verified"])
        self.assertEqual(strrchr["resolution"]["method"], "leaf-map-disasm+xref")
        self.assertGreaterEqual(strrchr["signals"]["direct_bl_xref_count"], 1000)
        self.assertTrue(strrchr["signals"]["leaf"])

    def test_non_seeded_targets_are_denied_by_default(self) -> None:
        row = self._row("kgsl_pwrctrl_force_no_nap_store")
        self.assertEqual(row["tier"], repl.CALL_SAFETY_DENY)
        self.assertFalse(row["safe_group"])
        self.assertIn("deny-by-default:not-in-vetted-seed-whitelist", row["reasons"])

    def test_seed_inventory_summary_counts_tiers(self) -> None:
        summary = repl.run_call_safety_classify(
            self.symbols,
            self.image,
            (),
            include_objdump=False,
        )
        self.assertTrue(summary["ok"], summary)
        self.assertTrue(summary["host_only"])
        self.assertFalse(summary["device_action"])
        self.assertEqual(summary["seed_whitelist_count"], len(repl.CALL_SAFETY_SEEDS))
        self.assertEqual(summary["counts"][repl.CALL_SAFETY_SAFE_SCALAR], 1)
        self.assertGreaterEqual(summary["counts"][repl.CALL_SAFETY_SAFE_WITH_VALID_PTR], 8)
        self.assertGreaterEqual(summary["counts"][repl.CALL_SAFETY_BEHAVIOR_CHANGING], 4)
        self.assertEqual(summary["counts"][repl.CALL_SAFETY_DENY], 1)

    def test_call_safety_gate_requires_pointer_tokens_for_safe_with_valid_ptr(self) -> None:
        with self.assertRaisesRegex(repl.ReplError, "SAFE-WITH-VALID-PTR requires"):
            repl.require_call_safety_for_call(
                self.symbols,
                self.image,
                "printk",
                ("0x1234",),
            )

        row = repl.require_call_safety_for_call(
            self.symbols,
            self.image,
            "printk",
            ("@repl_format",),
        )
        self.assertEqual(row["tier"], repl.CALL_SAFETY_SAFE_WITH_VALID_PTR)

    def test_kfree_requires_verified_pointer_or_null(self) -> None:
        with self.assertRaisesRegex(repl.ReplError, "SAFE-WITH-VALID-PTR requires"):
            repl.require_call_safety_for_call(
                self.symbols,
                self.image,
                "kfree",
                ("0x1234",),
            )

        row = repl.require_call_safety_for_call(
            self.symbols,
            self.image,
            "kfree",
            ("0x0",),
        )
        self.assertEqual(row["tier"], repl.CALL_SAFETY_SAFE_WITH_VALID_PTR)

        row = repl.require_call_safety_for_call(
            self.symbols,
            self.image,
            "kfree",
            ("@owned_kmalloc_ptr",),
        )
        self.assertEqual(row["tier"], repl.CALL_SAFETY_SAFE_WITH_VALID_PTR)

    def test_unvetted_override_does_not_override_deny(self) -> None:
        with self.assertRaisesRegex(repl.ReplError, "DENY cannot be overridden"):
            repl.require_call_safety_for_call(
                self.symbols,
                self.image,
                "kallsyms_lookup_name",
                ("@kallsyms_lookup_name",),
                allow_unvetted_token=repl.CALL_SAFETY_ALLOW_UNVETTED_TOKEN,
            )

    def test_unvetted_override_requires_exact_token_for_non_safe_tier(self) -> None:
        with self.assertRaisesRegex(repl.ReplError, "invalid --allow-unvetted token"):
            repl.require_call_safety_for_call(
                self.symbols,
                self.image,
                "commit_creds",
                ("@commit_creds",),
                allow_unvetted_token="wrong",
            )

        row = repl.require_call_safety_for_call(
            self.symbols,
            self.image,
            "commit_creds",
            ("@commit_creds",),
            allow_unvetted_token=repl.CALL_SAFETY_ALLOW_UNVETTED_TOKEN,
        )
        self.assertEqual(row["tier"], repl.CALL_SAFETY_BEHAVIOR_CHANGING)
        self.assertTrue(row["override_used"])

    def test_source_signature_oracle_distinguishes_scalar_and_pointer_args(self) -> None:
        if not KERNEL_SOURCE_ROOT.is_dir():
            self.skipTest("kernel source tree not present")

        kmalloc = repl.lookup_source_signature("__kmalloc", source_root=KERNEL_SOURCE_ROOT)
        self.assertEqual(kmalloc["status"], "found", kmalloc)
        self.assertEqual(kmalloc["selected"]["pointer_arg_indices"], [])
        self.assertIn("size_t size", kmalloc["selected"]["signature"])

        kfree = repl.lookup_source_signature("kfree", source_root=KERNEL_SOURCE_ROOT)
        self.assertEqual(kfree["status"], "found", kfree)
        self.assertEqual(kfree["selected"]["pointer_arg_indices"], [0])
        self.assertIn("const void *", kfree["selected"]["signature"])

        ksize = repl.lookup_source_signature("ksize", source_root=KERNEL_SOURCE_ROOT)
        self.assertTrue(ksize["found"], ksize)
        self.assertTrue(ksize["has_pointer_arg"], ksize)
        self.assertEqual(ksize["pointer_arg_indices"], [0])
        self.assertEqual(ksize["candidate_scan_strategy"], "hint")
        self.assertLessEqual(ksize["candidate_file_count"], 1)
        self.assertTrue(ksize["candidate_files_sample"][0].endswith("include/linux/slab.h"))
        self.assertTrue(ksize["selected"]["path"].endswith("include/linux/slab.h"))

        strlcpy = repl.lookup_source_signature("strlcpy", source_root=KERNEL_SOURCE_ROOT)
        self.assertEqual(strlcpy["status"], "found", strlcpy)
        self.assertEqual(strlcpy["selected"]["pointer_arg_indices"], [0, 1])
        self.assertEqual(strlcpy["selected"]["signature"], "size_t strlcpy(char *, const char *, size_t)")

        strnlen = repl.lookup_source_signature("strnlen", source_root=KERNEL_SOURCE_ROOT)
        self.assertEqual(strnlen["status"], "found", strnlen)
        self.assertEqual(strnlen["selected"]["pointer_arg_indices"], [0])
        self.assertEqual(strnlen["selected"]["signature"], "extern __kernel_size_t strnlen(const char *,__kernel_size_t)")
        self.assertTrue(strnlen["selected"]["path"].endswith("include/linux/string.h"))

        strlen = repl.lookup_source_signature("strlen", source_root=KERNEL_SOURCE_ROOT)
        self.assertEqual(strlen["status"], "found", strlen)
        self.assertEqual(strlen["selected"]["pointer_arg_indices"], [0])
        self.assertEqual(strlen["selected"]["signature"], "extern __kernel_size_t strlen(const char *)")
        self.assertTrue(strlen["selected"]["path"].endswith("include/linux/string.h"))

        strscpy = repl.lookup_source_signature("strscpy", source_root=KERNEL_SOURCE_ROOT)
        self.assertEqual(strscpy["status"], "found", strscpy)
        self.assertEqual(strscpy["selected"]["pointer_arg_indices"], [0, 1])
        self.assertEqual(strscpy["selected"]["signature"], "ssize_t strscpy(char *, const char *, size_t)")
        self.assertTrue(strscpy["selected"]["path"].endswith("include/linux/string.h"))

        strncpy = repl.lookup_source_signature("strncpy", source_root=KERNEL_SOURCE_ROOT)
        self.assertEqual(strncpy["status"], "found", strncpy)
        self.assertEqual(strncpy["selected"]["pointer_arg_indices"], [0, 1])
        self.assertEqual(
            strncpy["selected"]["signature"],
            "extern char * strncpy(char *,const char *, __kernel_size_t)",
        )
        self.assertTrue(strncpy["selected"]["path"].endswith("include/linux/string.h"))

        memcmp = repl.lookup_source_signature("memcmp", source_root=KERNEL_SOURCE_ROOT)
        self.assertEqual(memcmp["status"], "found", memcmp)
        self.assertEqual(memcmp["selected"]["pointer_arg_indices"], [0, 1])
        self.assertEqual(
            memcmp["selected"]["signature"],
            "extern int memcmp(const void *,const void *,__kernel_size_t)",
        )
        self.assertTrue(memcmp["selected"]["path"].endswith("include/linux/string.h"))

        strrchr = repl.lookup_source_signature("strrchr", source_root=KERNEL_SOURCE_ROOT)
        self.assertEqual(strrchr["status"], "found", strrchr)
        self.assertEqual(strrchr["selected"]["pointer_arg_indices"], [0])
        self.assertEqual(
            strrchr["selected"]["signature"],
            "extern char * strrchr(const char *,int)",
        )
        self.assertTrue(strrchr["selected"]["path"].endswith("include/linux/string.h"))

    def test_call_safety_sweep_is_advisory_and_does_not_promote_gate(self) -> None:
        if not KERNEL_SOURCE_ROOT.is_dir():
            self.skipTest("kernel source tree not present")

        seed_snapshot = repr(repl.CALL_SAFETY_SEEDS)
        summary = repl.run_call_safety_sweep(
            self.symbols,
            self.image,
            explicit_symbols=("__kmalloc", "kfree", "strcat", "kgsl_pwrctrl_force_no_nap_store"),
            limit=0,
            source_root=KERNEL_SOURCE_ROOT,
            include_objdump=False,
        )
        self.assertTrue(summary["ok"], summary)
        self.assertTrue(summary["host_only"])
        self.assertFalse(summary["device_action"])
        self.assertFalse(summary["network_dependency"])
        self.assertEqual(repr(repl.CALL_SAFETY_SEEDS), seed_snapshot)

        rows = {row["symbol"]: row for row in summary["rows"]}
        self.assertEqual(rows["__kmalloc"]["advisory"]["source_pointer_arg_indices"], [])
        self.assertNotEqual(
            rows["__kmalloc"]["advisory"]["tier"],
            repl.CALL_SAFETY_SAFE_WITH_VALID_PTR,
        )
        self.assertEqual(rows["kfree"]["advisory"]["source_pointer_arg_indices"], [0])
        self.assertNotEqual(rows["kfree"]["advisory"]["tier"], repl.CALL_SAFETY_SAFE_SCALAR)

        kgsl_store = rows["kgsl_pwrctrl_force_no_nap_store"]
        self.assertEqual(kgsl_store["source"]["status"], "missing")
        self.assertEqual(kgsl_store["advisory"]["tier"], repl.CALL_SAFETY_DENY)
        self.assertIn("source-missing", kgsl_store["advisory"]["danger_flags"])

        strcat = rows["strcat"]
        self.assertEqual(strcat["gate_tier"], repl.CALL_SAFETY_DENY)
        self.assertEqual(strcat["source"]["status"], "found")
        self.assertEqual(strcat["advisory"]["tier"], repl.CALL_SAFETY_SAFE_WITH_VALID_PTR)
        self.assertFalse(strcat["advisory"]["candidate_safe"])
        self.assertIn(
            "unseeded-arg-memory-flow-without-gate-pointer-contract",
            strcat["advisory"]["danger_flags"],
        )
        with self.assertRaisesRegex(repl.ReplError, "call-safety gate refused"):
            repl.require_call_safety_for_call(
                self.symbols,
                self.image,
                "strcat",
                ("@dst", "@src", "0x10"),
            )

    def test_gate2_source_oracle_blocks_init_and_unseeded_arg_flow(self) -> None:
        if not KERNEL_SOURCE_ROOT.is_dir():
            self.skipTest("kernel source tree not present")

        summary = repl.run_call_safety_sweep(
            self.symbols,
            self.image,
            explicit_symbols=(
                "ksize",
                "kfree_const",
                "kmem_cache_init",
                "kmem_cache_shrink",
                "kfree_skb_partial",
            ),
            limit=0,
            source_root=KERNEL_SOURCE_ROOT,
            include_objdump=False,
        )
        self.assertTrue(summary["ok"], summary)
        self.assertTrue(summary["offline_source_oracle"])
        self.assertFalse(summary["device_action"])
        self.assertFalse(summary["network_dependency"])

        rows = {row["symbol"]: row for row in summary["rows"]}

        ksize = rows["ksize"]
        self.assertTrue(ksize["source"]["found"], ksize)
        self.assertTrue(ksize["source"]["has_pointer_arg"], ksize)
        self.assertEqual(ksize["source"]["pointer_arg_indices"], [0])
        self.assertTrue(ksize["source"]["selected"]["path"].endswith("include/linux/slab.h"))
        self.assertEqual(ksize["advisory"]["source_pointer_arg_indices"], [0])
        self.assertEqual(ksize["source_signature"], "size_t ksize(const void *)")

        kmem_cache_init = rows["kmem_cache_init"]
        self.assertFalse(kmem_cache_init["advisory"]["candidate_safe"])
        self.assertIn(
            "source-__init-annotation",
            kmem_cache_init["source"]["selected"]["annotation_flags"],
        )
        self.assertIn(
            "source-__init-annotation",
            kmem_cache_init["advisory"]["danger_flags"],
        )
        self.assertEqual(
            kmem_cache_init["source_signature"],
            "void __init kmem_cache_init(void)",
        )
        self.assertEqual(kmem_cache_init["source_annotation_flags"], ["source-__init-annotation"])

        for name in ("kfree_const", "kmem_cache_shrink"):
            row = rows[name]
            self.assertFalse(row["gate_seeded"])
            self.assertTrue(row["source"]["has_pointer_arg"], row)
            self.assertEqual(row["advisory"]["source_pointer_arg_indices"], [0])
            self.assertEqual(row["advisory"]["source_or_arg_memory_indices"], [0])
            self.assertFalse(row["advisory"]["candidate_safe"])
            self.assertIn(
                "unseeded-arg-memory-flow-without-gate-pointer-contract",
                row["advisory"]["danger_flags"],
            )
            self.assertIsNotNone(row["source_signature"])
            self.assertEqual(row["source_annotation_flags"], [])

        kfree_skb_partial = rows["kfree_skb_partial"]
        self.assertFalse(kfree_skb_partial["gate_seeded"])
        self.assertFalse(kfree_skb_partial["advisory"]["candidate_safe"])
        self.assertGreater(
            kfree_skb_partial["signals"]["arg_taint_flow"]["arg_memory_base_use_count"],
            0,
        )
        self.assertIn(
            "unseeded-arg-memory-flow-without-gate-pointer-contract",
            kfree_skb_partial["advisory"]["danger_flags"],
        )

    def test_u4_family_sweep_verdicts_are_pinned(self) -> None:
        if not KERNEL_SOURCE_ROOT.is_dir():
            self.skipTest("kernel source tree not present")

        allocator = repl.run_call_safety_sweep(
            self.symbols,
            self.image,
            families=("allocator",),
            limit=80,
            source_root=KERNEL_SOURCE_ROOT,
            include_objdump=False,
        )
        self.assertTrue(allocator["ok"], allocator)
        self.assertTrue(allocator["host_only"])
        self.assertFalse(allocator["device_action"])
        self.assertFalse(allocator["network_dependency"])
        self.assertEqual(
            [row["symbol"] for row in allocator["candidate_safe_ranked"]],
            ["ksize"],
        )
        allocator_rows = {row["symbol"]: row for row in allocator["rows"]}
        self.assertIn(
            "source-__init-annotation",
            allocator_rows["kmem_cache_init"]["advisory"]["danger_flags"],
        )
        self.assertIn(
            "unseeded-arg-memory-flow-without-gate-pointer-contract",
            allocator_rows["kfree_skb_partial"]["advisory"]["danger_flags"],
        )
        for name in ("kfree_const", "kmem_cache_shrink"):
            self.assertFalse(allocator_rows[name]["advisory"]["candidate_safe"])
            self.assertIn(
                "unseeded-arg-memory-flow-without-gate-pointer-contract",
                allocator_rows[name]["advisory"]["danger_flags"],
            )

        read_io = repl.run_call_safety_sweep(
            self.symbols,
            self.image,
            families=("read-io",),
            limit=40,
            source_root=KERNEL_SOURCE_ROOT,
            include_objdump=False,
        )
        self.assertTrue(read_io["ok"], read_io)
        self.assertTrue(read_io["host_only"])
        self.assertFalse(read_io["device_action"])
        self.assertFalse(read_io["network_dependency"])
        self.assertEqual(
            [row["symbol"] for row in read_io["candidate_safe_ranked"]],
            ["filp_close", "filp_open", "kernel_read"],
        )


def _buf_from_op_sh(sh_str: str) -> bytes:
    octal = sh_str[len("printf '") : sh_str.index("'", len("printf '"))]
    return decode_printf_octal(octal)


class FaithfulFakeTransport:
    """Simulates the live REPL: decodes the op buffer the driver writes and
    returns the exact A90R line(s) the real stub would print, for a chosen
    slide, the real System.map, and the real v1-repl image."""

    def __init__(self, slide, symbols, image):
        self.slide = slide
        self.symbols = symbols
        self.image = image
        recovery = repl.recover_allocator_export_addresses(self.symbols, self.image)
        self.kmalloc_link = int(recovery["recovered"]["__kmalloc"], 16)
        self.kfree_link = int(recovery["recovered"]["kfree"], 16)
        self.printk_link = repl.resolve_verified(
            self.symbols,
            self.image,
            "printk",
            purpose="call",
        ).link_vaddr
        self.ksize_link = repl.resolve_verified(
            self.symbols,
            self.image,
            "ksize",
            purpose="call",
            allow_pre_arg_deref=True,
        ).link_vaddr
        self.strnlen_link = repl.resolve_verified(
            self.symbols,
            self.image,
            "strnlen",
            purpose="call",
            allow_pre_arg_deref=True,
        ).link_vaddr
        self.strlen_link = repl.resolve_verified(
            self.symbols,
            self.image,
            "strlen",
            purpose="call",
            allow_pre_arg_deref=True,
        ).link_vaddr
        self.strscpy_link = repl.resolve_verified(
            self.symbols,
            self.image,
            "strscpy",
            purpose="call",
            allow_pre_arg_deref=True,
        ).link_vaddr
        self.strlcpy_link = repl.resolve_verified(
            self.symbols,
            self.image,
            "strlcpy",
            purpose="call",
            allow_pre_arg_deref=True,
        ).link_vaddr
        self.strncpy_link = repl.resolve_verified(
            self.symbols,
            self.image,
            "strncpy",
            purpose="call",
            allow_pre_arg_deref=True,
        ).link_vaddr
        self.memcmp_link = repl.resolve_verified(
            self.symbols,
            self.image,
            "memcmp",
            purpose="call",
            allow_pre_arg_deref=True,
        ).link_vaddr
        self.strrchr_link = repl.resolve_verified(
            self.symbols,
            self.image,
            "strrchr",
            purpose="call",
            allow_pre_arg_deref=True,
        ).link_vaddr
        self.filp_open_link = repl.resolve_verified(
            self.symbols,
            self.image,
            "filp_open",
            purpose="call",
            allow_pre_arg_deref=True,
        ).link_vaddr
        self.filp_close_link = repl.resolve_verified(
            self.symbols,
            self.image,
            "filp_close",
            purpose="call",
            allow_pre_arg_deref=True,
        ).link_vaddr
        self.kernel_read_link = repl.resolve_verified(
            self.symbols,
            self.image,
            "kernel_read",
            purpose="call",
            allow_pre_arg_deref=True,
        ).link_vaddr
        self.heap_ptr = 0xFFFFFFC012300000
        self.next_heap_ptr = self.heap_ptr
        self.heap: dict[int, int] = {}
        self.allocated: set[int] = set()
        self.freed: list[int] = []
        self.ksize_return = 0x1000
        self.file_ptr = 0xFFFFFFC045670000
        self.opened_files: set[int] = set()
        self.closed_files: list[int] = []
        self.kernel_read_payload = b"\x7fELF" + b"A90READPROOF"
        self.op_count = 0

    def _heap_bytes(self, addr: int, length: int) -> bytes:
        out = bytearray()
        for offset in range(length):
            qaddr = addr + ((offset // 8) * 8)
            shift = (offset % 8) * 8
            out.append((self.heap.get(qaddr, 0) >> shift) & 0xFF)
        return bytes(out)

    def _set_heap_bytes(self, addr: int, data: bytes) -> None:
        for offset in range(0, len(data), 8):
            chunk = data[offset:offset + 8]
            self.heap[addr + offset] = int.from_bytes(chunk.ljust(8, b"\x00"), "little")

    def run_serial_command(self, argv, *, host, port, timeout):
        sh_str = argv[-1]
        if "grep -a A90R" not in sh_str:
            return {"ok": True, "rc": 0, "stdout": "", "stderr": ""}
        self.op_count += 1
        buf = _buf_from_op_sh(sh_str)
        op = buf[8]
        import struct as _s
        arg0 = _s.unpack_from("<Q", buf, 0x10)[0]
        arg1 = _s.unpack_from("<Q", buf, 0x18)[0]
        arg2 = _s.unpack_from("<Q", buf, 0x20)[0]
        arg3 = _s.unpack_from("<Q", buf, 0x28)[0]
        arg4 = _s.unpack_from("<Q", buf, 0x30)[0]
        lines = []
        if op == repl.OP_SLIDE:
            lines.append(f"A90R{(repl.ADR_SELF_LINK_VADDR + self.slide):x}")
        elif op == repl.OP_PEEK:
            if arg0 in self.heap:
                lines.append(f"A90R{self.heap[arg0]:x}")
            else:
                link = arg0 - self.slide
                lines.append(f"A90R{self.image.u64_at_vaddr(link):x}")
        elif op == repl.OP_POKE:
            if arg2 == 8:
                self.heap[arg0] = arg1 & repl.MASK64
            elif arg2 == 4:
                current = self.heap.get(arg0, 0)
                self.heap[arg0] = (current & ~0xFFFFFFFF) | (arg1 & 0xFFFFFFFF)
            else:
                raise AssertionError(f"unexpected poke width: {arg2}")
            lines.append(f"A90R{arg2:x}")
        elif op == repl.OP_CALL:
            kmalloc = self.kmalloc_link + self.slide
            kfree = self.kfree_link + self.slide
            assert self.printk_link is not None
            printk = self.printk_link + self.slide
            assert self.ksize_link is not None
            ksize = self.ksize_link + self.slide
            assert self.strnlen_link is not None
            strnlen = self.strnlen_link + self.slide
            assert self.strlen_link is not None
            strlen = self.strlen_link + self.slide
            assert self.strscpy_link is not None
            strscpy = self.strscpy_link + self.slide
            assert self.strlcpy_link is not None
            strlcpy = self.strlcpy_link + self.slide
            assert self.strncpy_link is not None
            strncpy = self.strncpy_link + self.slide
            assert self.memcmp_link is not None
            memcmp = self.memcmp_link + self.slide
            assert self.strrchr_link is not None
            strrchr = self.strrchr_link + self.slide
            assert self.filp_open_link is not None
            filp_open = self.filp_open_link + self.slide
            assert self.filp_close_link is not None
            filp_close = self.filp_close_link + self.slide
            assert self.kernel_read_link is not None
            kernel_read = self.kernel_read_link + self.slide
            if arg0 == kmalloc:
                ptr = self.next_heap_ptr
                self.next_heap_ptr += 0x1000
                self.allocated.add(ptr)
                lines.append(f"A90R{ptr:x}")
            elif arg0 == kfree:
                self.freed.append(arg1)
                self.allocated.discard(arg1)
                lines.append("A90R0")
            elif arg0 == ksize:
                if arg1 not in self.allocated:
                    raise AssertionError(f"ksize arg is not an allocated pointer: {arg1:#x}")
                lines.append(f"A90R{self.ksize_return:x}")
            elif arg0 == strnlen:
                if arg1 not in self.allocated:
                    raise AssertionError(f"strnlen arg is not an allocated pointer: {arg1:#x}")
                data = self._heap_bytes(arg1, arg2)
                nul = data.find(b"\x00")
                length = arg2 if nul < 0 else nul
                lines.append(f"A90R{length:x}")
            elif arg0 == strlen:
                if arg1 not in self.allocated:
                    raise AssertionError(f"strlen arg is not an allocated pointer: {arg1:#x}")
                data = self._heap_bytes(arg1, repl.STRLEN_ZERO_FILL_LEN)
                nul = data.find(b"\x00")
                if nul < 0:
                    raise AssertionError("strlen proof buffer is not NUL-terminated in scan window")
                lines.append(f"A90R{nul:x}")
            elif arg0 == strscpy:
                if arg1 not in self.allocated:
                    raise AssertionError(f"strscpy dst is not an allocated pointer: {arg1:#x}")
                if arg2 not in self.allocated:
                    raise AssertionError(f"strscpy src is not an allocated pointer: {arg2:#x}")
                if arg3 != repl.STRSCPY_PROOF_SIZE:
                    raise AssertionError(f"unexpected strscpy size: {arg3:#x}")
                data = self._heap_bytes(arg2, arg3)
                nul = data.find(b"\x00")
                if nul < 0:
                    raise AssertionError("strscpy source is not NUL-terminated within size")
                self._set_heap_bytes(arg1, data[:nul + 1])
                lines.append(f"A90R{nul:x}")
            elif arg0 == strlcpy:
                if arg1 not in self.allocated:
                    raise AssertionError(f"strlcpy dst is not an allocated pointer: {arg1:#x}")
                if arg2 not in self.allocated:
                    raise AssertionError(f"strlcpy src is not an allocated pointer: {arg2:#x}")
                if arg3 != repl.STRLCPY_PROOF_SIZE:
                    raise AssertionError(f"unexpected strlcpy size: {arg3:#x}")
                data = self._heap_bytes(arg2, repl.STRLCPY_SRC_ZERO_FILL_LEN)
                nul = data.find(b"\x00")
                if nul < 0:
                    raise AssertionError("strlcpy source is not NUL-terminated in scan window")
                copy_len = min(nul, arg3 - 1) if arg3 else 0
                if arg3:
                    self._set_heap_bytes(arg1, data[:copy_len] + b"\x00")
                lines.append(f"A90R{nul:x}")
            elif arg0 == strncpy:
                if arg1 not in self.allocated:
                    raise AssertionError(f"strncpy dst is not an allocated pointer: {arg1:#x}")
                if arg2 not in self.allocated:
                    raise AssertionError(f"strncpy src is not an allocated pointer: {arg2:#x}")
                if arg3 != repl.STRNCPY_PROOF_SIZE:
                    raise AssertionError(f"unexpected strncpy count: {arg3:#x}")
                data = self._heap_bytes(arg2, arg3)
                nul = data.find(b"\x00")
                if nul < 0:
                    copied = data[:arg3]
                else:
                    copied = data[:nul + 1] + (b"\x00" * (arg3 - (nul + 1)))
                self._set_heap_bytes(arg1, copied[:arg3])
                lines.append(f"A90R{arg1:x}")
            elif arg0 == memcmp:
                if arg1 not in self.allocated:
                    raise AssertionError(f"memcmp left is not an allocated pointer: {arg1:#x}")
                if arg2 not in self.allocated:
                    raise AssertionError(f"memcmp right is not an allocated pointer: {arg2:#x}")
                if arg3 != repl.MEMCMP_PROOF_SIZE:
                    raise AssertionError(f"unexpected memcmp size: {arg3:#x}")
                left = self._heap_bytes(arg1, arg3)
                right = self._heap_bytes(arg2, arg3)
                result = 0
                for left_byte, right_byte in zip(left, right, strict=True):
                    if left_byte != right_byte:
                        result = left_byte - right_byte
                        break
                if result < 0:
                    result &= 0xFFFFFFFF
                lines.append(f"A90R{result:x}")
            elif arg0 == strrchr:
                if arg1 not in self.allocated:
                    raise AssertionError(f"strrchr string is not an allocated pointer: {arg1:#x}")
                data = self._heap_bytes(arg1, len(repl.STRRCHR_PROOF_BYTES))
                nul = data.find(b"\x00")
                if nul < 0:
                    raise AssertionError("strrchr proof buffer is not NUL-terminated in scan window")
                search = arg2 & 0xFF
                offset = data[:nul].rfind(bytes([search]))
                lines.append("A90R0" if offset < 0 else f"A90R{arg1 + offset:x}")
            elif arg0 == filp_open:
                path = self._heap_bytes(arg1, 16).split(b"\x00", 1)[0]
                if path != b"/init":
                    raise AssertionError(f"unexpected filp_open path bytes: {path!r}")
                if arg2 != 0 or arg3 != 0:
                    raise AssertionError(f"unexpected filp_open flags/mode: {arg2:#x}/{arg3:#x}")
                self.opened_files.add(self.file_ptr)
                lines.append(f"A90R{self.file_ptr:x}")
            elif arg0 == filp_close:
                if arg1 not in self.opened_files:
                    raise AssertionError(f"filp_close arg is not an opened file: {arg1:#x}")
                if arg2 != 0:
                    raise AssertionError(f"unexpected filp_close owner: {arg2:#x}")
                self.opened_files.discard(arg1)
                self.closed_files.append(arg1)
                lines.append("A90R0")
            elif arg0 == kernel_read:
                if arg1 not in self.opened_files:
                    raise AssertionError(f"kernel_read file is not opened: {arg1:#x}")
                if arg2 not in self.allocated:
                    raise AssertionError(f"kernel_read buffer is not allocated: {arg2:#x}")
                if arg4 not in self.allocated:
                    raise AssertionError(f"kernel_read pos is not allocated: {arg4:#x}")
                if self.heap.get(arg4, 0) != 0:
                    raise AssertionError(f"kernel_read pos is not zero: {self.heap.get(arg4, 0):#x}")
                data = self.kernel_read_payload[:arg3]
                if len(data) != arg3:
                    raise AssertionError(f"kernel_read requested too much: {arg3}")
                self._set_heap_bytes(arg2, data)
                self.heap[arg4] = arg3
                lines.append(f"A90R{arg3:x}")
            elif arg0 == printk:
                sentinel = arg2  # arg2 == x1
                lines.append(f"A90R{sentinel:x}")   # called printk echoes the sentinel
                lines.append("A90Rb")               # stub prints printk's return value
            else:
                raise AssertionError(f"unexpected call target: {arg0:#x}")
        return {"ok": True, "rc": 0, "stdout": "\n".join(lines) + "\n", "stderr": ""}


@unittest.skipUnless(
    MAP_PATH.is_file() and IMAGE_PATH.is_file(),
    "v1-repl image and/or System.map not present",
)
class SelftestIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.symbols = repl.load_system_map(MAP_PATH)
        self.image = repl.load_static_image(IMAGE_PATH)

    def _run(self, slide):
        fake = FaithfulFakeTransport(slide, self.symbols, self.image)
        orig = repl.transport.run_serial_command
        repl.transport.run_serial_command = fake.run_serial_command
        self.addCleanup(lambda: setattr(repl.transport, "run_serial_command", orig))
        session = repl.ReplSession(repl.ReplConfig(settle_sec=0.0))
        return repl.run_selftest(
            session, self.symbols, self.image,
            peek_symbols=("kgsl_pwrctrl_force_no_nap_store", "__kmalloc"),
            call_symbol="printk",
        )

    def test_selftest_passes_with_faithful_stub(self) -> None:
        summary = self._run(0x130000)
        self.assertTrue(summary["ok"], summary)
        self.assertEqual(summary["decision"], "a90-repl-v2a1-selftest-pass")
        kinds = {c["check"] for c in summary["checks"]}
        self.assertEqual(kinds, {"named-peek", "named-call-printk"})
        self.assertTrue(all(c["ok"] for c in summary["checks"]))
        self.assertTrue(summary["call_resolution"]["verified"])
        self.assertEqual(summary["call_resolution"]["method"], "export-recovery")

    def test_selftest_rejects_known_unsafe_call_before_transport(self) -> None:
        fake = FaithfulFakeTransport(0x130000, self.symbols, self.image)
        orig = repl.transport.run_serial_command
        repl.transport.run_serial_command = fake.run_serial_command
        self.addCleanup(lambda: setattr(repl.transport, "run_serial_command", orig))
        session = repl.ReplSession(repl.ReplConfig(settle_sec=0.0))

        with self.assertRaisesRegex(repl.ReplError, "not verified"):
            repl.run_selftest(
                session,
                self.symbols,
                self.image,
                peek_symbols=("kgsl_pwrctrl_force_no_nap_store",),
                call_symbol="kallsyms_lookup_name",
            )
        self.assertEqual(fake.op_count, 0)

    def test_selftest_rejects_non_page_aligned_slide(self) -> None:
        with self.assertRaises(repl.ReplError):
            self._run(0x130123)

    def test_poke_roundtrip_passes_with_faithful_stub(self) -> None:
        fake = FaithfulFakeTransport(0x130000, self.symbols, self.image)
        orig = repl.transport.run_serial_command
        repl.transport.run_serial_command = fake.run_serial_command
        self.addCleanup(lambda: setattr(repl.transport, "run_serial_command", orig))
        session = repl.ReplSession(repl.ReplConfig(settle_sec=0.0))
        summary, private = repl.run_poke_roundtrip(
            session,
            self.symbols,
            self.image,
            check_allocator_abi=False,
        )

        self.assertTrue(summary["ok"], summary)
        self.assertEqual(summary["decision"], "a90-repl-v2a2-poke-roundtrip-pass")
        kinds = {c["check"] for c in summary["checks"]}
        self.assertEqual(
            kinds,
            {
                "kmalloc-owned-buffer",
                "poke-peek-qword",
                "poke-peek-low32",
                "kfree-owned-buffer",
            },
        )
        self.assertEqual(fake.heap[fake.heap_ptr], 0x11223344C001D00D)
        self.assertEqual(fake.freed, [fake.heap_ptr])
        self.assertEqual(private["alloc_ptr"], f"0x{fake.heap_ptr:x}")
        self.assertNotIn("alloc_ptr", summary)

    def test_poke_roundtrip_can_use_recovered_allocator_exports(self) -> None:
        recovery = repl.recover_allocator_export_addresses(self.symbols, self.image)
        recovered = {
            name: int(value, 16)
            for name, value in recovery["recovered"].items()
            if name in {"__kmalloc", "kfree"}
        }
        fake = FaithfulFakeTransport(0x130000, self.symbols, self.image)
        fake.kmalloc_link = recovered["__kmalloc"]
        fake.kfree_link = recovered["kfree"]
        orig = repl.transport.run_serial_command
        repl.transport.run_serial_command = fake.run_serial_command
        self.addCleanup(lambda: setattr(repl.transport, "run_serial_command", orig))
        session = repl.ReplSession(repl.ReplConfig(settle_sec=0.0))
        summary, _private = repl.run_poke_roundtrip(
            session,
            self.symbols,
            self.image,
            allocator_links=recovered,
            allocator_source="allocator-export-recovery",
        )

        self.assertTrue(summary["ok"], summary)
        self.assertEqual(summary["allocator_address_source"], "allocator-export-recovery")
        self.assertTrue(summary["allocator_resolutions"]["__kmalloc"]["verified"])
        self.assertTrue(summary["allocator_resolutions"]["kfree"]["verified"])
        self.assertEqual(
            summary["allocator_link_vaddrs"],
            {
                "__kmalloc": "0xffffff800826ae34",
                "kfree": "0xffffff800826b354",
            },
        )

    def test_call_proof_ksize_passes_with_owned_pointer_contract(self) -> None:
        if not C2B_PADDING_MAP_PATH.is_file() or not KERNEL_SOURCE_ROOT.is_dir():
            self.skipTest("promoted v2c System.map or kernel source tree not present")

        symbols = repl.load_system_map(C2B_PADDING_MAP_PATH)
        fake = FaithfulFakeTransport(0x130000, symbols, self.image)
        orig = repl.transport.run_serial_command
        repl.transport.run_serial_command = fake.run_serial_command
        self.addCleanup(lambda: setattr(repl.transport, "run_serial_command", orig))
        session = repl.ReplSession(repl.ReplConfig(settle_sec=0.0))
        summary, private = repl.run_call_proof(
            session,
            symbols,
            self.image,
            "ksize",
            source_root=KERNEL_SOURCE_ROOT,
        )

        self.assertTrue(summary["ok"], summary)
        self.assertEqual(summary["decision"], "a90-repl-live-call-proof-ksize-pass")
        self.assertEqual(summary["proof_status"], "trusted-under-owned-input-contract")
        self.assertEqual(summary["observed_return_value"], "0x1000")
        self.assertEqual(summary["function_map_entry"]["symbol"], "ksize")
        self.assertEqual(summary["function_map_entry"]["status"], "live-proven")
        self.assertEqual(summary["source_evidence"]["signature"], "size_t ksize(const void *)")
        self.assertTrue(summary["raw_runtime_values_redacted"])
        self.assertTrue(summary["owned_pointer_redacted"])
        self.assertNotIn("alloc_ptr", summary)
        self.assertEqual(private["alloc_ptr"], f"0x{fake.heap_ptr:x}")
        self.assertEqual(fake.freed, [fake.heap_ptr])
        self.assertEqual(fake.op_count, 4)  # slide + kmalloc + ksize + kfree

    def test_call_proof_strnlen_passes_with_owned_string_contract(self) -> None:
        if not C2B_PADDING_MAP_PATH.is_file() or not KERNEL_SOURCE_ROOT.is_dir():
            self.skipTest("promoted v2c System.map or kernel source tree not present")

        symbols = repl.load_system_map(C2B_PADDING_MAP_PATH)
        fake = FaithfulFakeTransport(0x130000, symbols, self.image)
        orig = repl.transport.run_serial_command
        repl.transport.run_serial_command = fake.run_serial_command
        self.addCleanup(lambda: setattr(repl.transport, "run_serial_command", orig))
        session = repl.ReplSession(repl.ReplConfig(settle_sec=0.0))
        summary, private = repl.run_call_proof(
            session,
            symbols,
            self.image,
            "strnlen",
            source_root=KERNEL_SOURCE_ROOT,
        )

        self.assertTrue(summary["ok"], summary)
        self.assertEqual(summary["decision"], "a90-repl-live-call-proof-strnlen-pass")
        self.assertEqual(summary["proof_status"], "trusted-under-owned-input-contract")
        self.assertEqual(summary["function_map_entry"]["symbol"], "strnlen")
        self.assertEqual(summary["function_map_entry"]["status"], "live-proven")
        self.assertEqual(summary["source_evidence"]["signature"], "extern __kernel_size_t strnlen(const char *,__kernel_size_t)")
        self.assertEqual(summary["expected_return_value"], "0xa")
        self.assertEqual(summary["observed_return_value"], "0xa")
        self.assertEqual(summary["proof_string"], "A90STRNLEN")
        self.assertTrue(summary["raw_runtime_values_redacted"])
        self.assertTrue(summary["owned_pointer_redacted"])
        self.assertNotIn("alloc_ptr", summary)
        self.assertEqual(private["alloc_ptr"], f"0x{fake.heap_ptr:x}")
        self.assertEqual(private["observed_bytes_hex"], repl.STRNLEN_PROOF_BYTES.hex())
        self.assertEqual(fake.freed, [fake.heap_ptr])

    def test_call_proof_strlen_passes_with_owned_string_contract(self) -> None:
        if not C2B_PADDING_MAP_PATH.is_file() or not KERNEL_SOURCE_ROOT.is_dir():
            self.skipTest("promoted v2c System.map or kernel source tree not present")

        symbols = repl.load_system_map(C2B_PADDING_MAP_PATH)
        fake = FaithfulFakeTransport(0x130000, symbols, self.image)
        orig = repl.transport.run_serial_command
        repl.transport.run_serial_command = fake.run_serial_command
        self.addCleanup(lambda: setattr(repl.transport, "run_serial_command", orig))
        session = repl.ReplSession(repl.ReplConfig(settle_sec=0.0))
        summary, private = repl.run_call_proof(
            session,
            symbols,
            self.image,
            "strlen",
            source_root=KERNEL_SOURCE_ROOT,
        )

        self.assertTrue(summary["ok"], summary)
        self.assertEqual(summary["decision"], "a90-repl-live-call-proof-strlen-pass")
        self.assertEqual(summary["proof_status"], "trusted-under-owned-input-contract")
        self.assertEqual(summary["function_map_entry"]["symbol"], "strlen")
        self.assertEqual(summary["function_map_entry"]["status"], "live-proven")
        self.assertEqual(summary["source_evidence"]["signature"], "extern __kernel_size_t strlen(const char *)")
        self.assertEqual(summary["expected_return_value"], "0x9")
        self.assertEqual(summary["observed_return_value"], "0x9")
        self.assertEqual(summary["proof_string"], "A90STRLEN")
        self.assertTrue(summary["raw_runtime_values_redacted"])
        self.assertTrue(summary["owned_pointer_redacted"])
        self.assertNotIn("alloc_ptr", summary)
        self.assertEqual(private["alloc_ptr"], f"0x{fake.heap_ptr:x}")
        self.assertEqual(private["observed_bytes_hex"], repl.STRLEN_PROOF_BYTES.hex())
        self.assertEqual(fake.freed, [fake.heap_ptr])

    def test_call_proof_strscpy_passes_with_owned_buffers_contract(self) -> None:
        if not C2B_PADDING_MAP_PATH.is_file() or not KERNEL_SOURCE_ROOT.is_dir():
            self.skipTest("promoted v2c System.map or kernel source tree not present")

        symbols = repl.load_system_map(C2B_PADDING_MAP_PATH)
        fake = FaithfulFakeTransport(0x130000, symbols, self.image)
        orig = repl.transport.run_serial_command
        repl.transport.run_serial_command = fake.run_serial_command
        self.addCleanup(lambda: setattr(repl.transport, "run_serial_command", orig))
        session = repl.ReplSession(repl.ReplConfig(settle_sec=0.0))
        summary, private = repl.run_call_proof(
            session,
            symbols,
            self.image,
            "strscpy",
            source_root=KERNEL_SOURCE_ROOT,
        )

        self.assertTrue(summary["ok"], summary)
        self.assertEqual(summary["decision"], "a90-repl-live-call-proof-strscpy-pass")
        self.assertEqual(summary["proof_status"], "trusted-under-owned-input-contract")
        self.assertEqual(summary["function_map_entry"]["symbol"], "strscpy")
        self.assertEqual(summary["function_map_entry"]["status"], "live-proven")
        self.assertEqual(summary["source_evidence"]["signature"], "ssize_t strscpy(char *, const char *, size_t)")
        self.assertEqual(summary["expected_return_value"], "0xa")
        self.assertEqual(summary["observed_return_value"], "0xa")
        self.assertEqual(summary["proof_string"], "A90STRSCPY")
        self.assertEqual(summary["size_arg"], repl.STRSCPY_PROOF_SIZE)
        self.assertTrue(summary["raw_runtime_values_redacted"])
        self.assertTrue(summary["owned_pointer_redacted"])
        self.assertNotIn("dst_ptr", summary)
        self.assertNotIn("src_ptr", summary)
        self.assertEqual(private["dst_ptr"], f"0x{fake.heap_ptr:x}")
        self.assertEqual(private["src_ptr"], f"0x{fake.heap_ptr + 0x1000:x}")
        self.assertEqual(private["observed_src_hex"], repl.STRSCPY_PROOF_SRC_BYTES.hex())
        self.assertTrue(private["observed_dst_hex"].startswith(repl.STRSCPY_PROOF_SRC_BYTES.hex()))
        self.assertEqual(fake.freed, [fake.heap_ptr, fake.heap_ptr + 0x1000])

    def test_call_proof_strlcpy_passes_with_owned_buffers_contract(self) -> None:
        if not C2B_PADDING_MAP_PATH.is_file() or not KERNEL_SOURCE_ROOT.is_dir():
            self.skipTest("promoted v2c System.map or kernel source tree not present")

        symbols = repl.load_system_map(C2B_PADDING_MAP_PATH)
        fake = FaithfulFakeTransport(0x130000, symbols, self.image)
        orig = repl.transport.run_serial_command
        repl.transport.run_serial_command = fake.run_serial_command
        self.addCleanup(lambda: setattr(repl.transport, "run_serial_command", orig))
        session = repl.ReplSession(repl.ReplConfig(settle_sec=0.0))
        summary, private = repl.run_call_proof(
            session,
            symbols,
            self.image,
            "strlcpy",
            source_root=KERNEL_SOURCE_ROOT,
        )

        self.assertTrue(summary["ok"], summary)
        self.assertEqual(summary["decision"], "a90-repl-live-call-proof-strlcpy-pass")
        self.assertEqual(summary["proof_status"], "trusted-under-owned-input-contract")
        self.assertEqual(summary["function_map_entry"]["symbol"], "strlcpy")
        self.assertEqual(summary["function_map_entry"]["status"], "live-proven")
        self.assertEqual(summary["source_evidence"]["signature"], "size_t strlcpy(char *, const char *, size_t)")
        self.assertEqual(summary["expected_return_value"], "0xa")
        self.assertEqual(summary["observed_return_value"], "0xa")
        self.assertEqual(summary["proof_string"], "A90STRLCPY")
        self.assertEqual(summary["size_arg"], repl.STRLCPY_PROOF_SIZE)
        self.assertTrue(summary["raw_runtime_values_redacted"])
        self.assertTrue(summary["owned_pointer_redacted"])
        self.assertNotIn("dst_ptr", summary)
        self.assertNotIn("src_ptr", summary)
        self.assertEqual(private["dst_ptr"], f"0x{fake.heap_ptr:x}")
        self.assertEqual(private["src_ptr"], f"0x{fake.heap_ptr + 0x1000:x}")
        self.assertEqual(private["observed_src_hex"], repl.STRLCPY_PROOF_SRC_BYTES.hex())
        self.assertTrue(private["observed_dst_hex"].startswith(repl.STRLCPY_PROOF_SRC_BYTES.hex()))
        self.assertEqual(fake.freed, [fake.heap_ptr, fake.heap_ptr + 0x1000])

    def test_call_proof_strncpy_passes_with_owned_buffers_contract(self) -> None:
        if not C2B_PADDING_MAP_PATH.is_file() or not KERNEL_SOURCE_ROOT.is_dir():
            self.skipTest("promoted v2c System.map or kernel source tree not present")

        symbols = repl.load_system_map(C2B_PADDING_MAP_PATH)
        fake = FaithfulFakeTransport(0x130000, symbols, self.image)
        orig = repl.transport.run_serial_command
        repl.transport.run_serial_command = fake.run_serial_command
        self.addCleanup(lambda: setattr(repl.transport, "run_serial_command", orig))
        session = repl.ReplSession(repl.ReplConfig(settle_sec=0.0))
        summary, private = repl.run_call_proof(
            session,
            symbols,
            self.image,
            "strncpy",
            source_root=KERNEL_SOURCE_ROOT,
        )

        self.assertTrue(summary["ok"], summary)
        self.assertEqual(summary["decision"], "a90-repl-live-call-proof-strncpy-pass")
        self.assertEqual(summary["proof_status"], "trusted-under-owned-input-contract")
        self.assertEqual(summary["function_map_entry"]["symbol"], "strncpy")
        self.assertEqual(summary["function_map_entry"]["status"], "live-proven")
        self.assertEqual(
            summary["source_evidence"]["signature"],
            "extern char * strncpy(char *,const char *, __kernel_size_t)",
        )
        self.assertEqual(summary["proof_string"], "A90STRNCPY")
        self.assertEqual(summary["count_arg"], repl.STRNCPY_PROOF_SIZE)
        self.assertTrue(summary["return_matches_destination"])
        self.assertEqual(summary["expected_return_value"], "owned-destination-pointer-redacted")
        self.assertEqual(summary["observed_return_value"], "owned-destination-pointer-redacted")
        self.assertTrue(summary["raw_runtime_values_redacted"])
        self.assertTrue(summary["owned_pointer_redacted"])
        self.assertNotIn("dst_ptr", summary)
        self.assertNotIn("src_ptr", summary)
        self.assertNotIn("return_ptr", summary)
        self.assertEqual(private["dst_ptr"], f"0x{fake.heap_ptr:x}")
        self.assertEqual(private["src_ptr"], f"0x{fake.heap_ptr + 0x1000:x}")
        self.assertEqual(private["return_ptr"], f"0x{fake.heap_ptr:x}")
        self.assertEqual(private["observed_src_hex"], repl.STRNCPY_PROOF_SRC_BYTES.hex())
        self.assertTrue(private["observed_dst_hex"].startswith(repl.STRNCPY_PROOF_SRC_BYTES.hex()))
        self.assertEqual(
            private["observed_dst_hex"][
                len(repl.STRNCPY_PROOF_SRC_BYTES.hex()):repl.STRNCPY_PROOF_SIZE * 2
            ],
            "00" * (repl.STRNCPY_PROOF_SIZE - len(repl.STRNCPY_PROOF_SRC_BYTES)),
        )
        self.assertEqual(fake.freed, [fake.heap_ptr, fake.heap_ptr + 0x1000])

    def test_call_proof_memcmp_passes_with_owned_buffers_contract(self) -> None:
        if not C2B_PADDING_MAP_PATH.is_file() or not KERNEL_SOURCE_ROOT.is_dir():
            self.skipTest("promoted v2c System.map or kernel source tree not present")

        symbols = repl.load_system_map(C2B_PADDING_MAP_PATH)
        fake = FaithfulFakeTransport(0x130000, symbols, self.image)
        orig = repl.transport.run_serial_command
        repl.transport.run_serial_command = fake.run_serial_command
        self.addCleanup(lambda: setattr(repl.transport, "run_serial_command", orig))
        session = repl.ReplSession(repl.ReplConfig(settle_sec=0.0))
        summary, private = repl.run_call_proof(
            session,
            symbols,
            self.image,
            "memcmp",
            source_root=KERNEL_SOURCE_ROOT,
        )

        self.assertTrue(summary["ok"], summary)
        self.assertEqual(summary["decision"], "a90-repl-live-call-proof-memcmp-pass")
        self.assertEqual(summary["proof_status"], "trusted-under-owned-input-contract")
        self.assertEqual(summary["function_map_entry"]["symbol"], "memcmp")
        self.assertEqual(summary["function_map_entry"]["status"], "live-proven")
        self.assertEqual(
            summary["source_evidence"]["signature"],
            "extern int memcmp(const void *,const void *,__kernel_size_t)",
        )
        self.assertEqual(summary["proof_bytes_label"], repl.MEMCMP_PROOF_BYTES.decode("ascii"))
        self.assertEqual(summary["size_arg"], repl.MEMCMP_PROOF_SIZE)
        self.assertEqual(summary["equal_expected_return_value"], "0x0")
        self.assertEqual(summary["equal_observed_return_value"], "0x0")
        self.assertEqual(summary["mismatch_expected_return_sign"], "positive")
        self.assertGreater(int(str(summary["mismatch_observed_return_value"]), 16), 0)
        self.assertEqual(summary["mismatch_offset"], repl.MEMCMP_MISMATCH_OFFSET)
        self.assertTrue(summary["buffers_unchanged_after_calls"])
        self.assertTrue(summary["raw_runtime_values_redacted"])
        self.assertTrue(summary["owned_pointer_redacted"])
        self.assertTrue(summary["observed_bytes_redacted"])
        self.assertNotIn("left_ptr", summary)
        self.assertNotIn("right_ptr", summary)
        self.assertEqual(private["left_ptr"], f"0x{fake.heap_ptr:x}")
        self.assertEqual(private["right_ptr"], f"0x{fake.heap_ptr + 0x1000:x}")
        expected_left_hex = (repl.MEMCMP_PROOF_BYTES + (b"\xcc" * repl.MEMCMP_CANARY_LEN)).hex()
        self.assertEqual(private["left_bytes_hex"], expected_left_hex)
        self.assertEqual(private["right_equal_bytes_hex"], expected_left_hex)
        right_mismatch = bytearray(repl.MEMCMP_PROOF_BYTES)
        right_mismatch[repl.MEMCMP_MISMATCH_OFFSET] = repl.MEMCMP_MISMATCH_RIGHT_BYTE
        expected_right_mismatch_hex = (
            bytes(right_mismatch) + (b"\xcc" * repl.MEMCMP_CANARY_LEN)
        ).hex()
        self.assertEqual(private["right_mismatch_bytes_hex"], expected_right_mismatch_hex)
        self.assertEqual(fake.freed, [fake.heap_ptr, fake.heap_ptr + 0x1000])

    def test_call_proof_strrchr_passes_with_owned_string_contract(self) -> None:
        if not C2B_PADDING_MAP_PATH.is_file() or not KERNEL_SOURCE_ROOT.is_dir():
            self.skipTest("promoted v2c System.map or kernel source tree not present")

        symbols = repl.load_system_map(C2B_PADDING_MAP_PATH)
        fake = FaithfulFakeTransport(0x130000, symbols, self.image)
        orig = repl.transport.run_serial_command
        repl.transport.run_serial_command = fake.run_serial_command
        self.addCleanup(lambda: setattr(repl.transport, "run_serial_command", orig))
        session = repl.ReplSession(repl.ReplConfig(settle_sec=0.0))
        summary, private = repl.run_call_proof(
            session,
            symbols,
            self.image,
            "strrchr",
            source_root=KERNEL_SOURCE_ROOT,
        )

        self.assertTrue(summary["ok"], summary)
        self.assertEqual(summary["decision"], "a90-repl-live-call-proof-strrchr-pass")
        self.assertEqual(summary["proof_status"], "trusted-under-owned-input-contract")
        self.assertEqual(summary["function_map_entry"]["symbol"], "strrchr")
        self.assertEqual(summary["function_map_entry"]["status"], "live-proven")
        self.assertEqual(
            summary["source_evidence"]["signature"],
            "extern char * strrchr(const char *,int)",
        )
        self.assertEqual(summary["proof_string"], repl.STRRCHR_PROOF_LABEL)
        self.assertEqual(summary["search_byte"], f"0x{repl.STRRCHR_SEARCH_BYTE:02x}")
        self.assertEqual(summary["expected_hit_offset"], repl.STRRCHR_EXPECTED_OFFSET)
        self.assertEqual(summary["hit_expected_return_value"], "owned-string-pointer-plus-offset-redacted")
        self.assertEqual(summary["hit_observed_return_value"], "owned-string-pointer-plus-offset-redacted")
        self.assertTrue(summary["return_matches_expected_offset"])
        self.assertEqual(summary["missing_expected_return_value"], "0x0")
        self.assertEqual(summary["missing_observed_return_value"], "0x0")
        self.assertTrue(summary["string_unchanged_after_calls"])
        self.assertTrue(summary["raw_runtime_values_redacted"])
        self.assertTrue(summary["owned_pointer_redacted"])
        self.assertTrue(summary["observed_bytes_redacted"])
        self.assertNotIn("alloc_ptr", summary)
        self.assertNotIn("hit_return_ptr", summary)
        self.assertEqual(private["alloc_ptr"], f"0x{fake.heap_ptr:x}")
        self.assertEqual(
            private["hit_return_ptr"],
            f"0x{fake.heap_ptr + repl.STRRCHR_EXPECTED_OFFSET:x}",
        )
        expected_hex = (
            repl.STRRCHR_PROOF_BYTES + (b"\xcc" * repl.STRRCHR_CANARY_LEN)
        ).hex()
        self.assertEqual(private["observed_bytes_hex"], expected_hex)
        self.assertEqual(fake.freed, [fake.heap_ptr])

    def test_call_proof_filp_open_passes_with_owned_pathname_contract(self) -> None:
        if not C2B_PADDING_MAP_PATH.is_file() or not KERNEL_SOURCE_ROOT.is_dir():
            self.skipTest("promoted v2c System.map or kernel source tree not present")

        symbols = repl.load_system_map(C2B_PADDING_MAP_PATH)
        fake = FaithfulFakeTransport(0x130000, symbols, self.image)
        orig = repl.transport.run_serial_command
        repl.transport.run_serial_command = fake.run_serial_command
        self.addCleanup(lambda: setattr(repl.transport, "run_serial_command", orig))
        session = repl.ReplSession(repl.ReplConfig(settle_sec=0.0))
        summary, private = repl.run_call_proof(
            session,
            symbols,
            self.image,
            "filp_open",
            source_root=KERNEL_SOURCE_ROOT,
        )

        self.assertTrue(summary["ok"], summary)
        self.assertEqual(summary["decision"], "a90-repl-live-call-proof-filp_open-pass")
        self.assertEqual(summary["proof_status"], "trusted-under-owned-input-contract")
        self.assertEqual(summary["function_map_entry"]["symbol"], "filp_open")
        self.assertEqual(summary["function_map_entry"]["status"], "live-proven")
        self.assertEqual(summary["paired_cleanup_function_map_entry"]["symbol"], "filp_close")
        self.assertEqual(summary["paired_cleanup_function_map_entry"]["status"], "cleanup-live-proven")
        self.assertEqual(summary["source_evidence"]["signature"], "extern struct file * filp_open(const char *, int, umode_t)")
        self.assertEqual(summary["close_return_value"], "0x0")
        self.assertTrue(summary["raw_runtime_values_redacted"])
        self.assertTrue(summary["owned_pointer_redacted"])
        self.assertNotIn("file_ptr", summary)
        self.assertEqual(private["file_ptr"], f"0x{fake.file_ptr:x}")
        self.assertEqual(fake.closed_files, [fake.file_ptr])
        self.assertEqual(fake.freed, [fake.heap_ptr])
        self.assertEqual(fake.opened_files, set())

    def test_call_proof_kernel_read_passes_with_owned_file_buffer_pos_contract(self) -> None:
        if not C2B_PADDING_MAP_PATH.is_file() or not KERNEL_SOURCE_ROOT.is_dir():
            self.skipTest("promoted v2c System.map or kernel source tree not present")

        symbols = repl.load_system_map(C2B_PADDING_MAP_PATH)
        fake = FaithfulFakeTransport(0x130000, symbols, self.image)
        orig = repl.transport.run_serial_command
        repl.transport.run_serial_command = fake.run_serial_command
        self.addCleanup(lambda: setattr(repl.transport, "run_serial_command", orig))
        session = repl.ReplSession(repl.ReplConfig(settle_sec=0.0))
        summary, private = repl.run_call_proof(
            session,
            symbols,
            self.image,
            "kernel_read",
            source_root=KERNEL_SOURCE_ROOT,
        )

        self.assertTrue(summary["ok"], summary)
        self.assertEqual(summary["decision"], "a90-repl-live-call-proof-kernel_read-pass")
        self.assertEqual(summary["proof_status"], "trusted-under-owned-input-contract")
        self.assertEqual(summary["function_map_entry"]["symbol"], "kernel_read")
        self.assertEqual(summary["function_map_entry"]["status"], "live-proven")
        self.assertEqual(summary["source_evidence"]["signature"], "extern ssize_t kernel_read(struct file *, void *, size_t, loff_t *)")
        self.assertEqual(summary["observed_return_value"], "0x10")
        self.assertEqual(summary["observed_prefix"], "7f454c46")
        self.assertEqual(summary["observed_pos_after"], "0x10")
        self.assertTrue(summary["raw_runtime_values_redacted"])
        self.assertTrue(summary["owned_pointer_redacted"])
        self.assertTrue(summary["read_data_redacted"])
        self.assertNotIn("file_ptr", summary)
        self.assertEqual(private["file_ptr"], f"0x{fake.file_ptr:x}")
        self.assertEqual(private["read_data_hex"][:8], "7f454c46")
        self.assertEqual(fake.closed_files, [fake.file_ptr])
        self.assertEqual(fake.freed, [
            fake.heap_ptr,
            fake.heap_ptr + 0x1000,
            fake.heap_ptr + 0x2000,
        ])
        self.assertEqual(fake.opened_files, set())

    def test_poke_roundtrip_rejects_non_lowmem_alloc(self) -> None:
        fake = FaithfulFakeTransport(0x130000, self.symbols, self.image)
        fake.heap_ptr = 0x12345000
        fake.next_heap_ptr = fake.heap_ptr
        orig = repl.transport.run_serial_command
        repl.transport.run_serial_command = fake.run_serial_command
        self.addCleanup(lambda: setattr(repl.transport, "run_serial_command", orig))
        session = repl.ReplSession(repl.ReplConfig(settle_sec=0.0))

        with self.assertRaises(repl.ReplError):
            repl.run_poke_roundtrip(
                session,
                self.symbols,
                self.image,
                check_allocator_abi=False,
            )
        self.assertFalse(fake.heap)
        self.assertFalse(fake.freed)

    def test_poke_roundtrip_rejects_unverified_allocator_override_before_transport(self) -> None:
        fake = FaithfulFakeTransport(0x130000, self.symbols, self.image)
        orig = repl.transport.run_serial_command
        repl.transport.run_serial_command = fake.run_serial_command
        self.addCleanup(lambda: setattr(repl.transport, "run_serial_command", orig))
        session = repl.ReplSession(repl.ReplConfig(settle_sec=0.0))
        bad_map_links = {
            "__kmalloc": repl.resolve_link(self.symbols, "__kmalloc"),
            "kfree": repl.resolve_link(self.symbols, "kfree"),
        }

        with self.assertRaisesRegex(repl.ReplError, "does not match verified resolution"):
            repl.run_poke_roundtrip(
                session,
                self.symbols,
                self.image,
                allocator_links=bad_map_links,
                allocator_source="System.map",
            )
        self.assertEqual(fake.op_count, 0)

    def test_u1_read_reads_arbitrary_length_in_chunks(self) -> None:
        slide = 0x130000
        fake = FaithfulFakeTransport(slide, self.symbols, self.image)
        orig = repl.transport.run_serial_command
        repl.transport.run_serial_command = fake.run_serial_command
        self.addCleanup(lambda: setattr(repl.transport, "run_serial_command", orig))
        session = repl.ReplSession(repl.ReplConfig(settle_sec=0.0))

        summary, private = repl.run_read(
            session,
            self.symbols,
            self.image,
            "kgsl_pwrctrl_force_no_nap_store",
            length=20,
        )

        link = repl.resolve_link(self.symbols, "kgsl_pwrctrl_force_no_nap_store")
        want = self.image.bytes_at_vaddr(link, 20)
        self.assertTrue(summary["ok"], summary)
        self.assertEqual(summary["decision"], "a90-repl-v2c-u1-read-pass")
        self.assertEqual(summary["chunk_count"], 3)
        self.assertEqual(summary["static_image_match"], True)
        self.assertEqual(summary["data_sha256"], hashlib.sha256(want).hexdigest())
        self.assertTrue(summary["raw_runtime_values_redacted"])
        self.assertNotIn("data_hex", summary)
        self.assertEqual(private["data_hex"], want.hex())
        self.assertEqual(fake.op_count, 4)  # slide + ceil(20/8) peek ops

    def test_u1_read_rejects_zero_length_before_transport(self) -> None:
        fake = FaithfulFakeTransport(0x130000, self.symbols, self.image)
        orig = repl.transport.run_serial_command
        repl.transport.run_serial_command = fake.run_serial_command
        self.addCleanup(lambda: setattr(repl.transport, "run_serial_command", orig))
        session = repl.ReplSession(repl.ReplConfig(settle_sec=0.0))

        with self.assertRaisesRegex(repl.ReplError, "read length"):
            repl.run_read(
                session,
                self.symbols,
                self.image,
                "kgsl_pwrctrl_force_no_nap_store",
                length=0,
            )
        self.assertEqual(fake.op_count, 0)

    def test_u1_call_verified_symbol_redacts_values(self) -> None:
        slide = 0x130000
        fake = FaithfulFakeTransport(slide, self.symbols, self.image)
        orig = repl.transport.run_serial_command
        repl.transport.run_serial_command = fake.run_serial_command
        self.addCleanup(lambda: setattr(repl.transport, "run_serial_command", orig))
        session = repl.ReplSession(repl.ReplConfig(settle_sec=0.0))

        summary, private = repl.run_call(
            session,
            self.symbols,
            self.image,
            "printk",
            ("@repl_format", f"0x{repl.CALL_SENTINEL:x}"),
            replay_safe=True,
        )

        self.assertTrue(summary["ok"], summary)
        self.assertEqual(summary["decision"], "a90-repl-v2c-u1-call-pass")
        self.assertEqual(summary["return_value_count"], 2)
        self.assertTrue(summary["resolution"]["verified"])
        self.assertEqual(summary["call_safety"]["tier"], repl.CALL_SAFETY_SAFE_WITH_VALID_PTR)
        self.assertTrue(summary["call_safety"]["safe_group"])
        self.assertTrue(summary["argument_values_redacted"])
        self.assertTrue(summary["return_values_redacted"])
        self.assertNotIn("return_values", summary)
        self.assertEqual(private["arg_sources"], ["pseudo:@repl_format", "integer"])
        self.assertEqual(
            private["args"],
            [f"0x{repl.FORMAT_LINK_VADDR + slide:x}", f"0x{repl.CALL_SENTINEL:x}"],
        )
        self.assertEqual(private["return_values"], [f"0x{repl.CALL_SENTINEL:x}", "0xb"])

    def test_u1_call_rejects_unverified_symbol_before_transport(self) -> None:
        fake = FaithfulFakeTransport(0x130000, self.symbols, self.image)
        orig = repl.transport.run_serial_command
        repl.transport.run_serial_command = fake.run_serial_command
        self.addCleanup(lambda: setattr(repl.transport, "run_serial_command", orig))
        session = repl.ReplSession(repl.ReplConfig(settle_sec=0.0))

        with self.assertRaisesRegex(repl.ReplError, "call-safety gate refused"):
            repl.run_call(
                session,
                self.symbols,
                self.image,
                "kallsyms_lookup_name",
                (),
            )
        self.assertEqual(fake.op_count, 0)

    def test_u2_call_gate_rejects_behavior_changing_symbol_before_transport(self) -> None:
        fake = FaithfulFakeTransport(0x130000, self.symbols, self.image)
        orig = repl.transport.run_serial_command
        repl.transport.run_serial_command = fake.run_serial_command
        self.addCleanup(lambda: setattr(repl.transport, "run_serial_command", orig))
        session = repl.ReplSession(repl.ReplConfig(settle_sec=0.0))

        with self.assertRaisesRegex(repl.ReplError, "call-safety gate refused"):
            repl.run_call(
                session,
                self.symbols,
                self.image,
                "commit_creds",
                ("@commit_creds",),
            )
        self.assertEqual(fake.op_count, 0)

    def test_u2_call_gate_rejects_printk_without_verified_pointer_arg(self) -> None:
        fake = FaithfulFakeTransport(0x130000, self.symbols, self.image)
        orig = repl.transport.run_serial_command
        repl.transport.run_serial_command = fake.run_serial_command
        self.addCleanup(lambda: setattr(repl.transport, "run_serial_command", orig))
        session = repl.ReplSession(repl.ReplConfig(settle_sec=0.0))

        with self.assertRaisesRegex(repl.ReplError, "SAFE-WITH-VALID-PTR requires"):
            repl.run_call(
                session,
                self.symbols,
                self.image,
                "printk",
                ("0xa90ca11",),
            )
        self.assertEqual(fake.op_count, 0)

    def test_gate2_kfree_scalar_is_refused_before_transport(self) -> None:
        fake = FaithfulFakeTransport(0x130000, self.symbols, self.image)
        orig = repl.transport.run_serial_command
        repl.transport.run_serial_command = fake.run_serial_command
        self.addCleanup(lambda: setattr(repl.transport, "run_serial_command", orig))
        session = repl.ReplSession(repl.ReplConfig(settle_sec=0.0))

        with self.assertRaisesRegex(repl.ReplError, "SAFE-WITH-VALID-PTR requires"):
            repl.run_call(
                session,
                self.symbols,
                self.image,
                "kfree",
                ("0x1234",),
            )
        self.assertEqual(fake.op_count, 0)

    def test_u1_poke_is_owned_buffer_only_and_redacted(self) -> None:
        fake = FaithfulFakeTransport(0x130000, self.symbols, self.image)
        orig = repl.transport.run_serial_command
        repl.transport.run_serial_command = fake.run_serial_command
        self.addCleanup(lambda: setattr(repl.transport, "run_serial_command", orig))
        session = repl.ReplSession(repl.ReplConfig(settle_sec=0.0))

        summary, private = repl.run_owned_poke(
            session,
            self.symbols,
            self.image,
            value=0xAABBCCDDEEFF0011,
            width=8,
        )

        self.assertTrue(summary["ok"], summary)
        self.assertEqual(summary["decision"], "a90-repl-v2c-u1-owned-poke-pass")
        self.assertEqual(fake.heap[fake.heap_ptr], 0xAABBCCDDEEFF0011)
        self.assertEqual(fake.freed, [fake.heap_ptr])
        self.assertTrue(summary["raw_runtime_values_redacted"])
        self.assertTrue(summary["value_redacted"])
        self.assertNotIn("alloc_ptr", summary)
        self.assertEqual(private["alloc_ptr"], f"0x{fake.heap_ptr:x}")


if __name__ == "__main__":
    unittest.main()
