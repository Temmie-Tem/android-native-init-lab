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
        "Unpacking the volumes: two opened, the MUIC driver one level deeper",
        "system and product, swept in full",
        "What actually initiates the role on stock",
        "The candidate channel that works, and the one that never has",
        "Why the P3.18 carrier decoded as bad-body",
        "The failure vocabulary, measured on the candidate that actually ran",
        "Can the candidate bring UCSI up? No, and the missing piece is one module",
        "The CCIC half: the bootloader parks the connector",
        "The bootloader enumerates without any of the kernel's role machinery",
        "Three bootloader modes, and only one leaves the mux open",
        "The RDX bring-up is five calls, and only half of them can fail loudly",
        "Resolving the vtable slots to register writes",
        "The download branch does not repeat the RDX sequence; it adds one call",
        "The register accounting closes, and it closes on a bit the census hid",
        "The corpus holds kernel-side MUIC evidence, and all of it is stock",
        "The shipped MUIC attach guards do not block the AP path",
        "The stock DT and nested IRQ chain close through the nonnegative I2C write path",
        "The IRQ numbers are not stock properties; the offsets are",
        "Initial classification precedes unmask; the historical live-load claim did not survive",
        "The platform probe has two silent failure points, not one",
        "Successor H0 design: four of the five witnesses need no new code",
        "Successor transport correction: stock retention is not candidate retention",
        "Review of the transport binding: the emitters are not in the plan",
        "V2 plan input: the load order, and the DWC3 tie is one symbol on the DP path",
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
        # Checked against the whitespace-flattened text: a forward reference
        # that happened to straddle a markdown line break slipped past the raw
        # check, and one did.
        for phrase in ("section below", "Closed below", "the trace below", "see below"):
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, self.report)
                self.assertNotIn(phrase, re.sub(r"\s+", " ", self.report))

    def test_open_list_carries_no_struck_through_backlog(self):
        section = re.search(
            r"^## What remains open$(.*?)(?=^## )",
            self.report,
            re.MULTILINE | re.DOTALL,
        )
        self.assertIsNotNone(section)
        self.assertNotIn("~~", section.group(1))
        items = re.findall(r"^- ", section.group(1), re.MULTILINE)
        # Six became nine when the register-accounting unit landed, then eight
        # when the notifier entry was closed and removed rather than struck
        # through.  The count is pinned so the list cannot drift silently.
        self.assertEqual(len(items), 8)
        self.assertNotIn("holds no analysable BL", section.group(1))

    def test_report_warrants_the_host_end_separately(self):
        # The captures are bootloader-local; nothing in them shows a host.
        for token in (
            "**The host end of that sentence needs a separate warrant, and a review was right\nto ask for one.**",
            "**no per-capture receipt binds any of the 62 download\nhashes to a particular host session**",
            "That is recorded in the campaign ledger, not in these\ncaptures",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)
        self.assertNotIn("enumerates to a host on this exact hardware every time the campaign flashes.\n\nThat changes", self.report)

    def test_report_qualifies_the_xblramdump_vtable_finding(self):
        # One path using its own callbacks is not a proof about every path.
        self.assertIn("**on this path**, `XblRamdump` does not call the", self.report)
        self.assertIn("does not establish that no path in the image ever reaches the DXE drivers", re.sub(r"\s+", " ", self.report))

    def test_report_separates_the_irq_offsets_from_the_irq_numbers(self):
        flat = re.sub(r"\s+", " ", self.report)
        for token in (
            "**The offsets are the invariant.**",
            "**at least 24 distinct parent IRQ numbers**",
            "`367` occurs in 6 of the 111 captures that carry the thread",
            "**324 in one capture and 330 in another**",
            "**10 of 10** captures, 17 occurrences",
            "That holds **16 times out of 17**",
            "appears in **two of ten** captures",
            "eight run in an IRQ-thread context and nine in `modprobe` or `kworker` context",
            "three `com_to_usb_ap`, three `06 09` dumps and three notifier attaches",
            "There is no retained-window truncation to invoke",
        ):
            with self.subTest(token=token):
                self.assertIn(re.sub(r"\s+", " ", token), flat)
        self.assertNotIn("appears in only **one** capture", self.report)

    def test_report_records_both_silent_failure_points(self):
        flat = re.sub(r"\s+", " ", self.report)
        for token in (
            "the call at `:3835` is\nbare — no assignment, no test",
            "the branch at\n`.text+0xd4e8` is followed by `mov x0,x19`",
            "failure in that **pre-MUIC USBC IRQ\nfamily** does not block",
            "does not prove\nthat every nested MUIC IRQ-registration failure is non-blocking",
            "two further call sites, at `:2888` and `:2921`",
        ):
            with self.subTest(token=token):
                self.assertIn(re.sub(r"\s+", " ", token), flat)

    def test_report_carries_the_successor_witness_design(self):
        flat = re.sub(r"\s+", " ", self.report)
        for token in (
            "**121 of 121**, 1163 lines",
            "`vbusdet(0)` is a *positive* witness that\nregistration failed",
            "`status[3]` and `status[4]` are read into the buffer and never logged",
            "**14 of 121**",
            "**the\nboot window has already been overwritten in 107 of 121 retained captures.**",
            "It is a **byte budget**",
            "that rate is unmeasured",
        ):
            with self.subTest(token=token):
                self.assertIn(re.sub(r"\s+", " ", token), flat)

    def test_report_separates_stock_retention_from_the_candidate_transport(self):
        flat = re.sub(r"\s+", " ", self.report)
        for token in (
            "The exact P3.18 static closure says `sec_log_buf_absent=true`",
            "it contains neither `sec_log_buf.ko` nor the stock `mfd_max77705.ko` and `pdic_max77705.ko`",
            "requires `head->idx == seed_idx` before every later update",
            "Adding that module therefore requires a Carrier redesign and is forbidden for this successor",
            "P3.18 inherited the P3.03 live `/dev/kmsg` observer",
            "`EPIPE` is an explicit ring-loss terminal",
            "drain after each relevant module rather than waiting for the whole loop",
            "publish their structured summary through the direct Carrier",
            "4111 bytes/SHA-256 `ef917cd3...`",
            "24025 bytes/SHA-256 `13f22634...`",
            "7386-byte focused test source is `0b3edc5e...`",
            "`20260820-01-failed-before-result` directory is preserved",
            "external-corpus qualification of the bounded P3.19 live-kmsg parser",
        ):
            with self.subTest(token=token):
                self.assertIn(token, flat)

    def test_report_records_the_transport_review_gap(self):
        flat = re.sub(r"\s+", " ", self.report)
        for token in (
            "**Every one\nof those lines is emitted by `pdic_max77705` or `mfd_max77705`**",
            "on the\ncurrent plan the parser has nothing to parse",
            "That requirement is load-bearing and unstated",
            "it fails closed on\nexactly the plan shape the successor needs",
        ):
            with self.subTest(token=token):
                self.assertIn(re.sub(r"\s+", " ", token), flat)

    def test_report_carries_the_v2_plan_input(self):
        flat = re.sub(r"\s+", " ", self.report)
        for token in (
            "**13 direct\ndependencies**",
            "The transitive closure is **14\nmodules**",
            "returns exactly **one** name",
            "`R_AARCH64_CALL26` at\n`.text+0x12318`",
            "**`max77705_vdm_dp_select_pin`**",
            "nothing here authorises a stub",
        ):
            with self.subTest(token=token):
                self.assertIn(re.sub(r"\s+", " ", token), flat)

    def test_report_states_the_h0_only_authority_boundary(self):
        for token in (
            "IMPLEMENTED_REVIEW_PENDING",
            "PASS_GO_P319_CANDIDATE_PDIC_PROBE_BOUNDARY_V2_H0_CAPABILITY",
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
            "neither `is_blocked` nor `get_otg_notify` appears\namong its undefined symbols",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_records_the_module_parameter_mechanism_and_why_it_is_benign(self):
        for token in (
            "muic_param_pmic_info=3",
            "There\nis no `modules.options` anywhere",
            "which is overbroad — `insmod` can pass parameters",
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
            "and that is wrong as stated",
            "`pdic_max77705` is not a second driver on the `maxim,max77705` parent",
            "The 69-entry plan is unchanged by this correction; only the\nexplanation was wrong.",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_scopes_the_consequence_to_p317_only(self):
        # The campaign has already corrected one generalisation from stock or
        # from one candidate to candidates at large; this must not repeat it.
        for token in (
            "The consequence is specific to P3.17 and must not be generalised.",
            "This says nothing about\nother candidates.",
            "The S7A2, M7, M11, M12 and M18 plans included\n`pdic_max77705`",
            "Treating plan inclusion\nas a successful live load was an overstatement",
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
            "That remains a hypothesis with a\ncheap future test rather than a retrospective finding",
            "the test cannot be run retrospectively",
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

    def test_report_keeps_the_dt_fact_and_drops_the_runtime_inference(self):
        for token in (
            "`extcon = <0x139>`, a single phandle, and `0x139` is `qcom,msm-eud@88e0000`",
            "The DT fact stands",
            "The registration does not happen.",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_keeps_the_eud_readings_that_survived(self):
        for token in (
            "`disable_eud` does end\nconnected",
            "`eud_event_notifier` does set `EXTCON_JIG`\ntrue",
            "Neither matters here, because nothing\nsubscribes.",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_reverses_the_eud_extcon_runtime_claim(self):
        # dwc3-msm registers no DT extcon notifier in this build; the sticky
        # EUD_SPOOF_DISCONNECT hazard is a source path that is not armed here.
        for token in (
            "**This subsection and the one that followed it were wrong, and an independent\nreview found it.**",
            "The device-tree half is right and the runtime half is not.",
            "does not import `extcon_register_notifier` or\n`extcon_get_edev_by_phandle` at all**",
            "The hazard is a real source path in a build\nthat enables it, and this is not that build.",
            "`enable_usb_notify`",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)
        self.assertNotIn("every extcon\nevent dwc3-msm can receive on this device is an EUD event", self.report)

    def test_report_withdraws_the_ss_mon_telemetry_only_claim(self):
        for token in (
            "hard load-time dependency of dwc3-msm rather than optional\ntelemetry",
            "an\nindependent review found that wrong.**",
            "the same\nnarrow-sample shape this unit made four other times",
            "`schedule_work(&…->set_vbus_current_work)`",
            "the\ninstance is **not** telemetry-only",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)
        self.assertNotIn("has no functional part in the pull-up", self.report)

    def test_report_withdraws_the_bootloader_unavailable_claim(self):
        for token in (
            "That is true of the AP material and\nmisleading as a conclusion.",
            "BL_S906NKSS7FYG8_S906NKSS7FYG8_MQB99315260_REV00_user_low_ship_MULTI_CERT.tar.md5",
            "It was never extracted. The bootloader was not missing; it\nwas unread.",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_identifies_the_images_as_uefi_volumes(self):
        for token in (
            "### Three images are compressed containers, and that route is open",
            "Both were\nwrong, and the error was declaring impossibility without trying the standard\nthing.**",
            "`78e58c8c-3d8a-4f1c-9935-896185c32dd3`, which is `EFI_FIRMWARE_FILE_SYSTEM2`",
            "`9e21fd93-9c72-4c15-8c4b-e77f1db2d792`",
            "entropy **6.13**, not high at all",
            "The\ncorrect status is *untried*, not *impossible*",
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
            "**So the bootloader issues a CONTROL1 write roughly 1.68 seconds into XBL",
            "Two captures do\nnot establish \"every boot\"",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_keeps_the_narrow_negative_that_survived(self):
        self.assertIn("`muic_set_path` is still absent from both captures", self.report)
        self.assertIn("That narrower negative\nsurvives; the broad one did not.", self.report)

    def test_report_reopens_the_written_value_route(self):
        # An earlier version called the UEFI/ABL images opaque and the written
        # CONTROL1 value unrecoverable.  Both were premature.
        for token in (
            "**The code that did run is in none of the extracted images as plaintext.**",
            "has not been\nattempted",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)
        self.assertNotIn("recoverable from this host by any means identified here", self.report)

    def test_report_reads_the_role_selection_from_registers(self):
        for token in (
            "and w8, w0, #0xffffcfff  ; clear PRTCAPDIR, bits [13:12]",
            "orr w1, w8, #0x2000      ; PRTCAPDIR = 0b10 = device",
            "`mov wN, #0xc110` occurs at exactly **two** sites",
            "and  w1, w0, #0xffffff3f             ; clear bits [7:6], GCTL_RAMCLKSEL",
            "bfxil w1, w0, #0, #19",
            "*The branch claim was false as written.*",
            "not\ndownward from a slot literally named `InitDevice`",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)
        self.assertNotIn("not from disassembling `InitDevice`", self.report)

    def test_report_reduces_the_candidate_instruction_to_one_action(self):
        for token in (
            "the value **0 in all 103 captures**",
            "| `[ ABL ] SetPath` | **62 / 62** | **0 / 41** |",
            "what the download branch adds is `muic_set_path(1)` **alone**",
            "**Setting the sink is therefore not a precondition for enumeration**",
            "**On the bootloader side, the difference between a boot that enumerates and one\nthat does not reduces to one action: write `COM_USB` to `CONTROL1`.**",
            "must not be read as an\ninstruction that would make a candidate work",
            "Five candidate *plans* — `S7A2`, `M7`, `M11`, `M12`, `M18` — included",
            "it has **not** shown that a candidate ever\nreached the stock writer",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)
        self.assertNotIn("the one\n  remaining gap in the five-call sequence", self.report)

    def test_report_bounds_the_static_bootloader_conclusion(self):
        for token in (
            "everything above is **static**",
            "not code observed executing on a\nparticular boot",
            "does not establish that the write landed",
            "follows from that, not from a proven execution",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)
        self.assertNotIn("exactly as\nOdin and RDX do", self.report)

    def test_report_does_not_claim_linux_cannot_issue_the_opcode(self):
        for token in (
            "**An earlier version of this sentence said Linux never issues it. That is\nwithdrawn as a capability claim.**",
            "`MXIM_DEBUG_OPCODE_WRITE` ioctl copies a user buffer",
            "**no Samsung enum entry, constant, or named helper for\n`0x5E` exists**",
            "F1-class for this campaign and no write through it has been made",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)
        self.assertNotIn("Linux never issues and does not name", self.report)

    def test_report_bounds_its_scan_and_container_claims(self):
        for token in (
            "`0x22a4 + table_byte * 4`",
            "path id 1 selects `0x0d` and lands at `0x22d8`, not at `0x22a8`",
            "2168:  mov w0, #0x1 ; 216c: bl 0x27cc",
            "Read the count as *three direct callers*, not as a\nproof that no other call site exists",
            "which is a statement about the four container\nlayers actually opened",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)
        self.assertNotIn("Nothing here was encrypted or Qualcomm-proprietary", self.report)

    def test_report_withdraws_the_rcps_reading_of_path_id_six(self):
        for token in (
            "**This row previously said it clears `RCPS` and leaves `COMN1SW`/`COMP2SW`\nuntouched. That was wrong and is withdrawn.**",
            "read-modify-write\nof **`BCCTRL1` bit 6**",
            "**The bit has a name, and an earlier version of this paragraph wrongly said it\nhad none.**",
            "BC_CTRL1_UIDEN_SHIFT       6",
            "therefore **`BC_CTRL1_UIDEN`**, bit 6",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)
        self.assertNotIn("clears `RCPS`, bit 6, and leaves", self.report)

    def test_report_resolves_the_slots_and_splits_the_opcode_provenance(self):
        for token in (
            "`{0x20c8, 0x210c, 0x2268, 0x2350}`",
            "`{0x2070, 0x20c0, 0x2144, 0x21f8}`",
            "`OPCODE_HVCTRL_R = 0x11`",
            "`0b 0d 0f 11 13 00 00`",
            "| 5 | `BCCTRL1` bit 6 **set** | `0x01` read, `0x02` write |",
            "the CCIC half is not",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_separates_entering_the_sequence_from_switching_the_mux(self):
        for token in (
            "`+0` probe, `+8` init, `+16` set_path, `+24` init_hv_control",
            "`cmp w8,#0x1a ; ccmp w8,#0x10,#0x4,ne ; b.eq`",
            "**execute a bare `ret`**",
            "returns **`-2`** when clear",
            "**And the log line is emitted before the call, unconditionally.**",
            "evidence that the\nsequence was *entered*, not that the mux was *switched*",
            "in this image the retry loop waits for nothing",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_open_list_does_not_relist_what_the_unit_closed(self):
        # The bootloader OP 0x06 bullet was closed by the Muic.efi disassembly;
        # the section states the removal rather than silently dropping it.
        self.assertIn("That\nentry is **closed**", self.report)
        self.assertIn("which is the reason this section is restated rather than appended to.", self.report)
        self.assertNotIn("whose Qualcomm-specific file\n  layout is not yet decoded", self.report)
        self.assertIn("`xbl_s.melf` (three LZMA candidates inside)", self.report)

    def test_report_withdraws_the_two_candidate_boots_claim(self):
        for token in (
            "**that is withdrawn**",
            "inherited from an earlier ledger row and not checked",
            "`candidate_observer_accepted` as **false**",
            "`rollback-observer-1.bin` and `rollback-observer-2.bin` — the rollback\nside, not two candidate boots",
            "is **not established** by anything on this host",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)
        self.assertNotIn("on two complete candidate boots, before writing", self.report)

    def test_report_widens_the_system_product_negative_with_the_full_sweep(self):
        for token in (
            "`system/etc/init` holds 108 files and exactly two of them name any USB path",
            "and no\n`android.hardware.usb.gadget` / `IUsbGadget` entry at all",
            "The privileged\nsweep has since run and the bound can be lifted",
            "**from `product`: nothing at all**",
            "`usbd` is an `IUsbGadget` **client**",
            "`IUsbGadgetCallback`",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)
        self.assertNotIn("the negative is about init, not about the whole partition", self.report)

    def test_report_states_what_the_sweep_does_not_establish(self):
        for token in (
            "named rather than characterised",
            "the jars\nand the APK were not decompiled",
            "establishes **which** artifacts\nreference those surfaces and not what they do with them",
            "they are requirements documents and not\nevidence that one exists",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_identifies_the_stock_role_initiator(self):
        for token in (
            "`usb_role_switch_register` at\n  `dwc3-msm-core.c:6091`",
            "`:5564` by `if (!mdwc->role_switch && !mdwc->extcon)`",
            "**that fallback does not run**",
            "contains no `usb_role_switch` reference at all",
            "**no module in `vendor_dlkm` defines any of them**",
            "the UCSI core is built into the kernel image",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_marks_the_role_chain_as_derived_not_traced(self):
        for token in (
            "corroborate the ordering without proving the call",
            "log at `dev_dbg`",
            "**not a traced call**",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_separates_the_analog_path_from_the_role(self):
        for token in (
            "seven are `qcom_glink`, `qcom_glink_smem`, `qcom_smd`,",
            "They are\nthere because they carry the role",
            "owns the **analog** D+/D- path through CONTROL1",
            "UCSI over GLINK owns\nthe **role** that starts the gadget",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_records_the_silent_acm_channel(self):
        for token in (
            "There are **28**",
            "**all 28 are zero bytes**",
            "`classification: endpoint-timeout` with `accepted: false` — 28 of 28",
            "`300.026865` seconds",
            "**The CDC-ACM observer has never\nreturned a byte.**",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_corrects_the_no_evidence_overreach(self):
        for token in (
            "**That was wrong**",
            "one channel was checked and the conclusion was generalised to all channels",
            "contains the marker **`S22E1L2|`**",
            "generation 47, stage `0x66`, item 38, failure\n`0x6010`",
            "the correct statement is a split, not an absence",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)
        self.assertNotIn("never captured a single byte of runtime evidence", self.report)

    def test_report_names_the_real_evidence_frontier(self):
        for token in (
            "they no longer need a *new* channel",
            "`[valid, bad-body]`",
            "payload integrity on a working\ncarrier, not the absence of a carrier",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_decodes_the_carrier_frame_at_its_offset(self):
        for token in (
            "offset **1,649,274**",
            "a 32-byte header plus two 80-byte\nslots",
            "`header_crc_valid: true`",
            "`slot_status: ['valid', 'bad-body']`",
            "**slot 0 is valid**: generation 46, stage `0x65`",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_isolates_which_bad_body_cause_fired(self):
        for token in (
            "one label for three very different situations",
            "**So slot 1 is authentic and undamaged.**",
            "`s22plus_fyg8_p294_telemetry_spec.py:417`",
            "`detail >= 0xC00`",
            "**policy refusal of a real datum**, not a corrupted payload",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_records_the_wrong_profile_self_correction(self):
        for token in (
            "an earlier run of this decode reported *both* slots as\n`bad-body`",
            'the profile string was guessed as `"p318"`',
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_credits_the_campaign_and_names_what_was_missing(self):
        for token in (
            "`valid-bad-body-recovered-0x6010`",
            "deliberate,\nrecorded practice and not an unnoticed integrity gap",
            "is the *reason* the\ndecoder refused it, which is now named",
            "not building a new channel",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_measures_the_real_candidate_population(self):
        for token in (
            "the third of its kind in this unit",
            "Neither number was about a candidate.",
            "holds **256** detail constants",
            "**176 are referenced**",
            "**163 of those are at or above `0xC00`**",
            "**52 are routed**",
            "**79 are covered by neither**",
            "48 percent of the reachable vocabulary rather than 99 percent",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)
        self.assertNotIn("**exactly one** of those 108 is routed", self.report)
        self.assertNotIn("The split is generational and total.", self.report)

    def test_report_describes_the_gap_between_two_models(self):
        for token in (
            "two islands with a gap between them",
            "| P3.07 | 0 | 0 | 9 | 9 |",
            "sits in the middle of that gap",
            "validated by a model that brackets it on both sides",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_keeps_the_frozen_spec_refusal_and_the_design(self):
        for token in (
            "**The frozen specs must not be edited**",
            "**Emitter-side.**",
            "**Decoder-side, diagnostic only.**",
            "now a measured size for that work rather than an estimate",
            "This unit stops at the\nmeasurement and the design.",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_still_credits_the_prior_semantic_record(self):
        for token in (
            "What is **not** new here is the meaning of `0x6010`",
            "S22PLUS_FYG8_P318_POSTLIVE_EUD_INDEX_RECOVERY_H0_2026-08-17.md:62",
            "makes the\nproposed read a duplicate",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_answers_the_ucsi_question_from_the_materialized_plan(self):
        for token in (
            "`s22plus_fyg8_p286_e3_plan.h` at 70 entries, not a reconstruction",
            "**zero violations**",
            "And it still cannot work.",
            'qcom,pmic-glink-channel  = "PMIC_RTR_ADSP_APPS"',
            "**neither is in the candidate's 70-entry plan.**",
            "four of its objections were\nverified as correct.**",
            "`schedule_work(&pgdev->init_work)` occurs **exactly once**",
            "a driver with no device tree node cannot bind",
            "after boot **initiation**,\nnot after completion",
            "This is **conditional**, not proved.",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_states_the_dependency_versus_device_lesson(self):
        for token in (
            "The methodological point is worth more than the fact",
            "`modules.dep` records\n**symbol** dependencies",
            "What it needs is a **device**",
            "Dependency-safe is not the same as\nfunctional",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_scopes_the_ucsi_finding_as_static(self):
        self.assertIn(
            "It\nis not a candidate observation, and there are none to be had; it says the plan\ncannot work, not that a run was seen failing this way.",
            self.report,
        )

    def test_report_reports_an_attempt_not_a_plan(self):
        for token in (
            "reports an actual attempt rather than a plan",
            "`ee4e5898-3914-4259-9d6e-dc7bd79403cf`",
            "expands 754989 bytes to **3592584**",
            "expands to **3166216**",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_credits_abl_with_the_cmdline_composition(self):
        for token in (
            "**ABL is where the kernel command\nline carrying those module parameters is composed**",
            "`common_muic.muic_param_pmic_info=3`",
            "rather than through a `modules.options` file",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_records_locating_the_muic_driver(self):
        for token in (
            "**What ABL does not contain is the MUIC driver.**",
            "ABL **consumes** UEFI protocols",
            "**The MUIC driver was then located, and the obstacle was mine.**",
            "are a textbook pad file",
            "`1f 8b 08 00` — **gzip**",
            "**`Ccic`** and **`Muic`**, 36946 bytes",
            "blockers were a pad-file bug and an assumption that the compression was LZMA",
            "### The value the bootloader writes is `0x3f`, COM_OPEN",
            "`0b 0d 0f 11 13 00 00`",
            "| 0 | `0x3f` | **`COM_OPEN`** |",
            "| 2 | `0x9b` | **`COM_UART`** |",
            "| 4 | `0xad` | **`COM_UART_CP`** |",
            "All five arithmetic checks match exactly",
            "**So the bootloader's initialisation path writes `0x3f`, COM_OPEN.**",
            "**That closes one half of a question this campaign has carried for months, and\nonly one half.**",
            "**It is\nwithdrawn again, and this time the reason is mechanical rather than\nevidentiary.**",
            "### The captured boots executed that path, opcode for opcode",
            "`\"muic_init: Error locating the CCIC protocol\"`",
            "including what is **missing** from\nit",
            "`0xC5` has bit 0 set",
            "is not a coincidence, and it\npins the executed path rather than inferring it",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_attributes_setpath_to_odin(self):
        for token in (
            "**`{ <us> }[ ABL ]`** — 1179, 1188 and 786 lines",
            "Launching odin -927639495",
            "**This report first attributed the line to Odin; that attribution is\nsuperseded below and is wrong.**",
            "the bootloader tail in every\nretained capture is a **download-mode session**, not a normal boot",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_resolves_the_candidate_0x3f_reading(self):
        for token in (
            "| **Download** | ABL → Odin |",
            "| **Normal** | ABL → LinuxLoader | no `SetPath` evidenced |",
            "**That is withdrawn**, for the third and\nlast time in this report.",
            "**why Download mode enumerates to a host while a candidate never has.**",
            "What the captures license is a statement\nabout *stock normal boots*",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_checks_the_abl_claim_against_every_capture(self):
        for token in (
            "### Checked against every capture, not three",
            "the same shape as\nfive other errors in this unit",
            "| → Odin (download mode) | **62** |",
            "| → normal handoff to Linux | **41** | **41** | **none at all, in all 41** |",
            "`SetPath: 0` never appears",
            "from *not evidenced* to **evidenced absent**",
            "**corrects a claim\nthis report briefly carried**",
            "987509 is `0xf1175`, not\n`0xf1195`",
            "finds **three** call sites",
            "belongs to **LinuxLoader's download-mode\nbranch**",
            "**three** callers, each with its argument in view",
            "| `0x45a98` |",
            "**no call site in LinuxLoader passes 0**",
            "it never writes `COM_OPEN`",
            "sixth instance in this unit of\nconcluding absence from an incomplete search",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)
        self.assertNotIn("There is **no capture of a normal boot's ABL stage**", self.report)

    def test_report_records_the_bootloader_usb_stack(self):
        for token in (
            "`UsbfnDwc3Dxe` at 102400 bytes is a full DWC3 **function**",
            "UsbCoreIfc->InitDevice",
            "`Cannot simulate host and device at the same time`",
            "There is no role\nswitch, no UCSI, no extcon and no PDIC anywhere in that path",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_reweights_the_ucsi_finding(self):
        for token in (
            "**not a precondition for device-mode enumeration on this SoC**",
            "**the candidate does not need to reach it.**",
            "the register evidence is\nattached to the Usbfn DWC3 driver's init path rather than to that name",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_completes_the_three_bootloader_modes(self):
        for token in (
            "`--adjust-vma=0xa7d00000`",
            "**`init_device_for_rdx`**",
            "| **normal boot** | nobody after XBL's `muic_init` | **`0x3f` COM_OPEN** |",
            "**Every bootloader mode that needs USB routes the mux explicitly, and the normal\nboot is the only one that does not.**",
            "it must route the analog path itself",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_report_separates_candidate_load_probe_init_and_unmask(self):
        for token in (
            "## Initial classification precedes unmask; the historical live-load claim did not survive",
            "`initial-probe captures == AP-path captures - chgtyp-IRQ captures`",
            "The initial\nattach therefore does not wait for a physical CHGT interrupt",
            "the `bl max77705_muic_probe` at `.text+0xd4f0` is followed by\n`mov x0,x19`",
            "`probing Complete..` or `cc_booting_complete == 1` does not prove",
            "The exact 100669481-byte S7A2 AP was unpacked again",
            "`mfd_max77705` 82,\n`spu_verify` 83 and `pdic_max77705` 84",
            "Their\nplans included it; their live `finit_module` results, platform binds, initial\nclassifications and unmask write results are unknown.",
            "durable per-module `finit_module` results",
            "the final VBUSDET `request_threaded_irq` result",
            "The bind, VBUSDET and initial-status witnesses must be retained together",
            "a readback of parent INTSRC mask register `0x23` with bit 3 clear",
            "reviewed V1 private receipt is 12719 bytes/SHA-256 `d4d40565...`",
            "Fifteen focused real-input and mutation tests pass.",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)
        self.assertNotIn("did load `pdic_max77705` and failed", self.report)
        self.assertNotIn("candidates that did load\n  `pdic_max77705`", self.report)

    def test_report_separates_usbc_and_nested_muic_irq_failures(self):
        for token in (
            "## The platform probe has two silent failure points, not one",
            "APC, SYSMSG, VDM0 through VDM6, and VIR0 interrupt\nfamilies",
            "This does not prove\nthat every nested MUIC IRQ-registration failure is non-blocking.",
            "UIADC, CHGT, DCD, VBADC and\nVBUSDET in that order",
            "a CHGT\nregistration failure can be hidden by a later successful request",
            "takes\n`fail_init_irq` before `max77705_muic_init_detect()`",
            "absence of a delivered CHGT\ninterrupt does not explain an absent **initial** mux transition",
            "counts all three source call sites but semantically reads only the\nprobe-path",
            "current V2 receipt is 14440 bytes/SHA-256 `cd3969eb...`",
            "The 14091-byte `3a4765ad...` intermediate is preserved",
            "Only V2 is the successor under the original\n`candidate-pdic-probe-boundary` review obligation.",
            "Independent source review reproduced the exact 14440-byte `cd3969eb...`\nreceipt",
            "The implementation\nsnapshot literally ran all 298 P3.19 tests successfully.",
            "measured 297/298, with only the known unrelated raw-first 1726/1729 identity\ndrift",
            "again measured\n297/298 but regenerated 1724 against the same preserved 1726",
            "Common Process-v2 passes 122/122.",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)
        self.assertNotIn(
            "a candidate that fails to register the MUIC interrupt handlers",
            self.report,
        )
        self.assertNotIn(
            "removes one otherwise attractive explanation for the five candidates",
            self.report,
        )

    def test_ledger_appends_the_v2_scope_correction(self):
        rows = [
            line
            for line in LEDGER.read_text(encoding="utf-8").splitlines()
            if "h0-candidate-pdic-probe-boundary-v2-6" in line
        ]
        self.assertEqual(len(rows), 1)
        self.assertIn("nonfinal failure such as CHGT can therefore be masked", rows[0])
        self.assertIn("final VBUSDET failure", rows[0])
        self.assertIn("original unresolved candidate-pdic-probe-boundary", rows[0])
        self.assertIn("creates no second obligation or PASS_GO", rows[0])
        review_rows = [
            line
            for line in LEDGER.read_text(encoding="utf-8").splitlines()
            if "h0-candidate-pdic-probe-boundary-review-5" in line
        ]
        self.assertEqual(len(review_rows), 1)
        self.assertIn(
            "PASS_GO_P319_CANDIDATE_PDIC_PROBE_BOUNDARY_V2_H0_CAPABILITY",
            review_rows[0],
        )
        self.assertIn("final VBUSDET registration result", review_rows[0])
        self.assertIn(
            "resolves only the matching candidate-pdic-probe-boundary topic",
            review_rows[0],
        )

    def test_ledger_appends_the_candidate_transport_review_obligation(self):
        rows = [
            line
            for line in LEDGER.read_text(encoding="utf-8").splitlines()
            if "h0-candidate-witness-transport-7" in line
        ]
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertIn(
            "P319_CANDIDATE_WITNESS_TRANSPORT_IMPLEMENTED_REVIEW_PENDING", row
        )
        self.assertIn("stock retained-log survival does not transfer", row)
        self.assertIn("4111-byte ef917cd3", row)
        self.assertIn("13 focused tests pass", row)
        self.assertIn("Independent review remains mandatory", row)
        self.assertIn("no device", row)

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
