"""Durable identity/deadline and explicit dynamic-source closure regressions."""
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import s22plus_fyg8_p384_candidate as candidate
import s22plus_fyg8_p384_process_v2_candidate_static as static


class Bindings(unittest.TestCase):
    def test_control_actual_sequence_raw_join_and_no_replay(self):
        owner = candidate.return_host
        request = dict(run_id_hex=candidate.IDENTITY.run_id_hex, mode='download', sequence=6,
            nonce_sha256='a'*64, kernel_boot_identity_sha256='b'*64,
            boot_id_semantic=candidate.CONTROL.BOOT_ID_SEMANTIC,
            boot_receipt_semantic=candidate.CONTROL.BOOT_RECEIPT_SEMANTIC)
        binding = dict(run='fixture'); lane = dict(accepted_for_p324=True, observation_phase='before-native-return-control')
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)
            receipt = owner.write_intent(path, binding=binding, endpoint_identity_sha256='e'*64, lane=lane, request=request)
            raw = (path/owner.INTENT_NAME).read_bytes()
            value, reopened = owner.read_intent(path, binding=binding, endpoint_identity_sha256='e'*64,
                proof=dict(control_sequence=6, nonce_sha256='a'*64, kernel_boot_identity_sha256='b'*64))
            self.assertEqual(receipt, reopened)
            self.assertGreater(owner.remaining_window(value), 0)
            for kwargs in (dict(binding=dict(run='foreign')), dict(endpoint_identity_sha256='f'*64),
                           dict(proof=dict(control_sequence=5, nonce_sha256='a'*64, kernel_boot_identity_sha256='b'*64))):
                with self.subTest(kwargs=kwargs), self.assertRaises(ValueError): owner.read_intent(path, **kwargs)
            with self.assertRaises(ValueError):
                owner.write_intent(path, binding=binding, endpoint_identity_sha256='e'*64, lane=lane, request=request)
            self.assertEqual((path/owner.INTENT_NAME).read_bytes(), raw)
            with mock.patch.object(owner, 'host_boot_sha256', return_value='c'*64):
                self.assertEqual(owner.remaining_window(value), 0)
            for sequence in (True, 4, 7):
                with self.subTest(sequence=sequence), self.assertRaises(ValueError): owner._request(dict(request, sequence=sequence))

    def test_dynamic_and_lazy_inputs_are_effective_closure_roots(self):
        paths = set(static.SOURCE_FILES.values()); root = static.ROOT
        for relative in ('workspace/public/src/scripts/revalidation/s22plus_fyg8_p321_artifact_identity.py',
                         'workspace/public/src/scripts/revalidation/s22plus_fyg8_p383_return_spec.py',
                         'workspace/public/src/scripts/revalidation/s22plus_fyg8_p328_auth_acm_observer.py',
                         'workspace/public/src/scripts/revalidation/s22plus_fyg8_p336_long_idle_acm_observer.py',
                         'workspace/public/src/scripts/revalidation/s22plus_fyg8_p363_return_host.py',
                         'workspace/public/src/scripts/analysis/s22plus_fyg8_p350_stock_candidate_build.py'):
            self.assertIn(root/relative, paths)
        self.assertTrue({root/name for name in static.builder.source_receipts()} <= paths)
        self.assertTrue({root/name for name in candidate.adapter.SOURCE_PATHS.values()} <= paths)
        self.assertIn(root/'workspace/public/src/scripts/revalidation/s22plus_native_roundtrip_owner_v1.py', paths)
        self.assertIn(root/'docs/operations/S22PLUS_NATIVE_ROUNDTRIP_FOLLOWUP_V2.md', paths)
        self.assertFalse(candidate.observer.audit_binding()['live_authorized'])

    def test_no_operator_plan_command_is_admitted(self):
        owner = candidate.console_owner
        plan = dict(schema=owner.SCHEMA, commands=[])
        # Validate without creating another candidate session or transport.
        value = dict(schema=owner.SCHEMA, commands=[dict(command='true')])
        with self.assertRaises(ValueError): owner.validate(value)
        with self.assertRaises(ValueError): owner.execution_projection(plan, [dict(sequence=5)])


if __name__ == '__main__': unittest.main()
