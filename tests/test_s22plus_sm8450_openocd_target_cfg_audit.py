import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path("workspace/public/src/scripts/revalidation/s22plus_sm8450_openocd_target_cfg_audit.py")


def load_module():
    spec = importlib.util.spec_from_file_location("s22plus_sm8450_openocd_target_cfg_audit", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


SAMPLE_DTS = """
/ {
	cpus {
		cpu@0 {
			reg = <0x00 0x00>;
			phandle = <0x15>;
		};
		cpu@100 {
			reg = <0x00 0x100>;
			phandle = <0x16>;
		};
	};

	soc {
		cti@12010000 {
			compatible = "arm,coresight-cti", "arm,primecell";
			reg = <0x12010000 0x1000>;
			coresight-name = "coresight-cti-cpu0";
		};

		cti@112060000 {
			compatible = "arm,coresight-cti", "arm,primecell";
			reg = <0x12060000 0x1000>;
			coresight-name = "coresight-cti-cpu5";
		};

		ete5 {
			compatible = "arm,embedded-trace-extension";
			coresight-name = "coresight-ete5";
		};

		funnel_ete {
			compatible = "arm,coresight-static-funnel";
		};
	};
};
"""


class S22PlusSm8450OpenocdTargetCfgAuditTest(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def test_extracts_cpu_and_cti_topology(self):
        cpus = self.module.extract_cpus(SAMPLE_DTS)
        ctis = self.module.extract_cpu_ctis(SAMPLE_DTS)
        self.assertEqual([cpu["reg"] for cpu in cpus], [0x0, 0x100])
        self.assertEqual(ctis[0]["cpu"], 0)
        self.assertEqual(ctis[0]["reg_addr"], 0x12010000)
        self.assertEqual(ctis[1]["cpu"], 5)
        self.assertEqual(ctis[1]["node"], "cti@112060000")
        self.assertEqual(ctis[1]["reg_addr"], 0x12060000)

    def test_trace_hints_are_non_debugbase_hints(self):
        trace = self.module.collect_trace_hints(SAMPLE_DTS)
        self.assertEqual(trace["ete_count"], 1)
        self.assertTrue(trace["funnel_ete_present"])
        self.assertEqual(self.module.collect_debugbase_hints(SAMPLE_DTS), [])
        self.assertEqual(
            self.module.collect_debugbase_hints(
                'qcom,cpufreq-hw-debug {\ncompatible = "qcom,cpufreq-hw-epss-debug";\n};'
            ),
            [],
        )

    def test_cfg_audit_rejects_hardcoded_dbgbase(self):
        with tempfile.TemporaryDirectory() as tempdir:
            cfg = Path(tempdir) / "sm8450.cfg"
            cfg.write_text(
                "set CTIBASE { "
                + " ".join(f"0x{addr:08x}" for addr in self.module.EXPECTED_CTIBASE)
                + " }\n"
                + "target create SM8450.cpu0 aarch64 -dbgbase 0x12340000\n",
                encoding="utf-8",
            )
            result = self.module.inspect_cfg(cfg, self.module.EXPECTED_CTIBASE)
        self.assertFalse(result["checks_passed"])
        self.assertIn("cfg-hardcodes-dbgbase", result["reasons"])

    def test_cfg_audit_allows_dbgbase_text_in_comments(self):
        with tempfile.TemporaryDirectory() as tempdir:
            cfg = Path(tempdir) / "sm8450.cfg"
            cfg.write_text(
                "# No -dbgbase: use ROM table discovery.\n"
                + "set CTIBASE { "
                + " ".join(f"0x{addr:08x}" for addr in self.module.EXPECTED_CTIBASE)
                + " }\n"
                + "target create SM8450.cpu0 aarch64 -cti SM8450.cpu0.cti\n",
                encoding="utf-8",
            )
            result = self.module.inspect_cfg(cfg, self.module.EXPECTED_CTIBASE)
        self.assertTrue(result["checks_passed"])
        self.assertFalse(result["hardcodes_dbgbase"])

    def test_classify_accepts_complete_romtable_cfg_with_dbgbase_reason(self):
        cpus = [{"reg": index, "node": f"cpu@{index:x}", "phandle": index} for index in range(8)]
        ctis = [
            {"cpu": index, "node": f"cti@{addr:x}", "reg_addr": addr, "reg_size": 0x1000}
            for index, addr in enumerate(self.module.EXPECTED_CTIBASE)
        ]
        cfg = {"present": True, "checks_passed": True, "reasons": []}
        result = self.module.classify(cpus, ctis, [], cfg)
        self.assertEqual(result["result"], "sm8450_cfg_draft_ready_romtable_dbgbase")
        self.assertIn("dbgbase-not-source-proven-romtable-required", result["reasons"])


if __name__ == "__main__":
    unittest.main()
