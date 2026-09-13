"""Real source selection, data factory and policy projection without device I/O."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

import test_s22plus_proportional_research_v1 as research

owner, scope = research.owner, research.scope
candidates = scope.candidates


class CapabilityIdentityTests(unittest.TestCase):
    def fixture(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        for name in ('AGENTS.md', 'docs/operations/DEVICE_ACTION_CONTRACT_DETAILS.md',
            'docs/operations/DEVICE_ACTION_RISK_TIERS.md', 'docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md',
            scope.POLICY, owner.PROFILE):
            path = root/name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes((owner.ROOT/name).read_bytes())
        return root

    def test_other_target_root_row_is_not_authority_but_common_rules_and_selected_policy_are(self):
        root = self.fixture(); first = scope.authority(root)
        path = root/'AGENTS.md'; original = path.read_text()
        path.write_text(original.replace('| Samsung Galaxy S20+ 5G', '| Samsung Galaxy S20+ updated 5G'))
        self.assertEqual(scope.authority(root), first)
        path.write_text(original+'\nAdditional common rule fixture.\n')
        self.assertNotEqual(scope.authority(root), first)
        path.write_text(original)
        selected = root/'docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md'
        selected.write_text(selected.read_text()+'\nChanged selected recovery scope fixture.\n')
        self.assertNotEqual(scope.authority(root), first)

    def test_cached_review_sources_refresh_when_selected_authority_bytes_change(self):
        root = self.fixture(); before = scope.review_sources(root)
        self.assertIs(scope.review_sources(root), before)
        selected = root/'docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md'
        selected.write_text(selected.read_text()+'\nChanged authority fixture.\n')
        after = scope.review_sources(root)
        self.assertNotEqual(before, after)
        paths = {value['path'] for value in after.values() if 'path' in value}
        for filename in ('s22plus_native_baseline_owner_v1.py', 's22plus_native_baseline_protocol_v1.py',
                         's22plus_native_reobservation_v1.py', 's22plus_boot_only_f1_transport.py'):
            self.assertTrue(any(path.endswith('/'+filename) for path in paths), filename)
        self.assertFalse(paths & scope.MUTABLE_INPUTS)
        self.assertNotIn(str(candidates.RESEARCH_DATA), paths)

    def test_new_candidate_data_uses_real_factory_without_changing_capability_sources(self):
        before = owner.core.json_sha256(scope.review_sources())
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)/'catalog.json'
            path.write_text(json.dumps(dict(schema=candidates.RESEARCH_DATA_SCHEMA, candidates=[dict(
                namespace='p392', run_id='0123456789abcdef0123456789abcdef', version='v0.2.0-rc.10',
                image_sha256='a'*64, profile='resident-v1')])) )
            code = '''from pathlib import Path
import os, json
from unittest import mock
original = Path.read_bytes
data = original(Path(os.environ['RESEARCH_TEST_CATALOG']))
def read(path):
    return data if path.name == 's22plus_native_research_candidates_v1.json' else original(path)
with mock.patch.object(Path, 'read_bytes', read):
    import s22plus_native_research_scope_v1 as scope
    import device_action_f1_live_v2 as live
    selected = scope.candidates.static('p392')
    print(json.dumps(dict(sources=scope.owner.core.json_sha256(scope.review_sources()),
        namespace=selected.declaration.IDENTITY.namespace,
        run_id=selected.declaration.IDENTITY.run_id_hex,
        profile=scope.candidates.research_profile(selected.declaration),
        routed='p392' in live.typed_evidence.SHELL_VARIANTS,
        native_inputs=len(selected.builder.source_receipts()))))
'''
            result = subprocess.run(['python3', '-c', code], cwd=owner.ROOT, env=dict(os.environ,
                PYTHONPATH=str(owner.ROOT/'workspace/public/src/scripts/revalidation'), RESEARCH_TEST_CATALOG=str(path)),
                text=True, capture_output=True, timeout=60, check=True)
            value = json.loads(result.stdout)
            self.assertEqual(value['sources'], before)
            self.assertEqual((value['namespace'], value['profile']), ('p392', 'resident-v1'))
            self.assertEqual(value['run_id'], '0123456789abcdef0123456789abcdef')
            self.assertTrue(value['routed']); self.assertGreater(value['native_inputs'], 100)

    def test_catalog_rejects_legacy_replacement_unknown_profile_duplicate_or_extra_field(self):
        root = self.fixture(); path = root/candidates.RESEARCH_DATA; path.parent.mkdir(parents=True, exist_ok=True)
        good = dict(namespace='p392', run_id='0123456789abcdef0123456789abcdef',
                    version='v0.2.0-rc.10', image_sha256='a'*64, profile='resident-v1')
        for patch in (dict(namespace='p391'), dict(profile='arbitrary-hardware'), dict(shell='id')):
            row = dict(good, **patch)
            path.write_text(json.dumps(dict(schema=candidates.RESEARCH_DATA_SCHEMA, candidates=[row])))
            with self.assertRaises(ValueError): candidates.research_data(root)
        path.write_text(json.dumps(dict(schema=candidates.RESEARCH_DATA_SCHEMA, candidates=[good, good])))
        with self.assertRaises(ValueError): candidates.research_data(root)
        path.write_text('{"schema":"x","schema":"y","candidates":[]}')
        with self.assertRaisesRegex(ValueError, 'duplicate'): candidates.research_data(root)

    def test_functional_assessment_does_not_transfer_to_another_native_context(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); (root/'workspace/private').mkdir(parents=True)
            functional = {name: dict(size=1, sha256='a'*64) for name in scope.MUTABLE_INPUTS}
            native = dict(native_sources=dict(functional, immutable=dict(size=1, sha256='b'*64)))
            request = dict(native_inputs=dict(functional, immutable=dict(size=1, sha256='c'*64)),
                           mutable_paths=sorted(scope.MUTABLE_INPUTS))
            path = root/'workspace/private/assessment.json'
            owner.publish(path, dict(schema='s22plus-functional-source-assessment-v1', verdict='PASS_GO', findings=[],
                independent_review=True, reviewer='fixture', **scope.source_assessment_binding(native, 'resident-v1')))
            current = copy.deepcopy(native); current['native_sources']['immutable']['sha256'] = 'c'*64
            name = sorted(scope.MUTABLE_INPUTS)[0]; request['native_inputs'][name] = dict(size=1, sha256='d'*64)
            with self.assertRaisesRegex(owner.BaselineError, 'exact executable bytes/context'):
                scope._scope_sources(root, request, current, 'resident-v1', owner.pin(path))


if __name__ == '__main__': unittest.main()
