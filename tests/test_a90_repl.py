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

        kfree = self._row("kfree")
        self.assertEqual(kfree["tier"], repl.CALL_SAFETY_SAFE_SCALAR)
        self.assertTrue(kfree["safe_group"])
        self.assertEqual(kfree["resolution"]["link_vaddr"], "0xffffff800826b354")
        self.assertEqual(kfree["signals"]["arg_pointer_derefs_before_first_bl_or_ret"], [])

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
        self.assertGreaterEqual(summary["counts"][repl.CALL_SAFETY_SAFE_SCALAR], 2)
        self.assertGreaterEqual(summary["counts"][repl.CALL_SAFETY_SAFE_WITH_VALID_PTR], 5)
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
        self.heap_ptr = 0xFFFFFFC012300000
        self.heap: dict[int, int] = {}
        self.freed: list[int] = []
        self.op_count = 0

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
            if arg0 == kmalloc:
                lines.append(f"A90R{self.heap_ptr:x}")
            elif arg0 == kfree:
                self.freed.append(arg1)
                lines.append("A90R0")
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

    def test_poke_roundtrip_rejects_non_lowmem_alloc(self) -> None:
        fake = FaithfulFakeTransport(0x130000, self.symbols, self.image)
        fake.heap_ptr = 0x12345000
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
