"""Timed UDC selection and both evidence outcomes in the original RAM owner."""
import unittest
from unittest import mock

import test_s22plus_mainline_live_v1 as ram
import s22plus_mainline_auto_recovery_v1 as auto
import s22plus_native_records_v3 as records


class TimerSelection(unittest.TestCase):
    def test_ordinary_image_cannot_admit_a_timer_archive(self):
        p = auto.profile
        image = dict(schema='s22plus-mainline-image-v1', profile=p.PROFILE, namespace=p.NAMESPACE,
                     version=p.VERSION, run_id_hex='a'*32, ap={'sha256':'1'*64}, member={}, key={},
                     runtime_sources={'kernel':{'sha256':'2'*64}}, debian_ram={})
        qualified = dict(schema='s22plus-mainline-qualification-v1', status='PASS_H0_MAINLINE_CANDIDATE',
                         image=dict(image), package='package', loader='loader', init_manifest='manifest',
                         entry_review='review', loader_tests={}, entry_tests={}, device_actions=0)
        image['qualification'] = 'qualification'
        records_by_name = dict(qualification=qualified, package={}, loader={}, review={},
                               manifest=dict(debian_ram={}, udc_timer_return=True))
        with mock.patch.object(p, 'unchanged', side_effect=lambda receipt: receipt), \
             mock.patch.object(p, 'read', side_effect=records_by_name.__getitem__), \
             self.assertRaisesRegex(ValueError, 'outside the exact UDC image'):
            p.image_binding(image)

    def test_exact_ap_kernel_and_scope_without_candidate_files(self):
        p = auto.profile
        image = dict(schema='s22plus-mainline-image-v1', profile=p.PROFILE,
                     udc_observation={}, ap={'sha256': p.UDC_TIMER_AP},
                     runtime_sources={'kernel': {'sha256': p.UDC_TIMER_KERNEL}})
        request = dict(operation='mainline-ram', N=image)
        self.assertTrue(auto.selected(request))
        for patch in (dict(ap={'sha256': '0' * 64}), dict(runtime_sources={}),
                      dict(schema='other'), dict(profile='other')):
            self.assertFalse(auto.selected(dict(request, N={**image, **patch})))
        self.assertFalse(auto.selected(dict(request, operation='other')))
        self.assertFalse(auto.selected(dict(request, N={k:v for k,v in image.items() if k!='udc_observation'})))


class TimedOwner(unittest.TestCase):
    setUp = ram.OwnerTests.setUp
    operation = ram.OwnerTests.operation

    def run_owner(self, *, no_response=False, arrived=True, transfer_failure=None):
        session, device = self.operation()
        device.directory = session.directory
        device.fail_after = 'observation' if no_response else transfer_failure
        status = 'EXACT_DOWNLOAD_OBSERVED' if arrived else 'DOWNLOAD_NOT_OBSERVED'
        caps = []
        transfer = device.transfer

        def fixture_transfer(step, request, *, guard, before_launch, recovery_window=None):
            caps.append(recovery_window)
            return transfer(step, request, guard=guard, before_launch=before_launch)

        def fixture_arrival(*args):
            if arrived:
                device.mode = 'Download'
            return dict(status=status, observed_ns=records.clock())

        window = dict(operation=records.pin(session.directory/'operation.json'),
                      deadline_ns=records.clock()+1_000_000_000)
        device.transfer = fixture_transfer
        with mock.patch.object(auto.profile, 'timed_udc', return_value=True), \
             mock.patch.object(auto, 'window', return_value=window), \
             mock.patch.object(auto, 'selected', return_value=True), \
             mock.patch.object(auto, 'observe', side_effect=fixture_arrival) as observe:
            result = session.execute(attended=True)
        self.assertEqual(observe.call_count, 1)
        self.assertFalse((session.directory/ram.mainline.Coordinator.READY_FILE).exists())
        return session, device, caps, result

    def test_response_automatically_returns_original_a(self):
        session, device, caps, result = self.run_owner()
        self.assertEqual(result['state'], 'ANDROID_CLOSED')
        self.assertEqual(device.actions.count('mainline-request-once'), 1)
        self.assertEqual(device.installed, ['N','A'])
        self.assertEqual(caps[-1], records.pin(session.directory/auto.FOLDER/'window.json'))

    def test_missing_response_automatically_returns_original_a(self):
        session, device, caps, result = self.run_owner(no_response=True)
        self.assertEqual(result['state'], 'ANDROID_CLOSED')
        self.assertEqual(device.installed, ['N','A'])
        self.assertEqual(caps[-1], records.pin(session.directory/auto.FOLDER/'window.json'))

    def test_missed_arrival_leaves_physical_fallback_to_the_original_owner(self):
        session, device, caps, result = self.run_owner(arrived=False)
        self.assertEqual(result['state'], 'AWAITING_ATTENDED_RECOVERY')
        self.assertEqual(device.installed, ['N'])
        device.mode = 'Download'
        self.assertEqual(session.recover(attended=True)['state'], 'ANDROID_CLOSED')
        self.assertEqual(device.installed, ['N','A'])
        self.assertIsNone(caps[-1])
