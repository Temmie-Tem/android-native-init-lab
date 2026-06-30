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

        strnchr = self._row("strnchr")
        self.assertEqual(strnchr["tier"], repl.CALL_SAFETY_SAFE_WITH_VALID_PTR)
        self.assertEqual(strnchr["required_valid_pointer_args"], {"0": "string-buffer"})
        self.assertTrue(strnchr["resolution"]["verified"])
        self.assertEqual(strnchr["resolution"]["method"], "export-recovery")
        self.assertEqual(strnchr["resolution"]["link_vaddr"], "0xffffff80099b99a4")
        self.assertGreaterEqual(strnchr["signals"]["direct_bl_xref_count"], 40)
        self.assertTrue(strnchr["signals"]["leaf"])

        skip_spaces = self._row("skip_spaces")
        self.assertEqual(skip_spaces["tier"], repl.CALL_SAFETY_SAFE_WITH_VALID_PTR)
        self.assertEqual(skip_spaces["required_valid_pointer_args"], {"0": "string-buffer"})
        self.assertTrue(skip_spaces["resolution"]["verified"])
        self.assertEqual(skip_spaces["resolution"]["method"], "export-recovery")
        self.assertEqual(skip_spaces["resolution"]["link_vaddr"], "0xffffff80099b99d4")
        self.assertGreaterEqual(skip_spaces["signals"]["direct_bl_xref_count"], 50)

        strim = self._row("strim")
        self.assertEqual(strim["tier"], repl.CALL_SAFETY_SAFE_WITH_VALID_PTR)
        self.assertEqual(strim["required_valid_pointer_args"], {"0": "mutable-string-buffer"})
        self.assertTrue(strim["resolution"]["verified"])
        self.assertEqual(strim["resolution"]["method"], "export-recovery")
        self.assertEqual(strim["resolution"]["link_vaddr"], "0xffffff80099b99f4")
        self.assertGreaterEqual(strim["signals"]["direct_bl_xref_count"], 50)

        strreplace = self._row("strreplace")
        self.assertEqual(strreplace["tier"], repl.CALL_SAFETY_SAFE_WITH_VALID_PTR)
        self.assertEqual(strreplace["required_valid_pointer_args"], {"0": "mutable-string-buffer"})
        self.assertTrue(strreplace["resolution"]["verified"])
        self.assertEqual(strreplace["resolution"]["method"], "export-recovery")
        self.assertEqual(strreplace["resolution"]["link_vaddr"], "0xffffff80099ba12c")
        self.assertGreaterEqual(strreplace["signals"]["direct_bl_xref_count"], 10)

        strchr = self._row("strchr")
        self.assertEqual(strchr["tier"], repl.CALL_SAFETY_SAFE_WITH_VALID_PTR)
        self.assertEqual(strchr["required_valid_pointer_args"], {"0": "string-buffer"})
        self.assertTrue(strchr["resolution"]["verified"])
        self.assertEqual(strchr["resolution"]["method"], "leaf-map-disasm+xref")
        self.assertGreaterEqual(strchr["signals"]["direct_bl_xref_count"], 100)
        self.assertTrue(strchr["signals"]["leaf"])

        strchrnul = self._row("strchrnul")
        self.assertEqual(strchrnul["tier"], repl.CALL_SAFETY_SAFE_WITH_VALID_PTR)
        self.assertEqual(strchrnul["required_valid_pointer_args"], {"0": "string-buffer"})
        self.assertTrue(strchrnul["resolution"]["verified"])
        self.assertEqual(strchrnul["resolution"]["method"], "export-recovery")
        self.assertGreaterEqual(strchrnul["signals"]["direct_bl_xref_count"], 7)
        self.assertTrue(strchrnul["signals"]["leaf"])

        strstr = self._row("strstr")
        self.assertEqual(strstr["tier"], repl.CALL_SAFETY_SAFE_WITH_VALID_PTR)
        self.assertEqual(
            strstr["required_valid_pointer_args"],
            {"0": "haystack-string-buffer", "1": "needle-string-buffer"},
        )
        self.assertTrue(strstr["resolution"]["verified"])
        self.assertEqual(strstr["resolution"]["method"], "export-recovery")
        self.assertGreaterEqual(strstr["signals"]["direct_bl_xref_count"], 50)
        self.assertFalse(strstr["signals"]["leaf"])

        strnstr = self._row("strnstr")
        self.assertEqual(strnstr["tier"], repl.CALL_SAFETY_SAFE_WITH_VALID_PTR)
        self.assertEqual(
            strnstr["required_valid_pointer_args"],
            {"0": "haystack-string-buffer", "1": "needle-string-buffer"},
        )
        self.assertTrue(strnstr["resolution"]["verified"])
        self.assertEqual(strnstr["resolution"]["method"], "export-recovery")
        self.assertEqual(strnstr["resolution"]["link_vaddr"], "0xffffff80099b9f44")
        self.assertGreaterEqual(strnstr["signals"]["direct_bl_xref_count"], 260)
        self.assertFalse(strnstr["signals"]["leaf"])

        match_string = self._row("match_string")
        self.assertEqual(match_string["tier"], repl.CALL_SAFETY_SAFE_WITH_VALID_PTR)
        self.assertEqual(
            match_string["required_valid_pointer_args"],
            {"0": "string-pointer-array", "2": "search-string-buffer"},
        )
        self.assertTrue(match_string["resolution"]["verified"])
        self.assertEqual(match_string["resolution"]["method"], "export-recovery")
        self.assertEqual(match_string["resolution"]["link_vaddr"], "0xffffff80099b9c9c")
        self.assertGreaterEqual(match_string["signals"]["direct_bl_xref_count"], 5)
        self.assertFalse(match_string["signals"]["leaf"])

        sysfs_streq = self._row("sysfs_streq")
        self.assertEqual(sysfs_streq["tier"], repl.CALL_SAFETY_SAFE_WITH_VALID_PTR)
        self.assertEqual(
            sysfs_streq["required_valid_pointer_args"],
            {"0": "left-string-buffer", "1": "right-string-buffer"},
        )
        self.assertTrue(sysfs_streq["resolution"]["verified"])
        self.assertEqual(sysfs_streq["resolution"]["method"], "export-recovery")
        self.assertEqual(sysfs_streq["resolution"]["link_vaddr"], "0xffffff80099b9c14")
        self.assertGreaterEqual(sysfs_streq["signals"]["direct_bl_xref_count"], 60)
        self.assertTrue(sysfs_streq["signals"]["leaf"])

        kstrdup = self._row("kstrdup")
        self.assertEqual(kstrdup["tier"], repl.CALL_SAFETY_SAFE_WITH_VALID_PTR)
        self.assertEqual(
            kstrdup["required_valid_pointer_args"],
            {"0": "source-string-buffer"},
        )
        self.assertTrue(kstrdup["resolution"]["verified"])
        self.assertEqual(kstrdup["resolution"]["method"], "export-recovery")
        self.assertEqual(kstrdup["resolution"]["link_vaddr"], "0xffffff800822a664")
        self.assertGreaterEqual(kstrdup["signals"]["direct_bl_xref_count"], 150)
        self.assertFalse(kstrdup["signals"]["leaf"])

        kstrndup = self._row("kstrndup")
        self.assertEqual(kstrndup["tier"], repl.CALL_SAFETY_SAFE_WITH_VALID_PTR)
        self.assertEqual(
            kstrndup["required_valid_pointer_args"],
            {"0": "source-string-buffer"},
        )
        self.assertTrue(kstrndup["resolution"]["verified"])
        self.assertEqual(kstrndup["resolution"]["method"], "export-recovery")
        self.assertEqual(kstrndup["resolution"]["link_vaddr"], "0xffffff800822a77c")
        self.assertGreaterEqual(kstrndup["signals"]["direct_bl_xref_count"], 20)
        self.assertFalse(kstrndup["signals"]["leaf"])

        kmemdup = self._row("kmemdup")
        self.assertEqual(kmemdup["tier"], repl.CALL_SAFETY_SAFE_WITH_VALID_PTR)
        self.assertEqual(
            kmemdup["required_valid_pointer_args"],
            {"0": "source-buffer"},
        )
        self.assertTrue(kmemdup["resolution"]["verified"])
        self.assertEqual(kmemdup["resolution"]["method"], "export-recovery")
        self.assertEqual(kmemdup["resolution"]["link_vaddr"], "0xffffff800822a7fc")
        self.assertGreaterEqual(kmemdup["signals"]["direct_bl_xref_count"], 900)
        self.assertFalse(kmemdup["signals"]["leaf"])

        kmemdup_nul = self._row("kmemdup_nul")
        self.assertEqual(kmemdup_nul["tier"], repl.CALL_SAFETY_SAFE_WITH_VALID_PTR)
        self.assertEqual(
            kmemdup_nul["required_valid_pointer_args"],
            {"0": "source-buffer"},
        )
        self.assertTrue(kmemdup_nul["resolution"]["verified"])
        self.assertEqual(kmemdup_nul["resolution"]["method"], "export-recovery")
        self.assertEqual(kmemdup_nul["resolution"]["link_vaddr"], "0xffffff800822a85c")
        self.assertGreaterEqual(kmemdup_nul["signals"]["direct_bl_xref_count"], 1)
        self.assertFalse(kmemdup_nul["signals"]["leaf"])

        strpbrk = self._row("strpbrk")
        self.assertEqual(strpbrk["tier"], repl.CALL_SAFETY_SAFE_WITH_VALID_PTR)
        self.assertEqual(
            strpbrk["required_valid_pointer_args"],
            {"0": "haystack-string-buffer", "1": "accept-string-buffer"},
        )
        self.assertTrue(strpbrk["resolution"]["verified"])
        self.assertEqual(strpbrk["resolution"]["method"], "export-recovery")
        self.assertEqual(strpbrk["resolution"]["link_vaddr"], "0xffffff80099b9b34")
        self.assertGreaterEqual(strpbrk["signals"]["direct_bl_xref_count"], 40)
        self.assertTrue(strpbrk["signals"]["leaf"])

        strspn = self._row("strspn")
        self.assertEqual(strspn["tier"], repl.CALL_SAFETY_SAFE_WITH_VALID_PTR)
        self.assertEqual(
            strspn["required_valid_pointer_args"],
            {"0": "haystack-string-buffer", "1": "accept-string-buffer"},
        )
        self.assertTrue(strspn["resolution"]["verified"])
        self.assertEqual(strspn["resolution"]["method"], "export-recovery")
        self.assertEqual(strspn["resolution"]["link_vaddr"], "0xffffff80099b9a6c")
        self.assertGreaterEqual(strspn["signals"]["direct_bl_xref_count"], 2)
        self.assertTrue(strspn["signals"]["leaf"])

        strcspn = self._row("strcspn")
        self.assertEqual(strcspn["tier"], repl.CALL_SAFETY_SAFE_WITH_VALID_PTR)
        self.assertEqual(
            strcspn["required_valid_pointer_args"],
            {"0": "haystack-string-buffer", "1": "reject-string-buffer"},
        )
        self.assertTrue(strcspn["resolution"]["verified"])
        self.assertEqual(strcspn["resolution"]["method"], "export-recovery")
        self.assertEqual(strcspn["resolution"]["link_vaddr"], "0xffffff80099b9ac4")
        self.assertGreaterEqual(strcspn["signals"]["direct_bl_xref_count"], 8)
        self.assertTrue(strcspn["signals"]["leaf"])

        strcmp = self._row("strcmp")
        self.assertEqual(strcmp["tier"], repl.CALL_SAFETY_SAFE_WITH_VALID_PTR)
        self.assertEqual(
            strcmp["required_valid_pointer_args"],
            {"0": "left-string-buffer", "1": "right-string-buffer"},
        )
        self.assertTrue(strcmp["resolution"]["verified"])
        self.assertEqual(strcmp["resolution"]["method"], "leaf-map-disasm+xref")
        self.assertGreaterEqual(strcmp["signals"]["direct_bl_xref_count"], 3000)
        self.assertTrue(strcmp["signals"]["leaf"])

        strncmp = self._row("strncmp")
        self.assertEqual(strncmp["tier"], repl.CALL_SAFETY_SAFE_WITH_VALID_PTR)
        self.assertEqual(
            strncmp["required_valid_pointer_args"],
            {"0": "left-string-buffer", "1": "right-string-buffer"},
        )
        self.assertTrue(strncmp["resolution"]["verified"])
        self.assertEqual(strncmp["resolution"]["method"], "leaf-map-disasm+xref")
        self.assertGreaterEqual(strncmp["signals"]["direct_bl_xref_count"], 500)
        self.assertTrue(strncmp["signals"]["leaf"])

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

        strcpy = self._row("strcpy")
        self.assertEqual(strcpy["tier"], repl.CALL_SAFETY_SAFE_WITH_VALID_PTR)
        self.assertEqual(
            strcpy["required_valid_pointer_args"],
            {"0": "destination-buffer", "1": "source-string-buffer"},
        )
        self.assertTrue(strcpy["resolution"]["verified"])
        self.assertEqual(strcpy["resolution"]["method"], "export-recovery")
        self.assertEqual(strcpy["resolution"]["link_vaddr"], "0xffffff80099b96d4")
        self.assertGreaterEqual(strcpy["signals"]["direct_bl_xref_count"], 500)
        self.assertTrue(strcpy["signals"]["leaf"])

        strcat = self._row("strcat")
        self.assertEqual(strcat["tier"], repl.CALL_SAFETY_SAFE_WITH_VALID_PTR)
        self.assertEqual(
            strcat["required_valid_pointer_args"],
            {"0": "destination-buffer", "1": "source-string-buffer"},
        )
        self.assertTrue(strcat["resolution"]["verified"])
        self.assertEqual(strcat["resolution"]["method"], "export-recovery")
        self.assertEqual(strcat["resolution"]["link_vaddr"], "0xffffff80099b988c")
        self.assertGreaterEqual(strcat["signals"]["direct_bl_xref_count"], 70)
        self.assertTrue(strcat["signals"]["leaf"])

        strncat = self._row("strncat")
        self.assertEqual(strncat["tier"], repl.CALL_SAFETY_SAFE_WITH_VALID_PTR)
        self.assertEqual(
            strncat["required_valid_pointer_args"],
            {"0": "destination-buffer", "1": "source-string-buffer"},
        )
        self.assertTrue(strncat["resolution"]["verified"])
        self.assertEqual(strncat["resolution"]["method"], "export-recovery")
        self.assertEqual(strncat["resolution"]["link_vaddr"], "0xffffff80099b98b4")
        self.assertGreaterEqual(strncat["signals"]["direct_bl_xref_count"], 190)
        self.assertTrue(strncat["signals"]["leaf"])

        strcasecmp = self._row("strcasecmp")
        self.assertEqual(strcasecmp["tier"], repl.CALL_SAFETY_SAFE_WITH_VALID_PTR)
        self.assertEqual(
            strcasecmp["required_valid_pointer_args"],
            {"0": "left-string-buffer", "1": "right-string-buffer"},
        )
        self.assertTrue(strcasecmp["resolution"]["verified"])
        self.assertEqual(strcasecmp["resolution"]["method"], "export-recovery")
        self.assertEqual(strcasecmp["resolution"]["link_vaddr"], "0xffffff80099b9684")
        self.assertGreaterEqual(strcasecmp["signals"]["direct_bl_xref_count"], 110)
        self.assertTrue(strcasecmp["signals"]["leaf"])

        strncasecmp = self._row("strncasecmp")
        self.assertEqual(strncasecmp["tier"], repl.CALL_SAFETY_SAFE_WITH_VALID_PTR)
        self.assertEqual(
            strncasecmp["required_valid_pointer_args"],
            {"0": "left-string-buffer", "1": "right-string-buffer"},
        )
        self.assertTrue(strncasecmp["resolution"]["verified"])
        self.assertEqual(strncasecmp["resolution"]["method"], "export-recovery")
        self.assertEqual(strncasecmp["resolution"]["link_vaddr"], "0xffffff80099b960c")
        self.assertGreaterEqual(strncasecmp["signals"]["direct_bl_xref_count"], 80)
        self.assertTrue(strncasecmp["signals"]["leaf"])

        strlcat = self._row("strlcat")
        self.assertEqual(strlcat["tier"], repl.CALL_SAFETY_SAFE_WITH_VALID_PTR)
        self.assertEqual(
            strlcat["required_valid_pointer_args"],
            {"0": "destination-buffer", "1": "source-string-buffer"},
        )
        self.assertTrue(strlcat["resolution"]["verified"])
        self.assertEqual(strlcat["resolution"]["method"], "export-recovery")
        self.assertEqual(strlcat["resolution"]["link_vaddr"], "0xffffff80099b98f4")
        self.assertGreaterEqual(strlcat["signals"]["direct_bl_xref_count"], 520)
        self.assertFalse(strlcat["signals"]["leaf"])

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

        memchr = self._row("memchr")
        self.assertEqual(memchr["tier"], repl.CALL_SAFETY_SAFE_WITH_VALID_PTR)
        self.assertEqual(memchr["required_valid_pointer_args"], {"0": "buffer"})
        self.assertTrue(memchr["resolution"]["verified"])
        self.assertEqual(memchr["resolution"]["method"], "leaf-map-disasm+xref")
        self.assertGreaterEqual(memchr["signals"]["direct_bl_xref_count"], 20)
        self.assertTrue(memchr["signals"]["leaf"])

        memchr_inv = self._row("memchr_inv")
        self.assertEqual(memchr_inv["tier"], repl.CALL_SAFETY_SAFE_WITH_VALID_PTR)
        self.assertEqual(memchr_inv["required_valid_pointer_args"], {"0": "buffer"})
        self.assertTrue(memchr_inv["resolution"]["verified"])
        self.assertEqual(memchr_inv["resolution"]["method"], "export-recovery")
        self.assertEqual(memchr_inv["resolution"]["link_vaddr"], "0xffffff80099b9fc4")
        self.assertGreaterEqual(memchr_inv["signals"]["direct_bl_xref_count"], 30)
        self.assertTrue(memchr_inv["signals"]["leaf"])

        memcpy = self._row("memcpy")
        self.assertEqual(memcpy["tier"], repl.CALL_SAFETY_SAFE_WITH_VALID_PTR)
        self.assertEqual(
            memcpy["required_valid_pointer_args"],
            {"0": "destination-buffer", "1": "source-buffer"},
        )
        self.assertTrue(memcpy["resolution"]["verified"])
        self.assertEqual(memcpy["resolution"]["method"], "leaf-map-disasm+xref")
        self.assertGreaterEqual(memcpy["signals"]["direct_bl_xref_count"], 5000)
        self.assertTrue(memcpy["signals"]["leaf"])

        memmove = self._row("memmove")
        self.assertEqual(memmove["tier"], repl.CALL_SAFETY_SAFE_WITH_VALID_PTR)
        self.assertEqual(
            memmove["required_valid_pointer_args"],
            {"0": "destination-buffer", "1": "source-buffer"},
        )
        self.assertTrue(memmove["resolution"]["verified"])
        self.assertEqual(memmove["resolution"]["method"], "leaf-map-disasm+xref")
        self.assertGreaterEqual(memmove["signals"]["direct_bl_xref_count"], 100)
        self.assertTrue(memmove["signals"]["leaf"])

        strrchr = self._row("strrchr")
        self.assertEqual(strrchr["tier"], repl.CALL_SAFETY_SAFE_WITH_VALID_PTR)
        self.assertEqual(strrchr["required_valid_pointer_args"], {"0": "string-buffer"})
        self.assertTrue(strrchr["resolution"]["verified"])
        self.assertEqual(strrchr["resolution"]["method"], "leaf-map-disasm+xref")
        self.assertGreaterEqual(strrchr["signals"]["direct_bl_xref_count"], 1000)
        self.assertTrue(strrchr["signals"]["leaf"])

        memset = self._row("memset")
        self.assertEqual(memset["tier"], repl.CALL_SAFETY_SAFE_WITH_VALID_PTR)
        self.assertEqual(memset["required_valid_pointer_args"], {"0": "destination-buffer"})
        self.assertTrue(memset["resolution"]["verified"])
        self.assertEqual(memset["resolution"]["method"], "leaf-map-disasm+xref")
        self.assertGreaterEqual(memset["signals"]["direct_bl_xref_count"], 5000)
        self.assertTrue(memset["signals"]["leaf"])

        hex_to_bin = self._row("hex_to_bin")
        self.assertEqual(hex_to_bin["tier"], repl.CALL_SAFETY_SAFE_SCALAR)
        self.assertEqual(hex_to_bin["required_valid_pointer_args"], {})
        self.assertTrue(hex_to_bin["resolution"]["verified"])
        self.assertEqual(hex_to_bin["resolution"]["method"], "export-recovery")
        self.assertEqual(hex_to_bin["resolution"]["link_vaddr"], "0xffffff800856a9dc")
        self.assertGreaterEqual(hex_to_bin["signals"]["direct_bl_xref_count"], 80)
        self.assertTrue(hex_to_bin["signals"]["leaf"])

        hex2bin = self._row("hex2bin")
        self.assertEqual(hex2bin["tier"], repl.CALL_SAFETY_SAFE_WITH_VALID_PTR)
        self.assertEqual(
            hex2bin["required_valid_pointer_args"],
            {"0": "destination-buffer", "1": "source-hex-buffer"},
        )
        self.assertTrue(hex2bin["resolution"]["verified"])
        self.assertEqual(hex2bin["resolution"]["method"], "export-recovery")
        self.assertEqual(hex2bin["resolution"]["link_vaddr"], "0xffffff800856aa3c")
        self.assertGreaterEqual(hex2bin["signals"]["direct_bl_xref_count"], 15)
        self.assertTrue(hex2bin["signals"]["leaf"])

        bin2hex = self._row("bin2hex")
        self.assertEqual(bin2hex["tier"], repl.CALL_SAFETY_SAFE_WITH_VALID_PTR)
        self.assertEqual(
            bin2hex["required_valid_pointer_args"],
            {"0": "destination-hex-buffer", "1": "source-byte-buffer"},
        )
        self.assertTrue(bin2hex["resolution"]["verified"])
        self.assertEqual(bin2hex["resolution"]["method"], "export-recovery")
        self.assertEqual(bin2hex["resolution"]["link_vaddr"], "0xffffff800856aaf4")
        self.assertGreaterEqual(bin2hex["signals"]["direct_bl_xref_count"], 5)
        self.assertTrue(bin2hex["signals"]["leaf"])

        parse_option_str = self._row("parse_option_str")
        self.assertEqual(parse_option_str["tier"], repl.CALL_SAFETY_SAFE_WITH_VALID_PTR)
        self.assertEqual(
            parse_option_str["required_valid_pointer_args"],
            {"0": "comma-separated-option-string", "1": "option-string"},
        )
        self.assertTrue(parse_option_str["resolution"]["verified"])
        self.assertEqual(parse_option_str["resolution"]["method"], "disasm-signature+xref+map")
        self.assertEqual(parse_option_str["resolution"]["link_vaddr"], "0xffffff80099a9c44")
        self.assertGreaterEqual(parse_option_str["signals"]["direct_bl_xref_count"], 3)
        self.assertFalse(parse_option_str["signals"]["leaf"])

        strsep = self._row("strsep")
        self.assertEqual(strsep["tier"], repl.CALL_SAFETY_SAFE_WITH_VALID_PTR)
        self.assertEqual(
            strsep["required_valid_pointer_args"],
            {"0": "string-pointer-slot", "1": "delimiter-string"},
        )
        self.assertTrue(strsep["resolution"]["verified"])
        self.assertEqual(strsep["resolution"]["method"], "export-recovery")
        self.assertEqual(strsep["resolution"]["link_vaddr"], "0xffffff80099b9b94")
        self.assertGreaterEqual(strsep["signals"]["direct_bl_xref_count"], 230)
        self.assertTrue(strsep["signals"]["leaf"])

        simple_strtoull = self._row("simple_strtoull")
        self.assertEqual(simple_strtoull["tier"], repl.CALL_SAFETY_SAFE_WITH_VALID_PTR)
        self.assertEqual(
            simple_strtoull["required_valid_pointer_args"],
            {"0": "numeric-string-buffer", "1": "end-pointer-output-slot"},
        )
        self.assertTrue(simple_strtoull["resolution"]["verified"])
        self.assertEqual(simple_strtoull["resolution"]["method"], "export-recovery")
        self.assertEqual(simple_strtoull["resolution"]["link_vaddr"], "0xffffff80099ba314")
        self.assertGreaterEqual(simple_strtoull["signals"]["direct_bl_xref_count"], 9)
        self.assertFalse(simple_strtoull["signals"]["leaf"])

        kstrtoull = self._row("kstrtoull")
        self.assertEqual(kstrtoull["tier"], repl.CALL_SAFETY_SAFE_WITH_VALID_PTR)
        self.assertEqual(
            kstrtoull["required_valid_pointer_args"],
            {"0": "numeric-string-buffer", "2": "ull-result-output-slot"},
        )
        self.assertTrue(kstrtoull["resolution"]["verified"])
        self.assertEqual(kstrtoull["resolution"]["method"], "export-recovery")
        self.assertEqual(kstrtoull["resolution"]["link_vaddr"], "0xffffff800856b3f4")
        self.assertGreaterEqual(kstrtoull["signals"]["direct_bl_xref_count"], 196)
        self.assertTrue(kstrtoull["signals"]["leaf"])

        kstrtoll = self._row("kstrtoll")
        self.assertEqual(kstrtoll["tier"], repl.CALL_SAFETY_SAFE_WITH_VALID_PTR)
        self.assertEqual(
            kstrtoll["required_valid_pointer_args"],
            {"0": "numeric-string-buffer", "2": "ll-result-output-slot"},
        )
        self.assertTrue(kstrtoll["resolution"]["verified"])
        self.assertEqual(kstrtoll["resolution"]["method"], "export-recovery")
        self.assertEqual(kstrtoll["resolution"]["link_vaddr"], "0xffffff800856b524")
        self.assertGreaterEqual(kstrtoll["signals"]["direct_bl_xref_count"], 42)
        self.assertFalse(kstrtoll["signals"]["leaf"])

        kstrtouint = self._row("kstrtouint")
        self.assertEqual(kstrtouint["tier"], repl.CALL_SAFETY_SAFE_WITH_VALID_PTR)
        self.assertEqual(
            kstrtouint["required_valid_pointer_args"],
            {"0": "numeric-string-buffer", "2": "uint-result-output-slot"},
        )
        self.assertTrue(kstrtouint["resolution"]["verified"])
        self.assertEqual(kstrtouint["resolution"]["method"], "export-recovery")
        self.assertEqual(kstrtouint["resolution"]["link_vaddr"], "0xffffff800856b7a4")
        self.assertGreaterEqual(kstrtouint["signals"]["direct_bl_xref_count"], 217)
        self.assertFalse(kstrtouint["signals"]["leaf"])

        kstrtou16 = self._row("kstrtou16")
        self.assertEqual(kstrtou16["tier"], repl.CALL_SAFETY_SAFE_WITH_VALID_PTR)
        self.assertEqual(
            kstrtou16["required_valid_pointer_args"],
            {"0": "numeric-string-buffer", "2": "u16-result-output-slot"},
        )
        self.assertTrue(kstrtou16["resolution"]["verified"])
        self.assertEqual(kstrtou16["resolution"]["method"], "export-recovery")
        self.assertEqual(kstrtou16["resolution"]["link_vaddr"], "0xffffff800856b8a4")
        self.assertGreaterEqual(kstrtou16["signals"]["direct_bl_xref_count"], 17)
        self.assertFalse(kstrtou16["signals"]["leaf"])

        kstrtou8 = self._row("kstrtou8")
        self.assertEqual(kstrtou8["tier"], repl.CALL_SAFETY_SAFE_WITH_VALID_PTR)
        self.assertEqual(
            kstrtou8["required_valid_pointer_args"],
            {"0": "numeric-string-buffer", "2": "u8-result-output-slot"},
        )
        self.assertTrue(kstrtou8["resolution"]["verified"])
        self.assertEqual(kstrtou8["resolution"]["method"], "export-recovery")
        self.assertEqual(kstrtou8["resolution"]["link_vaddr"], "0xffffff800856b9a4")
        self.assertGreaterEqual(kstrtou8["signals"]["direct_bl_xref_count"], 59)
        self.assertFalse(kstrtou8["signals"]["leaf"])

        kstrtos8 = self._row("kstrtos8")
        self.assertEqual(kstrtos8["tier"], repl.CALL_SAFETY_SAFE_WITH_VALID_PTR)
        self.assertEqual(
            kstrtos8["required_valid_pointer_args"],
            {"0": "numeric-string-buffer", "2": "s8-result-output-slot"},
        )
        self.assertTrue(kstrtos8["resolution"]["verified"])
        self.assertEqual(kstrtos8["resolution"]["method"], "export-recovery")
        self.assertEqual(kstrtos8["resolution"]["link_vaddr"], "0xffffff800856ba24")
        self.assertGreaterEqual(kstrtos8["signals"]["direct_bl_xref_count"], 12)
        self.assertFalse(kstrtos8["signals"]["leaf"])

        kstrtobool = self._row("kstrtobool")
        self.assertEqual(kstrtobool["tier"], repl.CALL_SAFETY_SAFE_WITH_VALID_PTR)
        self.assertEqual(
            kstrtobool["required_valid_pointer_args"],
            {"0": "bool-string-buffer", "1": "bool-result-output-slot"},
        )
        self.assertTrue(kstrtobool["resolution"]["verified"])
        self.assertEqual(kstrtobool["resolution"]["method"], "export-recovery")
        self.assertEqual(kstrtobool["resolution"]["link_vaddr"], "0xffffff800856baa4")
        self.assertGreaterEqual(kstrtobool["signals"]["direct_bl_xref_count"], 50)
        self.assertTrue(kstrtobool["signals"]["leaf"])

        kstrtoint = self._row("kstrtoint")
        self.assertEqual(kstrtoint["tier"], repl.CALL_SAFETY_SAFE_WITH_VALID_PTR)
        self.assertEqual(
            kstrtoint["required_valid_pointer_args"],
            {"0": "numeric-string-buffer", "2": "int-result-output-slot"},
        )
        self.assertTrue(kstrtoint["resolution"]["verified"])
        self.assertEqual(kstrtoint["resolution"]["method"], "export-recovery")
        self.assertEqual(kstrtoint["resolution"]["link_vaddr"], "0xffffff800856b824")
        self.assertGreaterEqual(kstrtoint["signals"]["direct_bl_xref_count"], 167)
        self.assertFalse(kstrtoint["signals"]["leaf"])

        kstrtos16 = self._row("kstrtos16")
        self.assertEqual(kstrtos16["tier"], repl.CALL_SAFETY_SAFE_WITH_VALID_PTR)
        self.assertEqual(
            kstrtos16["required_valid_pointer_args"],
            {"0": "numeric-string-buffer", "2": "s16-result-output-slot"},
        )
        self.assertTrue(kstrtos16["resolution"]["verified"])
        self.assertEqual(kstrtos16["resolution"]["method"], "export-recovery")
        self.assertEqual(kstrtos16["resolution"]["link_vaddr"], "0xffffff800856b924")
        self.assertGreaterEqual(kstrtos16["signals"]["direct_bl_xref_count"], 1)
        self.assertFalse(kstrtos16["signals"]["leaf"])

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
        self.assertEqual(summary["counts"][repl.CALL_SAFETY_SAFE_SCALAR], 2)
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

        strnchr = repl.lookup_source_signature("strnchr", source_root=KERNEL_SOURCE_ROOT)
        self.assertEqual(strnchr["status"], "found", strnchr)
        self.assertEqual(strnchr["selected"]["pointer_arg_indices"], [0])
        self.assertEqual(
            strnchr["selected"]["signature"],
            "extern char * strnchr(const char *, size_t, int)",
        )
        self.assertTrue(strnchr["selected"]["path"].endswith("include/linux/string.h"))

        skip_spaces = repl.lookup_source_signature("skip_spaces", source_root=KERNEL_SOURCE_ROOT)
        self.assertEqual(skip_spaces["status"], "found", skip_spaces)
        self.assertEqual(skip_spaces["selected"]["pointer_arg_indices"], [0])
        self.assertEqual(
            skip_spaces["selected"]["signature"],
            "extern char * __must_check skip_spaces(const char *)",
        )
        self.assertTrue(skip_spaces["selected"]["path"].endswith("include/linux/string.h"))

        strim = repl.lookup_source_signature("strim", source_root=KERNEL_SOURCE_ROOT)
        self.assertEqual(strim["status"], "found", strim)
        self.assertEqual(strim["selected"]["pointer_arg_indices"], [0])
        self.assertEqual(strim["selected"]["signature"], "extern char * strim(char *)")
        self.assertTrue(strim["selected"]["path"].endswith("include/linux/string.h"))

        strreplace = repl.lookup_source_signature("strreplace", source_root=KERNEL_SOURCE_ROOT)
        self.assertEqual(strreplace["status"], "found", strreplace)
        self.assertEqual(strreplace["selected"]["pointer_arg_indices"], [0])
        self.assertEqual(strreplace["selected"]["signature"], "char * strreplace(char *s, char old, char new)")
        self.assertTrue(strreplace["selected"]["path"].endswith("include/linux/string.h"))

        strchr = repl.lookup_source_signature("strchr", source_root=KERNEL_SOURCE_ROOT)
        self.assertEqual(strchr["status"], "found", strchr)
        self.assertEqual(strchr["selected"]["pointer_arg_indices"], [0])
        self.assertEqual(
            strchr["selected"]["signature"],
            "extern char * strchr(const char *,int)",
        )
        self.assertTrue(strchr["selected"]["path"].endswith("include/linux/string.h"))

        strchrnul = repl.lookup_source_signature("strchrnul", source_root=KERNEL_SOURCE_ROOT)
        self.assertEqual(strchrnul["status"], "found", strchrnul)
        self.assertEqual(strchrnul["selected"]["pointer_arg_indices"], [0])
        self.assertEqual(
            strchrnul["selected"]["signature"],
            "extern char * strchrnul(const char *,int)",
        )
        self.assertTrue(strchrnul["selected"]["path"].endswith("include/linux/string.h"))

        strstr = repl.lookup_source_signature("strstr", source_root=KERNEL_SOURCE_ROOT)
        self.assertEqual(strstr["status"], "found", strstr)
        self.assertEqual(strstr["selected"]["pointer_arg_indices"], [0, 1])
        self.assertEqual(
            strstr["selected"]["signature"],
            "extern char * strstr(const char *, const char *)",
        )
        self.assertTrue(strstr["selected"]["path"].endswith("include/linux/string.h"))

        strnstr = repl.lookup_source_signature("strnstr", source_root=KERNEL_SOURCE_ROOT)
        self.assertEqual(strnstr["status"], "found", strnstr)
        self.assertEqual(strnstr["selected"]["pointer_arg_indices"], [0, 1])
        self.assertEqual(
            strnstr["selected"]["signature"],
            "extern char * strnstr(const char *, const char *, size_t)",
        )
        self.assertTrue(strnstr["selected"]["path"].endswith("include/linux/string.h"))

        match_string = repl.lookup_source_signature("match_string", source_root=KERNEL_SOURCE_ROOT)
        self.assertEqual(match_string["status"], "found", match_string)
        self.assertEqual(match_string["selected"]["pointer_arg_indices"], [0, 2])
        self.assertEqual(
            match_string["selected"]["signature"],
            "int match_string(const char * const *array, size_t n, const char *string)",
        )
        self.assertTrue(match_string["selected"]["path"].endswith("include/linux/string.h"))

        sysfs_streq = repl.lookup_source_signature("sysfs_streq", source_root=KERNEL_SOURCE_ROOT)
        self.assertEqual(sysfs_streq["status"], "found", sysfs_streq)
        self.assertEqual(sysfs_streq["selected"]["pointer_arg_indices"], [0, 1])
        self.assertEqual(
            sysfs_streq["selected"]["signature"],
            "extern bool sysfs_streq(const char *s1, const char *s2)",
        )
        self.assertTrue(sysfs_streq["selected"]["path"].endswith("include/linux/string.h"))

        kstrdup = repl.lookup_source_signature("kstrdup", source_root=KERNEL_SOURCE_ROOT)
        self.assertEqual(kstrdup["status"], "found", kstrdup)
        self.assertEqual(kstrdup["selected"]["pointer_arg_indices"], [0])
        self.assertEqual(
            kstrdup["selected"]["signature"],
            "extern char * kstrdup(const char *s, gfp_t gfp) __malloc",
        )
        self.assertTrue(kstrdup["selected"]["path"].endswith("include/linux/string.h"))

        kstrndup = repl.lookup_source_signature("kstrndup", source_root=KERNEL_SOURCE_ROOT)
        self.assertEqual(kstrndup["status"], "found", kstrndup)
        self.assertEqual(kstrndup["selected"]["pointer_arg_indices"], [0])
        self.assertEqual(
            kstrndup["selected"]["signature"],
            "extern char * kstrndup(const char *s, size_t len, gfp_t gfp)",
        )
        self.assertTrue(kstrndup["selected"]["path"].endswith("include/linux/string.h"))

        kmemdup = repl.lookup_source_signature("kmemdup", source_root=KERNEL_SOURCE_ROOT)
        self.assertEqual(kmemdup["status"], "found", kmemdup)
        self.assertEqual(kmemdup["selected"]["pointer_arg_indices"], [0])
        self.assertEqual(
            kmemdup["selected"]["signature"],
            "extern void * kmemdup(const void *src, size_t len, gfp_t gfp)",
        )
        self.assertTrue(kmemdup["selected"]["path"].endswith("include/linux/string.h"))

        kmemdup_nul = repl.lookup_source_signature("kmemdup_nul", source_root=KERNEL_SOURCE_ROOT)
        self.assertEqual(kmemdup_nul["status"], "found", kmemdup_nul)
        self.assertEqual(kmemdup_nul["selected"]["pointer_arg_indices"], [0])
        self.assertEqual(
            kmemdup_nul["selected"]["signature"],
            "extern char * kmemdup_nul(const char *s, size_t len, gfp_t gfp)",
        )
        self.assertTrue(kmemdup_nul["selected"]["path"].endswith("include/linux/string.h"))

        strpbrk = repl.lookup_source_signature("strpbrk", source_root=KERNEL_SOURCE_ROOT)
        self.assertEqual(strpbrk["status"], "found", strpbrk)
        self.assertEqual(strpbrk["selected"]["pointer_arg_indices"], [0, 1])
        self.assertEqual(
            strpbrk["selected"]["signature"],
            "extern char * strpbrk(const char *,const char *)",
        )
        self.assertTrue(strpbrk["selected"]["path"].endswith("include/linux/string.h"))

        strspn = repl.lookup_source_signature("strspn", source_root=KERNEL_SOURCE_ROOT)
        self.assertEqual(strspn["status"], "found", strspn)
        self.assertEqual(strspn["selected"]["pointer_arg_indices"], [0, 1])
        self.assertEqual(
            strspn["selected"]["signature"],
            "extern __kernel_size_t strspn(const char *,const char *)",
        )
        self.assertTrue(strspn["selected"]["path"].endswith("include/linux/string.h"))

        strcspn = repl.lookup_source_signature("strcspn", source_root=KERNEL_SOURCE_ROOT)
        self.assertEqual(strcspn["status"], "found", strcspn)
        self.assertEqual(strcspn["selected"]["pointer_arg_indices"], [0, 1])
        self.assertEqual(
            strcspn["selected"]["signature"],
            "extern __kernel_size_t strcspn(const char *,const char *)",
        )
        self.assertTrue(strcspn["selected"]["path"].endswith("include/linux/string.h"))

        strcmp = repl.lookup_source_signature("strcmp", source_root=KERNEL_SOURCE_ROOT)
        self.assertEqual(strcmp["status"], "found", strcmp)
        self.assertEqual(strcmp["selected"]["pointer_arg_indices"], [0, 1])
        self.assertEqual(
            strcmp["selected"]["signature"],
            "extern int strcmp(const char *,const char *)",
        )
        self.assertTrue(strcmp["selected"]["path"].endswith("include/linux/string.h"))

        strncmp = repl.lookup_source_signature("strncmp", source_root=KERNEL_SOURCE_ROOT)
        self.assertEqual(strncmp["status"], "found", strncmp)
        self.assertEqual(strncmp["selected"]["pointer_arg_indices"], [0, 1])
        self.assertEqual(
            strncmp["selected"]["signature"],
            "extern int strncmp(const char *,const char *,__kernel_size_t)",
        )
        self.assertTrue(strncmp["selected"]["path"].endswith("include/linux/string.h"))

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

        strcpy = repl.lookup_source_signature("strcpy", source_root=KERNEL_SOURCE_ROOT)
        self.assertEqual(strcpy["status"], "found", strcpy)
        self.assertEqual(strcpy["selected"]["pointer_arg_indices"], [0, 1])
        self.assertEqual(
            strcpy["selected"]["signature"],
            "extern char * strcpy(char *,const char *)",
        )
        self.assertTrue(strcpy["selected"]["path"].endswith("include/linux/string.h"))

        strcat = repl.lookup_source_signature("strcat", source_root=KERNEL_SOURCE_ROOT)
        self.assertEqual(strcat["status"], "found", strcat)
        self.assertEqual(strcat["selected"]["pointer_arg_indices"], [0, 1])
        self.assertEqual(
            strcat["selected"]["signature"],
            "extern char * strcat(char *, const char *)",
        )
        self.assertTrue(strcat["selected"]["path"].endswith("include/linux/string.h"))

        strncat = repl.lookup_source_signature("strncat", source_root=KERNEL_SOURCE_ROOT)
        self.assertEqual(strncat["status"], "found", strncat)
        self.assertEqual(strncat["selected"]["pointer_arg_indices"], [0, 1])
        self.assertEqual(
            strncat["selected"]["signature"],
            "extern char * strncat(char *, const char *, __kernel_size_t)",
        )
        self.assertTrue(strncat["selected"]["path"].endswith("include/linux/string.h"))

        strcasecmp = repl.lookup_source_signature("strcasecmp", source_root=KERNEL_SOURCE_ROOT)
        self.assertEqual(strcasecmp["status"], "found", strcasecmp)
        self.assertEqual(strcasecmp["selected"]["pointer_arg_indices"], [0, 1])
        self.assertEqual(
            strcasecmp["selected"]["signature"],
            "extern int strcasecmp(const char *s1, const char *s2)",
        )
        self.assertTrue(strcasecmp["selected"]["path"].endswith("include/linux/string.h"))

        strncasecmp = repl.lookup_source_signature("strncasecmp", source_root=KERNEL_SOURCE_ROOT)
        self.assertEqual(strncasecmp["status"], "found", strncasecmp)
        self.assertEqual(strncasecmp["selected"]["pointer_arg_indices"], [0, 1])
        self.assertEqual(
            strncasecmp["selected"]["signature"],
            "extern int strncasecmp(const char *s1, const char *s2, size_t n)",
        )
        self.assertTrue(strncasecmp["selected"]["path"].endswith("include/linux/string.h"))

        strlcat = repl.lookup_source_signature("strlcat", source_root=KERNEL_SOURCE_ROOT)
        self.assertEqual(strlcat["status"], "found", strlcat)
        self.assertEqual(strlcat["selected"]["pointer_arg_indices"], [0, 1])
        self.assertEqual(
            strlcat["selected"]["signature"],
            "extern size_t strlcat(char *, const char *, __kernel_size_t)",
        )
        self.assertTrue(strlcat["selected"]["path"].endswith("include/linux/string.h"))

        memcmp = repl.lookup_source_signature("memcmp", source_root=KERNEL_SOURCE_ROOT)
        self.assertEqual(memcmp["status"], "found", memcmp)
        self.assertEqual(memcmp["selected"]["pointer_arg_indices"], [0, 1])
        self.assertEqual(
            memcmp["selected"]["signature"],
            "extern int memcmp(const void *,const void *,__kernel_size_t)",
        )
        self.assertTrue(memcmp["selected"]["path"].endswith("include/linux/string.h"))

        memchr = repl.lookup_source_signature("memchr", source_root=KERNEL_SOURCE_ROOT)
        self.assertEqual(memchr["status"], "found", memchr)
        self.assertEqual(memchr["selected"]["pointer_arg_indices"], [0])
        self.assertEqual(
            memchr["selected"]["signature"],
            "extern void * memchr(const void *,int,__kernel_size_t)",
        )
        self.assertTrue(memchr["selected"]["path"].endswith("include/linux/string.h"))

        memchr_inv = repl.lookup_source_signature("memchr_inv", source_root=KERNEL_SOURCE_ROOT)
        self.assertEqual(memchr_inv["status"], "found", memchr_inv)
        self.assertEqual(memchr_inv["selected"]["pointer_arg_indices"], [0])
        self.assertEqual(
            memchr_inv["selected"]["signature"],
            "void * memchr_inv(const void *s, int c, size_t n)",
        )
        self.assertTrue(memchr_inv["selected"]["path"].endswith("include/linux/string.h"))

        memcpy = repl.lookup_source_signature("memcpy", source_root=KERNEL_SOURCE_ROOT)
        self.assertEqual(memcpy["status"], "found", memcpy)
        self.assertEqual(memcpy["selected"]["pointer_arg_indices"], [0, 1])
        self.assertEqual(
            memcpy["selected"]["signature"],
            "extern void * memcpy(void *,const void *,__kernel_size_t)",
        )
        self.assertTrue(memcpy["selected"]["path"].endswith("include/linux/string.h"))

        memmove = repl.lookup_source_signature("memmove", source_root=KERNEL_SOURCE_ROOT)
        self.assertEqual(memmove["status"], "found", memmove)
        self.assertEqual(memmove["selected"]["pointer_arg_indices"], [0, 1])
        self.assertEqual(
            memmove["selected"]["signature"],
            "extern void * memmove(void *,const void *,__kernel_size_t)",
        )
        self.assertTrue(memmove["selected"]["path"].endswith("include/linux/string.h"))

        strrchr = repl.lookup_source_signature("strrchr", source_root=KERNEL_SOURCE_ROOT)
        self.assertEqual(strrchr["status"], "found", strrchr)
        self.assertEqual(strrchr["selected"]["pointer_arg_indices"], [0])
        self.assertEqual(
            strrchr["selected"]["signature"],
            "extern char * strrchr(const char *,int)",
        )
        self.assertTrue(strrchr["selected"]["path"].endswith("include/linux/string.h"))

        memset = repl.lookup_source_signature("memset", source_root=KERNEL_SOURCE_ROOT)
        self.assertEqual(memset["status"], "found", memset)
        self.assertEqual(memset["selected"]["pointer_arg_indices"], [0])
        self.assertEqual(
            memset["selected"]["signature"],
            "extern void * memset(void *,int,__kernel_size_t)",
        )
        self.assertTrue(memset["selected"]["path"].endswith("include/linux/string.h"))

        hex_to_bin = repl.lookup_source_signature("hex_to_bin", source_root=KERNEL_SOURCE_ROOT)
        self.assertEqual(hex_to_bin["status"], "found", hex_to_bin)
        self.assertEqual(hex_to_bin["selected"]["pointer_arg_indices"], [])
        self.assertEqual(
            hex_to_bin["selected"]["signature"],
            "extern int hex_to_bin(char ch)",
        )
        self.assertTrue(hex_to_bin["selected"]["path"].endswith("include/linux/kernel.h"))

        hex2bin = repl.lookup_source_signature("hex2bin", source_root=KERNEL_SOURCE_ROOT)
        self.assertEqual(hex2bin["status"], "found", hex2bin)
        self.assertEqual(hex2bin["selected"]["pointer_arg_indices"], [0, 1])
        self.assertEqual(
            hex2bin["selected"]["signature"],
            "extern int __must_check hex2bin(u8 *dst, const char *src, size_t count)",
        )
        self.assertTrue(hex2bin["selected"]["path"].endswith("include/linux/kernel.h"))

        bin2hex = repl.lookup_source_signature("bin2hex", source_root=KERNEL_SOURCE_ROOT)
        self.assertEqual(bin2hex["status"], "found", bin2hex)
        self.assertEqual(bin2hex["selected"]["pointer_arg_indices"], [0, 1])
        self.assertEqual(
            bin2hex["selected"]["signature"],
            "extern char * bin2hex(char *dst, const void *src, size_t count)",
        )
        self.assertTrue(bin2hex["selected"]["path"].endswith("include/linux/kernel.h"))

        parse_option_str = repl.lookup_source_signature("parse_option_str", source_root=KERNEL_SOURCE_ROOT)
        self.assertEqual(parse_option_str["status"], "found", parse_option_str)
        self.assertEqual(parse_option_str["selected"]["pointer_arg_indices"], [0, 1])
        self.assertEqual(
            parse_option_str["selected"]["signature"],
            "extern bool parse_option_str(const char *str, const char *option)",
        )
        self.assertTrue(parse_option_str["selected"]["path"].endswith("include/linux/kernel.h"))

        strsep = repl.lookup_source_signature("strsep", source_root=KERNEL_SOURCE_ROOT)
        self.assertEqual(strsep["status"], "found", strsep)
        self.assertEqual(strsep["selected"]["pointer_arg_indices"], [0, 1])
        self.assertEqual(strsep["selected"]["signature"], "extern char * strsep(char **,const char *)")
        self.assertTrue(strsep["selected"]["path"].endswith("include/linux/string.h"))

        simple_strtoull = repl.lookup_source_signature("simple_strtoull", source_root=KERNEL_SOURCE_ROOT)
        self.assertEqual(simple_strtoull["status"], "found", simple_strtoull)
        self.assertEqual(simple_strtoull["selected"]["pointer_arg_indices"], [0, 1])
        self.assertEqual(
            simple_strtoull["selected"]["signature"],
            "extern unsigned long long simple_strtoull(const char *,char **,unsigned int)",
        )
        self.assertTrue(simple_strtoull["selected"]["path"].endswith("include/linux/kernel.h"))

        kstrtoull = repl.lookup_source_signature("kstrtoull", source_root=KERNEL_SOURCE_ROOT)
        self.assertEqual(kstrtoull["status"], "found", kstrtoull)
        self.assertEqual(kstrtoull["selected"]["pointer_arg_indices"], [0, 2])
        self.assertEqual(
            kstrtoull["selected"]["signature"],
            "int __must_check kstrtoull(const char *s, unsigned int base, unsigned long long *res)",
        )
        self.assertTrue(kstrtoull["selected"]["path"].endswith("include/linux/kernel.h"))

        kstrtoll = repl.lookup_source_signature("kstrtoll", source_root=KERNEL_SOURCE_ROOT)
        self.assertEqual(kstrtoll["status"], "found", kstrtoll)
        self.assertEqual(kstrtoll["selected"]["pointer_arg_indices"], [0, 2])
        self.assertEqual(
            kstrtoll["selected"]["signature"],
            "int __must_check kstrtoll(const char *s, unsigned int base, long long *res)",
        )
        self.assertTrue(kstrtoll["selected"]["path"].endswith("include/linux/kernel.h"))

        kstrtouint = repl.lookup_source_signature("kstrtouint", source_root=KERNEL_SOURCE_ROOT)
        self.assertEqual(kstrtouint["status"], "found", kstrtouint)
        self.assertEqual(kstrtouint["selected"]["pointer_arg_indices"], [0, 2])
        self.assertEqual(
            kstrtouint["selected"]["signature"],
            "int __must_check kstrtouint(const char *s, unsigned int base, unsigned int *res)",
        )
        self.assertTrue(kstrtouint["selected"]["path"].endswith("include/linux/kernel.h"))

        kstrtou16 = repl.lookup_source_signature("kstrtou16", source_root=KERNEL_SOURCE_ROOT)
        self.assertEqual(kstrtou16["status"], "found", kstrtou16)
        self.assertEqual(kstrtou16["selected"]["pointer_arg_indices"], [0, 2])
        self.assertEqual(
            kstrtou16["selected"]["signature"],
            "int __must_check kstrtou16(const char *s, unsigned int base, u16 *res)",
        )
        self.assertTrue(kstrtou16["selected"]["path"].endswith("include/linux/kernel.h"))

        kstrtou8 = repl.lookup_source_signature("kstrtou8", source_root=KERNEL_SOURCE_ROOT)
        self.assertEqual(kstrtou8["status"], "found", kstrtou8)
        self.assertEqual(kstrtou8["selected"]["pointer_arg_indices"], [0, 2])
        self.assertEqual(
            kstrtou8["selected"]["signature"],
            "int __must_check kstrtou8(const char *s, unsigned int base, u8 *res)",
        )
        self.assertTrue(kstrtou8["selected"]["path"].endswith("include/linux/kernel.h"))

        kstrtos8 = repl.lookup_source_signature("kstrtos8", source_root=KERNEL_SOURCE_ROOT)
        self.assertEqual(kstrtos8["status"], "found", kstrtos8)
        self.assertEqual(kstrtos8["selected"]["pointer_arg_indices"], [0, 2])
        self.assertEqual(
            kstrtos8["selected"]["signature"],
            "int __must_check kstrtos8(const char *s, unsigned int base, s8 *res)",
        )
        self.assertTrue(kstrtos8["selected"]["path"].endswith("include/linux/kernel.h"))

        kstrtobool = repl.lookup_source_signature("kstrtobool", source_root=KERNEL_SOURCE_ROOT)
        self.assertEqual(kstrtobool["status"], "found", kstrtobool)
        self.assertEqual(kstrtobool["selected"]["pointer_arg_indices"], [0, 1])
        self.assertEqual(
            kstrtobool["selected"]["signature"],
            "int __must_check kstrtobool(const char *s, bool *res)",
        )
        self.assertTrue(kstrtobool["selected"]["path"].endswith("include/linux/kernel.h"))

        kstrtoint = repl.lookup_source_signature("kstrtoint", source_root=KERNEL_SOURCE_ROOT)
        self.assertEqual(kstrtoint["status"], "found", kstrtoint)
        self.assertEqual(kstrtoint["selected"]["pointer_arg_indices"], [0, 2])
        self.assertEqual(
            kstrtoint["selected"]["signature"],
            "int __must_check kstrtoint(const char *s, unsigned int base, int *res)",
        )
        self.assertTrue(kstrtoint["selected"]["path"].endswith("include/linux/kernel.h"))

        kstrtos16 = repl.lookup_source_signature("kstrtos16", source_root=KERNEL_SOURCE_ROOT)
        self.assertEqual(kstrtos16["status"], "found", kstrtos16)
        self.assertEqual(kstrtos16["selected"]["pointer_arg_indices"], [0, 2])
        self.assertEqual(
            kstrtos16["selected"]["signature"],
            "int __must_check kstrtos16(const char *s, unsigned int base, s16 *res)",
        )
        self.assertTrue(kstrtos16["selected"]["path"].endswith("include/linux/kernel.h"))

    def test_call_safety_sweep_is_advisory_and_does_not_promote_gate(self) -> None:
        if not KERNEL_SOURCE_ROOT.is_dir():
            self.skipTest("kernel source tree not present")

        seed_snapshot = repr(repl.CALL_SAFETY_SEEDS)
        summary = repl.run_call_safety_sweep(
            self.symbols,
            self.image,
            explicit_symbols=("__kmalloc", "kfree", "kstrdup_const", "kgsl_pwrctrl_force_no_nap_store"),
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

        kstrdup_const = rows["kstrdup_const"]
        self.assertEqual(kstrdup_const["gate_tier"], repl.CALL_SAFETY_DENY)
        self.assertEqual(kstrdup_const["source"]["status"], "found")
        self.assertEqual(kstrdup_const["advisory"]["tier"], repl.CALL_SAFETY_SAFE_WITH_VALID_PTR)
        self.assertFalse(kstrdup_const["advisory"]["candidate_safe"])
        self.assertIn(
            "unseeded-arg-memory-flow-without-gate-pointer-contract",
            kstrdup_const["advisory"]["danger_flags"],
        )
        with self.assertRaisesRegex(repl.ReplError, "call-safety gate refused"):
            repl.require_call_safety_for_call(
                self.symbols,
                self.image,
                "kstrdup_const",
                ("@src", "0x14000c0"),
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
        self.hex_to_bin_link = repl.resolve_verified(
            self.symbols,
            self.image,
            "hex_to_bin",
            purpose="call",
        ).link_vaddr
        self.hex2bin_link = repl.resolve_verified(
            self.symbols,
            self.image,
            "hex2bin",
            purpose="call",
        ).link_vaddr
        self.bin2hex_link = repl.resolve_verified(
            self.symbols,
            self.image,
            "bin2hex",
            purpose="call",
        ).link_vaddr
        self.parse_option_str_link = repl.resolve_verified(
            self.symbols,
            self.image,
            "parse_option_str",
            purpose="call",
            allow_pre_arg_deref=True,
        ).link_vaddr
        self.strsep_link = repl.resolve_verified(
            self.symbols,
            self.image,
            "strsep",
            purpose="call",
            allow_pre_arg_deref=True,
        ).link_vaddr
        self.simple_strtoull_link = repl.resolve_verified(
            self.symbols,
            self.image,
            "simple_strtoull",
            purpose="call",
        ).link_vaddr
        self.kstrtoull_link = repl.resolve_verified(
            self.symbols,
            self.image,
            "kstrtoull",
            purpose="call",
        ).link_vaddr
        self.kstrtoll_link = repl.resolve_verified(
            self.symbols,
            self.image,
            "kstrtoll",
            purpose="call",
            allow_pre_arg_deref=True,
        ).link_vaddr
        self.kstrtouint_link = repl.resolve_verified(
            self.symbols,
            self.image,
            "kstrtouint",
            purpose="call",
        ).link_vaddr
        self.kstrtou16_link = repl.resolve_verified(
            self.symbols,
            self.image,
            "kstrtou16",
            purpose="call",
        ).link_vaddr
        self.kstrtou8_link = repl.resolve_verified(
            self.symbols,
            self.image,
            "kstrtou8",
            purpose="call",
        ).link_vaddr
        self.kstrtos8_link = repl.resolve_verified(
            self.symbols,
            self.image,
            "kstrtos8",
            purpose="call",
        ).link_vaddr
        self.kstrtobool_link = repl.resolve_verified(
            self.symbols,
            self.image,
            "kstrtobool",
            purpose="call",
            allow_pre_arg_deref=True,
        ).link_vaddr
        self.kstrtoint_link = repl.resolve_verified(
            self.symbols,
            self.image,
            "kstrtoint",
            purpose="call",
        ).link_vaddr
        self.kstrtos16_link = repl.resolve_verified(
            self.symbols,
            self.image,
            "kstrtos16",
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
        self.strnchr_link = repl.resolve_verified(
            self.symbols,
            self.image,
            "strnchr",
            purpose="call",
            allow_pre_arg_deref=True,
        ).link_vaddr
        self.skip_spaces_link = repl.resolve_verified(
            self.symbols,
            self.image,
            "skip_spaces",
            purpose="call",
            allow_pre_arg_deref=True,
        ).link_vaddr
        self.strim_link = repl.resolve_verified(
            self.symbols,
            self.image,
            "strim",
            purpose="call",
            allow_pre_arg_deref=True,
        ).link_vaddr
        self.strreplace_link = repl.resolve_verified(
            self.symbols,
            self.image,
            "strreplace",
            purpose="call",
            allow_pre_arg_deref=True,
        ).link_vaddr
        self.strchr_link = repl.resolve_verified(
            self.symbols,
            self.image,
            "strchr",
            purpose="call",
            allow_pre_arg_deref=True,
        ).link_vaddr
        self.strchrnul_link = repl.resolve_verified(
            self.symbols,
            self.image,
            "strchrnul",
            purpose="call",
            allow_pre_arg_deref=True,
        ).link_vaddr
        self.strstr_link = repl.resolve_verified(
            self.symbols,
            self.image,
            "strstr",
            purpose="call",
            allow_pre_arg_deref=True,
        ).link_vaddr
        self.strnstr_link = repl.resolve_verified(
            self.symbols,
            self.image,
            "strnstr",
            purpose="call",
            allow_pre_arg_deref=True,
        ).link_vaddr
        self.match_string_link = repl.resolve_verified(
            self.symbols,
            self.image,
            "match_string",
            purpose="call",
            allow_pre_arg_deref=True,
        ).link_vaddr
        self.sysfs_streq_link = repl.resolve_verified(
            self.symbols,
            self.image,
            "sysfs_streq",
            purpose="call",
            allow_pre_arg_deref=True,
        ).link_vaddr
        self.kstrdup_link = repl.resolve_verified(
            self.symbols,
            self.image,
            "kstrdup",
            purpose="call",
        ).link_vaddr
        self.kstrndup_link = repl.resolve_verified(
            self.symbols,
            self.image,
            "kstrndup",
            purpose="call",
        ).link_vaddr
        self.kmemdup_link = repl.resolve_verified(
            self.symbols,
            self.image,
            "kmemdup",
            purpose="call",
        ).link_vaddr
        self.kmemdup_nul_link = repl.resolve_verified(
            self.symbols,
            self.image,
            "kmemdup_nul",
            purpose="call",
        ).link_vaddr
        self.strpbrk_link = repl.resolve_verified(
            self.symbols,
            self.image,
            "strpbrk",
            purpose="call",
            allow_pre_arg_deref=True,
        ).link_vaddr
        self.strspn_link = repl.resolve_verified(
            self.symbols,
            self.image,
            "strspn",
            purpose="call",
            allow_pre_arg_deref=True,
        ).link_vaddr
        self.strcspn_link = repl.resolve_verified(
            self.symbols,
            self.image,
            "strcspn",
            purpose="call",
            allow_pre_arg_deref=True,
        ).link_vaddr
        self.strcmp_link = repl.resolve_verified(
            self.symbols,
            self.image,
            "strcmp",
            purpose="call",
            allow_pre_arg_deref=True,
        ).link_vaddr
        self.strcasecmp_link = repl.resolve_verified(
            self.symbols,
            self.image,
            "strcasecmp",
            purpose="call",
            allow_pre_arg_deref=True,
        ).link_vaddr
        self.strncasecmp_link = repl.resolve_verified(
            self.symbols,
            self.image,
            "strncasecmp",
            purpose="call",
            allow_pre_arg_deref=True,
        ).link_vaddr
        self.strncmp_link = repl.resolve_verified(
            self.symbols,
            self.image,
            "strncmp",
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
        self.strcpy_link = repl.resolve_verified(
            self.symbols,
            self.image,
            "strcpy",
            purpose="call",
            allow_pre_arg_deref=True,
        ).link_vaddr
        self.strcat_link = repl.resolve_verified(
            self.symbols,
            self.image,
            "strcat",
            purpose="call",
            allow_pre_arg_deref=True,
        ).link_vaddr
        self.strncat_link = repl.resolve_verified(
            self.symbols,
            self.image,
            "strncat",
            purpose="call",
            allow_pre_arg_deref=True,
        ).link_vaddr
        self.strlcat_link = repl.resolve_verified(
            self.symbols,
            self.image,
            "strlcat",
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
        self.memchr_link = repl.resolve_verified(
            self.symbols,
            self.image,
            "memchr",
            purpose="call",
            allow_pre_arg_deref=True,
        ).link_vaddr
        self.memchr_inv_link = repl.resolve_verified(
            self.symbols,
            self.image,
            "memchr_inv",
            purpose="call",
            allow_pre_arg_deref=True,
        ).link_vaddr
        self.memcpy_link = repl.resolve_verified(
            self.symbols,
            self.image,
            "memcpy",
            purpose="call",
            allow_pre_arg_deref=True,
        ).link_vaddr
        self.memmove_link = repl.resolve_verified(
            self.symbols,
            self.image,
            "memmove",
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
        self.memset_link = repl.resolve_verified(
            self.symbols,
            self.image,
            "memset",
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
            byte_addr = addr + offset
            qaddr = byte_addr & ~0x7
            shift = (byte_addr & 0x7) * 8
            out.append((self.heap.get(qaddr, 0) >> shift) & 0xFF)
        return bytes(out)

    def _c_string(self, addr: int, max_len: int = 4096) -> bytes:
        data = self._heap_bytes(addr, max_len)
        end = data.find(b"\x00")
        if end < 0:
            raise AssertionError(f"NUL terminator not found at {addr:#x}")
        return data[:end]

    def _set_heap_bytes(self, addr: int, data: bytes) -> None:
        for offset, byte in enumerate(data):
            byte_addr = addr + offset
            qaddr = byte_addr & ~0x7
            shift = (byte_addr & 0x7) * 8
            current = self.heap.get(qaddr, 0)
            self.heap[qaddr] = (current & ~(0xFF << shift)) | ((byte & 0xFF) << shift)

    def _allocated_base_for(self, addr: int, length: int) -> int | None:
        for base in self.allocated:
            if base <= addr and addr + length <= base + 0x1000:
                return base
        return None

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
            assert self.hex_to_bin_link is not None
            hex_to_bin = self.hex_to_bin_link + self.slide
            assert self.hex2bin_link is not None
            hex2bin = self.hex2bin_link + self.slide
            assert self.bin2hex_link is not None
            bin2hex = self.bin2hex_link + self.slide
            assert self.parse_option_str_link is not None
            parse_option_str = self.parse_option_str_link + self.slide
            assert self.strsep_link is not None
            strsep = self.strsep_link + self.slide
            assert self.simple_strtoull_link is not None
            simple_strtoull = self.simple_strtoull_link + self.slide
            assert self.kstrtoull_link is not None
            kstrtoull = self.kstrtoull_link + self.slide
            assert self.kstrtoll_link is not None
            kstrtoll = self.kstrtoll_link + self.slide
            assert self.kstrtouint_link is not None
            kstrtouint = self.kstrtouint_link + self.slide
            assert self.kstrtou16_link is not None
            kstrtou16 = self.kstrtou16_link + self.slide
            assert self.kstrtou8_link is not None
            kstrtou8 = self.kstrtou8_link + self.slide
            assert self.kstrtos8_link is not None
            kstrtos8 = self.kstrtos8_link + self.slide
            assert self.kstrtobool_link is not None
            kstrtobool = self.kstrtobool_link + self.slide
            assert self.kstrtoint_link is not None
            kstrtoint = self.kstrtoint_link + self.slide
            assert self.kstrtos16_link is not None
            kstrtos16 = self.kstrtos16_link + self.slide
            assert self.ksize_link is not None
            ksize = self.ksize_link + self.slide
            assert self.strnlen_link is not None
            strnlen = self.strnlen_link + self.slide
            assert self.strlen_link is not None
            strlen = self.strlen_link + self.slide
            assert self.strnchr_link is not None
            strnchr = self.strnchr_link + self.slide
            assert self.skip_spaces_link is not None
            skip_spaces = self.skip_spaces_link + self.slide
            assert self.strim_link is not None
            strim = self.strim_link + self.slide
            assert self.strreplace_link is not None
            strreplace = self.strreplace_link + self.slide
            assert self.strchr_link is not None
            strchr = self.strchr_link + self.slide
            assert self.strchrnul_link is not None
            strchrnul = self.strchrnul_link + self.slide
            assert self.strstr_link is not None
            strstr = self.strstr_link + self.slide
            assert self.strnstr_link is not None
            strnstr = self.strnstr_link + self.slide
            assert self.match_string_link is not None
            match_string = self.match_string_link + self.slide
            assert self.sysfs_streq_link is not None
            sysfs_streq = self.sysfs_streq_link + self.slide
            assert self.kstrdup_link is not None
            kstrdup = self.kstrdup_link + self.slide
            assert self.kstrndup_link is not None
            kstrndup = self.kstrndup_link + self.slide
            assert self.kmemdup_link is not None
            kmemdup = self.kmemdup_link + self.slide
            assert self.kmemdup_nul_link is not None
            kmemdup_nul = self.kmemdup_nul_link + self.slide
            assert self.strpbrk_link is not None
            strpbrk = self.strpbrk_link + self.slide
            assert self.strspn_link is not None
            strspn = self.strspn_link + self.slide
            assert self.strcspn_link is not None
            strcspn = self.strcspn_link + self.slide
            assert self.strcmp_link is not None
            strcmp = self.strcmp_link + self.slide
            assert self.strcasecmp_link is not None
            strcasecmp = self.strcasecmp_link + self.slide
            assert self.strncasecmp_link is not None
            strncasecmp = self.strncasecmp_link + self.slide
            assert self.strncmp_link is not None
            strncmp = self.strncmp_link + self.slide
            assert self.strscpy_link is not None
            strscpy = self.strscpy_link + self.slide
            assert self.strlcpy_link is not None
            strlcpy = self.strlcpy_link + self.slide
            assert self.strncpy_link is not None
            strncpy = self.strncpy_link + self.slide
            assert self.strcpy_link is not None
            strcpy = self.strcpy_link + self.slide
            assert self.strcat_link is not None
            strcat = self.strcat_link + self.slide
            assert self.strncat_link is not None
            strncat = self.strncat_link + self.slide
            assert self.strlcat_link is not None
            strlcat = self.strlcat_link + self.slide
            assert self.memcmp_link is not None
            memcmp = self.memcmp_link + self.slide
            assert self.memchr_link is not None
            memchr = self.memchr_link + self.slide
            assert self.memchr_inv_link is not None
            memchr_inv = self.memchr_inv_link + self.slide
            assert self.memcpy_link is not None
            memcpy = self.memcpy_link + self.slide
            assert self.memmove_link is not None
            memmove = self.memmove_link + self.slide
            assert self.strrchr_link is not None
            strrchr = self.strrchr_link + self.slide
            assert self.memset_link is not None
            memset = self.memset_link + self.slide
            assert self.filp_open_link is not None
            filp_open = self.filp_open_link + self.slide
            assert self.filp_close_link is not None
            filp_close = self.filp_close_link + self.slide
            assert self.kernel_read_link is not None
            kernel_read = self.kernel_read_link + self.slide
            if arg0 == bin2hex:
                if arg1 not in self.allocated:
                    raise AssertionError(f"bin2hex dst is not an allocated pointer: {arg1:#x}")
                if arg2 not in self.allocated:
                    raise AssertionError(f"bin2hex src is not an allocated pointer: {arg2:#x}")
                src = self._heap_bytes(arg2, arg3)
                encoded = src.hex().encode("ascii")
                self._set_heap_bytes(arg1, encoded)
                lines.append(f"A90R{arg1 + len(encoded):x}")
            elif arg0 == parse_option_str:
                if arg1 not in self.allocated:
                    raise AssertionError(f"parse_option_str str is not an allocated pointer: {arg1:#x}")
                if arg2 not in self.allocated:
                    raise AssertionError(f"parse_option_str option is not an allocated pointer: {arg2:#x}")
                option = self._c_string(arg2)
                haystack = self._c_string(arg1)
                tokens = haystack.split(b",") if haystack else []
                lines.append("A90R1" if option in tokens else "A90R0")
            elif arg0 == strsep:
                if arg1 not in self.allocated:
                    raise AssertionError(f"strsep slot is not an allocated pointer: {arg1:#x}")
                if arg2 not in self.allocated:
                    raise AssertionError(f"strsep delimiter is not an allocated pointer: {arg2:#x}")
                cursor = int.from_bytes(self._heap_bytes(arg1, 8), "little")
                if cursor == 0:
                    lines.append("A90R0")
                else:
                    if cursor not in self.allocated:
                        raise AssertionError(f"strsep cursor is not an allocated pointer: {cursor:#x}")
                    data = self._c_string(cursor)
                    delims = self._c_string(arg2)
                    hit = next((index for index, byte in enumerate(data) if byte in delims), None)
                    if hit is None:
                        self._set_heap_bytes(arg1, (0).to_bytes(8, "little"))
                    else:
                        self._set_heap_bytes(cursor + hit, b"\x00")
                        self._set_heap_bytes(arg1, (cursor + hit + 1).to_bytes(8, "little"))
                    lines.append(f"A90R{cursor:x}")
            elif arg0 == simple_strtoull:
                if arg1 not in self.allocated:
                    raise AssertionError(f"simple_strtoull input is not an allocated pointer: {arg1:#x}")
                if arg2 not in self.allocated:
                    raise AssertionError(f"simple_strtoull endp slot is not an allocated pointer: {arg2:#x}")
                data = self._c_string(arg1)
                base = arg3
                value = 0
                end_offset = 0
                for index, byte in enumerate(data):
                    ch = chr(byte)
                    if "0" <= ch <= "9":
                        digit = ord(ch) - ord("0")
                    elif "a" <= ch.lower() <= "f":
                        digit = ord(ch.lower()) - ord("a") + 10
                    else:
                        break
                    if digit >= base:
                        break
                    value = value * base + digit
                    end_offset = index + 1
                self._set_heap_bytes(arg2, (arg1 + end_offset).to_bytes(8, "little"))
                lines.append(f"A90R{value:x}")
            elif arg0 == kstrtoull:
                if arg1 not in self.allocated:
                    raise AssertionError(f"kstrtoull input is not an allocated pointer: {arg1:#x}")
                if arg3 not in self.allocated:
                    raise AssertionError(f"kstrtoull result slot is not an allocated pointer: {arg3:#x}")
                data = self._c_string(arg1)
                base = arg2
                value = 0
                parsed_any = False
                for byte in data:
                    ch = chr(byte)
                    if "0" <= ch <= "9":
                        digit = ord(ch) - ord("0")
                    elif "a" <= ch.lower() <= "f":
                        digit = ord(ch.lower()) - ord("a") + 10
                    else:
                        lines.append("A90Rffffffea")
                        break
                    if digit >= base:
                        lines.append("A90Rffffffea")
                        break
                    parsed_any = True
                    value = value * base + digit
                else:
                    if not parsed_any:
                        lines.append("A90Rffffffea")
                    elif value > 0xFFFFFFFFFFFFFFFF:
                        lines.append("A90Rffffffde")
                    else:
                        self._set_heap_bytes(arg3, value.to_bytes(8, "little"))
                        lines.append("A90R0")
            elif arg0 == kstrtoll:
                if arg1 not in self.allocated:
                    raise AssertionError(f"kstrtoll input is not an allocated pointer: {arg1:#x}")
                if arg3 not in self.allocated:
                    raise AssertionError(f"kstrtoll result slot is not an allocated pointer: {arg3:#x}")
                data = self._c_string(arg1)
                base = arg2
                sign = 1
                if data.startswith(b"-"):
                    sign = -1
                    data = data[1:]
                elif data.startswith(b"+"):
                    data = data[1:]
                value = 0
                parsed_any = False
                for byte in data:
                    ch = chr(byte)
                    if "0" <= ch <= "9":
                        digit = ord(ch) - ord("0")
                    elif "a" <= ch.lower() <= "f":
                        digit = ord(ch.lower()) - ord("a") + 10
                    else:
                        lines.append("A90Rffffffea")
                        break
                    if digit >= base:
                        lines.append("A90Rffffffea")
                        break
                    parsed_any = True
                    value = value * base + digit
                else:
                    signed = sign * value
                    if not parsed_any:
                        lines.append("A90Rffffffea")
                    elif signed < -0x8000000000000000 or signed > 0x7FFFFFFFFFFFFFFF:
                        lines.append("A90Rffffffde")
                    else:
                        self._set_heap_bytes(arg3, (signed & 0xFFFFFFFFFFFFFFFF).to_bytes(8, "little"))
                        lines.append("A90R0")
            elif arg0 == kstrtouint:
                if arg1 not in self.allocated:
                    raise AssertionError(f"kstrtouint input is not an allocated pointer: {arg1:#x}")
                if arg3 not in self.allocated:
                    raise AssertionError(f"kstrtouint result slot is not an allocated pointer: {arg3:#x}")
                data = self._c_string(arg1)
                base = arg2
                value = 0
                for byte in data:
                    ch = chr(byte)
                    if "0" <= ch <= "9":
                        digit = ord(ch) - ord("0")
                    elif "a" <= ch.lower() <= "f":
                        digit = ord(ch.lower()) - ord("a") + 10
                    else:
                        lines.append("A90Rffffffea")
                        break
                    if digit >= base:
                        lines.append("A90Rffffffea")
                        break
                    value = value * base + digit
                else:
                    if value > 0xFFFFFFFF:
                        lines.append("A90Rffffffde")
                    else:
                        self._set_heap_bytes(arg3, value.to_bytes(4, "little"))
                        lines.append("A90R0")
            elif arg0 == kstrtou16:
                if arg1 not in self.allocated:
                    raise AssertionError(f"kstrtou16 input is not an allocated pointer: {arg1:#x}")
                if arg3 not in self.allocated:
                    raise AssertionError(f"kstrtou16 result slot is not an allocated pointer: {arg3:#x}")
                data = self._c_string(arg1)
                base = arg2
                value = 0
                parsed_any = False
                for byte in data:
                    ch = chr(byte)
                    if "0" <= ch <= "9":
                        digit = ord(ch) - ord("0")
                    elif "a" <= ch.lower() <= "f":
                        digit = ord(ch.lower()) - ord("a") + 10
                    else:
                        lines.append("A90Rffffffea")
                        break
                    if digit >= base:
                        lines.append("A90Rffffffea")
                        break
                    parsed_any = True
                    value = value * base + digit
                else:
                    if not parsed_any:
                        lines.append("A90Rffffffea")
                    elif value > 0xFFFF:
                        lines.append("A90Rffffffde")
                    else:
                        self._set_heap_bytes(arg3, value.to_bytes(2, "little"))
                        lines.append("A90R0")
            elif arg0 == kstrtou8:
                if arg1 not in self.allocated:
                    raise AssertionError(f"kstrtou8 input is not an allocated pointer: {arg1:#x}")
                if arg3 not in self.allocated:
                    raise AssertionError(f"kstrtou8 result slot is not an allocated pointer: {arg3:#x}")
                data = self._c_string(arg1)
                base = arg2
                value = 0
                parsed_any = False
                for byte in data:
                    ch = chr(byte)
                    if "0" <= ch <= "9":
                        digit = ord(ch) - ord("0")
                    elif "a" <= ch.lower() <= "f":
                        digit = ord(ch.lower()) - ord("a") + 10
                    else:
                        lines.append("A90Rffffffea")
                        break
                    if digit >= base:
                        lines.append("A90Rffffffea")
                        break
                    parsed_any = True
                    value = value * base + digit
                else:
                    if not parsed_any:
                        lines.append("A90Rffffffea")
                    elif value > 0xFF:
                        lines.append("A90Rffffffde")
                    else:
                        self._set_heap_bytes(arg3, value.to_bytes(1, "little"))
                        lines.append("A90R0")
            elif arg0 == kstrtos8:
                if arg1 not in self.allocated:
                    raise AssertionError(f"kstrtos8 input is not an allocated pointer: {arg1:#x}")
                if arg3 not in self.allocated:
                    raise AssertionError(f"kstrtos8 result slot is not an allocated pointer: {arg3:#x}")
                data = self._c_string(arg1)
                base = arg2
                sign = 1
                if data.startswith(b"-"):
                    sign = -1
                    data = data[1:]
                elif data.startswith(b"+"):
                    data = data[1:]
                value = 0
                parsed_any = False
                for byte in data:
                    ch = chr(byte)
                    if "0" <= ch <= "9":
                        digit = ord(ch) - ord("0")
                    elif "a" <= ch.lower() <= "f":
                        digit = ord(ch.lower()) - ord("a") + 10
                    else:
                        lines.append("A90Rffffffea")
                        break
                    if digit >= base:
                        lines.append("A90Rffffffea")
                        break
                    parsed_any = True
                    value = value * base + digit
                else:
                    signed = sign * value
                    if not parsed_any:
                        lines.append("A90Rffffffea")
                    elif signed < -0x80 or signed > 0x7F:
                        lines.append("A90Rffffffde")
                    else:
                        self._set_heap_bytes(arg3, (signed & 0xFF).to_bytes(1, "little"))
                        lines.append("A90R0")
            elif arg0 == kstrtobool:
                if arg1 not in self.allocated:
                    raise AssertionError(f"kstrtobool input is not an allocated pointer: {arg1:#x}")
                if arg2 not in self.allocated:
                    raise AssertionError(f"kstrtobool result slot is not an allocated pointer: {arg2:#x}")
                data = self._c_string(arg1)
                parsed: bool | None = None
                if data in (b"Y", b"y", b"1"):
                    parsed = True
                elif data in (b"N", b"n", b"0"):
                    parsed = False
                elif len(data) >= 2 and data[0:1] in (b"O", b"o"):
                    if data[1:2] in (b"N", b"n"):
                        parsed = True
                    elif data[1:2] in (b"F", b"f"):
                        parsed = False
                if parsed is None:
                    lines.append("A90Rffffffea")
                else:
                    self._set_heap_bytes(arg2, b"\x01" if parsed else b"\x00")
                    lines.append("A90R0")
            elif arg0 == kstrtoint:
                if arg1 not in self.allocated:
                    raise AssertionError(f"kstrtoint input is not an allocated pointer: {arg1:#x}")
                if arg3 not in self.allocated:
                    raise AssertionError(f"kstrtoint result slot is not an allocated pointer: {arg3:#x}")
                data = self._c_string(arg1)
                base = arg2
                sign = 1
                if data.startswith(b"-"):
                    sign = -1
                    data = data[1:]
                elif data.startswith(b"+"):
                    data = data[1:]
                value = 0
                parsed_any = False
                for byte in data:
                    ch = chr(byte)
                    if "0" <= ch <= "9":
                        digit = ord(ch) - ord("0")
                    elif "a" <= ch.lower() <= "f":
                        digit = ord(ch.lower()) - ord("a") + 10
                    else:
                        lines.append("A90Rffffffea")
                        break
                    if digit >= base:
                        lines.append("A90Rffffffea")
                        break
                    parsed_any = True
                    value = value * base + digit
                else:
                    signed = sign * value
                    if not parsed_any:
                        lines.append("A90Rffffffea")
                    elif signed < -0x80000000 or signed > 0x7FFFFFFF:
                        lines.append("A90Rffffffde")
                    else:
                        self._set_heap_bytes(arg3, (signed & 0xFFFFFFFF).to_bytes(4, "little"))
                        lines.append("A90R0")
            elif arg0 == kstrtos16:
                if arg1 not in self.allocated:
                    raise AssertionError(f"kstrtos16 input is not an allocated pointer: {arg1:#x}")
                if arg3 not in self.allocated:
                    raise AssertionError(f"kstrtos16 result slot is not an allocated pointer: {arg3:#x}")
                data = self._c_string(arg1)
                base = arg2
                sign = 1
                if data.startswith(b"-"):
                    sign = -1
                    data = data[1:]
                elif data.startswith(b"+"):
                    data = data[1:]
                value = 0
                parsed_any = False
                for byte in data:
                    ch = chr(byte)
                    if "0" <= ch <= "9":
                        digit = ord(ch) - ord("0")
                    elif "a" <= ch.lower() <= "f":
                        digit = ord(ch.lower()) - ord("a") + 10
                    else:
                        lines.append("A90Rffffffea")
                        break
                    if digit >= base:
                        lines.append("A90Rffffffea")
                        break
                    parsed_any = True
                    value = value * base + digit
                else:
                    signed = sign * value
                    if not parsed_any:
                        lines.append("A90Rffffffea")
                    elif signed < -0x8000 or signed > 0x7FFF:
                        lines.append("A90Rffffffde")
                    else:
                        self._set_heap_bytes(arg3, (signed & 0xFFFF).to_bytes(2, "little"))
                        lines.append("A90R0")
            elif arg0 == hex2bin:
                if arg1 not in self.allocated:
                    raise AssertionError(f"hex2bin dst is not an allocated pointer: {arg1:#x}")
                if arg2 not in self.allocated:
                    raise AssertionError(f"hex2bin src is not an allocated pointer: {arg2:#x}")
                src = self._heap_bytes(arg2, arg3 * 2)
                try:
                    decoded = bytes.fromhex(src.decode("ascii"))
                except ValueError:
                    lines.append("A90Rffffffea")
                else:
                    if len(decoded) != arg3:
                        raise AssertionError(f"hex2bin decoded length mismatch: {len(decoded)} != {arg3}")
                    self._set_heap_bytes(arg1, decoded)
                    lines.append("A90R0")
            elif arg0 == hex_to_bin:
                ch = arg1 & 0xFF
                if 0x30 <= ch <= 0x39:
                    result = ch - 0x30
                else:
                    lower = ch | 0x20
                    if 0x61 <= lower <= 0x66:
                        result = lower - 0x57
                    else:
                        result = repl.HEX_TO_BIN_INVALID_RETURN
                lines.append(f"A90R{result:x}")
            elif arg0 == kmalloc:
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
            elif arg0 == strnchr:
                if arg1 not in self.allocated:
                    raise AssertionError(f"strnchr string is not an allocated pointer: {arg1:#x}")
                if arg2 > len(repl.STRNCHR_PROOF_BYTES) + repl.STRNCHR_CANARY_LEN:
                    raise AssertionError(f"unexpected strnchr count: {arg2:#x}")
                data = self._heap_bytes(arg1, arg2)
                search = arg3 & 0xFF
                offset = -1
                for index, byte in enumerate(data):
                    if byte == 0:
                        break
                    if byte == search:
                        offset = index
                        break
                lines.append("A90R0" if offset < 0 else f"A90R{arg1 + offset:x}")
            elif arg0 == skip_spaces:
                if arg1 not in self.allocated:
                    raise AssertionError(f"skip_spaces string is not an allocated pointer: {arg1:#x}")
                scan_len = max(len(repl.SKIP_SPACES_PROOF_BYTES), len(repl.SKIP_SPACES_NO_LEADING_BYTES))
                data = self._heap_bytes(arg1, scan_len)
                nul = data.find(b"\x00")
                if nul < 0:
                    raise AssertionError("skip_spaces proof buffer is not NUL-terminated in scan window")
                offset = 0
                while offset < nul and data[offset] == 0x20:
                    offset += 1
                lines.append(f"A90R{arg1 + offset:x}")
            elif arg0 == strim:
                if arg1 not in self.allocated:
                    raise AssertionError(f"strim string is not an allocated pointer: {arg1:#x}")
                scan_len = max(len(repl.STRIM_PROOF_BYTES), len(repl.STRIM_CLEAN_BYTES))
                data = self._heap_bytes(arg1, scan_len)
                nul = data.find(b"\x00")
                if nul < 0:
                    raise AssertionError("strim proof buffer is not NUL-terminated in scan window")
                raw = data[:nul]
                leading = 0
                while leading < len(raw) and raw[leading] == 0x20:
                    leading += 1
                trimmed_end = len(raw.rstrip(b" "))
                if trimmed_end < len(raw):
                    self._set_heap_bytes(arg1 + trimmed_end, b"\x00")
                lines.append(f"A90R{arg1 + leading:x}")
            elif arg0 == strreplace:
                if arg1 not in self.allocated:
                    raise AssertionError(f"strreplace string is not an allocated pointer: {arg1:#x}")
                data = self._heap_bytes(arg1, len(repl.STRREPLACE_PROOF_BYTES))
                nul = data.find(b"\x00")
                if nul < 0:
                    raise AssertionError("strreplace proof buffer is not NUL-terminated in scan window")
                body = bytearray(data[:nul])
                for index, byte in enumerate(body):
                    if byte == (arg2 & 0xFF):
                        body[index] = arg3 & 0xFF
                self._set_heap_bytes(arg1, bytes(body))
                lines.append(f"A90R{arg1 + nul:x}")
            elif arg0 == strchr:
                if arg1 not in self.allocated:
                    raise AssertionError(f"strchr string is not an allocated pointer: {arg1:#x}")
                data = self._heap_bytes(arg1, len(repl.STRCHR_PROOF_BYTES))
                nul = data.find(b"\x00")
                if nul < 0:
                    raise AssertionError("strchr proof buffer is not NUL-terminated in scan window")
                search = arg2 & 0xFF
                offset = data[:nul].find(bytes([search]))
                lines.append("A90R0" if offset < 0 else f"A90R{arg1 + offset:x}")
            elif arg0 == strchrnul:
                if arg1 not in self.allocated:
                    raise AssertionError(f"strchrnul string is not an allocated pointer: {arg1:#x}")
                data = self._heap_bytes(arg1, len(repl.STRCHRNUL_PROOF_BYTES))
                nul = data.find(b"\x00")
                if nul < 0:
                    raise AssertionError("strchrnul proof buffer is not NUL-terminated in scan window")
                search = arg2 & 0xFF
                offset = data[:nul].find(bytes([search]))
                lines.append(f"A90R{arg1 + (nul if offset < 0 else offset):x}")
            elif arg0 == strstr:
                if arg1 not in self.allocated:
                    raise AssertionError(f"strstr haystack is not an allocated pointer: {arg1:#x}")
                if arg2 not in self.allocated:
                    raise AssertionError(f"strstr needle is not an allocated pointer: {arg2:#x}")
                haystack_data = self._heap_bytes(arg1, len(repl.STRSTR_HAYSTACK_BYTES))
                haystack_nul = haystack_data.find(b"\x00")
                if haystack_nul < 0:
                    raise AssertionError("strstr haystack is not NUL-terminated in scan window")
                needle_data = self._heap_bytes(
                    arg2,
                    max(len(repl.STRSTR_NEEDLE_BYTES), len(repl.STRSTR_MISSING_BYTES)),
                )
                needle_nul = needle_data.find(b"\x00")
                if needle_nul < 0:
                    raise AssertionError("strstr needle is not NUL-terminated in scan window")
                needle = needle_data[:needle_nul]
                offset = 0 if not needle else haystack_data[:haystack_nul].find(needle)
                lines.append("A90R0" if offset < 0 else f"A90R{arg1 + offset:x}")
            elif arg0 == strnstr:
                if arg1 not in self.allocated:
                    raise AssertionError(f"strnstr haystack is not an allocated pointer: {arg1:#x}")
                if arg2 not in self.allocated:
                    raise AssertionError(f"strnstr needle is not an allocated pointer: {arg2:#x}")
                count = arg3
                haystack_data = self._heap_bytes(arg1, count)
                needle_data = self._heap_bytes(
                    arg2,
                    max(len(repl.STRNSTR_NEEDLE_BYTES), len(repl.STRNSTR_MISSING_BYTES)),
                )
                needle_nul = needle_data.find(b"\x00")
                if needle_nul < 0:
                    raise AssertionError("strnstr needle is not NUL-terminated in scan window")
                needle = needle_data[:needle_nul]
                offset = -1
                if not needle:
                    offset = 0
                elif len(needle) <= count:
                    for index in range(0, count - len(needle) + 1):
                        if haystack_data[index:index + len(needle)] == needle:
                            offset = index
                            break
                lines.append("A90R0" if offset < 0 else f"A90R{arg1 + offset:x}")
            elif arg0 == match_string:
                count = arg2
                table_base = self._allocated_base_for(arg1, max(8, count * 8))
                if table_base is None:
                    raise AssertionError(f"match_string array is not in an allocated buffer: {arg1:#x}")
                search_base = self._allocated_base_for(arg3, repl.MATCH_STRING_MAX_STRING_SCAN_LEN)
                if search_base is None:
                    raise AssertionError(f"match_string search is not in an allocated buffer: {arg3:#x}")
                search_data = self._heap_bytes(arg3, repl.MATCH_STRING_MAX_STRING_SCAN_LEN)
                search_nul = search_data.find(b"\x00")
                if search_nul < 0:
                    raise AssertionError("match_string search is not NUL-terminated in scan window")
                search = search_data[:search_nul]
                result = repl.MATCH_STRING_EINVAL_RETURN
                for index in range(count):
                    entry = int.from_bytes(self._heap_bytes(arg1 + (index * 8), 8), "little")
                    if entry == 0:
                        break
                    item_base = self._allocated_base_for(entry, repl.MATCH_STRING_MAX_STRING_SCAN_LEN)
                    if item_base is None:
                        raise AssertionError(f"match_string item is not in an allocated buffer: {entry:#x}")
                    item_data = self._heap_bytes(entry, repl.MATCH_STRING_MAX_STRING_SCAN_LEN)
                    item_nul = item_data.find(b"\x00")
                    if item_nul < 0:
                        raise AssertionError("match_string item is not NUL-terminated in scan window")
                    if item_data[:item_nul] == search:
                        result = index
                        break
                lines.append(f"A90R{result:x}")
            elif arg0 == sysfs_streq:
                if arg1 not in self.allocated:
                    raise AssertionError(f"sysfs_streq left string is not an allocated pointer: {arg1:#x}")
                if arg2 not in self.allocated:
                    raise AssertionError(f"sysfs_streq right string is not an allocated pointer: {arg2:#x}")
                left_data = self._heap_bytes(arg1, repl.SYSFS_STREQ_SCAN_LEN)
                right_data = self._heap_bytes(arg2, repl.SYSFS_STREQ_SCAN_LEN)
                left_nul = left_data.find(b"\x00")
                right_nul = right_data.find(b"\x00")
                if left_nul < 0 or right_nul < 0:
                    raise AssertionError("sysfs_streq proof strings are not NUL-terminated in scan window")
                left = left_data[:left_nul]
                right = right_data[:right_nul]
                equal = (
                    left == right
                    or (left.endswith(b"\n") and left[:-1] == right)
                    or (right.endswith(b"\n") and right[:-1] == left)
                )
                lines.append("A90R1" if equal else "A90R0")
            elif arg0 == kstrdup:
                if arg1 not in self.allocated:
                    raise AssertionError(f"kstrdup source string is not an allocated pointer: {arg1:#x}")
                data = self._heap_bytes(arg1, repl.KSTRDUP_SOURCE_SCAN_LEN)
                nul = data.find(b"\x00")
                if nul < 0:
                    raise AssertionError("kstrdup source string is not NUL-terminated in scan window")
                duplicate = data[:nul + 1]
                ptr = self.next_heap_ptr
                self.next_heap_ptr += 0x1000
                self.allocated.add(ptr)
                self._set_heap_bytes(ptr, duplicate)
                lines.append(f"A90R{ptr:x}")
            elif arg0 == kstrndup:
                if arg1 not in self.allocated:
                    raise AssertionError(f"kstrndup source string is not an allocated pointer: {arg1:#x}")
                if arg2 > repl.KSTRNDUP_SOURCE_SCAN_LEN:
                    raise AssertionError(f"unexpected kstrndup bound: {arg2:#x}")
                data = self._heap_bytes(arg1, arg2)
                nul = data.find(b"\x00")
                length = arg2 if nul < 0 else nul
                duplicate = data[:length] + b"\x00"
                ptr = self.next_heap_ptr
                self.next_heap_ptr += 0x1000
                self.allocated.add(ptr)
                self._set_heap_bytes(ptr, duplicate)
                lines.append(f"A90R{ptr:x}")
            elif arg0 == kmemdup:
                if arg1 not in self.allocated:
                    raise AssertionError(f"kmemdup source buffer is not an allocated pointer: {arg1:#x}")
                if arg2 > repl.KMEMDUP_SOURCE_SCAN_LEN:
                    raise AssertionError(f"unexpected kmemdup length: {arg2:#x}")
                duplicate = self._heap_bytes(arg1, arg2)
                ptr = self.next_heap_ptr
                self.next_heap_ptr += 0x1000
                self.allocated.add(ptr)
                self._set_heap_bytes(ptr, duplicate)
                lines.append(f"A90R{ptr:x}")
            elif arg0 == kmemdup_nul:
                if arg1 not in self.allocated:
                    raise AssertionError(f"kmemdup_nul source buffer is not an allocated pointer: {arg1:#x}")
                if arg2 > repl.KMEMDUP_NUL_SOURCE_SCAN_LEN:
                    raise AssertionError(f"unexpected kmemdup_nul length: {arg2:#x}")
                duplicate = self._heap_bytes(arg1, arg2) + b"\x00"
                ptr = self.next_heap_ptr
                self.next_heap_ptr += 0x1000
                self.allocated.add(ptr)
                self._set_heap_bytes(ptr, duplicate)
                lines.append(f"A90R{ptr:x}")
            elif arg0 == strpbrk:
                if arg1 not in self.allocated:
                    raise AssertionError(f"strpbrk haystack is not an allocated pointer: {arg1:#x}")
                if arg2 not in self.allocated:
                    raise AssertionError(f"strpbrk accept set is not an allocated pointer: {arg2:#x}")
                haystack_data = self._heap_bytes(arg1, len(repl.STRPBRK_HAYSTACK_BYTES))
                haystack_nul = haystack_data.find(b"\x00")
                if haystack_nul < 0:
                    raise AssertionError("strpbrk haystack is not NUL-terminated in scan window")
                accept_data = self._heap_bytes(
                    arg2,
                    max(len(repl.STRPBRK_ACCEPT_BYTES), len(repl.STRPBRK_MISSING_BYTES)),
                )
                accept_nul = accept_data.find(b"\x00")
                if accept_nul < 0:
                    raise AssertionError("strpbrk accept set is not NUL-terminated in scan window")
                accept = set(accept_data[:accept_nul])
                offset = -1
                for index, byte in enumerate(haystack_data[:haystack_nul]):
                    if byte in accept:
                        offset = index
                        break
                lines.append("A90R0" if offset < 0 else f"A90R{arg1 + offset:x}")
            elif arg0 == strspn:
                if arg1 not in self.allocated:
                    raise AssertionError(f"strspn haystack is not an allocated pointer: {arg1:#x}")
                if arg2 not in self.allocated:
                    raise AssertionError(f"strspn accept set is not an allocated pointer: {arg2:#x}")
                haystack_data = self._heap_bytes(arg1, len(repl.STRSPN_HAYSTACK_BYTES))
                haystack_nul = haystack_data.find(b"\x00")
                if haystack_nul < 0:
                    raise AssertionError("strspn haystack is not NUL-terminated in scan window")
                accept_data = self._heap_bytes(
                    arg2,
                    max(len(repl.STRSPN_PREFIX_ACCEPT_BYTES), len(repl.STRSPN_FULL_ACCEPT_BYTES)),
                )
                accept_nul = accept_data.find(b"\x00")
                if accept_nul < 0:
                    raise AssertionError("strspn accept set is not NUL-terminated in scan window")
                accept = set(accept_data[:accept_nul])
                span = 0
                for byte in haystack_data[:haystack_nul]:
                    if byte not in accept:
                        break
                    span += 1
                lines.append(f"A90R{span:x}")
            elif arg0 == strcspn:
                if arg1 not in self.allocated:
                    raise AssertionError(f"strcspn haystack is not an allocated pointer: {arg1:#x}")
                if arg2 not in self.allocated:
                    raise AssertionError(f"strcspn reject set is not an allocated pointer: {arg2:#x}")
                haystack_data = self._heap_bytes(arg1, len(repl.STRCSPN_HAYSTACK_BYTES))
                haystack_nul = haystack_data.find(b"\x00")
                if haystack_nul < 0:
                    raise AssertionError("strcspn haystack is not NUL-terminated in scan window")
                reject_data = self._heap_bytes(
                    arg2,
                    max(len(repl.STRCSPN_REJECT_BYTES), len(repl.STRCSPN_MISSING_BYTES)),
                )
                reject_nul = reject_data.find(b"\x00")
                if reject_nul < 0:
                    raise AssertionError("strcspn reject set is not NUL-terminated in scan window")
                reject = set(reject_data[:reject_nul])
                span = haystack_nul
                for index, byte in enumerate(haystack_data[:haystack_nul]):
                    if byte in reject:
                        span = index
                        break
                lines.append(f"A90R{span:x}")
            elif arg0 == strcmp:
                if arg1 not in self.allocated:
                    raise AssertionError(f"strcmp left is not an allocated pointer: {arg1:#x}")
                if arg2 not in self.allocated:
                    raise AssertionError(f"strcmp right is not an allocated pointer: {arg2:#x}")
                scan_len = len(repl.STRCMP_PROOF_BYTES) + repl.STRCMP_CANARY_LEN
                left = self._heap_bytes(arg1, scan_len)
                right = self._heap_bytes(arg2, scan_len)
                result = 0
                for left_byte, right_byte in zip(left, right, strict=True):
                    if left_byte != right_byte:
                        result = left_byte - right_byte
                        break
                    if left_byte == 0:
                        break
                if result < 0:
                    result &= 0xFFFFFFFF
                lines.append(f"A90R{result:x}")
            elif arg0 == strcasecmp:
                if arg1 not in self.allocated:
                    raise AssertionError(f"strcasecmp left is not an allocated pointer: {arg1:#x}")
                if arg2 not in self.allocated:
                    raise AssertionError(f"strcasecmp right is not an allocated pointer: {arg2:#x}")
                scan_len = len(repl.STRCASECMP_LEFT_BYTES) + repl.STRCASECMP_CANARY_LEN
                left = self._heap_bytes(arg1, scan_len)
                right = self._heap_bytes(arg2, scan_len)

                def fold(byte: int) -> int:
                    return byte + 0x20 if 0x41 <= byte <= 0x5A else byte

                result = 0
                for left_byte, right_byte in zip(left, right, strict=True):
                    left_folded = fold(left_byte)
                    right_folded = fold(right_byte)
                    if left_folded != right_folded:
                        result = left_folded - right_folded
                        break
                    if left_folded == 0:
                        break
                if result < 0:
                    result &= 0xFFFFFFFF
                lines.append(f"A90R{result:x}")
            elif arg0 == strncasecmp:
                if arg1 not in self.allocated:
                    raise AssertionError(f"strncasecmp left is not an allocated pointer: {arg1:#x}")
                if arg2 not in self.allocated:
                    raise AssertionError(f"strncasecmp right is not an allocated pointer: {arg2:#x}")
                count = arg3
                left = self._heap_bytes(arg1, count)
                right = self._heap_bytes(arg2, count)

                def fold(byte: int) -> int:
                    return byte + 0x20 if 0x41 <= byte <= 0x5A else byte

                result = 0
                for left_byte, right_byte in zip(left, right, strict=True):
                    left_folded = fold(left_byte)
                    right_folded = fold(right_byte)
                    if left_folded != right_folded:
                        result = left_folded - right_folded
                        break
                    if left_folded == 0:
                        break
                if result < 0:
                    result &= 0xFFFFFFFF
                lines.append(f"A90R{result:x}")
            elif arg0 == strncmp:
                if arg1 not in self.allocated:
                    raise AssertionError(f"strncmp left is not an allocated pointer: {arg1:#x}")
                if arg2 not in self.allocated:
                    raise AssertionError(f"strncmp right is not an allocated pointer: {arg2:#x}")
                count = arg3
                left = self._heap_bytes(arg1, count)
                right = self._heap_bytes(arg2, count)
                result = 0
                for left_byte, right_byte in zip(left, right, strict=True):
                    if left_byte != right_byte:
                        result = left_byte - right_byte
                        break
                    if left_byte == 0:
                        break
                if result < 0:
                    result &= 0xFFFFFFFF
                lines.append(f"A90R{result:x}")
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
            elif arg0 == strcpy:
                if arg1 not in self.allocated:
                    raise AssertionError(f"strcpy dst is not an allocated pointer: {arg1:#x}")
                if arg2 not in self.allocated:
                    raise AssertionError(f"strcpy src is not an allocated pointer: {arg2:#x}")
                data = self._heap_bytes(arg2, len(repl.STRCPY_PROOF_SRC_BYTES) + repl.STRCPY_CANARY_LEN)
                nul = data.find(b"\x00")
                if nul < 0:
                    raise AssertionError("strcpy source is not NUL-terminated in scan window")
                self._set_heap_bytes(arg1, data[:nul + 1])
                lines.append(f"A90R{arg1:x}")
            elif arg0 == strcat:
                if arg1 not in self.allocated:
                    raise AssertionError(f"strcat dst is not an allocated pointer: {arg1:#x}")
                if arg2 not in self.allocated:
                    raise AssertionError(f"strcat src is not an allocated pointer: {arg2:#x}")
                dst_scan = self._heap_bytes(arg1, len(repl.STRCAT_EXPECTED_DST_BYTES) + repl.STRCAT_CANARY_LEN)
                dst_nul = dst_scan.find(b"\x00")
                if dst_nul < 0:
                    raise AssertionError("strcat destination is not NUL-terminated in scan window")
                src_scan = self._heap_bytes(arg2, len(repl.STRCAT_SRC_BYTES) + repl.STRCAT_CANARY_LEN)
                src_nul = src_scan.find(b"\x00")
                if src_nul < 0:
                    raise AssertionError("strcat source is not NUL-terminated in scan window")
                self._set_heap_bytes(arg1 + dst_nul, src_scan[:src_nul + 1])
                lines.append(f"A90R{arg1:x}")
            elif arg0 == strncat:
                if arg1 not in self.allocated:
                    raise AssertionError(f"strncat dst is not an allocated pointer: {arg1:#x}")
                if arg2 not in self.allocated:
                    raise AssertionError(f"strncat src is not an allocated pointer: {arg2:#x}")
                if arg3 != repl.STRNCAT_PROOF_COUNT:
                    raise AssertionError(f"unexpected strncat count: {arg3:#x}")
                dst_scan = self._heap_bytes(arg1, len(repl.STRNCAT_EXPECTED_DST_BYTES) + repl.STRNCAT_CANARY_LEN)
                dst_nul = dst_scan.find(b"\x00")
                if dst_nul < 0:
                    raise AssertionError("strncat destination is not NUL-terminated in scan window")
                src_scan = self._heap_bytes(arg2, len(repl.STRNCAT_SRC_BYTES) + repl.STRNCAT_CANARY_LEN)
                copy_bytes = src_scan[:arg3]
                src_nul = copy_bytes.find(b"\x00")
                if src_nul >= 0:
                    payload = copy_bytes[:src_nul + 1]
                else:
                    payload = copy_bytes + b"\x00"
                self._set_heap_bytes(arg1 + dst_nul, payload)
                lines.append(f"A90R{arg1:x}")
            elif arg0 == strlcat:
                if arg1 not in self.allocated:
                    raise AssertionError(f"strlcat dst is not an allocated pointer: {arg1:#x}")
                if arg2 not in self.allocated:
                    raise AssertionError(f"strlcat src is not an allocated pointer: {arg2:#x}")
                if arg3 != repl.STRLCAT_PROOF_SIZE:
                    raise AssertionError(f"unexpected strlcat size: {arg3:#x}")
                dst_scan = self._heap_bytes(arg1, len(repl.STRLCAT_EXPECTED_DST_BYTES) + repl.STRLCAT_CANARY_LEN)
                dst_nul = dst_scan.find(b"\x00")
                if dst_nul < 0:
                    raise AssertionError("strlcat destination is not NUL-terminated in scan window")
                if dst_nul >= arg3:
                    raise AssertionError("strlcat proof would hit fortified dlen >= size path")
                src_scan = self._heap_bytes(arg2, len(repl.STRLCAT_SRC_BYTES) + repl.STRLCAT_CANARY_LEN)
                src_nul = src_scan.find(b"\x00")
                if src_nul < 0:
                    raise AssertionError("strlcat source is not NUL-terminated in scan window")
                copy_len = min(src_nul, arg3 - dst_nul - 1)
                self._set_heap_bytes(arg1 + dst_nul, src_scan[:copy_len] + b"\x00")
                lines.append(f"A90R{dst_nul + src_nul:x}")
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
            elif arg0 == memchr:
                if arg1 not in self.allocated:
                    raise AssertionError(f"memchr buffer is not an allocated pointer: {arg1:#x}")
                data = self._heap_bytes(arg1, arg3)
                search = arg2 & 0xFF
                offset = data.find(bytes([search]))
                lines.append("A90R0" if offset < 0 else f"A90R{arg1 + offset:x}")
            elif arg0 == memchr_inv:
                if arg1 not in self.allocated:
                    raise AssertionError(f"memchr_inv buffer is not an allocated pointer: {arg1:#x}")
                data = self._heap_bytes(arg1, arg3)
                fill = arg2 & 0xFF
                offset = -1
                for index, byte in enumerate(data):
                    if byte != fill:
                        offset = index
                        break
                lines.append("A90R0" if offset < 0 else f"A90R{arg1 + offset:x}")
            elif arg0 == memcpy:
                if arg1 not in self.allocated:
                    raise AssertionError(f"memcpy dst is not an allocated pointer: {arg1:#x}")
                if arg2 not in self.allocated:
                    raise AssertionError(f"memcpy src is not an allocated pointer: {arg2:#x}")
                if arg3 != repl.MEMCPY_PROOF_SIZE:
                    raise AssertionError(f"unexpected memcpy size: {arg3:#x}")
                self._set_heap_bytes(arg1, self._heap_bytes(arg2, arg3))
                lines.append(f"A90R{arg1:x}")
            elif arg0 == memmove:
                dst_base = self._allocated_base_for(arg1, arg3)
                src_base = self._allocated_base_for(arg2, arg3)
                if dst_base is None:
                    raise AssertionError(f"memmove dst range is not allocated: {arg1:#x}/len={arg3:#x}")
                if src_base is None:
                    raise AssertionError(f"memmove src range is not allocated: {arg2:#x}/len={arg3:#x}")
                if dst_base != src_base:
                    raise AssertionError("memmove proof expects dst/src in the same owned allocation")
                if arg1 != dst_base + repl.MEMMOVE_DST_OFFSET or arg2 != dst_base:
                    raise AssertionError(f"unexpected memmove offsets: dst={arg1 - dst_base:#x} src={arg2 - dst_base:#x}")
                if arg3 != repl.MEMMOVE_PROOF_SIZE:
                    raise AssertionError(f"unexpected memmove size: {arg3:#x}")
                self._set_heap_bytes(arg1, self._heap_bytes(arg2, arg3))
                lines.append(f"A90R{arg1:x}")
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
            elif arg0 == memset:
                if arg1 not in self.allocated:
                    raise AssertionError(f"memset dst is not an allocated pointer: {arg1:#x}")
                if arg3 != repl.MEMSET_PROOF_SIZE:
                    raise AssertionError(f"unexpected memset size: {arg3:#x}")
                self._set_heap_bytes(arg1, bytes([arg2 & 0xFF]) * arg3)
                lines.append(f"A90R{arg1:x}")
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

    def test_call_proof_hex_to_bin_passes_with_scalar_contract(self) -> None:
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
            "hex_to_bin",
            source_root=KERNEL_SOURCE_ROOT,
        )

        self.assertTrue(summary["ok"], summary)
        self.assertEqual(summary["decision"], "a90-repl-live-call-proof-hex_to_bin-pass")
        self.assertEqual(summary["proof_status"], "trusted-under-scalar-input-contract")
        self.assertEqual(summary["function_map_entry"]["symbol"], "hex_to_bin")
        self.assertEqual(summary["function_map_entry"]["status"], "live-proven")
        self.assertEqual(summary["source_evidence"]["signature"], "extern int hex_to_bin(char ch)")
        self.assertEqual(summary["source_evidence"]["pointer_arg_indices"], [])
        self.assertEqual(summary["invalid_expected_return_value"], "0xffffffff")
        cases = {case["case"]: case for case in summary["case_results"]}
        self.assertEqual(cases["digit-zero"]["observed_return_value"], "0x0")
        self.assertEqual(cases["digit-nine"]["observed_return_value"], "0x9")
        self.assertEqual(cases["lower-a"]["observed_return_value"], "0xa")
        self.assertEqual(cases["upper-a"]["observed_return_value"], "0xa")
        self.assertEqual(cases["lower-f"]["observed_return_value"], "0xf")
        self.assertEqual(cases["upper-f"]["observed_return_value"], "0xf")
        self.assertEqual(cases["invalid-g"]["observed_return_value"], "0xffffffff")
        self.assertTrue(summary["raw_runtime_values_redacted"])
        self.assertNotIn("hex_to_bin_runtime", summary)
        self.assertIn("hex_to_bin_runtime", private)
        self.assertEqual(private["case_returns"]["invalid-g"], "0xffffffff")
        self.assertEqual(fake.op_count, 8)  # slide + 7 scalar case calls

    def test_call_proof_hex2bin_passes_with_owned_buffer_contract(self) -> None:
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
            "hex2bin",
            source_root=KERNEL_SOURCE_ROOT,
        )

        self.assertTrue(summary["ok"], summary)
        self.assertEqual(summary["decision"], "a90-repl-live-call-proof-hex2bin-pass")
        self.assertEqual(summary["proof_status"], "trusted-under-owned-input-contract")
        self.assertEqual(summary["function_map_entry"]["symbol"], "hex2bin")
        self.assertEqual(summary["function_map_entry"]["status"], "live-proven")
        self.assertEqual(
            summary["source_evidence"]["signature"],
            "extern int __must_check hex2bin(u8 *dst, const char *src, size_t count)",
        )
        self.assertEqual(summary["source_evidence"]["pointer_arg_indices"], [0, 1])
        self.assertEqual(summary["source_ascii"], repl.HEX2BIN_SOURCE_LABEL)
        self.assertEqual(summary["count"], repl.HEX2BIN_COUNT)
        self.assertEqual(summary["expected_output_hex"], repl.HEX2BIN_EXPECTED_BYTES.hex())
        self.assertEqual(summary["observed_output_hex"], repl.HEX2BIN_EXPECTED_BYTES.hex())
        self.assertEqual(summary["observed_return_value"], "0x0")
        self.assertTrue(summary["destination_canary_preserved"])
        self.assertTrue(summary["source_unchanged_after_call"])
        self.assertTrue(summary["raw_runtime_values_redacted"])
        self.assertTrue(summary["owned_pointer_redacted"])
        self.assertTrue(summary["observed_bytes_redacted"])
        self.assertNotIn("hex2bin_runtime", summary)
        self.assertNotIn("dst_ptr", summary)
        self.assertNotIn("src_ptr", summary)
        self.assertIn("hex2bin_runtime", private)
        self.assertIn("dst_ptr", private)
        self.assertIn("src_ptr", private)
        self.assertEqual(
            private["dst_after_hex"],
            (repl.HEX2BIN_EXPECTED_BYTES + (b"\xcc" * repl.HEX2BIN_DST_CANARY_LEN)).hex(),
        )
        self.assertEqual(
            private["src_after_hex"],
            (repl.HEX2BIN_SOURCE_BYTES + (b"\xcc" * repl.HEX2BIN_SRC_CANARY_LEN)).hex(),
        )
        self.assertEqual(fake.freed, [fake.heap_ptr, fake.heap_ptr + 0x1000])

    def test_call_proof_bin2hex_passes_with_owned_buffer_contract(self) -> None:
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
            "bin2hex",
            source_root=KERNEL_SOURCE_ROOT,
        )

        self.assertTrue(summary["ok"], summary)
        self.assertEqual(summary["decision"], "a90-repl-live-call-proof-bin2hex-pass")
        self.assertEqual(summary["proof_status"], "trusted-under-owned-input-contract")
        self.assertEqual(summary["function_map_entry"]["symbol"], "bin2hex")
        self.assertEqual(summary["function_map_entry"]["status"], "live-proven")
        self.assertEqual(
            summary["source_evidence"]["signature"],
            "extern char * bin2hex(char *dst, const void *src, size_t count)",
        )
        self.assertEqual(summary["source_evidence"]["pointer_arg_indices"], [0, 1])
        self.assertEqual(summary["source_hex"], repl.BIN2HEX_SOURCE_BYTES.hex())
        self.assertEqual(summary["count"], repl.BIN2HEX_COUNT)
        self.assertEqual(summary["expected_output_ascii"], repl.BIN2HEX_EXPECTED_LABEL)
        self.assertEqual(summary["observed_output_ascii"], repl.BIN2HEX_EXPECTED_LABEL)
        self.assertEqual(summary["expected_return_offset"], len(repl.BIN2HEX_EXPECTED_BYTES))
        self.assertTrue(summary["returned_owned_destination_pointer_plus_offset"])
        self.assertTrue(summary["destination_canary_preserved"])
        self.assertTrue(summary["source_unchanged_after_call"])
        self.assertTrue(summary["raw_runtime_values_redacted"])
        self.assertTrue(summary["owned_pointer_redacted"])
        self.assertTrue(summary["observed_bytes_redacted"])
        self.assertNotIn("bin2hex_runtime", summary)
        self.assertNotIn("dst_ptr", summary)
        self.assertNotIn("src_ptr", summary)
        self.assertNotIn("return_ptr", summary)
        self.assertIn("bin2hex_runtime", private)
        self.assertIn("dst_ptr", private)
        self.assertIn("src_ptr", private)
        self.assertIn("return_ptr", private)
        self.assertEqual(
            private["dst_after_hex"],
            (repl.BIN2HEX_EXPECTED_BYTES + (b"\xcc" * repl.BIN2HEX_DST_CANARY_LEN)).hex(),
        )
        self.assertEqual(
            private["src_after_hex"],
            (repl.BIN2HEX_SOURCE_BYTES + (b"\xcc" * repl.BIN2HEX_SRC_CANARY_LEN)).hex(),
        )
        self.assertEqual(fake.freed, [fake.heap_ptr, fake.heap_ptr + 0x1000])

    def test_call_proof_parse_option_str_passes_with_owned_string_contract(self) -> None:
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
            "parse_option_str",
            source_root=KERNEL_SOURCE_ROOT,
        )

        self.assertTrue(summary["ok"], summary)
        self.assertEqual(summary["decision"], "a90-repl-live-call-proof-parse_option_str-pass")
        self.assertEqual(summary["proof_status"], "trusted-under-owned-input-contract")
        self.assertEqual(summary["function_map_entry"]["symbol"], "parse_option_str")
        self.assertEqual(summary["function_map_entry"]["status"], "live-proven")
        self.assertEqual(
            summary["source_evidence"]["signature"],
            "extern bool parse_option_str(const char *str, const char *option)",
        )
        self.assertEqual(summary["source_evidence"]["pointer_arg_indices"], [0, 1])
        self.assertEqual(summary["option"], repl.PARSE_OPTION_STR_OPTION_LABEL)
        cases = summary["cases"]
        self.assertEqual(cases["exact-token-hit"]["observed_return"], 1)
        self.assertEqual(cases["prefix-token-miss"]["observed_return"], 0)
        self.assertEqual(cases["missing-token"]["observed_return"], 0)
        for case in cases.values():
            self.assertTrue(case["ok"])
            self.assertTrue(case["return_ok"])
            self.assertTrue(case["list_unchanged"])
            self.assertTrue(case["option_unchanged"])
        self.assertTrue(summary["raw_runtime_values_redacted"])
        self.assertTrue(summary["owned_pointer_redacted"])
        self.assertTrue(summary["observed_bytes_redacted"])
        self.assertNotIn("parse_option_str_runtime", summary)
        self.assertNotIn("list_ptr", summary)
        self.assertNotIn("option_ptr", summary)
        self.assertIn("parse_option_str_runtime", private)
        self.assertIn("list_ptr", private)
        self.assertIn("option_ptr", private)
        self.assertEqual(private["case_returns"]["exact-token-hit"], "0x1")
        self.assertEqual(private["case_returns"]["prefix-token-miss"], "0x0")
        self.assertEqual(private["case_returns"]["missing-token"], "0x0")
        self.assertEqual(
            private["option_after_hex"],
            (repl.PARSE_OPTION_STR_OPTION_BYTES + (b"\xcc" * repl.PARSE_OPTION_STR_CANARY_LEN)).hex(),
        )
        self.assertEqual(fake.freed, [fake.heap_ptr, fake.heap_ptr + 0x1000])

    def test_call_proof_strsep_passes_with_owned_slot_string_and_delimiter_contract(self) -> None:
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
            "strsep",
            source_root=KERNEL_SOURCE_ROOT,
        )

        self.assertTrue(summary["ok"], summary)
        self.assertEqual(summary["decision"], "a90-repl-live-call-proof-strsep-pass")
        self.assertEqual(summary["proof_status"], "trusted-under-owned-input-contract")
        self.assertEqual(summary["function_map_entry"]["symbol"], "strsep")
        self.assertEqual(summary["function_map_entry"]["status"], "live-proven")
        self.assertEqual(summary["source_evidence"]["signature"], "extern char * strsep(char **,const char *)")
        self.assertEqual(summary["source_evidence"]["pointer_arg_indices"], [0, 1])
        self.assertEqual(summary["input_ascii"], repl.STRSEP_STRING_LABEL)
        self.assertEqual(summary["delimiter_ascii"], repl.STRSEP_DELIM_LABEL)
        self.assertEqual(summary["expected_return_offset"], 0)
        self.assertEqual(summary["observed_return_offset"], 0)
        self.assertEqual(summary["expected_delimiter_offset"], repl.STRSEP_EXPECTED_DELIM_OFFSET)
        self.assertEqual(summary["expected_next_offset"], repl.STRSEP_EXPECTED_NEXT_OFFSET)
        self.assertTrue(summary["slot_updated_to_expected_next_offset"])
        self.assertTrue(summary["delimiter_replaced_with_nul"])
        self.assertTrue(summary["string_after_matches_expected"])
        self.assertTrue(summary["delimiter_unchanged_after_call"])
        self.assertTrue(summary["slot_canary_preserved"])
        self.assertTrue(summary["string_canary_preserved"])
        self.assertTrue(summary["delimiter_canary_preserved"])
        self.assertTrue(summary["raw_runtime_values_redacted"])
        self.assertTrue(summary["owned_pointer_redacted"])
        self.assertTrue(summary["observed_bytes_redacted"])
        self.assertNotIn("strsep_runtime", summary)
        self.assertNotIn("slot_ptr", summary)
        self.assertNotIn("string_ptr", summary)
        self.assertNotIn("delim_ptr", summary)
        self.assertIn("strsep_runtime", private)
        self.assertIn("slot_ptr", private)
        self.assertIn("string_ptr", private)
        self.assertIn("delim_ptr", private)
        self.assertEqual(private["slot_after_hex"], private["expected_slot_after_hex"])
        self.assertEqual(private["string_after_hex"], private["expected_string_after_hex"])
        self.assertEqual(
            private["delim_after_hex"],
            (repl.STRSEP_DELIM_BYTES + (b"\xcc" * repl.STRSEP_CANARY_LEN)).hex(),
        )
        self.assertEqual(fake.freed, [fake.heap_ptr, fake.heap_ptr + 0x1000, fake.heap_ptr + 0x2000])

    def test_call_proof_simple_strtoull_passes_with_owned_string_and_endp_contract(self) -> None:
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
            "simple_strtoull",
            source_root=KERNEL_SOURCE_ROOT,
        )

        self.assertTrue(summary["ok"], summary)
        self.assertEqual(summary["decision"], "a90-repl-live-call-proof-simple_strtoull-pass")
        self.assertEqual(summary["proof_status"], "trusted-under-owned-input-contract")
        self.assertEqual(summary["function_map_entry"]["symbol"], "simple_strtoull")
        self.assertEqual(summary["function_map_entry"]["status"], "live-proven")
        self.assertEqual(
            summary["source_evidence"]["signature"],
            "extern unsigned long long simple_strtoull(const char *,char **,unsigned int)",
        )
        self.assertEqual(summary["source_evidence"]["pointer_arg_indices"], [0, 1])
        self.assertEqual(summary["input_ascii"], repl.SIMPLE_STRTOULL_INPUT_LABEL)
        self.assertEqual(summary["base"], repl.SIMPLE_STRTOULL_BASE)
        self.assertEqual(summary["expected_return_hex"], "0x1234abcd")
        self.assertEqual(summary["observed_return_hex"], "0x1234abcd")
        self.assertEqual(summary["expected_end_offset"], repl.SIMPLE_STRTOULL_EXPECTED_END_OFFSET)
        self.assertTrue(summary["returned_owned_input_pointer_plus_offset"])
        self.assertTrue(summary["input_unchanged_after_call"])
        self.assertTrue(summary["end_slot_canary_preserved"])
        self.assertTrue(summary["raw_runtime_values_redacted"])
        self.assertTrue(summary["owned_pointer_redacted"])
        self.assertTrue(summary["observed_bytes_redacted"])
        self.assertNotIn("simple_strtoull_runtime", summary)
        self.assertNotIn("input_ptr", summary)
        self.assertNotIn("end_slot_ptr", summary)
        self.assertNotIn("observed_end_pointer", summary)
        self.assertNotIn("expected_end_pointer", summary)
        self.assertIn("simple_strtoull_runtime", private)
        self.assertIn("input_ptr", private)
        self.assertIn("end_slot_ptr", private)
        self.assertIn("observed_end_pointer", private)
        self.assertIn("expected_end_pointer", private)
        self.assertEqual(
            private["input_after_hex"],
            (repl.SIMPLE_STRTOULL_INPUT_BYTES + (b"\xcc" * repl.SIMPLE_STRTOULL_CANARY_LEN)).hex(),
        )
        self.assertTrue(
            private["end_slot_after_hex"].endswith(
                repl.SIMPLE_STRTOULL_END_SLOT_CANARY.to_bytes(8, "little").hex()
            )
        )
        self.assertEqual(fake.freed, [fake.heap_ptr, fake.heap_ptr + 0x1000])

    def test_call_proof_kstrtoull_passes_with_owned_string_and_ull_result_slot_contract(self) -> None:
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
            "kstrtoull",
            source_root=KERNEL_SOURCE_ROOT,
        )

        self.assertTrue(summary["ok"], summary)
        self.assertEqual(summary["decision"], "a90-repl-live-call-proof-kstrtoull-pass")
        self.assertEqual(summary["proof_status"], "trusted-under-owned-input-contract")
        self.assertEqual(summary["function_map_entry"]["symbol"], "kstrtoull")
        self.assertEqual(summary["function_map_entry"]["status"], "live-proven")
        self.assertEqual(
            summary["source_evidence"]["signature"],
            "int __must_check kstrtoull(const char *s, unsigned int base, unsigned long long *res)",
        )
        self.assertEqual(summary["source_evidence"]["pointer_arg_indices"], [0, 2])
        self.assertEqual(summary["input_ascii"], repl.KSTRTOULL_INPUT_LABEL)
        self.assertEqual(summary["base"], repl.KSTRTOULL_BASE)
        self.assertEqual(summary["expected_return"], 0)
        self.assertEqual(summary["observed_return"], 0)
        self.assertEqual(summary["expected_result"], repl.KSTRTOULL_EXPECTED_VALUE)
        self.assertEqual(summary["observed_result"], repl.KSTRTOULL_EXPECTED_VALUE)
        self.assertEqual(summary["expected_result_hex"], "0x1234567890abcdef")
        self.assertEqual(summary["observed_result_hex"], "0x1234567890abcdef")
        self.assertTrue(summary["input_unchanged_after_call"])
        self.assertTrue(summary["result_slot_canary_preserved"])
        self.assertTrue(summary["raw_runtime_values_redacted"])
        self.assertTrue(summary["owned_pointer_redacted"])
        self.assertTrue(summary["observed_bytes_redacted"])
        self.assertNotIn("kstrtoull_runtime", summary)
        self.assertNotIn("input_ptr", summary)
        self.assertNotIn("result_slot_ptr", summary)
        self.assertIn("kstrtoull_runtime", private)
        self.assertIn("input_ptr", private)
        self.assertIn("result_slot_ptr", private)
        self.assertEqual(
            private["input_after_hex"],
            (repl.KSTRTOULL_INPUT_BYTES + (b"\xcc" * repl.KSTRTOULL_CANARY_LEN)).hex(),
        )
        self.assertEqual(
            private["result_slot_after_hex"],
            (
                repl.KSTRTOULL_EXPECTED_VALUE.to_bytes(8, "little")
                + (b"\xcc" * repl.KSTRTOULL_RESULT_SLOT_CANARY_LEN)
            ).hex(),
        )
        self.assertEqual(private["result_slot_after_hex"], private["expected_result_slot_after_hex"])
        self.assertEqual(fake.freed, [fake.heap_ptr, fake.heap_ptr + 0x1000])

    def test_call_proof_kstrtoll_passes_with_owned_signed_string_and_ll_result_slot_contract(self) -> None:
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
            "kstrtoll",
            source_root=KERNEL_SOURCE_ROOT,
        )

        self.assertTrue(summary["ok"], summary)
        self.assertEqual(summary["decision"], "a90-repl-live-call-proof-kstrtoll-pass")
        self.assertEqual(summary["proof_status"], "trusted-under-owned-input-contract")
        self.assertEqual(summary["function_map_entry"]["symbol"], "kstrtoll")
        self.assertEqual(summary["function_map_entry"]["status"], "live-proven")
        self.assertEqual(
            summary["source_evidence"]["signature"],
            "int __must_check kstrtoll(const char *s, unsigned int base, long long *res)",
        )
        self.assertEqual(summary["source_evidence"]["pointer_arg_indices"], [0, 2])
        self.assertEqual(summary["input_ascii"], repl.KSTRTOLL_INPUT_LABEL)
        self.assertEqual(summary["base"], repl.KSTRTOLL_BASE)
        self.assertEqual(summary["expected_return"], 0)
        self.assertEqual(summary["observed_return"], 0)
        self.assertEqual(summary["expected_result"], repl.KSTRTOLL_EXPECTED_VALUE)
        self.assertEqual(summary["observed_result"], repl.KSTRTOLL_EXPECTED_VALUE)
        self.assertEqual(summary["expected_result_raw_hex"], "0xedcba9876f543211")
        self.assertEqual(summary["observed_result_raw_hex"], "0xedcba9876f543211")
        self.assertTrue(summary["input_unchanged_after_call"])
        self.assertTrue(summary["result_slot_canary_preserved"])
        self.assertTrue(summary["raw_runtime_values_redacted"])
        self.assertTrue(summary["owned_pointer_redacted"])
        self.assertTrue(summary["observed_bytes_redacted"])
        self.assertNotIn("kstrtoll_runtime", summary)
        self.assertNotIn("input_ptr", summary)
        self.assertNotIn("result_slot_ptr", summary)
        self.assertIn("kstrtoll_runtime", private)
        self.assertIn("input_ptr", private)
        self.assertIn("result_slot_ptr", private)
        self.assertEqual(
            private["input_after_hex"],
            (repl.KSTRTOLL_INPUT_BYTES + (b"\xcc" * repl.KSTRTOLL_CANARY_LEN)).hex(),
        )
        self.assertEqual(
            private["result_slot_after_hex"],
            (
                repl.KSTRTOLL_EXPECTED_RAW_U64.to_bytes(8, "little")
                + (b"\xcc" * repl.KSTRTOLL_RESULT_SLOT_CANARY_LEN)
            ).hex(),
        )
        self.assertEqual(private["result_slot_after_hex"], private["expected_result_slot_after_hex"])
        self.assertEqual(fake.freed, [fake.heap_ptr, fake.heap_ptr + 0x1000])

    def test_call_proof_kstrtouint_passes_with_owned_string_and_result_slot_contract(self) -> None:
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
            "kstrtouint",
            source_root=KERNEL_SOURCE_ROOT,
        )

        self.assertTrue(summary["ok"], summary)
        self.assertEqual(summary["decision"], "a90-repl-live-call-proof-kstrtouint-pass")
        self.assertEqual(summary["proof_status"], "trusted-under-owned-input-contract")
        self.assertEqual(summary["function_map_entry"]["symbol"], "kstrtouint")
        self.assertEqual(summary["function_map_entry"]["status"], "live-proven")
        self.assertEqual(
            summary["source_evidence"]["signature"],
            "int __must_check kstrtouint(const char *s, unsigned int base, unsigned int *res)",
        )
        self.assertEqual(summary["source_evidence"]["pointer_arg_indices"], [0, 2])
        self.assertEqual(summary["input_ascii"], repl.KSTRTOUINT_INPUT_LABEL)
        self.assertEqual(summary["base"], repl.KSTRTOUINT_BASE)
        self.assertEqual(summary["expected_return"], 0)
        self.assertEqual(summary["observed_return"], 0)
        self.assertEqual(summary["expected_result"], repl.KSTRTOUINT_EXPECTED_VALUE)
        self.assertEqual(summary["observed_result"], repl.KSTRTOUINT_EXPECTED_VALUE)
        self.assertEqual(summary["expected_result_hex"], "0x75bcd15")
        self.assertEqual(summary["observed_result_hex"], "0x75bcd15")
        self.assertTrue(summary["input_unchanged_after_call"])
        self.assertTrue(summary["result_slot_canary_preserved"])
        self.assertTrue(summary["raw_runtime_values_redacted"])
        self.assertTrue(summary["owned_pointer_redacted"])
        self.assertTrue(summary["observed_bytes_redacted"])
        self.assertNotIn("kstrtouint_runtime", summary)
        self.assertNotIn("input_ptr", summary)
        self.assertNotIn("result_slot_ptr", summary)
        self.assertIn("kstrtouint_runtime", private)
        self.assertIn("input_ptr", private)
        self.assertIn("result_slot_ptr", private)
        self.assertEqual(
            private["input_after_hex"],
            (repl.KSTRTOUINT_INPUT_BYTES + (b"\xcc" * repl.KSTRTOUINT_CANARY_LEN)).hex(),
        )
        self.assertEqual(
            private["result_slot_after_hex"],
            (
                repl.KSTRTOUINT_EXPECTED_VALUE.to_bytes(4, "little")
                + (b"\xcc" * repl.KSTRTOUINT_RESULT_SLOT_CANARY_LEN)
            ).hex(),
        )
        self.assertEqual(private["result_slot_after_hex"], private["expected_result_slot_after_hex"])
        self.assertEqual(fake.freed, [fake.heap_ptr, fake.heap_ptr + 0x1000])

    def test_call_proof_kstrtou16_passes_with_owned_string_and_u16_result_slot_contract(self) -> None:
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
            "kstrtou16",
            source_root=KERNEL_SOURCE_ROOT,
        )

        self.assertTrue(summary["ok"], summary)
        self.assertEqual(summary["decision"], "a90-repl-live-call-proof-kstrtou16-pass")
        self.assertEqual(summary["proof_status"], "trusted-under-owned-input-contract")
        self.assertEqual(summary["function_map_entry"]["symbol"], "kstrtou16")
        self.assertEqual(summary["function_map_entry"]["status"], "live-proven")
        self.assertEqual(
            summary["source_evidence"]["signature"],
            "int __must_check kstrtou16(const char *s, unsigned int base, u16 *res)",
        )
        self.assertEqual(summary["source_evidence"]["pointer_arg_indices"], [0, 2])
        self.assertEqual(summary["input_ascii"], repl.KSTRTOU16_INPUT_LABEL)
        self.assertEqual(summary["base"], repl.KSTRTOU16_BASE)
        self.assertEqual(summary["expected_return"], 0)
        self.assertEqual(summary["observed_return"], 0)
        self.assertEqual(summary["expected_result"], repl.KSTRTOU16_EXPECTED_VALUE)
        self.assertEqual(summary["observed_result"], repl.KSTRTOU16_EXPECTED_VALUE)
        self.assertEqual(summary["expected_result_raw_hex"], "0xd431")
        self.assertEqual(summary["observed_result_raw_hex"], "0xd431")
        self.assertTrue(summary["input_unchanged_after_call"])
        self.assertTrue(summary["result_slot_canary_preserved"])
        self.assertTrue(summary["raw_runtime_values_redacted"])
        self.assertTrue(summary["owned_pointer_redacted"])
        self.assertTrue(summary["observed_bytes_redacted"])
        self.assertNotIn("kstrtou16_runtime", summary)
        self.assertNotIn("input_ptr", summary)
        self.assertNotIn("result_slot_ptr", summary)
        self.assertIn("kstrtou16_runtime", private)
        self.assertIn("input_ptr", private)
        self.assertIn("result_slot_ptr", private)
        self.assertEqual(
            private["input_after_hex"],
            (repl.KSTRTOU16_INPUT_BYTES + (b"\xcc" * repl.KSTRTOU16_CANARY_LEN)).hex(),
        )
        self.assertEqual(
            private["result_slot_after_hex"],
            (
                repl.KSTRTOU16_EXPECTED_RAW_U16.to_bytes(2, "little")
                + (b"\xcc" * repl.KSTRTOU16_RESULT_SLOT_CANARY_LEN)
            ).hex(),
        )
        self.assertEqual(private["result_slot_after_hex"], private["expected_result_slot_after_hex"])
        self.assertEqual(fake.freed, [fake.heap_ptr, fake.heap_ptr + 0x1000])

    def test_call_proof_kstrtou8_passes_with_owned_string_and_u8_result_slot_contract(self) -> None:
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
            "kstrtou8",
            source_root=KERNEL_SOURCE_ROOT,
        )

        self.assertTrue(summary["ok"], summary)
        self.assertEqual(summary["decision"], "a90-repl-live-call-proof-kstrtou8-pass")
        self.assertEqual(summary["proof_status"], "trusted-under-owned-input-contract")
        self.assertEqual(summary["function_map_entry"]["symbol"], "kstrtou8")
        self.assertEqual(summary["function_map_entry"]["status"], "live-proven")
        self.assertEqual(
            summary["source_evidence"]["signature"],
            "int __must_check kstrtou8(const char *s, unsigned int base, u8 *res)",
        )
        self.assertEqual(summary["source_evidence"]["pointer_arg_indices"], [0, 2])
        self.assertEqual(summary["input_ascii"], repl.KSTRTOU8_INPUT_LABEL)
        self.assertEqual(summary["base"], repl.KSTRTOU8_BASE)
        self.assertEqual(summary["expected_return"], 0)
        self.assertEqual(summary["observed_return"], 0)
        self.assertEqual(summary["expected_result"], repl.KSTRTOU8_EXPECTED_VALUE)
        self.assertEqual(summary["observed_result"], repl.KSTRTOU8_EXPECTED_VALUE)
        self.assertEqual(summary["expected_result_raw_hex"], "0xd5")
        self.assertEqual(summary["observed_result_raw_hex"], "0xd5")
        self.assertTrue(summary["input_unchanged_after_call"])
        self.assertTrue(summary["result_slot_canary_preserved"])
        self.assertTrue(summary["raw_runtime_values_redacted"])
        self.assertTrue(summary["owned_pointer_redacted"])
        self.assertTrue(summary["observed_bytes_redacted"])
        self.assertNotIn("kstrtou8_runtime", summary)
        self.assertNotIn("input_ptr", summary)
        self.assertNotIn("result_slot_ptr", summary)
        self.assertIn("kstrtou8_runtime", private)
        self.assertIn("input_ptr", private)
        self.assertIn("result_slot_ptr", private)
        self.assertEqual(
            private["input_after_hex"],
            (repl.KSTRTOU8_INPUT_BYTES + (b"\xcc" * repl.KSTRTOU8_CANARY_LEN)).hex(),
        )
        self.assertEqual(
            private["result_slot_after_hex"],
            (
                repl.KSTRTOU8_EXPECTED_RAW_U8.to_bytes(1, "little")
                + (b"\xcc" * repl.KSTRTOU8_RESULT_SLOT_CANARY_LEN)
            ).hex(),
        )
        self.assertEqual(private["result_slot_after_hex"], private["expected_result_slot_after_hex"])
        self.assertEqual(fake.freed, [fake.heap_ptr, fake.heap_ptr + 0x1000])

    def test_call_proof_kstrtos8_passes_with_owned_signed_string_and_s8_result_slot_contract(self) -> None:
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
            "kstrtos8",
            source_root=KERNEL_SOURCE_ROOT,
        )

        self.assertTrue(summary["ok"], summary)
        self.assertEqual(summary["decision"], "a90-repl-live-call-proof-kstrtos8-pass")
        self.assertEqual(summary["proof_status"], "trusted-under-owned-input-contract")
        self.assertEqual(summary["function_map_entry"]["symbol"], "kstrtos8")
        self.assertEqual(summary["function_map_entry"]["status"], "live-proven")
        self.assertEqual(
            summary["source_evidence"]["signature"],
            "int __must_check kstrtos8(const char *s, unsigned int base, s8 *res)",
        )
        self.assertEqual(summary["source_evidence"]["pointer_arg_indices"], [0, 2])
        self.assertEqual(summary["input_ascii"], repl.KSTRTOS8_INPUT_LABEL)
        self.assertEqual(summary["base"], repl.KSTRTOS8_BASE)
        self.assertEqual(summary["expected_return"], 0)
        self.assertEqual(summary["observed_return"], 0)
        self.assertEqual(summary["expected_result"], repl.KSTRTOS8_EXPECTED_VALUE)
        self.assertEqual(summary["observed_result"], repl.KSTRTOS8_EXPECTED_VALUE)
        self.assertEqual(summary["expected_result_raw_hex"], "0xab")
        self.assertEqual(summary["observed_result_raw_hex"], "0xab")
        self.assertTrue(summary["input_unchanged_after_call"])
        self.assertTrue(summary["result_slot_canary_preserved"])
        self.assertTrue(summary["raw_runtime_values_redacted"])
        self.assertTrue(summary["owned_pointer_redacted"])
        self.assertTrue(summary["observed_bytes_redacted"])
        self.assertNotIn("kstrtos8_runtime", summary)
        self.assertNotIn("input_ptr", summary)
        self.assertNotIn("result_slot_ptr", summary)
        self.assertIn("kstrtos8_runtime", private)
        self.assertIn("input_ptr", private)
        self.assertIn("result_slot_ptr", private)
        self.assertEqual(
            private["input_after_hex"],
            (repl.KSTRTOS8_INPUT_BYTES + (b"\xcc" * repl.KSTRTOS8_CANARY_LEN)).hex(),
        )
        self.assertEqual(
            private["result_slot_after_hex"],
            (
                repl.KSTRTOS8_EXPECTED_RAW_U8.to_bytes(1, "little")
                + (b"\xcc" * repl.KSTRTOS8_RESULT_SLOT_CANARY_LEN)
            ).hex(),
        )
        self.assertEqual(private["result_slot_after_hex"], private["expected_result_slot_after_hex"])
        self.assertEqual(fake.freed, [fake.heap_ptr, fake.heap_ptr + 0x1000])

    def test_call_proof_kstrtobool_passes_with_owned_bool_string_and_result_slot_contract(self) -> None:
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
            "kstrtobool",
            source_root=KERNEL_SOURCE_ROOT,
        )

        self.assertTrue(summary["ok"], summary)
        self.assertEqual(summary["decision"], "a90-repl-live-call-proof-kstrtobool-pass")
        self.assertEqual(summary["proof_status"], "trusted-under-owned-input-contract")
        self.assertEqual(summary["function_map_entry"]["symbol"], "kstrtobool")
        self.assertEqual(summary["function_map_entry"]["status"], "live-proven")
        self.assertEqual(
            summary["source_evidence"]["signature"],
            "int __must_check kstrtobool(const char *s, bool *res)",
        )
        self.assertEqual(summary["source_evidence"]["pointer_arg_indices"], [0, 1])
        self.assertEqual(summary["input_ascii"], repl.KSTRTOBOOL_INPUT_LABEL)
        self.assertEqual(summary["expected_return"], 0)
        self.assertEqual(summary["observed_return"], 0)
        self.assertIs(summary["expected_result"], True)
        self.assertIs(summary["observed_result"], True)
        self.assertEqual(summary["expected_result_raw_hex"], "0x01")
        self.assertEqual(summary["observed_result_raw_hex"], "0x01")
        self.assertTrue(summary["input_unchanged_after_call"])
        self.assertTrue(summary["result_slot_canary_preserved"])
        self.assertTrue(summary["raw_runtime_values_redacted"])
        self.assertTrue(summary["owned_pointer_redacted"])
        self.assertTrue(summary["observed_bytes_redacted"])
        self.assertNotIn("kstrtobool_runtime", summary)
        self.assertNotIn("input_ptr", summary)
        self.assertNotIn("result_slot_ptr", summary)
        self.assertIn("kstrtobool_runtime", private)
        self.assertIn("input_ptr", private)
        self.assertIn("result_slot_ptr", private)
        self.assertEqual(
            private["input_after_hex"],
            (repl.KSTRTOBOOL_INPUT_BYTES + (b"\xcc" * repl.KSTRTOBOOL_CANARY_LEN)).hex(),
        )
        self.assertEqual(
            private["result_slot_after_hex"],
            (
                repl.KSTRTOBOOL_EXPECTED_RAW_U8.to_bytes(1, "little")
                + (b"\xcc" * repl.KSTRTOBOOL_RESULT_SLOT_CANARY_LEN)
            ).hex(),
        )
        self.assertEqual(private["result_slot_after_hex"], private["expected_result_slot_after_hex"])
        self.assertEqual(fake.freed, [fake.heap_ptr, fake.heap_ptr + 0x1000])

    def test_call_proof_kstrtoint_passes_with_owned_signed_string_and_result_slot_contract(self) -> None:
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
            "kstrtoint",
            source_root=KERNEL_SOURCE_ROOT,
        )

        self.assertTrue(summary["ok"], summary)
        self.assertEqual(summary["decision"], "a90-repl-live-call-proof-kstrtoint-pass")
        self.assertEqual(summary["proof_status"], "trusted-under-owned-input-contract")
        self.assertEqual(summary["function_map_entry"]["symbol"], "kstrtoint")
        self.assertEqual(summary["function_map_entry"]["status"], "live-proven")
        self.assertEqual(
            summary["source_evidence"]["signature"],
            "int __must_check kstrtoint(const char *s, unsigned int base, int *res)",
        )
        self.assertEqual(summary["source_evidence"]["pointer_arg_indices"], [0, 2])
        self.assertEqual(summary["input_ascii"], repl.KSTRTOINT_INPUT_LABEL)
        self.assertEqual(summary["base"], repl.KSTRTOINT_BASE)
        self.assertEqual(summary["expected_return"], 0)
        self.assertEqual(summary["observed_return"], 0)
        self.assertEqual(summary["expected_result"], repl.KSTRTOINT_EXPECTED_VALUE)
        self.assertEqual(summary["observed_result"], repl.KSTRTOINT_EXPECTED_VALUE)
        self.assertEqual(summary["expected_result_raw_hex"], "0xffffcfc7")
        self.assertEqual(summary["observed_result_raw_hex"], "0xffffcfc7")
        self.assertTrue(summary["input_unchanged_after_call"])
        self.assertTrue(summary["result_slot_canary_preserved"])
        self.assertTrue(summary["raw_runtime_values_redacted"])
        self.assertTrue(summary["owned_pointer_redacted"])
        self.assertTrue(summary["observed_bytes_redacted"])
        self.assertNotIn("kstrtoint_runtime", summary)
        self.assertNotIn("input_ptr", summary)
        self.assertNotIn("result_slot_ptr", summary)
        self.assertIn("kstrtoint_runtime", private)
        self.assertIn("input_ptr", private)
        self.assertIn("result_slot_ptr", private)
        self.assertEqual(
            private["input_after_hex"],
            (repl.KSTRTOINT_INPUT_BYTES + (b"\xcc" * repl.KSTRTOINT_CANARY_LEN)).hex(),
        )
        self.assertEqual(
            private["result_slot_after_hex"],
            (
                repl.KSTRTOINT_EXPECTED_RAW_U32.to_bytes(4, "little")
                + (b"\xcc" * repl.KSTRTOINT_RESULT_SLOT_CANARY_LEN)
            ).hex(),
        )
        self.assertEqual(private["result_slot_after_hex"], private["expected_result_slot_after_hex"])
        self.assertEqual(fake.freed, [fake.heap_ptr, fake.heap_ptr + 0x1000])

    def test_call_proof_kstrtos16_passes_with_owned_signed_string_and_s16_result_slot_contract(self) -> None:
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
            "kstrtos16",
            source_root=KERNEL_SOURCE_ROOT,
        )

        self.assertTrue(summary["ok"], summary)
        self.assertEqual(summary["decision"], "a90-repl-live-call-proof-kstrtos16-pass")
        self.assertEqual(summary["proof_status"], "trusted-under-owned-input-contract")
        self.assertEqual(summary["function_map_entry"]["symbol"], "kstrtos16")
        self.assertEqual(summary["function_map_entry"]["status"], "live-proven")
        self.assertEqual(
            summary["source_evidence"]["signature"],
            "int __must_check kstrtos16(const char *s, unsigned int base, s16 *res)",
        )
        self.assertEqual(summary["source_evidence"]["pointer_arg_indices"], [0, 2])
        self.assertEqual(summary["input_ascii"], repl.KSTRTOS16_INPUT_LABEL)
        self.assertEqual(summary["base"], repl.KSTRTOS16_BASE)
        self.assertEqual(summary["expected_return"], 0)
        self.assertEqual(summary["observed_return"], 0)
        self.assertEqual(summary["expected_result"], repl.KSTRTOS16_EXPECTED_VALUE)
        self.assertEqual(summary["observed_result"], repl.KSTRTOS16_EXPECTED_VALUE)
        self.assertEqual(summary["expected_result_raw_hex"], "0xfb2e")
        self.assertEqual(summary["observed_result_raw_hex"], "0xfb2e")
        self.assertTrue(summary["input_unchanged_after_call"])
        self.assertTrue(summary["result_slot_canary_preserved"])
        self.assertTrue(summary["raw_runtime_values_redacted"])
        self.assertTrue(summary["owned_pointer_redacted"])
        self.assertTrue(summary["observed_bytes_redacted"])
        self.assertNotIn("kstrtos16_runtime", summary)
        self.assertNotIn("input_ptr", summary)
        self.assertNotIn("result_slot_ptr", summary)
        self.assertIn("kstrtos16_runtime", private)
        self.assertIn("input_ptr", private)
        self.assertIn("result_slot_ptr", private)
        self.assertEqual(
            private["input_after_hex"],
            (repl.KSTRTOS16_INPUT_BYTES + (b"\xcc" * repl.KSTRTOS16_CANARY_LEN)).hex(),
        )
        self.assertEqual(
            private["result_slot_after_hex"],
            (
                repl.KSTRTOS16_EXPECTED_RAW_U16.to_bytes(2, "little")
                + (b"\xcc" * repl.KSTRTOS16_RESULT_SLOT_CANARY_LEN)
            ).hex(),
        )
        self.assertEqual(private["result_slot_after_hex"], private["expected_result_slot_after_hex"])
        self.assertEqual(fake.freed, [fake.heap_ptr, fake.heap_ptr + 0x1000])

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

    def test_call_proof_strnchr_passes_with_owned_string_contract(self) -> None:
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
            "strnchr",
            source_root=KERNEL_SOURCE_ROOT,
        )

        self.assertTrue(summary["ok"], summary)
        self.assertEqual(summary["decision"], "a90-repl-live-call-proof-strnchr-pass")
        self.assertEqual(summary["proof_status"], "trusted-under-owned-input-contract")
        self.assertEqual(summary["function_map_entry"]["symbol"], "strnchr")
        self.assertEqual(summary["function_map_entry"]["status"], "live-proven")
        self.assertEqual(
            summary["source_evidence"]["signature"],
            "extern char * strnchr(const char *, size_t, int)",
        )
        self.assertEqual(summary["proof_string"], repl.STRNCHR_PROOF_LABEL)
        self.assertEqual(summary["search_byte"], f"0x{repl.STRNCHR_SEARCH_BYTE:02x}")
        self.assertEqual(summary["hit_count"], repl.STRNCHR_HIT_COUNT)
        self.assertEqual(summary["expected_hit_offset"], repl.STRNCHR_EXPECTED_OFFSET)
        self.assertEqual(summary["hit_expected_return_value"], "owned-string-pointer-plus-offset-redacted")
        self.assertEqual(summary["hit_observed_return_value"], "owned-string-pointer-plus-offset-redacted")
        self.assertTrue(summary["hit_return_matches_expected_offset"])
        self.assertEqual(summary["boundary_miss_count"], repl.STRNCHR_BOUND_MISS_COUNT)
        self.assertEqual(summary["boundary_miss_expected_return_value"], "0x0")
        self.assertEqual(summary["boundary_miss_observed_return_value"], "0x0")
        self.assertTrue(summary["string_unchanged_after_calls"])
        self.assertTrue(summary["raw_runtime_values_redacted"])
        self.assertTrue(summary["owned_pointer_redacted"])
        self.assertTrue(summary["observed_bytes_redacted"])
        self.assertNotIn("alloc_ptr", summary)
        self.assertNotIn("hit_return_ptr", summary)
        self.assertNotIn("boundary_return_ptr", summary)
        self.assertEqual(private["alloc_ptr"], f"0x{fake.heap_ptr:x}")
        self.assertEqual(
            private["hit_return_ptr"],
            f"0x{fake.heap_ptr + repl.STRNCHR_EXPECTED_OFFSET:x}",
        )
        self.assertEqual(private["boundary_return_ptr"], "0x0")
        expected_hex = (
            repl.STRNCHR_PROOF_BYTES + (b"\xcc" * repl.STRNCHR_CANARY_LEN)
        ).hex()
        self.assertEqual(private["expected_bytes_hex"], expected_hex)
        self.assertEqual(private["observed_bytes_hex"], expected_hex)
        self.assertEqual(fake.freed, [fake.heap_ptr])

    def test_call_proof_skip_spaces_passes_with_owned_string_contract(self) -> None:
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
            "skip_spaces",
            source_root=KERNEL_SOURCE_ROOT,
        )

        payload_len = max(len(repl.SKIP_SPACES_PROOF_BYTES), len(repl.SKIP_SPACES_NO_LEADING_BYTES))
        expected_leading = repl.SKIP_SPACES_PROOF_BYTES.ljust(payload_len, b"\x00") + (
            b"\xcc" * repl.SKIP_SPACES_CANARY_LEN
        )
        expected_no_leading = repl.SKIP_SPACES_NO_LEADING_BYTES.ljust(payload_len, b"\x00") + (
            b"\xcc" * repl.SKIP_SPACES_CANARY_LEN
        )

        self.assertTrue(summary["ok"], summary)
        self.assertEqual(summary["decision"], "a90-repl-live-call-proof-skip_spaces-pass")
        self.assertEqual(summary["proof_status"], "trusted-under-owned-input-contract")
        self.assertEqual(summary["function_map_entry"]["symbol"], "skip_spaces")
        self.assertEqual(summary["function_map_entry"]["status"], "live-proven")
        self.assertEqual(
            summary["source_evidence"]["signature"],
            "extern char * __must_check skip_spaces(const char *)",
        )
        self.assertEqual(summary["proof_string"], repl.SKIP_SPACES_PROOF_LABEL)
        self.assertEqual(summary["no_leading_string"], repl.SKIP_SPACES_NO_LEADING_LABEL)
        self.assertEqual(summary["expected_skip_offset"], repl.SKIP_SPACES_EXPECTED_OFFSET)
        self.assertEqual(summary["leading_expected_return_value"], "owned-string-pointer-plus-offset-redacted")
        self.assertEqual(summary["leading_observed_return_value"], "owned-string-pointer-plus-offset-redacted")
        self.assertTrue(summary["leading_return_matches_expected_offset"])
        self.assertEqual(summary["no_leading_expected_return_value"], "owned-string-pointer-redacted")
        self.assertEqual(summary["no_leading_observed_return_value"], "owned-string-pointer-redacted")
        self.assertTrue(summary["no_leading_return_matches_original_pointer"])
        self.assertTrue(summary["string_unchanged_after_calls"])
        self.assertTrue(summary["raw_runtime_values_redacted"])
        self.assertTrue(summary["owned_pointer_redacted"])
        self.assertTrue(summary["observed_bytes_redacted"])
        self.assertNotIn("alloc_ptr", summary)
        self.assertNotIn("leading_return_ptr", summary)
        self.assertNotIn("no_leading_return_ptr", summary)
        self.assertEqual(private["alloc_ptr"], f"0x{fake.heap_ptr:x}")
        self.assertEqual(private["leading_return_ptr"], f"0x{fake.heap_ptr + repl.SKIP_SPACES_EXPECTED_OFFSET:x}")
        self.assertEqual(private["no_leading_return_ptr"], f"0x{fake.heap_ptr:x}")
        self.assertEqual(private["expected_leading_hex"], expected_leading.hex())
        self.assertEqual(private["expected_no_leading_hex"], expected_no_leading.hex())
        self.assertEqual(private["observed_bytes_hex"], expected_no_leading.hex())
        self.assertEqual(fake.freed, [fake.heap_ptr])

    def test_call_proof_strim_passes_with_owned_mutable_string_contract(self) -> None:
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
            "strim",
            source_root=KERNEL_SOURCE_ROOT,
        )

        payload_len = max(len(repl.STRIM_PROOF_BYTES), len(repl.STRIM_CLEAN_BYTES))
        expected_original = repl.STRIM_PROOF_BYTES.ljust(payload_len, b"\x00") + (
            b"\xcc" * repl.STRIM_CANARY_LEN
        )
        trimmed_payload = bytearray(repl.STRIM_PROOF_BYTES.ljust(payload_len, b"\x00"))
        trimmed_payload[repl.STRIM_EXPECTED_NUL_OFFSET] = 0
        expected_trimmed = bytes(trimmed_payload) + (b"\xcc" * repl.STRIM_CANARY_LEN)
        expected_clean = repl.STRIM_CLEAN_BYTES.ljust(payload_len, b"\x00") + (
            b"\xcc" * repl.STRIM_CANARY_LEN
        )

        self.assertTrue(summary["ok"], summary)
        self.assertEqual(summary["decision"], "a90-repl-live-call-proof-strim-pass")
        self.assertEqual(summary["proof_status"], "trusted-under-owned-input-contract")
        self.assertEqual(summary["function_map_entry"]["symbol"], "strim")
        self.assertEqual(summary["function_map_entry"]["status"], "live-proven")
        self.assertEqual(summary["source_evidence"]["signature"], "extern char * strim(char *)")
        self.assertEqual(summary["proof_string"], repl.STRIM_PROOF_LABEL)
        self.assertEqual(summary["trimmed_string"], repl.STRIM_TRIMMED_LABEL)
        self.assertEqual(summary["clean_string"], repl.STRIM_CLEAN_LABEL)
        self.assertEqual(summary["expected_trim_offset"], repl.STRIM_EXPECTED_OFFSET)
        self.assertEqual(summary["expected_first_trailing_space_nul_offset"], repl.STRIM_EXPECTED_NUL_OFFSET)
        self.assertEqual(summary["trim_expected_return_value"], "owned-string-pointer-plus-offset-redacted")
        self.assertEqual(summary["trim_observed_return_value"], "owned-string-pointer-plus-offset-redacted")
        self.assertTrue(summary["trim_return_matches_expected_offset"])
        self.assertTrue(summary["trimmed_bytes_match_expected"])
        self.assertEqual(summary["clean_expected_return_value"], "owned-string-pointer-redacted")
        self.assertEqual(summary["clean_observed_return_value"], "owned-string-pointer-redacted")
        self.assertTrue(summary["clean_return_matches_original_pointer"])
        self.assertTrue(summary["clean_string_unchanged_after_call"])
        self.assertTrue(summary["raw_runtime_values_redacted"])
        self.assertTrue(summary["owned_pointer_redacted"])
        self.assertTrue(summary["observed_bytes_redacted"])
        self.assertNotIn("alloc_ptr", summary)
        self.assertNotIn("trim_return_ptr", summary)
        self.assertNotIn("clean_return_ptr", summary)
        self.assertEqual(private["alloc_ptr"], f"0x{fake.heap_ptr:x}")
        self.assertEqual(private["trim_return_ptr"], f"0x{fake.heap_ptr + repl.STRIM_EXPECTED_OFFSET:x}")
        self.assertEqual(private["clean_return_ptr"], f"0x{fake.heap_ptr:x}")
        self.assertEqual(private["expected_original_hex"], expected_original.hex())
        self.assertEqual(private["expected_trimmed_hex"], expected_trimmed.hex())
        self.assertEqual(private["observed_trimmed_hex"], expected_trimmed.hex())
        self.assertEqual(private["expected_clean_hex"], expected_clean.hex())
        self.assertEqual(private["observed_bytes_hex"], expected_clean.hex())
        self.assertEqual(fake.freed, [fake.heap_ptr])

    def test_call_proof_strreplace_passes_with_owned_mutable_string_contract(self) -> None:
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
            "strreplace",
            source_root=KERNEL_SOURCE_ROOT,
        )

        expected_original = repl.STRREPLACE_PROOF_BYTES + (b"\xcc" * repl.STRREPLACE_CANARY_LEN)
        expected_replaced = repl.STRREPLACE_EXPECTED_BYTES + (b"\xcc" * repl.STRREPLACE_CANARY_LEN)

        self.assertTrue(summary["ok"], summary)
        self.assertEqual(summary["decision"], "a90-repl-live-call-proof-strreplace-pass")
        self.assertEqual(summary["proof_status"], "trusted-under-owned-input-contract")
        self.assertEqual(summary["function_map_entry"]["symbol"], "strreplace")
        self.assertEqual(summary["function_map_entry"]["status"], "live-proven")
        self.assertEqual(
            summary["source_evidence"]["signature"],
            "char * strreplace(char *s, char old, char new)",
        )
        self.assertEqual(summary["proof_string"], repl.STRREPLACE_PROOF_LABEL)
        self.assertEqual(summary["expected_replaced_string"], repl.STRREPLACE_EXPECTED_BYTES[:-1].decode("ascii"))
        self.assertEqual(summary["old_byte"], f"0x{repl.STRREPLACE_OLD_BYTE:02x}")
        self.assertEqual(summary["new_byte"], f"0x{repl.STRREPLACE_NEW_BYTE:02x}")
        self.assertEqual(summary["missing_byte"], f"0x{repl.STRREPLACE_MISSING_BYTE:02x}")
        self.assertEqual(summary["expected_nul_offset"], repl.STRREPLACE_NUL_OFFSET)
        self.assertEqual(summary["hit_expected_return_value"], "owned-string-nul-terminator-pointer-redacted")
        self.assertEqual(summary["hit_observed_return_value"], "owned-string-nul-terminator-pointer-redacted")
        self.assertTrue(summary["hit_return_matches_nul_offset"])
        self.assertTrue(summary["replacement_bytes_match_expected"])
        self.assertEqual(summary["missing_expected_return_value"], "owned-string-nul-terminator-pointer-redacted")
        self.assertEqual(summary["missing_observed_return_value"], "owned-string-nul-terminator-pointer-redacted")
        self.assertTrue(summary["missing_return_matches_nul_offset"])
        self.assertTrue(summary["missing_string_unchanged_after_call"])
        self.assertTrue(summary["raw_runtime_values_redacted"])
        self.assertTrue(summary["owned_pointer_redacted"])
        self.assertTrue(summary["observed_bytes_redacted"])
        self.assertNotIn("alloc_ptr", summary)
        self.assertNotIn("hit_return_ptr", summary)
        self.assertNotIn("missing_return_ptr", summary)
        self.assertEqual(private["alloc_ptr"], f"0x{fake.heap_ptr:x}")
        self.assertEqual(private["hit_return_ptr"], f"0x{fake.heap_ptr + repl.STRREPLACE_NUL_OFFSET:x}")
        self.assertEqual(private["missing_return_ptr"], f"0x{fake.heap_ptr + repl.STRREPLACE_NUL_OFFSET:x}")
        self.assertEqual(private["expected_original_hex"], expected_original.hex())
        self.assertEqual(private["expected_replaced_hex"], expected_replaced.hex())
        self.assertEqual(private["observed_replaced_hex"], expected_replaced.hex())
        self.assertEqual(private["expected_missing_hex"], expected_original.hex())
        self.assertEqual(private["observed_bytes_hex"], expected_original.hex())
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

    def test_call_proof_strcpy_passes_with_owned_buffers_contract(self) -> None:
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
            "strcpy",
            source_root=KERNEL_SOURCE_ROOT,
        )

        expected_src = repl.STRCPY_PROOF_SRC_BYTES + (b"\xcc" * repl.STRCPY_CANARY_LEN)
        expected_dst = (
            repl.STRCPY_PROOF_SRC_BYTES
            + (bytes([repl.STRCPY_DST_INITIAL_BYTE]) * repl.STRCPY_DST_TAIL_LEN)
            + (b"\xcc" * repl.STRCPY_CANARY_LEN)
        )

        self.assertTrue(summary["ok"], summary)
        self.assertEqual(summary["decision"], "a90-repl-live-call-proof-strcpy-pass")
        self.assertEqual(summary["proof_status"], "trusted-under-owned-input-contract")
        self.assertEqual(summary["function_map_entry"]["symbol"], "strcpy")
        self.assertEqual(summary["function_map_entry"]["status"], "live-proven")
        self.assertEqual(summary["source_evidence"]["signature"], "extern char * strcpy(char *,const char *)")
        self.assertEqual(summary["proof_string"], repl.STRCPY_PROOF_LABEL)
        self.assertEqual(summary["expected_return_value"], "owned-destination-pointer-redacted")
        self.assertEqual(summary["observed_return_value"], "owned-destination-pointer-redacted")
        self.assertTrue(summary["return_matches_destination_pointer"])
        self.assertTrue(summary["destination_matches_source"])
        self.assertTrue(summary["source_unchanged_after_call"])
        self.assertTrue(summary["raw_runtime_values_redacted"])
        self.assertTrue(summary["owned_pointer_redacted"])
        self.assertTrue(summary["observed_bytes_redacted"])
        self.assertNotIn("dst_ptr", summary)
        self.assertNotIn("src_ptr", summary)
        self.assertNotIn("return_ptr", summary)
        self.assertEqual(private["dst_ptr"], f"0x{fake.heap_ptr:x}")
        self.assertEqual(private["src_ptr"], f"0x{fake.heap_ptr + 0x1000:x}")
        self.assertEqual(private["return_ptr"], f"0x{fake.heap_ptr:x}")
        self.assertEqual(private["expected_src_hex"], expected_src.hex())
        self.assertEqual(private["expected_dst_hex"], expected_dst.hex())
        self.assertEqual(private["observed_src_hex"], expected_src.hex())
        self.assertEqual(private["observed_dst_hex"], expected_dst.hex())
        self.assertEqual(fake.freed, [fake.heap_ptr, fake.heap_ptr + 0x1000])

    def test_call_proof_strcat_passes_with_owned_buffers_contract(self) -> None:
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
            "strcat",
            source_root=KERNEL_SOURCE_ROOT,
        )

        expected_src = repl.STRCAT_SRC_BYTES + (b"\xcc" * repl.STRCAT_CANARY_LEN)
        expected_dst = (
            repl.STRCAT_EXPECTED_DST_BYTES
            + (bytes([repl.STRCAT_DST_INITIAL_BYTE]) * repl.STRCAT_DST_TAIL_LEN)
            + (b"\xcc" * repl.STRCAT_CANARY_LEN)
        )

        self.assertTrue(summary["ok"], summary)
        self.assertEqual(summary["decision"], "a90-repl-live-call-proof-strcat-pass")
        self.assertEqual(summary["proof_status"], "trusted-under-owned-input-contract")
        self.assertEqual(summary["function_map_entry"]["symbol"], "strcat")
        self.assertEqual(summary["function_map_entry"]["status"], "live-proven")
        self.assertEqual(summary["source_evidence"]["signature"], "extern char * strcat(char *, const char *)")
        self.assertEqual(summary["proof_string"], repl.STRCAT_PROOF_LABEL)
        self.assertEqual(summary["expected_return_value"], "owned-destination-pointer-redacted")
        self.assertEqual(summary["observed_return_value"], "owned-destination-pointer-redacted")
        self.assertTrue(summary["return_matches_destination_pointer"])
        self.assertTrue(summary["destination_appended_source"])
        self.assertTrue(summary["source_unchanged_after_call"])
        self.assertTrue(summary["raw_runtime_values_redacted"])
        self.assertTrue(summary["owned_pointer_redacted"])
        self.assertTrue(summary["observed_bytes_redacted"])
        self.assertNotIn("dst_ptr", summary)
        self.assertNotIn("src_ptr", summary)
        self.assertNotIn("return_ptr", summary)
        self.assertEqual(private["dst_ptr"], f"0x{fake.heap_ptr:x}")
        self.assertEqual(private["src_ptr"], f"0x{fake.heap_ptr + 0x1000:x}")
        self.assertEqual(private["return_ptr"], f"0x{fake.heap_ptr:x}")
        self.assertEqual(private["expected_src_hex"], expected_src.hex())
        self.assertEqual(private["expected_dst_hex"], expected_dst.hex())
        self.assertEqual(private["observed_src_hex"], expected_src.hex())
        self.assertEqual(private["observed_dst_hex"], expected_dst.hex())
        self.assertEqual(fake.freed, [fake.heap_ptr, fake.heap_ptr + 0x1000])

    def test_call_proof_strncat_passes_with_owned_buffers_contract(self) -> None:
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
            "strncat",
            source_root=KERNEL_SOURCE_ROOT,
        )

        expected_src = repl.STRNCAT_SRC_BYTES + (b"\xcc" * repl.STRNCAT_CANARY_LEN)
        expected_dst = (
            repl.STRNCAT_EXPECTED_DST_BYTES
            + (bytes([repl.STRNCAT_DST_INITIAL_BYTE]) * repl.STRNCAT_DST_TAIL_LEN)
            + (b"\xcc" * repl.STRNCAT_CANARY_LEN)
        )

        self.assertTrue(summary["ok"], summary)
        self.assertEqual(summary["decision"], "a90-repl-live-call-proof-strncat-pass")
        self.assertEqual(summary["proof_status"], "trusted-under-owned-input-contract")
        self.assertEqual(summary["function_map_entry"]["symbol"], "strncat")
        self.assertEqual(summary["function_map_entry"]["status"], "live-proven")
        self.assertEqual(
            summary["source_evidence"]["signature"],
            "extern char * strncat(char *, const char *, __kernel_size_t)",
        )
        self.assertEqual(summary["proof_string"], repl.STRNCAT_PROOF_LABEL)
        self.assertEqual(summary["count_arg"], repl.STRNCAT_PROOF_COUNT)
        self.assertEqual(summary["expected_return_value"], "owned-destination-pointer-redacted")
        self.assertEqual(summary["observed_return_value"], "owned-destination-pointer-redacted")
        self.assertTrue(summary["return_matches_destination_pointer"])
        self.assertTrue(summary["destination_appended_count_bounded_source"])
        self.assertTrue(summary["source_unchanged_after_call"])
        self.assertTrue(summary["raw_runtime_values_redacted"])
        self.assertTrue(summary["owned_pointer_redacted"])
        self.assertTrue(summary["observed_bytes_redacted"])
        self.assertNotIn("dst_ptr", summary)
        self.assertNotIn("src_ptr", summary)
        self.assertNotIn("return_ptr", summary)
        self.assertEqual(private["dst_ptr"], f"0x{fake.heap_ptr:x}")
        self.assertEqual(private["src_ptr"], f"0x{fake.heap_ptr + 0x1000:x}")
        self.assertEqual(private["return_ptr"], f"0x{fake.heap_ptr:x}")
        self.assertEqual(private["expected_src_hex"], expected_src.hex())
        self.assertEqual(private["expected_dst_hex"], expected_dst.hex())
        self.assertEqual(private["observed_src_hex"], expected_src.hex())
        self.assertEqual(private["observed_dst_hex"], expected_dst.hex())
        self.assertEqual(fake.freed, [fake.heap_ptr, fake.heap_ptr + 0x1000])

    def test_call_proof_strlcat_passes_with_owned_buffers_contract(self) -> None:
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
            "strlcat",
            source_root=KERNEL_SOURCE_ROOT,
        )

        expected_src = repl.STRLCAT_SRC_BYTES + (b"\xcc" * repl.STRLCAT_CANARY_LEN)
        expected_dst = (
            repl.STRLCAT_EXPECTED_DST_BYTES
            + (bytes([repl.STRLCAT_DST_INITIAL_BYTE]) * repl.STRLCAT_DST_TAIL_LEN)
            + (b"\xcc" * repl.STRLCAT_CANARY_LEN)
        )

        self.assertTrue(summary["ok"], summary)
        self.assertEqual(summary["decision"], "a90-repl-live-call-proof-strlcat-pass")
        self.assertEqual(summary["proof_status"], "trusted-under-owned-input-contract")
        self.assertEqual(summary["function_map_entry"]["symbol"], "strlcat")
        self.assertEqual(summary["function_map_entry"]["status"], "live-proven")
        self.assertEqual(
            summary["source_evidence"]["signature"],
            "extern size_t strlcat(char *, const char *, __kernel_size_t)",
        )
        self.assertEqual(summary["proof_string"], repl.STRLCAT_PROOF_LABEL)
        self.assertEqual(summary["size_arg"], repl.STRLCAT_PROOF_SIZE)
        self.assertEqual(summary["copy_len"], repl.STRLCAT_COPY_LEN)
        self.assertEqual(summary["expected_return_value"], f"0x{repl.STRLCAT_EXPECTED_RETURN:x}")
        self.assertEqual(summary["observed_return_value"], f"0x{repl.STRLCAT_EXPECTED_RETURN:x}")
        self.assertTrue(summary["destination_appended_size_bounded_source"])
        self.assertTrue(summary["source_unchanged_after_call"])
        self.assertTrue(summary["raw_runtime_values_redacted"])
        self.assertTrue(summary["owned_pointer_redacted"])
        self.assertTrue(summary["observed_bytes_redacted"])
        self.assertNotIn("dst_ptr", summary)
        self.assertNotIn("src_ptr", summary)
        self.assertEqual(private["dst_ptr"], f"0x{fake.heap_ptr:x}")
        self.assertEqual(private["src_ptr"], f"0x{fake.heap_ptr + 0x1000:x}")
        self.assertEqual(private["expected_src_hex"], expected_src.hex())
        self.assertEqual(private["expected_dst_hex"], expected_dst.hex())
        self.assertEqual(private["observed_src_hex"], expected_src.hex())
        self.assertEqual(private["observed_dst_hex"], expected_dst.hex())
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

    def test_call_proof_memchr_passes_with_owned_buffer_contract(self) -> None:
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
            "memchr",
            source_root=KERNEL_SOURCE_ROOT,
        )

        self.assertTrue(summary["ok"], summary)
        self.assertEqual(summary["decision"], "a90-repl-live-call-proof-memchr-pass")
        self.assertEqual(summary["proof_status"], "trusted-under-owned-input-contract")
        self.assertEqual(summary["function_map_entry"]["symbol"], "memchr")
        self.assertEqual(summary["function_map_entry"]["status"], "live-proven")
        self.assertEqual(
            summary["source_evidence"]["signature"],
            "extern void * memchr(const void *,int,__kernel_size_t)",
        )
        self.assertEqual(summary["proof_bytes_label"], repl.MEMCHR_PROOF_BYTES.decode("ascii"))
        self.assertEqual(summary["size_arg"], repl.MEMCHR_PROOF_SIZE)
        self.assertEqual(summary["search_byte"], f"0x{repl.MEMCHR_SEARCH_BYTE:02x}")
        self.assertEqual(summary["expected_hit_offset"], repl.MEMCHR_EXPECTED_OFFSET)
        self.assertEqual(summary["hit_expected_return_value"], "owned-buffer-pointer-plus-offset-redacted")
        self.assertEqual(summary["hit_observed_return_value"], "owned-buffer-pointer-plus-offset-redacted")
        self.assertTrue(summary["hit_return_matches_expected_offset"])
        self.assertEqual(summary["missing_byte"], f"0x{repl.MEMCHR_MISSING_BYTE:02x}")
        self.assertEqual(summary["missing_expected_return_value"], "0x0")
        self.assertEqual(summary["missing_observed_return_value"], "0x0")
        self.assertTrue(summary["missing_return_matches_null"])
        self.assertTrue(summary["canary_contains_missing_byte"])
        self.assertTrue(summary["buffer_unchanged_after_calls"])
        self.assertTrue(summary["raw_runtime_values_redacted"])
        self.assertTrue(summary["owned_pointer_redacted"])
        self.assertTrue(summary["observed_bytes_redacted"])
        self.assertNotIn("alloc_ptr", summary)
        self.assertNotIn("hit_return_ptr", summary)
        self.assertNotIn("missing_return_ptr", summary)
        self.assertEqual(private["alloc_ptr"], f"0x{fake.heap_ptr:x}")
        self.assertEqual(
            private["hit_return_ptr"],
            f"0x{fake.heap_ptr + repl.MEMCHR_EXPECTED_OFFSET:x}",
        )
        self.assertEqual(private["missing_return_ptr"], "0x0")
        expected_hex = (repl.MEMCHR_PROOF_BYTES + repl.MEMCHR_CANARY_BYTES).hex()
        self.assertEqual(private["observed_bytes_hex"], expected_hex)
        self.assertEqual(fake.freed, [fake.heap_ptr])

    def test_call_proof_memchr_inv_passes_with_owned_buffer_contract(self) -> None:
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
            "memchr_inv",
            source_root=KERNEL_SOURCE_ROOT,
        )

        self.assertTrue(summary["ok"], summary)
        self.assertEqual(summary["decision"], "a90-repl-live-call-proof-memchr_inv-pass")
        self.assertEqual(summary["proof_status"], "trusted-under-owned-input-contract")
        self.assertEqual(summary["function_map_entry"]["symbol"], "memchr_inv")
        self.assertEqual(summary["function_map_entry"]["status"], "live-proven")
        self.assertEqual(
            summary["source_evidence"]["signature"],
            "void * memchr_inv(const void *s, int c, size_t n)",
        )
        self.assertEqual(summary["size_arg"], repl.MEMCHR_INV_PROOF_SIZE)
        self.assertEqual(summary["fill_byte"], f"0x{repl.MEMCHR_INV_FILL_BYTE:02x}")
        self.assertEqual(summary["mismatch_byte"], f"0x{repl.MEMCHR_INV_MISMATCH_BYTE:02x}")
        self.assertEqual(summary["expected_hit_offset"], repl.MEMCHR_INV_EXPECTED_OFFSET)
        self.assertEqual(summary["hit_expected_return_value"], "owned-buffer-pointer-plus-offset-redacted")
        self.assertEqual(summary["hit_observed_return_value"], "owned-buffer-pointer-plus-offset-redacted")
        self.assertTrue(summary["hit_return_matches_expected_offset"])
        self.assertEqual(summary["all_fill_expected_return_value"], "0x0")
        self.assertEqual(summary["all_fill_observed_return_value"], "0x0")
        self.assertTrue(summary["all_fill_return_matches_null"])
        self.assertTrue(summary["canary_contains_non_fill_byte"])
        self.assertTrue(summary["buffer_unchanged_after_calls"])
        self.assertTrue(summary["raw_runtime_values_redacted"])
        self.assertTrue(summary["owned_pointer_redacted"])
        self.assertTrue(summary["observed_bytes_redacted"])
        self.assertNotIn("alloc_ptr", summary)
        self.assertNotIn("hit_return_ptr", summary)
        self.assertNotIn("all_fill_return_ptr", summary)
        self.assertEqual(private["alloc_ptr"], f"0x{fake.heap_ptr:x}")
        self.assertEqual(
            private["hit_return_ptr"],
            f"0x{fake.heap_ptr + repl.MEMCHR_INV_EXPECTED_OFFSET:x}",
        )
        self.assertEqual(private["all_fill_return_ptr"], "0x0")
        expected_hit_hex = (repl.MEMCHR_INV_HIT_BYTES + repl.MEMCHR_INV_CANARY_BYTES).hex()
        expected_equal_hex = (repl.MEMCHR_INV_EQUAL_BYTES + repl.MEMCHR_INV_CANARY_BYTES).hex()
        self.assertEqual(private["observed_hit_bytes_hex"], expected_hit_hex)
        self.assertEqual(private["observed_equal_bytes_hex"], expected_equal_hex)
        self.assertEqual(fake.freed, [fake.heap_ptr])

    def test_call_proof_memcpy_passes_with_owned_buffers_contract(self) -> None:
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
            "memcpy",
            source_root=KERNEL_SOURCE_ROOT,
        )

        self.assertTrue(summary["ok"], summary)
        self.assertEqual(summary["decision"], "a90-repl-live-call-proof-memcpy-pass")
        self.assertEqual(summary["proof_status"], "trusted-under-owned-input-contract")
        self.assertEqual(summary["function_map_entry"]["symbol"], "memcpy")
        self.assertEqual(summary["function_map_entry"]["status"], "live-proven")
        self.assertEqual(
            summary["source_evidence"]["signature"],
            "extern void * memcpy(void *,const void *,__kernel_size_t)",
        )
        self.assertEqual(summary["proof_bytes_label"], repl.MEMCPY_PROOF_BYTES.decode("ascii"))
        self.assertEqual(summary["size_arg"], repl.MEMCPY_PROOF_SIZE)
        self.assertEqual(summary["initial_destination_byte"], f"0x{repl.MEMCPY_DST_INITIAL_BYTE:02x}")
        self.assertEqual(summary["expected_return_value"], "owned-destination-pointer-redacted")
        self.assertEqual(summary["observed_return_value"], "owned-destination-pointer-redacted")
        self.assertTrue(summary["return_matches_destination"])
        self.assertTrue(summary["destination_prefix_matches_source"])
        self.assertTrue(summary["destination_post_size_canary_preserved"])
        self.assertTrue(summary["source_buffer_unchanged"])
        self.assertTrue(summary["raw_runtime_values_redacted"])
        self.assertTrue(summary["owned_pointer_redacted"])
        self.assertTrue(summary["observed_bytes_redacted"])
        self.assertNotIn("dst_ptr", summary)
        self.assertNotIn("src_ptr", summary)
        self.assertNotIn("return_ptr", summary)
        self.assertEqual(private["dst_ptr"], f"0x{fake.heap_ptr:x}")
        self.assertEqual(private["src_ptr"], f"0x{fake.heap_ptr + 0x1000:x}")
        self.assertEqual(private["return_ptr"], f"0x{fake.heap_ptr:x}")
        expected_dst_before_hex = (
            bytes([repl.MEMCPY_DST_INITIAL_BYTE]) * repl.MEMCPY_PROOF_SIZE
            + (b"\xcc" * repl.MEMCPY_DST_CANARY_LEN)
        ).hex()
        expected_dst_after_hex = (
            repl.MEMCPY_PROOF_BYTES
            + (b"\xcc" * repl.MEMCPY_DST_CANARY_LEN)
        ).hex()
        expected_src_hex = (
            repl.MEMCPY_PROOF_BYTES
            + (b"\xdd" * repl.MEMCPY_SRC_CANARY_LEN)
        ).hex()
        self.assertEqual(private["dst_before_hex"], expected_dst_before_hex)
        self.assertEqual(private["dst_after_hex"], expected_dst_after_hex)
        self.assertEqual(private["src_before_hex"], expected_src_hex)
        self.assertEqual(private["src_after_hex"], expected_src_hex)
        self.assertEqual(fake.freed, [fake.heap_ptr, fake.heap_ptr + 0x1000])

    def test_call_proof_memmove_passes_with_owned_overlap_contract(self) -> None:
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
            "memmove",
            source_root=KERNEL_SOURCE_ROOT,
        )

        self.assertTrue(summary["ok"], summary)
        self.assertEqual(summary["decision"], "a90-repl-live-call-proof-memmove-pass")
        self.assertEqual(summary["proof_status"], "trusted-under-owned-input-contract")
        self.assertEqual(summary["function_map_entry"]["symbol"], "memmove")
        self.assertEqual(summary["function_map_entry"]["status"], "live-proven")
        self.assertEqual(
            summary["source_evidence"]["signature"],
            "extern void * memmove(void *,const void *,__kernel_size_t)",
        )
        self.assertEqual(summary["proof_bytes_label"], repl.MEMMOVE_PROOF_BYTES.decode("ascii"))
        self.assertEqual(summary["size_arg"], repl.MEMMOVE_PROOF_SIZE)
        self.assertEqual(summary["source_offset"], 0)
        self.assertEqual(summary["destination_offset"], repl.MEMMOVE_DST_OFFSET)
        self.assertEqual(summary["overlap_direction"], "dst-after-src")
        self.assertEqual(summary["expected_path"], "overlap-backward-copy")
        self.assertEqual(summary["expected_return_value"], "owned-destination-pointer-redacted")
        self.assertEqual(summary["observed_return_value"], "owned-destination-pointer-redacted")
        self.assertTrue(summary["return_matches_destination"])
        self.assertTrue(summary["final_buffer_matches_overlap_safe_snapshot"])
        self.assertTrue(summary["post_move_canary_preserved"])
        self.assertTrue(summary["source_region_expected_to_overlap"])
        self.assertTrue(summary["raw_runtime_values_redacted"])
        self.assertTrue(summary["owned_pointer_redacted"])
        self.assertTrue(summary["observed_bytes_redacted"])
        self.assertNotIn("alloc_ptr", summary)
        self.assertNotIn("dst_ptr", summary)
        self.assertNotIn("src_ptr", summary)
        self.assertNotIn("return_ptr", summary)
        self.assertEqual(private["alloc_ptr"], f"0x{fake.heap_ptr:x}")
        self.assertEqual(private["src_ptr"], f"0x{fake.heap_ptr:x}")
        self.assertEqual(private["dst_ptr"], f"0x{fake.heap_ptr + repl.MEMMOVE_DST_OFFSET:x}")
        self.assertEqual(private["return_ptr"], f"0x{fake.heap_ptr + repl.MEMMOVE_DST_OFFSET:x}")
        initial = (
            repl.MEMMOVE_PROOF_BYTES
            + (bytes([repl.MEMMOVE_TAIL_FILL_BYTE]) * repl.MEMMOVE_DST_OFFSET)
            + (b"\xcc" * repl.MEMMOVE_CANARY_LEN)
        )
        expected_after = bytearray(initial)
        expected_after[
            repl.MEMMOVE_DST_OFFSET:repl.MEMMOVE_DST_OFFSET + repl.MEMMOVE_PROOF_SIZE
        ] = initial[:repl.MEMMOVE_PROOF_SIZE]
        self.assertEqual(private["before_hex"], initial.hex())
        self.assertEqual(private["after_hex"], bytes(expected_after).hex())
        self.assertEqual(private["expected_after_hex"], bytes(expected_after).hex())
        self.assertEqual(fake.freed, [fake.heap_ptr])

    def test_call_proof_strchr_passes_with_owned_string_contract(self) -> None:
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
            "strchr",
            source_root=KERNEL_SOURCE_ROOT,
        )

        self.assertTrue(summary["ok"], summary)
        self.assertEqual(summary["decision"], "a90-repl-live-call-proof-strchr-pass")
        self.assertEqual(summary["proof_status"], "trusted-under-owned-input-contract")
        self.assertEqual(summary["function_map_entry"]["symbol"], "strchr")
        self.assertEqual(summary["function_map_entry"]["status"], "live-proven")
        self.assertEqual(
            summary["source_evidence"]["signature"],
            "extern char * strchr(const char *,int)",
        )
        self.assertEqual(summary["proof_string"], repl.STRCHR_PROOF_LABEL)
        self.assertEqual(summary["search_byte"], f"0x{repl.STRCHR_SEARCH_BYTE:02x}")
        self.assertEqual(summary["expected_hit_offset"], repl.STRCHR_EXPECTED_OFFSET)
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
            f"0x{fake.heap_ptr + repl.STRCHR_EXPECTED_OFFSET:x}",
        )
        expected_hex = (
            repl.STRCHR_PROOF_BYTES + (b"\xcc" * repl.STRCHR_CANARY_LEN)
        ).hex()
        self.assertEqual(private["observed_bytes_hex"], expected_hex)
        self.assertEqual(fake.freed, [fake.heap_ptr])

    def test_call_proof_strchrnul_passes_with_owned_string_contract(self) -> None:
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
            "strchrnul",
            source_root=KERNEL_SOURCE_ROOT,
        )

        self.assertTrue(summary["ok"], summary)
        self.assertEqual(summary["decision"], "a90-repl-live-call-proof-strchrnul-pass")
        self.assertEqual(summary["proof_status"], "trusted-under-owned-input-contract")
        self.assertEqual(summary["function_map_entry"]["symbol"], "strchrnul")
        self.assertEqual(summary["function_map_entry"]["status"], "live-proven")
        self.assertEqual(
            summary["source_evidence"]["signature"],
            "extern char * strchrnul(const char *,int)",
        )
        self.assertEqual(summary["proof_string"], repl.STRCHRNUL_PROOF_LABEL)
        self.assertEqual(summary["search_byte"], f"0x{repl.STRCHRNUL_SEARCH_BYTE:02x}")
        self.assertEqual(summary["expected_hit_offset"], repl.STRCHRNUL_EXPECTED_OFFSET)
        self.assertEqual(summary["hit_expected_return_value"], "owned-string-pointer-plus-offset-redacted")
        self.assertEqual(summary["hit_observed_return_value"], "owned-string-pointer-plus-offset-redacted")
        self.assertTrue(summary["hit_return_matches_expected_offset"])
        self.assertEqual(summary["expected_missing_nul_offset"], repl.STRCHRNUL_NUL_OFFSET)
        self.assertEqual(
            summary["missing_expected_return_value"],
            "owned-string-pointer-plus-nul-offset-redacted",
        )
        self.assertEqual(
            summary["missing_observed_return_value"],
            "owned-string-pointer-plus-nul-offset-redacted",
        )
        self.assertTrue(summary["missing_return_matches_nul_offset"])
        self.assertTrue(summary["string_unchanged_after_calls"])
        self.assertTrue(summary["raw_runtime_values_redacted"])
        self.assertTrue(summary["owned_pointer_redacted"])
        self.assertTrue(summary["observed_bytes_redacted"])
        self.assertNotIn("alloc_ptr", summary)
        self.assertNotIn("hit_return_ptr", summary)
        self.assertNotIn("missing_return_ptr", summary)
        self.assertEqual(private["alloc_ptr"], f"0x{fake.heap_ptr:x}")
        self.assertEqual(
            private["hit_return_ptr"],
            f"0x{fake.heap_ptr + repl.STRCHRNUL_EXPECTED_OFFSET:x}",
        )
        self.assertEqual(
            private["missing_return_ptr"],
            f"0x{fake.heap_ptr + repl.STRCHRNUL_NUL_OFFSET:x}",
        )
        expected_hex = (
            repl.STRCHRNUL_PROOF_BYTES + (b"\xcc" * repl.STRCHRNUL_CANARY_LEN)
        ).hex()
        self.assertEqual(private["observed_bytes_hex"], expected_hex)
        self.assertEqual(fake.freed, [fake.heap_ptr])

    def test_call_proof_strstr_passes_with_owned_strings_contract(self) -> None:
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
            "strstr",
            source_root=KERNEL_SOURCE_ROOT,
        )

        self.assertTrue(summary["ok"], summary)
        self.assertEqual(summary["decision"], "a90-repl-live-call-proof-strstr-pass")
        self.assertEqual(summary["proof_status"], "trusted-under-owned-input-contract")
        self.assertEqual(summary["function_map_entry"]["symbol"], "strstr")
        self.assertEqual(summary["function_map_entry"]["status"], "live-proven")
        self.assertEqual(
            summary["source_evidence"]["signature"],
            "extern char * strstr(const char *, const char *)",
        )
        self.assertEqual(summary["haystack"], repl.STRSTR_HAYSTACK_LABEL)
        self.assertEqual(summary["needle"], repl.STRSTR_NEEDLE_LABEL)
        self.assertEqual(summary["missing_needle"], repl.STRSTR_MISSING_LABEL)
        self.assertEqual(summary["expected_hit_offset"], repl.STRSTR_EXPECTED_OFFSET)
        self.assertEqual(
            summary["hit_expected_return_value"],
            "owned-haystack-pointer-plus-offset-redacted",
        )
        self.assertEqual(
            summary["hit_observed_return_value"],
            "owned-haystack-pointer-plus-offset-redacted",
        )
        self.assertTrue(summary["hit_return_matches_expected_offset"])
        self.assertEqual(summary["missing_expected_return_value"], "0x0")
        self.assertEqual(summary["missing_observed_return_value"], "0x0")
        self.assertTrue(summary["strings_unchanged_after_calls"])
        self.assertTrue(summary["raw_runtime_values_redacted"])
        self.assertTrue(summary["owned_pointer_redacted"])
        self.assertTrue(summary["observed_bytes_redacted"])
        self.assertNotIn("haystack_ptr", summary)
        self.assertNotIn("needle_ptr", summary)
        self.assertNotIn("hit_return_ptr", summary)
        self.assertEqual(private["haystack_ptr"], f"0x{fake.heap_ptr:x}")
        self.assertEqual(private["needle_ptr"], f"0x{fake.heap_ptr + 0x1000:x}")
        self.assertEqual(
            private["hit_return_ptr"],
            f"0x{fake.heap_ptr + repl.STRSTR_EXPECTED_OFFSET:x}",
        )
        expected_haystack_hex = (
            repl.STRSTR_HAYSTACK_BYTES + (b"\xcc" * repl.STRSTR_CANARY_LEN)
        ).hex()
        expected_hit_needle_hex = (
            repl.STRSTR_NEEDLE_BYTES + (b"\xcc" * repl.STRSTR_CANARY_LEN)
        ).hex()
        expected_missing_needle_hex = (
            repl.STRSTR_MISSING_BYTES + (b"\xcc" * repl.STRSTR_CANARY_LEN)
        ).hex()
        self.assertEqual(private["expected_haystack_hex"], expected_haystack_hex)
        self.assertEqual(private["expected_hit_needle_hex"], expected_hit_needle_hex)
        self.assertEqual(private["expected_missing_needle_hex"], expected_missing_needle_hex)
        self.assertEqual(private["haystack_bytes_hex"], expected_haystack_hex)
        self.assertEqual(private["needle_bytes_hex"], expected_missing_needle_hex)
        self.assertEqual(fake.freed, [fake.heap_ptr, fake.heap_ptr + 0x1000])

    def test_call_proof_strnstr_passes_with_owned_strings_contract(self) -> None:
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
            "strnstr",
            source_root=KERNEL_SOURCE_ROOT,
        )

        self.assertTrue(summary["ok"], summary)
        self.assertEqual(summary["decision"], "a90-repl-live-call-proof-strnstr-pass")
        self.assertEqual(summary["proof_status"], "trusted-under-owned-input-contract")
        self.assertEqual(summary["function_map_entry"]["symbol"], "strnstr")
        self.assertEqual(summary["function_map_entry"]["status"], "live-proven")
        self.assertEqual(
            summary["source_evidence"]["signature"],
            "extern char * strnstr(const char *, const char *, size_t)",
        )
        self.assertEqual(summary["haystack"], repl.STRNSTR_HAYSTACK_LABEL)
        self.assertEqual(summary["needle"], repl.STRNSTR_NEEDLE_LABEL)
        self.assertEqual(summary["missing_needle"], repl.STRNSTR_MISSING_LABEL)
        self.assertEqual(summary["hit_len"], repl.STRNSTR_HIT_LEN)
        self.assertEqual(summary["bound_miss_len"], repl.STRNSTR_BOUND_MISS_LEN)
        self.assertEqual(summary["expected_hit_offset"], repl.STRNSTR_EXPECTED_OFFSET)
        self.assertTrue(summary["hit_return_matches_expected_offset"])
        self.assertEqual(summary["bound_miss_expected_return_value"], "0x0")
        self.assertEqual(summary["bound_miss_observed_return_value"], "0x0")
        self.assertEqual(summary["missing_expected_return_value"], "0x0")
        self.assertEqual(summary["missing_observed_return_value"], "0x0")
        self.assertTrue(summary["strings_unchanged_after_calls"])
        self.assertTrue(summary["raw_runtime_values_redacted"])
        self.assertTrue(summary["owned_pointer_redacted"])
        self.assertTrue(summary["observed_bytes_redacted"])
        self.assertNotIn("haystack_ptr", summary)
        self.assertNotIn("needle_ptr", summary)
        self.assertEqual(private["haystack_ptr"], f"0x{fake.heap_ptr:x}")
        self.assertEqual(private["needle_ptr"], f"0x{fake.heap_ptr + 0x1000:x}")
        self.assertEqual(
            private["expected_hit_return"],
            f"0x{fake.heap_ptr + repl.STRNSTR_EXPECTED_OFFSET:x}",
        )
        expected_haystack_hex = (
            repl.STRNSTR_HAYSTACK_BYTES + (b"\xcc" * repl.STRNSTR_CANARY_LEN)
        ).hex()
        expected_hit_needle_hex = (
            repl.STRNSTR_NEEDLE_BYTES + (b"\xcc" * repl.STRNSTR_CANARY_LEN)
        ).hex()
        expected_missing_hex = (
            repl.STRNSTR_MISSING_BYTES + (b"\xcc" * repl.STRNSTR_CANARY_LEN)
        ).hex()
        self.assertEqual(private["expected_haystack_hex"], expected_haystack_hex)
        self.assertEqual(private["expected_hit_needle_hex"], expected_hit_needle_hex)
        self.assertEqual(private["expected_missing_needle_hex"], expected_missing_hex)
        self.assertEqual(private["haystack_bytes_hex"], expected_haystack_hex)
        self.assertEqual(private["hit_needle_bytes_hex"], expected_hit_needle_hex)
        self.assertEqual(private["missing_needle_bytes_hex"], expected_missing_hex)
        self.assertEqual(fake.freed, [fake.heap_ptr, fake.heap_ptr + 0x1000])

    def test_call_proof_match_string_passes_with_owned_array_contract(self) -> None:
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
            "match_string",
            source_root=KERNEL_SOURCE_ROOT,
        )

        self.assertTrue(summary["ok"], summary)
        self.assertEqual(summary["decision"], "a90-repl-live-call-proof-match_string-pass")
        self.assertEqual(summary["proof_status"], "trusted-under-owned-input-contract")
        self.assertEqual(summary["function_map_entry"]["symbol"], "match_string")
        self.assertEqual(summary["function_map_entry"]["status"], "live-proven")
        self.assertEqual(
            summary["source_evidence"]["signature"],
            "int match_string(const char * const *array, size_t n, const char *string)",
        )
        self.assertEqual(summary["array_count"], repl.MATCH_STRING_ARRAY_COUNT)
        self.assertEqual(summary["array_items"], list(repl.MATCH_STRING_ITEM_LABELS))
        self.assertEqual(summary["search"], repl.MATCH_STRING_SEARCH_LABEL)
        self.assertEqual(summary["missing_search"], repl.MATCH_STRING_MISSING_LABEL)
        self.assertEqual(summary["expected_hit_index"], repl.MATCH_STRING_EXPECTED_INDEX)
        self.assertEqual(summary["hit_expected_return_value"], f"0x{repl.MATCH_STRING_EXPECTED_INDEX:x}")
        self.assertEqual(summary["hit_observed_return_value"], f"0x{repl.MATCH_STRING_EXPECTED_INDEX:x}")
        self.assertTrue(summary["hit_return_matches_expected_index"])
        self.assertEqual(summary["missing_expected_return_value"], f"0x{repl.MATCH_STRING_EINVAL_RETURN:x}")
        self.assertEqual(summary["missing_observed_return_value"], f"0x{repl.MATCH_STRING_EINVAL_RETURN:x}")
        self.assertEqual(summary["zero_count_expected_return_value"], f"0x{repl.MATCH_STRING_EINVAL_RETURN:x}")
        self.assertEqual(summary["zero_count_observed_return_value"], f"0x{repl.MATCH_STRING_EINVAL_RETURN:x}")
        self.assertTrue(summary["layout_unchanged_after_calls"])
        self.assertTrue(summary["raw_runtime_values_redacted"])
        self.assertTrue(summary["owned_pointer_redacted"])
        self.assertTrue(summary["observed_bytes_redacted"])
        self.assertNotIn("layout_ptr", summary)
        self.assertNotIn("search_ptr", summary)
        self.assertEqual(private["layout_ptr"], f"0x{fake.heap_ptr:x}")
        expected_item_ptrs = [
            f"0x{fake.heap_ptr + offset:x}"
            for offset in repl.MATCH_STRING_ITEM_OFFSETS
        ]
        self.assertEqual(private["item_ptrs"], expected_item_ptrs)
        self.assertEqual(private["search_ptr"], f"0x{fake.heap_ptr + repl.MATCH_STRING_SEARCH_OFFSET:x}")
        expected_table = struct.pack(
            "<" + ("Q" * repl.MATCH_STRING_TABLE_ENTRY_COUNT),
            *(fake.heap_ptr + offset for offset in repl.MATCH_STRING_ITEM_OFFSETS),
            0,
        ) + (b"\xcc" * repl.MATCH_STRING_CANARY_LEN)
        expected_items = [
            (item + (b"\xcc" * repl.MATCH_STRING_CANARY_LEN)).hex()
            for item in repl.MATCH_STRING_ITEMS_BYTES
        ]
        expected_search = (
            repl.MATCH_STRING_SEARCH_BYTES + (b"\xcc" * repl.MATCH_STRING_CANARY_LEN)
        ).hex()
        expected_missing = (
            repl.MATCH_STRING_MISSING_BYTES + (b"\xcc" * repl.MATCH_STRING_CANARY_LEN)
        ).hex()
        self.assertEqual(private["expected_table_hex"], expected_table.hex())
        self.assertEqual(private["table_bytes_hex"], expected_table.hex())
        self.assertEqual(private["expected_item_hex"], expected_items)
        self.assertEqual(private["item_bytes_hex"], expected_items)
        self.assertEqual(private["expected_search_hex"], expected_search)
        self.assertEqual(private["expected_missing_search_hex"], expected_missing)
        self.assertEqual(private["missing_search_bytes_hex"], expected_missing)
        self.assertEqual(fake.freed, [fake.heap_ptr])

    def test_call_proof_sysfs_streq_passes_with_owned_strings_contract(self) -> None:
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
            "sysfs_streq",
            source_root=KERNEL_SOURCE_ROOT,
        )

        self.assertTrue(summary["ok"], summary)
        self.assertEqual(summary["decision"], "a90-repl-live-call-proof-sysfs_streq-pass")
        self.assertEqual(summary["proof_status"], "trusted-under-owned-input-contract")
        self.assertEqual(summary["function_map_entry"]["symbol"], "sysfs_streq")
        self.assertEqual(summary["function_map_entry"]["status"], "live-proven")
        self.assertEqual(
            summary["source_evidence"]["signature"],
            "extern bool sysfs_streq(const char *s1, const char *s2)",
        )
        self.assertEqual(summary["newline_left"], repl.SYSFS_STREQ_LEFT_NEWLINE_LABEL)
        self.assertEqual(summary["equal_left"], repl.SYSFS_STREQ_LEFT_EQUAL_LABEL)
        self.assertEqual(summary["equal_right"], repl.SYSFS_STREQ_RIGHT_EQUAL_LABEL)
        self.assertEqual(summary["mismatch_right"], repl.SYSFS_STREQ_RIGHT_MISMATCH_LABEL)
        self.assertEqual(summary["newline_expected_return_value"], "0x1")
        self.assertEqual(summary["newline_observed_return_value"], "0x1")
        self.assertEqual(summary["strict_equal_expected_return_value"], "0x1")
        self.assertEqual(summary["strict_equal_observed_return_value"], "0x1")
        self.assertEqual(summary["mismatch_expected_return_value"], "0x0")
        self.assertEqual(summary["mismatch_observed_return_value"], "0x0")
        self.assertTrue(summary["strings_unchanged_after_calls"])
        self.assertTrue(summary["raw_runtime_values_redacted"])
        self.assertTrue(summary["owned_pointer_redacted"])
        self.assertTrue(summary["observed_bytes_redacted"])
        self.assertNotIn("left_ptr", summary)
        self.assertNotIn("right_ptr", summary)
        self.assertEqual(private["left_ptr"], f"0x{fake.heap_ptr:x}")
        self.assertEqual(private["right_ptr"], f"0x{fake.heap_ptr + 0x1000:x}")
        expected_left_newline = (
            repl.SYSFS_STREQ_LEFT_NEWLINE_BYTES.ljust(repl.SYSFS_STREQ_PAYLOAD_LEN, b"\x00")
            + (b"\xcc" * repl.SYSFS_STREQ_CANARY_LEN)
        ).hex()
        expected_left_equal = (
            repl.SYSFS_STREQ_LEFT_EQUAL_BYTES.ljust(repl.SYSFS_STREQ_PAYLOAD_LEN, b"\x00")
            + (b"\xcc" * repl.SYSFS_STREQ_CANARY_LEN)
        ).hex()
        expected_right_equal = (
            repl.SYSFS_STREQ_RIGHT_EQUAL_BYTES.ljust(repl.SYSFS_STREQ_PAYLOAD_LEN, b"\x00")
            + (b"\xcc" * repl.SYSFS_STREQ_CANARY_LEN)
        ).hex()
        expected_right_mismatch = (
            repl.SYSFS_STREQ_RIGHT_MISMATCH_BYTES.ljust(repl.SYSFS_STREQ_PAYLOAD_LEN, b"\x00")
            + (b"\xcc" * repl.SYSFS_STREQ_CANARY_LEN)
        ).hex()
        self.assertEqual(private["expected_left_newline_hex"], expected_left_newline)
        self.assertEqual(private["expected_left_equal_hex"], expected_left_equal)
        self.assertEqual(private["expected_right_equal_hex"], expected_right_equal)
        self.assertEqual(private["expected_right_mismatch_hex"], expected_right_mismatch)
        self.assertEqual(private["left_bytes_hex"], expected_left_equal)
        self.assertEqual(private["right_bytes_hex"], expected_right_mismatch)
        self.assertEqual(fake.freed, [fake.heap_ptr, fake.heap_ptr + 0x1000])

    def test_call_proof_kstrdup_passes_with_owned_string_contract(self) -> None:
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
            "kstrdup",
            source_root=KERNEL_SOURCE_ROOT,
        )

        self.assertTrue(summary["ok"], summary)
        self.assertEqual(summary["decision"], "a90-repl-live-call-proof-kstrdup-pass")
        self.assertEqual(summary["proof_status"], "trusted-under-owned-input-contract")
        self.assertEqual(summary["function_map_entry"]["symbol"], "kstrdup")
        self.assertEqual(summary["function_map_entry"]["status"], "live-proven")
        self.assertEqual(
            summary["source_evidence"]["signature"],
            "extern char * kstrdup(const char *s, gfp_t gfp) __malloc",
        )
        self.assertEqual(summary["source_string"], repl.KSTRDUP_SOURCE_LABEL)
        self.assertTrue(summary["duplicate_matches_source"])
        self.assertTrue(summary["returned_owned_duplicate_pointer"])
        self.assertTrue(summary["duplicate_distinct_from_source"])
        self.assertTrue(summary["source_unchanged_after_call"])
        self.assertTrue(summary["raw_runtime_values_redacted"])
        self.assertTrue(summary["owned_pointer_redacted"])
        self.assertTrue(summary["observed_bytes_redacted"])
        self.assertNotIn("source_ptr", summary)
        self.assertNotIn("duplicate_ptr", summary)
        self.assertEqual(private["source_ptr"], f"0x{fake.heap_ptr:x}")
        self.assertEqual(private["duplicate_ptr"], f"0x{fake.heap_ptr + 0x1000:x}")
        expected_source = (
            repl.KSTRDUP_SOURCE_BYTES + (b"\xcc" * repl.KSTRDUP_CANARY_LEN)
        ).hex()
        expected_duplicate = repl.KSTRDUP_SOURCE_BYTES.hex()
        self.assertEqual(private["expected_source_hex"], expected_source)
        self.assertEqual(private["source_bytes_hex"], expected_source)
        self.assertEqual(private["expected_duplicate_hex"], expected_duplicate)
        self.assertEqual(private["duplicate_bytes_hex"], expected_duplicate)
        self.assertEqual(fake.freed, [fake.heap_ptr + 0x1000, fake.heap_ptr])

    def test_call_proof_kstrndup_passes_with_owned_bounded_string_contract(self) -> None:
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
            "kstrndup",
            source_root=KERNEL_SOURCE_ROOT,
        )

        self.assertTrue(summary["ok"], summary)
        self.assertEqual(summary["decision"], "a90-repl-live-call-proof-kstrndup-pass")
        self.assertEqual(summary["proof_status"], "trusted-under-owned-input-contract")
        self.assertEqual(summary["function_map_entry"]["symbol"], "kstrndup")
        self.assertEqual(summary["function_map_entry"]["status"], "live-proven")
        self.assertEqual(
            summary["source_evidence"]["signature"],
            "extern char * kstrndup(const char *s, size_t len, gfp_t gfp)",
        )
        self.assertEqual(summary["source_string"], repl.KSTRNDUP_SOURCE_LABEL)
        self.assertEqual(summary["bounded_len"], repl.KSTRNDUP_BOUND_LEN)
        self.assertEqual(summary["expected_duplicate_string"], repl.KSTRNDUP_BOUND_PREFIX_LABEL)
        self.assertTrue(summary["duplicate_matches_bounded_prefix"])
        self.assertTrue(summary["returned_owned_duplicate_pointer"])
        self.assertTrue(summary["duplicate_distinct_from_source"])
        self.assertTrue(summary["source_unchanged_after_call"])
        self.assertTrue(summary["raw_runtime_values_redacted"])
        self.assertTrue(summary["owned_pointer_redacted"])
        self.assertTrue(summary["observed_bytes_redacted"])
        self.assertNotIn("source_ptr", summary)
        self.assertNotIn("duplicate_ptr", summary)
        self.assertEqual(private["source_ptr"], f"0x{fake.heap_ptr:x}")
        self.assertEqual(private["duplicate_ptr"], f"0x{fake.heap_ptr + 0x1000:x}")
        expected_source = (
            repl.KSTRNDUP_SOURCE_BYTES + (b"\xcc" * repl.KSTRNDUP_CANARY_LEN)
        ).hex()
        expected_duplicate = repl.KSTRNDUP_EXPECTED_DUP_BYTES.hex()
        self.assertEqual(private["expected_source_hex"], expected_source)
        self.assertEqual(private["source_bytes_hex"], expected_source)
        self.assertEqual(private["expected_duplicate_hex"], expected_duplicate)
        self.assertEqual(private["duplicate_bytes_hex"], expected_duplicate)
        self.assertEqual(fake.freed, [fake.heap_ptr + 0x1000, fake.heap_ptr])

    def test_call_proof_kmemdup_passes_with_owned_raw_buffer_contract(self) -> None:
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
            "kmemdup",
            source_root=KERNEL_SOURCE_ROOT,
        )

        self.assertTrue(summary["ok"], summary)
        self.assertEqual(summary["decision"], "a90-repl-live-call-proof-kmemdup-pass")
        self.assertEqual(summary["proof_status"], "trusted-under-owned-input-contract")
        self.assertEqual(summary["function_map_entry"]["symbol"], "kmemdup")
        self.assertEqual(summary["function_map_entry"]["status"], "live-proven")
        self.assertEqual(
            summary["source_evidence"]["signature"],
            "extern void * kmemdup(const void *src, size_t len, gfp_t gfp)",
        )
        self.assertEqual(summary["source_payload"], repl.KMEMDUP_SOURCE_LABEL)
        self.assertEqual(summary["copy_len"], repl.KMEMDUP_COPY_LEN)
        self.assertTrue(summary["duplicate_matches_source_bytes"])
        self.assertTrue(summary["returned_owned_duplicate_pointer"])
        self.assertTrue(summary["duplicate_distinct_from_source"])
        self.assertTrue(summary["source_unchanged_after_call"])
        self.assertTrue(summary["raw_runtime_values_redacted"])
        self.assertTrue(summary["owned_pointer_redacted"])
        self.assertTrue(summary["observed_bytes_redacted"])
        self.assertNotIn("source_ptr", summary)
        self.assertNotIn("duplicate_ptr", summary)
        self.assertEqual(private["source_ptr"], f"0x{fake.heap_ptr:x}")
        self.assertEqual(private["duplicate_ptr"], f"0x{fake.heap_ptr + 0x1000:x}")
        expected_source = (
            repl.KMEMDUP_SOURCE_BYTES + (b"\xcc" * repl.KMEMDUP_CANARY_LEN)
        ).hex()
        expected_duplicate = repl.KMEMDUP_SOURCE_BYTES.hex()
        self.assertEqual(private["expected_source_hex"], expected_source)
        self.assertEqual(private["source_bytes_hex"], expected_source)
        self.assertEqual(private["expected_duplicate_hex"], expected_duplicate)
        self.assertEqual(private["duplicate_bytes_hex"], expected_duplicate)
        self.assertEqual(fake.freed, [fake.heap_ptr + 0x1000, fake.heap_ptr])

    def test_call_proof_kmemdup_nul_passes_with_owned_raw_buffer_contract(self) -> None:
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
            "kmemdup_nul",
            source_root=KERNEL_SOURCE_ROOT,
        )

        self.assertTrue(summary["ok"], summary)
        self.assertEqual(summary["decision"], "a90-repl-live-call-proof-kmemdup_nul-pass")
        self.assertEqual(summary["proof_status"], "trusted-under-owned-input-contract")
        self.assertEqual(summary["function_map_entry"]["symbol"], "kmemdup_nul")
        self.assertEqual(summary["function_map_entry"]["status"], "live-proven")
        self.assertEqual(
            summary["source_evidence"]["signature"],
            "extern char * kmemdup_nul(const char *s, size_t len, gfp_t gfp)",
        )
        self.assertEqual(summary["source_payload"], repl.KMEMDUP_NUL_SOURCE_LABEL)
        self.assertEqual(summary["copy_len"], repl.KMEMDUP_NUL_COPY_LEN)
        self.assertTrue(summary["duplicate_matches_source_bytes_plus_nul"])
        self.assertTrue(summary["generated_trailing_nul"])
        self.assertTrue(summary["source_after_len_byte_not_copied"])
        self.assertTrue(summary["returned_owned_duplicate_pointer"])
        self.assertTrue(summary["duplicate_distinct_from_source"])
        self.assertTrue(summary["source_unchanged_after_call"])
        self.assertTrue(summary["raw_runtime_values_redacted"])
        self.assertTrue(summary["owned_pointer_redacted"])
        self.assertTrue(summary["observed_bytes_redacted"])
        self.assertNotIn("source_ptr", summary)
        self.assertNotIn("duplicate_ptr", summary)
        self.assertEqual(private["source_ptr"], f"0x{fake.heap_ptr:x}")
        self.assertEqual(private["duplicate_ptr"], f"0x{fake.heap_ptr + 0x1000:x}")
        expected_source = (
            repl.KMEMDUP_NUL_SOURCE_BYTES
            + repl.KMEMDUP_NUL_SOURCE_AFTER_LEN_BYTE
            + (b"\xcc" * repl.KMEMDUP_NUL_CANARY_LEN)
        ).hex()
        expected_duplicate = repl.KMEMDUP_NUL_EXPECTED_DUP_BYTES.hex()
        self.assertEqual(private["expected_source_hex"], expected_source)
        self.assertEqual(private["source_bytes_hex"], expected_source)
        self.assertEqual(private["expected_duplicate_hex"], expected_duplicate)
        self.assertEqual(private["duplicate_bytes_hex"], expected_duplicate)
        self.assertEqual(fake.freed, [fake.heap_ptr + 0x1000, fake.heap_ptr])

    def test_call_proof_strpbrk_passes_with_owned_strings_contract(self) -> None:
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
            "strpbrk",
            source_root=KERNEL_SOURCE_ROOT,
        )

        self.assertTrue(summary["ok"], summary)
        self.assertEqual(summary["decision"], "a90-repl-live-call-proof-strpbrk-pass")
        self.assertEqual(summary["proof_status"], "trusted-under-owned-input-contract")
        self.assertEqual(summary["function_map_entry"]["symbol"], "strpbrk")
        self.assertEqual(summary["function_map_entry"]["status"], "live-proven")
        self.assertEqual(
            summary["source_evidence"]["signature"],
            "extern char * strpbrk(const char *,const char *)",
        )
        self.assertEqual(summary["haystack"], repl.STRPBRK_HAYSTACK_LABEL)
        self.assertEqual(summary["accept_set"], repl.STRPBRK_ACCEPT_LABEL)
        self.assertEqual(summary["missing_accept_set"], repl.STRPBRK_MISSING_LABEL)
        self.assertEqual(summary["expected_hit_offset"], repl.STRPBRK_EXPECTED_OFFSET)
        self.assertEqual(
            summary["hit_expected_return_value"],
            "owned-haystack-pointer-plus-offset-redacted",
        )
        self.assertEqual(
            summary["hit_observed_return_value"],
            "owned-haystack-pointer-plus-offset-redacted",
        )
        self.assertTrue(summary["hit_return_matches_expected_offset"])
        self.assertEqual(summary["missing_expected_return_value"], "0x0")
        self.assertEqual(summary["missing_observed_return_value"], "0x0")
        self.assertTrue(summary["strings_unchanged_after_calls"])
        self.assertTrue(summary["raw_runtime_values_redacted"])
        self.assertTrue(summary["owned_pointer_redacted"])
        self.assertTrue(summary["observed_bytes_redacted"])
        self.assertNotIn("haystack_ptr", summary)
        self.assertNotIn("accept_ptr", summary)
        self.assertNotIn("hit_return_ptr", summary)
        self.assertEqual(private["haystack_ptr"], f"0x{fake.heap_ptr:x}")
        self.assertEqual(private["accept_ptr"], f"0x{fake.heap_ptr + 0x1000:x}")
        self.assertEqual(
            private["hit_return_ptr"],
            f"0x{fake.heap_ptr + repl.STRPBRK_EXPECTED_OFFSET:x}",
        )
        expected_haystack_hex = (
            repl.STRPBRK_HAYSTACK_BYTES + (b"\xcc" * repl.STRPBRK_CANARY_LEN)
        ).hex()
        expected_hit_accept_hex = (
            repl.STRPBRK_ACCEPT_BYTES + (b"\xcc" * repl.STRPBRK_CANARY_LEN)
        ).hex()
        expected_missing_accept_hex = (
            repl.STRPBRK_MISSING_BYTES + (b"\xcc" * repl.STRPBRK_CANARY_LEN)
        ).hex()
        self.assertEqual(private["expected_haystack_hex"], expected_haystack_hex)
        self.assertEqual(private["expected_hit_accept_hex"], expected_hit_accept_hex)
        self.assertEqual(private["expected_missing_accept_hex"], expected_missing_accept_hex)
        self.assertEqual(private["haystack_bytes_hex"], expected_haystack_hex)
        self.assertEqual(private["accept_bytes_hex"], expected_missing_accept_hex)
        self.assertEqual(fake.freed, [fake.heap_ptr, fake.heap_ptr + 0x1000])

    def test_call_proof_strspn_passes_with_owned_strings_contract(self) -> None:
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
            "strspn",
            source_root=KERNEL_SOURCE_ROOT,
        )

        self.assertTrue(summary["ok"], summary)
        self.assertEqual(summary["decision"], "a90-repl-live-call-proof-strspn-pass")
        self.assertEqual(summary["proof_status"], "trusted-under-owned-input-contract")
        self.assertEqual(summary["function_map_entry"]["symbol"], "strspn")
        self.assertEqual(summary["function_map_entry"]["status"], "live-proven")
        self.assertEqual(
            summary["source_evidence"]["signature"],
            "extern __kernel_size_t strspn(const char *,const char *)",
        )
        self.assertEqual(summary["haystack"], repl.STRSPN_HAYSTACK_LABEL)
        self.assertEqual(summary["prefix_accept_set"], repl.STRSPN_PREFIX_ACCEPT_LABEL)
        self.assertEqual(summary["full_accept_set"], repl.STRSPN_FULL_ACCEPT_LABEL)
        self.assertEqual(summary["expected_prefix_return_value"], repl.STRSPN_EXPECTED_PREFIX_LEN)
        self.assertEqual(summary["prefix_observed_return_value"], repl.STRSPN_EXPECTED_PREFIX_LEN)
        self.assertTrue(summary["prefix_return_matches_expected_length"])
        self.assertEqual(summary["full_expected_return_value"], repl.STRSPN_EXPECTED_FULL_LEN)
        self.assertEqual(summary["full_observed_return_value"], repl.STRSPN_EXPECTED_FULL_LEN)
        self.assertTrue(summary["full_return_matches_haystack_length"])
        self.assertTrue(summary["strings_unchanged_after_calls"])
        self.assertTrue(summary["raw_runtime_values_redacted"])
        self.assertTrue(summary["owned_pointer_redacted"])
        self.assertTrue(summary["observed_bytes_redacted"])
        self.assertNotIn("haystack_ptr", summary)
        self.assertNotIn("accept_ptr", summary)
        self.assertEqual(private["haystack_ptr"], f"0x{fake.heap_ptr:x}")
        self.assertEqual(private["accept_ptr"], f"0x{fake.heap_ptr + 0x1000:x}")
        expected_haystack_hex = (
            repl.STRSPN_HAYSTACK_BYTES + (b"\xcc" * repl.STRSPN_CANARY_LEN)
        ).hex()
        expected_prefix_accept_hex = (
            repl.STRSPN_PREFIX_ACCEPT_BYTES + (b"\xcc" * repl.STRSPN_CANARY_LEN)
        ).hex()
        expected_full_accept_hex = (
            repl.STRSPN_FULL_ACCEPT_BYTES + (b"\xcc" * repl.STRSPN_CANARY_LEN)
        ).hex()
        self.assertEqual(private["expected_haystack_hex"], expected_haystack_hex)
        self.assertEqual(private["expected_prefix_accept_hex"], expected_prefix_accept_hex)
        self.assertEqual(private["expected_full_accept_hex"], expected_full_accept_hex)
        self.assertEqual(private["haystack_bytes_hex"], expected_haystack_hex)
        self.assertEqual(private["accept_bytes_hex"], expected_full_accept_hex)
        self.assertEqual(fake.freed, [fake.heap_ptr, fake.heap_ptr + 0x1000])

    def test_call_proof_strcspn_passes_with_owned_strings_contract(self) -> None:
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
            "strcspn",
            source_root=KERNEL_SOURCE_ROOT,
        )

        self.assertTrue(summary["ok"], summary)
        self.assertEqual(summary["decision"], "a90-repl-live-call-proof-strcspn-pass")
        self.assertEqual(summary["proof_status"], "trusted-under-owned-input-contract")
        self.assertEqual(summary["function_map_entry"]["symbol"], "strcspn")
        self.assertEqual(summary["function_map_entry"]["status"], "live-proven")
        self.assertEqual(
            summary["source_evidence"]["signature"],
            "extern __kernel_size_t strcspn(const char *,const char *)",
        )
        self.assertEqual(summary["haystack"], repl.STRCSPN_HAYSTACK_LABEL)
        self.assertEqual(summary["reject_set"], repl.STRCSPN_REJECT_LABEL)
        self.assertEqual(summary["missing_reject_set"], repl.STRCSPN_MISSING_LABEL)
        self.assertEqual(summary["expected_hit_return_value"], repl.STRCSPN_EXPECTED_OFFSET)
        self.assertEqual(summary["hit_observed_return_value"], repl.STRCSPN_EXPECTED_OFFSET)
        self.assertTrue(summary["hit_return_matches_expected_offset"])
        self.assertEqual(summary["missing_expected_return_value"], repl.STRCSPN_EXPECTED_MISSING_LEN)
        self.assertEqual(summary["missing_observed_return_value"], repl.STRCSPN_EXPECTED_MISSING_LEN)
        self.assertTrue(summary["missing_return_matches_haystack_length"])
        self.assertTrue(summary["strings_unchanged_after_calls"])
        self.assertTrue(summary["raw_runtime_values_redacted"])
        self.assertTrue(summary["owned_pointer_redacted"])
        self.assertTrue(summary["observed_bytes_redacted"])
        self.assertNotIn("haystack_ptr", summary)
        self.assertNotIn("reject_ptr", summary)
        self.assertEqual(private["haystack_ptr"], f"0x{fake.heap_ptr:x}")
        self.assertEqual(private["reject_ptr"], f"0x{fake.heap_ptr + 0x1000:x}")
        expected_haystack_hex = (
            repl.STRCSPN_HAYSTACK_BYTES + (b"\xcc" * repl.STRCSPN_CANARY_LEN)
        ).hex()
        expected_hit_reject_hex = (
            repl.STRCSPN_REJECT_BYTES + (b"\xcc" * repl.STRCSPN_CANARY_LEN)
        ).hex()
        expected_missing_reject_hex = (
            repl.STRCSPN_MISSING_BYTES + (b"\xcc" * repl.STRCSPN_CANARY_LEN)
        ).hex()
        self.assertEqual(private["expected_haystack_hex"], expected_haystack_hex)
        self.assertEqual(private["expected_hit_reject_hex"], expected_hit_reject_hex)
        self.assertEqual(private["expected_missing_reject_hex"], expected_missing_reject_hex)
        self.assertEqual(private["haystack_bytes_hex"], expected_haystack_hex)
        self.assertEqual(private["reject_bytes_hex"], expected_missing_reject_hex)
        self.assertEqual(fake.freed, [fake.heap_ptr, fake.heap_ptr + 0x1000])

    def test_call_proof_strcmp_passes_with_owned_strings_contract(self) -> None:
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
            "strcmp",
            source_root=KERNEL_SOURCE_ROOT,
        )

        self.assertTrue(summary["ok"], summary)
        self.assertEqual(summary["decision"], "a90-repl-live-call-proof-strcmp-pass")
        self.assertEqual(summary["proof_status"], "trusted-under-owned-input-contract")
        self.assertEqual(summary["function_map_entry"]["symbol"], "strcmp")
        self.assertEqual(summary["function_map_entry"]["status"], "live-proven")
        self.assertEqual(
            summary["source_evidence"]["signature"],
            "extern int strcmp(const char *,const char *)",
        )
        self.assertEqual(summary["proof_string"], repl.STRCMP_PROOF_LABEL)
        self.assertEqual(summary["equal_expected_return_value"], "0x0")
        self.assertEqual(summary["equal_observed_return_value"], "0x0")
        self.assertEqual(summary["mismatch_expected_return_sign"], "positive")
        self.assertGreater(int(str(summary["mismatch_observed_return_value"]), 16), 0)
        self.assertEqual(summary["mismatch_offset"], repl.STRCMP_MISMATCH_OFFSET)
        self.assertTrue(summary["strings_unchanged_after_calls"])
        self.assertTrue(summary["raw_runtime_values_redacted"])
        self.assertTrue(summary["owned_pointer_redacted"])
        self.assertTrue(summary["observed_bytes_redacted"])
        self.assertNotIn("left_ptr", summary)
        self.assertNotIn("right_ptr", summary)
        self.assertEqual(private["left_ptr"], f"0x{fake.heap_ptr:x}")
        self.assertEqual(private["right_ptr"], f"0x{fake.heap_ptr + 0x1000:x}")
        expected_left_hex = (repl.STRCMP_PROOF_BYTES + (b"\xcc" * repl.STRCMP_CANARY_LEN)).hex()
        self.assertEqual(private["left_bytes_hex"], expected_left_hex)
        self.assertEqual(private["right_equal_bytes_hex"], expected_left_hex)
        right_mismatch = bytearray(repl.STRCMP_PROOF_BYTES)
        right_mismatch[repl.STRCMP_MISMATCH_OFFSET] = repl.STRCMP_MISMATCH_RIGHT_BYTE
        expected_right_mismatch_hex = (
            bytes(right_mismatch) + (b"\xcc" * repl.STRCMP_CANARY_LEN)
        ).hex()
        self.assertEqual(private["right_mismatch_bytes_hex"], expected_right_mismatch_hex)
        self.assertEqual(fake.freed, [fake.heap_ptr, fake.heap_ptr + 0x1000])

    def test_call_proof_strcasecmp_passes_with_owned_strings_contract(self) -> None:
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
            "strcasecmp",
            source_root=KERNEL_SOURCE_ROOT,
        )

        self.assertTrue(summary["ok"], summary)
        self.assertEqual(summary["decision"], "a90-repl-live-call-proof-strcasecmp-pass")
        self.assertEqual(summary["proof_status"], "trusted-under-owned-input-contract")
        self.assertEqual(summary["function_map_entry"]["symbol"], "strcasecmp")
        self.assertEqual(summary["function_map_entry"]["status"], "live-proven")
        self.assertEqual(
            summary["source_evidence"]["signature"],
            "extern int strcasecmp(const char *s1, const char *s2)",
        )
        self.assertEqual(summary["left_string"], repl.STRCASECMP_PROOF_LABEL)
        self.assertEqual(summary["casefold_equal_right_string"], "a90strcasecmp-proof-zz")
        self.assertEqual(summary["equal_expected_return_value"], "0x0")
        self.assertEqual(summary["equal_observed_return_value"], "0x0")
        self.assertEqual(summary["mismatch_expected_return_sign"], "positive")
        self.assertGreater(int(str(summary["mismatch_observed_return_value"]), 16), 0)
        self.assertEqual(summary["mismatch_offset"], repl.STRCASECMP_MISMATCH_OFFSET)
        self.assertTrue(summary["strings_unchanged_after_calls"])
        self.assertTrue(summary["raw_runtime_values_redacted"])
        self.assertTrue(summary["owned_pointer_redacted"])
        self.assertTrue(summary["observed_bytes_redacted"])
        self.assertNotIn("left_ptr", summary)
        self.assertNotIn("right_ptr", summary)
        self.assertEqual(private["left_ptr"], f"0x{fake.heap_ptr:x}")
        self.assertEqual(private["right_ptr"], f"0x{fake.heap_ptr + 0x1000:x}")
        expected_left_hex = (repl.STRCASECMP_LEFT_BYTES + (b"\xcc" * repl.STRCASECMP_CANARY_LEN)).hex()
        expected_right_equal_hex = (
            repl.STRCASECMP_RIGHT_EQUAL_BYTES + (b"\xcc" * repl.STRCASECMP_CANARY_LEN)
        ).hex()
        right_mismatch = bytearray(repl.STRCASECMP_RIGHT_EQUAL_BYTES)
        right_mismatch[repl.STRCASECMP_MISMATCH_OFFSET] = repl.STRCASECMP_MISMATCH_RIGHT_BYTE
        expected_right_mismatch_hex = (
            bytes(right_mismatch) + (b"\xcc" * repl.STRCASECMP_CANARY_LEN)
        ).hex()
        self.assertEqual(private["expected_left_hex"], expected_left_hex)
        self.assertEqual(private["expected_right_equal_hex"], expected_right_equal_hex)
        self.assertEqual(private["expected_right_mismatch_hex"], expected_right_mismatch_hex)
        self.assertEqual(private["left_bytes_hex"], expected_left_hex)
        self.assertEqual(private["right_equal_bytes_hex"], expected_right_equal_hex)
        self.assertEqual(private["right_mismatch_bytes_hex"], expected_right_mismatch_hex)
        self.assertEqual(fake.freed, [fake.heap_ptr, fake.heap_ptr + 0x1000])

    def test_call_proof_strncasecmp_passes_with_owned_strings_contract(self) -> None:
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
            "strncasecmp",
            source_root=KERNEL_SOURCE_ROOT,
        )

        self.assertTrue(summary["ok"], summary)
        self.assertEqual(summary["decision"], "a90-repl-live-call-proof-strncasecmp-pass")
        self.assertEqual(summary["proof_status"], "trusted-under-owned-input-contract")
        self.assertEqual(summary["function_map_entry"]["symbol"], "strncasecmp")
        self.assertEqual(summary["function_map_entry"]["status"], "live-proven")
        self.assertEqual(
            summary["source_evidence"]["signature"],
            "extern int strncasecmp(const char *s1, const char *s2, size_t n)",
        )
        self.assertEqual(summary["proof_left_prefix"], repl.STRNCASECMP_LEFT_PREFIX_BYTES.decode("ascii"))
        self.assertEqual(summary["proof_right_prefix"], repl.STRNCASECMP_RIGHT_PREFIX_BYTES.decode("ascii"))
        self.assertEqual(summary["count_arg"], repl.STRNCASECMP_PROOF_COUNT)
        self.assertEqual(summary["equal_expected_return_value"], "0x0")
        self.assertEqual(summary["equal_observed_return_value"], "0x0")
        self.assertTrue(summary["bounded_casefold_equal_ignores_post_count_difference"])
        self.assertEqual(summary["mismatch_expected_return_sign"], "positive")
        self.assertGreater(int(str(summary["mismatch_observed_return_value"]), 16), 0)
        self.assertEqual(summary["mismatch_offset"], repl.STRNCASECMP_MISMATCH_OFFSET)
        self.assertTrue(summary["strings_unchanged_after_calls"])
        self.assertTrue(summary["raw_runtime_values_redacted"])
        self.assertTrue(summary["owned_pointer_redacted"])
        self.assertTrue(summary["observed_bytes_redacted"])
        self.assertNotIn("left_ptr", summary)
        self.assertNotIn("right_ptr", summary)
        self.assertEqual(private["left_ptr"], f"0x{fake.heap_ptr:x}")
        self.assertEqual(private["right_ptr"], f"0x{fake.heap_ptr + 0x1000:x}")
        scan_payload_len = max(len(repl.STRNCASECMP_LEFT_BYTES), len(repl.STRNCASECMP_RIGHT_EQUAL_BYTES))
        expected_left_hex = (
            repl.STRNCASECMP_LEFT_BYTES.ljust(scan_payload_len, b"\x00")
            + (b"\xcc" * repl.STRNCASECMP_CANARY_LEN)
        ).hex()
        expected_right_equal_hex = (
            repl.STRNCASECMP_RIGHT_EQUAL_BYTES.ljust(scan_payload_len, b"\x00")
            + (b"\xcc" * repl.STRNCASECMP_CANARY_LEN)
        ).hex()
        right_mismatch = bytearray(repl.STRNCASECMP_RIGHT_EQUAL_BYTES)
        right_mismatch[repl.STRNCASECMP_MISMATCH_OFFSET] = repl.STRNCASECMP_MISMATCH_RIGHT_BYTE
        expected_right_mismatch_hex = (
            bytes(right_mismatch).ljust(scan_payload_len, b"\x00")
            + (b"\xcc" * repl.STRNCASECMP_CANARY_LEN)
        ).hex()
        self.assertEqual(private["expected_left_hex"], expected_left_hex)
        self.assertEqual(private["expected_right_equal_hex"], expected_right_equal_hex)
        self.assertEqual(private["expected_right_mismatch_hex"], expected_right_mismatch_hex)
        self.assertEqual(private["left_bytes_hex"], expected_left_hex)
        self.assertEqual(private["right_equal_bytes_hex"], expected_right_equal_hex)
        self.assertEqual(private["right_mismatch_bytes_hex"], expected_right_mismatch_hex)
        self.assertEqual(fake.freed, [fake.heap_ptr, fake.heap_ptr + 0x1000])

    def test_call_proof_strncmp_passes_with_owned_strings_contract(self) -> None:
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
            "strncmp",
            source_root=KERNEL_SOURCE_ROOT,
        )

        self.assertTrue(summary["ok"], summary)
        self.assertEqual(summary["decision"], "a90-repl-live-call-proof-strncmp-pass")
        self.assertEqual(summary["proof_status"], "trusted-under-owned-input-contract")
        self.assertEqual(summary["function_map_entry"]["symbol"], "strncmp")
        self.assertEqual(summary["function_map_entry"]["status"], "live-proven")
        self.assertEqual(
            summary["source_evidence"]["signature"],
            "extern int strncmp(const char *,const char *,__kernel_size_t)",
        )
        self.assertEqual(summary["proof_prefix"], repl.STRNCMP_PREFIX_BYTES.decode("ascii"))
        self.assertEqual(summary["count_arg"], repl.STRNCMP_PROOF_COUNT)
        self.assertEqual(summary["equal_expected_return_value"], "0x0")
        self.assertEqual(summary["equal_observed_return_value"], "0x0")
        self.assertTrue(summary["bounded_equal_ignores_post_count_difference"])
        self.assertEqual(summary["mismatch_expected_return_sign"], "positive")
        self.assertGreater(int(str(summary["mismatch_observed_return_value"]), 16), 0)
        self.assertEqual(summary["mismatch_offset"], repl.STRNCMP_MISMATCH_OFFSET)
        self.assertTrue(summary["strings_unchanged_after_calls"])
        self.assertTrue(summary["raw_runtime_values_redacted"])
        self.assertTrue(summary["owned_pointer_redacted"])
        self.assertTrue(summary["observed_bytes_redacted"])
        self.assertNotIn("left_ptr", summary)
        self.assertNotIn("right_ptr", summary)
        self.assertEqual(private["left_ptr"], f"0x{fake.heap_ptr:x}")
        self.assertEqual(private["right_ptr"], f"0x{fake.heap_ptr + 0x1000:x}")
        scan_payload_len = max(len(repl.STRNCMP_LEFT_BYTES), len(repl.STRNCMP_RIGHT_EQUAL_BYTES))
        expected_left_hex = (
            repl.STRNCMP_LEFT_BYTES.ljust(scan_payload_len, b"\x00")
            + (b"\xcc" * repl.STRNCMP_CANARY_LEN)
        ).hex()
        expected_right_equal_hex = (
            repl.STRNCMP_RIGHT_EQUAL_BYTES.ljust(scan_payload_len, b"\x00")
            + (b"\xcc" * repl.STRNCMP_CANARY_LEN)
        ).hex()
        right_mismatch = bytearray(repl.STRNCMP_RIGHT_EQUAL_BYTES)
        right_mismatch[repl.STRNCMP_MISMATCH_OFFSET] = repl.STRNCMP_MISMATCH_RIGHT_BYTE
        expected_right_mismatch_hex = (
            bytes(right_mismatch).ljust(scan_payload_len, b"\x00")
            + (b"\xcc" * repl.STRNCMP_CANARY_LEN)
        ).hex()
        self.assertEqual(private["left_bytes_hex"], expected_left_hex)
        self.assertEqual(private["right_equal_bytes_hex"], expected_right_equal_hex)
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

    def test_call_proof_memset_passes_with_owned_destination_contract(self) -> None:
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
            "memset",
            source_root=KERNEL_SOURCE_ROOT,
        )

        self.assertTrue(summary["ok"], summary)
        self.assertEqual(summary["decision"], "a90-repl-live-call-proof-memset-pass")
        self.assertEqual(summary["proof_status"], "trusted-under-owned-input-contract")
        self.assertEqual(summary["function_map_entry"]["symbol"], "memset")
        self.assertEqual(summary["function_map_entry"]["status"], "live-proven")
        self.assertEqual(
            summary["source_evidence"]["signature"],
            "extern void * memset(void *,int,__kernel_size_t)",
        )
        self.assertEqual(summary["size_arg"], repl.MEMSET_PROOF_SIZE)
        self.assertEqual(summary["fill_byte"], f"0x{repl.MEMSET_PROOF_BYTE:02x}")
        self.assertEqual(summary["initial_byte"], f"0x{repl.MEMSET_INITIAL_BYTE:02x}")
        self.assertEqual(summary["expected_return_value"], "owned-destination-pointer-redacted")
        self.assertEqual(summary["observed_return_value"], "owned-destination-pointer-redacted")
        self.assertTrue(summary["return_matches_destination"])
        self.assertTrue(summary["post_size_canary_preserved"])
        self.assertTrue(summary["raw_runtime_values_redacted"])
        self.assertTrue(summary["owned_pointer_redacted"])
        self.assertTrue(summary["observed_bytes_redacted"])
        self.assertNotIn("dst_ptr", summary)
        self.assertNotIn("return_ptr", summary)
        self.assertEqual(private["dst_ptr"], f"0x{fake.heap_ptr:x}")
        self.assertEqual(private["return_ptr"], f"0x{fake.heap_ptr:x}")
        expected_before_hex = (
            bytes([repl.MEMSET_INITIAL_BYTE]) * repl.MEMSET_PROOF_SIZE
            + (b"\xcc" * repl.MEMSET_CANARY_LEN)
        ).hex()
        expected_after_hex = (
            bytes([repl.MEMSET_PROOF_BYTE]) * repl.MEMSET_PROOF_SIZE
            + (b"\xcc" * repl.MEMSET_CANARY_LEN)
        ).hex()
        self.assertEqual(private["observed_before_hex"], expected_before_hex)
        self.assertEqual(private["observed_after_hex"], expected_after_hex)
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
