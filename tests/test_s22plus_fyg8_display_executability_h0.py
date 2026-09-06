"""Behavioral negatives against the retained exact DT/source producer inputs."""
import copy
import json
from pathlib import Path
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'workspace/public/src/scripts/analysis'))
import s22plus_fyg8_display_executability_h0 as closure


class ClosureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        merged = ROOT / 'workspace/private/outputs/s22plus_fyg8_p351/h0-work/merged-0.dtb'
        if not merged.is_file():
            raise unittest.SkipTest('retained hash-bound merged DT/source inputs required')
        # The cached DT is one exact output from the pinned rev12 merge.
        old = json.loads((merged.parent / 'executability-v1.json').read_text())
        pin = next(r['merged'] for r in old['results'] if r['base'] == 0 and r['overlay'] == 10)
        if closure.identity(merged) != pin:
            raise ValueError('retained fixture identity changed')
        cls.tree = closure.fixed.parse_tree(merged.read_bytes())
        cls.texts = closure.source_inputs()
        cls.config = (ROOT / closure.fixed.DEFAULT_CONFIG).read_text()
        cls.metadata = closure.fixed.module_plan.load_metadata(ROOT / closure.fixed.DEFAULT_METADATA)
        source = cls.texts[closure.KERNEL / 'common/drivers/of/property.c']
        cls.rows = closure.fixed.fw.parse_supplier_bindings(source)
        cls.rules = closure.fixed.fw.parse_macro_parser_rules(source)
        cls.modules = set(json.loads((closure.PROVIDERS / 'scoped-linkage.json').read_text())['modules'])

    def derive(self, tree=None, modules=None):
        return closure.derive(tree or self.tree, self.rows, self.rules, self.metadata,
                              self.config, self.texts, self.modules if modules is None else modules)

    def test_real_required_relationships(self):
        result = self.derive()
        self.assertTrue(result['converged'])
        edges = result['edges']
        self.assertTrue(any(e['consumer'] == closure.SECONDARY and e.get('property') == 'qcom,dsi-phy' for e in edges))
        self.assertTrue(any(e['mechanism'] == 'rpmh_dev[SDE_RSC_INDEX + counter]' for e in edges))
        self.assertTrue(any(e['mechanism'] == 'global cmd_db_ready/read_addr provider' for e in edges))
        self.assertTrue(any(e['mechanism'] == 'of_bcm_voter_get' for e in edges))
        self.assertEqual(set(result['named_regulators']),
                         {'panel_vdd3', 'panel_vddr', 'panel_vci', 'panel_aee_fd', 'panel_elvss'})

    def test_missing_provider_rejected(self):
        for module in ('s2dos05-regulator.ko', 'i2c-gpio.ko', 'cmd-db.ko', 'icc-bcm-voter.ko', 'arm_smmu.ko'):
            with self.subTest(module=module), self.assertRaises(ValueError):
                self.derive(modules=self.modules - {module})

    def test_changed_device_scope_rejected(self):
        mutations = [
            (closure.BUS, 'reg', struct.pack('>I', 50)),
            (closure.PMIC, 'adc_mode', struct.pack('>I', 1)),
            (closure.SECONDARY, 'qcom,dsi-default-panel', struct.pack('>I', 1)),
            ('/soc/rsc@af20000/sde_rsc_rpmh', 'cell-index', struct.pack('>I', 1)),
            (closure.PMIC, 'status', b'disabled\0'),
        ]
        for path, key, value in mutations:
            tree = copy.deepcopy(self.tree)
            tree.nodes[path].properties[key] = value
            with self.subTest(path=path, key=key), self.assertRaises(ValueError):
                self.derive(tree)

    def test_unknown_required_driver_rejected(self):
        tree = copy.deepcopy(self.tree)
        phandle = max(tree.phandles) + 1
        node = closure.fixed.Node('/soc/unknown@0', tree.nodes['/soc'], {'compatible': b'unknown,driver\0'})
        tree.nodes[node.path] = node
        tree.phandles[phandle] = node
        tree.nodes[closure.MASTER].properties['connectors'] += struct.pack('>I', phandle)
        with self.assertRaises(ValueError):
            self.derive(tree)

    def test_dp_definition_in_either_owned_header_rejected(self):
        for name in ('config/gki_waipiodispconf.h', 'msm/samsung/panel_common_conf.h'):
            texts = dict(self.texts)
            texts[closure.DISPLAY / name] += '\n#define\tCONFIG_SECDP\t1\n'
            with self.assertRaises(ValueError):
                closure.check_dp_disabled(texts, '')
        with self.assertRaises(ValueError):
            closure.check_dp_disabled(self.texts, 'CONFIG_SECDP=m\n')


if __name__ == '__main__':
    unittest.main()
