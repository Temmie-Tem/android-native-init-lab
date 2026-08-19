import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / (
    "docs/reports/"
    "S22PLUS_FYG8_P319_STOCK_USERSPACE_CHOREOGRAPHY_H0_2026-08-19.md"
)
LEDGER = ROOT / "docs/operations/CAMPAIGN_LEDGER_S22PLUS.md"


class P319StockChoreographyDocsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = REPORT.read_text(encoding="utf-8")

    SECTION_ORDER = (
        "Why this unit exists",
        "What was read",
        "The stock chain, resolved to this unit's actual values",
        "Stock gadget versus the candidate's",
        "Four candidate causes this unit refutes",
        "A stale path in the stock HAL, and the real role knob",
        "The second MUIC interface",
        "What this changes about the frontier",
        "The measurement was taken, and two claims above need correcting",
        "The P3.17 plan against the first stage, and what it omits on purpose",
        "The complete CONTROL1 writer graph",
        "The role-to-pull-up chain, traced",
        "The module identity question is closed, and it closes wider than asked",
        "The bootloader, which was available all along",
        "What remains open",
        "Evidence",
    )

    def test_report_reads_in_order_rather_than_in_discovery_order(self):
        # This report was first written by appending each unit's findings, which
        # left "What remains open" mid-document with five closing sections after
        # it and put conclusions ahead of the corrections that withdrew them.
        # Pinning the order stops that shape from coming back.
        found = re.findall(r"^## (.+)$", self.report, re.MULTILINE)
        self.assertEqual(tuple(found), self.SECTION_ORDER)

    def test_open_and_evidence_are_the_last_two_sections(self):
        found = re.findall(r"^## (.+)$", self.report, re.MULTILINE)
        self.assertEqual(found[-2:], ["What remains open", "Evidence"])

    def test_no_section_points_forward(self):
        # A backward reference survives reordering; a forward one does not.
        for phrase in ("section below", "Closed below", "the trace below", "see below"):
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, self.report)

    def test_open_list_carries_no_struck_through_backlog(self):
        section = re.search(
            r"^## What remains open$(.*?)(?=^## )",
            self.report,
            re.MULTILINE | re.DOTALL,
        )
        self.assertIsNotNone(section)
        self.assertNotIn("~~", section.group(1))
        items = re.findall(r"^- ", section.group(1), re.MULTILINE)
        self.assertEqual(len(items), 3)
        self.assertNotIn("holds no analysable BL", section.group(1))

    def test_report_states_the_h0_only_authority_boundary(self):
        for token in (
            "IMPLEMENTED_REVIEW_PENDING",
            "NO DEVICE OR LIVE AUTHORITY",
            "creates no D0, D1, F1, recovery, replay, device,\nor live authority",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_pins_the_three_properties_that_select_the_path(self):
        # The chain is only reproducible if the branch conditions are pinned
        # to this unit's values rather than assumed from the generic vendor rc.
        for token in (
            "vendor.usb.use_gadget_hal=0",
            "vendor/build.prop:326",
            "vendor.usb.controller=a600000.dwc3",
            "init.target.rc:130",
            "androidboot.usbcontroller=a600000.dwc3",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_states_the_udc_bind_ordering_gate(self):
        self.assertIn(
            "the UDC bind\nis gated on a userspace daemon having already opened "
            "the function's endpoints.",
            self.report,
        )
        self.assertIn("sys.usb.ffs.ready", self.report)

    def test_report_records_the_inert_aosp_usb_rc(self):
        for token in (
            "entirely gated on `sys.usb.configfs=0`",
            "is therefore inert here",
            "on property:init.svc.adbd=stopped",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def refutation_section(self):
        section = re.search(
            r"^## (\w+) candidate causes this unit refutes$(.*?)(?=^## )",
            self.report,
            re.MULTILINE | re.DOTALL,
        )
        self.assertIsNotNone(section, "refutation section missing")
        return section.group(1), re.findall(
            r"^\*\*\d\. ", section.group(2), re.MULTILINE
        )

    def test_refutation_count_matches_its_own_numbered_items(self):
        word, items = self.refutation_section()
        self.assertEqual(word, "Four")
        self.assertEqual(len(items), 4)

    def test_each_refutation_carries_a_binary_level_anchor(self):
        # A refutation from the source alone would not survive a config change;
        # each of these is anchored in a shipped .ko or an initialiser.
        for token in (
            "has no `pmic_info`, `charging_mode`, or\n`ccic_info` symbol",
            "carries no bare `lpcharge` or\n`factory_mode` symbol",
            "`set_gpio_usb_sel` is never assigned anywhere in the tree",
            "`usb_notify_sysfs.c:1260` sets\n`udev->usb_data_enabled = 1`",
            "`is_blocked` returns false on a NULL `otg_notify`",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_records_the_module_parameter_mechanism_and_why_it_is_benign(self):
        for token in (
            "muic_param_pmic_info=3",
            "There\nis no `modules.options` anywhere",
            "`insmod` does\nnot do this",
            "-1 & 0xfff = 0xfff",
            "the same result as the stock value\nof 3",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_corrects_the_three_nonexistent_hal_paths(self):
        for token in (
            "**None of the three exists in this kernel.**",
            "`b_sess`\ndoes not appear anywhere under `drivers/`",
            "The HAL is named for `coral`, a Pixel",
            "`orientation`, `mode`, `speed`, `bus_vote`",
            "The review's `a600000.ssusb/mode`\nis real",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_does_not_present_usb_sel_as_a_switch(self):
        self.assertIn("**It issues no I²C.**", self.report)
        self.assertIn("it does not move the mux", self.report)

    def test_report_names_the_next_measurement_as_a_read(self):
        self.assertIn(
            "cat /sys/bus/platform/devices/a600000.ssusb/mode", self.report
        )
        self.assertIn("has no side effect", self.report)
        self.assertIn(
            "strictly weaker action than the Stage B\nregister read", self.report
        )
        # The body first described mode as the controller's actual current role.
        self.assertIn(
            "It returns the role the driver has been told to take, not the\n"
            "controller's negotiated state",
            self.report,
        )
        self.assertNotIn("returns the controller's actual current role.", self.report)

    def test_report_keeps_the_ss_mon_question_open_rather_than_answering_it(self):
        self.assertIn(
            "Whether it is required for the pull-up is not\nestablished here",
            self.report,
        )

    def test_report_records_the_measured_control_tuple(self):
        for token in (
            "| `a600000.ssusb/mode` | `peripheral` |",
            "| `udc/state` | `configured` |",
            "| `udc/current_speed` | `super-speed` |",
            "| `configfs g1/UDC` | `a600000.dwc3` |",
            "`a600000.dwc3`, `dummy_udc.0`",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_withdraws_its_own_novelty_claims(self):
        # Both claims were checked against the campaign's own record after the
        # measurement, and both were too strong.
        for token in (
            "**First correction: this is not a new control.**",
            "S22PLUS_FYG8_P278_..._2026-07-26",
            "**Second correction: the runner is not a new instrument for the candidate.**",
            "p260_wait_role_and_udc",
            "p260_wait_configured",
            "a reproducible stock\ncontrol tuple",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_bounds_the_high_speed_predicate_without_calling_it_a_defect(self):
        for token in (
            "It is not a defect and not a discovery",
            "S22PLUS_FYG8_P274_..._2026-07-26",
            "finds no run\nin which stage `0x8f` produced `EPROTO`",
            "bounds it rather than clearing it",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_records_the_dummy_udc_trap_as_already_closed(self):
        for token in (
            "there is no\n`dummy_hcd.ko`",
            "built into the kernel",
            "That trap is already\nclosed",
            '`p260_udc_name` is the literal `"a600000.dwc3"`',
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_closes_the_module_identity_question_with_a_digest(self):
        for token in (
            "27e988788242888dc0c3acaf835a66585c024b034b07741e619b674ee77db3db  ramdisk",
            "27e988788242888dc0c3acaf835a66585c024b034b07741e619b674ee77db3db  vendor_dlkm",
            "here they\nare the same file",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_states_the_whole_tree_comparison_not_just_the_one_module(self):
        for token in (
            "441 `.ko` files",
            "`vendor_dlkm` holds 356",
            "**all 306 are byte\nidentical, with zero differences**",
            "every one of the 135 is in the ramdisk's\n  own 140-entry first-stage",
            "Not one of them matches `usb`, `typec`, `muic`, `pdic`, `dwc`, `phy`, or\n  `redriver`",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_states_the_consequence_for_a_candidate(self):
        for token in (
            "no difference between the two copies can explain any candidate\nfailure",
            "no candidate needs to mount a logical partition to reach the USB\npath",
            "strictly stronger statement than the matching\nvermagic",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_no_longer_lists_the_identity_question_as_open(self):
        self.assertNotIn(
            "- The ramdisk versus `vendor_dlkm` `pdic_max77705.ko` identity, "
            "still unresolved.",
            self.report,
        )

    def test_report_reproduces_the_review_counts_rather_than_repeating_them(self):
        for token in (
            "They were checked rather than repeated.",
            "**42\noverlapping and 27 genuinely late**, exactly the review's figures",
            "69 entries with 69 unique names, which is the\nself-check",
            "`EXPECTED_MODULE_PLAN_COUNT = 69`",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_verifies_the_candidate_passes_no_module_parameters(self):
        for token in (
            "**The candidate passes no module parameters at all.**",
            "it is the empty string for all 59 base entries",
            "verified in the plan rather\nthan inferred",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_reads_the_omission_as_a_substitution(self):
        for token in (
            "**The plan omits the stock mux driver, and the omission is a substitution.**",
            "`mfd_max77705.ko`, `spu_verify.ko` and `pdic_max77705.ko`",
            'CUSTOM_LATE_COMPAT = "maxim,max77705"',
            "Two drivers\ncannot bind one device",
            "not an oversight but a\nprecondition",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_scopes_the_consequence_to_p317_only(self):
        # The campaign has already corrected one generalisation from stock or
        # from one candidate to candidates at large; this must not repeat it.
        for token in (
            "The consequence is specific to P3.17 and must not be generalised.",
            "This says nothing about\nother candidates.",
            "S7A2, M7, M11, M12 and M18 did load `pdic_max77705` and failed\nanyway",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_does_not_read_the_96_omissions_as_a_defect(self):
        self.assertIn("omits 96 of the 140 stock first-stage modules", self.report)
        self.assertIn(
            "recorded as a fact about scope, not as a defect", self.report
        )

    def test_report_no_longer_lists_the_plan_diff_as_open(self):
        self.assertNotIn(
            "- The 69-entry P3.17 plan against the 140-entry first-stage list.\n",
            self.report,
        )

    def writer_graph_rows(self):
        section = re.search(
            r"^## The complete CONTROL1 writer graph$(.*?)(?=^### )",
            self.report,
            re.MULTILINE | re.DOTALL,
        )
        self.assertIsNotNone(section, "writer graph section missing")
        table = re.search(
            r"^\| Enclosing function \| Writes \| Trigger \|\n\|---\|---\|---\|\n((?:\|.*\n)+)",
            section.group(1),
            re.MULTILINE,
        )
        self.assertIsNotNone(table, "writer graph table missing")
        return table.group(1).splitlines()

    def test_writer_graph_count_matches_its_own_table(self):
        self.assertIn("eleven enclosing\nfunctions", self.report)
        self.assertEqual(len(self.writer_graph_rows()), 11)

    def test_report_records_the_symbol_table_method_correction(self):
        # Symbol absence for a static function is inlining, not absence; the
        # __func__ literal is the instrument that works.
        for token in (
            "**A method correction first.**",
            "the compiler inlines them",
            "`__func__` string literal each `pr_info` carries",
            "still leaves its name in `.rodata`",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_excludes_two_writers_with_their_evidence(self):
        for token in (
            "**`write_vps_regs` is dead as a writer.**",
            "sits inside an `#if 0`",
            "There is no\nrestore-previous-path behaviour.",
            "**The pogo writer is not compiled.**",
            "`CONFIG_MUIC_SM5504_POGO`",
            "On this device pogo cannot open the path.",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_proves_the_water_reroute_is_compiled_in(self):
        for token in (
            "pdic_max77705: %s water hiccup mode, Aux USB path",
            "`CONFIG_HICCUP_CHARGER`",
            "actively moves the mux to the\n**CP** path, not merely open",
            "initialised `false` at probe",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_answers_the_reopen_question_and_counts_the_mechanisms(self):
        for token in (
            "the path can be reopened or moved, and four\nof the mechanisms need no userspace",
            "Only `hiccup_store`\nrequires a userspace write",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_gives_the_stock_baseline_and_bounds_it(self):
        for token in (
            "`com_to_usb_ap` appears once",
            "each appear **zero** times",
            "writes\nCONTROL1 exactly once, to the AP USB path, and nothing reopens it",
            "bounded by the retained window",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_marks_the_water_branch_as_untestable_retrospectively(self):
        for token in (
            "a hypothesis with a cheap test rather than a finding",
            "the test cannot be run on them retrospectively",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_traces_the_chain_in_five_ordered_steps(self):
        section = re.search(
            r"^## The role-to-pull-up chain, traced$(.*?)(?=^### )",
            self.report,
            re.MULTILINE | re.DOTALL,
        )
        self.assertIsNotNone(section, "chain section missing")
        steps = re.findall(r"^\d\. ", section.group(1), re.MULTILINE)
        self.assertEqual(len(steps), 5)
        for token in (
            "`dwc3_msm_set_role`",
            "`dwc3_ext_event_notify`",
            "`dwc3_otg_sm_work`",
            "`dwc3_otg_start_peripheral`",
            "`dwc3_gadget_pullup`",
        ):
            with self.subTest(token=token):
                self.assertIn(token, section.group(1))

    def test_report_names_b_sess_vld_as_the_gate_and_the_flag_as_sticky(self):
        for token in (
            "**`B_SESS_VLD` is the gate, and it is not simply `vbus_active`.**",
            "That flag is sticky",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_justifies_the_runner_pair_as_a_mechanism(self):
        for token in (
            "### Why reading `mode` alone would have been a mistake",
            "sets that field\nunconditionally",
            "the state machine never leaves `DRD_STATE_IDLE`",
            "stated now as a mechanism instead of a preference",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_pins_the_single_extcon_to_eud_from_the_dtb(self):
        for token in (
            "`extcon = <0x139>`, a single\nphandle",
            "`qcom,msm-eud@88e0000`",
            "The plain `mdwc->vbus_active = event`\nelse-branch is unreachable here",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_records_the_truncated_read_correction(self):
        # A first pass stopped short of disable_eud's end and drew the wrong
        # conclusion from it.
        for token in (
            "A first reading of `disable_eud` stopped short of its end",
            "That was wrong",
            "Neither is the hazard.",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_localises_the_hazard_and_admits_it_is_undecided(self):
        for token in (
            "The hazard is `eud_event_notifier`",
            "sets `EXTCON_JIG` **true**",
            "cannot be settled statically",
            "/sys/module/eud/parameters/enable",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_closes_the_ss_mon_instance_question(self):
        for token in (
            "`vbus_session_notify(dwc->gadget, on, EAGAIN)`",
            "hard load-time dependency of dwc3-msm rather than optional\ntelemetry",
            "It does not, and the driver settles it in two lines.",
            "`if (!g_ss_monitor) return;`",
            "in `ss_monitor_alloc_inst`",
            "The **instance** is Samsung\ntelemetry into usblog and has no functional part in the pull-up.",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)
        self.assertNotIn("That narrower question stays open.", self.report)

    def test_report_withdraws_the_bootloader_unavailable_claim(self):
        for token in (
            "That is true of the AP material and\nmisleading as a conclusion.",
            "BL_S906NKSS7FYG8_S906NKSS7FYG8_MQB99315260_REV00_user_low_ship_MULTI_CERT.tar.md5",
            "It was never extracted. The bootloader was not missing; it\nwas unread.",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_separates_readable_from_encrypted_bootloader_images(self):
        for token in (
            "`%s : muic_set_path to USB`",
            "`0x88E0000`",
            "that must not be read as\nabsence",
            "`uefi.elf` has 7.97 bits per byte",
            "Static\nanalysis of the UEFI and ABL stages is blocked by that, not answered by it.",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_marks_its_own_bootloader_conclusion_as_reversed(self):
        # The first version of this subsection concluded the bootloader logs no
        # MUIC activity on a normal boot.  It does, on every boot.
        for token in (
            "**This subsection first concluded the opposite of what is written here, and the\nfirst version was wrong.**",
            "a search that looked at\none log format and generalised to the log",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)
        self.assertNotIn("all eight are kernel lines", self.report)
        self.assertNotIn("**unsupported within the retained window**, not refuted", self.report)

    def test_report_quantifies_the_second_log_format_it_had_missed(self):
        for token in (
            "a further **1168 lines**",
            "1,347,459\nto 11,701,965 microseconds",
            "**297 of them are Max77705 MUIC, CCIC or charger\nlines**",
            "The count is identical in both retained captures.",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_pins_the_control1_write_opcode_to_the_kernel_header(self):
        for token in (
            "`OP 0x06` is the CONTROL1 **write**",
            "`max77705.h:525` defines `OPCODE_BCCTRL1_R = 0x01`",
            "`OPCODE_CTRL1_W`, which is `0x06`",
            "independent evidence that the bootloader uses the same opcode numbering as the\nkernel",
            "**So the bootloader issues a CONTROL1 write on every normal boot",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_keeps_the_narrow_negative_that_survived(self):
        self.assertIn("`muic_set_path` is still absent from both captures", self.report)
        self.assertIn("That narrower negative\nsurvives; the broad one did not.", self.report)

    def test_report_resolves_the_inheritance_premise_from_both_ends(self):
        for token in (
            "The bootloader half is now positive",
            "read CONTROL1 as **`0x3f`**",
            "Both ends together say the mux is **not** in the USB position when a candidate\nstarts",
            "is not decided by this evidence",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_ledger_records_one_row_for_this_topic(self):
        rows = [
            line
            for line in LEDGER.read_text(encoding="utf-8").splitlines()
            if "h0-stock-choreography-1 " in line
        ]
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertIn("s22plus-fyg8-p319", row)
        self.assertIn(
            "P319_STOCK_USERSPACE_CHOREOGRAPHY_IMPLEMENTED_REVIEW_PENDING", row
        )
        self.assertIn("| 0/0 |", row)


if __name__ == "__main__":
    unittest.main()
